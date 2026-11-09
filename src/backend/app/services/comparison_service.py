"""So sánh văn hoá 2 quốc gia × 1 chủ đề (F3, AC11): trả bản đã lưu nếu có, nếu không thì AI sinh bản nháp (BR07).

1. Tìm bản đã lưu (cả hai chiều A–B / B–A). Bản `published` → `reviewed = true`, không gọi LLM (AC11.1).
   Bản nháp đã sinh trước đó cũng được trả lại → mỗi bộ (A, B, chủ đề, ngôn ngữ) chỉ gọi LLM một lần.
2. Chưa có: truy xuất bằng chứng RIÊNG cho từng nước (app/ai/retrieval.py), LLM điền bảng theo nhãn c#.
3. Kiểm từng ô: ô của nước A chỉ được dùng bằng chứng của A (B tương tự); điểm giống phải có bằng chứng của cả hai.
   Ô không đạt → null ("Chưa đủ nguồn để kết luận"), không bao giờ để LLM tự lấp (AC11.2).
4. Lưu `comparisons` với status = draft, origin = ai_generated (AC11.3) để biên tập viên duyệt.
"""
from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.llm_adapter import LLMAdapter, LLMUnavailable
from app.ai.retrieval import Embedder, Evidence, Reranker, retrieve
from app.ai.suggestions import CATEGORY_VI
from app.ai.vector_store import VectorSearch
from app.core.errors import ProblemError
from app.repositories.entry_repo import get_sources

PROMPT = (Path(__file__).resolve().parents[1] / "ai" / "prompts" / "compare_vi.txt").read_text(encoding="utf-8")
EVIDENCE_PER_COUNTRY = 6
MAX_ROWS = 6
MAX_CELL_CHARS = 400

# Tên chủ đề tiếng Anh: bằng chứng phần lớn là tiếng Anh nên tìm thêm bằng truy vấn tiếng Anh
CATEGORY_EN: dict[str, str] = {
    "greetings": "greetings", "etiquette": "etiquette manners", "food_dining": "food dining cuisine",
    "gift_giving": "gift giving gifts", "festivals": "festivals celebrations", "religion_beliefs": "religion beliefs",
    "clothing": "clothing traditional dress", "arts_music": "arts music", "family_life": "family life",
    "heritage": "cultural heritage", "business_culture": "business culture", "taboos": "taboos",
}

_CELL = {"type": "object", "additionalProperties": False, "required": ["text", "evidence"],
         "properties": {"text": {"type": "string"}, "evidence": {"type": "array", "items": {"type": "string"}}}}
SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["similarities", "rows", "context", "caveats", "insufficient"],
    "properties": {
        "similarities": {"type": "array", "items": _CELL},
        "rows": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["aspect", "a", "b"],
                                           "properties": {"aspect": {"type": "string"}, "a": _CELL, "b": _CELL}}},
        "context": {"type": "string"},
        "caveats": {"type": "array", "items": {"type": "string"}},
        "insufficient": {"type": "array", "items": {"type": "string"}},
    },
}

_SQL_COUNTRIES = "SELECT id, iso2, name_vi, name_en FROM countries WHERE iso2 = ANY(:isos)"

# Bản flagged / archived không được phục vụ; ưu tiên bản đã duyệt
_SQL_CACHED = """
SELECT cp.result, cp.status::text AS status, cp.country_a_id, u.display_name AS reviewer
FROM comparisons cp LEFT JOIN users u ON u.id = cp.reviewed_by
WHERE cp.topic = CAST(:topic AS category_code) AND cp.language = :lang
  AND ((cp.country_a_id = :a AND cp.country_b_id = :b) OR (cp.country_a_id = :b AND cp.country_b_id = :a))
  AND cp.status IN ('published', 'in_review', 'draft')
ORDER BY (cp.status = 'published') DESC, (cp.country_a_id = :a) DESC
LIMIT 1"""

_SQL_INSERT = """
INSERT INTO comparisons (country_a_id, country_b_id, topic, language, result, status, origin)
VALUES (:a, :b, CAST(:topic AS category_code), :lang, CAST(:result AS jsonb), 'draft', 'ai_generated')
ON CONFLICT (country_a_id, country_b_id, topic, language) DO NOTHING"""

_LABEL_TAG = re.compile(r"\s*\[c\d+\]")


@dataclasses.dataclass(frozen=True)
class _Country:
    id: int
    iso2: str
    name_vi: str
    name_en: str

    def name(self, lang: str) -> str:
        return self.name_en if lang == "en" else self.name_vi


def _clean_cell(cell: Any) -> dict[str, Any] | None:
    """Ô lấy từ DB: chỉ giữ ô có chữ và có nguồn (bản cũ / sửa tay thiếu nguồn vẫn hiện là null)."""
    if not isinstance(cell, dict) or not str(cell.get("text") or "").strip():
        return None
    ids = [int(i) for i in cell.get("sourceIds") or [] if isinstance(i, int | str) and str(i).isdigit()]
    return {"text": str(cell["text"]).strip(), "sourceIds": ids} if ids else None


def _swap(result: dict[str, Any]) -> dict[str, Any]:
    """Bản lưu theo chiều B–A → đổi cột để khớp chiều người dùng hỏi."""
    rows = [{**r, "a": r.get("b"), "b": r.get("a")} for r in result.get("rows") or []]
    return {**result, "rows": rows}


async def _response(conn: AsyncConnection, a: _Country, b: _Country, topic: str, result: dict[str, Any],
                    reviewed: bool, reviewer: str | None) -> dict[str, Any]:
    similarities = [c for c in map(_clean_cell, result.get("similarities") or []) if c]
    rows = [{"aspect": str(r.get("aspect") or ""), "a": _clean_cell(r.get("a")), "b": _clean_cell(r.get("b"))}
            for r in result.get("rows") or [] if isinstance(r, dict)]
    cited = {i for c in similarities for i in c["sourceIds"]}
    cited |= {i for r in rows for cell in (r["a"], r["b"]) if cell for i in cell["sourceIds"]}
    sources = await get_sources(conn, cited)
    known = {s["id"] for s in sources}
    # Nguồn đã bị xoá → ô đó không còn chỗ dựa
    for r in rows:
        for side in ("a", "b"):
            if r[side] and not set(r[side]["sourceIds"]) <= known:
                r[side] = None
    similarities = [c for c in similarities if set(c["sourceIds"]) <= known]
    return {"countryA": a.iso2, "countryB": b.iso2, "topic": topic, "reviewed": reviewed,
            "reviewedBy": reviewer if reviewed else None, "similarities": similarities, "rows": rows,
            "context": result.get("context") or None, "caveats": [str(c) for c in result.get("caveats") or []],
            "insufficient": [str(c) for c in result.get("insufficient") or []], "sources": sources}


def _evidence_block(country: _Country, group: str, evidence: list[Evidence]) -> str:
    lines = [f"[{e.label}] {e.title} — {e.publisher}: {e.text}" for e in evidence] or ["(không có bằng chứng)"]
    return f"NHÓM {group} — {country.name_vi} ({country.iso2}):\n" + "\n".join(lines)


def validate(raw: dict[str, Any], a: _Country, b: _Country, evidence: list[Evidence], lang: str) -> dict[str, Any]:
    """Đổi kết quả LLM (nhãn c#) thành bản lưu (sourceIds); ô không có bằng chứng hợp lệ → null (AC11.2).

    Ô của A chỉ nhận bằng chứng của A, ô của B chỉ nhận của B; điểm giống cần bằng chứng của cả hai nước.
    """
    by_label = {e.label: e for e in evidence if e.source_id is not None}

    def cell(c: Any, allowed: set[str]) -> dict[str, Any] | None:
        if not isinstance(c, dict):
            return None
        txt = _LABEL_TAG.sub("", str(c.get("text") or "")).strip()[:MAX_CELL_CHARS]
        labels = [lb for lb in dict.fromkeys(c.get("evidence") or []) if isinstance(lb, str)]
        if not txt or not labels or any(lb not in by_label or by_label[lb].country not in allowed for lb in labels):
            return None
        return {"text": txt, "sourceIds": list(dict.fromkeys(int(by_label[lb].source_id) for lb in labels))}

    def countries_of(c: Any) -> set[str | None]:
        return {by_label[lb].country for lb in (c.get("evidence") or []) if lb in by_label} if isinstance(c, dict) else set()

    both = {a.iso2, b.iso2}
    similarities = [c for s in raw.get("similarities") or [] if both <= countries_of(s) and (c := cell(s, both))]
    rows, insufficient = [], [str(x) for x in raw.get("insufficient") or [] if str(x).strip()]
    for r in (raw.get("rows") or [])[:MAX_ROWS]:
        if not isinstance(r, dict) or not str(r.get("aspect") or "").strip():
            continue
        aspect = str(r["aspect"]).strip()[:120]
        row = {"aspect": aspect, "a": cell(r.get("a"), {a.iso2}), "b": cell(r.get("b"), {b.iso2})}
        insufficient += [f"{aspect} ({c.name(lang)})" for c, side in ((a, "a"), (b, "b")) if row[side] is None]
        rows.append(row)
    return {"similarities": similarities, "rows": rows,
            "context": str(raw.get("context") or "").strip() or None,
            "caveats": [str(x) for x in raw.get("caveats") or [] if str(x).strip()],
            "insufficient": list(dict.fromkeys(insufficient))}


async def _load_countries(conn: AsyncConnection, iso_a: str, iso_b: str) -> tuple[_Country, _Country]:
    rows = {r.iso2.strip(): _Country(r.id, r.iso2.strip(), r.name_vi, r.name_en)
            for r in (await conn.execute(text(_SQL_COUNTRIES), {"isos": [iso_a, iso_b]})).all()}
    missing = [i for i in (iso_a, iso_b) if i not in rows]
    if missing:
        raise ProblemError(404, "Không tìm thấy quốc gia", f"Chưa có quốc gia mã {', '.join(missing)}.")
    return rows[iso_a], rows[iso_b]


async def compare(conn: AsyncConnection, llm: LLMAdapter, embedder: Embedder, local_ai: Reranker,
                  vstore: VectorSearch | None, iso_a: str, iso_b: str, topic: str, lang: str = "vi") -> dict[str, Any]:
    """Bản so sánh (DTO Comparison) cho (A, B, chủ đề, ngôn ngữ).

    Raises:
        ProblemError: 404 nếu quốc gia không có; 503 nếu cần sinh mới mà LLM không phản hồi.
    """
    a, b = await _load_countries(conn, iso_a, iso_b)
    params = {"a": a.id, "b": b.id, "topic": topic, "lang": lang}
    cached = (await conn.execute(text(_SQL_CACHED), params)).first()
    if cached is not None:
        result = cached.result if cached.country_a_id == a.id else _swap(cached.result)
        return await _response(conn, a, b, topic, result, cached.status == "published", cached.reviewer)

    evidence: list[Evidence] = []
    for c in (a, b):     # tìm riêng từng nước để nước có nhiều tài liệu không lấn át nước kia
        queries = [f"{CATEGORY_VI[topic]} ở {c.name_vi}", f"{CATEGORY_EN[topic]} {c.name_en}"]
        evidence += await retrieve(conn, embedder, local_ai, queries, [c.iso2], EVIDENCE_PER_COUNTRY, vstore)
    evidence = [dataclasses.replace(e, label=f"c{i}") for i, e in enumerate(evidence, start=1)]
    if not evidence:     # không có gì để so → không gọi LLM, không lưu nháp rỗng
        return await _response(conn, a, b, topic, {"rows": [], "insufficient": [
            f"{CATEGORY_VI[topic].capitalize()} ({a.name(lang)}, {b.name(lang)})"]}, False, None)

    language = "tiếng Anh" if lang == "en" else "tiếng Việt"
    user = (f"Chủ đề: {CATEGORY_VI[topic]}. Quốc gia A: {a.name_vi} ({a.iso2}). Quốc gia B: {b.name_vi} ({b.iso2}). "
            f"Viết bằng {language}.\n\nBẰNG CHỨNG:\n"
            + _evidence_block(a, "A", [e for e in evidence if e.country == a.iso2]) + "\n\n"
            + _evidence_block(b, "B", [e for e in evidence if e.country == b.iso2]))
    try:
        raw = await llm.complete_json([{"role": "system", "content": PROMPT}, {"role": "user", "content": user}],
                                      name="comparison", schema=SCHEMA)
    except LLMUnavailable as e:
        raise ProblemError(503, "Chưa so sánh được lúc này",
                           "Dịch vụ AI đang gián đoạn, bạn thử lại sau ít phút nhé.", "llm-unavailable") from e
    result = validate(raw, a, b, evidence, lang)
    await conn.execute(text(_SQL_INSERT), {**params, "result": json.dumps(result, ensure_ascii=False)})
    return await _response(conn, a, b, topic, result, False, None)

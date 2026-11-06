"""Lập chỉ mục RAG: chia đoạn + embedding → entry_chunks.

Ba loại đoạn (cột kind), mọi đoạn đều gắn nguồn để AI Guide trích dẫn:
- claim     : claim đã xuất bản của bài đã xuất bản (đã qua biên tập → độ tin cậy cao nhất)
- reference : tài liệu tham khảo worker thu thập (Wikipedia, trang du lịch chính thức…) — chưa qua biên tập
- heritage  : di sản UNESCO (tên, loại, năm ghi danh, mô tả)

Lưu trữ: văn bản + metadata ở PostgreSQL (entry_chunks, có chỉ mục từ khoá), embedding ở Qdrant (vector DB).
Chạy lại bao nhiêu lần cũng được: xoá đoạn của loại đang lập rồi tạo lại.
    python -m worker.cli index                 # embedding qua dịch vụ AI local (AI_LOCAL_URL) → Qdrant (QDRANT_URL)
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg

    from worker.core.vectors import VectorIndex

EmbedFn = Callable[[list[str]], list[list[float]]]
KINDS = ("claim", "reference", "heritage")
MAX_CHARS = 900
HERITAGE_TYPE_VI = {"tangible": "di sản vật thể", "intangible": "di sản văn hoá phi vật thể"}


@dataclass
class Chunk:
    """Một đoạn của chỉ mục RAG trước khi ghi: văn bản + metadata → entry_chunks, vector → Qdrant."""

    kind: str
    text: str
    language: str
    metadata: dict
    entry_id: int | None = None
    source_id: int | None = None
    source_document_id: int | None = None
    heritage_item_id: int | None = None
    chunk_index: int = 0
    claim_ids: list[int] = field(default_factory=list)


def split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Chia theo câu, mỗi phần ≤ max_chars (không cắt giữa câu, trừ câu quá dài)."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return [text] if text else []
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.!?…])\s+", text):
        while len(sent) > max_chars:                 # câu quá dài → cắt cứng
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(sent[:max_chars])
            sent = sent[max_chars:]
        if len(cur) + len(sent) + 1 > max_chars and cur:
            parts.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        parts.append(cur)
    return parts


def collect(conn: psycopg.Connection, kinds: Iterable[str] = KINDS) -> list[Chunk]:
    """Đọc nguồn của từng loại đoạn: claim đã xuất bản, tài liệu tham khảo, di sản UNESCO → danh sách Chunk."""
    chunks: list[Chunk] = []
    kinds = set(kinds)
    if "claim" in kinds:
        rows = conn.execute("""
            SELECT cl.id, cl.text, cl.language, cl.scope, cl.region, e.id, e.category::text, e.title_vi, c.iso2,
                   (SELECT cs.source_id FROM claim_sources cs WHERE cs.claim_id = cl.id ORDER BY cs.source_id LIMIT 1)
            FROM claims cl
            JOIN culture_entries e ON e.id = cl.entry_id AND e.status = 'published'
            JOIN countries c ON c.id = e.country_id
            WHERE cl.status = 'published'
            ORDER BY cl.id""").fetchall()
        for cid, text, lang, scope, region, eid, cat, title, iso, src in rows:
            chunks.append(Chunk("claim", text, lang or "vi", {
                "country": iso, "countries": [iso], "category": cat, "entry_id": eid, "title": title,
                "scope": scope, "region": region}, entry_id=eid, source_id=src, claim_ids=[cid]))
    if "reference" in kinds:
        rows = conn.execute("""
            SELECT d.id, d.title, d.section, d.body, d.url, d.language, d.category_guess::text, c.iso2, d.source_id, d.excerpt_only
            FROM source_documents d LEFT JOIN countries c ON c.id = d.country_id
            ORDER BY d.id""").fetchall()
        for did, title, section, body, url, lang, cat, iso, src, excerpt_only in rows:
            head = f"{title} — {section}: " if section and section != title else f"{title}: "
            for i, part in enumerate(split_text(body)):
                chunks.append(Chunk("reference", head + part, lang or "en", {
                    "country": iso, "countries": [iso] if iso else [], "category": cat, "title": f"{title} — {section}",
                    "url": url, "excerpt_only": bool(excerpt_only)},
                    source_id=src, source_document_id=did, chunk_index=i))
    if "heritage" in kinds:
        rows = conn.execute("""
            SELECT h.id, h.name, h.type::text, h.list_type, h.inscribed_year, h.raw_data->>'summary', h.source_id,
                   h.raw_data->>'url', COALESCE(array_agg(c.iso2 ORDER BY c.iso2) FILTER (WHERE c.iso2 IS NOT NULL), '{}')
            FROM heritage_items h
            LEFT JOIN heritage_item_countries hc ON hc.heritage_item_id = h.id
            LEFT JOIN countries c ON c.id = hc.country_id
            GROUP BY h.id ORDER BY h.id""").fetchall()
        for hid, name, htype, list_type, year, summary, src, url, isos in rows:
            isos = list(isos)
            year_txt = f", ghi danh năm {year}" if year else ""
            text = f"{name} — {HERITAGE_TYPE_VI.get(htype, 'di sản')} UNESCO ({list_type}{year_txt})."
            if summary:
                text += " " + re.sub(r"\s+", " ", summary).strip()
            chunks.append(Chunk("heritage", text[:MAX_CHARS * 2], "en", {
                "country": isos[0] if isos else None, "countries": isos, "category": "heritage",
                "title": name, "url": url, "heritage_type": htype},
                source_id=src, heritage_item_id=hid))
    return chunks


def index(conn: psycopg.Connection, embed: EmbedFn, kinds: Iterable[str] = KINDS, batch_size: int = 32,
          vectors: VectorIndex | None = None) -> dict[str, int]:
    """Xoá đoạn cũ của các loại được chọn rồi tạo lại: văn bản + metadata → PostgreSQL (entry_chunks),
    embedding → Qdrant (point id = entry_chunks.id). `vectors`: VectorIndex (mặc định đọc QDRANT_* từ môi trường)."""
    from worker.core.vectors import VectorIndex
    vectors = vectors or VectorIndex()
    kinds = tuple(kinds)
    chunks = collect(conn, kinds)
    embs: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        embs.extend(embed([c.text for c in chunks[i:i + batch_size]]))
    with conn.transaction():
        conn.execute("DELETE FROM entry_chunks WHERE kind = ANY(%s)", (list(kinds),))
        ids = []
        with conn.cursor() as cur:
            for c in chunks:
                cur.execute("""
                    INSERT INTO entry_chunks (kind, entry_id, source_id, source_document_id, heritage_item_id, chunk_index,
                                              claim_ids, chunk_text, language, metadata, token_count)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                            (c.kind, c.entry_id, c.source_id, c.source_document_id, c.heritage_item_id, c.chunk_index,
                             c.claim_ids or None, c.text, c.language, json.dumps(c.metadata, ensure_ascii=False), len(c.text.split())))
                ids.append(cur.fetchone()[0])
        # Qdrant lỗi → ngoại lệ → transaction PostgreSQL rollback (giữ chỉ mục cũ)
        vectors.delete_kinds(list(kinds))
        vectors.upsert(ids, embs, [{"kind": c.kind, "countries": c.metadata.get("countries") or [],
                                    "category": c.metadata.get("category"), "entry_id": c.entry_id} for c in chunks])
    return {k: sum(c.kind == k for c in chunks) for k in kinds}


def http_embedder(ai_local_url: str, timeout: float = 120.0) -> EmbedFn:
    """Embedding qua dịch vụ AI local (POST /v1/embed)."""
    import httpx

    def embed(texts: list[str]) -> list[list[float]]:
        r = httpx.post(f"{ai_local_url.rstrip('/')}/v1/embed", json={"texts": texts}, timeout=timeout)
        r.raise_for_status()
        return r.json()["vectors"]
    return embed

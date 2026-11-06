"""Truy xuất bằng chứng cho AI Guide: lọc quốc gia → tìm vector (Qdrant) + từ khoá (FTS không dấu ở PostgreSQL)
→ gộp RRF → rerank (dịch vụ AI local) → giữ đoạn vượt ngưỡng liên quan. Embedding/rerank chạy local, không gửi ra ngoài."""
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.local_ai import (
    LocalAIClient,
    LocalAIError,
    LocalAIUnavailable,
    get_local_ai,
)
from app.ai.text import words
from app.ai.vector_store import VectorSearch, VectorStoreUnavailable
from app.core.config import get_settings

# Từ hư / từ hỏi tiếng Việt (đã bỏ dấu) + vài từ tiếng Anh — bỏ khỏi truy vấn từ khoá
STOPWORDS = {"o", "gi", "la", "co", "khong", "nhu", "the", "nao", "cua", "va", "cac", "nhung", "can", "mot", "nay", "do", "thi", "ma", "de", "cho", "voi", "tai", "tu", "ve", "duoc", "bi", "rat", "nhieu", "it", "hay", "hoac", "neu", "khi", "vi", "sao", "lam", "bao", "gio", "dau", "ai", "minh", "ban", "toi", "chung", "ta", "nguoi", "ra", "vao", "len", "xuong", "da", "dang", "se", "nen", "phai", "muon", "biet", "hoi", "xin", "vui", "long", "giup", "ke", "nghe", "hai", "ba", "di", "hon", "nua", "cung", "con", "cai", "chiec", "nhe", "a", "u", "nhi", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "of", "on", "or", "that", "to", "was", "what", "which", "who", "why", "with", "how", "does"}


def keyword_query(query: str) -> str:
    """Truy vấn FTS dạng OR (to_tsquery) từ các từ có nghĩa — câu hỏi dài vẫn khớp đoạn chứa một phần từ khoá."""
    toks = [w for w in dict.fromkeys(words(query)) if w not in STOPWORDS and len(w) > 1 and w.isalnum()]
    return " | ".join(toks[:16]) or "zzzkhongcotukhoa"

log = logging.getLogger(__name__)


class Embedder(Protocol):
    """Sinh embedding cho câu hỏi (LocalAIClient ở production, FakeEmbedder trong test)."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Mỗi văn bản → vector 1024 chiều."""
        ...


class Reranker(Protocol):
    """Chấm lại độ liên quan (LocalAIClient ở production, FakeLocalAI trong test)."""

    async def rerank(self, query: str, documents: list[str], top_k: int | None = None) -> list[dict[str, float]]:
        """→ [{"index", "score"}]."""
        ...


def get_embedder() -> LocalAIClient:
    """FastAPI dependency: đối tượng có `async embed(texts) -> list[list[float]]` (1024 chiều). Test thay bằng FakeEmbedder."""
    return get_local_ai()


@dataclass
class Evidence:
    """Một đoạn bằng chứng đưa vào prompt (nhãn c#) và thành trích dẫn nếu câu trả lời dùng tới."""

    label: str            # c1, c2… — nhãn trong prompt và trong câu trả lời
    chunk_id: int
    kind: str             # claim | reference | heritage
    text: str
    country: str | None
    source_id: int | None
    title: str
    publisher: str
    url: str
    license: str
    score: float

    @property
    def verified(self) -> bool:
        """Chỉ claim (đã qua biên tập viên) là đã kiểm chứng; reference / heritage là tài liệu thô."""
        return self.kind == "claim"     # đã qua biên tập viên

    def citation(self) -> dict[str, Any]:
        """Dạng `Citation` của API (trích đoạn ≤ 300 ký tự)."""
        excerpt = self.text if len(self.text) <= 300 else self.text[:297].rsplit(" ", 1)[0] + "…"
        return {"id": self.label, "sourceId": self.source_id, "chunkId": self.chunk_id, "kind": self.kind,
                "title": self.title, "publisher": self.publisher, "url": self.url, "license": self.license,
                "excerpt": excerpt, "verified": self.verified}


# Tìm từ khoá (FTS không dấu) ở PostgreSQL — vector ở Qdrant (app/ai/vector_store.py), gộp RRF bằng Python.
_SQL_FTS = """
SELECT id FROM entry_chunks, to_tsquery('ca_simple', :q) q
WHERE tsv @@ q AND (:any_country OR metadata->>'country' = ANY(:countries) OR metadata->'countries' ?| :countries)
ORDER BY ts_rank(tsv, q) DESC LIMIT :pool
"""

_SQL_ROWS = """
SELECT ch.id, ch.kind, ch.chunk_text, COALESCE(ch.metadata->>'country', ch.metadata->'countries'->>0), ch.source_id,
       COALESCE(ch.metadata->>'title', ''), COALESCE(ch.metadata->>'url', s.source_url, ''),
       COALESCE(s.title, ''), COALESCE(s.publisher, ''), COALESCE(s.license, ''), COALESCE(s.source_url, ''), ch.claim_ids
FROM entry_chunks ch LEFT JOIN sources s ON s.id = ch.source_id
WHERE ch.id = ANY(:ids)
"""


async def _claim_source(conn: AsyncConnection, claim_ids: list[int] | None) -> tuple[str, str] | None:
    """Với claim: lấy đoạn bằng chứng gốc (evidence_excerpt) + locator của nguồn đầu tiên."""
    if not claim_ids:
        return None
    row = (await conn.execute(text("""SELECT evidence_excerpt, COALESCE(locator, '') FROM claim_sources
                                       WHERE claim_id = :c ORDER BY source_id LIMIT 1"""), {"c": claim_ids[0]})).first()
    return (row[0], row[1]) if row else None


def interleave[T](items: list[T], country_of: Callable[[T], str | None], countries: Sequence[str]) -> list[T]:
    """Câu hỏi nhiều nước: xếp xen kẽ theo quốc gia (giữ thứ tự điểm trong từng nước) để nước nào cũng có bằng chứng."""
    if len(countries) <= 1:
        return items
    buckets: dict[str, list[T]] = {}
    for it in items:
        buckets.setdefault(country_of(it) or "", []).append(it)
    order = [c for c in countries if c in buckets] + [c for c in buckets if c not in countries]
    out: list[T] = []
    while any(buckets[c] for c in order):
        out += [buckets[c].pop(0) for c in order if buckets[c]]
    return out


def merge_evidence(a: list[Evidence], b: list[Evidence], countries: list[str], k: int) -> list[Evidence]:
    """Gộp hai lần truy xuất: mỗi đoạn giữ điểm cao nhất, sắp lại, xen kẽ theo nước, đánh nhãn lại c1…ck."""
    best: dict[int, Evidence] = {}
    for e in a + b:
        if e.chunk_id not in best or e.score > best[e.chunk_id].score:
            best[e.chunk_id] = e
    items = interleave(sorted(best.values(), key=lambda e: -e.score), lambda e: e.country, countries)[:k]
    for n, e in enumerate(items, start=1):
        e.label = f"c{n}"
    return items


def is_strong(evidence: list[Evidence], countries: list[str], min_score: float) -> bool:
    """Bằng chứng đủ mạnh để bỏ qua bước viết lại truy vấn: điểm cao nhất ≥ ngưỡng và nước nào được hỏi cũng có nguồn."""
    if not evidence or max(e.score for e in evidence) < min_score:
        return False
    return all(any(e.country == c for e in evidence) for c in countries) if len(countries) > 1 else True


async def retrieve(conn: AsyncConnection, embedder: Embedder, local_ai: Reranker, queries: list[str] | str,
                   countries: list[str], k: int = 6, vstore: VectorSearch | None = None) -> list[Evidence]:
    """`queries`: câu hỏi gốc + các truy vấn viết lại (query_rewriter). `countries`: lọc theo quốc gia (rỗng = mọi nước).
    `vstore`: Qdrant (VectorStore). Embedding hoặc Qdrant lỗi → chỉ tìm theo từ khoá, chat vẫn chạy (AC06.7)."""
    s = get_settings()
    queries = [q for q in dict.fromkeys([queries] if isinstance(queries, str) else queries) if q and q.strip()][:4]
    if not queries:
        return []
    vecs: list[list[float]] | None = None
    if vstore is not None:
        try:
            vecs = await embedder.embed(queries)
        except (LocalAIUnavailable, LocalAIError) as e:
            log.warning("embedding không khả dụng (%s) — chỉ tìm theo từ khoá", type(e).__name__)

    # Câu hỏi nhiều nước → tìm riêng cho từng nước (nước có nhiều tài liệu không lấn át nước kia)
    scopes = [[c] for c in countries] if len(countries) > 1 else [countries]
    pool = max(8, s.rag_pool // len(scopes))
    fused: dict[int, list] = {}          # chunk id → [điểm RRF, cosine, có khớp từ khoá, truy vấn đã tìm ra]
    for qi, q in enumerate(queries):
        for scope in scopes:
            vec_hits: list[tuple[int, float]] = []
            if vecs is not None:
                try:
                    vec_hits = await vstore.search(vecs[qi], scope, pool)
                except VectorStoreUnavailable as e:
                    log.warning("Qdrant không khả dụng (%s) — chỉ tìm theo từ khoá", e)
                    vecs = None
            fts_ids = [r[0] for r in (await conn.execute(text(_SQL_FTS), {
                "q": keyword_query(q), "pool": pool, "countries": scope or [""], "any_country": not scope})).all()]
            per_query: dict[int, list] = {}
            for rank, (cid, cos) in enumerate(vec_hits, start=1):
                per_query[cid] = [1.0 / (60 + rank), cos, False, qi]
            for rank, cid in enumerate(fts_ids, start=1):
                e = per_query.setdefault(cid, [0.0, 0.0, False, qi])
                e[0] += 1.0 / (60 + rank)
                e[2] = True
            for cid, e in per_query.items():
                if cid not in fused or e[0] > fused[cid][0]:
                    fused[cid] = e
    if not fused:
        return []
    ranked_ids = sorted(fused, key=lambda c: -fused[c][0])[: s.rerank_max_candidates]
    rows = {r[0]: r for r in (await conn.execute(text(_SQL_ROWS), {"ids": ranked_ids})).all()}
    # hàng theo định dạng cũ: (…11 cột thông tin…, rrf, cos, kw, claim_ids)
    cand = {cid: (fused[cid][0], (*rows[cid][:11], fused[cid][0], fused[cid][1], fused[cid][2], rows[cid][11]), fused[cid][3])
            for cid in ranked_ids if cid in rows}
    if not cand:
        return []
    top = sorted(cand.values(), key=lambda x: -x[0])[: s.rerank_max_candidates]

    scores: dict[int, float] | None = {}
    try:   # chấm mỗi ứng viên theo đúng truy vấn đã tìm ra nó; cắt ngắn đoạn để rerank nhanh
        for qi in sorted({c[2] for c in top}):
            group = [c[1] for c in top if c[2] == qi]
            ranked = await local_ai.rerank(queries[qi], [r[2][: s.rerank_doc_chars] for r in group], None)
            for item in ranked:
                scores[group[item["index"]][0]] = float(item["score"])
    except (LocalAIUnavailable, LocalAIError, AttributeError) as e:     # không có rerank → dùng ngưỡng cosine
        log.warning("rerank không khả dụng (%s) — dùng ngưỡng cosine", type(e).__name__)
        scores = None

    picked = []
    for rrf, r, _ in top:
        relevant = scores.get(r[0], 0.0) >= s.rag_min_rerank if scores is not None else (r[12] >= s.rag_min_cosine or r[13])
        if relevant:
            picked.append((scores[r[0]] if scores is not None else rrf, r))
    picked.sort(key=lambda x: x[0], reverse=True)
    picked = interleave(picked, lambda p: p[1][3], countries)

    out: list[Evidence] = []
    for n, (score, r) in enumerate(picked[:k], start=1):
        cid, kind, chunk_text, country, src, meta_title, url, s_title, publisher, lic, s_url = r[:11]
        title = meta_title or s_title
        if kind == "claim":
            cs = await _claim_source(conn, r[14])
            title = f"{meta_title} · {s_title}" if s_title else meta_title
            url = s_url or url
            if cs:      # trích nguyên văn bằng chứng của nguồn thay vì câu claim
                chunk_text = f"{chunk_text} (Nguồn: “{cs[0]}”{' ' + cs[1] if cs[1] else ''})"
        out.append(Evidence(f"c{n}", cid, kind, chunk_text, country, src, title, publisher, url, lic, round(score, 4)))
    return out

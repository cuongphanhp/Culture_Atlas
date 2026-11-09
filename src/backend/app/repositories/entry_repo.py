"""culture_entries, claims, claim_sources, sources: bài viết đã xuất bản, claim kèm bằng chứng, chi tiết nguồn.

Người dùng cuối chỉ thấy nội dung `published` (BR02); claim `unverified` không bao giờ hiện (AC03.3).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.text import words
from app.core.errors import ProblemError

_SQL_ENTRIES = """
SELECT id, category::text AS category, title_vi, title_en, summary, updated_at::date AS updated_at
FROM culture_entries
WHERE country_id = :cid AND status = 'published' AND (CAST(:category AS text) IS NULL OR category::text = :category)
ORDER BY category, title_vi, id"""

_SQL_ENTRY = """
SELECT e.id, e.category::text AS category, e.title_vi, e.title_en, e.summary, e.updated_at::date AS updated_at,
       c.iso2, e.status::text AS status, e.version
FROM culture_entries e JOIN countries c ON c.id = e.country_id
WHERE e.id = :id AND e.status = 'published'"""

_SQL_CLAIMS = """
SELECT cl.id, cl.text, cl.scope::text AS scope, cl.region, cl.period, cl.confidence::text AS confidence,
       json_agg(json_build_object('sourceId', cs.source_id, 'evidenceExcerpt', cs.evidence_excerpt, 'locator', cs.locator)
                ORDER BY cs.source_id) AS sources
FROM claims cl JOIN claim_sources cs ON cs.claim_id = cl.id
WHERE cl.entry_id = :id AND cl.status = 'published' AND cl.confidence <> 'unverified'
GROUP BY cl.id
ORDER BY cl.position, cl.id"""

_SQL_SOURCES = """
SELECT id, title, publisher, source_url, source_type::text AS source_type, license,
       reliability_tier::text AS reliability_tier, retrieved_at
FROM sources WHERE id = ANY(:ids) ORDER BY id"""


def _title(r: Any, lang: str) -> str:
    return (r.title_en if lang == "en" and r.title_en else r.title_vi)


def _entry_summary(r: Any, lang: str) -> dict[str, Any]:
    return {"id": r.id, "category": r.category, "title": _title(r, lang), "summary": r.summary, "updatedAt": r.updated_at}


def source_dict(r: Any) -> dict[str, Any]:
    """Một hàng `sources` → DTO Source của API."""
    return {"id": r.id, "title": r.title, "publisher": r.publisher, "url": r.source_url, "sourceType": r.source_type,
            "license": r.license, "reliabilityTier": r.reliability_tier, "retrievedAt": r.retrieved_at}


async def list_entries(conn: AsyncConnection, country_id: int, category: str | None = None,
                       lang: str = "vi") -> list[dict[str, Any]]:
    """Bài viết đã xuất bản của một quốc gia, lọc theo danh mục nếu có (AC02.2)."""
    rows = (await conn.execute(text(_SQL_ENTRIES), {"cid": country_id, "category": category})).all()
    return [_entry_summary(r, lang) for r in rows]


async def get_sources(conn: AsyncConnection, ids: Iterable[int]) -> list[dict[str, Any]]:
    """Các nguồn theo id (bỏ qua id không tồn tại), sắp theo id."""
    wanted = sorted({int(i) for i in ids})
    if not wanted:
        return []
    return [source_dict(r) for r in (await conn.execute(text(_SQL_SOURCES), {"ids": wanted})).all()]


async def get_source(conn: AsyncConnection, source_id: int) -> dict[str, Any]:
    """Chi tiết một nguồn (AC03.2).

    Raises:
        ProblemError: 404 nếu không có nguồn này.
    """
    found = await get_sources(conn, [source_id])
    if not found:
        raise ProblemError(404, "Không tìm thấy nguồn")
    return found[0]


async def get_entry(conn: AsyncConnection, entry_id: int, lang: str = "vi") -> dict[str, Any]:
    """Bài viết đã xuất bản + claim đã kiểm chứng (kèm bằng chứng) + danh sách nguồn được trích.

    Raises:
        ProblemError: 404 nếu bài không tồn tại hoặc chưa xuất bản (không tiết lộ bài nháp).
    """
    r = (await conn.execute(text(_SQL_ENTRY), {"id": entry_id})).first()
    if r is None:
        raise ProblemError(404, "Không tìm thấy bài viết")
    claims = [{"id": c.id, "text": c.text, "scope": c.scope, "region": c.region, "period": c.period,
               "confidence": c.confidence, "sources": c.sources}
              for c in (await conn.execute(text(_SQL_CLAIMS), {"id": entry_id})).all()]
    sources = await get_sources(conn, (s["sourceId"] for c in claims for s in c["sources"]))
    return {**_entry_summary(r, lang), "countryIso": r.iso2, "status": r.status, "version": r.version,
            "claims": claims, "sources": sources}


# Chủ đề xuyên quốc gia = thẻ kind 'theme' gắn vào bài đã xuất bản (F1.7)
_SQL_THEMES = """
SELECT t.name, count(DISTINCT e.country_id)::int AS country_count
FROM tags t
JOIN entry_tags et ON et.tag_id = t.id
JOIN culture_entries e ON e.id = et.entry_id AND e.status = 'published'
WHERE t.kind = 'theme'
GROUP BY t.id
ORDER BY country_count DESC, t.name"""

# Lễ hội theo tháng = bài danh mục festivals gắn thẻ kind 'month', tên thẻ "1".."12" (F1.8). `period` mô tả thời điểm.
_SQL_FESTIVALS = """
SELECT DISTINCT e.id, e.title_vi, e.title_en, c.iso2, e.period
FROM culture_entries e
JOIN countries c ON c.id = e.country_id
JOIN entry_tags et ON et.entry_id = e.id
JOIN tags t ON t.id = et.tag_id AND t.kind = 'month' AND t.name = :month
WHERE e.category = 'festivals' AND e.status = 'published'
ORDER BY c.iso2, e.title_vi"""


async def list_themes(conn: AsyncConnection) -> list[dict[str, Any]]:
    """Chủ đề xuyên quốc gia có ít nhất một bài đã xuất bản, nhiều quốc gia nhất đứng đầu."""
    rows = (await conn.execute(text(_SQL_THEMES))).all()
    return [{"slug": "-".join(words(r.name)), "title": r.name, "countryCount": r.country_count} for r in rows]


async def list_festivals(conn: AsyncConnection, month: int, lang: str = "vi") -> list[dict[str, Any]]:
    """Lễ hội đã xuất bản diễn ra trong `month` (1–12)."""
    rows = (await conn.execute(text(_SQL_FESTIVALS), {"month": str(month)})).all()
    return [{"entryId": r.id, "name": _title(r, lang), "country": r.iso2, "dateText": r.period} for r in rows]

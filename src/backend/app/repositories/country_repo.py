"""Truy vấn countries + v_coverage: danh sách quốc gia có độ phủ, hồ sơ quốc gia (danh mục, điều cần biết)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import ProblemError

# Độ phủ = % trong 12 danh mục đã có ít nhất một claim xuất bản (v_coverage)
_SQL_LIST = """
SELECT c.id, c.iso2, c.name_vi, c.name_en, c.region, c.is_featured,
       round(100.0 * count(*) FILTER (WHERE v.published_claims > 0) / count(*))::int AS coverage
FROM countries c JOIN v_coverage v ON v.iso2 = c.iso2
WHERE (CAST(:region AS text) IS NULL OR c.region = :region) AND (CAST(:iso AS text) IS NULL OR c.iso2 = :iso)
GROUP BY c.id
ORDER BY c.name_vi"""

_SQL_CATEGORIES = """
SELECT cat.code::text AS code, count(e.id)::int AS entry_count
FROM unnest(enum_range(NULL::category_code)) WITH ORDINALITY AS cat(code, ord)
LEFT JOIN culture_entries e ON e.category = cat.code AND e.country_id = :cid AND e.status = 'published'
GROUP BY cat.code, cat.ord
ORDER BY cat.ord"""

# Ưu tiên claim đã kiểm chứng và phổ biến; claim unverified không bao giờ hiện (AC03.3)
_SQL_TIPS = """
SELECT cl.text, array_agg(cs.source_id ORDER BY cs.source_id) AS source_ids
FROM claims cl
JOIN culture_entries e ON e.id = cl.entry_id
JOIN claim_sources cs ON cs.claim_id = cl.id
WHERE e.country_id = :cid AND e.status = 'published' AND cl.status = 'published' AND cl.confidence <> 'unverified'
GROUP BY cl.id, e.id
ORDER BY (cl.confidence = 'verified') DESC, (cl.scope = 'common_practice') DESC, e.id, cl.position
LIMIT 5"""


def flag(iso2: str) -> str:
    """Emoji cờ từ mã ISO alpha-2 (hai ký tự "regional indicator")."""
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in iso2.upper())


def _summary(r: Any, lang: str) -> dict[str, Any]:
    return {"iso2": r.iso2, "name": r.name_en if lang == "en" else r.name_vi, "region": r.region,
            "flag": flag(r.iso2), "coverage": r.coverage, "featured": r.is_featured}


async def list_countries(conn: AsyncConnection, region: str | None = None, lang: str = "vi") -> list[dict[str, Any]]:
    """Mọi quốc gia (lọc theo `region` nếu có) kèm độ phủ 0–100, sắp theo tên tiếng Việt."""
    rows = (await conn.execute(text(_SQL_LIST), {"region": region, "iso": None})).all()
    return [_summary(r, lang) for r in rows]


async def country_id(conn: AsyncConnection, iso: str) -> int:
    """Id của quốc gia theo ISO2 (không phân biệt hoa thường).

    Raises:
        ProblemError: 404 nếu không có quốc gia này.
    """
    cid = (await conn.execute(text("SELECT id FROM countries WHERE iso2 = :iso"), {"iso": iso.upper()})).scalar()
    if cid is None:
        raise ProblemError(404, "Không tìm thấy quốc gia", f"Chưa có quốc gia mã {iso.upper()}.")
    return int(cid)


async def get_profile(conn: AsyncConnection, iso: str, lang: str = "vi") -> dict[str, Any]:
    """Hồ sơ quốc gia: thông tin nền, số bài theo 12 danh mục, tối đa 5 điều cần biết có nguồn.

    Raises:
        ProblemError: 404 nếu không có quốc gia này.
    """
    rows = (await conn.execute(text(_SQL_LIST), {"region": None, "iso": iso.upper()})).all()
    if not rows:
        raise ProblemError(404, "Không tìm thấy quốc gia", f"Chưa có quốc gia mã {iso.upper()}.")
    r = rows[0]
    info = (await conn.execute(text(
        "SELECT capital, languages, currencies, COALESCE(neighbors, '{}') AS neighbors FROM countries WHERE id = :id"),
        {"id": r.id})).one()
    cats = (await conn.execute(text(_SQL_CATEGORIES), {"cid": r.id})).all()
    tips = (await conn.execute(text(_SQL_TIPS), {"cid": r.id})).all()
    return {**_summary(r, lang), "nameEn": r.name_en, "capital": info.capital, "languages": info.languages or [],
            "currencies": info.currencies or [], "neighbors": [n.strip() for n in info.neighbors],
            "categories": [{"code": c.code, "entryCount": c.entry_count} for c in cats],
            "firstTimeTips": [{"text": t.text, "sourceIds": list(t.source_ids)} for t in tips]}

"""heritage_items: di sản UNESCO theo quốc gia / loại, kèm ghi công theo giấy phép của nguồn (AC04.1, AC04.2)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

_SQL = """
SELECT h.id, h.unesco_id, h.name, h.type::text AS type, h.list_type, h.inscribed_year,
       h.lat::float AS lat, h.lng::float AS lng, s.publisher, s.license,
       ARRAY(SELECT c.iso2::text FROM heritage_item_countries hc JOIN countries c ON c.id = hc.country_id
             WHERE hc.heritage_item_id = h.id ORDER BY c.iso2) AS countries
FROM heritage_items h LEFT JOIN sources s ON s.id = h.source_id
WHERE (CAST(:country AS text) IS NULL OR EXISTS (
         SELECT 1 FROM heritage_item_countries hc JOIN countries c ON c.id = hc.country_id
         WHERE hc.heritage_item_id = h.id AND c.iso2 = :country))
  AND (CAST(:type AS text) IS NULL OR h.type::text = :type)
ORDER BY h.inscribed_year NULLS LAST, h.id"""

# Dữ liệu UNESCO DataHub dùng CC BY-SA 4.0 — ghi công mặc định khi bản ghi chưa gắn nguồn
DEFAULT_ATTRIBUTION = "UNESCO — CC BY-SA 4.0"


async def list_heritage(conn: AsyncConnection, country: str | None = None,
                        kind: str | None = None) -> list[dict[str, Any]]:
    """Di sản (lọc theo ISO2 `country` và loại `kind` = tangible | intangible), sắp theo năm ghi danh."""
    rows = (await conn.execute(text(_SQL), {"country": country.upper() if country else None, "type": kind})).all()
    return [{"id": r.id, "unescoId": r.unesco_id, "name": r.name, "type": r.type, "listType": r.list_type,
             "inscribedYear": r.inscribed_year, "countries": list(r.countries), "lat": r.lat, "lng": r.lng,
             "attribution": f"{r.publisher} — {r.license}" if r.publisher else DEFAULT_ATTRIBUTION}
            for r in rows]

"""Tìm kiếm nội dung (AC05): quốc gia, bài viết đã xuất bản, di sản UNESCO, chủ đề — gõ không dấu vẫn tìm được.

Dùng full-text PostgreSQL cấu hình `ca_simple` (simple + unaccent), tính trên dữ liệu gốc mỗi lần tìm: kho MVP nhỏ
nên vẫn dưới 500 ms (AC05.2) mà không cần cột chỉ mục riêng. Mọi từ trong câu tìm đều phải khớp (AND).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.text import words

_SQL_SEARCH = """
WITH q AS (SELECT plainto_tsquery('ca_simple', :q) AS tsq),
hits AS (
  SELECT 'country' AS kind, c.iso2::text AS id, c.name_vi AS title, c.region AS snippet, c.iso2::text AS country_iso,
         0 AS prio, ts_rank(d.doc, q.tsq) AS rank
  FROM countries c CROSS JOIN q
  CROSS JOIN LATERAL (SELECT to_tsvector('ca_simple', c.name_vi || ' ' || c.name_en) AS doc) d
  WHERE d.doc @@ q.tsq AND CAST(:category AS text) IS NULL
    AND (CAST(:country AS text) IS NULL OR c.iso2 = :country)

  UNION ALL
  SELECT 'entry', e.id::text, e.title_vi, e.summary, c.iso2::text, 1, ts_rank(d.doc, q.tsq)
  FROM culture_entries e JOIN countries c ON c.id = e.country_id CROSS JOIN q
  CROSS JOIN LATERAL (SELECT
      setweight(to_tsvector('ca_simple', e.title_vi || ' ' || coalesce(e.title_en, '')), 'A')
   || setweight(to_tsvector('ca_simple', coalesce(e.summary, '') || ' ' || c.name_vi || ' ' || c.name_en), 'B')
   || setweight(to_tsvector('ca_simple', coalesce(e.content, '') || ' ' || coalesce((
          SELECT string_agg(cl.text, ' ') FROM claims cl
          WHERE cl.entry_id = e.id AND cl.status = 'published' AND cl.confidence <> 'unverified'), '')), 'C') AS doc) d
  WHERE e.status = 'published' AND d.doc @@ q.tsq
    AND (CAST(:country AS text) IS NULL OR c.iso2 = :country)
    AND (CAST(:category AS text) IS NULL OR e.category::text = :category)

  UNION ALL
  SELECT 'heritage', h.id::text, h.name, h.list_type, min(c.iso2)::text, 2, ts_rank(d.doc, q.tsq)
  FROM heritage_items h
  JOIN heritage_item_countries hc ON hc.heritage_item_id = h.id JOIN countries c ON c.id = hc.country_id
  CROSS JOIN q
  CROSS JOIN LATERAL (SELECT to_tsvector('ca_simple', h.name) AS doc) d
  WHERE d.doc @@ q.tsq AND CAST(:category AS text) IS NULL
    AND (CAST(:country AS text) IS NULL OR c.iso2 = :country)
  GROUP BY h.id, d.doc, q.tsq

  UNION ALL
  SELECT 'theme', t.name, t.name, NULL, NULL, 3, ts_rank(d.doc, q.tsq)
  FROM tags t CROSS JOIN q
  CROSS JOIN LATERAL (SELECT to_tsvector('ca_simple', t.name) AS doc) d
  WHERE t.kind = 'theme' AND d.doc @@ q.tsq AND CAST(:category AS text) IS NULL AND CAST(:country AS text) IS NULL
    AND EXISTS (SELECT 1 FROM entry_tags et JOIN culture_entries e ON e.id = et.entry_id
                WHERE et.tag_id = t.id AND e.status = 'published')
)
SELECT kind, id, title, snippet, country_iso, count(*) OVER ()::int AS total
FROM hits
ORDER BY prio, rank DESC, title
LIMIT :size OFFSET :offset"""


async def search(conn: AsyncConnection, q: str, country: str | None = None, category: str | None = None,
                 page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Tìm theo `q` (không phân biệt dấu); lọc quốc gia / danh mục nếu có. Có `category` → chỉ trả bài viết.

    Thứ tự: quốc gia → bài viết → di sản → chủ đề; trong mỗi loại theo độ khớp.
    """
    rows = (await conn.execute(text(_SQL_SEARCH), {
        "q": q, "country": country.upper() if country else None, "category": category,
        "size": page_size, "offset": (page - 1) * page_size})).all()
    items = [{"kind": r.kind, "id": "-".join(words(r.id)) if r.kind == "theme" else r.id, "title": r.title,
              "snippet": r.snippet, "countryIso": r.country_iso} for r in rows]
    total = rows[0].total if rows else 0
    if not rows and page > 1:   # trang vượt quá → vẫn báo đúng tổng số kết quả
        total = (await search(conn, q, country, category, 1, 1))["total"]
    return {"total": total, "page": page, "items": items}

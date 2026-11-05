"""Nạp dữ liệu đã tổng hợp vào PostgreSQL (upsert, chạy lại không tạo trùng). Bảng: xem src/database/culture_atlas.sql."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import psycopg

SOURCE_META = {
    "unesco_whc": ("UNESCO World Heritage List (DataHub whc001)", "UNESCO", "https://data.unesco.org/explore/dataset/whc001/", "api_dataset", "CC BY-SA 4.0", "official"),
    "unesco_ich": ("UNESCO Intangible Heritage Lists (DataHub ich001)", "UNESCO", "https://data.unesco.org/explore/dataset/ich001/", "api_dataset", "CC BY-SA 4.0", "official"),
    "smithsonian": ("Smithsonian Open Access", "Smithsonian Institution", "https://www.si.edu/openaccess", "museum", "CC0", "museum"),
    "europeana": ("Europeana Search API", "Europeana Foundation", "https://www.europeana.eu", "museum", "Per record", "museum"),
    "wikimedia_commons": ("Wikimedia Commons", "Wikimedia Foundation", "https://commons.wikimedia.org", "encyclopedia", "Per file", "community"),
    "wikipedia": ("Wikipedia", "Wikimedia Foundation", "https://en.wikipedia.org", "encyclopedia", "CC BY-SA 4.0", "community"),
    "official_sites": ("Official tourism sites", "Various national tourism organizations", "https://www.japan.travel", "official_site", "Excerpts only", "official"),
    "scale": ("SCALE Cultural Data", "Google Research", "https://github.com/google-research-datasets/SCALE-Cultural-Data", "academic", "Unspecified — reference only", "academic"),
}


def _load(p: Path) -> list[dict]:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _source_id(cur, key: str) -> int:
    title, pub, url, stype, lic, tier = SOURCE_META[key]
    cur.execute("""INSERT INTO sources (title, publisher, source_url, source_type, license, reliability_tier, retrieved_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (source_url) DO UPDATE SET retrieved_at = EXCLUDED.retrieved_at RETURNING id""",
                (title, pub, url, stype, lic, tier, date.today()))
    return cur.fetchone()[0]


def load(data_dir: Path, dsn: str) -> dict[str, int]:
    agg = data_dir / "aggregated"
    counts = {"countries": 0, "heritage": 0, "media": 0, "documents": 0, "runs": 0}
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        for c in _load(agg / "countries.json"):
            cur.execute("""UPDATE countries SET name_en = %s, capital = COALESCE(%s, capital), languages = %s, currencies = %s,
                             neighbors = %s, iso3 = COALESCE(%s, iso3), raw_data = %s, updated_at = now() WHERE iso2 = %s""",
                        (c["name_en"], c.get("capital"), json.dumps(c.get("languages", [])), json.dumps(c.get("currencies", [])),
                         c.get("neighbors") or None, c.get("iso3"), json.dumps(c, ensure_ascii=False), c["iso2"]))
            counts["countries"] += cur.rowcount
        cur.execute("SELECT iso2, id FROM countries")
        country_id = dict(cur.fetchall())

        src_ids = {k: _source_id(cur, k) for k in SOURCE_META}
        for h in _load(agg / "heritage.json"):
            src = h["provenance"]["source_name"]
            cur.execute("""INSERT INTO heritage_items (unesco_id, name, type, list_type, inscribed_year, criteria, lat, lng, source_id, raw_data)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (unesco_id) DO UPDATE SET name = EXCLUDED.name, list_type = EXCLUDED.list_type, raw_data = EXCLUDED.raw_data
                           RETURNING id""",
                        (h["unesco_id"], h["name"][:500], h["type"], h["list_type"][:120], h.get("inscribed_year"), h.get("criteria"),
                         h.get("lat"), h.get("lng"), src_ids[src], json.dumps(h, ensure_ascii=False)))
            hid = cur.fetchone()[0]
            for iso in h["countries"]:
                if iso in country_id:
                    cur.execute("INSERT INTO heritage_item_countries VALUES (%s,%s) ON CONFLICT DO NOTHING", (hid, country_id[iso]))
            counts["heritage"] += 1

        for m in _load(agg / "media.json"):
            src = m["provenance"]["source_name"]
            cur.execute("""INSERT INTO media_assets (source_id, url, stored_url, author, license, attribution_text, verified)
                           SELECT %s,%s,%s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM media_assets WHERE url = %s)""",
                        (src_ids[src], m["url"] or m["image_url"], m.get("local_path") if m.get("verified") else None,
                         (m.get("author") or "")[:255], m["license"][:120], m["attribution_text"], m.get("verified", False), m["url"]))
            counts["media"] += cur.rowcount

        for d in _load(agg / "documents.json"):
            src = d["provenance"]["source_name"]
            cur.execute("""INSERT INTO source_documents (country_id, source_id, title, section, body, url, language, category_guess, excerpt_only)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (url, section) DO UPDATE SET body = EXCLUDED.body, retrieved_at = now()""",
                        (country_id.get(d["country"]), src_ids[src], d["title"][:500], d["section"][:255], d["text"],
                         d["provenance"]["source_url"], d.get("language", "en"), d.get("category_guess"), d.get("excerpt_only", False)))
            counts["documents"] += 1

        for p in sorted((data_dir / "runs").glob("*.json")):
            r = json.loads(p.read_text(encoding="utf-8"))
            cur.execute("""INSERT INTO ingestion_runs (source_name, status, started_at, finished_at, records_in, records_changed, errors)
                           SELECT %s,%s,%s,%s,%s,%s,%s WHERE NOT EXISTS (
                             SELECT 1 FROM ingestion_runs WHERE source_name = %s AND started_at = %s)""",
                        (r["source_name"], "failed" if r["status"] == "failed" else "succeeded", r["started_at"], r["finished_at"],
                         r["records_in"], r["records_changed"], json.dumps(r.get("errors", []) + r.get("skipped", []), ensure_ascii=False),
                         r["source_name"], r["started_at"]))
            counts["runs"] += cur.rowcount
        conn.commit()
    return counts

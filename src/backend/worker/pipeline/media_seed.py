"""Nạp bộ ảnh tuyển chọn của giao diện (src/media-seed) lên object storage + ghi metadata vào media_assets.

    python -m worker.cli seed-media ../media-seed           # Cách A
    docker compose run --rm -v ./src/media-seed:/seed:ro worker python -m worker.cli seed-media /seed

Cấu trúc thư mục:
    culture/credits.json + *.jpg   ảnh Wikimedia Commons (tác giả, giấy phép, trang nguồn)  → key photos/<file>
    objects/credits.json + *.jpg   ảnh hiện vật Smithsonian Open Access (CC0)               → key objects/<file>
Frontend dùng URL /media/photos/<file>, /media/objects/<file>. Chạy lại không tạo trùng (khoá theo URL nguồn).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import psycopg

from worker.core.objectstore import ObjectStore

COLLECTIONS = {
    # thư mục: (tiền tố key, nguồn trong bảng sources)
    "culture": ("photos", ("Wikimedia Commons", "Wikimedia Foundation", "https://commons.wikimedia.org", "encyclopedia", "Per file", "community")),
    "objects": ("objects", ("Smithsonian Open Access", "Smithsonian Institution", "https://www.si.edu/openaccess", "museum", "CC0", "museum")),
}


def _source_id(cur: psycopg.Cursor, meta: tuple[str, ...]) -> int:
    """Upsert nguồn của bộ ảnh → id."""
    title, pub, url, stype, lic, tier = meta
    cur.execute("""INSERT INTO sources (title, publisher, source_url, source_type, license, reliability_tier, retrieved_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (source_url) DO UPDATE SET title = EXCLUDED.title RETURNING id""",
                (title, pub, url, stype, lic, tier, date.today()))
    return cur.fetchone()[0]


def seed(root: Path, dsn: str, store: ObjectStore) -> dict[str, int]:
    """Ảnh tuyển chọn (src/media-seed/{culture,objects} + credits.json) → object storage + media_assets. Chạy lại không tạo
    trùng.
    """
    counts = {"uploaded": 0, "rows": 0, "skipped": 0}
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT lower(iso2), id FROM countries")
        country_id = dict(cur.fetchall())
        for folder, (prefix, source_meta) in COLLECTIONS.items():
            credits_path = root / folder / "credits.json"
            if not credits_path.exists():
                continue
            src_id = _source_id(cur, source_meta)
            for key, c in json.loads(credits_path.read_text(encoding="utf-8")).items():
                f = root / folder / c["file"]
                if not f.is_file() or not c.get("sourceUrl"):
                    counts["skipped"] += 1
                    continue
                author, lic = c.get("author") or "", c.get("license") or ""
                obj = store.put_file(f, public=True, prefix=prefix, key=f"{prefix}/{c['file']}",
                                     metadata={"license": lic, "author": author, "source-url": c["sourceUrl"]})
                counts["uploaded"] += 1
                cur.execute("""
                    INSERT INTO media_assets (source_id, country_id, kind, title, url, stored_url, bucket, object_key, content_type,
                                              size_bytes, sha256, author, license, attribution_text, verified)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
                    ON CONFLICT (url) DO UPDATE SET stored_url = EXCLUDED.stored_url, bucket = EXCLUDED.bucket,
                      object_key = EXCLUDED.object_key, content_type = EXCLUDED.content_type, size_bytes = EXCLUDED.size_bytes,
                      sha256 = EXCLUDED.sha256, verified = TRUE""",
                            (src_id, country_id.get(key.split("-")[0]), obj.kind, (c.get("title") or key)[:500], c["sourceUrl"],
                             obj.url, obj.bucket, obj.key, obj.content_type, obj.size, obj.sha256, author[:255], lic[:120],
                             f"© {author or source_meta[1]} · {lic}"))
                counts["rows"] += 1
        conn.commit()
    return counts


def archive_raw(store: ObjectStore, data_dir: Path, source: str, run_id: str) -> int:
    """Lưu payload thô của một lần chạy vào bucket riêng tư (raw/<nguồn>/<run_id>/<file>)."""
    n = 0
    run_dir = data_dir / "raw" / source / run_id
    for f in sorted(run_dir.rglob("*")) if run_dir.is_dir() else []:
        if f.is_file():
            store.put_file(f, public=False, prefix="raw", key=f"raw/{source}/{run_id}/{f.relative_to(run_dir).as_posix()}")
            n += 1
    return n

"""F8 — Ingestion worker nạp dữ liệu vào PostgreSQL (US20)."""
import json
from pathlib import Path

import pytest

from tests.conftest import ac
from worker.pipeline.loader import load

pytestmark = pytest.mark.db

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"\xff\xd9"
PROV_WHC = {"source_name": "unesco_whc", "source_url": "https://data.unesco.org/explore/dataset/whc001/", "license": "CC BY-SA 4.0"}
PROV_EU = {"source_name": "europeana", "source_url": "https://www.europeana.eu", "license": "CC0"}
PROV_WIKI = {"source_name": "wikipedia", "source_url": "https://en.wikipedia.org/wiki/Etiquette_in_Japan", "license": "CC BY-SA 4.0"}


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    agg = tmp_path / "aggregated"
    agg.mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "1.jpg").write_bytes(JPEG)          # file worker đã tải (giấy phép CC0)
    (tmp_path / "media" / "2.jpg").write_bytes(JPEG + b"x")   # file KHÔNG được phép lưu (chưa xác minh giấy phép)
    (agg / "countries.json").write_text(json.dumps([{"iso2": "JP", "iso3": "JPN", "name_en": "Japan", "capital": "Tokyo",
                                                     "languages": ["Japanese"], "currencies": ["yen"], "neighbors": ["KR"]}]))
    (agg / "heritage.json").write_text(json.dumps([
        {"unesco_id": "WHC-660", "name": "Himeji-jo", "type": "tangible", "list_type": "World Heritage List", "countries": ["JP"],
         "inscribed_year": 1993, "criteria": "(i)(iv)", "lat": 34.83, "lng": 134.69, "provenance": PROV_WHC}]))
    (agg / "media.json").write_text(json.dumps([
        {"url": "https://www.europeana.eu/item/1", "image_url": "https://img/1.jpg", "local_path": "media/1.jpg", "verified": True,
         "author": "Museum A", "license": "CC0", "attribution_text": "Museum A via Europeana", "provenance": PROV_EU},
        {"url": "https://www.europeana.eu/item/2", "image_url": "https://img/2.jpg", "local_path": "media/2.jpg", "verified": False,
         "author": "Museum B", "license": "In copyright", "attribution_text": "Museum B via Europeana", "provenance": PROV_EU}]))
    (agg / "documents.json").write_text(json.dumps([
        {"country": "JP", "title": "Etiquette in Japan", "section": "Gift giving", "text": "Gifts are presented with both hands.",
         "language": "en", "category_guess": "gift_giving", "excerpt_only": False, "provenance": PROV_WIKI}]))
    (tmp_path / "runs" / "20261030T000000Z_unesco_whc.json").write_text(json.dumps(
        {"source_name": "unesco_whc", "status": "succeeded", "started_at": "2026-10-30T00:00:00Z", "finished_at": "2026-10-30T00:00:09Z",
         "records_in": 1, "records_changed": 1, "errors": [], "skipped": ["robots.txt chặn: https://whc.unesco.org"]}))
    return tmp_path


def _counts(db) -> dict[str, int]:
    return {t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("heritage_items", "heritage_item_countries", "media_assets", "source_documents", "ingestion_runs", "sources")}


@ac("AC20.1")
def test_run_is_logged_with_counts_and_errors(db, pg_dsn, data_dir):
    load(data_dir, pg_dsn)
    row = db.execute("SELECT status, records_in, records_changed, errors FROM ingestion_runs WHERE source_name = 'unesco_whc'").fetchone()
    assert row[0] == "succeeded" and row[1] == 1 and row[2] == 1
    assert any("robots.txt" in e for e in row[3])


@ac("AC20.2")
def test_reload_is_idempotent(db, pg_dsn, data_dir):
    load(data_dir, pg_dsn)
    first = _counts(db)
    load(data_dir, pg_dsn)
    assert _counts(db) == first


@ac("AC20.3")
def test_raw_data_is_kept(db, pg_dsn, data_dir):
    load(data_dir, pg_dsn)
    raw = db.execute("SELECT raw_data FROM heritage_items WHERE unesco_id = 'WHC-660'").fetchone()[0]
    assert raw["name"] == "Himeji-jo"
    assert db.execute("SELECT raw_data->>'name_en' FROM countries WHERE iso2 = 'JP'").fetchone()[0] == "Japan"


@ac("AC18.2")
def test_only_verified_media_goes_to_object_storage(db, pg_dsn, data_dir, object_store):
    load(data_dir, pg_dsn, object_store)
    rows = {r[0]: r[1:] for r in db.execute("""SELECT url, stored_url, bucket, object_key FROM media_assets
                                                WHERE url LIKE 'https://www.europeana.eu/item/%'""").fetchall()}
    stored_url, bucket, key = rows["https://www.europeana.eu/item/1"]
    assert bucket == "test-media" and stored_url == f"/media/{key}" and object_store.exists(bucket, key)
    assert rows["https://www.europeana.eu/item/2"] == (None, None, None), "chưa xác minh giấy phép → chỉ lưu liên kết (BR09)"


@ac("AC04.2")
def test_loaded_heritage_keeps_unesco_license(db, pg_dsn, data_dir):
    load(data_dir, pg_dsn)
    lic = db.execute("""SELECT s.license FROM heritage_items h JOIN sources s ON s.id = h.source_id
                        WHERE h.unesco_id = 'WHC-660'""").fetchone()[0]
    assert lic == "CC BY-SA 4.0"


@ac("AC20.4")
def test_index_builds_sourced_chunks_for_all_kinds_idempotently(db, fake_embedder):
    from worker.pipeline.indexer import index
    embed = lambda texts: [fake_embedder.embed_one(t) for t in texts]
    first = index(db, embed)
    assert first["claim"] == 6 and first["reference"] >= 1 and first["heritage"] == 3
    second = index(db, embed)
    assert second == first
    assert db.execute("SELECT count(*) FROM entry_chunks").fetchone()[0] == sum(first.values())
    assert db.execute("SELECT count(*) FROM entry_chunks WHERE source_id IS NULL").fetchone()[0] == 0, "mọi đoạn phải có nguồn"
    assert db.execute("SELECT count(*) FROM entry_chunks WHERE kind = 'claim' AND entry_id IN (3, 5)").fetchone()[0] == 0


@ac("AC20.4")
def test_long_documents_are_split_on_sentences():
    from worker.pipeline.indexer import split_text
    text = " ".join(f"Câu số {i} nói về phong tục tặng quà ở Nhật Bản." for i in range(80))
    parts = split_text(text, 300)
    assert len(parts) > 1 and all(len(p) <= 300 for p in parts)
    assert all(p.endswith(".") for p in parts)

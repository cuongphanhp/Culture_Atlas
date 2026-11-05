"""F8 — Ingestion worker nạp dữ liệu vào PostgreSQL (US20)."""
import json
from pathlib import Path

import pytest

from tests.conftest import ac
from worker.pipeline.loader import load

pytestmark = pytest.mark.db

PROV_WHC = {"source_name": "unesco_whc", "source_url": "https://data.unesco.org/explore/dataset/whc001/", "license": "CC BY-SA 4.0"}
PROV_EU = {"source_name": "europeana", "source_url": "https://www.europeana.eu", "license": "CC0"}
PROV_WIKI = {"source_name": "wikipedia", "source_url": "https://en.wikipedia.org/wiki/Etiquette_in_Japan", "license": "CC BY-SA 4.0"}


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    agg = tmp_path / "aggregated"
    agg.mkdir()
    (tmp_path / "runs").mkdir()
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
def test_only_verified_media_is_stored_locally(db, pg_dsn, data_dir):
    load(data_dir, pg_dsn)
    rows = dict(db.execute("SELECT url, stored_url FROM media_assets WHERE url LIKE 'https://www.europeana.eu/item/%'").fetchall())
    assert rows["https://www.europeana.eu/item/1"] == "media/1.jpg"
    assert rows["https://www.europeana.eu/item/2"] is None


@ac("AC04.2")
def test_loaded_heritage_keeps_unesco_license(db, pg_dsn, data_dir):
    load(data_dir, pg_dsn)
    lic = db.execute("""SELECT s.license FROM heritage_items h JOIN sources s ON s.id = h.source_id
                        WHERE h.unesco_id = 'WHC-660'""").fetchone()[0]
    assert lic == "CC BY-SA 4.0"

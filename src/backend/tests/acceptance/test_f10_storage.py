"""Lưu trữ: file phi cấu trúc ở object storage (MinIO/S3), embedding ở Qdrant, PostgreSQL giữ metadata + URL + văn bản.
Chạy trên MinIO và Qdrant riêng của bộ test (compose.test.yaml)."""
import hashlib
import json
import os
from pathlib import Path

import httpx
import pytest

from tests.conftest import JSON_HEADERS, REPO, ac, route
from worker.pipeline.loader import load
from worker.pipeline.media_seed import archive_raw, seed

pytestmark = pytest.mark.db
S3 = "http://" + os.environ["S3_ENDPOINT"]
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"\xff\xd9"
PROV = {"source_name": "europeana", "source_url": "https://www.europeana.eu", "license": "CC0"}


def _media_dir(tmp_path: Path, verified: bool = True) -> Path:
    (tmp_path / "aggregated").mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "a.jpg").write_bytes(JPEG)
    (tmp_path / "aggregated" / "media.json").write_text(json.dumps([
        {"url": "https://www.europeana.eu/item/a", "image_url": "https://img/a.jpg", "local_path": "media/a.jpg",
         "verified": verified, "country": "JP", "title": "Kimono", "author": "Museum A", "license": "CC0",
         "attribution_text": "Museum A via Europeana", "provenance": PROV}]))
    return tmp_path


# ── AC18.3 — file ở object storage, DB chỉ giữ metadata + URL ──
@ac("AC18.3")
def test_media_metadata_and_url_in_db_file_in_object_storage(db, pg_dsn, tmp_path, object_store):
    d = _media_dir(tmp_path)
    load(d, pg_dsn, object_store)
    row = db.execute("""SELECT kind, bucket, object_key, content_type, size_bytes, sha256, stored_url, author, license, title,
                               (SELECT iso2 FROM countries WHERE id = country_id) FROM media_assets
                        WHERE url = 'https://www.europeana.eu/item/a'""").fetchone()
    kind, bucket, key, ctype, size, sha, url, author, lic, title, iso = row
    assert (kind, bucket, ctype, size, author, lic, title, iso) == ("image", "test-media", "image/jpeg", len(JPEG), "Museum A", "CC0", "Kimono", "JP")
    assert sha == hashlib.sha256(JPEG).hexdigest() and key.endswith(sha + ".jpg")
    assert url == f"/media/{key}", "URL công khai do object storage cấp (nginx chuyển /media/* tới bucket)"
    obj = object_store.client.get_object(bucket, key)
    assert obj.read() == JPEG and obj.headers["x-amz-meta-license"] == "CC0"
    cols = {r[0] for r in db.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'media_assets'")}
    assert not cols & {"data", "content", "blob", "bytes"}, "DB không chứa nội dung file"


@ac("AC18.3")
def test_reload_does_not_duplicate_objects_or_rows(db, pg_dsn, tmp_path, object_store):
    d = _media_dir(tmp_path)
    load(d, pg_dsn, object_store)
    load(d, pg_dsn, object_store)
    assert db.execute("SELECT count(*) FROM media_assets WHERE url = 'https://www.europeana.eu/item/a'").fetchone()[0] == 1
    keys = [o.object_name for o in object_store.client.list_objects("test-media", prefix="media/europeana/", recursive=True)
            if o.object_name.endswith(hashlib.sha256(JPEG).hexdigest() + ".jpg")]
    assert len(keys) == 1


@ac("AC18.3")
def test_link_only_media_is_fetched_into_object_storage(db, pg_dsn, tmp_path, object_store):
    d = _media_dir(tmp_path)
    (d / "media" / "a.jpg").unlink()                      # worker chưa tải file → loader tải bản thu nhỏ
    fetched = []
    load(d, pg_dsn, object_store, fetch=lambda url: (fetched.append(url) or JPEG, "image/jpeg"))
    assert fetched == ["https://img/a.jpg"]
    assert db.execute("SELECT stored_url IS NOT NULL FROM media_assets WHERE url = 'https://www.europeana.eu/item/a'").fetchone()[0]


# ── AC18.4 — quyền truy cập bucket ──
@ac("AC18.4")
def test_media_objects_public_bucket_not_listable_raw_private(db, pg_dsn, tmp_path, object_store):
    load(_media_dir(tmp_path), pg_dsn, object_store)
    key = db.execute("SELECT object_key FROM media_assets WHERE object_key IS NOT NULL LIMIT 1").fetchone()[0]
    assert httpx.get(f"{S3}/test-media/{key}").status_code == 200, "ảnh đã xác minh: ai cũng xem được"
    assert httpx.get(f"{S3}/test-media/").status_code == 403, "không được liệt kê bucket media"
    raw = object_store.put_bytes(b'{"secret": false}', "raw/test/run/x.json", public=False)
    assert raw.url == "s3://test-raw/raw/test/run/x.json"
    assert httpx.get(f"{S3}/test-raw/raw/test/run/x.json").status_code == 403, "payload thô phải riêng tư"


@ac("AC18.4")
def test_worker_raw_payloads_archived_privately(tmp_path, object_store):
    run_dir = tmp_path / "raw" / "unesco_whc" / "20261106T000000Z"
    run_dir.mkdir(parents=True)
    (run_dir / "export.json").write_text('{"rows": []}')
    assert archive_raw(object_store, tmp_path, "unesco_whc", "20261106T000000Z") == 1
    assert object_store.exists("test-raw", "raw/unesco_whc/20261106T000000Z/export.json")


# ── AC18.5 — ảnh giao diện nạp lên object storage ──
@ac("AC18.5")
def test_seed_media_uploads_curated_photos_with_credits(db, pg_dsn, tmp_path, object_store):
    (tmp_path / "culture").mkdir()
    (tmp_path / "culture" / "jp.jpg").write_bytes(JPEG)
    (tmp_path / "culture" / "credits.json").write_text(json.dumps({"jp": {
        "file": "jp.jpg", "title": "Fushimi Inari", "author": "Tác giả A", "license": "CC BY-SA 4.0",
        "sourceUrl": "https://commons.wikimedia.org/wiki/File:Fushimi.jpg"}}))
    assert seed(tmp_path, pg_dsn, object_store)["rows"] == 1
    assert seed(tmp_path, pg_dsn, object_store)["rows"] == 1                    # chạy lại không tạo trùng
    row = db.execute("""SELECT stored_url, object_key, license, attribution_text, verified, (SELECT iso2 FROM countries c WHERE c.id = country_id)
                        FROM media_assets WHERE url = 'https://commons.wikimedia.org/wiki/File:Fushimi.jpg'""").fetchall()
    assert row == [("/media/photos/jp.jpg", "photos/jp.jpg", "CC BY-SA 4.0", "© Tác giả A · CC BY-SA 4.0", True, "JP")]
    assert httpx.get(f"{S3}/test-media/photos/jp.jpg").content == JPEG


@ac("AC18.5")
def test_frontend_photo_credits_match_media_seed_and_files_exist():
    seed_credits = json.loads((REPO / "src/media-seed/culture/credits.json").read_text(encoding="utf-8"))
    fe_credits = json.loads((REPO / "src/frontend/src/app/core/mock/photo-credits.json").read_text(encoding="utf-8"))
    assert fe_credits == seed_credits, "photo-credits.json của frontend phải là bản sao của src/media-seed/culture/credits.json"
    for folder in ("culture", "objects"):
        for c in json.loads((REPO / f"src/media-seed/{folder}/credits.json").read_text(encoding="utf-8")).values():
            assert (REPO / f"src/media-seed/{folder}/{c['file']}").is_file(), c["file"]
            assert c.get("license") and c.get("sourceUrl"), "mọi ảnh phải có giấy phép + trang nguồn (BR08)"
    assert not (REPO / "src/frontend/public/images").exists(), "ảnh không được đóng gói vào bản build giao diện"


# ── AC20.5 — embedding ở Qdrant ──
@ac("AC20.5")
def test_embeddings_live_in_qdrant_not_postgres(db):
    from worker.core.vectors import VectorIndex
    vi = VectorIndex()
    n_chunks = db.execute("SELECT count(*) FROM entry_chunks").fetchone()[0]
    assert n_chunks > 0 and vi.count() == n_chunks, "mỗi đoạn có đúng một vector trong Qdrant"
    cid = db.execute("SELECT id FROM entry_chunks WHERE kind = 'claim' AND metadata->>'country' = 'JP' LIMIT 1").fetchone()[0]
    p = vi.get(cid)
    assert p.payload["kind"] == "claim" and p.payload["countries"] == ["JP"] and len(p.vector) == 1024
    cols = {r[0] for r in db.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'entry_chunks'")}
    assert "embedding" not in cols, "PostgreSQL không lưu vector"


@route("POST", "/api/ai/chat")
@ac("AC06.7", "AC20.5")
def test_chat_falls_back_to_keywords_when_qdrant_down(client):
    from app.ai.vector_store import VectorStore, get_vector_store
    from app.main import app
    app.dependency_overrides[get_vector_store] = lambda: VectorStore("http://127.0.0.1:1", "", "khong-co")
    r = client.post("/api/ai/chat", json={"message": "Vì sao người Nhật cúi chào?"}, headers=JSON_HEADERS)
    assert r.status_code == 200 and r.json()["route"] == "rag" and r.json()["citations"]

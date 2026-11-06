-- Migration 003 — media_assets chuyển sang mô hình object storage: file ở MinIO/S3, DB giữ metadata + URL.
--   docker compose exec -T db psql -U atlas -d culture_atlas < src/database/migrations/003_media_object_storage.sql
BEGIN;
ALTER TABLE media_assets
  ADD COLUMN IF NOT EXISTS country_id INT REFERENCES countries(id),
  ADD COLUMN IF NOT EXISTS kind VARCHAR(10) NOT NULL DEFAULT 'image',
  ADD COLUMN IF NOT EXISTS title VARCHAR(500),
  ADD COLUMN IF NOT EXISTS bucket VARCHAR(63),
  ADD COLUMN IF NOT EXISTS object_key VARCHAR(1024),
  ADD COLUMN IF NOT EXISTS content_type VARCHAR(120),
  ADD COLUMN IF NOT EXISTS size_bytes BIGINT,
  ADD COLUMN IF NOT EXISTS sha256 CHAR(64);
-- stored_url cũ là đường dẫn file cục bộ của worker → bỏ; chạy lại `worker.cli load` để tải file lên object storage
UPDATE media_assets SET stored_url = NULL WHERE stored_url IS NOT NULL AND object_key IS NULL;
ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS ck_media_kind;
ALTER TABLE media_assets ADD CONSTRAINT ck_media_kind CHECK (kind IN ('image', 'video', 'audio', 'document', 'data'));
ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS ck_media_size;
ALTER TABLE media_assets ADD CONSTRAINT ck_media_size CHECK (size_bytes IS NULL OR size_bytes >= 0);
ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS ck_media_stored_only_if_verified;
ALTER TABLE media_assets ADD CONSTRAINT ck_media_stored_only_if_verified CHECK ((stored_url IS NULL AND object_key IS NULL) OR verified);
ALTER TABLE media_assets DROP CONSTRAINT IF EXISTS ck_media_object_complete;
ALTER TABLE media_assets ADD CONSTRAINT ck_media_object_complete CHECK (object_key IS NULL OR (bucket IS NOT NULL AND stored_url IS NOT NULL));
-- url là khoá tự nhiên (loader cũ đã chống trùng bằng NOT EXISTS)
DELETE FROM media_assets a USING media_assets b WHERE a.url = b.url AND a.id > b.id;
CREATE UNIQUE INDEX IF NOT EXISTS ux_media_url ON media_assets (url);
CREATE UNIQUE INDEX IF NOT EXISTS ux_media_object ON media_assets (bucket, object_key);
CREATE INDEX IF NOT EXISTS ix_media_country ON media_assets (country_id, kind);
COMMIT;

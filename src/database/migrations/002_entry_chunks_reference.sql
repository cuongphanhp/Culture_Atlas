-- Migration 002 — entry_chunks chứa thêm đoạn từ tài liệu tham khảo và di sản UNESCO (cho AI Guide).
-- Áp dụng cho DB đã tạo trước đó (DB mới tạo từ culture_atlas.sql đã có sẵn):
--   docker compose exec -T db psql -U atlas -d culture_atlas < src/database/migrations/002_entry_chunks_reference.sql
BEGIN;
ALTER TABLE entry_chunks
  ADD COLUMN IF NOT EXISTS kind VARCHAR(12) NOT NULL DEFAULT 'claim',
  ADD COLUMN IF NOT EXISTS source_id BIGINT REFERENCES sources(id),
  ADD COLUMN IF NOT EXISTS source_document_id BIGINT REFERENCES source_documents(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS heritage_item_id BIGINT REFERENCES heritage_items(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS chunk_index SMALLINT NOT NULL DEFAULT 0,
  ALTER COLUMN entry_id DROP NOT NULL;
ALTER TABLE entry_chunks DROP CONSTRAINT IF EXISTS ck_chunk_kind;
ALTER TABLE entry_chunks ADD CONSTRAINT ck_chunk_kind CHECK (kind IN ('claim', 'reference', 'heritage'));
ALTER TABLE entry_chunks DROP CONSTRAINT IF EXISTS ck_chunk_owner;
ALTER TABLE entry_chunks ADD CONSTRAINT ck_chunk_owner CHECK (
  (kind = 'claim' AND entry_id IS NOT NULL) OR
  (kind = 'reference' AND source_document_id IS NOT NULL) OR
  (kind = 'heritage' AND heritage_item_id IS NOT NULL));
CREATE INDEX IF NOT EXISTS ix_chunks_kind ON entry_chunks (kind);
COMMIT;

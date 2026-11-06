-- Migration 004 — embedding của chỉ mục RAG chuyển sang Qdrant (vector DB). PostgreSQL chỉ giữ văn bản + metadata.
-- Sau khi chạy: lập lại chỉ mục để ghi vector vào Qdrant:  docker compose run --rm worker python -m worker.cli index
--   docker compose exec -T db psql -U atlas -d culture_atlas < src/database/migrations/004_embeddings_to_qdrant.sql
BEGIN;
DROP INDEX IF EXISTS ix_chunks_embedding;
ALTER TABLE entry_chunks DROP COLUMN IF EXISTS embedding;
COMMIT;

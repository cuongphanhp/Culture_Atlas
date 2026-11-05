"""Lọc metadata + hybrid search (FTS + pgvector) + rerank. Embedding/rerank chạy ở dịch vụ AI local."""
from __future__ import annotations

from app.ai.local_ai import LocalAIClient, get_local_ai


def get_embedder() -> LocalAIClient:
    """FastAPI dependency: đối tượng có `async embed(texts) -> list[list[float]]` (1024 chiều). Test thay bằng FakeEmbedder."""
    return get_local_ai()

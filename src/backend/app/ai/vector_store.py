"""Tìm kiếm vector cho AI Guide trên Qdrant (embedding lưu ở vector DB, không ở PostgreSQL).
Gọi REST API của Qdrant bằng httpx (không dùng qdrant-client để image backend nhỏ gọn)."""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import get_settings


class VectorStoreUnavailable(RuntimeError):
    """Qdrant không phản hồi → truy xuất chỉ dùng tìm kiếm từ khoá (AC06.7)."""


class VectorSearch(Protocol):
    """Giao diện tìm vector mà retrieval dùng (VectorStore ở production; test có thể thay bằng bản lỗi)."""

    async def search(self, vector: list[float], countries: list[str], limit: int) -> list[tuple[int, float]]:
        """→ [(chunk_id, cosine)]."""
        ...


class VectorStore:
    """Client REST của Qdrant cho API (chỉ đọc). Ghi vector do worker đảm nhiệm (worker/core/vectors.py)."""

    def __init__(self, url: str, api_key: str, collection: str, timeout: float = 10.0) -> None:
        self.url = url.rstrip("/")
        self.headers = {"api-key": api_key} if api_key else {}
        self.collection = collection
        self.timeout = timeout

    async def search(self, vector: list[float], countries: list[str], limit: int) -> list[tuple[int, float]]:
        """→ [(chunk_id, cosine)], lọc theo quốc gia (payload `countries`) ngay trong Qdrant."""
        body: dict = {"query": vector, "limit": limit, "with_payload": False, "with_vector": False}
        if countries:
            body["filter"] = {"must": [{"key": "countries", "match": {"any": countries}}]}
        try:
            # client mới mỗi lần gọi: không dính event loop cũ (nhiều worker / test)
            async with httpx.AsyncClient(base_url=self.url, headers=self.headers, timeout=self.timeout) as http:
                r = await http.post(f"/collections/{self.collection}/points/query", json=body)
                r.raise_for_status()
        except httpx.HTTPError as e:      # mất kết nối, collection chưa có, sai API key…
            raise VectorStoreUnavailable(f"{type(e).__name__}: {e}") from e
        return [(int(p["id"]), float(p["score"])) for p in r.json()["result"]["points"]]


@lru_cache
def get_vector_store() -> VectorStore:
    """FastAPI dependency. Test dùng Qdrant riêng (compose.test.yaml) hoặc thay bằng bản lỗi."""
    s = get_settings()
    return VectorStore(s.qdrant_url, s.qdrant_api_key, s.qdrant_collection)

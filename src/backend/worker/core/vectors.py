"""Ghi embedding của chỉ mục RAG vào Qdrant (vector DB). PostgreSQL giữ văn bản + metadata của đoạn (entry_chunks);
Qdrant giữ vector, point id = entry_chunks.id, payload để lọc khi tìm (kind, countries, category).

Gọi thẳng REST API của Qdrant bằng httpx (không dùng qdrant-client: kéo theo grpcio/protobuf/numpy ~150 MB vào image).
API key qua HTTP chỉ trong mạng Docker nội bộ / 127.0.0.1 — dùng https khi Qdrant nằm ngoài máy chủ.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

DIM = 1024


@dataclass(frozen=True)
class QdrantConfig:
    """Kết nối Qdrant: QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION."""

    url: str = "http://localhost:6333"
    api_key: str = ""
    collection: str = "culture_chunks"

    @classmethod
    def from_env(cls) -> QdrantConfig:
        """Đọc cấu hình từ biến môi trường."""
        return cls(os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/"), os.getenv("QDRANT_API_KEY", ""),
                   os.getenv("QDRANT_COLLECTION", "culture_chunks"))


@dataclass
class Point:
    """Một point của Qdrant: id = entry_chunks.id, payload để lọc, vector 1024 chiều."""

    id: int
    payload: dict = field(default_factory=dict)
    vector: list[float] | None = None


class VectorIndex:
    """Ghi / đọc collection vector của chỉ mục RAG (REST API của Qdrant, đồng bộ)."""

    def __init__(self, cfg: QdrantConfig | None = None, timeout: float = 60.0) -> None:
        self.cfg = cfg or QdrantConfig.from_env()
        headers = {"api-key": self.cfg.api_key} if self.cfg.api_key else {}
        self.http = httpx.Client(base_url=self.cfg.url, headers=headers, timeout=timeout)
        self.base = f"/collections/{self.cfg.collection}"

    def _call(self, method: str, path: str, **kw: Any) -> dict | list:
        """Gọi REST API, lỗi HTTP → httpx.HTTPStatusError; trả trường `result`."""
        r = self.http.request(method, path, **kw)
        r.raise_for_status()
        return r.json().get("result") if r.content else {}

    def exists(self) -> bool:
        """Collection đã tồn tại chưa."""
        return bool(self._call("GET", f"{self.base}/exists")["exists"])

    def ensure(self) -> None:
        """Tạo collection (1024 chiều, cosine) + index payload kind / countries / category nếu chưa có."""
        if self.exists():
            return
        self._call("PUT", self.base, json={"vectors": {"size": DIM, "distance": "Cosine"}})
        for name in ("kind", "countries", "category"):
            self._call("PUT", f"{self.base}/index", params={"wait": "true"}, json={"field_name": name, "field_schema": "keyword"})

    def drop(self) -> None:
        """Xoá collection (dùng khi dựng lại chỉ mục từ đầu / test)."""
        if self.exists():
            self._call("DELETE", self.base)

    def delete_kinds(self, kinds: list[str]) -> None:
        """Xoá mọi point thuộc các loại đoạn `kinds` (trước khi dựng lại các loại đó)."""
        self.ensure()
        self._call("POST", f"{self.base}/points/delete", params={"wait": "true"},
                   json={"filter": {"must": [{"key": "kind", "match": {"any": list(kinds)}}]}})

    def upsert(self, ids: list[int], vectors: list[list[float]], payloads: list[dict], batch: int = 256) -> None:
        """Ghi vector theo lô `batch` point."""
        self.ensure()
        for i in range(0, len(ids), batch):
            points = [{"id": pid, "vector": vec, "payload": pl}
                      for pid, vec, pl in zip(ids[i:i + batch], vectors[i:i + batch], payloads[i:i + batch], strict=True)]
            self._call("PUT", f"{self.base}/points", params={"wait": "true"}, json={"points": points})

    def count(self) -> int:
        """Số point hiện có (0 nếu chưa có collection)."""
        return int(self._call("POST", f"{self.base}/points/count", json={"exact": True})["count"]) if self.exists() else 0

    def get(self, point_id: int) -> Point | None:
        """Đọc một point kèm payload và vector."""
        res = self._call("POST", f"{self.base}/points", json={"ids": [point_id], "with_payload": True, "with_vector": True})
        return Point(res[0]["id"], res[0].get("payload") or {}, res[0].get("vector")) if res else None

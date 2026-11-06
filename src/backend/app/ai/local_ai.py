"""Client gọi dịch vụ AI local (src/ai-local): nhận dạng giọng nói, đọc văn bản, embedding, rerank.
Âm thanh của người dùng chỉ đi tới dịch vụ local trong mạng nội bộ — không gửi ra ngoài."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings


class LocalAIUnavailable(RuntimeError):
    """Dịch vụ AI local không chạy / model chưa nạp → API trả 503."""


class LocalAIError(RuntimeError):
    """Dịch vụ AI local từ chối yêu cầu (âm thanh lỗi, quá dài…) → chuyển tiếp mã lỗi."""

    def __init__(self, status: int, title: str, detail: str | None) -> None:
        super().__init__(title)
        self.status, self.title, self.detail = status, title, detail


class LocalAIClient:
    """Client HTTP của dịch vụ AI local (src/ai-local, mạng Docker nội bộ). Lỗi kết nối / 503 → LocalAIUnavailable."""

    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url, self.timeout = base_url, timeout

    async def _call(self, method: str, path: str, **kw: Any) -> httpx.Response:
        """Gọi một endpoint, đổi lỗi mạng / HTTP thành LocalAIUnavailable hoặc LocalAIError."""
        try:
            # Client mới cho mỗi lần gọi: không dính event loop cũ (nhiều worker / test); gọi nội bộ nên rẻ
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as http:
                r = await http.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise LocalAIUnavailable(f"Không kết nối được dịch vụ AI local: {type(e).__name__}") from e
        if r.status_code == 503:
            raise LocalAIUnavailable(r.json().get("detail", "Model chưa sẵn sàng"))
        if r.status_code >= 400:
            body = r.json() if r.headers.get("content-type", "").startswith("application/") else {}
            raise LocalAIError(r.status_code, body.get("title", "Lỗi AI local"), body.get("detail"))
        return r

    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> dict[str, Any]:
        """STT: âm thanh → {"text", "segments", "duration", "model"}. Âm thanh không được lưu."""
        r = await self._call("POST", "/v1/stt", files={"file": (filename, audio, content_type)})
        return r.json()

    async def synthesize(self, text: str, voice: str | None) -> tuple[bytes, dict[str, str]]:
        """TTS: văn bản → (WAV, header X-* mô tả giọng / thời lượng)."""
        r = await self._call("POST", "/v1/tts", json={"text": text, "voice": voice})
        return r.content, {k: v for k, v in r.headers.items() if k.lower().startswith("x-")}

    async def voices(self) -> dict[str, Any]:
        """Danh sách giọng đọc của TTS."""
        return (await self._call("GET", "/v1/voices")).json()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embedding 1024 chiều (AITeamVN) cho từng văn bản."""
        return (await self._call("POST", "/v1/embed", json={"texts": texts})).json()["vectors"]

    async def rerank(self, query: str, documents: list[str], top_k: int | None = None) -> list[dict[str, float]]:
        """Chấm độ liên quan (query, đoạn) → [{"index", "score"}] giảm dần."""
        r = await self._call("POST", "/v1/rerank", json={"query": query, "documents": documents, "top_k": top_k})
        return r.json()["results"]


@lru_cache
def get_local_ai() -> LocalAIClient:
    """FastAPI dependency. Test thay bằng FakeLocalAI (tests/fakes.py)."""
    s = get_settings()
    return LocalAIClient(s.ai_local_url, s.ai_local_timeout_s)

"""LLM adapter: giao diện chung + bản cài đặt OpenAI (GPT-6 Luna chính, GPT-4o dự phòng). Xem docs/11-vietnamese-chat-stack.md.

Hợp đồng dùng chung với bộ test (tests/fakes.py::FakeLLM):
- API lấy adapter qua dependency `get_llm()` để test thay bằng FakeLLM.
- Bằng chứng truy xuất được gán nhãn c1..cN trong prompt; câu trả lời trích dẫn bằng "[c#]".
- `complete_json(name=...)`: tên tác vụ cố định — "follow_ups", "comparison", "quiz_drafts".
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import get_settings


class LLMUnavailable(RuntimeError):
    """Nhà cung cấp LLM lỗi / hết thời gian → API trả 503."""


class LLMAdapter(Protocol):
    model: str

    def stream(self, messages: list[dict[str, str]], *, temperature: float | None = None) -> AsyncIterator[str]:
        """Sinh câu trả lời dạng stream (từng đoạn văn bản)."""
        ...

    async def complete_json(self, messages: list[dict[str, str]], *, name: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Sinh JSON theo schema (structured output)."""
        ...


def _is_reasoning(model: str) -> bool:
    """GPT-6 (Luna…) là model suy luận: không nhận `temperature`, dùng `reasoning_effort`."""
    return not model.startswith("gpt-4")


def _retryable(e: Exception) -> bool:
    """Lỗi tạm thời (mạng, quá tải, 5xx) → thử model dự phòng. Lỗi 4xx (sai tham số, key) thì không."""
    import openai
    return isinstance(e, (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError, openai.InternalServerError))


class OpenAIAdapter:
    """OpenAI Chat Completions: model chính (GPT-6 Luna) + dự phòng (GPT-4o).
    Stream văn bản và structured output (json_schema strict). `last_model` = model thực sự đã trả lời (ghi chat_logs)."""

    def __init__(self, api_key: str, model: str = "gpt-6-luna", fallback: str = "gpt-4o", *,
                 reasoning_effort: str = "none", temperature: float = 0.4, timeout: float = 30.0, client: Any = None) -> None:
        if client is None:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=1)
        self.client = client
        self.model, self.fallback = model, fallback
        self.reasoning_effort, self.temperature = reasoning_effort, temperature
        self.last_model = model

    def _params(self, model: str, temperature: float | None) -> dict[str, Any]:
        if _is_reasoning(model):
            return {"reasoning_effort": self.reasoning_effort}
        return {"temperature": self.temperature if temperature is None else temperature}

    def _models(self) -> list[str]:
        return [self.model] + ([self.fallback] if self.fallback and self.fallback != self.model else [])

    async def _stream(self, messages: list[dict[str, str]], temperature: float | None) -> AsyncIterator[str]:
        import openai
        models = self._models()
        for i, model in enumerate(models):
            started = False
            try:
                resp = await self.client.chat.completions.create(
                    model=model, messages=messages, stream=True, **self._params(model, temperature))
                async for chunk in resp:
                    if chunk.choices and (text := chunk.choices[0].delta.content):
                        started = True
                        self.last_model = model
                        yield text
                return
            except openai.OpenAIError as e:
                # Chỉ chuyển model khi chưa gửi chữ nào cho người dùng — tránh câu trả lời bị ghép từ 2 model
                if started or i == len(models) - 1 or not _retryable(e):
                    raise LLMUnavailable(f"{model}: {e}") from e

    def stream(self, messages: list[dict[str, str]], *, temperature: float | None = None) -> AsyncIterator[str]:
        return self._stream(messages, temperature)

    async def complete_json(self, messages: list[dict[str, str]], *, name: str, schema: dict[str, Any]) -> dict[str, Any]:
        import openai
        models = self._models()
        for i, model in enumerate(models):
            try:
                resp = await self.client.chat.completions.create(
                    model=model, messages=messages, **self._params(model, 0.2),
                    response_format={"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}})
                self.last_model = model
                return json.loads(resp.choices[0].message.content or "{}")
            except openai.OpenAIError as e:
                if i == len(models) - 1 or not _retryable(e):
                    raise LLMUnavailable(f"{model}: {e}") from e
        raise LLMUnavailable("Không có model nào khả dụng")


@lru_cache
def _openai() -> OpenAIAdapter:
    s = get_settings()
    if not s.openai_api_key:
        raise LLMUnavailable("Chưa cấu hình OPENAI_API_KEY")
    return OpenAIAdapter(s.openai_api_key, s.llm_model, s.llm_fallback_model, reasoning_effort=s.llm_reasoning_effort,
                         temperature=s.llm_temperature, timeout=s.llm_timeout_s)


def get_llm() -> LLMAdapter:
    """FastAPI dependency. Test thay bằng FakeLLM."""
    return _openai()

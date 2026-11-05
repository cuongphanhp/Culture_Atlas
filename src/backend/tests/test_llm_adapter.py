"""OpenAIAdapter với client OpenAI giả (không gọi mạng): tham số theo model, dự phòng GPT-4o, chặn model lạ."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.ai.llm_adapter import LLMUnavailable, OpenAIAdapter
from tests.conftest import ac

REQ = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _chunk(text):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


class FakeCompletions:
    """Kịch bản theo model: "ok" | "down" (5xx) | "bad" (400) | "cut" (đứt giữa chừng)."""

    def __init__(self, plan):
        self.plan, self.calls = plan, []

    async def create(self, **kw):
        self.calls.append(kw)
        mode = self.plan[kw["model"]]
        if mode == "down":
            raise openai.InternalServerError("server error", response=httpx.Response(500, request=REQ), body=None)
        if mode == "bad":
            raise openai.BadRequestError("bad param", response=httpx.Response(400, request=REQ), body=None)
        if not kw.get("stream"):
            msg = SimpleNamespace(content=json.dumps({"questions": [f"từ {kw['model']}"]}))
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

        async def gen():
            yield _chunk(f"[{kw['model']}] Xin ")
            if mode == "cut":
                raise openai.APIConnectionError(request=REQ)
            yield _chunk("chào")
        return gen()


def adapter(plan, **kw):
    comp = FakeCompletions(plan)
    client = SimpleNamespace(chat=SimpleNamespace(completions=comp))
    return OpenAIAdapter("k", "gpt-6-luna", "gpt-4o", client=client, **kw), comp


def collect(a, **kw):
    async def run():
        return "".join([t async for t in a.stream([{"role": "user", "content": "hi"}], **kw)])
    return asyncio.run(run())


@ac("AC06.1")
def test_luna_uses_reasoning_effort_not_temperature():
    a, comp = adapter({"gpt-6-luna": "ok", "gpt-4o": "ok"})
    assert collect(a) == "[gpt-6-luna] Xin chào"
    call = comp.calls[0]
    assert call["reasoning_effort"] == "none" and "temperature" not in call
    assert a.last_model == "gpt-6-luna"


@ac("AC06.1")
def test_gpt4o_uses_temperature():
    comp = FakeCompletions({"gpt-4o": "ok"})
    a = OpenAIAdapter("k", "gpt-4o", "", client=SimpleNamespace(chat=SimpleNamespace(completions=comp)), temperature=0.4)
    collect(a)
    assert comp.calls[0]["temperature"] == 0.4 and "reasoning_effort" not in comp.calls[0]


@ac("AC06.1")
def test_falls_back_to_gpt4o_when_luna_down():
    a, comp = adapter({"gpt-6-luna": "down", "gpt-4o": "ok"})
    assert collect(a) == "[gpt-4o] Xin chào"
    assert [c["model"] for c in comp.calls] == ["gpt-6-luna", "gpt-4o"]
    assert a.last_model == "gpt-4o"


@ac("AC06.1")
def test_no_fallback_on_bad_request():
    a, comp = adapter({"gpt-6-luna": "bad", "gpt-4o": "ok"})
    with pytest.raises(LLMUnavailable):
        collect(a)
    assert [c["model"] for c in comp.calls] == ["gpt-6-luna"]


@ac("AC06.1")
def test_no_fallback_after_text_already_streamed():
    """Không ghép câu trả lời từ 2 model: đã gửi chữ cho người dùng mà đứt → báo lỗi (API trả 503)."""
    a, comp = adapter({"gpt-6-luna": "cut", "gpt-4o": "ok"})
    with pytest.raises(LLMUnavailable):
        collect(a)
    assert [c["model"] for c in comp.calls] == ["gpt-6-luna"]


@ac("AC06.1")
def test_both_down_raises_unavailable():
    a, _ = adapter({"gpt-6-luna": "down", "gpt-4o": "down"})
    with pytest.raises(LLMUnavailable):
        collect(a)


@ac("AC10.1")
def test_complete_json_strict_schema_and_fallback():
    a, comp = adapter({"gpt-6-luna": "down", "gpt-4o": "ok"})
    out = asyncio.run(a.complete_json([{"role": "user", "content": "x"}], name="follow_ups", schema={"type": "object"}))
    assert out == {"questions": ["từ gpt-4o"]}
    assert comp.calls[-1]["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize("model", ["gpt-6.1-sol", "gpt-6-astra", "claude-x"])
def test_only_allowed_models(model, monkeypatch):
    from pydantic import ValidationError

    from app.core.config import Settings
    monkeypatch.setenv("LLM_MODEL", model)
    with pytest.raises(ValidationError, match="không được phép"):
        Settings()


def test_defaults_luna_with_gpt4o_fallback(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.delenv("LLM_FALLBACK_MODEL", raising=False)
    s = Settings(_env_file=None)
    assert (s.llm_model, s.llm_fallback_model, s.llm_reasoning_effort) == ("gpt-6-luna", "gpt-4o", "none")

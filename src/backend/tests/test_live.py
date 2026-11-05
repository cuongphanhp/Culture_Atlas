"""Kiểm tra dịch vụ thật — KHÔNG chạy mặc định (tốn tiền / cần dịch vụ chạy). Chạy: pytest -m live
- GPT-4o: cần OPENAI_API_KEY trong .env
- AI local: cần `uvicorn ai_local.main:app --port 8100` đang chạy
"""
import asyncio
import os

import pytest

from tests.conftest import ac

pytestmark = pytest.mark.live
VI_CHARS = set("ăâđêôơưàảãáạằắặầấậèẻẽéẹềểễếệìỉĩíịòỏõóọồổỗốộờởỡớợùủũúụừửữứựỳỷỹýỵ")


def _settings():
    os.environ.pop("OPENAI_API_KEY", None)          # conftest đặt rỗng; lấy key thật từ .env
    from app.core.config import Settings
    return Settings()


@ac("AC06.1")
@pytest.mark.parametrize("model", ["gpt-6-luna", "gpt-4o"])
def test_llm_streams_vietnamese_fast(model):
    import time
    s = _settings()
    if not s.openai_api_key:
        pytest.skip("Chưa có OPENAI_API_KEY")
    from app.ai.llm_adapter import OpenAIAdapter
    llm = OpenAIAdapter(s.openai_api_key, model, "")

    async def run():
        t0, ttft, parts = time.perf_counter(), None, []
        async for p in llm.stream([
                {"role": "system", "content": "Bạn là hướng dẫn viên văn hoá. Trả lời ngắn gọn bằng tiếng Việt tự nhiên."},
                {"role": "user", "content": "Một câu: người Nhật trao quà thế nào?"}]):
            ttft = ttft or time.perf_counter() - t0
            parts.append(p)
        return "".join(parts), ttft
    answer, ttft = asyncio.run(run())
    assert len(answer) > 10 and VI_CHARS & set(answer.lower()), answer
    assert ttft < 5.0, f"{model} TTFT {ttft:.1f}s"
    assert llm.last_model == model


@ac("AC10.1")
def test_luna_structured_json():
    s = _settings()
    if not s.openai_api_key:
        pytest.skip("Chưa có OPENAI_API_KEY")
    from app.ai.llm_adapter import OpenAIAdapter
    llm = OpenAIAdapter(s.openai_api_key, "gpt-6-luna", "")
    schema = {"type": "object", "additionalProperties": False, "required": ["questions"],
              "properties": {"questions": {"type": "array", "items": {"type": "string"}}}}
    out = asyncio.run(llm.complete_json([{"role": "user", "content": "3 câu hỏi gợi ý tiếp về tặng quà ở Nhật."}],
                                        name="follow_ups", schema=schema))
    assert 1 <= len(out["questions"]) <= 5


@ac("AC21.1")
def test_local_ai_round_trip():
    import httpx
    url = _settings().ai_local_url
    try:
        httpx.get(f"{url}/health", timeout=2)
    except httpx.HTTPError:
        pytest.skip(f"Dịch vụ AI local chưa chạy ở {url}")
    tts = httpx.post(f"{url}/v1/tts", json={"text": "Xin chào, tôi muốn hỏi về văn hoá Nhật Bản."}, timeout=120)
    assert tts.status_code == 200
    stt = httpx.post(f"{url}/v1/stt", files={"file": ("a.wav", tts.content, "audio/wav")}, timeout=120).json()
    assert {"xin", "chào", "nhật", "bản"} <= set(stt["text"].lower().replace(",", "").split()), stt["text"]

"""LLM và embedding giả cho bộ test: không gọi mạng, kết quả xác định.

Khi agent / comparison / quiz đổi cách gọi LLM, cập nhật FakeLLM ở đây cho khớp (đây là một phần hợp đồng).
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import AsyncIterator
from typing import Any

from app.ai.llm_adapter import LLMUnavailable

DEFAULT_ANSWER = (
    "Ở Nhật Bản, quà thường được trao và nhận bằng hai tay để thể hiện sự tôn trọng [c1]. "
    "Bạn cũng nên tránh tặng quà theo bộ bốn món [c2]. "
    "Ngoài ra, người Nhật luôn tặng quà vào thứ Ba [c99]."  # [c99] là trích dẫn bịa — verifier phải loại bỏ
)


class FakeLLM:
    model = "fake-llm"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail = False
        self.answer = DEFAULT_ANSWER
        self.json: dict[str, dict[str, Any]] = {
            "follow_ups": {"questions": ["Ở Nhật nên tránh những món quà nào?", "Gói quà ở Nhật có gì đặc biệt?"]},
            # Ô có "evidence": [] (không có bằng chứng) → API phải trả null ("Chưa đủ nguồn để kết luận")
            "comparison": {
                "similarities": [{"text": "Ẩm thực gắn với gia đình và lễ hội.", "evidence": ["c1"]}],
                "rows": [
                    {"aspect": "Bữa ăn gia đình", "a": {"text": "Cả nhà ăn chung mâm cơm.", "evidence": ["c1"]},
                     "b": {"text": "Bữa tối kéo dài nhiều món.", "evidence": []}},
                ],
                "context": "Bối cảnh lịch sử khác nhau.",
                "caveats": ["Khác nhau theo vùng."],
                "insufficient": [],
            },
            "quiz_drafts": {"questions": [
                {"question": "Ở Nhật, quà được trao bằng mấy tay?", "options": ["Một tay", "Hai tay"], "answerIndex": 1,
                 "explanation": "Trao bằng hai tay thể hiện sự tôn trọng [c1].", "difficulty": "easy"},
            ]},
        }

    async def _stream(self, text: str) -> AsyncIterator[str]:
        for word in re.findall(r"\S+\s*", text):
            yield word

    def stream(self, messages: list[dict[str, str]], *, temperature: float = 0.3) -> AsyncIterator[str]:
        self.calls.append({"kind": "stream", "messages": messages})
        if self.fail:
            raise LLMUnavailable("fake outage")
        return self._stream(self.answer)

    async def complete_json(self, messages: list[dict[str, str]], *, name: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"kind": "json", "name": name, "messages": messages})
        if self.fail:
            raise LLMUnavailable("fake outage")
        if name not in self.json:
            raise KeyError(f"FakeLLM chưa có kịch bản cho tác vụ '{name}' — thêm vào tests/fakes.py")
        return self.json[name]


def _norm(text: str) -> list[str]:
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.findall(r"\w+", text)


class FakeEmbedder:
    """Embedding túi từ (băm từ + cặp từ) 1024 chiều — câu cùng từ khoá sẽ gần nhau."""

    dim = 1024
    model = "fake-embedding"

    def embed_one(self, text: str) -> list[float]:
        toks = _norm(text)
        vec = [0.0] * self.dim
        for t in toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:], strict=False)]:
            vec[int(hashlib.md5(t.encode()).hexdigest(), 16) % self.dim] += 1.0
        n = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / n for v in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]


class FakeLocalAI:
    """Thay dịch vụ AI local (src/ai-local) trong test backend."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.down = False

    def _check(self) -> None:
        if self.down:
            from app.ai.local_ai import LocalAIUnavailable
            raise LocalAIUnavailable("fake: ai-local không chạy")

    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> dict[str, Any]:
        self._check()
        self.calls.append(("transcribe", len(audio)))
        if not audio.startswith(b"RIFF"):
            from app.ai.local_ai import LocalAIError
            raise LocalAIError(400, "Âm thanh không hợp lệ", "Không đọc được file âm thanh")
        return {"text": "Ở Nhật Bản tặng quà cần lưu ý gì", "segments": [{"start": 0.0, "end": 2.1, "text": "ở nhật bản tặng quà cần lưu ý gì"}],
                "duration": 2.1, "model": "fake-stt"}

    async def synthesize(self, text: str, voice: str | None) -> tuple[bytes, dict[str, str]]:
        self._check()
        if voice and voice not in {"Hải Đăng", "Thái Sơn"}:
            from app.ai.local_ai import LocalAIError
            raise LocalAIError(400, "Giọng đọc không tồn tại", voice)
        self.calls.append(("synthesize", text))
        from urllib.parse import quote  # dịch vụ thật mã hoá URL tên giọng (header chỉ nhận latin-1)
        return b"RIFF\x00\x00\x00\x00WAVEfmt ", {"x-voice": quote(voice or "Hải Đăng"), "x-audio-seconds": "1.00"}

    async def voices(self) -> dict[str, Any]:
        self._check()
        return {"default": "Hải Đăng", "voices": [{"id": "Hải Đăng", "label": "Hải Đăng — giọng Bắc"},
                                                  {"id": "Thái Sơn", "label": "Thái Sơn — giọng Nam"}]}

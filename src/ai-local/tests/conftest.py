"""Engine giả cho test nhanh (không nạp model). Test model thật: pytest -m models."""
from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ai_local.audio import STT_RATE
from ai_local.engines import Engines, EngineUnavailable
from ai_local.main import app


class FakeSTT:
    model = "fake-stt"

    def __init__(self):
        self.calls = 0

    def transcribe(self, samples):
        self.calls += 1
        return {"text": "Xin chào", "segments": [{"start": 0.0, "end": 1.0, "text": "xin chào"}],
                "duration": round(len(samples) / STT_RATE, 2), "model": self.model, "elapsedMs": 1}


class FakeTTS:
    model = "fake-tts"
    sample_rate = 24_000

    def __init__(self):
        self.last_text = None

    def voices(self):
        return [{"id": "Hải Đăng", "label": "Hải Đăng — Bắc"}, {"id": "Thái Sơn", "label": "Thái Sơn — Nam"}]

    def has_voice(self, v):
        return v in {"Hải Đăng", "Thái Sơn"}

    def synthesize(self, text, voice=None):
        from ai_local.text import clean_for_speech
        self.last_text = clean_for_speech(text)
        return np.zeros(self.sample_rate // 2 if self.last_text else 0, dtype=np.float32)


class FakeEmbed:
    model = "fake-embed"

    def embed(self, texts):
        v = np.ones((len(texts), 1024), dtype=np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)


class FakeRerank:
    model = "fake-rerank"

    def score(self, query, docs):
        return np.array([1.0 if any(w in d.lower() for w in query.lower().split()) else 0.0 for d in docs])


def _broken():
    raise RuntimeError("model file missing")


@pytest.fixture
def fakes():
    return {"stt": FakeSTT(), "tts": FakeTTS(), "embed": FakeEmbed(), "rerank": FakeRerank()}


@pytest.fixture
def client(fakes):
    app.state.engines = Engines({k: (lambda v=v: v) for k, v in fakes.items()})
    with TestClient(app) as c:
        yield c
    del app.state.engines


@pytest.fixture
def broken_client():
    app.state.engines = Engines({k: _broken for k in ("stt", "tts", "embed", "rerank")})
    with TestClient(app) as c:
        yield c
    del app.state.engines


def wav_bytes(seconds: float, rate: int = 16_000) -> bytes:
    from ai_local.audio import encode_wav
    t = np.arange(int(seconds * rate)) / rate
    return encode_wav(0.3 * np.sin(2 * np.pi * 220 * t).astype(np.float32), rate)


__all__ = ["EngineUnavailable", "wav_bytes"]

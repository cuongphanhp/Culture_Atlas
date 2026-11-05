"""Kiểm tra model thật (chậm, cần tải trước: python -m ai_local.download). Chạy: pytest -m models"""
import time

import numpy as np
import pytest

from ai_local.audio import decode_to_mono16k, encode_wav
from ai_local.engines import Engines

pytestmark = pytest.mark.models


@pytest.fixture(scope="module")
def engines():
    return Engines()


@pytest.mark.ac("AC21.1", "AC21.4")
def test_tts_then_stt_round_trip_vietnamese(engines):
    tts, stt = engines.get("tts"), engines.get("stt")
    t = time.perf_counter()
    wav = tts.synthesize("Ở Nhật Bản, quà thường được trao và nhận bằng hai tay [c1].")
    rtf = (time.perf_counter() - t) / (len(wav) / tts.sample_rate)
    assert rtf < 1.0, f"TTS chậm hơn thời gian thực (RTF {rtf:.2f})"
    r = stt.transcribe(decode_to_mono16k(encode_wav(wav, tts.sample_rate)))
    words = set(r["text"].lower().replace(",", "").split())
    assert {"nhật", "bản", "trao", "nhận", "hai", "tay"} <= words, r["text"]
    assert r["elapsedMs"] < 2000


def test_embedding_cross_lingual(engines):
    v = engines.get("embed").embed(["Người Nhật đưa quà như thế nào?", "Gifts in Japan are presented with both hands.",
                                    "Lì xì ở Việt Nam đựng trong phong bao đỏ."])
    assert v.shape == (3, 1024) and np.allclose(np.linalg.norm(v, axis=1), 1, atol=1e-3)
    assert v[1] @ v[0] > v[2] @ v[0]


def test_rerank_orders_relevant_first(engines):
    s = engines.get("rerank").score("Người Nhật đưa quà như thế nào?",
                                    ["Lì xì ở Việt Nam đựng trong phong bao đỏ.", "Ở Nhật Bản, quà được trao bằng hai tay."])
    assert s[1] > 0.5 > s[0]

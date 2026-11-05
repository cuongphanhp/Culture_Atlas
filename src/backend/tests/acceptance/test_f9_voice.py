"""F9 — Hỏi đáp bằng giọng nói (US21). Âm thanh xử lý ở dịch vụ AI local; test dùng FakeLocalAI."""
import io
import wave

import pytest

from tests.conftest import ac, assert_problem, route

pytestmark = pytest.mark.db


def wav(seconds: float = 1.0) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buf.getvalue()


@route("POST", "/api/ai/transcribe")
@ac("AC21.1")
def test_transcribe_returns_vietnamese_text(client, fake_local_ai):
    r = client.post("/api/ai/transcribe", files={"file": ("question.webm", wav(), "audio/webm")})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "Ở Nhật Bản tặng quà cần lưu ý gì" and body["segments"] and body["durationS"] == 2.1
    assert fake_local_ai.calls[0][0] == "transcribe", "âm thanh phải được xử lý bởi dịch vụ AI local"


@route("POST", "/api/ai/transcribe")
@ac("AC21.2")
def test_transcribe_rejects_bad_audio(client):
    assert_problem(client.post("/api/ai/transcribe", files={"file": ("x.txt", b"hello", "text/plain")}), 400)
    assert_problem(client.post("/api/ai/transcribe", files={"file": ("e.wav", b"", "audio/wav")}), 400)


@route("POST", "/api/ai/transcribe")
@ac("AC21.2")
def test_transcribe_rejects_oversized_upload(client):
    big = b"RIFF" + b"\x00" * (10 * 1024 * 1024 + 10)
    assert_problem(client.post("/api/ai/transcribe", files={"file": ("big.wav", big, "audio/wav")}), 413)


@route("POST", "/api/ai/transcribe")
@ac("AC21.3")
def test_audio_is_not_stored(client, db):
    client.post("/api/ai/transcribe", files={"file": ("q.wav", wav(), "audio/wav")})
    cols = {r[0] for r in db.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public'")}
    assert not {c for c in cols if "audio" in c or "voice" in c}, "DB không được có cột lưu âm thanh"


@route("POST", "/api/ai/speech")
@ac("AC21.4")
def test_speech_returns_wav(client, fake_local_ai):
    r = client.post("/api/ai/speech", json={"text": "Ở Nhật Bản, quà trao bằng hai tay [c1].", "voice": "Thái Sơn"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content.startswith(b"RIFF")
    assert fake_local_ai.calls[-1] == ("synthesize", "Ở Nhật Bản, quà trao bằng hai tay [c1].")


@route("POST", "/api/ai/speech")
@ac("AC21.4")
def test_speech_validation(client):
    assert_problem(client.post("/api/ai/speech", json={"text": "Xin chào", "voice": "Không tồn tại"}), 400)
    assert_problem(client.post("/api/ai/speech", json={"text": ""}), 400)
    assert_problem(client.post("/api/ai/speech", json={"text": "x" * 1501}), 413)


@route("GET", "/api/ai/voices")
@ac("AC21.4")
def test_voices_include_north_and_south(client):
    v = client.get("/api/ai/voices").json()
    labels = " ".join(x["label"] for x in v["voices"])
    assert v["default"] and "Bắc" in labels and "Nam" in labels


@route("POST", "/api/ai/transcribe")
@route("POST", "/api/ai/speech")
@ac("AC21.5")
def test_local_ai_down_returns_503(client, fake_local_ai):
    fake_local_ai.down = True
    assert_problem(client.post("/api/ai/transcribe", files={"file": ("q.wav", wav(), "audio/wav")}), 503)
    assert_problem(client.post("/api/ai/speech", json={"text": "Xin chào"}), 503)
    assert client.get("/api/health").status_code == 200, "phần còn lại của app vẫn hoạt động"

"""API dịch vụ AI local với engine giả — chạy nhanh, không cần model."""
from urllib.parse import unquote

import pytest

from tests.conftest import wav_bytes


@pytest.mark.ac("AC21.3")
def test_uploaded_audio_is_not_kept_on_disk(client, tmp_path, monkeypatch):
    """File tạm chứa âm thanh người dùng bị xoá ngay sau khi giải mã."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    client.post("/v1/stt", files={"file": ("q.wav", wav_bytes(1.0), "audio/wav")})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.ac("AC21.2")
def test_oversized_upload_rejected(client):
    big = b"RIFF" + b"0" * (10 * 1024 * 1024 + 1)
    assert client.post("/v1/stt", files={"file": ("big.wav", big, "audio/wav")}).status_code == 413


def is_problem(r, status):
    assert r.status_code == status, r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    return r.json()


def test_health_reports_loaded_models(client):
    assert client.get("/health").json()["loaded"] == {"stt": False, "tts": False, "embed": False, "rerank": False}


def test_stt_any_format_decoded_and_transcribed(client, fakes):
    r = client.post("/v1/stt", files={"file": ("q.wav", wav_bytes(1.5), "audio/wav")})
    assert r.status_code == 200
    assert r.json()["text"] == "Xin chào" and r.json()["duration"] == 1.5
    assert fakes["stt"].calls == 1


def test_stt_rejects_non_audio(client):
    is_problem(client.post("/v1/stt", files={"file": ("x.txt", b"khong phai am thanh", "text/plain")}), 400)


def test_stt_rejects_too_long(client):
    body = is_problem(client.post("/v1/stt", files={"file": ("long.wav", wav_bytes(61), "audio/wav")}), 413)
    assert "60" in body["detail"]


def test_stt_rejects_empty(client):
    is_problem(client.post("/v1/stt", files={"file": ("e.wav", b"", "audio/wav")}), 400)


def test_tts_returns_wav_and_strips_citations(client, fakes):
    r = client.post("/v1/tts", json={"text": "Ở Nhật, quà trao bằng **hai tay** [c1].", "voice": "Thái Sơn"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    assert r.content[:4] == b"RIFF" and unquote(r.headers["X-Voice"]) == "Thái Sơn"
    assert fakes["tts"].last_text == "Ở Nhật, quà trao bằng hai tay."


def test_tts_unknown_voice_and_limits(client):
    is_problem(client.post("/v1/tts", json={"text": "Xin chào", "voice": "Không có"}), 400)
    is_problem(client.post("/v1/tts", json={"text": "x" * 1501}), 413)
    is_problem(client.post("/v1/tts", json={"text": ""}), 400)
    is_problem(client.post("/v1/tts", json={"text": "[c1] [c2]"}), 400)


def test_voices(client):
    v = client.get("/v1/voices").json()
    assert v["default"] and {x["id"] for x in v["voices"]} == {"Hải Đăng", "Thái Sơn"}


def test_embed_and_rerank(client):
    e = client.post("/v1/embed", json={"texts": ["a", "b"]}).json()
    assert e["dim"] == 1024 and len(e["vectors"]) == 2
    r = client.post("/v1/rerank", json={"query": "nhật", "documents": ["Việt Nam", "Nhật Bản"], "top_k": 1}).json()
    assert r["results"] == [{"index": 1, "score": 1.0}]
    is_problem(client.post("/v1/embed", json={"texts": []}), 400)


def test_model_failure_returns_503(broken_client):
    body = is_problem(broken_client.post("/v1/tts", json={"text": "Xin chào"}), 503)
    assert "tts" in body["detail"]

"""Giải mã / mã hoá âm thanh. Âm thanh người dùng chỉ nằm trong file tạm và bị xoá ngay sau khi giải mã."""
from __future__ import annotations

import io
import subprocess
import tempfile

import numpy as np
import soundfile as sf

STT_RATE = 16_000


class AudioError(ValueError):
    """File không phải âm thanh hợp lệ."""


def decode_to_mono16k(data: bytes) -> np.ndarray:
    """Mọi định dạng ffmpeg đọc được (webm/opus từ trình duyệt, m4a, mp3, wav…) → float32 mono 16 kHz."""
    if not data:
        raise AudioError("File âm thanh rỗng")
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=True) as tmp:   # xoá ngay khi ra khỏi khối
        tmp.write(data)
        tmp.flush()
        proc = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", tmp.name,
             "-f", "f32le", "-ac", "1", "-ar", str(STT_RATE), "pipe:1"],
            capture_output=True, check=False, timeout=60,
        )
    if proc.returncode != 0 or not proc.stdout:
        raise AudioError("Không đọc được file âm thanh")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def encode_wav(samples: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.clip(samples, -1.0, 1.0), rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()

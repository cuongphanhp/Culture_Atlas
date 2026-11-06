"""Giải mã / mã hoá âm thanh bằng PyAV (thư viện ffmpeg đóng gói sẵn — không cần cài ffmpeg hệ thống).
Âm thanh người dùng chỉ nằm trong bộ nhớ: không ghi ra đĩa (AC21.3)."""
from __future__ import annotations

import io

import av
import numpy as np
import soundfile as sf

STT_RATE = 16_000


class AudioError(ValueError):
    """File không phải âm thanh hợp lệ."""


def decode_to_mono16k(data: bytes) -> np.ndarray:
    """Mọi định dạng ffmpeg đọc được (webm/opus từ trình duyệt, ogg, m4a, mp3, wav…) → float32 mono 16 kHz."""
    if not data:
        raise AudioError("File âm thanh rỗng")
    try:
        with av.open(io.BytesIO(data), mode="r") as container:
            if not container.streams.audio:
                raise AudioError("File không có kênh âm thanh")
            resampler = av.AudioResampler(format="flt", layout="mono", rate=STT_RATE)
            chunks = []
            for frame in container.decode(audio=0):
                for out in resampler.resample(frame):
                    chunks.append(out.to_ndarray().reshape(-1))
            for out in resampler.resample(None):          # xả phần còn lại trong bộ đệm
                chunks.append(out.to_ndarray().reshape(-1))
    except AudioError:
        raise
    except (av.FFmpegError, ValueError, IndexError) as e:
        raise AudioError("Không đọc được file âm thanh") from e
    if not chunks:
        raise AudioError("Không đọc được file âm thanh")
    return np.concatenate(chunks).astype(np.float32, copy=False)


def encode_wav(samples: np.ndarray, rate: int) -> bytes:
    """Mẫu float [-1, 1] → WAV PCM 16-bit (trong bộ nhớ, không ghi đĩa)."""
    buf = io.BytesIO()
    sf.write(buf, np.clip(samples, -1.0, 1.0), rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()

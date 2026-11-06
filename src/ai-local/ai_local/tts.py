"""Đọc văn bản tiếng Việt: VieNeu-TTS v3 Turbo (ONNX/CPU, 48 kHz, giọng Bắc & Nam). Có sẵn chuẩn hoá số, ngày tháng (sea-g2p)."""
from __future__ import annotations

import numpy as np

from ai_local.text import clean_for_speech


class VieneuTTS:
    """Đọc tiếng Việt bằng VieNeu-TTS v3 Turbo (giọng có sẵn, chạy CPU)."""

    model = "VieNeu-TTS-v3-Turbo"

    def __init__(self, threads: int, precision: str, default_voice: str) -> None:
        from vieneu import Vieneu
        self.engine = Vieneu(threads=threads, precision=precision)
        self.sample_rate = self.engine.sample_rate
        self.default_voice = default_voice

    def voices(self) -> list[dict[str, str]]:
        """Danh sách giọng [{id, label}]."""
        return [{"id": vid, "label": label} for label, vid in self.engine.list_preset_voices()]

    def has_voice(self, voice: str) -> bool:
        """Giọng có tồn tại không."""
        return self.engine.resolve_voice_name(voice) is not None

    def synthesize(self, text: str, voice: str | None = None) -> np.ndarray:
        """Văn bản (đã làm sạch markdown / trích dẫn) → mẫu float32; rỗng nếu không còn gì để đọc."""
        speech = clean_for_speech(text)
        if not speech:
            return np.zeros(0, dtype=np.float32)
        return np.asarray(self.engine.infer(speech, voice=voice or self.default_voice), dtype=np.float32)

"""Nhận dạng giọng nói tiếng Việt: silero VAD cắt đoạn → Gipformer 1.5 (Zipformer RNN-T, ONNX) qua sherpa-onnx."""
from __future__ import annotations

import time

import numpy as np
import sherpa_onnx

from ai_local.audio import STT_RATE
from ai_local.text import tidy_transcript


class GipformerSTT:
    model = "gipformer1.5-68M-rnnt"

    def __init__(self, paths: dict[str, str], threads: int, decoding: str, max_seconds: float) -> None:
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=paths["encoder"], decoder=paths["decoder"], joiner=paths["joiner"], tokens=paths["tokens"],
            num_threads=threads, sample_rate=STT_RATE, feature_dim=80, decoding_method=decoding)
        cfg = sherpa_onnx.VadModelConfig()
        cfg.silero_vad.model = paths["vad"]
        cfg.silero_vad.threshold = 0.5
        cfg.silero_vad.min_silence_duration = 0.35
        cfg.silero_vad.min_speech_duration = 0.2
        cfg.silero_vad.max_speech_duration = 20
        cfg.sample_rate = STT_RATE
        cfg.num_threads = 1
        self.vad_cfg = cfg
        self.max_seconds = max_seconds

    def _segments(self, samples: np.ndarray) -> list[tuple[float, np.ndarray]]:
        vad = sherpa_onnx.VoiceActivityDetector(self.vad_cfg, buffer_size_in_seconds=self.max_seconds + 10)
        win = self.vad_cfg.silero_vad.window_size
        for i in range(0, len(samples), win):
            vad.accept_waveform(samples[i:i + win])
        vad.flush()
        out = []
        while not vad.empty():
            seg = vad.front
            out.append((seg.start / STT_RATE, np.asarray(seg.samples, dtype=np.float32)))
            vad.pop()
        return out

    def transcribe(self, samples: np.ndarray) -> dict:
        t0 = time.perf_counter()
        segs = self._segments(samples)
        streams = []
        for _, s in segs:
            st = self.recognizer.create_stream()
            st.accept_waveform(STT_RATE, s)
            streams.append(st)
        if streams:
            self.recognizer.decode_streams(streams)
        items = [{"start": round(start, 2), "end": round(start + len(s) / STT_RATE, 2), "text": st.result.text.strip()}
                 for (start, s), st in zip(segs, streams, strict=True) if st.result.text.strip()]
        return {
            "text": tidy_transcript(" ".join(i["text"] for i in items)),
            "segments": items,
            "duration": round(len(samples) / STT_RATE, 2),
            "model": self.model,
            "elapsedMs": int((time.perf_counter() - t0) * 1000),
        }

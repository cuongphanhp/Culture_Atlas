"""Nạp model lười (lần gọi đầu) và dùng chung cho mọi request. Test thay bằng engine giả qua `app.state.engines`."""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from ai_local.config import settings


def _stt() -> Any:
    """Gipformer STT (ONNX)."""
    from ai_local.download import stt as fetch
    from ai_local.stt import GipformerSTT
    return GipformerSTT(fetch(), settings.threads, settings.stt_decoding, settings.max_audio_seconds)


def _tts() -> Any:
    """VieNeu TTS."""
    from ai_local.hfcache import materialize_all
    from ai_local.tts import VieneuTTS
    materialize_all()
    return VieneuTTS(settings.threads, settings.tts_precision, settings.tts_voice)


def _embed() -> Any:
    """Embedding AITeamVN (ONNX)."""
    from ai_local.download import embed as fetch
    from ai_local.embed import OnnxEmbedder
    from ai_local.hfcache import materialize_all
    path = fetch()
    materialize_all()
    return OnnxEmbedder(path, settings.embed_repo, settings.threads, settings.embed_max_tokens)


def _rerank() -> Any:
    """Reranker AITeamVN (ONNX int8)."""
    from ai_local.download import embed_tokenizer
    from ai_local.download import rerank as fetch
    from ai_local.rerank import OnnxReranker
    return OnnxReranker(fetch(), embed_tokenizer(), settings.rerank_repo, settings.threads, settings.rerank_max_tokens)


FACTORIES: dict[str, Callable[[], Any]] = {"stt": _stt, "tts": _tts, "embed": _embed, "rerank": _rerank}


class EngineUnavailable(RuntimeError):
    """Model không nạp được (thiếu file, hết bộ nhớ…) → API trả 503."""


class Engines:
    """Kho model: nạp lười, mỗi model một khoá để hai request đầu không nạp trùng."""

    def __init__(self, factories: dict[str, Callable[[], Any]] | None = None) -> None:
        self.factories = factories or FACTORIES
        self._loaded: dict[str, Any] = {}
        self._locks = {k: threading.Lock() for k in self.factories}

    def get(self, name: str) -> Any:
        """Model `name` (stt | tts | embed | rerank), nạp ở lần gọi đầu; lỗi → EngineUnavailable."""
        if name in self._loaded:
            return self._loaded[name]
        with self._locks[name]:
            if name not in self._loaded:
                try:
                    self._loaded[name] = self.factories[name]()
                except Exception as e:
                    raise EngineUnavailable(f"Không nạp được model '{name}': {e}") from e
        return self._loaded[name]

    def status(self) -> dict[str, bool]:
        """Model nào đã nạp."""
        return {k: k in self._loaded for k in self.factories}

    def preload(self) -> None:
        """Nạp sẵn mọi model (AI_LOCAL_PRELOAD=1) để request đầu không phải chờ."""
        for k in self.factories:
            self.get(k)

"""Nạp model lười (lần gọi đầu) và dùng chung cho mọi request. Test thay bằng engine giả qua `app.state.engines`."""
from __future__ import annotations

import threading
from typing import Any, Callable

from ai_local.config import settings


def _stt():
    from ai_local.download import stt as fetch
    from ai_local.stt import GipformerSTT
    return GipformerSTT(fetch(), settings.threads, settings.stt_decoding, settings.max_audio_seconds)


def _tts():
    from ai_local.hfcache import materialize_all
    from ai_local.tts import VieneuTTS
    materialize_all()
    return VieneuTTS(settings.threads, settings.tts_precision, settings.tts_voice)


def _embed():
    from ai_local.download import embed as fetch
    from ai_local.embed import OnnxEmbedder
    from ai_local.hfcache import materialize_all
    path = fetch()
    materialize_all()
    return OnnxEmbedder(path, settings.embed_repo, settings.threads, settings.embed_max_tokens)


def _rerank():
    from pathlib import Path

    from ai_local.download import embed as fetch_embed
    from ai_local.download import rerank as fetch
    from ai_local.rerank import CrossEncoderReranker
    tokenizer = str(Path(fetch_embed()) / "onnx" / "tokenizer.json")
    return CrossEncoderReranker(fetch(), settings.rerank_repo, settings.threads, settings.rerank_max_tokens, tokenizer)


FACTORIES: dict[str, Callable[[], Any]] = {"stt": _stt, "tts": _tts, "embed": _embed, "rerank": _rerank}


class EngineUnavailable(RuntimeError):
    pass


class Engines:
    def __init__(self, factories: dict[str, Callable[[], Any]] | None = None) -> None:
        self.factories = factories or FACTORIES
        self._loaded: dict[str, Any] = {}
        self._locks = {k: threading.Lock() for k in self.factories}

    def get(self, name: str) -> Any:
        if name in self._loaded:
            return self._loaded[name]
        with self._locks[name]:
            if name not in self._loaded:
                try:
                    self._loaded[name] = self.factories[name]()
                except Exception as e:  # noqa: BLE001
                    raise EngineUnavailable(f"Không nạp được model '{name}': {e}") from e
        return self._loaded[name]

    def status(self) -> dict[str, bool]:
        return {k: k in self._loaded for k in self.factories}

    def preload(self) -> None:
        for k in self.factories:
            self.get(k)

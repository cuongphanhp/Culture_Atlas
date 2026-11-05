"""Tải trước toàn bộ model (chạy một lần, hoặc khi build image):  python -m ai_local.download [stt tts embed rerank]"""
from __future__ import annotations

import sys
import time
import urllib.request

from huggingface_hub import hf_hub_download, snapshot_download

from ai_local.config import settings
from ai_local.hfcache import materialize_all

STT_FILES = ["encoder.{q}.onnx", "decoder.{q}.onnx", "joiner.{q}.onnx", "tokens.txt"]


def vad_path():
    p = settings.models_dir / "silero_vad.onnx"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(settings.vad_url, p)
    return p


def stt() -> dict[str, str]:
    q = settings.stt_quantize
    files = [f.replace(".{q}", "" if q == "fp32" else f".{q}") for f in STT_FILES]
    paths = {f.split(".")[0]: hf_hub_download(settings.stt_repo, f) for f in files}
    paths["vad"] = str(vad_path())
    return paths


def embed() -> str:
    return snapshot_download(settings.embed_repo, allow_patterns=["onnx/*"])


def rerank() -> str:
    return snapshot_download(settings.rerank_repo)


def tts() -> None:
    from vieneu import Vieneu
    try:
        Vieneu(precision=settings.tts_precision)   # lần đầu sẽ tải model v3 Turbo + codec về cache
    except Exception:  # noqa: BLE001 — file đã tải nhưng đang là symlink → onnxruntime từ chối
        materialize_all()
        Vieneu(precision=settings.tts_precision)


STEPS = {"stt": stt, "embed": embed, "rerank": rerank, "tts": tts}

if __name__ == "__main__":
    for name in sys.argv[1:] or list(STEPS):
        t = time.time()
        print(f"▶ {name} …", flush=True)
        STEPS[name]()
        materialize_all()
        print(f"✔ {name} ({time.time() - t:.0f}s)", flush=True)

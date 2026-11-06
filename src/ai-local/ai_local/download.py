"""Tải trước toàn bộ model (chạy một lần):  python -m ai_local.download [stt tts embed rerank]

Reranker gốc chỉ có trọng số safetensors → bước `rerank` xuất sang ONNX rồi lượng tử hoá int8 (~4 lần nhỏ hơn).
Bước này cần torch + transformers + onnx (extra [export], có sẵn trong image Docker `setup`).
Lúc chạy dịch vụ chỉ cần file ONNX — image runtime không có torch."""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

from ai_local.config import settings
from ai_local.hfcache import materialize_all

STT_FILES = ["encoder.{q}.onnx", "decoder.{q}.onnx", "joiner.{q}.onnx", "tokens.txt"]


def vad_path() -> Path:
    """File Silero VAD (cắt đoạn lặng cho STT); tải về models_dir nếu chưa có."""
    p = settings.models_dir / "silero_vad.onnx"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(settings.vad_url, p)
    return p


def stt() -> dict[str, str]:
    """Tải các file ONNX của Gipformer theo mức lượng tử hoá → {encoder, decoder, joiner, tokens, vad}."""
    q = settings.stt_quantize
    files = [f.replace(".{q}", "" if q == "fp32" else f".{q}") for f in STT_FILES]
    paths = {f.split(".")[0]: hf_hub_download(settings.stt_repo, f) for f in files}
    paths["vad"] = str(vad_path())
    return paths


def embed() -> str:
    """Tải bản ONNX của model embedding AITeamVN → thư mục snapshot."""
    return snapshot_download(settings.embed_repo, allow_patterns=["onnx/*"])


def embed_tokenizer() -> str:
    """tokenizer.json dùng chung cho embedding và rerank."""
    return str(Path(embed()) / "onnx" / "tokenizer.json")


def rerank_onnx_path() -> Path:
    """Vị trí file ONNX int8 của reranker (xuất một lần ở target setup của Dockerfile)."""
    return settings.models_dir / "reranker-onnx" / "model.int8.onnx"


def rerank() -> str:
    """Trả về đường dẫn ONNX int8 của reranker; nếu chưa có thì xuất từ safetensors (cần extra [export])."""
    out = rerank_onnx_path()
    if out.exists():
        return str(out)
    try:
        import torch
        from onnxruntime.quantization import QuantType, quantize_dynamic
        from transformers import AutoModelForSequenceClassification
    except ImportError as e:
        raise RuntimeError("Chưa có reranker ONNX. Chạy bước tải model bằng image/extra có torch: "
                           "`docker compose run --rm ai-local-setup` hoặc `pip install -e '.[export]'`") from e
    from tokenizers import Tokenizer

    src = snapshot_download(settings.rerank_repo)
    tmp = out.parent / "fp32"
    tmp.mkdir(parents=True, exist_ok=True)
    fp32 = tmp / "model.onnx"
    model = AutoModelForSequenceClassification.from_pretrained(src).eval()
    tok = Tokenizer.from_file(embed_tokenizer())
    enc = tok.encode("câu hỏi", "đoạn văn bản mẫu")
    ids = torch.tensor([enc.ids], dtype=torch.long)
    mask = torch.tensor([enc.attention_mask], dtype=torch.long)
    with torch.inference_mode():
        torch.onnx.export(
            model, (ids, mask), str(fp32), input_names=["input_ids", "attention_mask"], output_names=["logits"],
            dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}, "logits": {0: "batch"}},
            opset_version=17, dynamo=False)
    quantize_dynamic(str(fp32), str(out), weight_type=QuantType.QInt8, use_external_data_format=False)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return str(out)


def tts() -> None:
    """Tải model VieNeu-TTS v3 Turbo + codec về cache Hugging Face (lần đầu)."""
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

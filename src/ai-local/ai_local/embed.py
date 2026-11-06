"""Embedding tiếng Việt: Vietnamese_Embedding_v2 (XLM-R/BGE-M3, ONNX) — lấy CLS rồi chuẩn hoá L2, 1024 chiều."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


class OnnxEmbedder:
    """Embedding tiếng Việt (AITeamVN, 1024 chiều) chạy bằng onnxruntime trên CPU, không cần torch."""

    def __init__(self, model_dir: str, name: str, threads: int, max_tokens: int) -> None:
        d = Path(model_dir) / "onnx"
        self.tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        self.tok.enable_truncation(max_length=max_tokens)
        self.tok.enable_padding(pad_id=self.tok.token_to_id("<pad>") or 1, pad_token="<pad>")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        self.sess = ort.InferenceSession(str(d / "model.onnx"), opts, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.model = name
        self.dim = 1024

    def embed(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        """Văn bản → ma trận (n, 1024) đã chuẩn hoá L2 (cosine = tích vô hướng)."""
        out = []
        for i in range(0, len(texts), batch_size):
            enc = self.tok.encode_batch(texts[i:i + batch_size])
            feed = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                    "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64)}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
            hidden = self.sess.run(None, {k: v for k, v in feed.items() if k in self.inputs})[0]
            cls = hidden[:, 0, :] if hidden.ndim == 3 else hidden
            out.append(cls / np.linalg.norm(cls, axis=1, keepdims=True).clip(min=1e-12))
        return np.concatenate(out) if out else np.zeros((0, self.dim), dtype=np.float32)

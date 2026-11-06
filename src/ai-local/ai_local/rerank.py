"""Rerank tiếng Việt: Vietnamese_Reranker (cross-encoder gốc bge-reranker-v2-m3) chạy bằng ONNX Runtime — không cần torch.
Model gốc chỉ có safetensors → xuất sang ONNX + lượng tử hoá int8 một lần bằng `python -m ai_local.download rerank`
(cần extra [export]); lúc chạy chỉ dùng file ONNX. Điểm 0..1 (sigmoid)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


class OnnxReranker:
    """Cross-encoder AITeamVN (ONNX int8) chấm độ liên quan câu hỏi–đoạn; chạy CPU, không cần torch."""

    def __init__(self, onnx_path: str, tokenizer_file: str, name: str, threads: int, max_tokens: int) -> None:
        self.tok = Tokenizer.from_file(tokenizer_file)
        self.tok.enable_truncation(max_length=max_tokens, strategy="only_second")
        self.tok.enable_padding(pad_id=self.tok.token_to_id("<pad>") or 1, pad_token="<pad>")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        self.sess = ort.InferenceSession(str(Path(onnx_path)), opts, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.model = name

    def score(self, query: str, documents: list[str], batch_size: int = 16) -> np.ndarray:
        """Điểm liên quan (sigmoid, 0–1) cho từng đoạn, theo thứ tự đầu vào."""
        scores = []
        for i in range(0, len(documents), batch_size):
            enc = self.tok.encode_batch([(query, d) for d in documents[i:i + batch_size]])
            feed = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                    "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64)}
            logits = self.sess.run(None, {k: v for k, v in feed.items() if k in self.inputs})[0].reshape(-1)
            scores.append(1.0 / (1.0 + np.exp(-logits)))
        return np.concatenate(scores).astype(np.float32) if scores else np.zeros(0, dtype=np.float32)

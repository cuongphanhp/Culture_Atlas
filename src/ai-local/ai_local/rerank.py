"""Rerank tiếng Việt: Vietnamese_Reranker (cross-encoder gốc bge-reranker-v2-m3) — điểm 0..1 (sigmoid)."""
from __future__ import annotations

import numpy as np


class CrossEncoderReranker:
    def __init__(self, model_dir: str, name: str, threads: int, max_tokens: int, tokenizer_file: str) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, PreTrainedTokenizerFast
        torch.set_num_threads(threads)
        self.torch = torch
        # Repo reranker không kèm tokenizer.json; dùng tokenizer XLM-R (cùng từ vựng 250k) của model embedding
        self.tok = PreTrainedTokenizerFast(tokenizer_file=tokenizer_file, bos_token="<s>", eos_token="</s>",
                                           sep_token="</s>", cls_token="<s>", unk_token="<unk>", pad_token="<pad>",
                                           mask_token="<mask>")
        self.net = AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
        self.max_tokens = max_tokens
        self.model = name

    def score(self, query: str, documents: list[str], batch_size: int = 8) -> np.ndarray:
        scores = []
        with self.torch.inference_mode():
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                enc = self.tok([query] * len(batch), batch, padding=True, truncation="only_second",
                               max_length=self.max_tokens, return_tensors="pt")
                scores.append(self.torch.sigmoid(self.net(**enc).logits.view(-1).float()).numpy())
        return np.concatenate(scores) if scores else np.zeros(0, dtype=np.float32)

"""onnxruntime ≥ 1.2x từ chối file trọng số ngoài (model.onnx_data…) nếu đường dẫn thật nằm ngoài thư mục model.
Cache Hugging Face dùng symlink snapshot → blobs/, nên ta thay symlink bằng hardlink (không tốn thêm dung lượng)."""
from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub.constants import HF_HUB_CACHE

ONNX_REPOS = [
    "pnnbao-ump/VieNeu-TTS-v3-Turbo",
    "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX",
    "AITeamVN/Vietnamese_Embedding_v2",
    "g-group-ai-lab/gipformer1.5-68M-rnnt",
]


def materialize(repo_id: str) -> int:
    root = Path(HF_HUB_CACHE) / f"models--{repo_id.replace('/', '--')}" / "snapshots"
    n = 0
    for p in root.rglob("*") if root.exists() else []:
        if p.is_symlink():
            target = p.resolve()
            tmp = p.with_name(p.name + ".tmp-link")
            try:
                os.link(target, tmp)          # hardlink cùng ổ đĩa
            except OSError:
                import shutil
                shutil.copy2(target, tmp)     # khác ổ đĩa → sao chép
            os.replace(tmp, p)
            n += 1
    return n


def materialize_all() -> int:
    return sum(materialize(r) for r in ONNX_REPOS)

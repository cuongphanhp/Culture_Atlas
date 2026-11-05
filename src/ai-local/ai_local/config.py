"""Cấu hình đọc từ biến môi trường (tiền tố AI_LOCAL_)."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_LOCAL_", env_file=None)

    models_dir: Path = Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "ai-local"
    threads: int = max(2, (os.cpu_count() or 4) // 2)
    preload: bool = False                      # tải sẵn mọi model khi khởi động (production nên bật)

    # Nhận dạng giọng nói — Gipformer 1.5 (Zipformer RNN-T, MIT) chạy bằng sherpa-onnx
    stt_repo: str = "g-group-ai-lab/gipformer1.5-68M-rnnt"
    stt_quantize: str = "int8"                 # int8 | fp32
    stt_decoding: str = "modified_beam_search"
    vad_url: str = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
    max_audio_seconds: float = 60.0
    max_upload_mb: float = 10.0

    # Đọc văn bản — VieNeu-TTS v3 Turbo (Apache-2.0, ONNX, 48 kHz)
    tts_voice: str = "Hải Đăng"
    tts_precision: str = "int8"                # int8 cần CPU có VNNI (Core Ultra có avx_vnni); fp32 nếu không
    max_tts_chars: int = 1500

    # Embedding — Vietnamese_Embedding_v2 (gốc BGE-M3, 1024 chiều, CLS + chuẩn hoá L2)
    embed_repo: str = "AITeamVN/Vietnamese_Embedding_v2"
    embed_max_tokens: int = 2048
    # Rerank — Vietnamese_Reranker (gốc bge-reranker-v2-m3)
    rerank_repo: str = "AITeamVN/Vietnamese_Reranker"
    rerank_max_tokens: int = 1024            # chunk của kho ngắn; giảm để nhanh trên CPU (tối đa 2304)


settings = Settings()

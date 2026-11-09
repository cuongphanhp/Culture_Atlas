"""Cấu hình từ biến môi trường / file .env ở gốc repo (pydantic-settings). Biến môi trường luôn ưu tiên hơn .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PARENTS = Path(__file__).resolve().parents
# .env ở gốc repo khi chạy từ mã nguồn; trong Docker (/app/app/core) không có cấp đó → chỉ dùng biến môi trường
REPO_ENV = _PARENTS[4] / ".env" if len(_PARENTS) > 4 else Path("/nonexistent/.env")
ALLOWED_LLM_MODELS = {"gpt-6-luna", "gpt-4o"}   # quyết định của chủ dự án — không thêm model khác khi chưa được đồng ý


class Settings(BaseSettings):
    """Mọi cấu hình của API; tên biến môi trường = tên trường viết hoa (vd. LLM_MODEL). Mẫu: .env.example."""

    model_config = SettingsConfigDict(env_file=REPO_ENV if REPO_ENV.exists() else None, extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql+asyncpg://atlas:atlas@localhost:5432/culture_atlas"
    jwt_secret: str = "change-me"          # ≥ 32 byte, nếu không thì đăng nhập trả 503 (app/core/security.py)
    jwt_ttl_minutes: int = 60
    guest_daily_limit: int = 10

    # LLM — chỉ OpenAI: GPT-6 Luna (chính) + GPT-4o (dự phòng). Xem docs/11-vietnamese-chat-stack.md
    llm_provider: str = "openai"
    openai_api_key: str = ""
    llm_model: str = "gpt-6-luna"
    llm_fallback_model: str = "gpt-4o"      # dùng khi model chính lỗi mạng / quá tải; để trống = tắt
    llm_reasoning_effort: str = "none"      # cho model suy luận (Luna): none | low | medium | high
    llm_temperature: float = 0.4            # cho GPT-4o (Luna chỉ nhận mặc định)
    llm_timeout_s: float = 30.0

    # Dịch vụ AI local (src/ai-local): STT, TTS, embedding, rerank
    ai_local_url: str = "http://localhost:8100"
    ai_local_timeout_s: float = 60.0
    voice_max_upload_mb: float = 10.0
    voice_max_tts_chars: int = 1500

    # Lưu trữ: embedding → Qdrant; ảnh/video/file → object storage S3 (MinIO); văn bản + metadata → PostgreSQL
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "culture_chunks"
    s3_endpoint: str = ""
    media_public_base: str = "/media"

    # AI Guide (RAG)
    rag_pool: int = 24                 # số đoạn ứng viên lấy từ mỗi kiểu tìm (vector / từ khoá) trước khi rerank
    rag_min_rerank: float = 0.08       # ngưỡng liên quan sau rerank (sigmoid 0..1)
    rag_min_cosine: float = 0.45       # ngưỡng dự phòng khi dịch vụ rerank không chạy
    rerank_max_candidates: int = 16    # rerank (cross-encoder trên CPU) là bước chậm nhất → giới hạn số ứng viên
    rerank_doc_chars: int = 500        # cắt ngắn đoạn khi chấm rerank (đoạn đầy đủ vẫn đưa vào prompt)
    rag_strong_score: float = 0.5      # câu gốc đã cho bằng chứng mạnh → bỏ qua bước viết lại truy vấn (nhanh hơn)
    chat_history_turns: int = 3        # số lượt hỏi–đáp trước đưa vào ngữ cảnh hội thoại

    @field_validator("llm_model", mode="before")
    @classmethod
    def _model(cls, v: str | None) -> str:
        v = v or "gpt-6-luna"          # LLM_MODEL= để trống → model chính mặc định
        if v not in ALLOWED_LLM_MODELS:
            raise ValueError(f"LLM_MODEL={v} không được phép. Chỉ dùng: {', '.join(sorted(ALLOWED_LLM_MODELS))}")
        return v

    @field_validator("llm_fallback_model", mode="before")
    @classmethod
    def _fallback(cls, v: str | None) -> str:
        if v and v not in ALLOWED_LLM_MODELS:
            raise ValueError(f"LLM_FALLBACK_MODEL={v} không được phép. Chỉ dùng: {', '.join(sorted(ALLOWED_LLM_MODELS))}")
        return v or ""


@lru_cache
def get_settings() -> Settings:
    """Cấu hình đọc một lần cho cả tiến trình (test xoá cache bằng get_settings.cache_clear())."""
    return Settings()

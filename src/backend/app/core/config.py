"""Cấu hình từ biến môi trường / file .env ở gốc repo (pydantic-settings). Biến môi trường luôn ưu tiên hơn .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ENV = Path(__file__).resolve().parents[4] / ".env"
ALLOWED_LLM_MODELS = {"gpt-6-luna", "gpt-4o"}   # quyết định của chủ dự án — không thêm model khác khi chưa được đồng ý


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ENV if REPO_ENV.exists() else None, extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql+asyncpg://atlas:atlas@localhost:5432/culture_atlas"
    jwt_secret: str = "change-me"
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
    return Settings()

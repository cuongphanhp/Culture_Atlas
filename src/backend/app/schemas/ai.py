"""Schema của AI API (xem docs/api/openapi.yaml: ChatRequest, ChatAnswer, Citation)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CategoryCode = Literal["greetings", "etiquette", "food_dining", "gift_giving", "festivals", "religion_beliefs",
                       "clothing", "arts_music", "family_life", "heritage", "business_culture", "taboos"]


class ChatContext(BaseModel):
    """Ngữ cảnh trang: quốc gia / mục đang xem → ưu tiên khi truy xuất và gợi ý câu hỏi."""

    country: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")
    category: CategoryCode | None = None
    entryId: int | None = None


class ChatRequest(BaseModel):
    """Body của POST /api/ai/chat."""

    message: str = Field(min_length=2, max_length=1000)
    sessionId: str | None = Field(default=None, max_length=64)
    level: Literal["simple", "normal", "deep"] = "normal"
    lang: Literal["vi", "en"] = "vi"
    context: ChatContext | None = None


class RatingRequest(BaseModel):
    """Body của POST /api/ai/chat/messages/{id}/rating."""

    rating: Literal[-1, 1]


class SuggestedQuestion(BaseModel):
    """Một câu hỏi gợi ý; `country`/`category` là None với câu gợi ý chung."""

    text: str
    category: CategoryCode | None = None
    country: str | None = None


class SuggestionsResponse(BaseModel):
    """Kết quả GET /api/ai/suggestions."""

    country: str | None
    interests: list[CategoryCode]
    questions: list[SuggestedQuestion]


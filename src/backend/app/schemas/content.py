"""Pydantic DTO cho Content API — khớp components.schemas trong docs/api/openapi.yaml.

Tên trường viết camelCase giống hợp đồng API để frontend dùng thẳng, không cần alias.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.ai import CategoryCode

ClaimScope = Literal["common_practice", "historical_tradition", "regional", "community_specific"]
Confidence = Literal["verified", "partially_supported", "unverified"]
ContentStatus = Literal["draft", "in_review", "published", "flagged", "archived"]
SourceType = Literal["api_dataset", "official_site", "museum", "academic", "editorial", "encyclopedia"]
ReliabilityTier = Literal["official", "museum", "academic", "community"]
FeedbackTarget = Literal["entry", "claim", "chat_message", "comparison", "quiz_question"]
# "unanswered" là loại nội bộ (AI Guide tự ghi khi từ chối) — người dùng không gửi được
FeedbackType = Literal["factual_error", "stereotype", "missing_source", "other"]
FeedbackStatus = Literal["open", "in_progress", "resolved", "dismissed"]


class CountrySummary(BaseModel):
    """Một quốc gia trên bản đồ / danh sách. `coverage` = % trong 12 danh mục đã có claim xuất bản."""

    iso2: str
    name: str
    region: str
    flag: str
    coverage: int = Field(ge=0, le=100)
    featured: bool


class CategoryCount(BaseModel):
    """Số bài viết đã xuất bản của một danh mục."""

    code: CategoryCode
    entryCount: int


class Tip(BaseModel):
    """Một "điều cần biết" — luôn kèm nguồn."""

    text: str
    sourceIds: list[int]


class CountryProfile(CountrySummary):
    """Hồ sơ quốc gia: thông tin nền, 12 danh mục, tối đa 5 điều cần biết."""

    nameEn: str
    capital: str | None
    languages: list[str]
    currencies: list[str]
    neighbors: list[str]
    categories: list[CategoryCount]
    firstTimeTips: list[Tip] = Field(max_length=5)


class EntrySummary(BaseModel):
    """Bài viết trong danh sách theo danh mục."""

    id: int
    category: CategoryCode
    title: str
    summary: str | None
    updatedAt: date


class ClaimSourceRef(BaseModel):
    """Liên kết claim → nguồn, kèm đoạn trích làm bằng chứng."""

    sourceId: int
    evidenceExcerpt: str
    locator: str | None = None


class Claim(BaseModel):
    """Một phát biểu có phạm vi, độ tin cậy và ≥ 1 nguồn."""

    id: int
    text: str
    scope: ClaimScope
    region: str | None
    period: str | None
    confidence: Confidence
    sources: list[ClaimSourceRef] = Field(min_length=1)


class Source(BaseModel):
    """Nguồn và giấy phép."""

    id: int
    title: str
    publisher: str
    url: str
    sourceType: SourceType
    license: str
    reliabilityTier: ReliabilityTier
    retrievedAt: date


class EntryDetail(EntrySummary):
    """Bài viết đầy đủ: chỉ claim đã xuất bản và đã kiểm chứng (AC03.3)."""

    countryIso: str
    status: ContentStatus
    version: int
    claims: list[Claim]
    sources: list[Source]


class HeritageItem(BaseModel):
    """Di sản UNESCO, kèm ghi công theo giấy phép của nguồn (AC04.2)."""

    id: int
    unescoId: str
    name: str
    type: Literal["tangible", "intangible"]
    listType: str
    inscribedYear: int | None
    countries: list[str]
    lat: float | None
    lng: float | None
    attribution: str


class SearchItem(BaseModel):
    """Một kết quả tìm kiếm. `id` là chuỗi vì gộp nhiều loại (ISO2 với quốc gia, số với bài viết)."""

    kind: Literal["country", "entry", "heritage", "theme"]
    id: str
    title: str
    snippet: str | None
    countryIso: str | None


class SearchPage(BaseModel):
    """Một trang kết quả tìm kiếm."""

    total: int
    page: int
    items: list[SearchItem]


class Theme(BaseModel):
    """Chủ đề xuyên quốc gia (thẻ `tags.kind = 'theme'`)."""

    slug: str
    title: str
    countryCount: int


class Festival(BaseModel):
    """Lễ hội (bài viết danh mục festivals) diễn ra trong tháng được hỏi."""

    entryId: int
    name: str
    country: str
    dateText: str | None


class FeedbackCreate(BaseModel):
    """Body của POST /api/feedback (AC14.1)."""

    targetType: FeedbackTarget
    targetId: int = Field(ge=1)
    type: FeedbackType
    comment: str | None = Field(default=None, max_length=1000)


class Feedback(FeedbackCreate):
    """Báo cáo đã ghi nhận."""

    id: int
    status: FeedbackStatus
    createdAt: datetime

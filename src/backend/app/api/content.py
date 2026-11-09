"""Content API (không gọi LLM, chỉ nội dung `published`): countries, entries, heritage, search, sources, themes,
festivals, feedback. Quiz (P3) chưa có.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.db import get_db
from app.core.security import AuthUser, optional_user
from app.repositories import country_repo, entry_repo, feedback_repo, heritage_repo
from app.schemas.ai import CategoryCode
from app.schemas.content import (
    CountryProfile,
    CountrySummary,
    EntryDetail,
    EntrySummary,
    Feedback,
    FeedbackCreate,
    Festival,
    HeritageItem,
    SearchPage,
    Source,
    Theme,
)
from app.services import content_service

router = APIRouter(tags=["Content"])
Db = Annotated[AsyncConnection, Depends(get_db)]
Lang = Annotated[Literal["vi", "en"], Query()]
Iso = Annotated[str, Path(pattern=r"^[A-Za-z]{2}$")]
Id = Annotated[int, Path(ge=1)]


@router.get("/countries", response_model=list[CountrySummary], tags=["Countries"])
async def list_countries(db: Db, region: str | None = None, lang: Lang = "vi") -> list[dict[str, Any]]:
    """Mọi quốc gia kèm % độ phủ (AC01.1, AC01.2)."""
    return await country_repo.list_countries(db, region, lang)


@router.get("/countries/{iso}", response_model=CountryProfile, tags=["Countries"])
async def get_country(db: Db, iso: Iso, lang: Lang = "vi") -> dict[str, Any]:
    """Hồ sơ quốc gia: thông tin nền, 12 danh mục, 5 điều cần biết có nguồn (AC02.1). Không có → 404."""
    return await country_repo.get_profile(db, iso, lang)


@router.get("/countries/{iso}/entries", response_model=list[EntrySummary])
async def list_country_entries(db: Db, iso: Iso, category: CategoryCode | None = None,
                               lang: Lang = "vi") -> list[dict[str, Any]]:
    """Bài viết đã xuất bản của quốc gia, lọc theo danh mục (AC02.2). Quốc gia không có → 404."""
    cid = await country_repo.country_id(db, iso)
    return await entry_repo.list_entries(db, cid, category, lang)


@router.get("/entries/{id}", response_model=EntryDetail)
async def get_entry(db: Db, id: Id, lang: Lang = "vi") -> dict[str, Any]:
    """Bài viết + claim có phạm vi, độ tin cậy, bằng chứng (AC03). Bài chưa xuất bản → 404."""
    return await entry_repo.get_entry(db, id, lang)


@router.get("/sources/{id}", response_model=Source)
async def get_source(db: Db, id: Id) -> dict[str, Any]:
    """Chi tiết nguồn: nhà xuất bản, giấy phép, ngày truy xuất (AC03.2)."""
    return await entry_repo.get_source(db, id)


@router.get("/heritage", response_model=list[HeritageItem], tags=["Heritage"])
async def list_heritage(db: Db, country: Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")] = None,
                        type: Literal["tangible", "intangible"] | None = None) -> list[dict[str, Any]]:
    """Di sản UNESCO lọc theo quốc gia / loại, kèm ghi công CC BY-SA (AC04)."""
    return await heritage_repo.list_heritage(db, country, type)


@router.get("/search", response_model=SearchPage, tags=["Search"])
async def search(db: Db, q: Annotated[str, Query(min_length=2, max_length=200)],
                 country: Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")] = None,
                 category: CategoryCode | None = None,
                 page: Annotated[int, Query(ge=1)] = 1,
                 pageSize: Annotated[int, Query(ge=1, le=100)] = 20) -> dict[str, Any]:
    """Tìm quốc gia, bài viết, di sản, chủ đề — gõ không dấu được (AC05)."""
    return await content_service.search(db, q.strip(), country, category, page, pageSize)


@router.get("/themes", response_model=list[Theme])
async def list_themes(db: Db) -> list[dict[str, Any]]:
    """Chủ đề xuyên quốc gia có bài đã xuất bản (F1.7)."""
    return await entry_repo.list_themes(db)


@router.get("/festivals", response_model=list[Festival])
async def list_festivals(db: Db, month: Annotated[int, Query(ge=1, le=12)], lang: Lang = "vi") -> list[dict[str, Any]]:
    """Lễ hội diễn ra trong tháng `month` (F1.8)."""
    return await entry_repo.list_festivals(db, month, lang)


@router.post("/feedback", response_model=Feedback, status_code=201, tags=["Feedback"])
async def create_feedback(db: Db, body: FeedbackCreate,
                          user: Annotated[AuthUser | None, Depends(optional_user)]) -> dict[str, Any]:
    """Báo cáo sai / góp ý → `open`, chờ biên tập viên xử lý (AC14). Khách gửi được; đã đăng nhập thì ghi người gửi."""
    return await feedback_repo.create_feedback(db, body.targetType, body.targetId, body.type, body.comment,
                                               user.id if user else None)

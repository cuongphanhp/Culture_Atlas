"""Admin API (JWT, vai trò editor/admin). Đã có: users (admin). Còn lại (P3): review-queue, entries, claims, sources,
feedback, coverage, ai/drafts, ingestion, benchmark.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.db import get_db
from app.core.errors import ProblemError
from app.core.security import AuthUser, require_role
from app.repositories import user_repo
from app.schemas.auth import User, UserUpdate

router = APIRouter()
Db = Annotated[AsyncConnection, Depends(get_db)]
Admin = Annotated[AuthUser, Depends(require_role("admin"))]


@router.get("/users", response_model=list[User], tags=["Admin - Users"])
async def list_users(db: Db, _: Admin) -> list[dict[str, Any]]:
    """Danh sách người dùng — chỉ admin; editor / learner → 403 (AC15.1)."""
    return await user_repo.list_users(db)


@router.patch("/users/{id}", response_model=User, tags=["Admin - Users"])
async def update_user(db: Db, admin: Admin, body: UserUpdate, id: Annotated[int, Path(ge=1)]) -> dict[str, Any]:
    """Đổi vai trò / khoá người dùng — chỉ admin.

    Admin không tự hạ quyền hay tự khoá mình (tránh hệ thống không còn ai quản trị) → 422.
    """
    if id == admin.id and ((body.role and body.role != "admin") or body.isActive is False):
        raise ProblemError(422, "Không thể tự hạ quyền hoặc tự khoá tài khoản của mình", slug="self-demotion")
    return await user_repo.update_user(db, id, body.role, body.isActive)

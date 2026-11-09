"""Schema của Auth API và quản lý người dùng (docs/api/openapi.yaml: TokenResponse, User, UserRole)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["learner", "editor", "admin"]


class LoginRequest(BaseModel):
    """Body của POST /api/auth/login."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class User(BaseModel):
    """Người dùng (không bao giờ kèm mật khẩu / hash)."""

    id: int
    email: str
    displayName: str | None
    role: UserRole
    locale: str
    isActive: bool


class TokenResponse(BaseModel):
    """Kết quả đăng nhập: access token Bearer + thông tin người dùng."""

    accessToken: str
    tokenType: Literal["Bearer"] = "Bearer"
    expiresAt: datetime
    user: User


class UserUpdate(BaseModel):
    """Body của PATCH /api/admin/users/{id}: đổi vai trò và/hoặc khoá / mở khoá."""

    role: UserRole | None = None
    isActive: bool | None = None

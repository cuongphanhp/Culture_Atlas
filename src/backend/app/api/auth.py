"""Auth API: POST /login (email + mật khẩu → JWT), GET /me (người dùng của token). Xem app/core/security.py."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.security import AuthUser, authenticate, create_access_token, current_user
from app.schemas.auth import LoginRequest, TokenResponse, User

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> dict[str, Any]:
    """Đăng nhập; sai thông tin hoặc tài khoản bị khoá → 401 (AC15.1)."""
    user = await authenticate(body.email.strip(), body.password)
    token, expires_at = create_access_token(user.id, user.role)
    return {"accessToken": token, "tokenType": "Bearer", "expiresAt": expires_at, "user": user.to_dict()}


@router.get("/me", response_model=User)
async def me(user: Annotated[AuthUser, Depends(current_user)]) -> dict[str, Any]:
    """Người dùng hiện tại; không có / hết hạn token → 401 (AC15.2)."""
    return user.to_dict()

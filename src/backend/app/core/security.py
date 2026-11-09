"""JWT (Bearer, HS256 qua PyJWT), băm mật khẩu Argon2, dependency lấy người dùng và require_role (AC15).

Mỗi request đọc lại người dùng từ DB: đổi vai trò hoặc khoá tài khoản có hiệu lực ngay, không chờ token hết hạn.
Vai trò theo bậc learner < editor < admin — `require_role("editor")` cho cả admin.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.errors import ProblemError

ALGORITHM = "HS256"
MIN_SECRET_BYTES = 32          # RFC 7518 §3.2: khoá HS256 ≥ 256 bit
ROLE_RANK = {"learner": 0, "editor": 1, "admin": 2}

_hasher = PasswordHasher()
# Băm sẵn để email không tồn tại cũng tốn thời gian như email có thật (không lộ email nào đã đăng ký)
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


@dataclass(frozen=True)
class AuthUser:
    """Người dùng đã xác thực (đọc từ DB)."""

    id: int
    email: str
    display_name: str | None
    role: str
    locale: str
    is_active: bool

    def to_dict(self) -> dict[str, Any]:
        """DTO User của API."""
        return {"id": self.id, "email": self.email, "displayName": self.display_name, "role": self.role,
                "locale": self.locale, "isActive": self.is_active}


def hash_password(password: str) -> str:
    """Băm Argon2id (tham số mặc định của argon2-cffi)."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """So mật khẩu với hash; hash rỗng / hỏng → False (vẫn tốn thời gian như khi so thật)."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and bool(password_hash)
    except (VerificationError, InvalidHashError):
        return False


def _secret() -> str:
    secret = get_settings().jwt_secret
    if len(secret.encode()) < MIN_SECRET_BYTES:
        # Không cấp / nhận token bằng khoá yếu; phần còn lại của API vẫn chạy
        raise ProblemError(503, "Đăng nhập chưa được cấu hình",
                           f"JWT_SECRET phải dài ít nhất {MIN_SECRET_BYTES} byte (tạo bằng: openssl rand -hex 32).",
                           "auth-misconfigured")
    return secret


def create_access_token(user_id: int, role: str) -> tuple[str, datetime]:
    """Token HS256 có `sub`, `role`, `iat`, `exp`; trả (token, thời điểm hết hạn)."""
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=get_settings().jwt_ttl_minutes)
    token = jwt.encode({"sub": str(user_id), "role": role, "iat": now, "exp": exp}, _secret(), algorithm=ALGORITHM)
    return token, exp


def _unauthorized(detail: str) -> ProblemError:
    return ProblemError(401, "Chưa đăng nhập hoặc phiên đã hết hạn", detail, "unauthorized")


def decode_token(token: str) -> int:
    """Kiểm chữ ký + hạn của token, trả id người dùng.

    Raises:
        ProblemError: 401 nếu token hết hạn, sai chữ ký hoặc thiếu trường (AC15.2).
    """
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
        return int(claims["sub"])
    except jwt.ExpiredSignatureError as e:
        raise _unauthorized("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.") from e
    except (jwt.InvalidTokenError, ValueError) as e:
        raise _unauthorized("Token không hợp lệ.") from e


_SQL_USER = """SELECT id, email, display_name, role::text AS role, locale, is_active, password_hash
               FROM users WHERE {where}"""


def _user(r: Any) -> AuthUser:
    return AuthUser(r.id, r.email, r.display_name, r.role, r.locale, r.is_active)


async def authenticate(email: str, password: str) -> AuthUser:
    """Kiểm email + mật khẩu, ghi `last_login_at`.

    Raises:
        ProblemError: 401 nếu sai thông tin hoặc tài khoản bị khoá (cùng một thông báo, không lộ lý do).
    """
    async with get_engine().begin() as conn:
        r = (await conn.execute(text(_SQL_USER.format(where="lower(email) = lower(:email)")), {"email": email})).first()
        # Argon2 tốn CPU → chạy ngoài event loop
        ok = await asyncio.to_thread(verify_password, password, r.password_hash if r else None)
        if r is None or not ok or not r.is_active:
            raise ProblemError(401, "Email hoặc mật khẩu không đúng", slug="invalid-credentials")
        await conn.execute(text("UPDATE users SET last_login_at = now() WHERE id = :id"), {"id": r.id})
        if _hasher.check_needs_rehash(r.password_hash):
            await conn.execute(text("UPDATE users SET password_hash = :h WHERE id = :id"),
                               {"h": await asyncio.to_thread(hash_password, password), "id": r.id})
    return _user(r)


def _bearer(request: Request) -> str | None:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


async def optional_user(request: Request) -> AuthUser | None:
    """Người dùng của header `Authorization: Bearer …`; không có header → None.

    Raises:
        ProblemError: 401 nếu có token nhưng token không hợp lệ / hết hạn, hoặc tài khoản đã bị khoá.
    """
    token = _bearer(request)
    if token is None:
        return None
    user_id = decode_token(token)
    async with get_engine().connect() as conn:
        r = (await conn.execute(text(_SQL_USER.format(where="id = :id")), {"id": user_id})).first()
    if r is None or not r.is_active:
        raise _unauthorized("Tài khoản không còn hoạt động.")
    return _user(r)


async def current_user(user: Annotated[AuthUser | None, Depends(optional_user)]) -> AuthUser:
    """Bắt buộc đăng nhập.

    Raises:
        ProblemError: 401 nếu không có token hợp lệ.
    """
    if user is None:
        raise _unauthorized("Cần đăng nhập để dùng chức năng này.")
    return user


def require_role(role: str) -> Callable[..., Awaitable[AuthUser]]:
    """Dependency: người dùng phải có vai trò ≥ `role` (learner < editor < admin), không thì 403 (AC15.1)."""
    need = ROLE_RANK[role]

    async def _check(user: Annotated[AuthUser, Depends(current_user)]) -> AuthUser:
        if ROLE_RANK.get(user.role, -1) < need:
            raise ProblemError(403, "Bạn không có quyền dùng chức năng này", f"Cần vai trò {role}.", "forbidden")
        return user

    return _check

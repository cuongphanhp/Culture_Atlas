"""users: danh sách người dùng và đổi vai trò / khoá tài khoản (chỉ admin gọi, AC15.1)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import ProblemError

_COLS = "id, email, display_name, role::text AS role, locale, is_active"


def _user(r: Any) -> dict[str, Any]:
    return {"id": r.id, "email": r.email, "displayName": r.display_name, "role": r.role, "locale": r.locale,
            "isActive": r.is_active}


async def list_users(conn: AsyncConnection) -> list[dict[str, Any]]:
    """Mọi người dùng, theo id."""
    return [_user(r) for r in (await conn.execute(text(f"SELECT {_COLS} FROM users ORDER BY id"))).all()]


async def update_user(conn: AsyncConnection, user_id: int, role: str | None, is_active: bool | None) -> dict[str, Any]:
    """Đổi vai trò và/hoặc trạng thái hoạt động; trường None giữ nguyên.

    Raises:
        ProblemError: 404 nếu không có người dùng này.
    """
    r = (await conn.execute(text(f"""
        UPDATE users SET role = COALESCE(CAST(:role AS user_role), role),
                         is_active = COALESCE(CAST(:active AS boolean), is_active), updated_at = now()
        WHERE id = :id RETURNING {_COLS}"""), {"id": user_id, "role": role, "active": is_active})).first()
    if r is None:
        raise ProblemError(404, "Không tìm thấy người dùng")
    return _user(r)

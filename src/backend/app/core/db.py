"""Kết nối PostgreSQL async (SQLAlchemy + asyncpg). Dùng câu SQL tường minh qua text().

NullPool: mỗi request mở/đóng kết nối — đơn giản, không giữ kết nối cũ khi DB khởi động lại (và khi test nạp lại seed).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Engine dùng chung cho cả tiến trình (DATABASE_URL)."""
    return create_async_engine(get_settings().database_url, poolclass=NullPool)


async def get_db() -> AsyncIterator[AsyncConnection]:
    """FastAPI dependency: một kết nối + transaction cho mỗi request (commit khi thành công)."""
    async with get_engine().begin() as conn:
        yield conn

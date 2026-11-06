"""Giới hạn lượt hỏi AI cho khách theo anon_key (BR12, AC06.3) — đếm chat_logs trong ngày, không cần Redis."""
from __future__ import annotations

import re

from fastapi import Request
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.errors import ProblemError

_CLIENT_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def client_key(request: Request) -> str:
    """Khách được nhận diện bằng header X-Client-Id (frontend sinh và lưu trên trình duyệt); không có thì theo IP."""
    cid = request.headers.get("x-client-id", "")
    if _CLIENT_ID.match(cid):
        return cid
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return f"ip:{fwd or (request.client.host if request.client else 'unknown')}"[:64]


async def consume(key: str) -> int:
    """Kiểm tra còn lượt không; trả về số lượt còn lại SAU lượt này. Hết lượt → 429."""
    limit = get_settings().guest_daily_limit
    async with get_engine().begin() as conn:
        used = (await conn.execute(text("""
            SELECT COUNT(*) FROM chat_logs l JOIN chat_sessions s ON s.id = l.session_id
            WHERE s.anon_key = :k AND l.created_at >= date_trunc('day', now())"""), {"k": key})).scalar_one()
    if used >= limit:
        raise ProblemError(429, "Bạn đã dùng hết lượt hỏi hôm nay",
                           f"Khách được hỏi AI {limit} lượt mỗi ngày. Hãy quay lại vào ngày mai nhé — các trang khám phá, "
                           "so sánh và quiz vẫn dùng bình thường.", "rate-limit")
    return limit - used - 1

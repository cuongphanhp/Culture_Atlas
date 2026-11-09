"""feedback: báo cáo sai / góp ý của người dùng (AC14). AI Guide tự ghi loại `unanswered` trong app/ai/agent.py."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

_SQL_INSERT = """
INSERT INTO feedback (target_type, target_id, user_id, type, comment)
VALUES (CAST(:target_type AS feedback_target), :target_id, :user_id, CAST(:type AS feedback_type), :comment)
RETURNING id, status::text AS status, created_at"""


async def create_feedback(conn: AsyncConnection, target_type: str, target_id: int, kind: str,
                          comment: str | None, user_id: int | None = None) -> dict[str, Any]:
    """Ghi một báo cáo mới ở trạng thái `open`; trả về DTO Feedback."""
    r = (await conn.execute(text(_SQL_INSERT), {"target_type": target_type, "target_id": target_id, "user_id": user_id,
                                                "type": kind, "comment": comment})).one()
    return {"id": r.id, "targetType": target_type, "targetId": target_id, "type": kind, "comment": comment,
            "status": r.status, "createdAt": r.created_at}

"""Viết lại câu hỏi hội thoại thành truy vấn tìm kiếm độc lập.

Vì sao cần: cross-encoder rerank chấm rất thấp câu hỏi dạng hội thoại ("Còn chuyện tặng quà thì sao?" → 0.09)
nhưng chấm cao truy vấn dạng từ khoá ("gift giving etiquette Japan" → 0.9+), và tài liệu tham khảo phần lớn là tiếng Anh.
Câu so sánh nhiều nước được tách thành một truy vấn cho mỗi nước. Lỗi LLM → dùng lại câu hỏi gốc.
"""
from __future__ import annotations

from app.ai.llm_adapter import LLMAdapter, LLMUnavailable
from app.ai.router import Country

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["queries"],
          "properties": {"queries": {"type": "array", "items": {"type": "string"}}}}

INSTRUCTION = (
    "Viết lại câu hỏi mới nhất của người dùng thành 1–3 truy vấn tìm kiếm ngắn để tra tài liệu văn hoá. Yêu cầu:\n"
    "- Mỗi truy vấn 3–8 từ, bằng TIẾNG ANH, độc lập (đọc riêng vẫn hiểu, không dùng 'đó', 'thì sao').\n"
    "- Luôn ghi rõ tên quốc gia. Nếu câu hỏi nối tiếp lượt trước, lấy chủ đề/quốc gia từ lượt trước.\n"
    "- Câu so sánh nhiều nước: mỗi nước một truy vấn riêng.\n"
    "- Chỉ tạo truy vấn, không trả lời câu hỏi."
)


async def rewrite(llm: LLMAdapter, message: str, history: list[tuple[str, str]], countries: list[Country]) -> list[str]:
    """→ 1–3 truy vấn tiếng Anh độc lập; [] nếu LLM lỗi (khi đó chỉ tìm bằng câu gốc)."""
    prev = "\n".join(f"- Người dùng: {q}" for q, _ in history[-2:])
    ctx = f"Quốc gia đang nói tới: {', '.join(f'{c.name_vi} ({c.name_en})' for c in countries)}\n" if countries else ""
    try:
        out = await llm.complete_json([
            {"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": f"{ctx}{'Các lượt trước:' + chr(10) + prev + chr(10) if prev else ''}Câu hỏi mới nhất: {message}"}],
            name="search_queries", schema=SCHEMA)
        qs = [q.strip() for q in out.get("queries", []) if isinstance(q, str) and 2 <= len(q.strip()) <= 200]
        return list(dict.fromkeys(qs))[:3]
    except (LLMUnavailable, KeyError, ValueError, TypeError):
        return []

"""Tiện ích chuẩn hoá tiếng Việt cho router / truy xuất."""
from __future__ import annotations

import re
import unicodedata


def fold(text: str) -> str:
    """Chữ thường, bỏ dấu (đ → d), gộp khoảng trắng: "Nhật Bản" → "nhat ban"."""
    text = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def words(text: str) -> list[str]:
    """Các từ của câu đã `fold`."""
    return fold(text).split()

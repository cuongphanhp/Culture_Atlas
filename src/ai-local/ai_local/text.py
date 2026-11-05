"""Xử lý văn bản trước khi đọc (TTS) và sau khi nhận dạng (STT)."""
from __future__ import annotations

import re

_CITE = re.compile(r"\s*\[c\d+\]")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD = re.compile(r"(\*\*|__|\*|_|`|~~|^#+\s*|^>\s*)", re.MULTILINE)
_BULLET = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+", re.MULTILINE)


def clean_for_speech(text: str) -> str:
    """Bỏ nhãn trích dẫn [c#], markdown, gạch đầu dòng — giữ lại câu chữ để đọc tự nhiên."""
    text = _CITE.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _BULLET.sub("", text)
    text = _MD.sub("", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # mỗi dòng (gạch đầu dòng cũ) thành một câu để TTS ngắt nghỉ đúng
    text = " ".join(ln if ln[-1] in ".!?…:;" else ln + "." for ln in lines)
    return re.sub(r"\s{2,}", " ", text).strip()


def tidy_transcript(text: str) -> str:
    """Gipformer trả chữ IN HOA, không dấu câu → chữ thường, viết hoa chữ đầu, gộp khoảng trắng."""
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text[:1].upper() + text[1:] if text else text

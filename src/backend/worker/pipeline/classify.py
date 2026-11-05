"""Gán danh mục văn hoá (12 mã cố định) cho đoạn văn bằng từ khoá — gợi ý cho biên tập viên, không phải kết luận."""
from __future__ import annotations

import re

KEYWORDS: dict[str, list[str]] = {
    "greetings": ["greet", "bow", "handshake", "wai", "hello", "kiss on the cheek", "la bise", "namaste", "address"],
    "gift_giving": ["gift", "omiyage", "red envelope", "lì xì", "wrapping"],
    "food_dining": ["dining", "meal", "chopstick", "table manner", "food", "eat", "restaurant", "tipping", "drink", "cuisine"],
    "festivals": ["festival", "new year", "holiday", "celebrat", "tết", "diwali", "carnival"],
    "religion_beliefs": ["religio", "buddhis", "hindu", "islam", "christian", "shinto", "temple", "shrine", "ancestor", "worship"],
    "clothing": ["dress", "cloth", "attire", "kimono", "hanbok", "sari", "áo dài", "shoe"],
    "arts_music": ["music", "dance", "theatre", "theater", "painting", "craft", "literature", "art"],
    "family_life": ["family", "marriage", "wedding", "elder", "children", "funeral", "parent"],
    "business_culture": ["business", "meeting", "workplace", "office", "business card", "colleague", "punctual"],
    "taboos": ["taboo", "avoid", "rude", "offensive", "forbidden", "never ", "inappropriate", "considered impolite"],
    "heritage": ["heritage", "unesco", "monument", "historic site"],
    "etiquette": ["etiquette", "manners", "polite", "custom", "courtesy", "respect"],
}


def _count(text: str, kws: list[str]) -> int:
    return sum(len(re.findall(r"(?<![a-z])" + re.escape(k), text)) for k in kws)


def guess_category(heading: str, body: str = "") -> str | None:
    """Tiêu đề mục có trọng số gấp 3 lần nội dung."""
    h, b = (heading or "").lower(), (body or "").lower()
    scores = {cat: 3 * _count(h, kws) + _count(b, kws) for cat, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None

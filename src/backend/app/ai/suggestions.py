"""Câu hỏi gợi ý của AI Guide theo quốc gia và mối quan tâm của người dùng (AC10.3, AC10.4).

Không gọi LLM: chọn từ ngân hàng câu hỏi biên soạn sẵn (`prompts/suggestions_vi.json`), mỗi nước có câu nêu nét
văn hoá riêng của nước đó. Cách chọn:
1. Suy ra chủ đề quan tâm (category) từ các câu người dùng đã hỏi — câu gần nhất có trọng số cao nhất.
2. Ưu tiên chủ đề quan tâm nhất (2 câu), sau đó mở rộng sang chủ đề khác để người dùng khám phá.
3. Trong các chủ đề khám phá, chủ đề có bằng chứng trong kho cho nước đó đứng trước (chủ đề chưa có dữ liệu chỉ để
   bù cho đủ số câu); bỏ câu người dùng đã hỏi.

Dùng ở: `ChatAgent` (gợi ý sau câu trả lời không qua RAG / khi LLM lỗi, và làm gợi ý mẫu cho LLM)
và `GET /api/ai/suggestions` (lời chào, cột "Thử hỏi" của giao diện).
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.text import fold

BANK_FILE = Path(__file__).parent / "prompts" / "suggestions_vi.json"

# Tên tiếng Việt của category_code (đưa vào prompt gợi ý của LLM)
CATEGORY_VI: dict[str, str] = {
    "greetings": "chào hỏi", "etiquette": "phép lịch sự", "food_dining": "ẩm thực", "gift_giving": "tặng quà",
    "festivals": "lễ hội", "religion_beliefs": "tôn giáo – tín ngưỡng", "clothing": "trang phục", "arts_music": "nghệ thuật",
    "family_life": "gia đình", "heritage": "di sản", "business_culture": "văn hoá công sở", "taboos": "điều kiêng kỵ",
}

# Từ khoá (có dấu, chữ thường) → chủ đề. Câu có dấu so khớp nguyên dấu (phân biệt "quà"/"qua", "múa"/"mua");
# câu gõ không dấu so khớp bản đã bỏ dấu, bỏ qua từ một âm tiết dễ nhầm (xem `_AMBIGUOUS_FOLDED`).
INTEREST_KEYWORDS: dict[str, list[str]] = {
    "greetings": ["chào hỏi", "cúi chào", "cúi đầu", "bắt tay", "wai", "namaste", "la bise", "xưng hô", "kính ngữ", "greet", "bow"],
    "etiquette": ["lễ phép", "phép lịch sự", "lịch sự", "cư xử", "ứng xử", "phép tắc", "thể diện", "keigo", "chụp ảnh",
                  "etiquette", "manners"],
    "gift_giving": ["quà", "tặng", "tặng quà", "quà tặng", "món quà", "quà lưu niệm", "lì xì", "omiyage", "phong bì", "gift"],
    "food_dining": ["ăn", "món", "ăn uống", "món ăn", "bữa ăn", "đồ ăn", "ăn gì", "ẩm thực", "bữa", "đũa", "đồ uống", "uống", "rượu", "trà", "nhà hàng", "kimchi", "washoku",
                    "koshary", "tom yum", "food", "cuisine", "dining"],
    "festivals": ["lễ hội", "tết", "ngày lễ", "trung thu", "diwali", "songkran", "seollal", "chuseok", "muertos", "giáng sinh",
                  "festival", "holiday"],
    "religion_beliefs": ["tôn giáo", "tín ngưỡng", "chùa", "đền", "đi chùa", "đền thờ", "phật giáo", "thần đạo", "hồi giáo", "hindu", "ấn độ giáo",
                         "nho giáo", "thờ cúng", "tâm linh", "religion", "temple", "shrine"],
    "clothing": ["trang phục", "quần áo", "mặc", "áo dài", "kimono", "hanbok", "sari", "qipao", "sườn xám", "onsen", "clothing",
                 "dress"],
    "arts_music": ["nghệ thuật", "âm nhạc", "nhạc", "múa", "hát", "điệu múa", "bài hát", "ca hát", "nhạc cụ", "kịch", "tranh", "thư pháp", "kabuki", "pansori", "mariachi",
                   "yoga", "music", "dance", "art"],
    "family_life": ["gia đình", "đám cưới", "cưới hỏi", "hôn nhân", "đám tang", "tang lễ", "người già", "trẻ em", "trưởng thành",
                    "family", "wedding", "funeral"],
    "heritage": ["di sản", "unesco", "di tích", "cố đô", "kim tự tháp", "heritage"],
    "business_culture": ["kinh doanh", "công việc", "đối tác", "danh thiếp", "cuộc họp", "văn phòng", "business"],
    "taboos": ["kiêng", "kiêng kỵ", "cấm kỵ", "tránh", "bất lịch sự", "thô lỗ", "taboo"],
}
# Bỏ dấu thì trùng từ thường ("qua", "mua", "an", "hat", "tra", "den", "mon", "bua"…) → không dùng khi câu gõ không dấu
_AMBIGUOUS_FOLDED = {"qua", "tang", "an", "mon", "bua", "tra", "uong", "mua", "hat", "nhac", "tranh", "den", "chua", "mac",
                     "kieng"}
# "ăn mặc" là trang phục, không phải ẩm thực
_FALSE_FRIENDS: dict[str, re.Pattern[str]] = {"food_dining": re.compile(r"\băn mặc\b")}


def _pattern(words: Iterable[str]) -> re.Pattern[str]:
    alts = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(r"(?<!\w)(" + alts + r")(?!\w)")


_ACCENTED = {cat: _pattern(kws) for cat, kws in INTEREST_KEYWORDS.items()}
_FOLDED = {cat: _pattern({fold(k) for k in kws} - _AMBIGUOUS_FOLDED) for cat, kws in INTEREST_KEYWORDS.items()}


@dataclass(frozen=True)
class Suggestion:
    """Một câu hỏi gợi ý: nội dung, chủ đề (category_code) và quốc gia (ISO2, None nếu là câu chung)."""

    text: str
    category: str | None
    country: str | None

    def to_dict(self) -> dict[str, str | None]:
        """Dạng JSON của API (`SuggestedQuestion` trong openapi.yaml)."""
        return {"text": self.text, "category": self.category, "country": self.country}


@lru_cache
def load_bank() -> dict:
    """Đọc ngân hàng câu hỏi (một lần cho mỗi tiến trình)."""
    return json.loads(BANK_FILE.read_text(encoding="utf-8"))


def detect_interests(questions: Sequence[str]) -> list[str]:
    """Chủ đề người dùng quan tâm, xếp giảm dần theo mức độ.

    `questions` theo thứ tự thời gian (cũ → mới); câu mới hơn có trọng số lớn hơn (1, 1/2, 1/3… tính từ câu mới nhất).
    """
    scores: dict[str, float] = {}
    for age, q in enumerate(reversed(list(questions))):
        lower = " ".join((q or "").lower().split())
        folded = fold(q)
        accented = lower != folded                        # câu có dấu tiếng Việt / ký tự ngoài ASCII
        for cat in INTEREST_KEYWORDS:
            pat, target = (_ACCENTED[cat], lower) if accented else (_FOLDED[cat], folded)
            hits = len(pat.findall(target))
            ff = _FALSE_FRIENDS.get(cat)
            if ff and accented:
                hits -= len(ff.findall(target))
            if hits > 0:
                scores[cat] = scores.get(cat, 0.0) + 1.0 / (age + 1)
    return sorted(scores, key=lambda c: -scores[c])


def interests_of(asked: Sequence[str], focus: str | None = None) -> list[str]:
    """Chủ đề quan tâm: chủ đề đang xem (`focus`) đứng đầu, sau đó là chủ đề suy ra từ câu đã hỏi."""
    found = detect_interests(asked)
    return ([focus] + [c for c in found if c != focus]) if focus in INTEREST_KEYWORDS else found


async def available_categories(conn: AsyncConnection, iso2: str) -> set[str]:
    """Các chủ đề có bằng chứng trong kho cho quốc gia `iso2` (đoạn claim / reference có category, hoặc di sản UNESCO)."""
    rows = await conn.execute(text("""
        SELECT DISTINCT CASE WHEN kind = 'heritage' THEN 'heritage' ELSE metadata->>'category' END
        FROM entry_chunks
        WHERE (metadata->>'country' = :c OR metadata->'countries' ? :c)
          AND (kind = 'heritage' OR metadata->>'category' IS NOT NULL)"""), {"c": iso2})
    return {r[0] for r in rows if r[0]}


def _interleave(order: Sequence[str], pools: dict[str, list[str]], n: int, top_extra: int) -> list[tuple[str, str]]:
    """Lấy câu xoay vòng theo thứ tự chủ đề `order`, mỗi chủ đề 1 câu/vòng; riêng vòng đầu chủ đề đứng đầu lấy thêm
    `top_extra` câu (ưu tiên chủ đề người dùng quan tâm nhất mà vẫn chừa chỗ cho chủ đề mới)."""
    pools = {c: list(qs) for c, qs in pools.items()}
    picked: list[tuple[str, str]] = []
    first_round = True
    while len(picked) < n and any(pools.get(c) for c in order):
        for i, cat in enumerate(order):
            take = 1 + (top_extra if first_round and i == 0 else 0)
            while take and pools.get(cat) and len(picked) < n:
                picked.append((cat, pools[cat].pop(0)))
                take -= 1
        first_round = False
    return picked


def suggest(country: str | None, asked: Sequence[str] = (), *, n: int = 3, available: Iterable[str] | None = None,
            countries: Sequence[str] = (), focus: str | None = None) -> list[Suggestion]:
    """Chọn `n` câu hỏi gợi ý.

    Args:
        country: ISO2 của quốc gia đang nói tới; None → gợi ý chung (nhiều nước, theo chủ đề quan tâm nếu có).
        asked: các câu người dùng đã hỏi trong phiên, cũ → mới (để suy ra mối quan tâm và không gợi ý lại).
        n: số câu cần lấy.
        available: chủ đề có dữ liệu cho `country` (từ `available_categories`) — xếp trước trong nhóm chủ đề khám phá.
        countries: các nước đã nhắc tới trong phiên — dùng khi `country` là None để ưu tiên nước người dùng đang tìm hiểu.
        focus: chủ đề người dùng đang xem trên giao diện (vd. mục "Ẩm thực" của trang quốc gia) — xếp trước mọi chủ đề khác.
    """
    bank = load_bank()
    interests = interests_of(asked, focus)
    seen = {fold(q) for q in asked}
    by_country: dict[str, dict[str, list[str]]] = bank["countries"]

    if country and country in by_country:
        avail = set(available or ())
        pools = {cat: [q for q in qs if fold(q) not in seen] for cat, qs in by_country[country].items()}
        pools = {c: qs for c, qs in pools.items() if qs}
        rest = list(pools)
        shift = len(asked) % len(rest) if rest else 0           # đổi chủ đề khám phá theo lượt để gợi ý không lặp lại
        rest = rest[shift:] + rest[:shift]
        # Thứ tự: chủ đề quan tâm → chủ đề khám phá có dữ liệu → chủ đề chưa có dữ liệu (chỉ để bù cho đủ số câu)
        explore = sorted((c for c in rest if c not in interests), key=lambda c: bool(avail) and c not in avail)
        order = [c for c in interests if c in pools] + explore
        top_extra = 1 if interests and order and order[0] == interests[0] else 0
        return [Suggestion(q, cat, country) for cat, q in _interleave(order, pools, n, top_extra)]

    # Không rõ quốc gia: theo chủ đề quan tâm, mỗi câu một nước khác nhau (ưu tiên nước đã nhắc trong phiên)
    out: list[Suggestion] = []
    if interests:
        isos = [c for c in countries if c in by_country] + [c for c in by_country if c not in countries]
        for cat in interests:
            for iso in isos:
                if len(out) >= n:
                    return out
                q = next((q for q in by_country[iso].get(cat, []) if fold(q) not in seen), None)
                if q and all(s.country != iso for s in out):
                    out.append(Suggestion(q, cat, iso))
    for q in bank["general"]:
        if len(out) >= n:
            break
        if fold(q) not in seen and all(s.text != q for s in out):
            out.append(Suggestion(q, None, None))
    return out[:n]

"""Phân loại câu hỏi: smalltalk (chào hỏi) | structured (dữ kiện trả từ DB, không gọi LLM) | rag (văn hoá, cần nguồn).
Nhận diện quốc gia theo tên tiếng Việt / tiếng Anh / tên gọi khác, kể cả gõ không dấu."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.ai.text import fold

# Tên gọi khác (có dấu). Câu có dấu → so khớp có dấu; câu gõ không dấu → so khớp bản đã bỏ dấu (chỉ tên ≥ 2 âm tiết).
ALIASES: dict[str, list[str]] = {
    "VN": ["việt nam", "vietnam"], "JP": ["nhật bản", "nhật", "japan", "xứ phù tang"],
    "KR": ["hàn quốc", "hàn", "korea", "đại hàn"], "CN": ["trung quốc", "trung hoa", "china"],
    "TH": ["thái lan", "thailand"], "IN": ["ấn độ", "india"], "FR": ["pháp", "france"],
    "MX": ["mexico", "mê hi cô"], "EG": ["ai cập", "egypt"], "KE": ["kenya", "kê nia"],
}
# Tên ngắn trùng với từ thường gặp → loại trừ các cụm này
AMBIGUOUS: dict[str, re.Pattern] = {
    "pháp": re.compile(r"(phương|biện|giải|liệu|hiến|tư|lập|hợp|ngữ|cú|thủ|phật|chính|công|tà|ma|thuật) pháp|"
                       r"pháp (luật|lý|chế|sư|danh|nhân|thuật|môn|quy|định|lệnh|trường|đình|y|bảo|hội)"),
    "phap": re.compile(r"(phuong|bien|giai|lieu|hien|tu|lap|hop|ngu|cu|thu|phat|chinh|cong|ta|ma|thuat) phap|"
                       r"phap (luat|ly|che|su|danh|nhan|thuat|mon|quy|dinh|lenh|truong|dinh|y|bao|hoi)"),
    "nhật": re.compile(r"(sinh|chủ|cập|thường|mỗi|hằng|thứ) nhật|nhật (ký|kí|thực|trình|dụng|lệnh|báo|nguyệt|quang)"),
    "hàn": re.compile(r"(bần|cơ|nghèo|giàu|ấm|lạnh|ngăn) hàn|hàn (huyên|lâm|gắn|xì|the|vi|thử|đới|thực|nối)"),
}

SMALLTALK = re.compile(
    r"^(xin )?(chao|hello|hi|hey|alo|chao ban|chao bot)\b|^(cam on|thank|thanks|cảm ơn)\b|"
    r"\b(ban la ai|ban ten gi|ban lam duoc gi|ban giup (duoc )?gi|ban co the lam gi|gioi thieu ve ban|ai tao ra ban|"
    r"who are you|what can you do)\b|^(tam biet|bye|goodbye)\b|^(ok|oke|uh|vang|da|duoc|hay qua|tuyet)\s*$")

STRUCTURED: list[tuple[str, re.Pattern]] = [
    ("capital", re.compile(r"\b(thu do|capital)\b")),
    ("currency", re.compile(r"\b(tien te|dong tien|don vi tien|tien gi|currency)\b")),
    ("languages", re.compile(r"\b(ngon ngu|tieng gi|noi tieng|language)\b")),
    ("heritage_count", re.compile(r"\b(bao nhieu|may|so luong)\b.*\bdi san\b|\bdi san\b.*\b(bao nhieu|may)\b")),
    ("neighbors", re.compile(r"\b(giap|giap ranh|lang gieng|bien gioi)\b")),
]


@dataclass
class Country:
    """Quốc gia trong DB + các tên gọi dùng để nhận diện (`keys`, dài trước)."""

    iso2: str
    name_vi: str
    name_en: str
    capital: str | None
    languages: list[str]
    currencies: list[str]
    neighbors: list[str]
    keys: list[str] = field(default_factory=list)


@dataclass
class Route:
    """Kết quả phân loại câu hỏi."""

    kind: str                       # smalltalk | structured | rag
    countries: list[Country]
    intent: str | None = None       # với structured: capital | currency | languages | heritage_count | neighbors


async def load_countries(conn: AsyncConnection) -> list[Country]:
    """Đọc 10 quốc gia + tên gọi khác (ALIASES) để nhận diện trong câu hỏi."""
    rows = (await conn.execute(text(
        "SELECT iso2, name_vi, name_en, capital, languages, currencies, COALESCE(neighbors, '{}') FROM countries"))).all()
    out = []
    for iso, vi, en, cap, langs, curs, neigh in rows:
        keys = {vi.lower(), en.lower(), *ALIASES.get(iso, [])}
        out.append(Country(iso, vi, en, cap, list(langs or []), list(curs or []), list(neigh or []),
                           sorted((k for k in keys if k), key=len, reverse=True)))
    return out


def _has_diacritics(message: str) -> bool:
    """Câu có gõ dấu tiếng Việt không."""
    return fold(message) != re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", message.lower())).strip()


def _norm_accented(message: str) -> str:
    """Chữ thường, bỏ dấu câu, giữ dấu tiếng Việt."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", message.lower())).strip()


def find_countries(message: str, countries: list[Country]) -> list[Country]:
    """Quốc gia được nhắc tới, theo thứ tự xuất hiện. Khớp nguyên từ, bỏ qua cụm trùng từ thường ("phương pháp", "sinh nhật")."""
    accented = _has_diacritics(message)
    m = f" {_norm_accented(message) if accented else fold(message)} "
    found: list[tuple[int, Country]] = []
    taken: list[tuple[int, int]] = []
    for c in countries:
        keys = c.keys if accented else sorted({fold(k) for k in c.keys if len(fold(k).split()) >= 2 or fold(k) in
                                                ("phap", "japan", "korea", "china", "india", "france", "mexico",
                                                 "egypt", "kenya", "vietnam", "thailand")}, key=len, reverse=True)
        for k in keys:
            hit_found = False
            for hit in re.finditer(rf"(?<=\s){re.escape(k)}(?=\s)", m):
                window = m[max(0, hit.start() - 12): hit.end() + 12]
                if k in AMBIGUOUS and AMBIGUOUS[k].search(window):
                    continue
                span = (hit.start(), hit.end())
                if any(a < span[1] and span[0] < b for a, b in taken):
                    continue
                taken.append(span)
                found.append((hit.start(), c))
                hit_found = True
                break
            if hit_found:
                break
    seen, ordered = set(), []
    for _, c in sorted(found, key=lambda x: x[0]):
        if c.iso2 not in seen:
            seen.add(c.iso2)
            ordered.append(c)
    return ordered


def classify(message: str, countries_in_msg: list[Country]) -> Route:
    """structured: hỏi dữ kiện về đúng 1 nước | smalltalk: chào hỏi, không nhắc nước nào | còn lại: rag."""
    m = fold(message)
    for intent, pat in STRUCTURED:
        if pat.search(m) and len(countries_in_msg) == 1 and len(m.split()) <= 14:
            return Route("structured", countries_in_msg, intent)
    if not countries_in_msg and SMALLTALK.search(m) and len(m.split()) <= 10:
        return Route("smalltalk", [])
    return Route("rag", countries_in_msg)


def _join(items: list[object]) -> str:
    """["a", "b", "c"] → "a, b và c"."""
    items = [str(x) for x in items if x]
    return ", ".join(items[:-1]) + (" và " if len(items) > 1 else "") + items[-1] if items else ""


async def structured_answer(conn: AsyncConnection, route: Route, all_countries: list[Country]) -> str | None:
    """Câu trả lời dữ kiện lấy từ DB (không gọi LLM); None nếu DB thiếu dữ liệu → chuyển sang RAG."""
    c = route.countries[0]
    if route.intent == "capital" and c.capital:
        return f"Thủ đô của {c.name_vi} là **{c.capital}**."
    if route.intent == "currency" and c.currencies:
        return f"Đơn vị tiền tệ của {c.name_vi} là **{_join(c.currencies)}**."
    if route.intent == "languages" and c.languages:
        return f"Ngôn ngữ chính thức của {c.name_vi}: **{_join(c.languages)}**."
    if route.intent == "neighbors" and c.neighbors:
        names = {x.iso2: x.name_vi for x in all_countries}
        return f"{c.name_vi} giáp với: {_join([names.get(n, n) for n in c.neighbors])}."
    if route.intent == "heritage_count":
        row = (await conn.execute(text("""
            SELECT COUNT(*) FILTER (WHERE h.type = 'tangible'), COUNT(*) FILTER (WHERE h.type = 'intangible')
            FROM heritage_items h JOIN heritage_item_countries hc ON hc.heritage_item_id = h.id
            JOIN countries c ON c.id = hc.country_id WHERE c.iso2 = :iso"""), {"iso": c.iso2})).one()
        if row[0] or row[1]:
            return (f"Trong kho dữ liệu UNESCO của CultureAtlas, {c.name_vi} có **{row[0]} di sản vật thể** "
                    f"(Danh sách Di sản Thế giới) và **{row[1]} di sản văn hoá phi vật thể**.")
    return None

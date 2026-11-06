"""Bản ghi chuẩn hoá — khớp các bảng trong src/database/culture_atlas.sql. Mọi bản ghi mang provenance."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class Provenance:
    """Nguồn gốc của một bản ghi: nguồn, URL gốc, giấy phép, ngày lấy."""

    source_name: str          # khoá nguồn, ví dụ "unesco_whc"
    source_url: str           # URL bản ghi gốc
    license: str              # giấy phép áp dụng cho bản ghi
    retrieved_at: str = field(default_factory=lambda: date.today().isoformat())


@dataclass
class CountryRecord:
    """Quốc gia (Wikidata / REST Countries) → bảng countries."""

    iso2: str
    name_en: str
    capital: str | None = None
    region: str | None = None
    subregion: str | None = None
    languages: list[str] = field(default_factory=list)
    currencies: list[str] = field(default_factory=list)
    neighbors: list[str] = field(default_factory=list)
    population: int | None = None
    iso3: str | None = None
    iso_numeric: str | None = None
    provenance: Provenance | None = None
    kind: str = "country"


@dataclass
class HeritageRecord:
    """Di sản UNESCO (vật thể / phi vật thể) → heritage_items + heritage_item_countries."""

    unesco_id: str
    name: str
    type: str                 # tangible | intangible
    list_type: str
    countries: list[str]
    inscribed_year: int | None = None
    category: str | None = None
    criteria: str | None = None
    lat: float | None = None
    lng: float | None = None
    summary: str | None = None
    provenance: Provenance | None = None
    kind: str = "heritage"


@dataclass
class MediaRecord:
    """Ảnh / hiện vật bảo tàng → media_assets (file chỉ lưu khi giấy phép cho phép, BR09)."""

    country: str
    title: str
    url: str                  # trang bản ghi gốc
    image_url: str | None
    author: str | None
    license: str
    attribution_text: str
    local_path: str | None = None   # chỉ khi giấy phép cho phép lưu (CC0 / CC BY / CC BY-SA)
    verified: bool = False
    provenance: Provenance | None = None
    kind: str = "media"


@dataclass
class DocumentRecord:
    """Tài liệu tham khảo cho biên tập viên (không xuất bản trực tiếp). Nguồn có bản quyền chỉ lưu trích đoạn ngắn."""
    country: str
    title: str
    section: str
    text: str
    category_guess: str | None = None
    language: str = "en"
    excerpt_only: bool = False
    provenance: Provenance | None = None
    kind: str = "document"


@dataclass
class TopicRecord:
    """Chủ đề văn hoá từ bộ dữ liệu SCALE (món ăn, lễ hội, trang phục, địa danh)."""

    country: str
    aspect: str               # cuisine | holidays_and_festivals | clothing_and_accessories | landmarks
    item: str
    translation: str | None = None
    provenance: Provenance | None = None
    kind: str = "topic"


def to_dict(rec: object) -> dict:
    """Dataclass → dict (để ghi JSONL)."""
    return asdict(rec)

"""
UNESCO DataHub (Opendatasoft API) — whc001 (World Heritage List) và ich001 (Intangible Heritage Lists), CC BY-SA 4.0.
Không scrape whc.unesco.org / ich.unesco.org: robots.txt của hai trang này cấm bot / mô hình AI khi chưa được phép.
"""
from __future__ import annotations

import ast
from collections.abc import Iterator

from worker.core.models import HeritageRecord, Provenance
from worker.sources.base import Source

API = "https://data.unesco.org/api/explore/v2.1/catalog/datasets"


def _list(v: object) -> list:
    """Trường danh sách của DataHub (list hoặc chuỗi "[...]") → list."""
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.startswith("["):
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return []
    return []


def _point(v: object) -> tuple[float | None, float | None]:
    """Toạ độ (dict hoặc chuỗi "{...}") → (lat, lng)."""
    if isinstance(v, dict):
        return v.get("lat"), v.get("lon")
    if isinstance(v, str) and v.startswith("{"):
        try:
            d = ast.literal_eval(v)
            return d.get("lat"), d.get("lon")
        except (ValueError, SyntaxError):
            pass
    return None, None


def _short(s: str | None, n: int = 600) -> str | None:
    """Rút gọn văn bản tối đa `n` ký tự."""
    if not s or s == "None":
        return None
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def parse_whc(row: dict, wanted: set[str]) -> HeritageRecord | None:
    """Một dòng Danh sách Di sản Thế giới (whc001) → HeritageRecord vật thể, nếu thuộc nước cần lấy."""
    isos = [c.upper() for c in _list(row.get("iso_codes"))]
    hit = [c for c in isos if c in wanted]
    if not hit:
        return None
    lat, lng = _point(row.get("geo_point_2d"))
    return HeritageRecord(
        unesco_id=f"WHC-{row['id_no']}", name=row["name_en"].strip(), type="tangible",
        list_type="World Heritage List" + (" (in danger)" if str(row.get("danger")) == "True" else ""),
        countries=isos, inscribed_year=int(row["date_inscribed"]) if row.get("date_inscribed") else None,
        category=row.get("category"), criteria=row.get("criteria_txt"), lat=lat, lng=lng,
        summary=_short(row.get("short_description_en")),
        provenance=Provenance("unesco_whc", f"https://whc.unesco.org/en/list/{row['id_no']}", "CC BY-SA 4.0"))


def parse_ich(row: dict, wanted: set[str]) -> HeritageRecord | None:
    """Một dòng di sản phi vật thể (ich001) → HeritageRecord, nếu thuộc nước cần lấy."""
    isos = [c.upper() for c in _list(row.get("countries"))]
    if not any(c in wanted for c in isos):
        return None
    return HeritageRecord(
        unesco_id=f"ICH-{row['ich_public_ref']}", name=row["title_en"].strip(), type="intangible",
        list_type=row.get("type_of_element_en") or row.get("type_acronym") or "ICH",
        countries=isos, inscribed_year=int(row["inscription_year"]) if row.get("inscription_year") else None,
        category=", ".join(_list(row.get("concepts_primary_names"))[:4]) or None,
        summary=_short(row.get("description_en")),
        provenance=Provenance("unesco_ich", row.get("http_url_en") or "https://ich.unesco.org", "CC BY-SA 4.0"))


class _UnescoDataset(Source):
    """Tải trọn bộ dữ liệu UNESCO DataHub (export JSON) rồi lọc theo quốc gia."""

    dataset = ""
    parser = staticmethod(parse_whc)
    access, auth, license = "api", "none", "CC BY-SA 4.0"

    def collect(self) -> Iterator[HeritageRecord]:
        """Sinh bản ghi chuẩn hoá cho từng quốc gia; payload thô được lưu qua self.raw."""
        meta = self.ctx.http.get_json(f"{API}/{self.dataset}", respect_robots=False)
        self.raw.save("dataset_meta", meta)
        rows = self.ctx.http.get_json(f"{API}/{self.dataset}/exports/json", respect_robots=False)
        self.raw.save("export", rows)
        wanted = set(self.ctx.countries)
        per_country: dict[str, int] = {}
        for row in rows:
            rec = self.parser(row, wanted)
            if not rec:
                continue
            main = next(c for c in rec.countries if c in wanted)
            if self.ctx.limit and per_country.get(main, 0) >= self.ctx.limit:
                continue
            per_country[main] = per_country.get(main, 0) + 1
            yield rec


class UnescoWorldHeritage(_UnescoDataset):
    """Di sản thế giới UNESCO (vật thể) — CC BY-SA 4.0."""

    name, title, dataset = "unesco_whc", "UNESCO World Heritage List (DataHub whc001)", "whc001"
    homepage = "https://data.unesco.org/explore/dataset/whc001/"
    parser = staticmethod(parse_whc)


class UnescoIntangibleHeritage(_UnescoDataset):
    """Di sản văn hoá phi vật thể UNESCO — CC BY-SA 4.0."""

    name, title, dataset = "unesco_ich", "UNESCO Intangible Heritage Lists (DataHub ich001)", "ich001"
    homepage = "https://data.unesco.org/explore/dataset/ich001/"
    parser = staticmethod(parse_ich)

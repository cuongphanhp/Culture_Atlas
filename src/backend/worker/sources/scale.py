"""
SCALE Cultural Data (Google Research, GitHub). File Excel theo khía cạnh, mỗi sheet một quốc gia.
Repo chưa công bố giấy phép → chỉ dùng tham khảo taxonomy / gợi ý chủ đề, không xuất bản nguyên văn.
"""
from __future__ import annotations

import io
from collections.abc import Iterator

import openpyxl

from worker.core.models import Provenance, TopicRecord
from worker.sources.base import Source

RAW = "https://raw.githubusercontent.com/google-research-datasets/SCALE-Cultural-Data/main/data/{aspect}.xlsx"
ASPECTS = ("cuisine", "holidays_and_festivals", "clothing_and_accessories", "landmarks")
SHEETS = {"IN": "India", "KR": "South Korea", "CN": "China", "TH": "Thailand", "JP": "Japan", "MX": "Mexico", "FR": "France",
          "VN": "Vietnam", "EG": "Egypt", "KE": "Kenya"}


def parse_workbook(data: bytes, aspect: str, countries: dict[str, str], limit: int | None) -> list[TopicRecord]:
    """Một file Excel của SCALE (một khía cạnh) → TopicRecord cho các quốc gia cần lấy."""
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
    out = []
    for iso in countries:
        sheet = SHEETS.get(iso)
        if sheet not in wb.sheetnames:
            continue
        rows = [r for r in wb[sheet].iter_rows(values_only=True)][1:]
        for r in rows[: limit or None]:
            if r and r[0]:
                out.append(TopicRecord(country=iso, aspect=aspect, item=str(r[0]).strip(),
                                       translation=str(r[1]).strip() if len(r) > 1 and r[1] else None,
                                       provenance=Provenance("scale", RAW.format(aspect=aspect), "Unspecified — reference only")))
    return out


class ScaleCulturalData(Source):
    """Bộ dữ liệu SCALE (Google Research): gợi ý chủ đề món ăn, lễ hội, trang phục, địa danh."""

    name, title = "scale", "SCALE Cultural Data (Google Research)"
    access, auth, license = "file", "none", "Unspecified — reference only"
    homepage = "https://github.com/google-research-datasets/SCALE-Cultural-Data"

    def collect(self) -> Iterator[TopicRecord]:
        """Sinh bản ghi chuẩn hoá cho từng quốc gia; payload thô được lưu qua self.raw."""
        for aspect in ASPECTS:
            r = self.ctx.http.get(RAW.format(aspect=aspect))  # raw.githubusercontent.com — có kiểm tra robots.txt
            self.raw.save(f"{aspect}.xlsx", r.content)
            yield from parse_workbook(r.content, aspect, self.ctx.countries, self.ctx.limit)
        missing = [c for c in self.ctx.countries if SHEETS.get(c) not in ("India", "South Korea", "China", "Thailand", "Japan", "Mexico", "France")]
        if missing:
            self.run.skipped.append(f"SCALE không có dữ liệu cho: {', '.join(missing)}")

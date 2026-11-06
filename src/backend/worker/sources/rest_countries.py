"""
REST Countries v5 — cần token của người dùng (`REST_COUNTRIES_TOKEN`), gửi qua header `Authorization: Bearer`.
Không có token → nguồn bị bỏ qua; thông tin nền lấy từ Wikidata.
Parser chấp nhận cả cấu trúc kiểu v3 (name.common, capital[], languages{}, currencies{}, borders[]) vì định dạng v5
chưa được kiểm chứng trong dự án — dữ liệu thô luôn được lưu để chuẩn hoá lại.
"""
from __future__ import annotations

from collections.abc import Iterator

from worker.core.models import CountryRecord, Provenance
from worker.sources.base import Source

API = "https://api.restcountries.com/countries/v5"


def _names(v: object) -> list[str]:
    """Danh sách tên từ dict / list / chuỗi của REST Countries (ngôn ngữ, tiền tệ)."""
    if isinstance(v, dict):
        return sorted(str(x.get("name", x)) if isinstance(x, dict) else str(x) for x in v.values())
    if isinstance(v, list):
        return sorted(str(x.get("name", x)) if isinstance(x, dict) else str(x) for x in v)
    return [str(v)] if v else []


def parse_country(item: dict) -> CountryRecord | None:
    """Một bản ghi REST Countries → CountryRecord (None nếu thiếu mã ISO)."""
    iso2 = item.get("cca2") or item.get("iso2") or item.get("alpha2Code") or (item.get("codes") or {}).get("alpha2")
    if not iso2:
        return None
    name = item.get("name")
    name_en = name.get("common") if isinstance(name, dict) else name
    cap = item.get("capital")
    return CountryRecord(
        iso2=iso2.upper(), name_en=name_en or iso2, capital=cap[0] if isinstance(cap, list) and cap else cap,
        region=item.get("region"), subregion=item.get("subregion"), languages=_names(item.get("languages")),
        currencies=_names(item.get("currencies")), neighbors=_names(item.get("borders")),
        population=item.get("population"), iso3=item.get("cca3") or item.get("iso3"), iso_numeric=item.get("ccn3"),
        provenance=Provenance("rest_countries", "https://restcountries.com", "MPL-2.0"))


class RestCountries(Source):
    """REST Countries v5 (cần REST_COUNTRIES_TOKEN): thủ đô, ngôn ngữ, tiền tệ, láng giềng."""

    name, title = "rest_countries", "REST Countries v5"
    access, auth, license, homepage = "api", "bearer_token", "MPL-2.0", "https://restcountries.com"

    def available(self) -> tuple[bool, str]:
        """Chỉ chạy khi có token."""
        if not self.ctx.settings.rest_countries_token:
            return False, "chưa có REST_COUNTRIES_TOKEN"
        return True, ""

    def collect(self) -> Iterator[CountryRecord]:
        """Sinh bản ghi chuẩn hoá cho từng quốc gia; payload thô được lưu qua self.raw."""
        headers = {"Authorization": f"Bearer {self.ctx.settings.rest_countries_token}"}
        for iso, name in self.ctx.countries.items():
            data = self.ctx.http.get_json(API, respect_robots=False, params={"q": name}, headers=headers)
            self.raw.save(f"{iso}", data)
            items = data.get("data", data) if isinstance(data, dict) else data
            items = items if isinstance(items, list) else [items]
            for it in items:
                rec = parse_country(it) if isinstance(it, dict) else None
                if rec and rec.iso2 == iso:
                    yield rec
                    break

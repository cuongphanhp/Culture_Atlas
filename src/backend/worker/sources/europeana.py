"""
Europeana Search API (`EUROPEANA_WSKEY`). Phân trang bằng cursor, lọc `reusability=open`, lưu trường rights từng bản ghi.
Ảnh không tải về (giấy phép khác nhau theo bản ghi) — chỉ lưu URL preview + rights để biên tập viên xác minh.
"""
from __future__ import annotations

from collections.abc import Iterator

from worker.core.models import MediaRecord, Provenance
from worker.sources.base import Source

API = "https://api.europeana.eu/record/v2/search.json"
QUERIES: dict[str, list[str]] = {
    "VN": ["Vietnam costume", "Annam", "Tonkin"], "TH": ["Siam", "Thai costume"], "JP": ["ukiyo-e", "kimono", "Japanese netsuke"],
    "KR": ["Korean costume", "Korea ceramic"], "CN": ["Chinese porcelain", "Chinese painting"], "IN": ["Indian miniature", "India textile"],
    "FR": ["costume France", "French folk costume"], "MX": ["Mexican textile", "Aztec"], "EG": ["Egyptian amulet", "Egyptian papyrus"],
    "KE": ["Kenya beadwork", "Maasai"],
}
OPEN_RIGHTS = ("publicdomain", "/by/", "/by-sa/", "/zero/", "/mark/")


def parse_item(it: dict, iso: str) -> MediaRecord | None:
    """Một item Europeana → MediaRecord; chỉ giữ giấy phép mở (CC0 / PDM / CC BY / CC BY-SA)."""
    rights = (it.get("rights") or [""])[0]
    if not any(r in rights for r in OPEN_RIGHTS):
        return None
    url = (it.get("guid") or "").split("?")[0]
    provider = (it.get("dataProvider") or [""])[0]
    return MediaRecord(country=iso, title=(it.get("title") or [""])[0][:300], url=url, image_url=(it.get("edmPreview") or [None])[0],
                       author=provider, license=rights, attribution_text=f"{provider} via Europeana — {rights}", verified=False,
                       provenance=Provenance("europeana", url, rights))


class Europeana(Source):
    """Europeana Search API: hiện vật văn hoá có ảnh, theo từ khoá từng quốc gia."""

    name, title = "europeana", "Europeana Search API"
    access, auth, license, homepage = "api", "api_key", "Per record (rights field)", "https://pro.europeana.eu/page/apis"

    def collect(self) -> Iterator[MediaRecord]:
        """Sinh bản ghi chuẩn hoá cho từng quốc gia; payload thô được lưu qua self.raw."""
        key = self.ctx.settings.europeana_wskey
        target = self.ctx.limit or 12
        for iso in self.ctx.countries:
            got = 0
            for q in QUERIES.get(iso, []):
                cursor, pages = "*", 0
                while cursor and got < target and pages < 3:
                    data = self.ctx.http.get_json(API, respect_robots=False, headers={"X-Api-Key": key}, params={
                        "query": q, "rows": 24, "cursor": cursor, "reusability": "open",
                        "media": "true", "thumbnail": "true", "qf": "TYPE:IMAGE"})
                    self.raw.save(f"{iso}_{q}_{pages}", {k: v for k, v in data.items() if k not in ("apikey", "wskey")})
                    for it in data.get("items", []):
                        rec = parse_item(it, iso)
                        if rec:
                            got += 1
                            yield rec
                            if got >= target:
                                break
                    cursor, pages = data.get("nextCursor"), pages + 1
                if got >= target:
                    break

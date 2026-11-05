"""Wikimedia Commons API — ảnh minh hoạ văn hoá theo quốc gia, kèm tác giả + giấy phép từ extmetadata."""
from __future__ import annotations

import re

from worker.core.models import MediaRecord, Provenance
from worker.sources.base import Source

API = "https://commons.wikimedia.org/w/api.php"
TOPICS = ["traditional festival", "traditional costume", "traditional food", "temple"]
ALLOWED = ("CC0", "CC BY", "CC BY-SA", "Public domain", "PD")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def parse_page(pg: dict, iso: str) -> MediaRecord | None:
    ii = (pg.get("imageinfo") or [{}])[0]
    meta = ii.get("extmetadata", {})
    lic = meta.get("LicenseShortName", {}).get("value", "")
    if not lic.startswith(ALLOWED) or ii.get("width", 0) < 1000:
        return None
    author = _clean(meta.get("Artist", {}).get("value", ""))[:120]
    return MediaRecord(country=iso, title=pg["title"].removeprefix("File:"), url=ii.get("descriptionurl", ""),
                       image_url=ii.get("thumburl"), author=author, license=lic,
                       attribution_text=f"© {author or 'Wikimedia Commons'} · {lic}", verified=True,
                       provenance=Provenance("wikimedia_commons", ii.get("descriptionurl", ""), lic))


class WikimediaCommons(Source):
    name, title = "wikimedia_commons", "Wikimedia Commons"
    access, auth, license, homepage = "api", "none", "Per file (CC0 / CC BY / CC BY-SA / PD)", "https://commons.wikimedia.org"

    def collect(self):
        per_topic = max(1, (self.ctx.limit or 8) // len(TOPICS))
        for iso, country in self.ctx.countries.items():
            for topic in TOPICS:
                data = self.ctx.http.get_json(API, respect_robots=False, min_interval_s=3.0, params={
                    "action": "query", "format": "json", "generator": "search", "gsrnamespace": "6", "gsrlimit": "10",
                    "gsrsearch": f"{country} {topic} filetype:bitmap", "prop": "imageinfo",
                    "iiprop": "url|extmetadata|size", "iiurlwidth": "1280"})
                self.raw.save(f"{iso}_{topic}", data)
                pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
                kept = 0
                for pg in pages:
                    rec = parse_page(pg, iso)
                    if rec:
                        kept += 1
                        yield rec
                    if kept >= per_topic:
                        break

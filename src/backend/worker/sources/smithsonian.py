"""
Smithsonian Open Access API (api.data.gov key: `SMITHSONIAN_API_KEY`, mặc định DEMO_KEY bị giới hạn lượt).
Chỉ giữ media `usage.access == "CC0"`. Ảnh CC0 được tải về vì máy chủ ids.si.edu chặn hiển thị trực tiếp từ trình duyệt.
"""
from __future__ import annotations

from pathlib import Path

from requests import HTTPError
from requests.exceptions import RetryError

from worker.core.models import MediaRecord, Provenance
from worker.sources.base import Source

API = "https://api.si.edu/openaccess/api/v1.0/category/{cat}/search"
CATEGORIES = ("art_design", "history_culture")
PAGE = 100


def parse_row(row: dict, iso: str) -> MediaRecord | None:
    c = row.get("content", {})
    dnr = c.get("descriptiveNonRepeating", {})
    media = [m for m in dnr.get("online_media", {}).get("media", [])
             if m.get("usage", {}).get("access") == "CC0" and (m.get("thumbnail") or m.get("content"))]
    if not media:
        return None
    m = media[0]
    unit = dnr.get("data_source") or "Smithsonian Institution"
    url = dnr.get("record_link") or dnr.get("guid") or ""
    return MediaRecord(country=iso, title=row.get("title", "").strip(), url=url, image_url=m.get("thumbnail") or m.get("content"),
                       author=unit, license="CC0", attribution_text=f"{unit}, Smithsonian Open Access (CC0)", verified=True,
                       provenance=Provenance("smithsonian", url, "CC0"))


class SmithsonianOpenAccess(Source):
    name, title = "smithsonian", "Smithsonian Open Access"
    access, auth, license, homepage = "api", "api_key", "CC0 (Open Access records only)", "https://www.si.edu/openaccess"

    def collect(self):
        key = self.ctx.settings.smithsonian_api_key
        media_dir = self.ctx.settings.data_dir / "media" / "smithsonian"
        media_dir.mkdir(parents=True, exist_ok=True)
        target = self.ctx.limit or 12
        headers = {"X-Api-Key": key}  # khoá qua header, không nằm trong URL / log
        for iso, country in self.ctx.countries.items():
            try:
                yield from self._country(iso, country, headers, media_dir, target)
            except (RetryError, HTTPError) as e:
                if "429" in str(e) or "too many" in str(e).lower():
                    self.run.skipped.append("api.data.gov giới hạn lượt gọi (429) — đặt SMITHSONIAN_API_KEY riêng rồi chạy lại")
                    return
                self.run.error(iso, e)

    def _country(self, iso, country, headers, media_dir, target):
        got, seen = 0, set()
        for cat in CATEGORIES:
            start = 0
            while got < target and start < 400:  # phân trang theo start/rows
                data = self.ctx.http.get_json(API.format(cat=cat), respect_robots=False,
                                              params={"q": country, "start": start, "rows": PAGE}, headers=headers)
                rows = data.get("response", {}).get("rows", [])
                self.raw.save(f"{iso}_{cat}_{start}", {k: v for k, v in data.items() if k != "api_key"})
                if not rows:
                    break
                for row in rows:
                    rec = parse_row(row, iso)
                    if not rec or rec.title in seen:
                        continue
                    seen.add(rec.title)
                    rec.local_path = self._download(rec, media_dir, f"{iso.lower()}-{got}")
                    got += 1
                    yield rec
                    if got >= target:
                        break
                start += PAGE
            if got >= target:
                break

    def _download(self, rec: MediaRecord, media_dir: Path, stem: str) -> str | None:
        try:
            r = self.ctx.http.get(rec.image_url + ("&" if "?" in rec.image_url else "?") + "max=640", respect_robots=False,
                                  min_interval_s=0.3)
            if not r.headers.get("content-type", "").startswith("image/"):
                return None
            path = media_dir / f"{stem}.jpg"
            path.write_bytes(r.content)
            return str(path.relative_to(self.ctx.settings.data_dir))
        except Exception as e:  # noqa: BLE001
            self.run.error(f"download {rec.url}", e)
            return None

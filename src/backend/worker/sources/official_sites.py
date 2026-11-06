"""
Trang du lịch / văn hoá chính thức render bằng JavaScript → Selenium + BeautifulSoup.

Quy trình: đọc sitemap (hỗ trợ sitemap index lồng nhau) → lọc URL theo từ khoá → kiểm tra robots.txt từng URL →
render bằng Chrome headless (chờ nội dung, cuộn để nạp lazy-load) → BeautifulSoup tách tiêu đề/đoạn văn.

Nội dung có bản quyền: chỉ lưu TRÍCH ĐOẠN NGẮN (≤ 300 ký tự mỗi mục) + URL làm "đầu mối" cho biên tập viên viết bài
có trích dẫn. Gặp CAPTCHA / trang xác minh → bỏ qua URL, không cố vượt.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass

from bs4 import BeautifulSoup

from worker.core.browser import ChallengeDetected, chrome, render
from worker.core.http import RobotsDisallowed
from worker.core.models import DocumentRecord, Provenance
from worker.pipeline.classify import guess_category
from worker.sources.base import Source

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
EXCERPT = 300


@dataclass(frozen=True)
class SiteConfig:
    """Một trang du lịch chính thức: sitemap, mẫu URL cần lấy / bỏ, CSS chờ khi trang dùng JavaScript."""

    country: str
    publisher: str
    sitemap: str
    include: str                  # regex trên URL
    exclude: str = r"$^"
    lang_prefix: str = "/en/"
    wait_css: str = "main, article"


SITES: list[SiteConfig] = [
    SiteConfig("JP", "Japan National Tourism Organization", "https://www.japan.travel/sitemap.xml",
               include=r"(etiquette|manner|tips|custom|tradition|culture|onsen|temple|shrine|festival)",
               exclude=r"(luxury|sports/|greenexpo|model-courses|travel-directory)"),
    SiteConfig("VN", "Vietnam National Authority of Tourism", "https://vietnam.travel/sitemap.xml",
               include=r"(culture|tradition|festival|etiquette|tet|food)", lang_prefix="/",
               exclude=r"vietnam\.travel/[a-z]{2}(-[a-z]{2})?/"),  # bản dịch: /jp/, /pt/, /zh-tw/…
]


def parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    """Trả về (urls, sitemap con)."""
    root = ET.fromstring(xml_text.encode() if isinstance(xml_text, str) else xml_text)
    locs = [e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
    return (locs, []) if root.tag.endswith("urlset") else ([], locs)


def extract_sections(html: str) -> tuple[str, list[tuple[str, str]]]:
    """HTML trang → (tiêu đề, [(mục, văn bản)]); bỏ menu, footer, script."""
    soup = BeautifulSoup(html, "lxml")
    for bad in soup.select("script, style, noscript, nav, header, footer, aside, form, [aria-hidden=true]"):
        bad.decompose()
    title = (soup.find("h1") or soup.find("title"))
    title_txt = title.get_text(" ", strip=True) if title else ""
    main = soup.select_one("main, article, [role=main]") or soup.body or soup
    sections: list[tuple[str, list[str]]] = [(title_txt or "Introduction", [])]
    for el in main.find_all(["h2", "h3", "p", "li"]):
        txt = el.get_text(" ", strip=True)
        if not txt or "${" in txt:  # bỏ template chưa render
            continue
        if el.name in ("h2", "h3"):
            sections.append((txt, []))
        elif len(txt) > 40:
            sections[-1][1].append(txt)
    return title_txt, [(h, " ".join(p)) for h, p in sections if p]


class OfficialTourismSites(Source):
    """Trang du lịch quốc gia (JNTO, vietnam.travel): sitemap → trang văn hoá → trích đoạn ngắn."""

    name, title = "official_sites", "Official tourism sites (Selenium)"
    access, auth, license, homepage = "browser", "none", "All rights reserved — excerpts + links only", ""

    def _discover(self, cfg: SiteConfig, max_urls: int) -> list[str]:
        """Duyệt sitemap (kể cả sitemap con) → các URL khớp mẫu `include`, tối đa `max_urls`."""
        todo, urls, seen = [cfg.sitemap], [], set()
        while todo and len(seen) < 30:
            sm = todo.pop(0)
            if sm in seen:
                continue
            seen.add(sm)
            r = self.ctx.http.get(sm)  # respect_robots=True
            self.raw.save(f"sitemap_{cfg.country}_{len(seen)}.xml", r.text)
            found, children = parse_sitemap(r.text)
            todo += children
            inc, exc = re.compile(cfg.include, re.IGNORECASE), re.compile(cfg.exclude, re.IGNORECASE)
            urls += [u for u in found if cfg.lang_prefix in u and inc.search(u) and not exc.search(u)]
        return list(dict.fromkeys(urls))[:max_urls]

    def collect(self) -> Iterator[DocumentRecord]:
        """Sinh bản ghi chuẩn hoá cho từng quốc gia; payload thô được lưu qua self.raw."""
        max_pages = self.ctx.limit or 6
        sites = [s for s in SITES if s.country in self.ctx.countries]
        if not sites:
            return
        with chrome(self.ctx.settings) as driver:
            for cfg in sites:
                try:
                    urls = self._discover(cfg, max_pages)
                except Exception as e:  # noqa: BLE001
                    self.run.error(f"sitemap {cfg.sitemap}", e)
                    continue
                blocked = 0
                for url in urls:
                    try:
                        html = render(driver, self.ctx.http, url, wait_css=cfg.wait_css)
                    except RobotsDisallowed:
                        self.run.skipped.append(f"robots.txt: {url}")
                        continue
                    except ChallengeDetected:
                        self.run.skipped.append(f"bị chặn bot / trang xác minh — bỏ qua, không vượt: {url}")
                        blocked += 1
                        if blocked >= 2:  # site chặn có hệ thống → dừng cả site
                            self.run.skipped.append(f"dừng {cfg.publisher}: máy chủ chặn bot")
                            break
                        continue
                    except Exception as e:  # noqa: BLE001
                        self.run.error(url, e)
                        continue
                    self.raw.save(f"{cfg.country}_{url}.html", html)
                    title, sections = extract_sections(html)
                    for heading, text in sections[:8]:
                        yield DocumentRecord(
                            country=cfg.country, title=title or url, section=heading,
                            text=text[:EXCERPT] + ("…" if len(text) > EXCERPT else ""), excerpt_only=True,
                            category_guess=guess_category(heading, text[:1500]),
                            provenance=Provenance(self.name, url, f"© {cfg.publisher} — excerpt for reference"))

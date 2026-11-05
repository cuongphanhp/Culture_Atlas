"""
Wikipedia (CC BY-SA 4.0) qua API chính thức. Tìm bài "Etiquette in X" / "Culture of X", lấy HTML đã render
rồi dùng BeautifulSoup tách theo mục (h2/h3), làm sạch chú thích [1], gán danh mục gợi ý → tài liệu tham khảo cho biên tập.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from worker.core.models import DocumentRecord, Provenance
from worker.pipeline.classify import guess_category
from worker.sources.base import Source

API = "https://en.wikipedia.org/w/api.php"
SKIP_SECTIONS = {"see also", "references", "further reading", "external links", "notes", "bibliography", "sources", "citations"}
DEMONYM = {"VN": "Vietnamese", "TH": "Thai", "JP": "Japanese", "KR": "Korean", "CN": "Chinese", "IN": "Indian",
           "FR": "French", "MX": "Mexican", "EG": "Egyptian", "KE": "Kenyan"}


def parse_sections(html: str, min_chars: int = 200) -> list[tuple[str, str]]:
    """Trả về [(tiêu đề mục, văn bản)] từ HTML bài Wikipedia."""
    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one(".mw-parser-output") or soup
    for bad in root.select("sup.reference, .mw-editsection, table, style, script, .navbox, .reflist, .hatnote, figure, .thumb"):
        bad.decompose()
    sections: list[tuple[str, list[str]]] = [("Introduction", [])]
    for el in root.find_all(["h2", "h3", "p", "ul"], recursive=True):
        if el.name in ("h2", "h3"):
            sections.append((el.get_text(" ", strip=True), []))
        elif el.find_parent(["table", "nav"]) is None:
            txt = el.get_text(" ", strip=True)
            if txt:
                sections[-1][1].append(txt)
    out = []
    for title, parts in sections:
        text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        text = re.sub(r"\[\s*\d+\s*\]", "", text)
        if title.lower() not in SKIP_SECTIONS and len(text) >= min_chars:
            out.append((title, text))
    return out


class Wikipedia(Source):
    name, title = "wikipedia", "Wikipedia — etiquette & culture articles"
    access, auth, license, homepage = "api", "none", "CC BY-SA 4.0", "https://en.wikipedia.org"

    def _titles(self, iso: str, country: str) -> list[str]:
        candidates = [f"Etiquette in {country}", f"{DEMONYM[iso]} etiquette", f"Culture of {country}"]
        data = self.ctx.http.get_json(API, respect_robots=False, params={
            "action": "query", "format": "json", "titles": "|".join(candidates), "redirects": 1})
        pages = data.get("query", {}).get("pages", {}).values()
        found = [p["title"] for p in pages if "missing" not in p]
        return list(dict.fromkeys(found))[:2]

    def collect(self):
        for iso, country in self.ctx.countries.items():
            for title in self._titles(iso, country):
                data = self.ctx.http.get_json(API, respect_robots=False, params={
                    "action": "parse", "format": "json", "page": title, "prop": "text|revid", "redirects": 1,
                    "disableeditsection": 1, "formatversion": 2})
                html = data.get("parse", {}).get("text", "")
                self.raw.save(f"{iso}_{title}.html", html)
                url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
                for i, (section, text) in enumerate(parse_sections(html)):
                    if self.ctx.limit and i >= self.ctx.limit:
                        break
                    yield DocumentRecord(country=iso, title=title, section=section, text=text[:4000],
                                         category_guess=guess_category(section, text[:1500]),
                                         provenance=Provenance("wikipedia", f"{url}#{section.replace(' ', '_')}", "CC BY-SA 4.0"))

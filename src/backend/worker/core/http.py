"""HTTP client "lịch sự": robots.txt, giới hạn tốc độ theo domain, retry có backoff, User-Agent định danh."""
from __future__ import annotations

import logging
import threading
import time
import urllib.robotparser
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from worker.config import Settings

log = logging.getLogger(__name__)


class RobotsDisallowed(Exception):
    """URL bị robots.txt cấm với User-Agent của worker — không được thu thập."""


class RateLimiter:
    """Đảm bảo khoảng cách tối thiểu giữa hai request tới cùng một domain."""

    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = min_interval_s
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str, interval_s: float | None = None) -> float:
        """Chờ đủ khoảng cách tới request trước cùng domain; trả về số giây đã chờ."""
        interval = self.min_interval_s if interval_s is None else interval_s
        with self._lock:
            now = time.monotonic()
            sleep_for = max(0.0, self._last.get(host, 0.0) + interval - now)
            self._last[host] = now + sleep_for
        if sleep_for:
            time.sleep(sleep_for)
        return sleep_for


class RobotsCache:
    """Đọc và nhớ robots.txt theo domain (RFC 9309): bị chặn đọc / lỗi mạng → coi như cấm."""

    def __init__(self, session: requests.Session, user_agent: str, timeout: float) -> None:
        self.session, self.user_agent, self.timeout = session, user_agent, timeout
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def parser(self, url: str) -> urllib.robotparser.RobotFileParser:
        """Bộ phân tích robots.txt của domain chứa `url` (tải một lần)."""
        p = urlparse(url)
        root = f"{p.scheme}://{p.netloc}"
        if root not in self._parsers:
            rp = urllib.robotparser.RobotFileParser(root + "/robots.txt")
            try:
                r = self.session.get(root + "/robots.txt", timeout=self.timeout)
                if r.status_code in (401, 403):
                    rp.parse(["User-agent: *", "Disallow: /"])  # theo RFC 9309: bị chặn đọc robots → coi như cấm
                elif r.status_code >= 400:
                    rp.parse([])  # không có robots.txt → cho phép
                else:
                    rp.parse(r.text.splitlines())
            except requests.RequestException:
                rp.parse(["User-agent: *", "Disallow: /"])  # không kiểm tra được → không thu thập
            self._parsers[root] = rp
        return self._parsers[root]

    def allowed(self, url: str) -> bool:
        """User-Agent của worker có được thu thập `url` không."""
        return self.parser(url).can_fetch(self.user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        """Crawl-delay mà robots.txt yêu cầu (giây), None nếu không có."""
        d = self.parser(url).crawl_delay(self.user_agent)
        return float(d) if d else None


class PoliteSession:
    """
    `respect_robots=True` cho mọi request thu thập trang HTML.
    Với API chính thức có tài liệu và giấy phép (UNESCO DataHub, Smithsonian, Europeana…), nguồn truyền
    `respect_robots=False` vì việc dùng API được điều chỉnh bởi điều khoản API, không phải robots.txt.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent, "Accept-Language": "en,vi;q=0.8"})
        retry = Retry(total=settings.max_retries, backoff_factor=1.5, respect_retry_after_header=False,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET", "HEAD"))
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.limiter = RateLimiter(settings.min_interval_s)
        self.robots = RobotsCache(self.session, settings.user_agent, settings.timeout_s)

    def get(self, url: str, *, respect_robots: bool = True, params: dict | None = None,
            headers: dict | None = None, min_interval_s: float | None = None) -> requests.Response:
        """GET có kiểm tra robots.txt, giãn cách theo domain, retry; lỗi HTTP → ném requests.HTTPError."""
        if respect_robots and not self.robots.allowed(url):
            raise RobotsDisallowed(url)
        interval = min_interval_s
        if respect_robots:
            interval = max(interval or 0, self.robots.crawl_delay(url) or 0) or None
        self.limiter.wait(urlparse(url).netloc, interval)
        r = self.session.get(url, params=params, headers=headers, timeout=self.settings.timeout_s)
        log.debug("GET %s → %s", r.url.split("?")[0], r.status_code)
        r.raise_for_status()
        return r

    def get_json(self, url: str, **kw: Any) -> dict | list:
        """GET rồi parse JSON."""
        return self.get(url, **kw).json()

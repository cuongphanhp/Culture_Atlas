"""Selenium (Chrome headless) cho các trang render bằng JavaScript. Không vượt CAPTCHA / đăng nhập / anti-bot."""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from worker.config import Settings
from worker.core.http import PoliteSession, RobotsDisallowed

log = logging.getLogger(__name__)

# Dấu hiệu trang yêu cầu xác minh người dùng → dừng lại, không cố vượt qua.
CHALLENGE_MARKERS = ("captcha", "cf-challenge", "are you a robot", "verify you are human", "access denied",
                     "403 error", "request blocked", "the request could not be satisfied")


class ChallengeDetected(Exception):
    """Trang trả về thử thách xác minh hoặc chặn bot (CAPTCHA / 403 / WAF). Worker bỏ qua URL này, không cố vượt."""


@contextmanager
def chrome(settings: Settings) -> Iterator[webdriver.Chrome]:
    """Chrome headless (Selenium) cho trang cần JavaScript; tự đóng khi ra khỏi `with`."""
    opts = webdriver.ChromeOptions()
    if settings.headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument(f"--user-agent={settings.user_agent}")  # định danh trung thực, không giả làm trình duyệt người dùng
    if settings.chrome_binary:
        opts.binary_location = settings.chrome_binary
    driver = webdriver.Chrome(options=opts)  # Selenium Manager tự tìm chromedriver khớp phiên bản Chrome
    driver.set_page_load_timeout(settings.timeout_s * 2)
    try:
        yield driver
    finally:
        driver.quit()


def render(driver: webdriver.Chrome, http: PoliteSession, url: str, *, wait_css: str = "main, article, body",
           scroll_rounds: int = 3, timeout_s: float = 20) -> str:
    """Mở URL (đã kiểm tra robots.txt), chờ nội dung, cuộn để nạp phần lazy-load, trả về HTML đã render."""
    if not http.robots.allowed(url):
        raise RobotsDisallowed(url)
    http.limiter.wait(url.split("/")[2], http.robots.crawl_delay(url))
    driver.get(url)
    head = driver.page_source[:5000].lower()
    if len(driver.page_source) < 5000 and any(m in head for m in CHALLENGE_MARKERS):
        raise ChallengeDetected(url)  # trang chặn ngắn → dừng sớm, không chờ
    try:
        WebDriverWait(driver, timeout_s).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_css)))
    except TimeoutException:
        log.warning("Hết thời gian chờ %s tại %s", wait_css, url)
    last_h = 0
    for _ in range(scroll_rounds):  # cuộn vô hạn / lazy-load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.0)
        h = driver.execute_script("return document.body.scrollHeight")
        if h == last_h:
            break
        last_h = h
    html = driver.page_source
    if any(m in html[:20000].lower() for m in CHALLENGE_MARKERS) and len(html) < 60000:
        raise ChallengeDetected(url)
    return html

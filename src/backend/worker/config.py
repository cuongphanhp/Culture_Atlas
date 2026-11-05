"""Cấu hình worker, đọc từ biến môi trường (xem .env.example ở gốc repo)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 10 quốc gia giai đoạn MVP: ISO alpha-2 → tên tiếng Anh dùng cho truy vấn.
MVP_COUNTRIES: dict[str, str] = {
    "VN": "Vietnam", "TH": "Thailand", "JP": "Japan", "KR": "South Korea", "CN": "China",
    "IN": "India", "FR": "France", "MX": "Mexico", "EG": "Egypt", "KE": "Kenya",
}


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("WORKER_DATA_DIR", Path(__file__).resolve().parents[1] / "data")))
    user_agent: str = os.getenv(
        "WORKER_USER_AGENT", "CultureAtlasBot/0.1 (+https://github.com/cuongphanhp/Culture_Atlas; education project)")
    min_interval_s: float = float(os.getenv("WORKER_MIN_INTERVAL_S", "1.0"))  # giãn cách tối thiểu mỗi domain
    timeout_s: float = float(os.getenv("WORKER_TIMEOUT_S", "30"))
    max_retries: int = int(os.getenv("WORKER_MAX_RETRIES", "4"))
    # Khoá / token do người dùng cung cấp — không bao giờ ghi vào log hay dữ liệu thô.
    smithsonian_api_key: str = os.getenv("SMITHSONIAN_API_KEY", "DEMO_KEY")
    europeana_wskey: str = os.getenv("EUROPEANA_WSKEY", "api2demo")
    rest_countries_token: str = os.getenv("REST_COUNTRIES_TOKEN", "")
    database_url: str = os.getenv("WORKER_DATABASE_URL", "")
    headless: bool = os.getenv("WORKER_HEADLESS", "1") != "0"
    chrome_binary: str = os.getenv("WORKER_CHROME_BINARY", "")


def countries_from_arg(arg: str | None) -> dict[str, str]:
    if not arg:
        return dict(MVP_COUNTRIES)
    wanted = [c.strip().upper() for c in arg.split(",") if c.strip()]
    unknown = [c for c in wanted if c not in MVP_COUNTRIES]
    if unknown:
        raise SystemExit(f"Quốc gia chưa hỗ trợ: {', '.join(unknown)}")
    return {c: MVP_COUNTRIES[c] for c in wanted}

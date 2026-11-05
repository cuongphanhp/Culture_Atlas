"""Lưu dữ liệu thô (để chuẩn hoá lại mà không gọi lại nguồn), bản ghi chuẩn hoá (JSONL) và nhật ký mỗi lần chạy."""
from __future__ import annotations

import hashlib
import json
import re
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from worker.core.models import to_dict


SECRET_PARAMS = re.compile(r"(?i)\b(api_key|api-key|apikey|wskey|key|token|access_token)=([^&\s'\"]+)")


def redact(text: str) -> str:
    """Che khoá / token trong URL hoặc thông báo lỗi trước khi ghi log."""
    return SECRET_PARAMS.sub(r"\1=***", text)


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:120]


class RawStore:
    """`secrets`: giá trị khoá/token đang cấu hình — được thay bằng *** trước khi ghi (một số API nhúng khoá vào link trả về)."""

    def __init__(self, root: Path, source: str, run_id: str, secrets: tuple[str, ...] = ()):
        self.dir = root / "raw" / source / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.secrets = tuple(s for s in secrets if s and len(s) >= 4)

    def _clean(self, text: str) -> str:
        for s in self.secrets:
            text = text.replace(s, "***")
        return redact(text)

    def save(self, name: str, payload: str | bytes | dict | list) -> Path:
        path = self.dir / _slug(name)
        if isinstance(payload, (dict, list)):
            path = path.with_suffix(".json")
            path.write_text(self._clean(json.dumps(payload, ensure_ascii=False, indent=1)), encoding="utf-8")
        elif isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(self._clean(payload), encoding="utf-8")
        return path


def record_countries(d: dict) -> set[str]:
    return {c for c in [d.get("iso2"), d.get("country"), *(d.get("countries") or [])] if c}


class RecordWriter:
    """
    Ghi bản ghi chuẩn hoá ra data/normalized/<source>.jsonl, khử trùng theo khoá.
    Chỉ thay bản ghi của các quốc gia trong lượt chạy hiện tại; bản ghi của quốc gia khác được giữ nguyên.
    """

    def __init__(self, root: Path, source: str, countries: set[str] | None = None):
        self.path = root / "normalized" / f"{source}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        kept: list[str] = []
        if countries is not None and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip() and not (record_countries(json.loads(line)) & countries):
                    kept.append(line)
        self._seen: set[str] = {self.key(json.loads(line)) for line in kept}
        self._fh = self.path.open("w", encoding="utf-8")
        for line in kept:
            self._fh.write(line + "\n")
        self.count = 0

    @staticmethod
    def key(d: dict) -> str:
        ident = [d.get("kind"), d.get("iso2") or d.get("unesco_id") or d.get("url") or "", d.get("country"),
                 d.get("section"), d.get("item"), d.get("title")]
        return hashlib.sha1(json.dumps(ident, ensure_ascii=False).encode()).hexdigest()

    def write(self, rec) -> bool:
        d = to_dict(rec)
        k = self.key(d)
        if k in self._seen:
            return False
        self._seen.add(k)
        self._fh.write(json.dumps(d, ensure_ascii=False) + "\n")
        self.count += 1
        return True

    def close(self) -> None:
        self._fh.close()


@dataclass
class RunLog:
    """Tương ứng bảng ingestion_runs."""
    source_name: str
    run_id: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    status: str = "running"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    records_in: int = 0
    records_changed: int = 0
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    _t0: float = field(default_factory=time.monotonic, repr=False)

    def error(self, where: str, exc: BaseException) -> None:
        self.errors.append(redact(f"{where}: {type(exc).__name__}: {exc}")[:500])

    def finish(self, root: Path) -> Path:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        if self.status == "running":
            self.status = "failed" if self.errors and not self.records_changed else "succeeded"
        out = root / "runs" / f"{self.run_id}_{self.source_name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        d = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        d["duration_s"] = round(time.monotonic() - self._t0, 1)
        out.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return out


def format_exc() -> str:
    return traceback.format_exc(limit=3)

"""Khung chung cho một nguồn dữ liệu: fetch → lưu thô → parse → ghi bản ghi chuẩn hoá → nhật ký."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from worker.config import Settings
from worker.core.http import PoliteSession, RobotsDisallowed
from worker.core.storage import RawStore, RecordWriter, RunLog

log = logging.getLogger(__name__)


@dataclass
class Context:
    """Ngữ cảnh một lượt chạy: cấu hình, HTTP client lịch sự, các quốc gia cần lấy, giới hạn bản ghi."""

    settings: Settings
    http: PoliteSession
    countries: dict[str, str]
    limit: int | None = None     # giới hạn số bản ghi mỗi quốc gia (chạy thử)


class Source(ABC):
    """Một nguồn dữ liệu. Lớp con khai báo metadata (tên, giấy phép, cách truy cập) và cài `collect()`."""

    name: str = ""
    title: str = ""
    access: str = "api"          # api | html | browser | file
    auth: str = "none"           # none | api_key | bearer_token
    license: str = ""
    homepage: str = ""

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.run = RunLog(self.name)
        st = ctx.settings
        self.raw = RawStore(st.data_dir, self.name, self.run.run_id,
                            secrets=(st.smithsonian_api_key, st.europeana_wskey, st.rest_countries_token))
        self.out = RecordWriter(st.data_dir, self.name, countries=set(ctx.countries))

    def available(self) -> tuple[bool, str]:
        """Nguồn có chạy được không (ví dụ thiếu token)."""
        return True, ""

    @abstractmethod
    def collect(self) -> Iterable:
        """Sinh các bản ghi chuẩn hoá (đã lưu dữ liệu thô bên trong)."""

    def execute(self) -> RunLog:
        """Chạy trọn một lượt: kiểm tra điều kiện, thu thập, ghi bản ghi, ghi nhật ký; lỗi không làm dừng worker."""
        ok, why = self.available()
        if not ok:
            self.run.status = "skipped"
            self.run.skipped.append(why)
            log.warning("[%s] bỏ qua: %s", self.name, why)
        else:
            try:
                for rec in self.collect():
                    self.run.records_in += 1
                    if self.out.write(rec):
                        self.run.records_changed += 1
            except RobotsDisallowed as e:
                self.run.skipped.append(f"robots.txt cấm: {e}")
            except Exception as e:
                log.exception("[%s] lỗi", self.name)
                self.run.error("collect", e)
        self.out.close()
        path = self.run.finish(self.ctx.settings.data_dir)
        log.info("[%s] %s · %d bản ghi · %d lỗi · %s", self.name, self.run.status, self.run.records_changed,
                 len(self.run.errors), path.name)
        return self.run

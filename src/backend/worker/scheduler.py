"""
Lịch đồng bộ định kỳ (APScheduler). Chạy: python -m worker.scheduler
Tần suất theo mức thay đổi của nguồn: UNESCO cập nhật sau mỗi kỳ họp hằng năm; museum/ảnh thay đổi thường xuyên hơn.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from worker.cli import main as cli

SCHEDULE = {
    "wikidata rest_countries": CronTrigger(day=1, hour=2),                        # hằng tháng
    "unesco_whc unesco_ich": CronTrigger(day_of_week="mon", hour=3),            # hằng tuần
    "smithsonian europeana wikimedia_commons": CronTrigger(day_of_week="tue", hour=3),
    "wikipedia official_sites": CronTrigger(day_of_week="wed", hour=3),
    "scale": CronTrigger(month="1,7", day=1, hour=4),                           # 6 tháng
}


def job(names: str) -> None:
    """Chạy nhóm nguồn rồi nạp lại DB."""
    cli(["run", *names.split()])
    cli(["load"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sched = BlockingScheduler(timezone="Asia/Ho_Chi_Minh")
    for names, trigger in SCHEDULE.items():
        sched.add_job(job, trigger, args=[names], id=names.replace(" ", "+"), max_instances=1, coalesce=True)
    sched.start()

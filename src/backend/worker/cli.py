"""
CLI của worker.

  python -m worker.cli sources                         # liệt kê nguồn, loại truy cập, xác thực, giấy phép
  python -m worker.cli run unesco_whc wikipedia --countries JP,VN --limit 5
  python -m worker.cli run-all [--skip official_sites]
  python -m worker.cli aggregate                       # gộp → data/aggregated + data/report.md
  python -m worker.cli load --dsn postgresql://...     # upsert vào PostgreSQL
"""
from __future__ import annotations

import argparse
import logging
import sys

from worker.config import Settings, countries_from_arg
from worker.core.http import PoliteSession
from worker.pipeline.aggregate import aggregate
from worker.sources import REGISTRY
from worker.sources.base import Context


def _ctx(args) -> Context:
    settings = Settings()
    return Context(settings=settings, http=PoliteSession(settings), countries=countries_from_arg(args.countries), limit=args.limit)


def run_sources(names: list[str], args) -> int:
    ctx = _ctx(args)
    failed = 0
    for name in names:
        if name not in REGISTRY:
            print(f"Nguồn không tồn tại: {name}. Dùng `sources` để xem danh sách.", file=sys.stderr)
            return 2
        run = REGISTRY[name](ctx).execute()
        failed += run.status == "failed"
    summary = aggregate(ctx.settings.data_dir)
    print(f"\nĐã tổng hợp: {summary['countries']} quốc gia · {summary['heritage']} di sản · {summary['media']} media · "
          f"{summary['documents']} tài liệu · {summary['topics']} chủ đề → {ctx.settings.data_dir / 'report.md'}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="worker")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sources")
    for name in ("run", "run-all"):
        p = sub.add_parser(name)
        if name == "run":
            p.add_argument("names", nargs="+")
        else:
            p.add_argument("--skip", default="")
        p.add_argument("--countries", help="ISO alpha-2, phân tách bằng dấu phẩy (mặc định 10 nước MVP)")
        p.add_argument("--limit", type=int, help="giới hạn bản ghi mỗi quốc gia (chạy thử)")
    sub.add_parser("aggregate")
    p = sub.add_parser("load")
    p.add_argument("--dsn", default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)

    if args.cmd == "sources":
        print(f"{'name':<18} {'access':<8} {'auth':<13} license")
        for name, cls in REGISTRY.items():
            print(f"{name:<18} {cls.access:<8} {cls.auth:<13} {cls.license}")
        return 0
    if args.cmd == "run":
        return run_sources(args.names, args)
    if args.cmd == "run-all":
        skip = {s.strip() for s in args.skip.split(",") if s.strip()}
        return run_sources([n for n in REGISTRY if n not in skip], args)
    if args.cmd == "aggregate":
        print(aggregate(Settings().data_dir)["sources"])
        return 0
    if args.cmd == "load":
        from worker.pipeline.loader import load
        settings = Settings()
        dsn = args.dsn or settings.database_url
        if not dsn:
            print("Thiếu --dsn hoặc WORKER_DATABASE_URL", file=sys.stderr)
            return 2
        print(load(settings.data_dir, dsn))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

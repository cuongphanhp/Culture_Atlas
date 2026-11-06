"""
CLI của worker.

  python -m worker.cli sources                         # liệt kê nguồn, loại truy cập, xác thực, giấy phép
  python -m worker.cli run unesco_whc wikipedia --countries JP,VN --limit 5
  python -m worker.cli run-all [--skip official_sites]
  python -m worker.cli aggregate                       # gộp → data/aggregated + data/report.md
  python -m worker.cli load --dsn postgresql://...     # upsert vào PostgreSQL (+ file media → object storage)
  python -m worker.cli seed-media ../media-seed        # ảnh tuyển chọn của giao diện → object storage + media_assets
  python -m worker.cli index                           # chỉ mục RAG: văn bản ở PostgreSQL, embedding ở Qdrant
Object storage bật khi có S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY (xem .env.example).
"""
from __future__ import annotations

import argparse
import logging
import sys

from worker.config import Settings, countries_from_arg
from worker.core.http import PoliteSession
from worker.core.objectstore import ObjectStore
from worker.pipeline.aggregate import aggregate
from worker.pipeline.media_seed import archive_raw
from worker.sources import REGISTRY
from worker.sources.base import Context


def _ctx(args: argparse.Namespace) -> Context:
    """Ngữ cảnh chạy nguồn từ tham số dòng lệnh."""
    settings = Settings()
    return Context(settings=settings, http=PoliteSession(settings), countries=countries_from_arg(args.countries), limit=args.limit)


def run_sources(names: list[str], args: argparse.Namespace) -> int:
    """Chạy các nguồn, lưu payload thô vào bucket riêng tư, rồi gộp dữ liệu; mã thoát 1 nếu có nguồn lỗi."""
    ctx = _ctx(args)
    store = ObjectStore.from_env()
    failed = 0
    for name in names:
        if name not in REGISTRY:
            print(f"Nguồn không tồn tại: {name}. Dùng `sources` để xem danh sách.", file=sys.stderr)
            return 2
        run = REGISTRY[name](ctx).execute()
        failed += run.status == "failed"
        if store is not None:          # payload thô → bucket riêng tư của object storage
            try:
                n = archive_raw(store, ctx.settings.data_dir, name, run.run_id)
                logging.getLogger(__name__).info("[%s] đã lưu %d file thô vào object storage", name, n)
            except Exception as e:  # noqa: BLE001 — không làm hỏng lần thu thập
                logging.getLogger(__name__).warning("[%s] không lưu được file thô vào object storage: %s", name, e)
    summary = aggregate(ctx.settings.data_dir)
    print(f"\nĐã tổng hợp: {summary['countries']} quốc gia · {summary['heritage']} di sản · {summary['media']} media · "
          f"{summary['documents']} tài liệu · {summary['topics']} chủ đề → {ctx.settings.data_dir / 'report.md'}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Điểm vào CLI (xem docstring đầu file); trả mã thoát."""
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
    p.add_argument("--no-fetch-media", action="store_true", help="không tải media còn ở dạng liên kết lên object storage")
    p = sub.add_parser("seed-media", help="ảnh tuyển chọn (src/media-seed) → object storage + media_assets")
    p.add_argument("dir")
    p.add_argument("--dsn", default=None)
    p = sub.add_parser("index", help="chia đoạn + embedding cho AI Guide (cần dịch vụ AI local)")
    p.add_argument("--dsn", default=None)
    p.add_argument("--ai-local-url", default=None, help="mặc định: biến AI_LOCAL_URL hoặc http://localhost:8100")
    p.add_argument("--kinds", default="claim,reference,heritage")
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
        store = ObjectStore.from_env()
        if store is None:
            print("⚠ Chưa cấu hình object storage (S3_ENDPOINT…) — file media sẽ KHÔNG được lưu, chỉ ghi metadata + liên kết",
                  file=sys.stderr)
        from worker.pipeline.loader import http_fetch
        fetch = None if args.no_fetch_media or store is None else http_fetch(settings.user_agent)
        print(load(settings.data_dir, dsn, store, fetch))
        return 0
    if args.cmd == "seed-media":
        from pathlib import Path

        from worker.pipeline.media_seed import seed
        dsn = args.dsn or Settings().database_url
        store = ObjectStore.from_env()
        if not dsn or store is None:
            print("Cần --dsn/WORKER_DATABASE_URL và S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY", file=sys.stderr)
            return 2
        print(seed(Path(args.dir), dsn, store))
        return 0
    if args.cmd == "index":
        import os

        import psycopg

        from worker.pipeline.indexer import http_embedder, index
        dsn = args.dsn or Settings().database_url
        if not dsn:
            print("Thiếu --dsn hoặc WORKER_DATABASE_URL", file=sys.stderr)
            return 2
        url = args.ai_local_url or os.getenv("AI_LOCAL_URL", "http://localhost:8100")
        with psycopg.connect(dsn, autocommit=True) as conn:
            print(index(conn, http_embedder(url), [k.strip() for k in args.kinds.split(",") if k.strip()]))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

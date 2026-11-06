#!/usr/bin/env python3
"""Sinh mục "Bản đồ file" của docs/PROJECT_OVERVIEW.md từ chính mã nguồn.

Mô tả mỗi file lấy từ:
- .py: docstring đầu module · .ts: chú thích /** … */ hoặc // đầu file · .sql / .sh: dòng chú thích đầu file;
- các file còn lại (cấu hình, dữ liệu, template): bảng FILE_NOTES / PATTERN_NOTES bên dưới.

    python3 scripts/project_overview.py          # cập nhật docs/PROJECT_OVERVIEW.md
    python3 scripts/project_overview.py --check  # thoát 1 nếu tài liệu đã cũ hoặc có file chưa có mô tả (scripts/test.sh)

Thêm file mới → viết docstring / chú thích đầu file (hoặc thêm vào FILE_NOTES) rồi chạy lại script.
"""
from __future__ import annotations

import ast
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "PROJECT_OVERVIEW.md"
BEGIN, END = "<!-- FILE-MAP:BEGIN (tự sinh bởi scripts/project_overview.py — không sửa tay) -->", "<!-- FILE-MAP:END -->"
MAX_LEN = 170

# Không liệt kê: dữ liệu thu thập, ảnh, file sinh tự động
SKIP = ["src/backend/data/*", "src/media-seed/*.jpg", "src/media-seed/*.jpeg", "src/media-seed/*.png", "src/media-seed/*.webp",
        "*.egg-info/*", "*.pptx", "*.xmind", "docs/images/*", "docs/*.png", "docs/PROJECT_OVERVIEW.md", "*/package-lock.json"]

DIR_NOTES: dict[str, str] = {
    ".": "Gốc repo: cấu hình chạy toàn bộ app, quy tắc làm việc, hướng dẫn.",
    "docs": "Tài liệu sản phẩm: phạm vi, tính năng, tiêu chí chấp nhận (AC), mô hình dữ liệu, lộ trình.",
    "scripts": "Script vận hành: chạy dev, chạy test, quét lỗ hổng image, nạp model AI.",
    "src/backend": "API FastAPI (app/) + worker thu thập dữ liệu (worker/) + bộ test chấp nhận (tests/). Python 3.13.",
    "src/backend/app": "API phục vụ người dùng.",
    "src/backend/app/ai": "AI Guide: phân tuyến câu hỏi, truy xuất lai, gọi LLM, kiểm tra trích dẫn, gợi ý câu hỏi.",
    "src/backend/app/ai/prompts": "Prompt và dữ liệu tĩnh của AI Guide.",
    "src/backend/worker": "Worker: thu thập nguồn mở → chuẩn hoá → gộp → nạp PostgreSQL / MinIO / Qdrant.",
    "src/backend/worker/sources": "Mỗi file một nguồn dữ liệu (lớp con của Source).",
    "src/backend/tests": "Bộ test (pytest). Test bám mã AC qua @ac / @route; dịch vụ ngoài được thay bằng bản giả.",
    "src/backend/tests/acceptance": "Test chấp nhận theo nhóm tính năng F1–F10.",
    "src/ai-local": "Dịch vụ AI local (Python 3.12, ONNX, không torch lúc chạy): STT, TTS, embedding, rerank.",
    "src/frontend": "Giao diện Angular 22 (zoneless, standalone components, Vitest).",
    "src/frontend/src/app/features": "Mỗi thư mục một trang: *.page.ts (logic) + .html (template) + .css + .spec.ts (test).",
    "src/database": "Schema PostgreSQL (nguồn sự thật: .dbml) và migration cho DB đã tạo trước.",
    "src/media-seed": "Ảnh tuyển chọn của giao diện + ghi công; nạp lên object storage bằng `worker.cli seed-media`.",
    "src/object-storage": "Image MinIO đã hardening (ngoại lệ bảo mật EX-001).",
}

FILE_NOTES: dict[str, str] = {
    "CLAUDE.md": "Quy tắc làm việc cho AI / người đóng góp: test bắt buộc, model được phép, Docker, lưu trữ, code sạch.",
    "README.md": "Giới thiệu dự án.",
    "Guide.md": "Hướng dẫn chạy toàn bộ app (Cách A: conda/venv, Cách B: Docker Compose).",
    "docker-production-skill.md": "Chuẩn build Docker production (multi-stage, non-root, quét CVE…) mà các Dockerfile tuân theo.",
    "compose.yaml": "Docker Compose chạy toàn bộ app: db, object-storage, qdrant, ai-local, api, worker, web.",
    "compose.test.yaml": "Hạ tầng cho bộ test: PostgreSQL 55432, MinIO 59000, Qdrant 56333 (dữ liệu trong RAM).",
    ".env.example": "Mẫu biến môi trường (OpenAI, DB, S3/MinIO, Qdrant, AI local, cổng). Bản thật `.env` không commit.",
    ".gitignore": "File / thư mục không đưa vào git.",
    ".githooks/pre-commit": "Chặn commit nếu test của phần đã sửa fail (bật: git config core.hooksPath .githooks).",
    ".github/workflows/tests.yml": "CI: ruff + pytest backend, ai-local; build + quét CVE image; test + build frontend.",
    ".vscode/tasks.json": "VS Code Tasks chạy từng thành phần ở chế độ dev (scripts/dev.sh).",
    "docs/01-scope.md": "Phạm vi MVP.", "docs/02-features.md": "Danh sách tính năng F1–F10.",
    "docs/03-use-cases.md": "Use case.", "docs/04-information-architecture.md": "Kiến trúc thông tin / sơ đồ trang.",
    "docs/05-data-model.md": "Mô hình dữ liệu (giải thích).", "docs/06-acceptance-criteria.md": "Tiêu chí chấp nhận ACxx.y — test bám theo file này.",
    "docs/08-invest-requirements.md": "User story theo INVEST.", "docs/09-data-ingestion.md": "Thiết kế thu thập dữ liệu, nguồn, giấy phép.",
    "docs/10-roadmap.md": "Lộ trình nâng cấp.", "docs/11-vietnamese-chat-stack.md": "Lựa chọn model AI (LLM OpenAI + AI local) và số đo.",
    "docs/DATABASE.md": "Hướng dẫn DB: bảng, view, quy tắc.", "docs/security-exceptions.md": "Ngoại lệ bảo mật đã ghi nhận (EX-001: MinIO).",
    "docs/api/openapi.yaml": "Hợp đồng API (OpenAPI 3) — nguồn sự thật cho backend và frontend.",
    "docs/mindmap/mindmap.html": "Sơ đồ tư duy tương tác của dự án.", "docs/mindmap/mindmap-data.json": "Dữ liệu sơ đồ tư duy (tiếng Việt).",
    "docs/mindmap/mindmap-data.en.json": "Dữ liệu sơ đồ tư duy (tiếng Anh).",
    "docs/requirements/business-rules.md": "Quy tắc nghiệp vụ BR01–BR09.",
    "docs/requirements/non-functional-requirements.md": "Yêu cầu phi chức năng (hiệu năng, bảo mật…).",
    "src/backend/Dockerfile": "Image API + worker (multi-stage, non-root, read-only).",
    "src/backend/pyproject.toml": "Thư viện Python của backend + cấu hình pytest / ruff (bắt buộc docstring, type hint).",
    "src/backend/requirements.lock": "Phiên bản thư viện khoá cho image Docker.",
    "src/backend/tests/README.md": "Cách viết / chạy test, cơ chế PENDING và truy vết AC.",
    "src/backend/tests/fixtures/seed.sql": "Dữ liệu mẫu nạp lại trước mỗi test cần DB.",
    "src/backend/eval/benchmark/questions.jsonl": "Bộ câu hỏi benchmark chất lượng AI Guide.",
    "src/backend/app/ai/prompts/system_vi.txt": "System prompt RAG: chỉ trả lời theo bằng chứng, trích dẫn [c#].",
    "src/backend/app/ai/prompts/smalltalk_vi.txt": "System prompt cho chào hỏi / hỏi về trợ lý (không đưa thông tin văn hoá).",
    "src/backend/app/ai/prompts/suggestions_vi.json": "Ngân hàng câu hỏi gợi ý theo quốc gia × chủ đề (app/ai/suggestions.py).",
    "src/ai-local/Dockerfile": "Image AI local: target setup (có torch, xuất ONNX) và runtime (không torch).",
    "src/ai-local/pyproject.toml": "Thư viện của dịch vụ AI local + cấu hình pytest / ruff.",
    "src/ai-local/README.md": "Hướng dẫn dịch vụ AI local: model, giấy phép, cách chạy.",
    "src/ai-local/requirements.lock": "Thư viện khoá cho runtime.", "src/ai-local/requirements-export.lock": "Thư viện khoá cho bước xuất ONNX.",
    "src/database/culture_atlas.dbml": "Mô hình dữ liệu DBML — nguồn sự thật của schema.",
    "src/frontend/Dockerfile": "Image web: build Angular → nginx non-root.",
    "src/frontend/nginx.conf": "nginx: phục vụ SPA, proxy /api → backend, /media → MinIO (chỉ GET/HEAD).",
    "src/frontend/proxy.conf.mjs": "Proxy của `ng serve` (dev): /api → API, /media → MinIO.",
    "src/frontend/angular.json": "Cấu hình build / test Angular.", "src/frontend/package.json": "Thư viện npm và script.",
    "src/frontend/tsconfig.json": "Cấu hình TypeScript chung.", "src/frontend/tsconfig.app.json": "TypeScript cho bản build.",
    "src/frontend/tsconfig.spec.json": "TypeScript cho test.", "src/frontend/public/robots.txt": "robots.txt của web.",
    "src/frontend/src/index.html": "Trang HTML gốc.", "src/frontend/src/styles.css": "CSS toàn cục (biến màu, kiểu chung).",
    "src/frontend/src/app/core/mock/photo-credits.json": "Ghi công ảnh — bản sao của src/media-seed/culture/credits.json.",
    "src/frontend/src/app/core/mock/sources-snapshot.json": "Số liệu thật từ nguồn mở (worker sinh) cho giao diện.",
    "src/media-seed/culture/credits.json": "Ghi công + giấy phép của ảnh văn hoá (Wikimedia Commons).",
    "src/media-seed/objects/credits.json": "Ghi công của ảnh hiện vật (Smithsonian, CC0).",
    "src/object-storage/Dockerfile": "Build MinIO từ image chủ dự án cung cấp: bỏ `mc`, chạy uid 10001.",
}
PATTERN_NOTES: list[tuple[str, str]] = [
    ("*/.dockerignore", "File không gửi vào ngữ cảnh build Docker."),
    ("src/frontend/src/app/features/*/*.page.html", "Template của trang."),
    ("src/frontend/src/app/features/*/*.page.css", "CSS của trang."),
    ("src/frontend/src/app/shared/components/*.css", "CSS của component."),
]


def files() -> list[str]:
    """File trong git (kể cả file mới chưa commit, trừ file bị .gitignore), bỏ SKIP."""
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split("\n")
    return sorted(f for f in out if f and (ROOT / f).is_file() and not any(fnmatch.fnmatch(f, p) for p in SKIP))


def _short(text: str) -> str:
    """Đoạn đầu của docstring / chú thích, gộp dòng, cắt ở câu đầu nếu quá dài."""
    para = " ".join(text.strip().split("\n\n")[0].split())
    if len(para) > MAX_LEN:
        m = re.search(r"^(.{40,%d}?[.;])\s" % MAX_LEN, para)
        para = m.group(1) if m else para[: MAX_LEN - 1].rsplit(" ", 1)[0] + "…"
    return para.replace("|", "\\|")


def describe(rel: str) -> str | None:
    """Mô tả một file, None nếu chưa có."""
    if rel in FILE_NOTES:
        return FILE_NOTES[rel]
    for pat, note in PATTERN_NOTES:
        if fnmatch.fnmatch(rel, pat):
            return note
    path = ROOT / rel
    src = path.read_text(encoding="utf-8", errors="replace")
    if rel.endswith(".py"):
        doc = ast.get_docstring(ast.parse(src))
        if doc:
            return _short(doc)
        return "Đánh dấu package Python." if path.name == "__init__.py" and not src.strip() else None
    if rel.endswith((".ts", ".mjs")):
        if rel.endswith(".spec.ts"):
            m = re.search(r"describe\(\s*'([^']+)'", src)
            return f"Test: {m.group(1)}" if m else "Test."
        m = re.match(r"\s*/\*\*(.*?)\*/", src, re.S)
        if m:
            return _short(re.sub(r"^\s*\*\s?", "", m.group(1), flags=re.M))
        m = re.match(r"((?:\s*//[^\n]*\n)+)", src)
        return _short(re.sub(r"^\s*//\s?", "", m.group(1), flags=re.M)) if m else None
    if rel.endswith((".sql", ".sh")):
        lines = [ln for ln in src.splitlines() if not ln.startswith("#!")]
        head = []
        for ln in lines:
            if ln.startswith(("--", "#")):
                head.append(ln.lstrip("-# "))
            else:
                break
        return _short(" ".join(head[:2])) if head else None
    return None


def render() -> tuple[str, list[str]]:
    """→ (Markdown của mục bản đồ file, các file chưa có mô tả)."""
    by_dir: dict[str, list[str]] = {}
    for f in files():
        by_dir.setdefault(str(Path(f).parent), []).append(f)
    missing: list[str] = []
    out = [BEGIN, ""]
    for d in sorted(by_dir, key=lambda x: (x != ".", x)):
        out.append(f"#### `{d}/`" if d != "." else "#### Gốc repo")
        if d in DIR_NOTES:
            out.append(f"_{DIR_NOTES[d]}_")
        out += ["", "| File | Chức năng |", "|---|---|"]
        for f in by_dir[d]:
            desc = describe(f)
            if desc is None:
                missing.append(f)
                desc = "**(chưa có mô tả)**"
            out.append(f"| [{Path(f).name}](../{f}) | {desc} |")
        out.append("")
    out.append(END)
    return "\n".join(out), missing


def main() -> int:
    """Cập nhật (hoặc kiểm tra với --check) mục bản đồ file trong docs/PROJECT_OVERVIEW.md."""
    block, missing = render()
    doc = DOC.read_text(encoding="utf-8")
    if BEGIN not in doc or END not in doc:
        print(f"Thiếu cặp đánh dấu FILE-MAP trong {DOC}", file=sys.stderr)
        return 1
    new = doc[: doc.index(BEGIN)] + block + doc[doc.index(END) + len(END):]
    if "--check" in sys.argv:
        problems = []
        if missing:
            problems.append("File chưa có mô tả (viết docstring / chú thích đầu file hoặc thêm vào FILE_NOTES):\n  "
                            + "\n  ".join(missing))
        if new != doc:
            problems.append("docs/PROJECT_OVERVIEW.md đã cũ — chạy: python3 scripts/project_overview.py")
        for p in problems:
            print("✘ " + p, file=sys.stderr)
        return 1 if problems else 0
    DOC.write_text(new, encoding="utf-8")
    print(f"Đã cập nhật {DOC.relative_to(ROOT)}" + (f" — {len(missing)} file chưa có mô tả" if missing else ""))
    for f in missing:
        print("  " + f)
    return 0


if __name__ == "__main__":
    sys.exit(main())

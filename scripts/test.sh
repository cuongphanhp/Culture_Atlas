#!/usr/bin/env bash
# Chạy toàn bộ bộ test CultureAtlas AI. Bắt buộc chạy trước khi commit / merge tính năng.
#   scripts/test.sh              backend + AI local + frontend (tự bật PostgreSQL test nếu cần)
#   scripts/test.sh backend      chỉ backend
#   scripts/test.sh frontend     chỉ frontend
#   scripts/test.sh ai-local     chỉ dịch vụ AI local (engine giả; model thật: cd src/ai-local && pytest -m models)
#   ACCEPTANCE_STRICT=1 scripts/test.sh   test PENDING (tính năng chưa code) bị tính là FAIL
# Python được tìm theo thứ tự: <thư mục>/.venv → môi trường conda (culture-api / culture-ai, xem Guide.md) → python3
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-all}"
cd "$ROOT"

# In ra lệnh python cho một thành phần; rỗng nếu không tìm thấy (khi không cho phép dùng python3 mặc định)
find_python() {   # $1 = thư mục .venv, $2 = tên môi trường conda, $3 = "fallback" để dùng python3
  if [ -x "$1/bin/python" ]; then echo "$1/bin/python"; return; fi
  if command -v conda >/dev/null 2>&1; then
    local prefix
    prefix="$(conda env list 2>/dev/null | awk -v n="$2" '$1 == n {print $NF}')"
    if [ -n "$prefix" ] && [ -x "$prefix/bin/python" ]; then echo "$prefix/bin/python"; return; fi
  fi
  [ "${3:-}" = "fallback" ] && echo "python3"
}

# Quy ước code: docstring + type hint đầy đủ (cấu hình [tool.ruff.lint] trong pyproject.toml)
lint() {   # $1 = python, $2 = thư mục
  if "$1" -m ruff --version >/dev/null 2>&1; then
    echo "  ruff check $2"
    (cd "$2" && "$1" -m ruff check .)
  else
    echo "  (bỏ qua ruff: chưa cài — pip install -e \".[dev]\")"
  fi
}

# docs/PROJECT_OVERVIEW.md phải khớp mã nguồn (bản đồ file sinh từ docstring)
run_overview() {
  echo "▶ Tổng quan dự án (docs/PROJECT_OVERVIEW.md)"
  python3 scripts/project_overview.py --check
}

run_backend() {
  echo "▶ Backend (pytest)"
  if [ -z "${TEST_DATABASE_URL:-}" ] && command -v docker >/dev/null; then
    docker compose -f compose.test.yaml up -d --wait >/dev/null
  fi
  local py
  py="$(find_python "$ROOT/src/backend/.venv" culture-api fallback)"
  lint "$py" src/backend
  (cd src/backend && "$py" -m pytest -q)
}

run_ai_local() {
  echo "▶ AI local (pytest)"
  local py
  py="$(find_python "$ROOT/src/ai-local/.venv" culture-ai)"
  if [ -z "$py" ]; then echo "  (bỏ qua: chưa có src/ai-local/.venv hoặc môi trường conda culture-ai — xem Guide.md)"; return 0; fi
  lint "$py" src/ai-local
  (cd src/ai-local && "$py" -m pytest -q)
}

run_frontend() {
  echo "▶ Frontend (vitest)"
  (cd src/frontend && npx ng test --watch=false)
}

case "$TARGET" in
  backend)  run_overview; run_backend ;;
  frontend) run_frontend ;;
  ai-local) run_ai_local ;;
  all)      run_overview; run_backend; run_ai_local; run_frontend ;;
  *) echo "Không rõ: $TARGET (backend|ai-local|frontend|all)"; exit 2 ;;
esac
echo "✔ Tất cả test đã qua"

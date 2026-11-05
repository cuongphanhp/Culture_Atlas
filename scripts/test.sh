#!/usr/bin/env bash
# Chạy toàn bộ bộ test CultureAtlas AI. Bắt buộc chạy trước khi commit / merge tính năng.
#   scripts/test.sh              backend + frontend (tự bật PostgreSQL test nếu cần)
#   scripts/test.sh backend      chỉ backend
#   scripts/test.sh frontend     chỉ frontend
#   scripts/test.sh ai-local     chỉ dịch vụ AI local (engine giả; model thật: cd src/ai-local && pytest -m models)
#   ACCEPTANCE_STRICT=1 scripts/test.sh   test PENDING (tính năng chưa code) bị tính là FAIL
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-all}"
cd "$ROOT"

run_backend() {
  echo "▶ Backend (pytest)"
  if [ -z "${TEST_DATABASE_URL:-}" ] && command -v docker >/dev/null; then
    docker compose -f compose.test.yaml up -d --wait >/dev/null
  fi
  local py="$ROOT/src/backend/.venv/bin/python"
  [ -x "$py" ] || py="python3"
  (cd src/backend && "$py" -m pytest -q)
}

run_ai_local() {
  echo "▶ AI local (pytest)"
  local py="$ROOT/src/ai-local/.venv/bin/python"
  if [ ! -x "$py" ]; then echo "  (bỏ qua: chưa tạo src/ai-local/.venv — xem src/ai-local/README.md)"; return 0; fi
  (cd src/ai-local && "$py" -m pytest -q)
}

run_frontend() {
  echo "▶ Frontend (vitest)"
  (cd src/frontend && npx ng test --watch=false)
}

case "$TARGET" in
  backend)  run_backend ;;
  frontend) run_frontend ;;
  ai-local) run_ai_local ;;
  all)      run_backend; run_ai_local; run_frontend ;;
  *) echo "Không rõ: $TARGET (backend|ai-local|frontend|all)"; exit 2 ;;
esac
echo "✔ Tất cả test đã qua"

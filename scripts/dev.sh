#!/usr/bin/env bash
# Chạy một thành phần của app ở chế độ dev (Cách A trong Guide.md). Dùng cho VS Code Tasks hoặc terminal thường.
#   scripts/dev.sh db     PostgreSQL (Docker) + theo dõi log
#   scripts/dev.sh api    Backend FastAPI   (mặc định cổng 8000, bận thì dùng cổng kế tiếp)
#   scripts/dev.sh ai     AI local          (cổng 8100)
#   scripts/dev.sh web    Frontend Angular  (mặc định cổng 4200, bận thì dùng cổng kế tiếp)
# Đặt cổng cố định: API_PORT=8001 WEB_PORT=4300 AI_LOCAL_PORT=8100 scripts/dev.sh api
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Cổng cố định ghi trong .env (dùng chung với Docker Compose) — chỉ đọc API_PORT / WEB_PORT / S3_PORT, không đọc bí mật
if [ -f .env ]; then
  for v in API_PORT WEB_PORT S3_PORT; do
    if [ -z "${!v:-}" ]; then
      val="$(grep -E "^$v=[0-9]+$" .env | tail -1 | cut -d= -f2)"
      [ -n "$val" ] && export "$v=$val"
    fi
  done
fi

port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

free_port() {   # $1 = cổng mong muốn → in cổng trống đầu tiên từ đó trở đi
  local p=$1
  while port_busy "$p"; do
    echo "⚠ Cổng $p đang bận → thử $((p + 1))" >&2
    p=$((p + 1))
  done
  echo "$p"
}

# Địa chỉ lắng nghe của API/Frontend: 0.0.0.0 để mở được từ máy khác (SSH/Tailscale/LAN). Chỉ máy này: DEV_HOST=127.0.0.1
HOST="${DEV_HOST:-0.0.0.0}"

urls() {   # $1 = cổng → in các địa chỉ truy cập được
  echo "   • http://localhost:$1"
  if [ "$HOST" = "0.0.0.0" ]; then
    hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | grep -v '^172\.' | while read -r ip; do echo "   • http://$ip:$1"; done
  fi
}

# Shell không tương tác (VS Code Tasks) thường không có conda / nvm trong PATH → tự tìm
find_conda() {
  local c
  for c in "${CONDA_EXE:-}" "$(command -v conda 2>/dev/null)" "$HOME/anaconda3/bin/conda" "$HOME/miniconda3/bin/conda" "$HOME/miniforge3/bin/conda"; do
    [ -n "$c" ] && [ -x "$c" ] && { echo "$c"; return; }
  done
}

use_node22() {   # Angular 22 cần Node ≥ 20.19; ưu tiên Node 22 trong nvm nếu node hiện tại cũ hơn
  local major
  major="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/')"
  if [ -z "$major" ] || [ "$major" -lt 20 ]; then
    local nvm_node
    nvm_node="$(ls -d "${NVM_DIR:-$HOME/.nvm}"/versions/node/v22* 2>/dev/null | sort -V | tail -1)"
    [ -z "$nvm_node" ] && { echo "✗ Cần Node 22 (đang có: $(node -v 2>/dev/null || echo không có)). Cài: nvm install 22" >&2; exit 1; }
    export PATH="$nvm_node/bin:$PATH"
  fi
  echo "   (node $(node -v))"
}

python_of() {   # $1 = môi trường conda, $2 = thư mục .venv dự phòng
  local prefix="" conda
  conda="$(find_conda)"
  if [ -n "$conda" ]; then
    prefix="$("$conda" env list 2>/dev/null | awk -v n="$1" '$1 == n {print $NF}')"
  fi
  if [ -n "$prefix" ] && [ -x "$prefix/bin/python" ]; then echo "$prefix/bin/python"
  elif [ -x "$2/bin/python" ]; then echo "$2/bin/python"
  else echo "✗ Chưa có môi trường conda '$1' — xem Guide.md mục 4" >&2; exit 1
  fi
}

case "${1:-}" in
  db)
    docker compose up -d --wait db
    echo "✔ PostgreSQL sẵn sàng ở localhost:${DB_PORT:-5432} — đang theo dõi log (Ctrl+C chỉ dừng xem log; dừng DB: docker compose stop db)"
    exec docker compose logs -f --tail 20 db
    ;;
  api)
    py="$(python_of culture-api "$ROOT/src/backend/.venv")"
    port="${API_PORT:-$(free_port 8000)}"
    echo "▶ Backend API (Swagger ở /api/docs)   python: $py"
    urls "$port"
    cd src/backend
    exec "$py" -m uvicorn app.main:app --reload --host "$HOST" --port "$port"
    ;;
  ai)
    py="$(python_of culture-ai "$ROOT/src/ai-local/.venv")"
    port="${AI_LOCAL_PORT:-8100}"
    if port_busy "$port"; then echo "✗ Cổng $port đang bận — backend cần AI local ở cổng này (AI_LOCAL_URL trong .env)" >&2; exit 1; fi
    echo "▶ AI local: http://127.0.0.1:$port/health   (chỉ mở cho máy này; nạp sẵn 4 model, ~10 s; python: $py)"
    cd src/ai-local
    AI_LOCAL_PRELOAD="${AI_LOCAL_PRELOAD:-1}" exec "$py" -m uvicorn ai_local.main:app --host 127.0.0.1 --port "$port"
    ;;
  web)
    port="${WEB_PORT:-$(free_port 4200)}"
    use_node22
    cd src/frontend
    [ -d node_modules ] || npm ci --legacy-peer-deps
    export API_URL="${API_URL:-http://localhost:${API_PORT:-8000}}"
    export MEDIA_URL="${MEDIA_URL:-http://localhost:${S3_PORT:-9000}}"
    echo "▶ Frontend (proxy /api → $API_URL, /media → $MEDIA_URL):"
    urls "$port"
    exec npx ng serve --host "$HOST" --port "$port"
    ;;
  *)
    echo "Dùng: scripts/dev.sh db|api|ai|web" >&2
    exit 2
    ;;
esac

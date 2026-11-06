#!/usr/bin/env bash
# Nạp volume Docker `ai-models` từ cache Hugging Face có sẵn trên máy chủ — KHÔNG cần Internet.
# Dùng khi mạng chặn Hugging Face / CDN, hoặc để khỏi tải lại ~5 GB khi đã chạy Cách A (python -m ai_local.download).
#   scripts/seed-ai-models.sh                 # nguồn: ~/.cache/huggingface → volume culture_ai-models
#   HF_CACHE=/duong/dan/cache scripts/seed-ai-models.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${HF_CACHE:-$HOME/.cache/huggingface}"
VOLUME="${AI_MODELS_VOLUME:-culture_ai-models}"
IMAGE="culture-atlas/ai-local:${IMAGE_TAG:-local}"
REPOS="g-group-ai-lab--gipformer1.5-68M-rnnt pnnbao-ump--VieNeu-TTS-v3-Turbo OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX AITeamVN--Vietnamese_Embedding_v2"

missing=""
for r in $REPOS; do [ -d "$SRC/hub/models--$r/snapshots" ] || missing="$missing $r"; done
for f in ai-local/silero_vad.onnx ai-local/reranker-onnx/model.int8.onnx; do [ -f "$SRC/$f" ] || missing="$missing $f"; done
if [ -n "$missing" ]; then
  echo "✗ Thiếu trong $SRC:$missing" >&2
  echo "  Tải trước trên máy này (Cách A): cd src/ai-local && python -m ai_local.download" >&2
  exit 1
fi
# Cache phải là file thật (không symlink) — `python -m ai_local.download` đã tự chuyển symlink thành hardlink
for r in $REPOS; do
  if [ -n "$(find "$SRC/hub/models--$r/snapshots" -type l 2>/dev/null | head -1)" ]; then
    echo "✗ $r trong cache còn symlink. Chạy lại: cd $ROOT/src/ai-local && python -m ai_local.download" >&2
    exit 1
  fi
done

docker image inspect "$IMAGE" >/dev/null 2>&1 || { echo "✗ Chưa có image $IMAGE — chạy: docker compose build ai-local" >&2; exit 1; }
echo "▶ Chép model từ $SRC vào volume $VOLUME (chạy bằng uid 10001)…"
docker run --rm --user 10001:10001 --network none --entrypoint sh \
  -v "$SRC":/src:ro -v "$VOLUME":/models "$IMAGE" -c "
    set -e
    for r in $REPOS; do
      mkdir -p /models/hub/models--\$r
      cp -r /src/hub/models--\$r/refs /src/hub/models--\$r/snapshots /models/hub/models--\$r/
    done
    mkdir -p /models/ai-local
    cp -r /src/ai-local/silero_vad.onnx /src/ai-local/reranker-onnx /models/ai-local/
    du -sh /models"
echo "✔ Xong. Khởi động: docker compose up -d"

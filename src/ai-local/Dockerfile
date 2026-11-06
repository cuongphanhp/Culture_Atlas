# AI local (CPU): STT Gipformer, TTS VieNeu, embedding + rerank ONNX. Không torch, không ffmpeg hệ thống (PyAV), non-root.
#   target runtime : dịch vụ chạy thật
#   target setup   : runtime + torch CPU — chỉ dùng MỘT LẦN để tải model và xuất reranker sang ONNX int8
ARG PYTHON_IMAGE=public.ecr.aws/docker/library/python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30

FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore
# Vá các gói hệ thống đã có bản sửa (quét: scripts/scan-images.sh), dọn chỉ mục apt trong cùng layer
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app

# ---------- build: venv theo lockfile (vieneu --no-deps nằm sẵn trong lock) ----------
FROM base AS builder
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.lock .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps -r requirements.lock \
    && pip uninstall -y pip    # runtime không cài thêm gói được

# ---------- runtime ----------
FROM base AS runtime
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY ai_local ./ai_local
RUN mkdir -p /models && chown 10001:10001 /models
# HF_HUB_OFFLINE: lúc chạy không gọi ra Internet — model đã có trong volume /models
ENV PATH=/opt/venv/bin:$PATH \
    HF_HOME=/models \
    HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache
USER 10001:10001
EXPOSE 8100
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')"]
CMD ["uvicorn", "ai_local.main:app", "--host", "0.0.0.0", "--port", "8100"]

# ---------- setup: tải model + xuất reranker (cần torch CPU) ----------
FROM runtime AS setup
USER root
COPY requirements-export.lock .
RUN --mount=type=cache,target=/root/.cache/pip \
    /usr/local/bin/python -m pip --python /opt/venv/bin/python install --no-deps \
        --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-export.lock \
    && rm requirements-export.lock
# Xet (giao thức tải mới của Hugging Face) có thể bị chặn ở một số mạng → dùng HTTP thường
ENV HF_HUB_OFFLINE=0 \
    HF_HUB_DISABLE_XET=1
USER 10001:10001
CMD ["python", "-m", "ai_local.download"]

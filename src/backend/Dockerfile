# Backend API + worker. Multi-stage: build venv → runtime chỉ có Python + venv + mã nguồn, chạy non-root.
# Base lấy từ Amazon ECR Public (bản sao chính thức của Docker Official Images), ghim theo digest.
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

# ---------- build: cài thư viện theo lockfile vào /opt/venv ----------
FROM base AS builder
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.lock .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps -r requirements.lock \
    # bỏ pip khỏi venv runtime (không cài thêm gói được khi chạy) và binary selenium-manager của Windows/macOS
    && pip uninstall -y pip \
    && find /opt/venv -path '*selenium/webdriver/common/*' \( -name 'windows' -o -name 'macos' \) -type d -prune -exec rm -rf {} +

# ---------- runtime ----------
FROM base AS runtime
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
# Mã nguồn thuộc root → user ứng dụng không sửa được
COPY app ./app
COPY worker ./worker
RUN mkdir -p /data && chown 10001:10001 /data
ENV PATH=/opt/venv/bin:$PATH \
    WORKER_DATA_DIR=/data
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

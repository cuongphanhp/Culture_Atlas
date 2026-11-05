# Dịch vụ AI local (CPU). Model lưu ở volume /models (HF_HOME) — tải một lần.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
COPY ai_local ./ai_local
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu ".[rerank]"
ENV HF_HOME=/models AI_LOCAL_PRELOAD=1
EXPOSE 8100
CMD ["uvicorn", "ai_local.main:app", "--host", "0.0.0.0", "--port", "8100"]

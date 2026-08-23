# Sentinel API image. Build context = repo root (see docker-compose.prod.yml):
#   docker build -f backend/Dockerfile -t sentinel-backend .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/app ./app
# Knowledge base, so `python -m app.cli ingest` can run inside the container.
# config.ROOT resolves to "/" here, so DOCS_DIR is "/docs".
COPY docs /docs

EXPOSE 8000

# FastAPI endpoints are sync `def` (blocking I/O runs in a threadpool); a couple
# of workers give basic concurrency. No --reload in production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

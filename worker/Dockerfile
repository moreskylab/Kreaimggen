# ── Stage 1: build deps ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app
COPY --from=builder /install /usr/local
# Worker shares the same app code as the API
COPY app ./app

USER appuser

# Concurrency via env var CELERYD_CONCURRENCY (default 4)
CMD ["celery", "-A", "app.celery_app:celery_app", "worker", \
     "--loglevel=info", "--queues=image_generation", \
     "--concurrency=4", "--hostname=worker@%h"]

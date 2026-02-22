#!/bin/sh
set -e

echo "Running database migrations…"
# Retry loop: alembic may transiently fail if postgres is still initialising its
# data directory (it passes pg_isready but rejects connections for a few seconds).
MAX_TRIES=10
TRY=0
until alembic upgrade head; do
  TRY=$((TRY + 1))
  if [ "$TRY" -ge "$MAX_TRIES" ]; then
    echo "Migration failed after $MAX_TRIES attempts. Aborting."
    exit 1
  fi
  echo "Migration attempt $TRY failed, retrying in 5s…"
  sleep 5
done

echo "Starting API server…"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --timeout-keep-alive 75

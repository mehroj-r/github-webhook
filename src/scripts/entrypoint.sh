#!/bin/sh
set -e

echo "Running database migrations..."
alembic -c /app/database/alembic.ini upgrade head

if [ -n "$PROMETHEUS_MULTIPROC_DIR" ]; then
  # Stale per-worker metric files from a previous run would be summed into the new one
  rm -rf "$PROMETHEUS_MULTIPROC_DIR"
  mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
fi

echo "Starting application with Gunicorn + Uvicorn workers..."
exec gunicorn asgi:app --config /app/gunicorn.conf.py

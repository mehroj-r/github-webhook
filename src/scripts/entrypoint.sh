#!/bin/sh
set -e

echo "Running database migrations..."
alembic -c /app/database/alembic.ini upgrade head

echo "Starting application with Gunicorn + Uvicorn workers..."
exec gunicorn asgi:app --config /app/gunicorn.conf.py

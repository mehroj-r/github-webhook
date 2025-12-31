#!/bin/sh
set -e

echo "Running database migrations..."
python -m manage migrate

echo "Starting application with Gunicorn + Uvicorn workers..."
exec gunicorn asgi:app --config /app/gunicorn.conf.py

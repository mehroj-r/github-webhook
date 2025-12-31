#!/bin/sh
set -e

echo "[$(date)] Running healthcheck..."

if curl http://localhost:8000/misc/health/ > /dev/null; then
  echo "Healthcheck passed ✅"
  exit 0
else
  echo "Healthcheck failed ❌"
  exit 1
fi
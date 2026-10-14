"""Prometheus metrics. With PROMETHEUS_MULTIPROC_DIR set, values are aggregated across Gunicorn workers."""

import os
import time
from contextlib import contextmanager

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest, multiprocess

WEBHOOK_DELIVERIES = Counter(
    "gh_webhook_deliveries_total",
    "GitHub webhook deliveries by event type and final status",
    ["event", "status"],
)

TELEGRAM_REQUEST_SECONDS = Histogram(
    "telegram_request_duration_seconds",
    "Telegram Bot API call latency, including retries",
    ["method", "outcome"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)


def record_delivery(event: str, status: str) -> None:
    WEBHOOK_DELIVERIES.labels(event=event, status=status).inc()


@contextmanager
def observe_telegram_call(method: str):
    """Time a Telegram call; the outcome label is "ok" or "error"."""
    started = time.perf_counter()
    outcome = "error"
    try:
        yield
        outcome = "ok"
    finally:
        TELEGRAM_REQUEST_SECONDS.labels(method=method, outcome=outcome).observe(time.perf_counter() - started)


def render_metrics() -> tuple[bytes, str]:
    """Serialize all metrics in the Prometheus text format. Returns (body, content type)."""
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST

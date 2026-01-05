import multiprocessing
import os

from core import get_logger, get_logger_config

logger = get_logger("gunicorn")

# Server Socket
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker Processes
worker_class = "uvicorn.workers.UvicornWorker"

# Number of workers (Recommended: CPU cores * 2 + 1)
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Worker connections (for async workers, this can be higher)
worker_connections = 1000

# Timeout
timeout = 120
keepalive = 5

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG")
errorlog = os.getenv("GUNICORN_ERROR_LOG")
loglevel = os.getenv("LOG_LEVEL", "info")

# Use dictConfig for custom logging configuration
logconfig_dict = get_logger_config()

# Process naming
proc_name = "gh-webhook-bot"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Preload app for better memory usage
preload_app = True

# Graceful timeout for worker shutdown
graceful_timeout = 30

# Max requests per worker (helps prevent memory leaks)
max_requests = int(os.getenv("MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", 50))

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190


def on_starting(_):
    """Called just before the master process is initialized."""
    # Ensure logs directory exists
    log_dir = os.getenv("LOG_DIR")
    os.makedirs(log_dir, exist_ok=True)
    logger.info(f"Starting Gunicorn with {workers} Uvicorn workers")
    logger.info(f"Access log: {accesslog}")
    logger.info(f"Error log: {errorlog}")


def on_reload(_):
    """Called to recycle workers during a reload via SIGHUP."""
    logger.info("Reloading Gunicorn...")


def when_ready(_):
    """Called just after the server is started."""
    logger.info(f"Gunicorn is ready. Listening on {bind}")


def on_exit(_):
    """Called just before exiting Gunicorn."""
    logger.info("Shutting down Gunicorn...")


def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    logger.warning(f"Worker {worker.pid} received SIGINT/SIGQUIT")


def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    logger.warning(f"Worker {worker.pid} received SIGABRT")

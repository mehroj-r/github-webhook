import json
import logging.config
import os
from contextvars import ContextVar
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from config import settings

LOG_DIR = settings.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

# GitHub delivery id of the webhook being handled; attached to every record as ``delivery_id``
delivery_id_var: ContextVar[str | None] = ContextVar("delivery_id", default=None)

_RESERVED_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


class ContextFilter(logging.Filter):
    """Copy request-scoped context (the delivery id) onto each record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "delivery_id"):
            record.delivery_id = delivery_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line; ``extra=`` fields are included as top-level keys."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and value is not None:
                entry[key] = value
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            entry["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s[%(asctime)s] %(levelname)-5s%(reset)s %(blue)s%(module)s%(reset)s: %(log_color)s%(message)s",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            },
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "[%(asctime)s] %(levelname)-8s in %(module)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {"()": JsonFormatter},
    },
    "filters": {
        "context": {"()": ContextFilter},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["context"],
            "formatter": "colored",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filters": ["context"],
            "filename": f"{LOG_DIR}/app.log",
            "formatter": "detailed",
            "level": "INFO",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filters": ["context"],
            "filename": f"{LOG_DIR}/errors.log",
            "formatter": "detailed",
            "level": "ERROR",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "gunicorn_access": {
            "class": "logging.handlers.RotatingFileHandler",
            "filters": ["context"],
            "filename": os.getenv("GUNICORN_ACCESS_LOG", f"{LOG_DIR}/gunicorn_access.log"),
            "formatter": "detailed",
            "level": "INFO",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "gunicorn_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "filters": ["context"],
            "filename": os.getenv("GUNICORN_ERROR_LOG", f"{LOG_DIR}/gunicorn_error.log"),
            "formatter": "detailed",
            "level": "INFO",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "gunicorn.error": {
            "handlers": ["gunicorn_error", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": ["gunicorn_access"],
            "level": "INFO",
            "propagate": False,
        },
        "alembic": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": "DEBUG" if settings.DEBUG else "INFO",
    },
}

if settings.LOG_FORMAT == "json":
    for handler in LOGGING_CONFIG["handlers"].values():
        handler["formatter"] = "json"

_configured = False


def configure_logging() -> None:
    """Apply the logging configuration once per process."""
    global _configured
    if _configured:
        return
    logging.config.dictConfig(LOGGING_CONFIG)
    _configured = True


@lru_cache
def get_logger(name: str) -> logging.Logger:
    """
    Create and return a singleton logger with the specified name.

    :param name: The name of the logger.

    :return: The singleton logger.
    """

    configure_logging()
    return logging.getLogger(name)


def get_logger_config() -> dict:
    """
    Get the logging configuration for Gunicorn and application loggers.

    :return: The logging configuration dictionary.
    """

    return LOGGING_CONFIG

import logging.config
import os
from functools import lru_cache

from config import settings

LOG_DIR = settings.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING_CONFIG = {
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
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colored",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/app.log",
            "formatter": "detailed",
            "level": "INFO",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{LOG_DIR}/errors.log",
            "formatter": "detailed",
            "level": "ERROR",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "gunicorn_access": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.getenv("GUNICORN_ACCESS_LOG", f"{LOG_DIR}/gunicorn_access.log"),
            "formatter": "detailed",
            "level": "INFO",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "gunicorn_error": {
            "class": "logging.handlers.RotatingFileHandler",
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
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": "DEBUG",
    },
}


@lru_cache()
def get_logger(name: str) -> logging.Logger:
    """
    Create and return a singleton logger with the specified name.

    :param name: The name of the logger.

    :return: The singleton logger.
    """

    # Configure the logging system
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(name)

    return logger


def get_logger_config() -> dict:
    """
    Get the logging configuration for Gunicorn and application loggers.

    :return: The logging configuration dictionary.
    """

    return LOGGING_CONFIG

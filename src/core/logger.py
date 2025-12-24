import logging.config
import os
from functools import lru_cache

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
            "filename": "logs/app.log",
            "formatter": "detailed",
            "level": "INFO",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/errors.log",
            "formatter": "detailed",
            "level": "ERROR",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
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
    # Make sure the logs directory exists
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Configure the logging system
    logging.config.dictConfig(LOGGING_CONFIG)

    logger = logging.getLogger(name)

    return logger


def get_logger_config() -> dict:
    """
    Get the logging configuration for a specific logger.

    :return: The logging configuration dictionary.
    """
    return LOGGING_CONFIG

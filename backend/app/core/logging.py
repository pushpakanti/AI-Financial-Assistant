"""Application logging configuration."""

import logging
from logging.config import dictConfig

from app.core.config import settings


def configure_logging() -> None:
    """Configure consistent console logging for the application."""
    log_level = "DEBUG" if settings.DEBUG else "INFO"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": log_level,
            },
        }
    )

    logging.getLogger(__name__).debug("Logging configured at %s level", log_level)

"""Process-wide logging configuration.

A small wrapper around :func:`logging.config.dictConfig` so the rest of
the app gets consistent, readable log output without each module having
to wire up its own handlers.

Why dictConfig and not basicConfig:
    ``logging.basicConfig`` is a no-op once any handler is attached to
    the root logger. By the time a uvicorn worker imports our app, uvicorn
    has already set up its own handlers, so basicConfig would silently do
    nothing. dictConfig replaces the configuration unconditionally.

Why ``disable_existing_loggers=False``:
    The dictConfig default is to disable every logger already created at
    the time the config is applied. That includes uvicorn's loggers, which
    we want to leave alone — uvicorn manages its own access/error pipeline
    and we should not stomp on it.
"""

from __future__ import annotations

import logging
from logging.config import dictConfig


_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s :: %(message)s"

_HANDLER_ID = "week2_stderr"


def configure_logging(level: str = "INFO") -> None:
    """Install the app's logging configuration.

    Idempotent: a second call replaces the previous configuration rather
    than appending duplicate handlers, because dictConfig fully replaces
    the existing config when called.

    Args:
        level: Root logger level name (e.g. ``"INFO"``, ``"DEBUG"``).
            Case-insensitive; ``logging`` accepts either case.
    """
    normalized_level = level.upper()
    # Validate the level eagerly so a typo in APP_LOG_LEVEL fails loudly.
    if not isinstance(logging.getLevelName(normalized_level), int):
        raise ValueError(f"Unknown log level: {level!r}")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": _LOG_FORMAT,
                },
            },
            "handlers": {
                _HANDLER_ID: {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                    "formatter": "default",
                    "level": normalized_level,
                },
            },
            "root": {
                "level": normalized_level,
                "handlers": [_HANDLER_ID],
            },
        }
    )

"""
Healthcare AI Router — Structured Logging
==========================================
Configures a JSON-formatted, async-safe logger using Python's standard
`logging` module with structured output suitable for log aggregators
(Datadog, Loki, CloudWatch, etc.).

Usage:
    from backend.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Request received", extra={"correlation_id": "..."})
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Every log entry contains:
      - timestamp  (ISO 8601, UTC)
      - level      (DEBUG / INFO / WARNING / ERROR / CRITICAL)
      - logger     (module name)
      - message    (the log message)
      - extra      (any additional key-value pairs passed via `extra={}`)
      - exception  (formatted traceback, only on exc_info records)
    """

    RESERVED_ATTRS: frozenset[str] = frozenset(
        {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach any extra fields passed by the caller
        extra: dict[str, Any] = {
            k: v
            for k, v in record.__dict__.items()
            if k not in self.RESERVED_ATTRS and not k.startswith("_")
        }
        if extra:
            log_entry["extra"] = extra

        # Attach exception info when present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            log_entry["exception"] = record.exc_text

        return json.dumps(log_entry, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """
    Configure the root logger for the application.

    Call this exactly once at application startup (inside `main.py`).
    All subsequent calls to `get_logger()` will inherit this configuration.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Replace any existing handlers on the root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "motor", "pymongo"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Args:
        name: Typically `__name__` of the calling module.

    Returns:
        A standard `logging.Logger` instance.
    """
    return logging.getLogger(name)

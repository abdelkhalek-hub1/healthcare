"""
Healthcare AI Router — Structured Request Logging Middleware
============================================================
Emits one JSON log entry per request/response pair, capturing:
    - HTTP method and path
    - Response status code
    - Total processing time
    - Correlation ID

Excludes health and docs endpoints from verbose logging to reduce noise.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Paths that generate high-frequency noise — log at DEBUG instead of INFO
_QUIET_PATHS: frozenset[str] = frozenset(
    {"/", "/docs", "/redoc", "/openapi.json", "/api/v1/health"}
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that produces a structured log line per request.

    Depends on ``CorrelationMiddleware`` and ``TimingMiddleware`` having
    already run (reads ``request.state.correlation_id`` and
    ``request.state.start_time``).
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request metadata before and after handler execution."""
        response: Response = await call_next(request)

        elapsed_ms = (
            (time.monotonic() - request.state.start_time) * 1000
            if hasattr(request.state, "start_time")
            else -1.0
        )

        correlation_id: str = getattr(request.state, "correlation_id", "")

        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(elapsed_ms, 2),
            "correlation_id": correlation_id,
            "client_ip": request.client.host if request.client else "unknown",
        }

        if request.url.path in _QUIET_PATHS:
            logger.debug("Request completed", extra=log_data)
        elif response.status_code >= 500:
            logger.error("Request failed with server error", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Request completed with client error", extra=log_data)
        else:
            logger.info("Request completed", extra=log_data)

        return response

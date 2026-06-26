"""
Healthcare AI Router — Request Timing Middleware
=================================================
Records the wall-clock start time of every request on ``request.state``
and emits an ``X-Process-Time`` response header with the elapsed milliseconds.

The timing data is also available to the monitoring agent via
``request.state.start_time``.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

PROCESS_TIME_HEADER = "X-Process-Time"


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that measures total request processing time.

    Sets:
        ``request.state.start_time`` — ``time.monotonic()`` value recorded
        at the very beginning of the request.
        ``X-Process-Time`` response header — elapsed milliseconds as a string.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Record start time, delegate, then annotate the response."""
        request.state.start_time = time.monotonic()

        response: Response = await call_next(request)

        elapsed_ms = (time.monotonic() - request.state.start_time) * 1000
        response.headers[PROCESS_TIME_HEADER] = f"{elapsed_ms:.2f}ms"
        return response

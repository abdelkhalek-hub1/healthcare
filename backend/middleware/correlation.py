"""
Healthcare AI Router — Correlation ID Middleware
=================================================
Generates or forwards a ``X-Correlation-ID`` header on every request
and stores it on ``request.state`` for use throughout the request lifecycle.

If the client already provides a ``X-Correlation-ID`` header (e.g. from an
upstream service), it is reused. Otherwise a new UUID4 is generated.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that attaches a correlation ID to every request.

    Sets:
        ``request.state.correlation_id`` — available to all downstream
        handlers and dependencies.
        ``X-Correlation-ID`` response header — echoed back to the client.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Attach correlation ID and delegate to the next handler."""
        correlation_id: str = (
            request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        )
        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response

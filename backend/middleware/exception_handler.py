"""
Healthcare AI Router — Global Exception Handler Middleware
==========================================================
Catches any unhandled exception from the application and normalises it
into the standard ``ErrorResponse`` envelope before returning it to the client.

This is the outermost safety net. It ensures that:
    - No Python traceback ever reaches the API consumer.
    - Every error response has a consistent JSON structure.
    - Application-specific exceptions are mapped to their correct HTTP codes.
    - Correlation IDs are always present, even on unexpected failures.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.schemas.error_schema import (
    AppBaseException,
    ErrorCode,
    ErrorResponse,
    get_http_status,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Outermost middleware that catches all unhandled exceptions.

    Priority order:
        1. ``AppBaseException`` subclasses → mapped error code + HTTP status
        2. ``ValueError`` / ``TypeError`` → 422 Validation Error
        3. Any other ``Exception`` → 500 Internal Server Error

    The correlation ID is read from ``request.state`` (set by
    ``CorrelationMiddleware``). Falls back to ``"unknown"`` if not available.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Delegate to the handler; catch and normalise any exception."""
        try:
            return await call_next(request)

        except AppBaseException as exc:
            return self._build_response(
                request=request,
                code=exc.code,
                message=exc.message,
                http_status=get_http_status(exc.code),
                details=exc.details,
            )

        except ValueError as exc:
            return self._build_response(
                request=request,
                code=ErrorCode.VALIDATION_ERROR,
                message=str(exc),
                http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        except Exception as exc:
            # Log the full traceback for internal debugging
            logger.error(
                "Unhandled exception",
                extra={
                    "correlation_id": getattr(
                        request.state, "correlation_id", "unknown"
                    ),
                    "path": request.url.path,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            return self._build_response(
                request=request,
                code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred. Please try again later.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _build_response(
        request: Request,
        code: str,
        message: str,
        http_status: int,
        details: dict | None = None,
    ) -> JSONResponse:
        """
        Construct a ``JSONResponse`` with the standard error envelope.

        Args:
            request:     The originating Starlette request.
            code:        Machine-readable error code string.
            message:     Human-readable error description.
            http_status: HTTP status code for the response.
            details:     Optional extra context dict.

        Returns:
            A ``JSONResponse`` with the serialised ``ErrorResponse`` body.
        """
        correlation_id: str = getattr(request.state, "correlation_id", "unknown")

        error_body = ErrorResponse(
            correlation_id=correlation_id,
            code=code,
            message=message,
            timestamp=datetime.now(tz=timezone.utc),
            details=details,
        )

        return JSONResponse(
            status_code=http_status,
            content=error_body.model_dump(mode="json"),
            headers={"X-Correlation-ID": correlation_id},
        )

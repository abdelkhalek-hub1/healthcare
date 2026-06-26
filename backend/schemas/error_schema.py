"""
Healthcare AI Router — Centralized Error Schemas
=================================================
Defines ErrorCode enum and ErrorResponse Pydantic model.

Every API error — regardless of origin (LLM, DB, validation, timeout) —
is normalized into this single ErrorResponse structure before being
returned to the client. This guarantees a predictable contract for
frontend error handling.

Wire format:
    {
        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "error",
        "code": "GROQ_UNAVAILABLE",
        "message": "The Groq service is temporarily unavailable.",
        "timestamp": "2026-06-26T10:00:00.000000Z",
        "details": null
    }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorCode:
    """
    String constants for all recognized error codes.

    Using a plain class instead of Enum so that values can be used
    directly as strings in FastAPI response bodies without `.value` coercion.
    """

    GROQ_UNAVAILABLE: str = "GROQ_UNAVAILABLE"
    GROQ_RATE_LIMIT: str = "GROQ_RATE_LIMIT"
    GROQ_TIMEOUT: str = "GROQ_TIMEOUT"
    GROQ_AUTH_ERROR: str = "GROQ_AUTH_ERROR"

    MONGO_UNAVAILABLE: str = "MONGO_UNAVAILABLE"
    MONGO_WRITE_ERROR: str = "MONGO_WRITE_ERROR"
    MONGO_READ_ERROR: str = "MONGO_READ_ERROR"

    VALIDATION_ERROR: str = "VALIDATION_ERROR"
    INTENT_CLASSIFICATION_FAILED: str = "INTENT_CLASSIFICATION_FAILED"
    PROMPT_NOT_FOUND: str = "PROMPT_NOT_FOUND"

    SESSION_NOT_FOUND: str = "SESSION_NOT_FOUND"
    SESSION_EXPIRED: str = "SESSION_EXPIRED"

    REQUEST_TIMEOUT: str = "REQUEST_TIMEOUT"
    INTERNAL_ERROR: str = "INTERNAL_ERROR"
    LANGSMITH_UNAVAILABLE: str = "LANGSMITH_UNAVAILABLE"


# HTTP status code mapping for each error code
ERROR_HTTP_STATUS: dict[str, int] = {
    ErrorCode.GROQ_UNAVAILABLE: 503,
    ErrorCode.GROQ_RATE_LIMIT: 429,
    ErrorCode.GROQ_TIMEOUT: 504,
    ErrorCode.GROQ_AUTH_ERROR: 500,
    ErrorCode.MONGO_UNAVAILABLE: 503,
    ErrorCode.MONGO_WRITE_ERROR: 500,
    ErrorCode.MONGO_READ_ERROR: 500,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.INTENT_CLASSIFICATION_FAILED: 500,
    ErrorCode.PROMPT_NOT_FOUND: 500,
    ErrorCode.SESSION_NOT_FOUND: 404,
    ErrorCode.SESSION_EXPIRED: 410,
    ErrorCode.REQUEST_TIMEOUT: 504,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.LANGSMITH_UNAVAILABLE: 503,
}


def get_http_status(code: str) -> int:
    """Return the HTTP status code for a given ErrorCode string."""
    return ERROR_HTTP_STATUS.get(code, 500)


class ErrorResponse(BaseModel):
    """
    Standardized error envelope returned by every API error path.

    Fields:
        correlation_id: The X-Correlation-ID for the failed request.
        status:         Always "error".
        code:           Machine-readable error code from ErrorCode.
        message:        Human-readable description of the error.
        timestamp:      UTC timestamp when the error was generated.
        details:        Optional extra context (e.g. validation field errors).
    """

    correlation_id: str = Field(
        ...,
        description="Unique identifier for the failed request",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    status: Literal["error"] = "error"
    code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=[ErrorCode.GROQ_UNAVAILABLE],
    )
    message: str = Field(
        ...,
        description="Human-readable description of what went wrong",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp when the error occurred",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional context about the error",
    )

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    @classmethod
    def build(
        cls,
        code: str,
        message: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> "ErrorResponse":
        """
        Factory method for constructing an ErrorResponse cleanly.

        Example:
            ErrorResponse.build(
                code=ErrorCode.GROQ_UNAVAILABLE,
                message="Groq service is unavailable after 3 retries.",
                correlation_id=request.state.correlation_id,
            )
        """
        return cls(
            correlation_id=correlation_id,
            code=code,
            message=message,
            details=details,
        )


# ---------------------------------------------------------------------------
# Custom exceptions — raised inside agents/services and caught by the
# global exception handler middleware, which converts them to ErrorResponse.
# ---------------------------------------------------------------------------


class AppBaseException(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class GroqUnavailableError(AppBaseException):
    def __init__(self, message: str = "Groq LLM service is unavailable.") -> None:
        super().__init__(code=ErrorCode.GROQ_UNAVAILABLE, message=message)


class GroqRateLimitError(AppBaseException):
    def __init__(self, message: str = "Groq rate limit exceeded.") -> None:
        super().__init__(code=ErrorCode.GROQ_RATE_LIMIT, message=message)


class GroqTimeoutError(AppBaseException):
    def __init__(self, message: str = "Groq request timed out.") -> None:
        super().__init__(code=ErrorCode.GROQ_TIMEOUT, message=message)


class MongoUnavailableError(AppBaseException):
    def __init__(self, message: str = "MongoDB is unavailable.") -> None:
        super().__init__(code=ErrorCode.MONGO_UNAVAILABLE, message=message)


class IntentClassificationError(AppBaseException):
    def __init__(self, message: str = "Failed to classify intent.") -> None:
        super().__init__(code=ErrorCode.INTENT_CLASSIFICATION_FAILED, message=message)


class SessionNotFoundError(AppBaseException):
    def __init__(self, session_id: str) -> None:
        super().__init__(
            code=ErrorCode.SESSION_NOT_FOUND,
            message=f"Session '{session_id}' not found.",
            details={"session_id": session_id},
        )


class PromptNotFoundError(AppBaseException):
    def __init__(self, prompt_name: str) -> None:
        super().__init__(
            code=ErrorCode.PROMPT_NOT_FOUND,
            message=f"Prompt '{prompt_name}' not found in the prompt repository.",
            details={"prompt_name": prompt_name},
        )

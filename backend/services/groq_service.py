"""
Healthcare AI Router — Groq Service (Resilient LLM Invocation)
===============================================================
Wraps the LangChain ``ChatGroq`` model with production-grade reliability:

    - Exponential backoff retry via ``tenacity`` for transient errors
    - Hard-fail on non-retryable errors (authentication)
    - Automatic token usage extraction from ``AIMessage.usage_metadata``
    - Async-first design (all public methods are coroutines)
    - Lightweight connectivity health check

Dependency injection pattern::

    # In a FastAPI endpoint or agent:
    from backend.services.groq_service import GroqService, get_groq_service

    async def my_handler(groq: GroqService = Depends(get_groq_service)):
        response, usage = await groq.invoke_with_retry(messages, correlation_id)
"""

from __future__ import annotations

import asyncio
import logging
import time
from functools import lru_cache
from typing import Any

from groq import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from tenacity import (
    AsyncRetrying,
    RetryError,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.config import get_settings
from backend.models.domain import TokenUsage
from backend.schemas.error_schema import (
    GroqRateLimitError,
    GroqTimeoutError,
    GroqUnavailableError,
)
from backend.services.llm_factory import LLMFactory, LLMProvider
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Exceptions that warrant a retry (transient / rate-limited)
_RETRYABLE_EXCEPTIONS = (RateLimitError, APITimeoutError, APIConnectionError)


class GroqService:
    """
    Resilient LLM invocation service for the Groq backend.

    Handles retry logic, error normalisation, and token usage extraction
    so that agents remain free of these cross-cutting concerns.

    Args:
        llm:         A configured ``BaseChatModel`` produced by ``LLMFactory``.
        max_retries: Maximum number of invocation attempts before failing.
        base_delay:  Initial backoff delay in seconds (doubles on each attempt).
        max_delay:   Upper bound for backoff delay in seconds.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._llm = llm
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def invoke_with_retry(
        self,
        messages: list[BaseMessage],
        correlation_id: str = "",
    ) -> tuple[AIMessage, TokenUsage]:
        """
        Invoke the LLM with automatic exponential backoff retry.

        Retries on:
            - ``RateLimitError``  (Groq rate limiting)
            - ``APITimeoutError`` (request timeout)
            - ``APIConnectionError`` (transient network errors)

        Does NOT retry on:
            - ``AuthenticationError`` (invalid API key — non-retryable)

        Args:
            messages:       List of ``BaseMessage`` objects (system + human turns).
            correlation_id: Request correlation ID for structured logging.

        Returns:
            A tuple of (``AIMessage``, ``TokenUsage``).

        Raises:
            GroqRateLimitError:   Rate limit exceeded after all retries.
            GroqTimeoutError:     Timeout after all retries.
            GroqUnavailableError: Connection error or auth failure.
        """
        # Fail fast on authentication issues without consuming retry budget
        try:
            return await self._invoke_with_tenacity(messages, correlation_id)
        except AuthenticationError as exc:
            logger.error(
                "Groq authentication failed — check GROQ_API_KEY",
                extra={"correlation_id": correlation_id, "error": str(exc)},
            )
            raise GroqUnavailableError(
                "Groq authentication failed. Verify your GROQ_API_KEY."
            ) from exc

    async def invoke_raw(
        self,
        messages: list[BaseMessage],
    ) -> AIMessage:
        """
        Invoke the LLM once without retry logic.

        Intended for health checks and internal diagnostics.

        Args:
            messages: List of ``BaseMessage`` objects.

        Returns:
            The raw ``AIMessage`` from the model.

        Raises:
            Any Groq SDK exception on failure.
        """
        return await self._llm.ainvoke(messages)  # type: ignore[return-value]

    async def check_connectivity(self) -> tuple[bool, float]:
        """
        Perform a lightweight connectivity probe against the Groq API.

        Sends a minimal single-token request and measures round-trip latency.
        This is used by the ``/health`` endpoint.

        Returns:
            A tuple of ``(is_healthy: bool, latency_ms: float)``.
            ``latency_ms`` is ``-1.0`` when the check fails.
        """
        start = time.monotonic()
        try:
            await asyncio.wait_for(
                self.invoke_raw([HumanMessage(content="ping")]),
                timeout=8.0,
            )
            latency_ms = (time.monotonic() - start) * 1000
            logger.debug(
                "Groq connectivity check passed",
                extra={"latency_ms": round(latency_ms, 2)},
            )
            return True, latency_ms
        except Exception as exc:
            logger.warning(
                "Groq connectivity check failed",
                extra={"error": str(exc)},
            )
            return False, -1.0

    # -------------------------------------------------------------------------
    # Internal implementation
    # -------------------------------------------------------------------------

    async def _invoke_with_tenacity(
        self,
        messages: list[BaseMessage],
        correlation_id: str,
    ) -> tuple[AIMessage, TokenUsage]:
        """
        Execute the LLM call inside tenacity's async retry loop.

        Args:
            messages:       Prompt messages for the LLM.
            correlation_id: For structured log entries per attempt.

        Returns:
            Tuple of (``AIMessage``, ``TokenUsage``).

        Raises:
            GroqRateLimitError | GroqTimeoutError | GroqUnavailableError:
                On exhausted retries.
        """
        result: AIMessage | None = None

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(
                    multiplier=self._base_delay,
                    min=self._base_delay,
                    max=self._max_delay,
                ),
                retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            ):
                with attempt:
                    attempt_num = attempt.retry_state.attempt_number
                    start = time.monotonic()

                    logger.debug(
                        "Groq invocation attempt",
                        extra={
                            "correlation_id": correlation_id,
                            "attempt": attempt_num,
                        },
                    )

                    result = await self._llm.ainvoke(messages)  # type: ignore[assignment]
                    latency_ms = (time.monotonic() - start) * 1000

                    logger.info(
                        "Groq invocation succeeded",
                        extra={
                            "correlation_id": correlation_id,
                            "attempt": attempt_num,
                            "latency_ms": round(latency_ms, 2),
                        },
                    )

        except RateLimitError as exc:
            logger.error(
                "Groq rate limit exceeded after retries",
                extra={"correlation_id": correlation_id, "retries": self._max_retries},
            )
            raise GroqRateLimitError(
                f"Groq rate limit exceeded after {self._max_retries} attempts."
            ) from exc

        except APITimeoutError as exc:
            logger.error(
                "Groq request timed out after retries",
                extra={"correlation_id": correlation_id, "retries": self._max_retries},
            )
            raise GroqTimeoutError(
                f"Groq request timed out after {self._max_retries} attempts."
            ) from exc

        except APIConnectionError as exc:
            logger.error(
                "Groq connection error after retries",
                extra={"correlation_id": correlation_id, "error": str(exc)},
            )
            raise GroqUnavailableError(
                f"Cannot reach Groq API after {self._max_retries} attempts: {exc}"
            ) from exc

        except RetryError as exc:
            raise GroqUnavailableError(
                "Groq service unavailable after exhausting all retry attempts."
            ) from exc

        # result is guaranteed non-None if we reach here (tenacity raises on failure)
        assert result is not None, "Tenacity loop exited without a result or exception"

        token_usage = self._extract_token_usage(result)
        return result, token_usage

    @staticmethod
    def _extract_token_usage(response: AIMessage) -> TokenUsage:
        """
        Extract token consumption from the model response.

        LangChain >= 0.3 populates ``AIMessage.usage_metadata`` with:
            ``{"input_tokens": N, "output_tokens": M, "total_tokens": T}``

        Falls back to zero values if the field is absent (some model
        configurations or test mocks may not include it).

        Args:
            response: The ``AIMessage`` returned by the LLM.

        Returns:
            A populated ``TokenUsage`` value object.
        """
        usage: dict[str, Any] = response.usage_metadata or {}  # type: ignore[assignment]
        return TokenUsage(
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )


# ---------------------------------------------------------------------------
# Dependency injection factory
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_groq_service() -> GroqService:
    """
    Build the application-wide ``GroqService`` singleton.

    The LLM instance is created once via ``LLMFactory`` and reused
    for every request, as recommended by LangChain.

    Returns:
        A fully configured ``GroqService`` instance.
    """
    settings = get_settings()
    llm = LLMFactory.create(LLMProvider.GROQ, settings)

    logger.info(
        "GroqService initialised",
        extra={
            "model": settings.GROQ_MODEL,
            "max_retries": settings.GROQ_MAX_RETRIES,
        },
    )

    return GroqService(
        llm=llm,
        max_retries=settings.GROQ_MAX_RETRIES,
        base_delay=settings.GROQ_BASE_DELAY,
        max_delay=settings.GROQ_MAX_DELAY,
    )


def get_groq_service() -> GroqService:
    """
    FastAPI dependency that returns the ``GroqService`` singleton.

    Usage in an endpoint or agent::

        async def handler(groq: GroqService = Depends(get_groq_service)):
            response, usage = await groq.invoke_with_retry(messages, corr_id)
    """
    return _build_groq_service()

"""
Healthcare AI Router — Router Agent (Intent Classification Only)
================================================================
The Router Agent is the sole entry point of the LangGraph graph.

Strict responsibilities:
    1. Load the classification prompt from ``backend/prompts/router.txt``.
    2. Build a message list (system + history context + user message).
    3. Call the Groq LLM via ``GroqService.invoke_with_retry()``.
    4. Parse the LLM's JSON response into a ``RouterOutput`` model.
    5. Return ONLY ``intent`` and ``confidence`` updates to the state.

What the Router Agent MUST NOT do:
    - Answer the user's question.
    - Generate business logic.
    - Know about MongoDB, FastAPI, or any downstream agent.
    - Produce anything other than a classification result.

Error handling:
    - If the LLM returns malformed JSON → state is updated with
      ``error`` set and ``intent="error"``, routing to ``error_node``.
    - If the Groq service is unavailable → the exception propagates
      as an ``AppBaseException`` and is caught by the ExceptionHandlerMiddleware
      (when invoked via the API). In graph-only tests, it is re-raised.

LangSmith tracing:
    Each invocation of this node is automatically traced by LangGraph
    when ``LANGCHAIN_TRACING_V2=true``. The ``run_name`` metadata is
    injected via the ``RunnableConfig`` in ``graph_builder.py``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from backend.schemas.router_schema import RouterOutput
from backend.services.groq_service import get_groq_service
from backend.utils.logger import get_logger
from backend.utils.prompt_loader import get_prompt_loader

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------


def _extract_json(text: str) -> dict[str, Any]:
    """
    Robustly extract a JSON object from an LLM response string.

    Handles:
        - Direct JSON strings: ``{"intent": "faq", "confidence": 0.97}``
        - Markdown-fenced JSON blocks: triple-backtick json fences
        - JSON embedded in prose: ``The intent is: {"intent": "faq", ...}``

    Args:
        text: Raw string returned by the LLM.

    Returns:
        Parsed Python dict.

    Raises:
        ValueError: If no valid JSON object is found in ``text``.
    """
    text = text.strip()

    # Strategy 1: entire response is valid JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: JSON inside a markdown code block
    for pattern in (
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
    ):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    # Strategy 3: first JSON object in the text
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"No valid JSON object found in LLM response. "
        f"First 300 chars: {text[:300]!r}"
    )


# ---------------------------------------------------------------------------
# Router Node
# ---------------------------------------------------------------------------


async def router_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Router Node — Classify the user's intent.

    This is the first node executed in the LangGraph Router Graph.
    It reads the user message and conversation history from ``state``,
    calls the Groq LLM, and returns ONLY the classified intent and
    confidence score. No business logic is performed here.

    Args:
        state: The current ``GraphState`` dict.

    Returns:
        A partial state dict with keys: ``intent``, ``confidence``,
        and optionally ``error``.
    """
    correlation_id: str = state.get("correlation_id", "")
    session_id: str = state.get("session_id", "")
    message: str = state.get("message", "")

    logger.info(
        "RouterNode: classifying intent",
        extra={
            "correlation_id": correlation_id,
            "session_id": session_id,
            "message_preview": message[:80],
        },
    )

    try:
        # ── Load system prompt ────────────────────────────────────────────────
        loader = get_prompt_loader()
        system_prompt: str = loader.get("router")

        # ── Build message list (system + user) ───────────────────────────────
        # We deliberately exclude conversation history from the router prompt.
        # The router classifies the CURRENT message only — history is not
        # relevant to intent classification and would waste tokens.
        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message),
        ]

        # ── Invoke LLM ───────────────────────────────────────────────────────
        groq = get_groq_service()
        ai_response, token_usage = await groq.invoke_with_retry(
            messages=llm_messages,
            correlation_id=correlation_id,
        )

        raw_text: str = ai_response.content  # type: ignore[assignment]

        # ── Parse JSON response ──────────────────────────────────────────────
        raw_json = _extract_json(raw_text)
        router_output = RouterOutput.model_validate(raw_json)

        logger.info(
            "RouterNode: classification complete",
            extra={
                "correlation_id": correlation_id,
                "intent": router_output.intent,
                "confidence": router_output.confidence,
                "total_tokens": token_usage.total_tokens,
            },
        )

        return {
            "intent": router_output.intent,
            "confidence": router_output.confidence,
            "token_usage": {
                "prompt_tokens": token_usage.prompt_tokens,
                "completion_tokens": token_usage.completion_tokens,
                "total_tokens": token_usage.total_tokens,
            },
        }

    except ValidationError as exc:
        error_msg = f"Router returned invalid intent JSON: {exc.errors()}"
        logger.error(
            "RouterNode: Pydantic validation failed",
            extra={"correlation_id": correlation_id, "error": error_msg},
        )
        return {"intent": "error", "confidence": 0.0, "error": error_msg}

    except ValueError as exc:
        error_msg = f"Router JSON parsing failed: {exc}"
        logger.error(
            "RouterNode: JSON extraction failed",
            extra={"correlation_id": correlation_id, "error": error_msg},
        )
        return {"intent": "error", "confidence": 0.0, "error": error_msg}

    except Exception as exc:
        error_msg = f"RouterNode unexpected error: {type(exc).__name__}: {exc}"
        logger.error(
            "RouterNode: unexpected failure",
            extra={"correlation_id": correlation_id, "error": error_msg},
        )
        return {"intent": "error", "confidence": 0.0, "error": error_msg}

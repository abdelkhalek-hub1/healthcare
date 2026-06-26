"""
Healthcare AI Router — Medical FAQ Agent Node
==============================================
Answers general medical questions about diseases, conditions, symptoms,
treatments, and procedures. Always appends the mandatory medical disclaimer.

Strict rule: the disclaimer is ALWAYS present in the response.
It is hardcoded in ``FAQData`` as a default and cannot be omitted by the LLM.

Phase 3 implementation:
    - Calls Groq with the FAQ prompt and user message.
    - Parses the JSON response into a ``FAQData``-compatible dict.
    - Enforces the disclaimer regardless of what the LLM returned.
    - Returns a populated ``AgentResponse`` in the graph state.

Phase 4 enhancements (to be added):
    - MongoDB write to ``faq_logs`` collection.
    - Full Pydantic structured output validation.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.models.domain import AgentName
from backend.schemas.agent_schemas import AgentResponse, FAQData
from backend.services.groq_service import get_groq_service
from backend.utils.logger import get_logger
from backend.utils.prompt_loader import get_prompt_loader

logger = get_logger(__name__)

# The disclaimer is defined here as well as in FAQData to make the
# enforcement explicit and visible to any developer reading this file.
MANDATORY_DISCLAIMER = (
    "This information does not replace professional medical advice. "
    "Always consult a qualified healthcare professional for diagnosis, "
    "treatment, and any health concerns specific to your situation."
)


def _parse_faq_json(text: str) -> dict[str, Any]:
    """
    Extract and parse the FAQ JSON from the LLM response.

    If the LLM returns plain prose instead of JSON, the entire text
    is treated as the answer and the disclaimer is appended separately.

    Args:
        text: Raw LLM output string.

    Returns:
        Dict with at least an ``"answer"`` key.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for pattern in (r"```json\s*(\{.*?\})\s*```", r"```\s*(\{.*?\})\s*```"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback: treat the entire response as the answer text
    return {"answer": text, "disclaimer": MANDATORY_DISCLAIMER}


async def faq_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    FAQ Node — Answer general medical questions with mandatory disclaimer.

    Reads the user message and history from state, calls Groq with the
    FAQ prompt, parses the response, and enforces the medical disclaimer
    regardless of the LLM output.

    Args:
        state: Current ``GraphState`` dict.

    Returns:
        Partial state dict with ``response`` and ``token_usage`` keys.
        The response ``answer`` always ends with the mandatory disclaimer.
    """
    correlation_id: str = state.get("correlation_id", "")
    session_id: str = state.get("session_id", "")
    message: str = state.get("message", "")

    logger.info(
        "FAQNode: processing request",
        extra={"correlation_id": correlation_id, "session_id": session_id},
    )

    try:
        loader = get_prompt_loader()
        system_prompt = loader.get("faq")

        llm_messages = [
            SystemMessage(content=system_prompt),
            *state.get("history", []),
            HumanMessage(content=message),
        ]

        groq = get_groq_service()
        ai_response, token_usage = await groq.invoke_with_retry(
            messages=llm_messages,
            correlation_id=correlation_id,
        )

        raw_data = _parse_faq_json(ai_response.content)  # type: ignore[arg-type]

        faq_data = FAQData(
            answer=raw_data.get("answer", ""),
            # Disclaimer is always overridden with the canonical text —
            # the LLM's version (if any) is ignored.
            disclaimer=MANDATORY_DISCLAIMER,
        )

        # Compose the full answer: LLM answer + newline + disclaimer
        full_answer = f"{faq_data.answer}\n\n[Medical Disclaimer] {faq_data.disclaimer}"

        agent_response = AgentResponse(
            correlation_id=correlation_id,
            session_id=session_id,
            intent="faq",
            agent=AgentName.FAQ.value,
            answer=full_answer,
            data=faq_data,
        )

        logger.info(
            "FAQNode: response generated",
            extra={
                "correlation_id": correlation_id,
                "answer_length": len(faq_data.answer),
                "total_tokens": token_usage.total_tokens,
            },
        )

        return {
            "response": agent_response.to_state_dict(),
            "token_usage": {
                "prompt_tokens": token_usage.prompt_tokens,
                "completion_tokens": token_usage.completion_tokens,
                "total_tokens": token_usage.total_tokens,
            },
        }

    except Exception as exc:
        error_msg = f"FAQNode error: {type(exc).__name__}: {exc}"
        logger.error(
            "FAQNode: failed",
            extra={"correlation_id": correlation_id, "error": error_msg},
        )
        return {
            "error": error_msg,
            "response": {
                "correlation_id": correlation_id,
                "session_id": session_id,
                "intent": "faq",
                "agent": AgentName.FAQ.value,
                "answer": "I encountered an issue answering your question. Please try again.",
                "data": None,
            },
        }

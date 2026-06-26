"""
Healthcare AI Router — Consultation Agent Node
================================================
Handles appointment booking requests. Extracts structured patient
data (name, specialty, date, city, doctor preference) from the
conversation and generates a natural-language booking confirmation.

Phase 3 implementation:
    - Calls Groq with the consultation prompt and user message.
    - Parses the JSON response into a ``ConsultationData``-compatible dict.
    - Returns a populated ``AgentResponse`` in the graph state.

Phase 4 enhancements (to be added):
    - MongoDB write to ``consultations`` collection.
    - Full Pydantic structured output validation.
    - Session-aware history injection for multi-turn booking flows.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.models.domain import AgentName
from backend.schemas.agent_schemas import AgentResponse, ConsultationData
from backend.services.groq_service import get_groq_service
from backend.utils.logger import get_logger
from backend.utils.prompt_loader import get_prompt_loader

logger = get_logger(__name__)


def _parse_consultation_json(text: str) -> dict[str, Any]:
    """
    Extract and parse the consultation JSON from the LLM response.

    Args:
        text: Raw LLM output string.

    Returns:
        Parsed dict with consultation fields.

    Raises:
        ValueError: If no valid JSON object is found.
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

    raise ValueError(f"No valid JSON in consultation response: {text[:200]!r}")


async def consultation_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Consultation Node — Extract patient data and generate a booking confirmation.

    Reads the user message and history from state, calls Groq with the
    consultation prompt, parses the structured response, and returns an
    ``AgentResponse`` stored in ``state["response"]``.

    Args:
        state: Current ``GraphState`` dict.

    Returns:
        Partial state dict with ``response`` and ``token_usage`` keys.
    """
    correlation_id: str = state.get("correlation_id", "")
    session_id: str = state.get("session_id", "")
    message: str = state.get("message", "")

    logger.info(
        "ConsultationNode: processing request",
        extra={"correlation_id": correlation_id, "session_id": session_id},
    )

    try:
        loader = get_prompt_loader()
        system_prompt = loader.get("consultation")

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

        raw_data = _parse_consultation_json(ai_response.content)  # type: ignore[arg-type]

        consultation_data = ConsultationData(
            patient_name=raw_data.get("patient_name"),
            specialty=raw_data.get("specialty"),
            preferred_date=raw_data.get("preferred_date"),
            city=raw_data.get("city"),
            doctor_preference=raw_data.get("doctor_preference"),
            confirmation=raw_data.get(
                "confirmation",
                "Your consultation request has been registered successfully.",
            ),
        )

        agent_response = AgentResponse(
            correlation_id=correlation_id,
            session_id=session_id,
            intent="consultation",
            agent=AgentName.CONSULTATION.value,
            answer=consultation_data.confirmation,
            data=consultation_data,
        )

        logger.info(
            "ConsultationNode: response generated",
            extra={
                "correlation_id": correlation_id,
                "specialty": consultation_data.specialty,
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
        error_msg = f"ConsultationNode error: {type(exc).__name__}: {exc}"
        logger.error(
            "ConsultationNode: failed",
            extra={"correlation_id": correlation_id, "error": error_msg},
        )
        return {
            "error": error_msg,
            "response": {
                "correlation_id": correlation_id,
                "session_id": session_id,
                "intent": "consultation",
                "agent": AgentName.CONSULTATION.value,
                "answer": "I encountered an issue processing your consultation request. Please try again.",
                "data": None,
            },
        }

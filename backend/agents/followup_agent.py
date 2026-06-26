"""
Healthcare AI Router — Follow-up Agent Node
=============================================
Handles ongoing symptom reports and post-treatment follow-up requests.
Assesses symptom severity, generates care recommendations, and flags
cases requiring urgent attention.

Phase 3 implementation:
    - Calls Groq with the followup prompt and user message.
    - Parses the JSON response into a ``FollowupData``-compatible dict.
    - Sets ``requires_urgent_care`` based on the LLM's assessment.
    - Returns a populated ``AgentResponse`` in the graph state.

Phase 4 enhancements (to be added):
    - MongoDB write to ``followups`` collection.
    - Urgency-based alert system integration.
    - Full Pydantic structured output validation.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.models.domain import AgentName
from backend.schemas.agent_schemas import AgentResponse, FollowupData
from backend.services.groq_service import get_groq_service
from backend.utils.logger import get_logger
from backend.utils.prompt_loader import get_prompt_loader

logger = get_logger(__name__)


def _parse_followup_json(text: str) -> dict[str, Any]:
    """
    Extract and parse the follow-up JSON from the LLM response.

    Args:
        text: Raw LLM output string.

    Returns:
        Parsed dict with follow-up fields.

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

    raise ValueError(f"No valid JSON in follow-up response: {text[:200]!r}")


async def followup_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Follow-up Node — Provide care guidance for ongoing symptoms.

    Reads the user message and history from state, calls Groq with the
    follow-up prompt, parses the structured response (including urgency
    assessment), and returns an ``AgentResponse`` in the graph state.

    Args:
        state: Current ``GraphState`` dict.

    Returns:
        Partial state dict with ``response`` and ``token_usage`` keys.
    """
    correlation_id: str = state.get("correlation_id", "")
    session_id: str = state.get("session_id", "")
    message: str = state.get("message", "")

    logger.info(
        "FollowupNode: processing request",
        extra={"correlation_id": correlation_id, "session_id": session_id},
    )

    try:
        loader = get_prompt_loader()
        system_prompt = loader.get("followup")

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

        raw_data = _parse_followup_json(ai_response.content)  # type: ignore[arg-type]

        followup_data = FollowupData(
            symptoms=raw_data.get("symptoms", []),
            recommendations=raw_data.get("recommendations", []),
            requires_urgent_care=bool(raw_data.get("requires_urgent_care", False)),
            answer=raw_data.get("answer", ""),
        )

        agent_response = AgentResponse(
            correlation_id=correlation_id,
            session_id=session_id,
            intent="followup",
            agent=AgentName.FOLLOWUP.value,
            answer=followup_data.answer,
            data=followup_data,
        )

        logger.info(
            "FollowupNode: response generated",
            extra={
                "correlation_id": correlation_id,
                "requires_urgent_care": followup_data.requires_urgent_care,
                "symptoms_count": len(followup_data.symptoms),
                "total_tokens": token_usage.total_tokens,
            },
        )

        if followup_data.requires_urgent_care:
            logger.warning(
                "FollowupNode: URGENT CARE REQUIRED",
                extra={
                    "correlation_id": correlation_id,
                    "session_id": session_id,
                    "symptoms": followup_data.symptoms,
                },
            )

        # ── Write to MongoDB (best-effort) ──────────────────────────────────────
        try:
            from backend.database.connection import get_database
            from backend.database.repository import FollowupRepository

            db = get_database()
            repo = FollowupRepository(db[FollowupRepository.COLLECTION])

            followup_doc = followup_data.model_dump()
            followup_doc["correlation_id"] = correlation_id
            followup_doc["session_id"] = session_id

            await repo.insert_one(followup_doc)
        except RuntimeError:
            logger.debug(
                "FollowupNode: MongoDB not initialised — skipping log write",
                extra={"correlation_id": correlation_id},
            )
        except Exception as exc:
            logger.warning(
                "FollowupNode: failed to write followup log",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(exc),
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
        error_msg = f"FollowupNode error: {type(exc).__name__}: {exc}"
        logger.error(
            "FollowupNode: failed",
            extra={"correlation_id": correlation_id, "error": error_msg},
        )
        return {
            "error": error_msg,
            "response": {
                "correlation_id": correlation_id,
                "session_id": session_id,
                "intent": "followup",
                "agent": AgentName.FOLLOWUP.value,
                "answer": "I encountered an issue processing your follow-up request. Please try again.",
                "data": None,
            },
        }

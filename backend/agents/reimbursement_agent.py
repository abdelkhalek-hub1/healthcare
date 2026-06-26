"""
Healthcare AI Router — Reimbursement Agent Node
=================================================
Handles insurance reimbursement inquiries. Explains the process,
lists required documents, coverage details, and processing timelines.

Phase 3 implementation:
    - Calls Groq with the reimbursement prompt and user message.
    - Parses the JSON response into a ``ReimbursementData``-compatible dict.
    - Returns a populated ``AgentResponse`` in the graph state.

Phase 4 enhancements (to be added):
    - MongoDB write to ``reimbursements`` collection.
    - Full Pydantic structured output validation.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.models.domain import AgentName
from backend.schemas.agent_schemas import AgentResponse, ReimbursementData
from backend.services.groq_service import get_groq_service
from backend.utils.logger import get_logger
from backend.utils.prompt_loader import get_prompt_loader

logger = get_logger(__name__)


def _parse_reimbursement_json(text: str) -> dict[str, Any]:
    """
    Extract and parse the reimbursement JSON from the LLM response.

    Args:
        text: Raw LLM output string.

    Returns:
        Parsed dict with reimbursement fields.

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

    raise ValueError(f"No valid JSON in reimbursement response: {text[:200]!r}")


async def reimbursement_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Reimbursement Node — Explain the reimbursement process.

    Reads the user message and history from state, calls Groq with the
    reimbursement prompt, parses the structured response, and returns an
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
        "ReimbursementNode: processing request",
        extra={"correlation_id": correlation_id, "session_id": session_id},
    )

    try:
        loader = get_prompt_loader()
        system_prompt = loader.get("reimbursement")

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

        raw_data = _parse_reimbursement_json(ai_response.content)  # type: ignore[arg-type]

        reimbursement_data = ReimbursementData(
            required_documents=raw_data.get("required_documents", []),
            coverage=raw_data.get("coverage", "Coverage information not available."),
            delay=raw_data.get("delay", "Processing time not specified."),
            steps=raw_data.get("steps", []),
            answer=raw_data.get("answer", ""),
        )

        agent_response = AgentResponse(
            correlation_id=correlation_id,
            session_id=session_id,
            intent="reimbursement",
            agent=AgentName.REIMBURSEMENT.value,
            answer=reimbursement_data.answer,
            data=reimbursement_data,
        )

        logger.info(
            "ReimbursementNode: response generated",
            extra={
                "correlation_id": correlation_id,
                "documents_count": len(reimbursement_data.required_documents),
                "total_tokens": token_usage.total_tokens,
            },
        )

        # ── Write to MongoDB (best-effort) ──────────────────────────────────────
        try:
            from backend.database.connection import get_database
            from backend.database.repository import ReimbursementRepository

            db = get_database()
            repo = ReimbursementRepository(db[ReimbursementRepository.COLLECTION])

            reimbursement_doc = reimbursement_data.model_dump()
            reimbursement_doc["correlation_id"] = correlation_id
            reimbursement_doc["session_id"] = session_id

            await repo.insert_one(reimbursement_doc)
        except RuntimeError:
            logger.debug(
                "ReimbursementNode: MongoDB not initialised — skipping log write",
                extra={"correlation_id": correlation_id},
            )
        except Exception as exc:
            logger.warning(
                "ReimbursementNode: failed to write reimbursement log",
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
        error_msg = f"ReimbursementNode error: {type(exc).__name__}: {exc}"
        logger.error(
            "ReimbursementNode: failed",
            extra={"correlation_id": correlation_id, "error": error_msg},
        )
        return {
            "error": error_msg,
            "response": {
                "correlation_id": correlation_id,
                "session_id": session_id,
                "intent": "reimbursement",
                "agent": AgentName.REIMBURSEMENT.value,
                "answer": "I encountered an issue processing your reimbursement inquiry. Please try again.",
                "data": None,
            },
        }

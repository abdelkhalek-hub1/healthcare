"""
Healthcare AI Router — API Route Handlers
=========================================
Implements all FastAPI endpoints for:
    - Chat execution (routes request to LangGraph StateGraph)
    - User feedback collection (thumbs up/down)
    - Session listing and history lookup
    - Telemetry monitoring and metrics aggregation
    - Service health checks (MongoDB & Groq API)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.database.connection import check_mongo_health
from backend.database.repository import (
    FeedbackRepository,
    MessageRepository,
    MonitoringLogRepository,
    SessionRepository,
    get_feedback_repository,
    get_message_repository,
    get_monitoring_repository,
    get_session_repository,
)
from backend.graph.graph_builder import invoke_graph
from backend.models.domain import (
    HealthStatus,
    ServiceHealth,
    Session,
    SystemHealth,
)
from backend.schemas.agent_schemas import AgentResponse
from backend.schemas.error_schema import SessionNotFoundError
from backend.services.groq_service import GroqService, get_groq_service
from backend.services.session_manager import SessionManager, get_session_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Healthcare AI Router"])

# Record start time for uptime calculations
ROUTES_START_TIME = time.monotonic()


# =============================================================================
# Request & Response Schemas
# =============================================================================


class ChatRequest(BaseModel):
    """Payload to initiate a new message turn in a session."""
    message: str = Field(..., description="The user's message text.")
    session_id: str | None = Field(default=None, description="Optional UUID session identifier.")


class FeedbackRequest(BaseModel):
    """Payload to rate a specific assistant response turn."""
    correlation_id: str = Field(..., description="The correlation ID of the assistant message.")
    rating: int = Field(..., description="Feedback value: 1 for positive, 0 or -1 for negative.")
    comment: str | None = Field(default=None, description="Optional detailed feedback comment.")


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/chat",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a message to the AI Healthcare Assistant",
)
async def chat(
    request: Request,
    payload: ChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> dict[str, Any]:
    """
    Submits a message, loads session context history, executes the LangGraph
    router pattern, stores results, and returns the response envelope.
    """
    correlation_id: str = getattr(request.state, "correlation_id", "unknown")
    logger.info(
        "Received chat request",
        extra={
            "correlation_id": correlation_id,
            "session_id": payload.session_id,
            "message_length": len(payload.message),
        },
    )

    # 1. Load or create the session
    session: Session = await session_manager.get_or_create_session(payload.session_id)

    # 2. Retrieve history (LangChain BaseMessage list)
    history = await session_manager.get_history(session.id)

    # 3. Save the new user message to MongoDB
    await session_manager.save_user_message(session.id, payload.message, correlation_id)

    # 4. Invoke LangGraph router graph
    final_state = await invoke_graph(
        message=payload.message,
        session_id=session.id,
        correlation_id=correlation_id,
        history=history,
    )

    # 5. Save assistant reply turn to MongoDB
    response_dict: dict[str, Any] = final_state.get("response") or {}
    answer: str = response_dict.get("answer", "")
    intent: str = final_state.get("intent", "error")
    agent: str = response_dict.get("agent", "RouterAgent")
    token_usage: dict[str, int] | None = final_state.get("token_usage")

    await session_manager.save_assistant_message(
        session_id=session.id,
        message=answer,
        correlation_id=correlation_id,
        intent=intent,
        agent=agent,
        token_usage=token_usage,
    )

    # Ensure the returned payload matches the AgentResponse format
    # (final_state["response"] is already serialised from AgentResponse)
    return response_dict


@router.post(
    "/feedback",
    status_code=status.HTTP_200_OK,
    summary="Submit user feedback for an assistant response",
)
async def submit_feedback(
    payload: FeedbackRequest,
    feedback_repo: FeedbackRepository = Depends(get_feedback_repository),
) -> dict[str, str]:
    """
    Saves a user rating and optional comment for a specific assistant turn
    using the correlation ID.
    """
    logger.info(
        "Submitting user feedback",
        extra={"correlation_id": payload.correlation_id, "rating": payload.rating},
    )

    await feedback_repo.upsert_feedback(payload.model_dump())

    return {
        "status": "success",
        "message": "Feedback submitted successfully.",
    }


@router.get(
    "/health",
    response_model=SystemHealth,
    status_code=status.HTTP_200_OK,
    summary="Check API status and downstream dependencies",
)
async def health(
    groq_service: GroqService = Depends(get_groq_service),
) -> SystemHealth:
    """
    Performs live connectivity checks against MongoDB and the Groq LLM API.
    Calculates application uptime and returns an aggregated health report.
    """
    settings = get_settings()

    # 1. MongoDB connectivity check
    db_ok, db_latency = await check_mongo_health()
    db_status = HealthStatus.HEALTHY if db_ok else HealthStatus.UNHEALTHY
    db_health = ServiceHealth(
        name="MongoDB",
        status=db_status,
        latency_ms=db_latency if db_latency >= 0 else None,
        error=None if db_ok else "Unable to ping MongoDB",
    )

    # 2. Groq connectivity check
    groq_ok, groq_latency = await groq_service.check_connectivity()
    groq_status = HealthStatus.HEALTHY if groq_ok else HealthStatus.UNHEALTHY
    groq_health = ServiceHealth(
        name="Groq API",
        status=groq_status,
        latency_ms=groq_latency if groq_latency >= 0 else None,
        error=None if groq_ok else "Unable to connect to Groq API",
    )

    # Calculate overall health status
    overall_status = HealthStatus.HEALTHY
    if db_status == HealthStatus.UNHEALTHY or groq_status == HealthStatus.UNHEALTHY:
        overall_status = HealthStatus.UNHEALTHY

    uptime = time.monotonic() - ROUTES_START_TIME

    return SystemHealth(
        status=overall_status,
        version=settings.APP_VERSION,
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(tz=timezone.utc),
        services={
            "mongodb": db_health,
            "groq": groq_health,
        },
        metrics={},
    )


@router.get(
    "/sessions",
    status_code=status.HTTP_200_OK,
    summary="List recent conversation sessions",
)
async def list_sessions(
    limit: int = Query(default=20, le=50, description="Max sessions to list"),
    session_repo: SessionRepository = Depends(get_session_repository),
) -> list[dict[str, Any]]:
    """Retrieves a list of recent conversation session documents."""
    return await session_repo.list_recent(limit=limit)


@router.get(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve session metadata detail",
)
async def get_session_detail(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repository),
) -> dict[str, Any]:
    """Retrieves metadata for a specific session ID. Raises 404 if not found."""
    doc = await session_repo.get_by_id(session_id)
    if not doc:
        raise SessionNotFoundError(session_id)
    return doc


@router.get(
    "/sessions/{session_id}/history",
    status_code=status.HTTP_200_OK,
    summary="Get conversation history logs",
)
async def get_session_history_logs(
    session_id: str,
    limit: int = Query(default=50, le=100, description="Max messages to retrieve"),
    message_repo: MessageRepository = Depends(get_message_repository),
) -> list[dict[str, Any]]:
    """Retrieves recent conversation turn log documents for a specific session."""
    return await message_repo.get_session_history(session_id, limit=limit)


@router.get(
    "/monitoring",
    status_code=status.HTTP_200_OK,
    summary="List recent execution telemetry logs",
)
async def list_monitoring_logs(
    limit: int = Query(default=50, le=100, description="Max logs to retrieve"),
    monitoring_repo: MonitoringLogRepository = Depends(get_monitoring_repository),
) -> list[dict[str, Any]]:
    """Retrieves recent LangGraph execution telemetry documents."""
    return await monitoring_repo.get_recent(limit=limit)


@router.get(
    "/monitoring/metrics",
    status_code=status.HTTP_200_OK,
    summary="Retrieve system aggregate metrics",
)
async def get_monitoring_metrics(
    monitoring_repo: MonitoringLogRepository = Depends(get_monitoring_repository),
    feedback_repo: FeedbackRepository = Depends(get_feedback_repository),
) -> dict[str, Any]:
    """Calculates latency, token usage, success rate, and user feedback rates."""
    metrics = await monitoring_repo.compute_aggregate_metrics()
    satisfaction = await feedback_repo.compute_satisfaction_rate()
    metrics["satisfaction_rate"] = round(satisfaction, 4)
    return metrics


@router.get(
    "/monitoring/agents",
    status_code=status.HTTP_200_OK,
    summary="Get request breakdown per specialized agent",
)
async def get_agent_breakdown(
    monitoring_repo: MonitoringLogRepository = Depends(get_monitoring_repository),
) -> list[dict[str, Any]]:
    """Retrieves a count and average latency report grouped by agent node."""
    return await monitoring_repo.get_agent_breakdown()

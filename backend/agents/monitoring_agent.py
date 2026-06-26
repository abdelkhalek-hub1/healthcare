"""
Healthcare AI Router — Monitoring Agent Node
=============================================
The Monitoring Node is the final node in every execution path. It runs
AFTER the specialised agent node and BEFORE ``END``.

Strict responsibilities:
    1. Compute execution latency from ``state["start_time"]``.
    2. Collect token usage from ``state["token_usage"]``.
    3. Construct a ``MonitoringLog`` Pydantic model.
    4. Write the log to MongoDB ``monitoring_logs`` collection (best-effort).
    5. Update ``state["monitoring"]`` with the serialised log.

What the Monitoring Node MUST NOT do:
    - Call the Groq LLM.
    - Modify ``state["response"]`` or ``state["intent"]``.
    - Crash the graph if MongoDB is unavailable (fail-safe logging).

LangSmith tracing:
    Tracing of this node is automatic via LangGraph when
    ``LANGCHAIN_TRACING_V2=true``.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from backend.models.domain import AgentName
from backend.schemas.monitoring_schema import MonitoringLog
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def monitoring_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Monitoring Node — Record telemetry for every graph execution.

    This node has no LLM dependency and is designed to be extremely
    resilient. MongoDB failures are logged as warnings and do not
    propagate — the graph always returns successfully even if monitoring
    write fails.

    Args:
        state: Current ``GraphState`` dict.

    Returns:
        Partial state dict with ``monitoring`` key populated.
    """
    correlation_id: str = state.get("correlation_id", "")
    session_id: str = state.get("session_id", "")

    # ── Compute execution time ────────────────────────────────────────────────
    start_time: float = state.get("start_time", time.monotonic())
    latency_ms: float = (time.monotonic() - start_time) * 1000

    # ── Collect state data ────────────────────────────────────────────────────
    response: dict[str, Any] = state.get("response") or {}
    token_usage: dict[str, int] = state.get("token_usage") or {}
    error_text: str | None = state.get("error")
    intent: str = state.get("intent", "unknown")

    selected_agent: str = response.get("agent", AgentName.MONITORING.value)
    status: str = "error" if error_text else "success"

    logger.info(
        "MonitoringNode: recording telemetry",
        extra={
            "correlation_id": correlation_id,
            "session_id": session_id,
            "intent": intent,
            "selected_agent": selected_agent,
            "latency_ms": round(latency_ms, 2),
            "status": status,
            "total_tokens": token_usage.get("total_tokens", 0),
        },
    )

    # ── Build monitoring log ──────────────────────────────────────────────────
    monitoring_log = MonitoringLog(
        correlation_id=correlation_id,
        session_id=session_id,
        timestamp=datetime.now(tz=timezone.utc),
        selected_agent=selected_agent,
        intent=intent,
        latency_ms=round(latency_ms, 2),
        execution_time_ms=round(latency_ms, 2),
        prompt_tokens=token_usage.get("prompt_tokens", 0),
        completion_tokens=token_usage.get("completion_tokens", 0),
        total_tokens=token_usage.get("total_tokens", 0),
        status=status,  # type: ignore[arg-type]
        error=error_text,
    )

    log_dict = monitoring_log.to_mongo_doc()

    # ── Write to MongoDB (best-effort — never crash the graph) ────────────────
    await _write_monitoring_log(log_dict, correlation_id)

    return {"monitoring": log_dict}


async def _write_monitoring_log(
    log_doc: dict[str, Any],
    correlation_id: str,
) -> None:
    """
    Persist the monitoring log to MongoDB ``monitoring_logs`` collection.

    Failures are caught and logged as warnings — this is intentional
    best-effort behaviour that prevents a MongoDB outage from breaking
    the main request flow.

    Args:
        log_doc:        The serialised ``MonitoringLog`` dict.
        correlation_id: For structured error logging.
    """
    try:
        from backend.database.connection import get_database
        from backend.database.repository import MonitoringLogRepository

        db = get_database()
        repo = MonitoringLogRepository(db[MonitoringLogRepository.COLLECTION])
        inserted_id = await repo.insert_one(log_doc)

        logger.debug(
            "MonitoringNode: log persisted",
            extra={
                "correlation_id": correlation_id,
                "inserted_id": inserted_id,
            },
        )

    except RuntimeError:
        # MongoDB not yet initialised (e.g., running tests without DB)
        logger.debug(
            "MonitoringNode: MongoDB not initialised — skipping log write",
            extra={"correlation_id": correlation_id},
        )

    except Exception as exc:
        logger.warning(
            "MonitoringNode: failed to write monitoring log",
            extra={
                "correlation_id": correlation_id,
                "error": str(exc),
            },
        )

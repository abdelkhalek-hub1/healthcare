"""
Healthcare AI Router — LangGraph Router Graph Builder
=====================================================
Constructs and compiles the LangGraph StateGraph that implements the
Router Pattern architecture.

Graph topology:
    START
      │
      ▼
    router_node                          ← Classifies intent only
      │
      ▼ (conditional_edge: route_to_agent)
      ├──► consultation_node  ─────────┐
      ├──► reimbursement_node ─────────┤──► monitoring_node ──► END
      ├──► followup_node ──────────────┤
      ├──► faq_node ───────────────────┤
      └──► error_node ─────────────────┘

Extensibility (rule #8 — adding a future agent):
    1. Create ``backend/agents/new_agent.py`` with a node function.
    2. Add ``"new_intent": "new_node"`` to ``_INTENT_ROUTING_MAP``.
    3. Call ``graph.add_node("new_node", new_node_fn)``.
    4. Call ``graph.add_edge("new_node", "monitoring_node")``.
    5. Add ``"new_intent": "new_node"`` to ``add_conditional_edges`` mapping.
    → No modifications to existing nodes, prompts, or schemas required.

LangSmith tracing:
    All nodes are automatically traced by LangGraph when the environment
    variables ``LANGCHAIN_TRACING_V2=true`` and ``LANGCHAIN_API_KEY`` are set.
    The ``RunnableConfig`` passed to ``ainvoke`` carries the ``run_name`` that
    appears in the LangSmith UI.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from backend.agents.consultation_agent import consultation_node
from backend.agents.faq_agent import faq_node
from backend.agents.followup_agent import followup_node
from backend.agents.monitoring_agent import monitoring_node
from backend.agents.reimbursement_agent import reimbursement_node
from backend.agents.router_agent import router_node
from backend.graph.state import GraphState, build_initial_state
from backend.models.domain import AgentName
from backend.schemas.agent_schemas import AgentResponse, ErrorData
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Routing map — the single place to register intents ↔ nodes
# ---------------------------------------------------------------------------

#: Maps each recognised intent to its handler node name.
#: To add a new agent: add one entry here. Nothing else changes.
_INTENT_ROUTING_MAP: dict[str, str] = {
    "consultation": "consultation_node",
    "reimbursement": "reimbursement_node",
    "followup": "followup_node",
    "faq": "faq_node",
}


# ---------------------------------------------------------------------------
# Error Node
# ---------------------------------------------------------------------------


async def error_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Error Node — Return a standardised error response.

    This node is reached when the Router Node returns ``intent="error"``
    due to malformed JSON, failed Pydantic validation, or an unexpected
    exception. It does NOT call the LLM.

    Args:
        state: Current ``GraphState`` dict.

    Returns:
        Partial state dict with an ``AgentResponse`` error payload.
    """
    correlation_id: str = state.get("correlation_id", "")
    session_id: str = state.get("session_id", "")
    error_text: str = state.get("error") or "Intent classification failed."

    logger.error(
        "ErrorNode: handling classification failure",
        extra={
            "correlation_id": correlation_id,
            "error": error_text,
        },
    )

    error_response = AgentResponse(
        correlation_id=correlation_id,
        session_id=session_id,
        intent="error",
        agent=AgentName.ROUTER.value,
        answer=(
            "I was unable to understand your request. "
            "Please rephrase your question and try again."
        ),
        data=ErrorData(
            code="INTENT_CLASSIFICATION_FAILED",
            message=error_text,
        ),
    )

    return {"response": error_response.to_state_dict()}


# ---------------------------------------------------------------------------
# Conditional edge function
# ---------------------------------------------------------------------------


def route_to_agent(state: dict[str, Any]) -> str:
    """
    Determine which node to execute after the Router Node.

    This is a pure function — it reads ``state["intent"]`` and returns
    the corresponding node name from ``_INTENT_ROUTING_MAP``. No LLM
    call, no side effects.

    Adding a new route requires only adding one entry to
    ``_INTENT_ROUTING_MAP``. This function never needs to change.

    Args:
        state: Current ``GraphState`` dict (after router_node has run).

    Returns:
        The node name to execute next (string key registered in the graph).
    """
    intent: str = state.get("intent", "")
    next_node: str = _INTENT_ROUTING_MAP.get(intent, "error_node")

    logger.debug(
        "Routing decision",
        extra={
            "intent": intent,
            "confidence": state.get("confidence", 0.0),
            "next_node": next_node,
            "correlation_id": state.get("correlation_id", ""),
        },
    )

    return next_node


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_compiled_graph():  # type: ignore[return]
    """
    Build and compile the LangGraph Router StateGraph.

    Uses ``@lru_cache`` so the (expensive) compilation happens exactly
    once per process lifetime. The compiled graph is thread-safe and
    can be shared across concurrent requests.

    Returns:
        A compiled ``CompiledStateGraph`` ready for ``ainvoke()``.
    """
    graph: StateGraph = StateGraph(GraphState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("router_node", router_node)
    graph.add_node("consultation_node", consultation_node)
    graph.add_node("reimbursement_node", reimbursement_node)
    graph.add_node("followup_node", followup_node)
    graph.add_node("faq_node", faq_node)
    graph.add_node("error_node", error_node)
    graph.add_node("monitoring_node", monitoring_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.add_edge(START, "router_node")

    # ── Conditional routing from router to specialised agent ─────────────────
    graph.add_conditional_edges(
        "router_node",
        route_to_agent,
        {
            "consultation_node": "consultation_node",
            "reimbursement_node": "reimbursement_node",
            "followup_node": "followup_node",
            "faq_node": "faq_node",
            "error_node": "error_node",
        },
    )

    # ── All agent nodes (including error) lead to monitoring ──────────────────
    for _agent_node in (
        "consultation_node",
        "reimbursement_node",
        "followup_node",
        "faq_node",
        "error_node",
    ):
        graph.add_edge(_agent_node, "monitoring_node")

    # ── Monitoring leads to END ───────────────────────────────────────────────
    graph.add_edge("monitoring_node", END)

    compiled = graph.compile()

    logger.info(
        "LangGraph Router Graph compiled",
        extra={
            "nodes": list(_INTENT_ROUTING_MAP.keys()) + ["error"],
            "routing_map": _INTENT_ROUTING_MAP,
        },
    )

    return compiled


# ---------------------------------------------------------------------------
# Public invocation function
# ---------------------------------------------------------------------------


async def invoke_graph(
    message: str,
    session_id: str,
    correlation_id: str,
    history: list[BaseMessage] | None = None,
) -> dict[str, Any]:
    """
    Invoke the compiled LangGraph Router Graph for a single user message.

    This is the primary entry point called by the FastAPI route handlers
    (Phase 5). It handles state initialisation, graph invocation, and
    final state extraction.

    Args:
        message:        The user's input message.
        session_id:     UUID of the current conversation session.
        correlation_id: Request-scoped correlation UUID from the middleware.
        history:        Prior conversation ``BaseMessage`` objects (oldest first).
                        Defaults to an empty list.

    Returns:
        The final ``GraphState`` dict after all nodes have executed.
        Key fields: ``intent``, ``confidence``, ``response``, ``monitoring``,
        ``error``.

    Raises:
        Any unhandled exception from a node (caught by FastAPI middleware
        in production; propagates in tests for assertion).
    """
    start_time = time.monotonic()

    initial_state = build_initial_state(
        message=message,
        session_id=session_id,
        correlation_id=correlation_id,
        history=history or [],
        start_time=start_time,
    )

    # RunnableConfig allows LangSmith to group all node traces under one
    # parent run named after the correlation ID.
    config: RunnableConfig = {
        "run_name": f"healthcare-router-{correlation_id[:8]}",
        "tags": ["healthcare-ai", "router-graph"],
        "metadata": {
            "correlation_id": correlation_id,
            "session_id": session_id,
        },
    }

    logger.info(
        "Graph invocation started",
        extra={
            "correlation_id": correlation_id,
            "session_id": session_id,
            "message_preview": message[:80],
            "history_turns": len(history or []),
        },
    )

    compiled = get_compiled_graph()
    final_state: dict[str, Any] = await compiled.ainvoke(initial_state, config=config)

    logger.info(
        "Graph invocation complete",
        extra={
            "correlation_id": correlation_id,
            "intent": final_state.get("intent"),
            "agent": (final_state.get("response") or {}).get("agent"),
            "status": "error" if final_state.get("error") else "success",
        },
    )

    return final_state

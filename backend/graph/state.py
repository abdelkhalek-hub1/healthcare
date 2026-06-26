"""
Healthcare AI Router — LangGraph State Definition
==================================================
Defines the single, shared ``GraphState`` TypedDict that flows through
every node in the LangGraph Router Graph.

Design decisions:
    - ``TypedDict`` (not Pydantic) is used as recommended by LangGraph.
    - Every field is present from the initial invocation onward; nodes only
      update the fields they are responsible for.
    - Fields are organised into four semantic groups:
        1. **Input** — supplied by the API layer before graph invocation.
        2. **Router** — populated exclusively by the Router Node.
        3. **Agent** — populated by whichever Specialized Agent Node runs.
        4. **Monitoring** — populated by the Monitoring Node after every execution.
    - ``start_time`` and ``token_usage`` are operational fields (not part of
      the API response) that enable accurate execution-time measurement and
      token accounting in the Monitoring Node.

Extensibility (rule #8):
    Adding a new agent requires NO changes to ``GraphState``. The new agent
    node simply writes its output to ``response`` and ``token_usage`` —
    the same fields used by all existing agents.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class GraphState(TypedDict):
    """
    Immutable-by-convention state that flows through the router graph.

    Each node returns a *partial dict* that LangGraph merges into this state.
    Nodes must only write to the fields they own.
    """

    # ── 1. Input (set once by the API layer) ─────────────────────────────────
    message: str
    """The raw user message to process."""

    session_id: str
    """UUID identifying the current conversation session."""

    correlation_id: str
    """UUID for end-to-end request tracing across logs, DB, and LangSmith."""

    history: list[BaseMessage]
    """Conversation history loaded by the Session Manager (oldest → newest)."""

    start_time: float
    """``time.monotonic()`` recorded at graph invocation; used for latency calc."""

    # ── 2. Router Node output ─────────────────────────────────────────────────
    intent: str
    """
    Classified intent string.

    Valid values: ``"consultation"``, ``"reimbursement"``, ``"followup"``, ``"faq"``.
    Set to ``"error"`` if classification fails.
    """

    confidence: float
    """Router's confidence score for the classified intent (0.0 – 1.0)."""

    # ── 3. Specialized Agent Node output ──────────────────────────────────────
    response: dict[str, Any] | None
    """
    Agent response payload.

    Structure set by the agent node; consumed by the API layer and stored
    in MongoDB by the Monitoring Node. Always includes ``"agent"`` and
    ``"answer"`` keys.
    """

    token_usage: dict[str, int] | None
    """
    Token consumption from the LLM call inside the agent node.

    Keys: ``prompt_tokens``, ``completion_tokens``, ``total_tokens``.
    Set to ``None`` for error paths that skip the LLM call.
    """

    # ── 4. Monitoring Node output ─────────────────────────────────────────────
    monitoring: dict[str, Any] | None
    """
    Telemetry record produced by the Monitoring Node.

    Mirrors ``MonitoringLog`` schema. Stored in MongoDB ``monitoring_logs``
    collection and sent to LangSmith.
    """

    # ── 5. Error (set by any node on failure) ────────────────────────────────
    error: str | None
    """
    Human-readable error description.

    ``None`` on successful execution. Presence triggers the ``error_node``
    route and causes the Monitoring Node to log ``status="error"``.
    """


def build_initial_state(
    message: str,
    session_id: str,
    correlation_id: str,
    history: list[BaseMessage],
    start_time: float,
) -> GraphState:
    """
    Construct a fully initialised ``GraphState`` for graph invocation.

    All optional fields are set to their zero values so that every node
    can safely read from the state without ``KeyError``.

    Args:
        message:        The user's input message.
        session_id:     UUID of the current conversation session.
        correlation_id: Request-scoped correlation UUID.
        history:        Prior conversation messages from the Session Manager.
        start_time:     ``time.monotonic()`` captured before graph invocation.

    Returns:
        A fully populated ``GraphState`` ready for ``compiled_graph.ainvoke()``.
    """
    return GraphState(
        message=message,
        session_id=session_id,
        correlation_id=correlation_id,
        history=history,
        start_time=start_time,
        intent="",
        confidence=0.0,
        response=None,
        token_usage=None,
        monitoring=None,
        error=None,
    )

"""
Healthcare AI Router — LangGraph Router Graph Integration Tests
==============================================================
Tests the compiled StateGraph's end-to-end routing behavior.
"""

from __future__ import annotations

import pytest

from backend.graph.graph_builder import invoke_graph
from backend.models.domain import AgentName


@pytest.mark.asyncio
async def test_graph_integration_consultation(mock_groq) -> None:
    """Test full graph execution path routing to ConsultationAgent."""
    result = await invoke_graph(
        message="I want to book an appointment with a cardiologist",
        session_id="session-graph-1",
        correlation_id="corr-graph-1",
        history=[],
    )

    assert result["intent"] == "consultation"
    assert result.get("error") is None
    assert result["response"] is not None
    assert result["response"]["agent"] == AgentName.CONSULTATION.value
    assert result["response"]["data"]["patient_name"] == "John Doe"
    assert result["monitoring"] is not None
    assert result["monitoring"]["selected_agent"] == AgentName.CONSULTATION.value
    assert result["monitoring"]["status"] == "success"


@pytest.mark.asyncio
async def test_graph_integration_reimbursement(mock_groq) -> None:
    """Test full graph execution path routing to ReimbursementAgent."""
    result = await invoke_graph(
        message="How can I get reimbursed for my surgery?",
        session_id="session-graph-2",
        correlation_id="corr-graph-2",
        history=[],
    )

    assert result["intent"] == "reimbursement"
    assert result.get("error") is None
    assert result["response"]["agent"] == AgentName.REIMBURSEMENT.value
    assert result["monitoring"]["selected_agent"] == AgentName.REIMBURSEMENT.value


@pytest.mark.asyncio
async def test_graph_integration_followup(mock_groq) -> None:
    """Test full graph execution path routing to FollowupAgent."""
    result = await invoke_graph(
        message="My fever has not gone down after 3 days",
        session_id="session-graph-3",
        correlation_id="corr-graph-3",
        history=[],
    )

    assert result["intent"] == "followup"
    assert result.get("error") is None
    assert result["response"]["agent"] == AgentName.FOLLOWUP.value
    assert result["response"]["data"]["requires_urgent_care"] is True
    assert result["monitoring"]["selected_agent"] == AgentName.FOLLOWUP.value


@pytest.mark.asyncio
async def test_graph_integration_faq(mock_groq) -> None:
    """Test full graph execution path routing to FAQAgent."""
    result = await invoke_graph(
        message="What is diabetes?",
        session_id="session-graph-4",
        correlation_id="corr-graph-4",
        history=[],
    )

    assert result["intent"] == "faq"
    assert result.get("error") is None
    assert result["response"]["agent"] == AgentName.FAQ.value
    assert result["monitoring"]["selected_agent"] == AgentName.FAQ.value


@pytest.mark.asyncio
async def test_graph_integration_error(mock_groq) -> None:
    """Test full graph execution path routing to error_node."""
    # Force LLM router output failure
    mock_groq.should_raise_generic = True

    result = await invoke_graph(
        message="Hello",
        session_id="session-graph-5",
        correlation_id="corr-graph-5",
        history=[],
    )

    assert result["intent"] == "error"
    assert "Generic Groq LLM failure" in result.get("error", "")
    assert result["response"]["agent"] == AgentName.ROUTER.value
    assert result["response"]["intent"] == "error"
    assert result["monitoring"]["selected_agent"] == AgentName.ROUTER.value
    assert result["monitoring"]["status"] == "error"

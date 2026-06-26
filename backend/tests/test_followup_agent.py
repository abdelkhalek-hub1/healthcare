"""
Healthcare AI Router — Follow-up Agent Node Tests
=================================================
Tests the followup_node function in isolation.
Verifies recommendations and urgent condition routing logic.
"""

from __future__ import annotations

import pytest

from backend.agents.followup_agent import followup_node


@pytest.mark.asyncio
async def test_followup_node_success(mock_groq) -> None:
    """Verify that symptoms are logged and recommendations are returned."""
    state = {
        "message": "I still feel a bit weak after my session",
        "correlation_id": "corr-follow",
        "session_id": "sess-follow",
        "history": [],
    }

    result = await followup_node(state)
    assert result.get("error") is None

    response = result["response"]
    assert response["intent"] == "followup"
    assert response["agent"] == "FollowupAgent"
    assert "fever" in response["data"]["symptoms"]
    assert "Rest" in response["data"]["recommendations"]
    assert response["data"]["requires_urgent_care"] is False


@pytest.mark.asyncio
async def test_followup_node_urgent(mock_groq) -> None:
    """Verify that severe symptoms flag requires_urgent_care as True."""
    state = {
        "message": "I have a high fever for 3 days",
        "correlation_id": "corr-follow-urg",
        "session_id": "sess-follow-urg",
        "history": [],
    }

    result = await followup_node(state)
    assert result.get("error") is None
    response = result["response"]
    assert response["data"]["requires_urgent_care"] is True

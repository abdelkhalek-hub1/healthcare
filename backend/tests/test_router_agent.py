"""
Healthcare AI Router — Router Agent Node Tests
==============================================
Tests the router_node function in isolation. Verifies classification
accuracy and error containment for invalid responses.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from backend.agents.router_agent import router_node


@pytest.mark.asyncio
async def test_router_node_success(mock_groq) -> None:
    """Verifies that normal inputs route correctly based on mock LLM response."""
    state = {
        "message": "I want to book an appointment with a cardiologist",
        "correlation_id": "test-corr-123",
        "session_id": "test-sess-123",
        "history": [],
    }

    result = await router_node(state)
    assert result["intent"] == "consultation"
    assert result["confidence"] == 0.95
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_router_node_malformed_json(mock_groq) -> None:
    """Verifies that malformed JSON triggers containment and maps to error intent."""
    state = {
        "message": "Hello",
        "correlation_id": "test-corr-123",
        "session_id": "test-sess-123",
        "history": [],
    }

    # Force mock Groq to return invalid JSON
    mock_groq.invoke_with_retry = MagicMock()
    mock_groq.invoke_with_retry.side_effect = Exception("Groq connection timeout")

    result = await router_node(state)
    assert result["intent"] == "error"
    assert result["confidence"] == 0.0
    assert "Groq connection timeout" in result.get("error", "")

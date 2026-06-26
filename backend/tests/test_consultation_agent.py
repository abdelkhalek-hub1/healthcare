"""
Healthcare AI Router — Consultation Agent Node Tests
===================================================
Tests the consultation_node function in isolation.
Verifies that appointment information is correctly extracted.
"""

from __future__ import annotations

import pytest

from backend.agents.consultation_agent import consultation_node


@pytest.mark.asyncio
async def test_consultation_node_success(mock_groq) -> None:
    """Verify extracting slots and generating response envelope."""
    state = {
        "message": "I want to see a cardiologist in Paris next week",
        "correlation_id": "corr-consult",
        "session_id": "sess-consult",
        "history": [],
    }

    result = await consultation_node(state)
    assert result.get("error") is None
    assert result["token_usage"] is not None

    response = result["response"]
    assert response["intent"] == "consultation"
    assert response["agent"] == "ConsultationAgent"
    assert response["data"]["patient_name"] == "John Doe"
    assert response["data"]["specialty"] == "cardiologist"
    assert response["data"]["city"] == "Paris"

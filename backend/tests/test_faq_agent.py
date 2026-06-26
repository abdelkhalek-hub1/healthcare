"""
Healthcare AI Router — FAQ Agent Node Tests
===========================================
Tests the faq_node function in isolation.
Verifies that the legal medical disclaimer is always present.
"""

from __future__ import annotations

import pytest

from backend.agents.faq_agent import MANDATORY_DISCLAIMER, faq_node


@pytest.mark.asyncio
async def test_faq_node_success(mock_groq) -> None:
    """Verify that general questions are answered and include the disclaimer."""
    state = {
        "message": "What is diabetes?",
        "correlation_id": "corr-faq",
        "session_id": "sess-faq",
        "history": [],
    }

    result = await faq_node(state)
    assert result.get("error") is None

    response = result["response"]
    assert response["intent"] == "faq"
    assert response["agent"] == "FAQAgent"
    assert MANDATORY_DISCLAIMER in response["answer"]
    assert response["data"]["disclaimer"] == MANDATORY_DISCLAIMER

"""
Healthcare AI Router — Reimbursement Agent Node Tests
=====================================================
Tests the reimbursement_node function in isolation.
Verifies coverage levels, timelines, and document requirements.
"""

from __future__ import annotations

import pytest

from backend.agents.reimbursement_agent import reimbursement_node


@pytest.mark.asyncio
async def test_reimbursement_node_success(mock_groq) -> None:
    """Verify document listing and envelope payload parsing."""
    state = {
        "message": "How do I submit surgery claims?",
        "correlation_id": "corr-reimb",
        "session_id": "sess-reimb",
        "history": [],
    }

    result = await reimbursement_node(state)
    assert result.get("error") is None

    response = result["response"]
    assert response["intent"] == "reimbursement"
    assert response["agent"] == "ReimbursementAgent"
    assert "Medical invoice" in response["data"]["required_documents"]
    assert response["data"]["coverage"] == "70% coverage"
    assert response["data"]["delay"] == "5 business days"

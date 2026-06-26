"""
Healthcare AI Router — API Endpoint Tests
=========================================
Tests all FastAPI route handlers, ensuring correlation IDs are correctly
generated and echoed, errors mapped to standard envelopes, and sessions persisted.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_chat_success(app_client: AsyncClient) -> None:
    """Verify that chat endpoint processes and returns the standard envelope."""
    payload = {
        "message": "I want to see a cardiologist in Paris next week.",
        "session_id": None,
    }

    response = await app_client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "correlation_id" in data
    assert "session_id" in data
    assert data["intent"] == "consultation"
    assert data["agent"] == "ConsultationAgent"
    assert "cardiologist" in data["answer"].lower()

    # Echo correlation ID header
    assert "X-Correlation-ID" in response.headers
    correlation_id = response.headers["X-Correlation-ID"]
    assert data["correlation_id"] == correlation_id


@pytest.mark.asyncio
async def test_api_feedback_submission(app_client: AsyncClient) -> None:
    """Verify that user feedback rating is successfully accepted."""
    payload = {
        "correlation_id": "test-correlation-id-999",
        "rating": 1,
        "comment": "Very helpful explanation!",
    }

    response = await app_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_api_health_check(app_client: AsyncClient) -> None:
    """Verify health endpoint probes MongoDB and Groq service connectivity."""
    response = await app_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "mongodb" in data["services"]
    assert "groq" in data["services"]
    assert data["services"]["mongodb"]["status"] == "healthy"
    assert data["services"]["groq"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_sessions_endpoints(app_client: AsyncClient) -> None:
    """Verify list, detail, and message history endpoints for sessions."""
    import uuid
    unique_session_id = f"session-api-test-{uuid.uuid4()}"
    # 1. Start a chat to auto-generate a session
    payload = {
        "message": "What is diabetes?",
        "session_id": unique_session_id,
    }
    chat_response = await app_client.post("/api/v1/chat", json=payload)
    assert chat_response.status_code == 200
    session_id = chat_response.json()["session_id"]

    # 2. List sessions
    list_response = await app_client.get("/api/v1/sessions")
    assert list_response.status_code == 200
    sessions = list_response.json()
    assert len(sessions) >= 1
    assert any(s["id"] == session_id for s in sessions)

    # 3. Retrieve session details
    detail_response = await app_client.get(f"/api/v1/sessions/{session_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == session_id
    assert detail["last_intent"] == "faq"

    # 4. Get message history logs
    history_response = await app_client.get(f"/api/v1/sessions/{session_id}/history")
    assert history_response.status_code == 200
    history = history_response.json()
    # Should contain 2 messages: 1 user, 1 assistant
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_api_monitoring_endpoints(app_client: AsyncClient) -> None:
    """Verify monitoring log listing and aggregate metrics retrieval."""
    # 1. Trigger executions to generate monitoring entries
    await app_client.post(
        "/api/v1/chat",
        json={"message": "What documents do I need to get reimbursed?", "session_id": "session-api-test-02"},
    )
    await app_client.post(
        "/api/v1/chat",
        json={"message": "My fever has not gone down.", "session_id": "session-api-test-02"},
    )

    # 2. Get monitoring logs
    logs_response = await app_client.get("/api/v1/monitoring")
    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert len(logs) >= 2

    # 3. Get metrics
    metrics_response = await app_client.get("/api/v1/monitoring/metrics")
    assert metrics_response.status_code == 200
    metrics = metrics_response.json()
    assert metrics["total_requests"] >= 2

    # 4. Get agent breakdown
    breakdown_response = await app_client.get("/api/v1/monitoring/agents")
    assert breakdown_response.status_code == 200
    breakdown = breakdown_response.json()
    assert len(breakdown) >= 1

"""
Healthcare AI Router — Database Repository Tests
=================================================
Tests all operations inside SessionRepository, MessageRepository,
and other repositories using an in-memory Motor client.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.database.repository import (
    FeedbackRepository,
    MessageRepository,
    MonitoringLogRepository,
    SessionRepository,
)
from backend.models.domain import MessageRole


@pytest.mark.asyncio
async def test_session_repository(mock_mongo_client) -> None:
    """Verify session creation, lookup, and atomic state updates."""
    db = mock_mongo_client["healthcare_ai_test"]
    repo = SessionRepository(db[SessionRepository.COLLECTION])

    session_id = "session-123"
    session_doc = {
        "id": session_id,
        "user_id": "user-456",
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
        "message_count": 0,
        "last_intent": None,
    }

    # 1. Create session
    inserted_id = await repo.create_session(session_doc)
    assert inserted_id is not None

    # 2. Get by ID
    loaded = await repo.get_by_id(session_id)
    assert loaded is not None
    assert loaded["user_id"] == "user-456"

    # 3. Increment message count
    await repo.increment_message_count(session_id)
    loaded = await repo.get_by_id(session_id)
    assert loaded["message_count"] == 1

    # 4. Update last intent
    await repo.update_last_intent(session_id, "faq")
    loaded = await repo.get_by_id(session_id)
    assert loaded["last_intent"] == "faq"

    # 5. List recent
    recent = await repo.list_recent(limit=10)
    assert len(recent) == 1
    assert recent[0]["id"] == session_id


@pytest.mark.asyncio
async def test_message_repository(mock_mongo_client) -> None:
    """Verify turn log saving, counting, and oldest-first history recovery."""
    db = mock_mongo_client["healthcare_ai_test"]
    repo = MessageRepository(db[MessageRepository.COLLECTION])

    session_id = "session-hist"
    msg1 = {
        "session_id": session_id,
        "role": MessageRole.USER.value,
        "content": "Hello",
        "timestamp": datetime(2026, 6, 26, 10, 0, 0, tzinfo=timezone.utc),
    }
    msg2 = {
        "session_id": session_id,
        "role": MessageRole.ASSISTANT.value,
        "content": "Hi there",
        "timestamp": datetime(2026, 6, 26, 10, 0, 5, tzinfo=timezone.utc),
    }

    # Save messages
    await repo.save_message(msg1)
    await repo.save_message(msg2)

    # Count
    cnt = await repo.count_session_messages(session_id)
    assert cnt == 2

    # Chronological history (oldest first)
    history = await repo.get_session_history(session_id)
    assert len(history) == 2
    assert history[0]["content"] == "Hello"
    assert history[1]["content"] == "Hi there"


@pytest.mark.asyncio
async def test_feedback_repository(mock_mongo_client) -> None:
    """Verify positive rating satisfaction calculations."""
    db = mock_mongo_client["healthcare_ai_test"]
    repo = FeedbackRepository(db[FeedbackRepository.COLLECTION])

    # Insert ratings: one positive, one negative
    await repo.upsert_feedback({"correlation_id": "corr-1", "rating": 1})
    await repo.upsert_feedback({"correlation_id": "corr-2", "rating": 0})

    rate = await repo.compute_satisfaction_rate()
    # 1 out of 2 is 0.50
    assert rate == 0.50


@pytest.mark.asyncio
async def test_monitoring_repository(mock_mongo_client) -> None:
    """Verify aggregation logic on telemetry logs."""
    db = mock_mongo_client["healthcare_ai_test"]
    repo = MonitoringLogRepository(db[MonitoringLogRepository.COLLECTION])

    log1 = {
        "correlation_id": "corr-a",
        "session_id": "sess-a",
        "timestamp": datetime.now(tz=timezone.utc),
        "selected_agent": "FAQAgent",
        "intent": "faq",
        "latency_ms": 100.0,
        "execution_time_ms": 100.0,
        "prompt_tokens": 5,
        "completion_tokens": 10,
        "total_tokens": 15,
        "status": "success",
    }
    log2 = {
        "correlation_id": "corr-b",
        "session_id": "sess-a",
        "timestamp": datetime.now(tz=timezone.utc),
        "selected_agent": "ConsultationAgent",
        "intent": "consultation",
        "latency_ms": 200.0,
        "execution_time_ms": 200.0,
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "status": "success",
    }

    await repo.insert_one(log1)
    await repo.insert_one(log2)

    # Aggregate
    agg = await repo.compute_aggregate_metrics()
    assert agg["total_requests"] == 2
    assert agg["avg_latency_ms"] == 150.0
    assert agg["total_tokens"] == 45

    # Breakdown
    breakdown = await repo.get_agent_breakdown()
    assert len(breakdown) == 2

"""
Healthcare AI Router — Domain Models
=====================================
Shared domain-level Python dataclasses / Pydantic models that represent
core business concepts used across multiple layers of the application.

These are NOT request/response schemas (those live in `schemas/`).
They are internal value objects used by agents, services, and repositories.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class IntentType(str, Enum):
    """The recognized healthcare intents the Router can classify."""

    CONSULTATION = "consultation"
    REIMBURSEMENT = "reimbursement"
    FOLLOWUP = "followup"
    FAQ = "faq"
    ERROR = "error"


class AgentName(str, Enum):
    """Canonical agent identifiers used in monitoring logs and responses."""

    ROUTER = "RouterAgent"
    CONSULTATION = "ConsultationAgent"
    REIMBURSEMENT = "ReimbursementAgent"
    FOLLOWUP = "FollowupAgent"
    FAQ = "FAQAgent"
    MONITORING = "MonitoringAgent"


class MessageRole(str, Enum):
    """Role of a chat message participant."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ExecutionStatus(str, Enum):
    """Final status of a graph execution."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


# =============================================================================
# Value Objects
# =============================================================================


class TokenUsage(BaseModel):
    """LLM token consumption for a single invocation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class ChatMessage(BaseModel):
    """A single turn in a conversation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    correlation_id: str | None = None
    intent: IntentType | None = None
    agent: AgentName | None = None
    token_usage: TokenUsage | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    """A conversation session."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    message_count: int = 0
    last_intent: IntentType | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> "Session":
        """Update the `updated_at` timestamp."""
        return self.model_copy(
            update={"updated_at": datetime.now(tz=timezone.utc)}
        )


class HealthStatus(str, Enum):
    """Aggregated health state of a service or the whole application."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Health status of a single downstream service."""

    name: str
    status: HealthStatus
    latency_ms: float | None = None
    error: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class SystemHealth(BaseModel):
    """Aggregated health report for the entire application."""

    status: HealthStatus
    version: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    services: dict[str, ServiceHealth] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)

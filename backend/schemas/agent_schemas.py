"""
Healthcare AI Router — Agent Response Schemas
=============================================
Pydantic models for all specialized agent outputs.

Design notes:
    - ``AgentResponse`` is the outer envelope returned by every agent node.
      The ``data`` field contains the agent-specific payload.
    - Each agent-specific data model (``ConsultationData``, etc.) is a
      separate Pydantic model so that Phase 4 can validate LLM structured
      outputs against them.
    - The ``disclaimer`` field is mandatory in ``FAQData`` and is hardcoded
      to the required legal text — agents cannot omit or alter it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Specialised agent data models
# ---------------------------------------------------------------------------


class ConsultationData(BaseModel):
    """
    Extracted fields from a Consultation Agent response.

    Attributes:
        patient_name:       Patient name extracted from the message.
        specialty:          Medical specialty requested.
        preferred_date:     Patient's preferred appointment date.
        city:               Patient's preferred city.
        doctor_preference:  Specific doctor name, or ``None`` if no preference.
        confirmation:       Natural-language confirmation message to show the user.
    """

    patient_name: str | None = Field(default=None, description="Patient name")
    specialty: str | None = Field(default=None, description="Medical specialty")
    preferred_date: str | None = Field(
        default=None, description="Preferred appointment date"
    )
    city: str | None = Field(default=None, description="Preferred city")
    doctor_preference: str | None = Field(
        default=None, description="Specific doctor preference"
    )
    confirmation: str = Field(..., description="Confirmation message for the user")


class ReimbursementData(BaseModel):
    """
    Structured reimbursement guidance from the Reimbursement Agent.

    Attributes:
        required_documents: List of documents the patient must submit.
        coverage:           Description of coverage level.
        delay:              Typical processing timeline.
        steps:              Ordered list of steps to complete reimbursement.
        answer:             Natural-language explanation for the user.
    """

    required_documents: list[str] = Field(
        default_factory=list, description="Documents required for reimbursement"
    )
    coverage: str = Field(..., description="Insurance coverage description")
    delay: str = Field(..., description="Processing timeline description")
    steps: list[str] = Field(
        default_factory=list, description="Step-by-step reimbursement process"
    )
    answer: str = Field(..., description="Natural-language response for the user")


class FollowupData(BaseModel):
    """
    Follow-up care guidance from the Follow-up Agent.

    Attributes:
        symptoms:              Symptoms identified in the patient's message.
        recommendations:       Care recommendations for the patient.
        requires_urgent_care:  ``True`` if symptoms indicate urgent attention.
        answer:                Natural-language guidance for the patient.
    """

    symptoms: list[str] = Field(
        default_factory=list, description="Symptoms identified in the message"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Care recommendations"
    )
    requires_urgent_care: bool = Field(
        default=False,
        description="True if symptoms require immediate medical attention",
    )
    answer: str = Field(..., description="Natural-language guidance for the patient")


class FAQData(BaseModel):
    """
    Medical FAQ response from the FAQ Agent.

    Attributes:
        answer:     Answer to the medical question.
        disclaimer: Mandatory legal disclaimer (always appended, never omitted).
    """

    answer: str = Field(..., description="Answer to the medical question")
    disclaimer: str = Field(
        default=(
            "This information does not replace professional medical advice. "
            "Always consult a qualified healthcare professional for diagnosis, "
            "treatment, and any health concerns specific to your situation."
        ),
        description="Mandatory medical disclaimer",
    )


class ErrorData(BaseModel):
    """Structured error payload returned by the error node."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")


# ---------------------------------------------------------------------------
# Outer response envelope
# ---------------------------------------------------------------------------


class AgentResponse(BaseModel):
    """
    Standardised response envelope produced by every specialized agent node.

    This is what the API layer reads from ``state["response"]`` and returns
    to the client (after serialisation to the wire format in routes.py).

    Attributes:
        correlation_id: Request correlation UUID.
        session_id:     Conversation session UUID.
        intent:         The classified intent.
        agent:          Name of the agent that produced this response.
        answer:         Main text answer to display to the user.
        data:           Agent-specific structured payload (optional).
        timestamp:      UTC time of response creation.
    """

    correlation_id: str = Field(..., description="Request correlation UUID")
    session_id: str = Field(..., description="Conversation session UUID")
    intent: str = Field(..., description="Classified intent")
    agent: str = Field(..., description="Agent that produced this response")
    answer: str = Field(..., description="Main answer text for the user")
    data: ConsultationData | ReimbursementData | FollowupData | FAQData | ErrorData | None = Field(
        default=None,
        description="Agent-specific structured payload",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC response creation time",
    )

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    def to_state_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for storage in ``GraphState["response"]``."""
        return self.model_dump(mode="json")

"""
Healthcare AI Router — Router Agent Schemas
============================================
Pydantic schemas for Router Node input and output.

The ``RouterOutput`` model enforces that:
    - ``intent`` is one of the four recognised healthcare intents.
    - ``confidence`` is a float strictly within [0.0, 1.0].

Any LLM response that fails validation raises a ``ValidationError``,
which the Router Node catches and converts to an ``IntentClassificationError``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RouterOutput(BaseModel):
    """
    Structured output returned by the Router Node after intent classification.

    This model is populated by parsing the LLM's JSON response.
    It is intentionally minimal — the Router classifies only, never answers.

    Attributes:
        intent:     One of the four recognised intents.
        confidence: Model's confidence score for the classification.
    """

    intent: Literal["consultation", "reimbursement", "followup", "faq"] = Field(
        ...,
        description="Classified intent for the user's message.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the classification (0.0 – 1.0).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"intent": "consultation", "confidence": 0.98},
                {"intent": "faq", "confidence": 0.95},
            ]
        }
    }

"""
Healthcare AI Router — pytest Configuration
===========================================
Defines fixtures and overrides to support running tests completely in-memory:
    - Overrides MongoDB connection to use ``mongomock_motor``
    - Overrides Groq service to use a dynamic mock implementation
    - Customizes test environment settings
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Generator
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

# Ensure test mode settings
os.environ["GROQ_API_KEY"] = "mock-groq-api-key-12345"
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["MONGO_DB_NAME"] = "healthcare_ai_test"

from backend.config import get_settings, Settings  # noqa: E402
from backend.models.domain import TokenUsage  # noqa: E402


# =============================================================================
# Mock Groq Service
# =============================================================================


class MockGroqService:
    """
    In-memory mock for GroqService that intercepts LLM calls and returns
    realistic JSON responses based on the system prompt context.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.should_fail_auth = False
        self.should_rate_limit = False
        self.should_timeout = False
        self.should_raise_generic = False

    async def invoke_with_retry(
        self,
        messages: list[Any],
        correlation_id: str = "",
    ) -> tuple[AIMessage, TokenUsage]:
        from backend.schemas.error_schema import (
            GroqUnavailableError,
            GroqRateLimitError,
            GroqTimeoutError,
        )

        if self.should_fail_auth:
            raise GroqUnavailableError("Groq authentication failed.")
        if self.should_rate_limit:
            raise GroqRateLimitError("Groq rate limit exceeded.")
        if self.should_timeout:
            raise GroqTimeoutError("Groq request timed out.")
        if self.should_raise_generic:
            raise RuntimeError("Generic Groq LLM failure.")

        # Extract message contents
        system_content = ""
        human_content = ""
        for msg in messages:
            if getattr(msg, "type", "") == "system":
                system_content = msg.content
            elif getattr(msg, "type", "") == "human":
                human_content = msg.content

        # 1. Router Agent prompt
        if "intent" in system_content or "classification" in system_content:
            intent = "faq"
            if any(k in human_content.lower() for k in ["book", "appointment", "cardiologist", "paris"]):
                intent = "consultation"
            elif any(k in human_content.lower() for k in ["reimburse", "documents", "surgery", "refund"]):
                intent = "reimbursement"
            elif any(k in human_content.lower() for k in ["fever", "days", "treatment", "followup", "follow-up"]):
                intent = "followup"

            content = f'{{"intent": "{intent}", "confidence": 0.95}}'

        # 2. Consultation Agent
        elif "patient_name" in system_content or "specialty" in system_content:
            content = (
                '{"patient_name": "John Doe", "specialty": "cardiologist", '
                '"preferred_date": "next week", "city": "Paris", '
                '"doctor_preference": null, "confirmation": "Your cardiologist consultation has been booked."}'
            )

        # 3. Reimbursement Agent
        elif "required_documents" in system_content or "coverage" in system_content:
            content = (
                '{"required_documents": ["Medical invoice", "Prescription"], '
                '"coverage": "70% coverage", "delay": "5 business days", '
                '"steps": ["Submit invoice", "Wait for approval"], '
                '"answer": "Reimbursement details generated."}'
            )

        # 4. Follow-up Agent
        elif "symptoms" in system_content or "requires_urgent_care" in system_content:
            is_urgent = any(k in human_content.lower() for k in ["fever", "pain", "3 days"])
            content = (
                f'{{"symptoms": ["fever"], "recommendations": ["Rest", "Hydrate"], '
                f'"requires_urgent_care": {str(is_urgent).lower()}, '
                f'"answer": "Followup care suggestions logged."}}'
            )

        # 5. FAQ Agent
        elif "FAQ" in system_content or "disclaimer" in system_content:
            content = (
                '{"answer": "Diabetes is defined by high blood sugar levels.", '
                '"disclaimer": "This information does not replace professional medical advice."}'
            )
        else:
            content = '{"answer": "Default mock response answer."}'

        ai_msg = AIMessage(content=content)
        ai_msg.usage_metadata = {
            "input_tokens": 15,
            "output_tokens": 25,
            "total_tokens": 40,
        }
        token_usage = TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
        return ai_msg, token_usage

    async def invoke_raw(self, messages: list[Any]) -> AIMessage:
        return AIMessage(content="pong")

    async def check_connectivity(self) -> tuple[bool, float]:
        if self.should_raise_generic:
            return False, -1.0
        return True, 12.5


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Return Settings configured for test execution."""
    return get_settings()


@pytest.fixture(autouse=True)
def mock_mongo_client() -> Generator[Any, None, None]:
    """
    Overriding AsyncIOMotorClient inside connection.py to use mongomock_motor.
    """
    from mongomock_motor import AsyncMongoMockClient
    from backend.database import connection

    mock_client = AsyncMongoMockClient()
    connection._client = mock_client
    connection._database = mock_client[get_settings().MONGO_DB_NAME]

    yield mock_client

    connection._client = None
    connection._database = None


@pytest.fixture
def mock_groq() -> Generator[MockGroqService, None, None]:
    """
    Mock GroqService globally and inject it into the dependency cache.
    """
    mock_service = MockGroqService()
    with patch("backend.services.groq_service._build_groq_service", return_value=mock_service):
        from backend.services.groq_service import _build_groq_service
        _build_groq_service.cache_clear()
        yield mock_service


@pytest.fixture
async def app_client(mock_groq) -> AsyncGenerator[Any, None]:
    """
    Provides an async HTTP client for testing API routes.
    """
    from httpx import AsyncClient, ASGITransport
    from backend.main import create_app
    from backend.database.connection import connect_mongo, close_mongo

    await connect_mongo()
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    await close_mongo()

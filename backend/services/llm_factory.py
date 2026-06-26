"""
Healthcare AI Router — LLM Factory / Provider Layer
====================================================
The ``LLMFactory`` is the single point of LLM instantiation in the system.
No agent or service should call ``ChatGroq()`` directly — all LLM creation
flows through this factory.

Benefits:
    - Centralises model configuration.
    - Enables provider switching (GROQ → OpenAI / Anthropic / Gemini) by
      changing a single environment variable and adding a branch here.
    - Makes the provider contract explicit via the ``LLMProvider`` enum.

Usage::

    from backend.services.llm_factory import LLMFactory, LLMProvider
    from backend.config import get_settings

    llm = LLMFactory.create(LLMProvider.GROQ, get_settings())
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq

from backend.config import Settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Provider enum
# ---------------------------------------------------------------------------


class LLMProvider(str, Enum):
    """Supported LLM backend providers."""

    GROQ = "groq"
    # Future providers can be added here:
    # OPENAI = "openai"
    # ANTHROPIC = "anthropic"
    # GEMINI = "gemini"


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LLMConfig:
    """
    Immutable configuration snapshot for an LLM instantiation.

    Decoupled from ``Settings`` so that individual agents can override
    specific parameters (e.g., temperature) without mutating global config.

    Attributes:
        provider:    Which LLM backend to use.
        model:       Model identifier string (provider-specific).
        temperature: Sampling temperature; lower = more deterministic.
        max_tokens:  Maximum completion tokens.
        timeout:     Request timeout in seconds.
        max_retries: Number of retries *at the SDK level* (set to 0 here
                     because ``GroqService`` handles retries with tenacity).
    """

    provider: LLMProvider = LLMProvider.GROQ
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 30
    max_retries: int = 0  # Delegated to GroqService / tenacity

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMConfig":
        """
        Construct an ``LLMConfig`` from application settings.

        Args:
            settings: The application ``Settings`` singleton.

        Returns:
            A populated ``LLMConfig`` instance.
        """
        return cls(
            provider=LLMProvider.GROQ,
            model=settings.GROQ_MODEL,
            temperature=settings.GROQ_TEMPERATURE,
            max_tokens=settings.GROQ_MAX_TOKENS,
            timeout=settings.GROQ_TIMEOUT,
            max_retries=0,  # Always 0 — retries are handled by GroqService
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class LLMFactory:
    """
    Static factory for creating ``BaseChatModel`` instances.

    All construction logic is encapsulated here, keeping agents and
    services free of instantiation details.
    """

    @staticmethod
    def create(provider: LLMProvider, settings: Settings) -> BaseChatModel:
        """
        Create and return a configured ``BaseChatModel`` for the given provider.

        Args:
            provider: The LLM backend to instantiate.
            settings: Application settings containing API keys and model config.

        Returns:
            A configured ``BaseChatModel`` subclass ready for invocation.

        Raises:
            ValueError: If ``provider`` is not supported.
            ImportError: If the required provider package is not installed.
        """
        config = LLMConfig.from_settings(settings)

        if provider == LLMProvider.GROQ:
            return LLMFactory._create_groq(config, settings)

        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Supported providers: {[p.value for p in LLMProvider]}"
        )

    @staticmethod
    def create_with_config(config: LLMConfig, settings: Settings) -> BaseChatModel:
        """
        Create an LLM from an explicit ``LLMConfig`` instance.

        Use this when an agent needs to override specific parameters
        (e.g., a lower temperature for structured JSON output).

        Args:
            config:   The explicit configuration to use.
            settings: Application settings (for API keys).

        Returns:
            A configured ``BaseChatModel`` subclass.

        Raises:
            ValueError: If the provider in ``config`` is not supported.
        """
        if config.provider == LLMProvider.GROQ:
            return LLMFactory._create_groq(config, settings)

        raise ValueError(f"Unsupported LLM provider: '{config.provider}'")

    # -------------------------------------------------------------------------
    # Private builder methods per provider
    # -------------------------------------------------------------------------

    @staticmethod
    def _create_groq(config: LLMConfig, settings: Settings) -> ChatGroq:
        """
        Instantiate a ``ChatGroq`` model with the given configuration.

        Args:
            config:   LLM configuration parameters.
            settings: Application settings containing the Groq API key.

        Returns:
            A configured ``ChatGroq`` instance.
        """
        logger.debug(
            "Creating Groq LLM instance",
            extra={
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            },
        )

        return ChatGroq(
            api_key=settings.GROQ_API_KEY,  # type: ignore[arg-type]
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

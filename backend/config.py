"""
Healthcare AI Router — Application Configuration
================================================
Uses pydantic-settings to validate ALL environment variables at startup.
The application will fail fast with a descriptive error if any required
variable is absent or malformed.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration object.

    All values are read from environment variables (or a .env file).
    Required fields without defaults will raise a ValidationError on startup
    if they are not supplied — this is intentional fail-fast behaviour.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "Healthcare AI Router"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "LangGraph-powered multi-agent healthcare assistant "
        "with Router Pattern architecture."
    )
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )
    REQUEST_TIMEOUT_SECONDS: int = 60

    # ── Groq LLM ──────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(..., description="Groq API key — required")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0)
    GROQ_MAX_TOKENS: int = Field(default=2048, ge=1)
    GROQ_TIMEOUT: int = Field(default=30, ge=1)
    GROQ_MAX_RETRIES: int = Field(default=3, ge=0, le=10)
    GROQ_BASE_DELAY: float = Field(default=1.0, ge=0.0)
    GROQ_MAX_DELAY: float = Field(default=30.0, ge=0.0)

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "healthcare_ai"
    MONGO_MAX_POOL_SIZE: int = Field(default=10, ge=1)
    MONGO_MIN_POOL_SIZE: int = Field(default=2, ge=0)
    MONGO_CONNECTION_TIMEOUT_MS: int = Field(default=5000, ge=100)
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = Field(default=5000, ge=100)

    # ── LangSmith ─────────────────────────────────────────────────────────────
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "healthcare-ai-router"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # ── Prompts ───────────────────────────────────────────────────────────────
    PROMPTS_DIR: str = Field(
        default="",
        description=(
            "Absolute path to the prompts directory. "
            "Defaults to backend/prompts/ relative to this file."
        ),
    )

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="Secret key used for internal token signing",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Validators
    # ─────────────────────────────────────────────────────────────────────────

    @field_validator("GROQ_API_KEY", mode="before")
    @classmethod
    def validate_groq_key(cls, v: Any) -> str:
        """Fail fast if the Groq API key is missing or empty."""
        if not v or not str(v).strip():
            raise ValueError(
                "GROQ_API_KEY is required and must not be empty. "
                "Set it in your .env file or as an environment variable."
            )
        return str(v).strip()

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        value = str(v).upper()
        if value not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return value

    @model_validator(mode="after")
    def validate_langsmith(self) -> "Settings":
        """Warn (but do not fail) if tracing is enabled without an API key."""
        if self.LANGCHAIN_TRACING_V2 and not self.LANGCHAIN_API_KEY:
            import warnings

            warnings.warn(
                "LANGCHAIN_TRACING_V2=true but LANGCHAIN_API_KEY is not set. "
                "LangSmith tracing will be disabled.",
                UserWarning,
                stacklevel=2,
            )
            # Disable tracing to prevent runtime errors
            object.__setattr__(self, "LANGCHAIN_TRACING_V2", False)
        return self

    @model_validator(mode="after")
    def resolve_prompts_dir(self) -> "Settings":
        """Resolve the prompts directory path relative to this file."""
        if not self.PROMPTS_DIR:
            base = os.path.dirname(os.path.abspath(__file__))
            object.__setattr__(self, "PROMPTS_DIR", os.path.join(base, "prompts"))
        return self

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def is_langsmith_enabled(self) -> bool:
        """Return True only when both the flag and API key are present."""
        return self.LANGCHAIN_TRACING_V2 and bool(self.LANGCHAIN_API_KEY)

    def get_mongo_options(self) -> dict[str, Any]:
        """Return Motor-compatible connection kwargs."""
        return {
            "maxPoolSize": self.MONGO_MAX_POOL_SIZE,
            "minPoolSize": self.MONGO_MIN_POOL_SIZE,
            "connectTimeoutMS": self.MONGO_CONNECTION_TIMEOUT_MS,
            "serverSelectionTimeoutMS": self.MONGO_SERVER_SELECTION_TIMEOUT_MS,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Using @lru_cache ensures that the .env file is parsed exactly once
    at startup, and the same Settings object is reused everywhere.
    """
    return Settings()  # type: ignore[call-arg]

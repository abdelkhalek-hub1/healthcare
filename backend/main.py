"""
Healthcare AI Router — FastAPI Application Entry Point
======================================================
Bootstraps the FastAPI application with:
  - Structured JSON logging
  - CORS configuration
  - Middleware stack (Correlation ID → Timing → Logging → Exception Handler)
  - MongoDB connection lifecycle (startup/shutdown)
  - API router registration
  - OpenAPI / Swagger UI customization
  - Application-level health probe
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.utils.logger import configure_logging, get_logger

# ── Bootstrap logging before any other import that might log ──────────────────
settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

# Import database after logging is configured
from backend.database.connection import close_mongo, connect_mongo  # noqa: E402

# ── Application startup time (used for uptime calculation) ───────────────────
APP_START_TIME: float = time.monotonic()


# =============================================================================
# Lifespan — startup / shutdown events
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan events.

    Startup:
      1. Validate configuration (already done via pydantic-settings import)
      2. Connect to MongoDB and ensure indexes
      3. Warm up the LangGraph router graph

    Shutdown:
      1. Close MongoDB connection pool
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info(
        "Starting Healthcare AI Router",
        extra={
            "version": settings.APP_VERSION,
            "groq_model": settings.GROQ_MODEL,
            "mongo_db": settings.MONGO_DB_NAME,
            "langsmith_enabled": settings.is_langsmith_enabled(),
        },
    )

    await connect_mongo()
    logger.info("MongoDB connection established")

    # Configure LangSmith tracing environment variables if enabled
    if settings.is_langsmith_enabled():
        import os

        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY  # type: ignore[arg-type]
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
        logger.info(
            "LangSmith tracing enabled",
            extra={"project": settings.LANGCHAIN_PROJECT},
        )

    logger.info("Application startup complete — ready to serve requests")

    yield  # ── Application running ──────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down Healthcare AI Router")
    await close_mongo()
    logger.info("MongoDB connection closed — shutdown complete")


# =============================================================================
# FastAPI application factory
# =============================================================================


def create_app() -> FastAPI:
    """
    Construct and configure the FastAPI application instance.

    Separated into a factory function to facilitate testing
    (tests can call `create_app()` directly without importing `app`).
    """
    _app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Process-Time"],
    )

    # ── Custom middleware stack ───────────────────────────────────────────────
    # Import here to avoid circular imports during test collection
    from backend.middleware.correlation import CorrelationMiddleware
    from backend.middleware.exception_handler import ExceptionHandlerMiddleware
    from backend.middleware.logging_mw import LoggingMiddleware
    from backend.middleware.timing import TimingMiddleware

    # Order matters: added last = executes first (LIFO for Starlette middleware)
    _app.add_middleware(ExceptionHandlerMiddleware)
    _app.add_middleware(LoggingMiddleware)
    _app.add_middleware(TimingMiddleware)
    _app.add_middleware(CorrelationMiddleware)

    # ── API routes ────────────────────────────────────────────────────────────
    from backend.api.routes import router as api_router

    _app.include_router(api_router, prefix=settings.API_PREFIX)

    # ── Root endpoint (useful for load-balancer probes) ───────────────────────
    @_app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            {
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "status": "running",
                "docs": "/docs",
            }
        )

    return _app


# =============================================================================
# Application instance (used by uvicorn and tests)
# =============================================================================

app: FastAPI = create_app()

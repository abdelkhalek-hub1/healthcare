"""
Healthcare AI Router — MongoDB Connection Manager
=================================================
Manages the Motor async client lifecycle and database index creation.

Design decisions:
    - Module-level client stored in private variables, exposed only through
      the ``get_database()`` dependency function. This avoids globals leaking
      into application code while keeping Motor's recommended pattern of a
      single shared client per process.
    - Index creation is idempotent — safe to re-run on every startup.
    - Connection parameters are sourced exclusively from ``Settings`` to
      honour the single-source-of-truth principle.

Typical usage (via FastAPI dependency injection)::

    from backend.database.connection import get_database
    from motor.motor_asyncio import AsyncIOMotorDatabase

    async def my_endpoint(db: AsyncIOMotorDatabase = Depends(get_database)):
        ...
"""

from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from backend.config import Settings, get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level client storage (private — do not import these directly)
# ---------------------------------------------------------------------------
_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
_database: AsyncIOMotorDatabase | None = None  # type: ignore[type-arg]

# ---------------------------------------------------------------------------
# Index definitions per collection
# ---------------------------------------------------------------------------
_COLLECTION_INDEXES: dict[str, list[IndexModel]] = {
    "users": [
        IndexModel([("id", ASCENDING)], unique=True, name="idx_users_id"),
        IndexModel([("email", ASCENDING)], sparse=True, name="idx_users_email"),
    ],
    "sessions": [
        IndexModel([("id", ASCENDING)], unique=True, name="idx_sessions_id"),
        IndexModel([("user_id", ASCENDING)], sparse=True, name="idx_sessions_user_id"),
        IndexModel([("created_at", DESCENDING)], name="idx_sessions_created_at"),
    ],
    "messages": [
        IndexModel([("session_id", ASCENDING)], name="idx_messages_session_id"),
        IndexModel([("correlation_id", ASCENDING)], sparse=True, name="idx_messages_correlation_id"),
        IndexModel(
            [("session_id", ASCENDING), ("timestamp", ASCENDING)],
            name="idx_messages_session_timestamp",
        ),
    ],
    "consultations": [
        IndexModel([("session_id", ASCENDING)], name="idx_consultations_session_id"),
        IndexModel([("correlation_id", ASCENDING)], unique=True, name="idx_consultations_correlation_id"),
        IndexModel([("created_at", DESCENDING)], name="idx_consultations_created_at"),
    ],
    "reimbursements": [
        IndexModel([("session_id", ASCENDING)], name="idx_reimbursements_session_id"),
        IndexModel([("correlation_id", ASCENDING)], unique=True, name="idx_reimbursements_correlation_id"),
        IndexModel([("created_at", DESCENDING)], name="idx_reimbursements_created_at"),
    ],
    "followups": [
        IndexModel([("session_id", ASCENDING)], name="idx_followups_session_id"),
        IndexModel([("correlation_id", ASCENDING)], unique=True, name="idx_followups_correlation_id"),
        IndexModel([("created_at", DESCENDING)], name="idx_followups_created_at"),
    ],
    "faq_logs": [
        IndexModel([("session_id", ASCENDING)], name="idx_faq_logs_session_id"),
        IndexModel([("correlation_id", ASCENDING)], unique=True, name="idx_faq_logs_correlation_id"),
        IndexModel([("created_at", DESCENDING)], name="idx_faq_logs_created_at"),
    ],
    "monitoring_logs": [
        IndexModel([("correlation_id", ASCENDING)], unique=True, name="idx_monitoring_correlation_id"),
        IndexModel([("session_id", ASCENDING)], name="idx_monitoring_session_id"),
        IndexModel([("timestamp", DESCENDING)], name="idx_monitoring_timestamp"),
        IndexModel([("selected_agent", ASCENDING)], name="idx_monitoring_agent"),
        IndexModel([("status", ASCENDING)], name="idx_monitoring_status"),
    ],
    "feedback": [
        IndexModel([("correlation_id", ASCENDING)], name="idx_feedback_correlation_id"),
        IndexModel([("session_id", ASCENDING)], name="idx_feedback_session_id"),
        IndexModel([("created_at", DESCENDING)], name="idx_feedback_created_at"),
    ],
    "metrics": [
        IndexModel([("date", ASCENDING)], unique=True, sparse=True, name="idx_metrics_date"),
        IndexModel([("timestamp", DESCENDING)], name="idx_metrics_timestamp"),
    ],
}


# ---------------------------------------------------------------------------
# Lifecycle functions (called from main.py lifespan)
# ---------------------------------------------------------------------------


async def connect_mongo(settings: Settings | None = None) -> None:
    """
    Initialize the Motor async client and create database indexes.

    Args:
        settings: Application settings. Uses the global singleton if not provided.

    Raises:
        RuntimeError: If the connection cannot be established within the
            server selection timeout.
    """
    global _client, _database

    cfg = settings or get_settings()

    logger.info(
        "Connecting to MongoDB",
        extra={
            "uri_prefix": cfg.MONGO_URI[:20] + "...",
            "database": cfg.MONGO_DB_NAME,
        },
    )

    _client = AsyncIOMotorClient(
        cfg.MONGO_URI,
        **cfg.get_mongo_options(),
    )

    # Force a real connection attempt — raises if unreachable
    await _client.admin.command("ping")

    _database = _client[cfg.MONGO_DB_NAME]

    # Create indexes in the background — failures are logged but non-fatal
    asyncio.create_task(_create_indexes(_database))

    logger.info(
        "MongoDB connected successfully",
        extra={"database": cfg.MONGO_DB_NAME},
    )


async def close_mongo() -> None:
    """
    Close the Motor client and release connection pool resources.

    Safe to call even if ``connect_mongo`` was never called.
    """
    global _client, _database

    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


# ---------------------------------------------------------------------------
# Dependency function
# ---------------------------------------------------------------------------


def get_database() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """
    Return the active Motor database instance.

    Intended for use as a FastAPI dependency::

        async def endpoint(db = Depends(get_database)):
            ...

    Raises:
        RuntimeError: If called before ``connect_mongo()`` has been awaited.
    """
    if _database is None:
        raise RuntimeError(
            "MongoDB database is not initialized. "
            "Ensure 'connect_mongo()' is called during application startup."
        )
    return _database


async def check_mongo_health() -> tuple[bool, float]:
    """
    Perform a lightweight ping to verify MongoDB connectivity.

    Returns:
        A tuple of (is_healthy: bool, latency_ms: float).
        latency_ms is -1.0 when the check fails.
    """
    import time

    if _client is None:
        return False, -1.0

    start = time.monotonic()
    try:
        await asyncio.wait_for(
            _client.admin.command("ping"),
            timeout=3.0,
        )
        return True, (time.monotonic() - start) * 1000
    except Exception as exc:
        logger.warning("MongoDB health check failed", extra={"error": str(exc)})
        return False, -1.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
    """
    Create all defined indexes across all collections.

    Idempotent: MongoDB ignores requests to create an existing index
    with the same definition. Only logs a warning on unexpected errors.
    """
    for collection_name, index_models in _COLLECTION_INDEXES.items():
        try:
            collection = db[collection_name]
            await collection.create_indexes(index_models)
            logger.debug(
                "Indexes ensured",
                extra={
                    "collection": collection_name,
                    "count": len(index_models),
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to create indexes for collection",
                extra={
                    "collection": collection_name,
                    "error": str(exc),
                },
            )

    logger.info("All MongoDB indexes ensured", extra={"collections": len(_COLLECTION_INDEXES)})

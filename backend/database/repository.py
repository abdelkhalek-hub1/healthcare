"""
Healthcare AI Router — Repository Layer
========================================
Provides typed, async-first data access objects for every MongoDB collection.

Architecture:
    - ``BaseRepository`` encapsulates all raw Motor operations.
    - Specific repositories extend ``BaseRepository`` and add domain-specific
      query methods relevant to their collection.
    - Every repository is injected via FastAPI's ``Depends`` — no global state.
    - Documents are serialised to / from plain Python dicts. Domain model
      conversion is the responsibility of the calling service or agent.

MongoDB ``_id`` handling:
    - Insertions accept documents without ``_id``; MongoDB auto-generates it.
    - The returned ``inserted_id`` (ObjectId) is converted to a ``str``.
    - Find operations strip ``_id`` from results to avoid Pydantic issues.

Usage::

    from backend.database.repository import get_monitoring_repository

    async def my_handler(repo = Depends(get_monitoring_repository)):
        await repo.insert_log({...})
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import DESCENDING

from backend.database.connection import get_database
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _strip_mongo_id(document: dict[str, Any]) -> dict[str, Any]:
    """Remove the MongoDB ``_id`` field from a document dict."""
    document.pop("_id", None)
    return document


def _now_utc() -> datetime:
    """Return the current UTC datetime with timezone info."""
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Base Repository
# ---------------------------------------------------------------------------


class BaseRepository:
    """
    Generic async repository providing standard CRUD operations.

    All methods are coroutines and should be awaited. Motor operations
    are fully non-blocking on the asyncio event loop.

    Args:
        collection: The Motor ``AsyncIOMotorCollection`` to operate on.
    """

    def __init__(self, collection: AsyncIOMotorCollection) -> None:  # type: ignore[type-arg]
        self._collection = collection

    async def find_one(
        self,
        filter_: dict[str, Any],
        projection: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Find the first document matching ``filter_``.

        Args:
            filter_:    MongoDB query filter.
            projection: Optional field projection.

        Returns:
            The matching document as a dict, or ``None`` if not found.
        """
        doc = await self._collection.find_one(filter_, projection)
        if doc is None:
            return None
        return _strip_mongo_id(dict(doc))

    async def find_many(
        self,
        filter_: dict[str, Any],
        limit: int = 50,
        skip: int = 0,
        sort_field: str = "created_at",
        sort_order: int = DESCENDING,
    ) -> list[dict[str, Any]]:
        """
        Find all documents matching ``filter_``, with pagination and sorting.

        Args:
            filter_:     MongoDB query filter.
            limit:       Maximum documents to return (capped at 200).
            skip:        Number of documents to skip (for pagination).
            sort_field:  Field to sort by.
            sort_order:  ``pymongo.ASCENDING`` or ``pymongo.DESCENDING``.

        Returns:
            A list of matching documents as dicts.
        """
        effective_limit = min(limit, 200)
        cursor = (
            self._collection.find(filter_)
            .sort(sort_field, sort_order)
            .skip(skip)
            .limit(effective_limit)
        )
        results = await cursor.to_list(length=effective_limit)
        return [_strip_mongo_id(dict(doc)) for doc in results]

    async def insert_one(self, document: dict[str, Any]) -> str:
        """
        Insert a single document and return the inserted ID.

        Automatically injects ``created_at`` if the document does not
        already have one.

        Args:
            document: The document to insert (without ``_id``).

        Returns:
            The string representation of the inserted MongoDB ``_id``.
        """
        if "created_at" not in document:
            document["created_at"] = _now_utc()

        result = await self._collection.insert_one(document)
        return str(result.inserted_id)

    async def update_one(
        self,
        filter_: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> bool:
        """
        Update the first document matching ``filter_``.

        Args:
            filter_: MongoDB query filter.
            update:  MongoDB update document (e.g. ``{"$set": {...}}``).
            upsert:  If ``True``, insert the document if it doesn't exist.

        Returns:
            ``True`` if a document was modified or upserted, ``False`` otherwise.
        """
        result = await self._collection.update_one(filter_, update, upsert=upsert)
        return result.modified_count > 0 or result.upserted_id is not None

    async def delete_one(self, filter_: dict[str, Any]) -> bool:
        """
        Delete the first document matching ``filter_``.

        Args:
            filter_: MongoDB query filter.

        Returns:
            ``True`` if a document was deleted, ``False`` otherwise.
        """
        result = await self._collection.delete_one(filter_)
        return result.deleted_count > 0

    async def count(self, filter_: dict[str, Any] | None = None) -> int:
        """
        Count documents in the collection matching ``filter_``.

        Args:
            filter_: MongoDB query filter. Counts all documents if ``None``.

        Returns:
            Integer document count.
        """
        return await self._collection.count_documents(filter_ or {})

    async def aggregate(
        self,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Execute a MongoDB aggregation pipeline.

        Args:
            pipeline: List of aggregation stage documents.

        Returns:
            List of result documents.
        """
        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        return [_strip_mongo_id(dict(doc)) for doc in results]


# ---------------------------------------------------------------------------
# Session Repository
# ---------------------------------------------------------------------------


class SessionRepository(BaseRepository):
    """
    Repository for the ``sessions`` collection.

    Stores conversation session metadata: ID, user, timestamps,
    message count, and last intent.
    """

    COLLECTION = "sessions"

    async def get_by_id(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve a session document by its logical session ID.

        Args:
            session_id: The UUID session identifier.

        Returns:
            The session document or ``None``.
        """
        return await self.find_one({"id": session_id})

    async def create_session(self, session_data: dict[str, Any]) -> str:
        """
        Insert a new session document.

        Args:
            session_data: Session fields (must include ``id``).

        Returns:
            Inserted MongoDB ``_id`` as a string.
        """
        return await self.insert_one(session_data)

    async def increment_message_count(self, session_id: str) -> None:
        """
        Atomically increment the message counter for a session.

        Args:
            session_id: The UUID session identifier.
        """
        await self.update_one(
            {"id": session_id},
            {
                "$inc": {"message_count": 1},
                "$set": {"updated_at": _now_utc()},
            },
        )

    async def update_last_intent(self, session_id: str, intent: str) -> None:
        """
        Update the ``last_intent`` field on a session.

        Args:
            session_id: The UUID session identifier.
            intent:     The classified intent string.
        """
        await self.update_one(
            {"id": session_id},
            {"$set": {"last_intent": intent, "updated_at": _now_utc()}},
        )

    async def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Return the most recently active sessions.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of session documents sorted by ``updated_at`` descending.
        """
        return await self.find_many({}, limit=limit, sort_field="updated_at")


# ---------------------------------------------------------------------------
# Message Repository
# ---------------------------------------------------------------------------


class MessageRepository(BaseRepository):
    """
    Repository for the ``messages`` collection.

    Each document represents one turn in a conversation (user or assistant).
    """

    COLLECTION = "messages"

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most recent messages for a session, oldest-first.

        Args:
            session_id: The session UUID.
            limit:      Maximum number of messages to return.

        Returns:
            List of message documents in chronological order.
        """
        messages = await self.find_many(
            {"session_id": session_id},
            limit=limit,
            sort_field="timestamp",
            sort_order=DESCENDING,
        )
        # Reverse so oldest is first (chronological order for LLM context)
        return list(reversed(messages))

    async def save_message(self, message_data: dict[str, Any]) -> str:
        """
        Persist a single conversation message.

        Args:
            message_data: Message fields including ``session_id``, ``role``,
                ``content``, and ``timestamp``.

        Returns:
            Inserted MongoDB ``_id`` as a string.
        """
        return await self.insert_one(message_data)

    async def count_session_messages(self, session_id: str) -> int:
        """
        Count the total number of messages in a session.

        Args:
            session_id: The session UUID.

        Returns:
            Integer message count.
        """
        return await self.count({"session_id": session_id})


# ---------------------------------------------------------------------------
# Consultation Repository
# ---------------------------------------------------------------------------


class ConsultationRepository(BaseRepository):
    """Repository for the ``consultations`` collection."""

    COLLECTION = "consultations"

    async def get_by_correlation_id(
        self, correlation_id: str
    ) -> dict[str, Any] | None:
        """
        Find a consultation record by its correlation ID.

        Args:
            correlation_id: The request correlation UUID.

        Returns:
            The consultation document or ``None``.
        """
        return await self.find_one({"correlation_id": correlation_id})

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """
        Return all consultations for a session.

        Args:
            session_id: The session UUID.

        Returns:
            List of consultation documents.
        """
        return await self.find_many({"session_id": session_id})


# ---------------------------------------------------------------------------
# Reimbursement Repository
# ---------------------------------------------------------------------------


class ReimbursementRepository(BaseRepository):
    """Repository for the ``reimbursements`` collection."""

    COLLECTION = "reimbursements"

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """
        Return all reimbursement interactions for a session.

        Args:
            session_id: The session UUID.

        Returns:
            List of reimbursement documents.
        """
        return await self.find_many({"session_id": session_id})


# ---------------------------------------------------------------------------
# Followup Repository
# ---------------------------------------------------------------------------


class FollowupRepository(BaseRepository):
    """Repository for the ``followups`` collection."""

    COLLECTION = "followups"

    async def get_urgent_cases(self) -> list[dict[str, Any]]:
        """
        Return all follow-up records where urgent care is required.

        Returns:
            List of follow-up documents with ``requires_urgent_care=True``.
        """
        return await self.find_many(
            {"requires_urgent_care": True},
            limit=50,
            sort_field="created_at",
        )

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """
        Return all follow-ups for a session.

        Args:
            session_id: The session UUID.

        Returns:
            List of follow-up documents.
        """
        return await self.find_many({"session_id": session_id})


# ---------------------------------------------------------------------------
# FAQ Log Repository
# ---------------------------------------------------------------------------


class FAQLogRepository(BaseRepository):
    """Repository for the ``faq_logs`` collection."""

    COLLECTION = "faq_logs"

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """
        Return all FAQ interactions for a session.

        Args:
            session_id: The session UUID.

        Returns:
            List of FAQ log documents.
        """
        return await self.find_many({"session_id": session_id})


# ---------------------------------------------------------------------------
# Monitoring Log Repository
# ---------------------------------------------------------------------------


class MonitoringLogRepository(BaseRepository):
    """
    Repository for the ``monitoring_logs`` collection.

    Every LangGraph execution produces one monitoring log entry
    containing telemetry (latency, token usage, agent, status, etc.).
    """

    COLLECTION = "monitoring_logs"

    async def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Return the most recent monitoring log entries.

        Args:
            limit: Maximum entries to return.

        Returns:
            List of monitoring log documents sorted by timestamp descending.
        """
        return await self.find_many({}, limit=limit, sort_field="timestamp")

    async def get_by_correlation_id(
        self, correlation_id: str
    ) -> dict[str, Any] | None:
        """
        Find a monitoring log by correlation ID.

        Args:
            correlation_id: The request correlation UUID.

        Returns:
            The monitoring log document or ``None``.
        """
        return await self.find_one({"correlation_id": correlation_id})

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """
        Return all monitoring logs for a session.

        Args:
            session_id: The session UUID.

        Returns:
            List of monitoring log documents.
        """
        return await self.find_many(
            {"session_id": session_id},
            limit=100,
            sort_field="timestamp",
        )

    async def compute_aggregate_metrics(self) -> dict[str, Any]:
        """
        Compute aggregated system metrics from monitoring logs.

        Runs a MongoDB aggregation pipeline to calculate:
            - Total request count
            - Success/error counts
            - Average latency
            - Per-agent request breakdown

        Returns:
            Dictionary with aggregated metric values.
        """
        pipeline: list[dict[str, Any]] = [
            {
                "$group": {
                    "_id": None,
                    "total_requests": {"$sum": 1},
                    "success_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                    },
                    "error_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "error"]}, 1, 0]}
                    },
                    "avg_latency_ms": {"$avg": "$latency_ms"},
                    "total_tokens": {"$sum": "$total_tokens"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "total_requests": 1,
                    "success_count": 1,
                    "error_count": 1,
                    "avg_latency_ms": 1,
                    "total_tokens": 1,
                    "success_rate": {
                        "$cond": [
                            {"$eq": ["$total_requests", 0]},
                            0,
                            {
                                "$divide": [
                                    "$success_count",
                                    "$total_requests",
                                ]
                            },
                        ]
                    },
                }
            },
        ]
        results = await self.aggregate(pipeline)
        if not results:
            return {
                "total_requests": 0,
                "success_count": 0,
                "error_count": 0,
                "avg_latency_ms": 0.0,
                "total_tokens": 0,
                "success_rate": 0.0,
            }
        res = results[0]
        res["avg_latency_ms"] = round(res.get("avg_latency_ms") or 0.0, 2)
        res["success_rate"] = round(res.get("success_rate") or 0.0, 4)
        return res

    async def get_agent_breakdown(self) -> list[dict[str, Any]]:
        """
        Return per-agent request counts and average latency.

        Returns:
            List of dicts with ``agent``, ``count``, and ``avg_latency_ms``.
        """
        pipeline: list[dict[str, Any]] = [
            {
                "$group": {
                    "_id": "$selected_agent",
                    "count": {"$sum": 1},
                    "avg_latency_ms": {"$avg": "$latency_ms"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "agent": "$_id",
                    "count": 1,
                    "avg_latency_ms": 1,
                }
            },
            {"$sort": {"count": DESCENDING}},
        ]
        results = await self.aggregate(pipeline)
        for r in results:
            r["avg_latency_ms"] = round(r.get("avg_latency_ms") or 0.0, 2)
        return results


# ---------------------------------------------------------------------------
# Feedback Repository
# ---------------------------------------------------------------------------


class FeedbackRepository(BaseRepository):
    """
    Repository for the ``feedback`` collection.

    Stores user ratings (thumbs up/down) and optional comments per response.
    """

    COLLECTION = "feedback"

    async def get_by_correlation_id(
        self, correlation_id: str
    ) -> dict[str, Any] | None:
        """
        Find feedback for a specific AI response.

        Args:
            correlation_id: The correlation ID of the rated response.

        Returns:
            The feedback document or ``None``.
        """
        return await self.find_one({"correlation_id": correlation_id})

    async def upsert_feedback(self, feedback_data: dict[str, Any]) -> bool:
        """
        Insert or update feedback for a given correlation ID.

        Args:
            feedback_data: Feedback fields including ``correlation_id``,
                ``rating``, and optional ``comment``.

        Returns:
            ``True`` if the document was written successfully.
        """
        correlation_id = feedback_data.get("correlation_id")
        return await self.update_one(
            {"correlation_id": correlation_id},
            {
                "$set": {
                    **feedback_data,
                    "updated_at": _now_utc(),
                },
                "$setOnInsert": {"created_at": _now_utc()},
            },
            upsert=True,
        )

    async def compute_satisfaction_rate(self) -> float:
        """
        Compute the overall positive feedback rate.

        Returns:
            A float in ``[0.0, 1.0]`` representing the proportion of
            thumbs-up ratings (rating == 1) across all feedback documents.
        """
        pipeline: list[dict[str, Any]] = [
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "positive": {
                        "$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "rate": {
                        "$cond": [
                            {"$eq": ["$total", 0]},
                            0.0,
                            {"$divide": ["$positive", "$total"]},
                        ]
                    },
                }
            },
        ]
        results = await self.aggregate(pipeline)
        return results[0]["rate"] if results else 0.0


# ---------------------------------------------------------------------------
# Metrics Repository
# ---------------------------------------------------------------------------


class MetricsRepository(BaseRepository):
    """
    Repository for the ``metrics`` collection.

    Stores pre-aggregated daily metrics snapshots for fast dashboard reads.
    """

    COLLECTION = "metrics"

    async def upsert_daily_metrics(
        self,
        date: str,
        metrics_data: dict[str, Any],
    ) -> bool:
        """
        Upsert the aggregated metrics document for a given date.

        Args:
            date:         Date string in ``YYYY-MM-DD`` format.
            metrics_data: Metric values to store/update.

        Returns:
            ``True`` if the document was written.
        """
        return await self.update_one(
            {"date": date},
            {
                "$set": {
                    **metrics_data,
                    "date": date,
                    "updated_at": _now_utc(),
                },
                "$setOnInsert": {"created_at": _now_utc()},
            },
            upsert=True,
        )

    async def get_latest(self) -> dict[str, Any] | None:
        """
        Return the most recent daily metrics document.

        Returns:
            The latest metrics document or ``None``.
        """
        results = await self.find_many({}, limit=1, sort_field="date")
        return results[0] if results else None


# ===========================================================================
# Dependency injection functions
# ===========================================================================
# Each function creates a repository instance from the injected database.
# FastAPI resolves these via Depends(). Motor is thread-safe and connection-
# pool-backed, so creating a new repository object per request is very cheap.


def get_session_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> SessionRepository:
    """FastAPI dependency — returns a ``SessionRepository`` for this request."""
    return SessionRepository(db[SessionRepository.COLLECTION])


def get_message_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> MessageRepository:
    """FastAPI dependency — returns a ``MessageRepository`` for this request."""
    return MessageRepository(db[MessageRepository.COLLECTION])


def get_consultation_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ConsultationRepository:
    """FastAPI dependency — returns a ``ConsultationRepository`` for this request."""
    return ConsultationRepository(db[ConsultationRepository.COLLECTION])


def get_reimbursement_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> ReimbursementRepository:
    """FastAPI dependency — returns a ``ReimbursementRepository`` for this request."""
    return ReimbursementRepository(db[ReimbursementRepository.COLLECTION])


def get_followup_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> FollowupRepository:
    """FastAPI dependency — returns a ``FollowupRepository`` for this request."""
    return FollowupRepository(db[FollowupRepository.COLLECTION])


def get_faq_log_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> FAQLogRepository:
    """FastAPI dependency — returns a ``FAQLogRepository`` for this request."""
    return FAQLogRepository(db[FAQLogRepository.COLLECTION])


def get_monitoring_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> MonitoringLogRepository:
    """FastAPI dependency — returns a ``MonitoringLogRepository`` for this request."""
    return MonitoringLogRepository(db[MonitoringLogRepository.COLLECTION])


def get_feedback_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> FeedbackRepository:
    """FastAPI dependency — returns a ``FeedbackRepository`` for this request."""
    return FeedbackRepository(db[FeedbackRepository.COLLECTION])


def get_metrics_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),  # type: ignore[type-arg]
) -> MetricsRepository:
    """FastAPI dependency — returns a ``MetricsRepository`` for this request."""
    return MetricsRepository(db[MetricsRepository.COLLECTION])

"""
Healthcare AI Router — Session Manager Service
=============================================
Provides session management, load history, and message history persistence.
Uses MongoDB repositories (SessionRepository and MessageRepository) to store
metadata and conversation logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Depends
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from backend.database.repository import (
    SessionRepository,
    MessageRepository,
    get_session_repository,
    get_message_repository,
)
from backend.models.domain import Session, ChatMessage, MessageRole, TokenUsage
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Session Manager.
    Coordinates generating session IDs, loading context history, and saving turns.
    """

    def __init__(
        self,
        session_repo: SessionRepository = Depends(get_session_repository),
        message_repo: MessageRepository = Depends(get_message_repository),
    ) -> None:
        self.session_repo = session_repo
        self.message_repo = message_repo

    async def get_or_create_session(self, session_id: str | None) -> Session:
        """
        Retrieves a session from MongoDB or creates one if it doesn't exist.

        Args:
            session_id: Logical UUID session identifier.

        Returns:
            The loaded or newly created Session domain model.
        """
        if session_id:
            doc = await self.session_repo.get_by_id(session_id)
            if doc:
                logger.debug("Loaded existing session", extra={"session_id": session_id})
                return Session(**doc)

        new_id = session_id or str(uuid.uuid4())
        session = Session(
            id=new_id,
            user_id=None,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            message_count=0,
            last_intent=None,
            metadata={},
        )
        await self.session_repo.create_session(session.model_dump())
        logger.info("Created new session", extra={"session_id": new_id})
        return session

    async def get_history(self, session_id: str, limit: int = 20) -> list[BaseMessage]:
        """
        Retrieves recent chronological message history for a session from MongoDB,
        translating them into LangChain BaseMessage objects.

        Args:
            session_id: Session identifier.
            limit: Maximum history turns to load.

        Returns:
            List of BaseMessage instances representing historical turns.
        """
        db_messages = await self.message_repo.get_session_history(session_id, limit=limit)
        lc_messages: list[BaseMessage] = []
        for msg in db_messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == MessageRole.USER.value:
                lc_messages.append(HumanMessage(content=content))
            elif role in (MessageRole.ASSISTANT.value, "ai"):
                lc_messages.append(AIMessage(content=content))
            elif role == MessageRole.SYSTEM.value:
                lc_messages.append(SystemMessage(content=content))
        logger.debug(
            "Loaded history turns from MongoDB",
            extra={"session_id": session_id, "turns": len(lc_messages)},
        )
        return lc_messages

    async def save_user_message(
        self, session_id: str, message: str, correlation_id: str
    ) -> ChatMessage:
        """
        Saves a user message and increments message count.

        Args:
            session_id: Session identifier.
            message: Raw user message.
            correlation_id: Request correlation identifier.

        Returns:
            The saved ChatMessage domain model.
        """
        chat_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=message,
            correlation_id=correlation_id,
            timestamp=datetime.now(tz=timezone.utc),
        )
        await self.message_repo.save_message(chat_msg.model_dump(mode="json"))
        await self.session_repo.increment_message_count(session_id)
        return chat_msg

    async def save_assistant_message(
        self,
        session_id: str,
        message: str,
        correlation_id: str,
        intent: str,
        agent: str,
        token_usage: dict | None = None,
    ) -> ChatMessage:
        """
        Saves assistant reply, increments message count, and updates intent.

        Args:
            session_id: Session identifier.
            message: Assistant text reply.
            correlation_id: Request correlation identifier.
            intent: Classified intent.
            agent: Agent that handled the request.
            token_usage: Optional dictionary of LLM token metrics.

        Returns:
            The saved ChatMessage domain model.
        """
        usage = None
        if token_usage:
            usage = TokenUsage(
                prompt_tokens=token_usage.get("prompt_tokens", 0),
                completion_tokens=token_usage.get("completion_tokens", 0),
                total_tokens=token_usage.get("total_tokens", 0),
            )

        chat_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=message,
            correlation_id=correlation_id,
            intent=intent,
            agent=agent,
            token_usage=usage,
            timestamp=datetime.now(tz=timezone.utc),
        )
        await self.message_repo.save_message(chat_msg.model_dump(mode="json"))
        await self.session_repo.increment_message_count(session_id)
        if intent and intent != "error":
            await self.session_repo.update_last_intent(session_id, intent)
        return chat_msg


def get_session_manager(
    session_repo: SessionRepository = Depends(get_session_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
) -> SessionManager:
    """FastAPI dependency — returns a SessionManager instance."""
    return SessionManager(session_repo=session_repo, message_repo=message_repo)

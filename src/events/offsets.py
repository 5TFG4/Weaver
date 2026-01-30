"""
Consumer Offset Management

Tracks consumer progress through the event log.
Enables at-least-once delivery and recovery after consumer restart.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import AsyncConnectionPool


class OffsetStore(ABC):
    """
    Abstract base class for consumer offset storage.

    Consumers use this to:
    - Record their progress through the event log
    - Resume from last processed offset after restart
    """

    @abstractmethod
    async def get_offset(self, consumer_id: str) -> int:
        """
        Get the last processed offset for a consumer.

        Args:
            consumer_id: Unique identifier for the consumer

        Returns:
            Last processed offset, or -1 if never processed
        """
        pass

    @abstractmethod
    async def set_offset(self, consumer_id: str, offset: int) -> None:
        """
        Update the last processed offset for a consumer.

        Args:
            consumer_id: Unique identifier for the consumer
            offset: The offset to record
        """
        pass

    @abstractmethod
    async def get_all_offsets(self) -> dict[str, int]:
        """
        Get all consumer offsets.

        Returns:
            Dictionary mapping consumer_id to offset
        """
        pass


class InMemoryOffsetStore(OffsetStore):
    """
    In-memory offset store for testing and development.

    Not suitable for production - offsets are lost on restart.
    """

    def __init__(self) -> None:
        self._offsets: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def get_offset(self, consumer_id: str) -> int:
        """Get the last processed offset."""
        async with self._lock:
            return self._offsets.get(consumer_id, -1)

    async def set_offset(self, consumer_id: str, offset: int) -> None:
        """Update the last processed offset."""
        async with self._lock:
            self._offsets[consumer_id] = offset

    async def get_all_offsets(self) -> dict[str, int]:
        """Get all consumer offsets."""
        async with self._lock:
            return dict(self._offsets)

    def clear(self) -> None:
        """Clear all offsets (for testing)."""
        self._offsets.clear()


class PostgresOffsetStore(OffsetStore):
    """
    PostgreSQL-backed offset store using SQLAlchemy.

    Stores consumer offsets in the 'consumer_offsets' table.
    Uses upsert for atomic set_offset operations.
    """

    def __init__(self, session_factory: Any) -> None:
        """
        Initialize with a SQLAlchemy session factory.

        Args:
            session_factory: SQLAlchemy async_sessionmaker
        """
        self._session_factory = session_factory

    async def get_offset(self, consumer_id: str) -> int:
        """Get the last processed offset from the database."""
        from sqlalchemy import select
        from src.walle.models import ConsumerOffset

        async with self._session_factory() as session:
            result = await session.execute(
                select(ConsumerOffset.last_offset).where(
                    ConsumerOffset.consumer_id == consumer_id
                )
            )
            offset = result.scalar()
            return offset if offset is not None else -1

    async def set_offset(self, consumer_id: str, offset: int) -> None:
        """Update the last processed offset in the database."""
        from sqlalchemy.dialects.postgresql import insert
        from src.walle.models import ConsumerOffset

        async with self._session_factory() as session:
            stmt = insert(ConsumerOffset).values(
                consumer_id=consumer_id,
                last_offset=offset,
                updated_at=datetime.now(timezone.utc),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["consumer_id"],
                set_={
                    "last_offset": offset,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await session.execute(stmt)
            await session.commit()

    async def get_all_offsets(self) -> dict[str, int]:
        """Get all consumer offsets from the database."""
        from sqlalchemy import select
        from src.walle.models import ConsumerOffset

        async with self._session_factory() as session:
            result = await session.execute(
                select(ConsumerOffset.consumer_id, ConsumerOffset.last_offset)
            )
            rows = result.all()
            return {row.consumer_id: row.last_offset for row in rows}


class EventConsumer:
    """
    High-level event consumer with automatic offset tracking.

    Provides:
    - Automatic offset persistence
    - At-least-once delivery semantics
    - Resume from last processed offset
    """

    def __init__(
        self,
        consumer_id: str,
        event_log: Any,  # EventLog
        offset_store: OffsetStore,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize the event consumer.

        Args:
            consumer_id: Unique identifier for this consumer
            event_log: The event log to consume from
            offset_store: Store for offset persistence
            batch_size: Number of events to fetch per batch
        """
        self.consumer_id = consumer_id
        self._event_log = event_log
        self._offset_store = offset_store
        self._batch_size = batch_size
        self._running = False
        self._current_offset: int = -1

    async def start(self) -> None:
        """Start consuming events."""
        self._current_offset = await self._offset_store.get_offset(self.consumer_id)
        self._running = True

    async def stop(self) -> None:
        """Stop consuming events."""
        self._running = False

    async def poll(self) -> list[tuple[int, Any]]:
        """
        Poll for new events.

        Returns:
            List of (offset, envelope) tuples
        """
        if not self._running:
            return []

        events = await self._event_log.read_from(
            self._current_offset,
            limit=self._batch_size,
        )
        return events

    async def commit(self, offset: int) -> None:
        """
        Commit the processed offset.

        Args:
            offset: The last successfully processed offset
        """
        await self._offset_store.set_offset(self.consumer_id, offset)
        self._current_offset = offset

    @property
    def current_offset(self) -> int:
        """Get the current offset."""
        return self._current_offset

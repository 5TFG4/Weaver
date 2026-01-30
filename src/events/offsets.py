"""
Consumer Offset Management

Tracks consumer progress through the event log.
Enables at-least-once delivery and recovery after consumer restart.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


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
    PostgreSQL-backed offset store.

    Stores consumer offsets in the 'consumer_offsets' table.

    Note: Requires asyncpg and a running PostgreSQL instance.
    This is a placeholder implementation - will be completed in integration phase.
    """

    def __init__(self, pool: Any) -> None:
        """
        Initialize with a database connection pool.

        Args:
            pool: asyncpg connection pool
        """
        self._pool = pool

    async def get_offset(self, consumer_id: str) -> int:
        """Get the last processed offset from the database."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT last_offset
                FROM consumer_offsets
                WHERE consumer_id = $1
                """,
                consumer_id,
            )
            return row["last_offset"] if row else -1

    async def set_offset(self, consumer_id: str, offset: int) -> None:
        """Update the last processed offset in the database."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO consumer_offsets (consumer_id, last_offset, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (consumer_id)
                DO UPDATE SET last_offset = $2, updated_at = $3
                """,
                consumer_id,
                offset,
                datetime.now(timezone.utc),
            )

    async def get_all_offsets(self) -> dict[str, int]:
        """Get all consumer offsets from the database."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT consumer_id, last_offset
                FROM consumer_offsets
                """
            )
            return {row["consumer_id"]: row["last_offset"] for row in rows}


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

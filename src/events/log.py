"""
Event Log (Outbox Pattern)

Implements the Outbox pattern with PostgreSQL LISTEN/NOTIFY for event delivery.
Business writes and event appends happen in the same transaction.
After commit, NOTIFY wakes subscribers for at-least-once delivery.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from .protocol import Envelope

if TYPE_CHECKING:
    from .types import AsyncConnectionPool

logger = logging.getLogger(__name__)


class EventLog(ABC):
    """
    Abstract base class for event log implementations.

    The event log provides:
    - Atomic append with business transaction
    - Fan-out notification to subscribers
    - Ordered event retrieval from offset
    """

    @abstractmethod
    async def append(
        self,
        envelope: Envelope,
        *,
        connection: Any | None = None,
    ) -> int:
        """
        Append an event to the log.

        Args:
            envelope: The event envelope to append
            connection: Optional database connection for transaction

        Returns:
            The sequence number (offset) of the appended event
        """
        pass

    @abstractmethod
    async def read_from(
        self,
        offset: int,
        limit: int = 100,
    ) -> list[tuple[int, Envelope]]:
        """
        Read events from the log starting at offset.

        Args:
            offset: Starting sequence number (exclusive)
            limit: Maximum number of events to return

        Returns:
            List of (offset, envelope) tuples
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        callback: Callable[[Envelope], Any],
    ) -> Callable[[], None]:
        """
        Subscribe to new events.

        Args:
            callback: Function to call for each new event

        Returns:
            Unsubscribe function
        """
        pass

    @abstractmethod
    async def get_latest_offset(self) -> int:
        """Get the latest event offset in the log."""
        pass


class InMemoryEventLog(EventLog):
    """
    In-memory event log for testing and development.

    Not suitable for production - events are lost on restart.
    """

    def __init__(self) -> None:
        self._events: list[Envelope] = []
        self._subscribers: list[Callable[[Envelope], Any]] = []
        self._lock = asyncio.Lock()

    async def append(
        self,
        envelope: Envelope,
        *,
        connection: Any | None = None,
    ) -> int:
        """Append an event to the in-memory log."""
        async with self._lock:
            offset = len(self._events)
            self._events.append(envelope)

        # Notify subscribers (outside lock to prevent deadlock)
        for callback in self._subscribers:
            try:
                result = callback(envelope)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Subscriber callback failed in InMemoryEventLog")

        return offset

    async def read_from(
        self,
        offset: int,
        limit: int = 100,
    ) -> list[tuple[int, Envelope]]:
        """Read events from the in-memory log."""
        async with self._lock:
            start = offset + 1 if offset >= 0 else 0
            end = min(start + limit, len(self._events))
            return [(i, self._events[i]) for i in range(start, end)]

    async def subscribe(
        self,
        callback: Callable[[Envelope], Any],
    ) -> Callable[[], None]:
        """Subscribe to new events."""
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    async def get_latest_offset(self) -> int:
        """Get the latest event offset."""
        async with self._lock:
            return len(self._events) - 1

    @property
    def event_count(self) -> int:
        """Get the total number of events."""
        return len(self._events)

    @property
    def events(self) -> list[Envelope]:
        """Get all events (for testing)."""
        return list(self._events)

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()


class PostgresEventLog(EventLog):
    """
    PostgreSQL-backed event log using Outbox pattern.

    Uses LISTEN/NOTIFY for real-time notification.
    Events are stored in the 'outbox' table.

    Note: Requires asyncpg and a running PostgreSQL instance.
    This is a placeholder implementation - will be completed in integration phase.
    """

    CHANNEL = "weaver_events"

    def __init__(self, pool: "AsyncConnectionPool") -> None:
        """
        Initialize with a database connection pool.

        Args:
            pool: asyncpg connection pool
        """
        self._pool = pool
        self._subscribers: list[Callable[[Envelope], Any]] = []
        self._listener_task: asyncio.Task | None = None

    async def append(
        self,
        envelope: Envelope,
        *,
        connection: Any | None = None,
    ) -> int:
        """
        Append an event to the outbox table.

        Should be called within a transaction with business writes.
        """
        conn = connection or await self._pool.acquire()
        try:
            # Insert into outbox
            row = await conn.fetchrow(
                """
                INSERT INTO outbox (type, payload, created_at)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                envelope.type,
                json.dumps(envelope.to_dict()),
                envelope.ts,
            )
            offset = row["id"]

            # Notify listeners (after successful insert)
            await conn.execute(f"NOTIFY {self.CHANNEL}, '{offset}'")

            return offset
        finally:
            if connection is None:
                await self._pool.release(conn)

    async def read_from(
        self,
        offset: int,
        limit: int = 100,
    ) -> list[tuple[int, Envelope]]:
        """Read events from the outbox table."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, payload
                FROM outbox
                WHERE id > $1
                ORDER BY id
                LIMIT $2
                """,
                offset,
                limit,
            )
            return [
                (row["id"], Envelope.from_dict(json.loads(row["payload"])))
                for row in rows
            ]

    async def subscribe(
        self,
        callback: Callable[[Envelope], Any],
    ) -> Callable[[], None]:
        """Subscribe to new events via LISTEN/NOTIFY."""
        self._subscribers.append(callback)

        # Start listener if not running
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self._listen_loop())

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    async def _listen_loop(self) -> None:
        """Background task to listen for notifications."""
        async with self._pool.acquire() as conn:
            await conn.add_listener(self.CHANNEL, self._on_notify)
            try:
                while True:
                    await asyncio.sleep(3600)  # Keep connection alive
            finally:
                await conn.remove_listener(self.CHANNEL, self._on_notify)

    def _on_notify(
        self,
        connection: Any,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """Handle NOTIFY callback."""
        # Schedule async processing
        asyncio.create_task(self._process_notification(int(payload)))

    async def _process_notification(self, offset: int) -> None:
        """Process a notification by reading and dispatching the event."""
        events = await self.read_from(offset - 1, limit=1)
        if events:
            _, envelope = events[0]
            for callback in self._subscribers:
                try:
                    result = callback(envelope)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception("Subscriber callback failed in PostgresEventLog")

    async def get_latest_offset(self) -> int:
        """Get the latest event offset from the outbox."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT MAX(id) as max_id FROM outbox")
            return row["max_id"] or -1

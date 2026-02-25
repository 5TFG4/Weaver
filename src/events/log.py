"""
Event Log (Outbox Pattern)

Implements the Outbox pattern with PostgreSQL LISTEN/NOTIFY for event delivery.
Business writes and event appends happen in the same transaction.
After commit, NOTIFY wakes subscribers for at-least-once delivery.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

import sqlalchemy as sa

from .protocol import Envelope, Subscription

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
    async def subscribe_filtered(
        self,
        event_types: list[str],
        callback: Callable[[Envelope], Any],
        filter_fn: Callable[[Envelope], bool] | None = None,
    ) -> str:
        """
        Subscribe to events with type filtering.

        Args:
            event_types: List of event types to receive (use ['*'] for all)
            callback: Async function to call for each matching event
            filter_fn: Optional function to further filter events

        Returns:
            Subscription ID for unsubscribing
        """
        pass

    @abstractmethod
    async def unsubscribe_by_id(self, subscription_id: str) -> None:
        """
        Unsubscribe by subscription ID.

        Args:
            subscription_id: The ID returned from subscribe_filtered()

        Note:
            Safe to call with unknown ID (no-op).
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
        self._filtered_subscriptions: dict[str, Subscription] = {}
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

        # Notify legacy subscribers (outside lock to prevent deadlock)
        for callback in self._subscribers:
            try:
                result = callback(envelope)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Subscriber callback failed in InMemoryEventLog")

        # Notify filtered subscriptions
        for sub in self._filtered_subscriptions.values():
            if sub.matches(envelope):
                try:
                    result = sub.callback(envelope)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception(
                        "Filtered subscriber callback failed",
                        extra={"subscription_id": sub.id},
                    )

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

    async def subscribe_filtered(
        self,
        event_types: list[str],
        callback: Callable[[Envelope], Any],
        filter_fn: Callable[[Envelope], bool] | None = None,
    ) -> str:
        """
        Subscribe to events with type filtering.

        Args:
            event_types: List of event types to receive (use ['*'] for all)
            callback: Async function to call for each matching event
            filter_fn: Optional function to further filter events

        Returns:
            Subscription ID for unsubscribing
        """
        from uuid import uuid4

        sub_id = str(uuid4())
        subscription = Subscription(
            id=sub_id,
            event_types=event_types,
            callback=callback,
            filter_fn=filter_fn,
        )
        self._filtered_subscriptions[sub_id] = subscription
        return sub_id

    async def unsubscribe_by_id(self, subscription_id: str) -> None:
        """
        Unsubscribe by subscription ID.

        Args:
            subscription_id: The ID returned from subscribe_filtered()

        Note:
            Safe to call with unknown ID (no-op).
        """
        self._filtered_subscriptions.pop(subscription_id, None)


class PostgresEventLog(EventLog):
    """
    PostgreSQL-backed event log using Outbox pattern.

    Uses LISTEN/NOTIFY for real-time notification.
    Events are stored in the 'outbox' table.

    Supports two modes:
    1. SQLAlchemy AsyncSession (recommended for transaction integration)
    2. asyncpg connection pool (for LISTEN/NOTIFY)
    """

    CHANNEL = "weaver_events"

    def __init__(
        self,
        session_factory: Any | None = None,
        pool: "AsyncConnectionPool | None" = None,
    ) -> None:
        """
        Initialize with session factory and/or connection pool.

        Args:
            session_factory: SQLAlchemy async_sessionmaker (for append/read)
            pool: asyncpg connection pool (for LISTEN/NOTIFY)
        """
        self._session_factory = session_factory
        self._pool = pool
        self._subscribers: list[Callable[[Envelope], Any]] = []
        self._filtered_subscriptions: dict[str, Subscription] = {}
        self._listener_task: asyncio.Task[None] | None = None

    async def append(
        self,
        envelope: Envelope,
        *,
        connection: Any | None = None,
    ) -> int:
        """
        Append an event to the outbox table.

        Can use either:
        - An existing SQLAlchemy session (passed via connection)
        - The session factory to create a new session

        D-1: After DB write, dispatches to in-process subscribers directly
        (matching InMemoryEventLog behavior). pg_notify is still used for
        cross-process notification.

        Returns the sequence number (offset) of the appended event.
        """
        from src.walle.models import OutboxEvent

        # If connection is an AsyncSession, use it directly
        if connection is not None:
            event = OutboxEvent(
                type=envelope.type,
                payload=envelope.to_dict(),
                created_at=envelope.ts,
            )
            connection.add(event)
            await connection.flush()  # Get the ID without committing
            offset = event.id

            # NOTIFY using pg_notify() function (supports parameterization)
            await connection.execute(
                sa.text("SELECT pg_notify(:channel, :payload)"),
                {"channel": self.CHANNEL, "payload": str(offset)},
            )

            # D-1: Direct in-process subscriber dispatch
            await self._dispatch_to_subscribers(envelope)

            return offset

        # Otherwise, create a new session
        if self._session_factory is None:
            raise RuntimeError("No session factory configured")

        async with self._session_factory() as session:
            event = OutboxEvent(
                type=envelope.type,
                payload=envelope.to_dict(),
                created_at=envelope.ts,
            )
            session.add(event)
            await session.flush()
            offset = event.id

            await session.execute(
                sa.text("SELECT pg_notify(:channel, :payload)"),
                {"channel": self.CHANNEL, "payload": str(offset)},
            )
            await session.commit()

        # D-1: Direct in-process subscriber dispatch (after commit)
        await self._dispatch_to_subscribers(envelope)

        return offset

    async def read_from(
        self,
        offset: int,
        limit: int = 100,
    ) -> list[tuple[int, Envelope]]:
        """Read events from the outbox table."""
        from src.walle.models import OutboxEvent

        if self._session_factory is None:
            raise RuntimeError("No session factory configured")

        async with self._session_factory() as session:
            result = await session.execute(
                sa.select(OutboxEvent)
                .where(OutboxEvent.id > offset)
                .order_by(OutboxEvent.id)
                .limit(limit)
            )
            events = result.scalars().all()
            return [
                (event.id, Envelope.from_dict(event.payload))
                for event in events
            ]

    async def _dispatch_to_subscribers(self, envelope: Envelope) -> None:
        """
        Dispatch event to all in-process subscribers.

        D-1: Shared dispatch logic for direct subscriber notification.
        Called after DB write to ensure behavioral parity with InMemoryEventLog.
        Errors in individual subscribers are logged but do not block others.
        """
        # Notify legacy subscribers
        for callback in self._subscribers:
            try:
                result = callback(envelope)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Subscriber callback failed in PostgresEventLog")

        # Notify filtered subscriptions
        for sub in self._filtered_subscriptions.values():
            if sub.matches(envelope):
                try:
                    result = sub.callback(envelope)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception(
                        "Filtered subscriber callback failed",
                        extra={"subscription_id": sub.id},
                    )

    async def subscribe(
        self,
        callback: Callable[[Envelope], Any],
    ) -> Callable[[], None]:
        """Subscribe to new events via LISTEN/NOTIFY."""
        self._subscribers.append(callback)

        # Start listener if not running and pool is available
        if self._listener_task is None and self._pool is not None:
            self._listener_task = asyncio.create_task(self._listen_loop())

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    async def _listen_loop(self) -> None:
        """Background task to listen for notifications."""
        if self._pool is None:
            return

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
            # Notify legacy subscribers
            for callback in self._subscribers:
                try:
                    result = callback(envelope)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception("Subscriber callback failed in PostgresEventLog")

            # Notify filtered subscriptions
            for sub in self._filtered_subscriptions.values():
                if sub.matches(envelope):
                    try:
                        result = sub.callback(envelope)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        logger.exception(
                            "Filtered subscriber callback failed",
                            extra={"subscription_id": sub.id},
                        )

    async def subscribe_filtered(
        self,
        event_types: list[str],
        callback: Callable[[Envelope], Any],
        filter_fn: Callable[[Envelope], bool] | None = None,
    ) -> str:
        """
        Subscribe to events with type filtering via LISTEN/NOTIFY.

        Args:
            event_types: List of event types to receive (use ['*'] for all)
            callback: Async function to call for each matching event
            filter_fn: Optional function to further filter events

        Returns:
            Subscription ID for unsubscribing
        """
        from uuid import uuid4

        sub_id = str(uuid4())
        subscription = Subscription(
            id=sub_id,
            event_types=event_types,
            callback=callback,
            filter_fn=filter_fn,
        )
        self._filtered_subscriptions[sub_id] = subscription

        # Start listener if not running and pool is available
        if self._listener_task is None and self._pool is not None:
            self._listener_task = asyncio.create_task(self._listen_loop())

        return sub_id

    async def unsubscribe_by_id(self, subscription_id: str) -> None:
        """
        Unsubscribe by subscription ID.

        Args:
            subscription_id: The ID returned from subscribe_filtered()

        Note:
            Safe to call with unknown ID (no-op).
        """
        self._filtered_subscriptions.pop(subscription_id, None)

    async def get_latest_offset(self) -> int:
        """Get the latest event offset from the outbox."""
        from src.walle.models import OutboxEvent

        if self._session_factory is None:
            raise RuntimeError("No session factory configured")

        async with self._session_factory() as session:
            result = await session.execute(
                sa.select(sa.func.max(OutboxEvent.id))
            )
            max_id = result.scalar()
            return max_id if max_id is not None else -1

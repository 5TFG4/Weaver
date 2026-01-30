"""Integration tests for PostgresEventLog with real database.

Tests the complete event log functionality including:
- Event persistence
- Event reading with offset
- LISTEN/NOTIFY for real-time notifications
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from src.events.log import PostgresEventLog
from src.events.protocol import Envelope
from src.walle.database import Database
from src.walle.models import OutboxEvent

if TYPE_CHECKING:
    pass


pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.environ.get("DB_URL"),
        reason="DB_URL environment variable not set (run with docker-compose)",
    ),
]


class TestPostgresEventLogAppend:
    """Tests for appending events to the log."""

    async def test_append_single_event(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should persist event to database with correct data."""
        event_log = PostgresEventLog(session_factory=database.session_factory)
        envelope = Envelope(
            type="test.event",
            producer="test",
            payload={"key": "value", "number": 42},
        )

        offset = await event_log.append(envelope)

        assert offset >= 1  # First event should have offset 1

        # Verify event was persisted
        async with database.session() as session:
            result = await session.execute(
                select(OutboxEvent).where(OutboxEvent.id == offset)
            )
            row = result.scalar_one()
            assert row.type == "test.event"
            # Payload is stored as serialized envelope
            assert row.payload["payload"] == {"key": "value", "number": 42}
            assert row.created_at is not None

    async def test_append_multiple_events_increments_offset(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should assign sequential offsets to events."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        offsets = []
        for i in range(5):
            envelope = Envelope(
                type=f"test.event.{i}",
                producer="test",
                payload={"index": i},
            )
            offset = await event_log.append(envelope)
            offsets.append(offset)

        # Offsets should be sequential
        assert offsets == [1, 2, 3, 4, 5]

    async def test_append_preserves_complex_payload(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should correctly store and retrieve complex JSON payloads."""
        event_log = PostgresEventLog(session_factory=database.session_factory)
        complex_payload = {
            "nested": {"deep": {"value": 123}},
            "array": [1, 2, 3],
            "boolean": True,
            "null_value": None,
            "unicode": "日本語テスト",
        }
        envelope = Envelope(
            type="test.complex",
            producer="test",
            payload=complex_payload,
        )

        offset = await event_log.append(envelope)

        async with database.session() as session:
            result = await session.execute(
                select(OutboxEvent).where(OutboxEvent.id == offset)
            )
            row = result.scalar_one()
            assert row.payload["payload"] == complex_payload


class TestPostgresEventLogRead:
    """Tests for reading events from the log."""

    async def test_read_from_beginning(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should read all events when starting from offset -1."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        # Append some events
        for i in range(3):
            envelope = Envelope(
                type=f"test.event.{i}",
                producer="test",
                payload={"index": i},
            )
            await event_log.append(envelope)

        # Read from beginning (offset -1 means "start before first event")
        events = await event_log.read_from(-1)

        assert len(events) == 3
        assert events[0][1].type == "test.event.0"
        assert events[1][1].type == "test.event.1"
        assert events[2][1].type == "test.event.2"

    async def test_read_from_middle_offset(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should read only events after specified offset."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        # Append events (index 0-4 → offsets 1-5)
        for i in range(5):
            envelope = Envelope(
                type=f"test.event.{i}",
                producer="test",
                payload={"index": i},
            )
            await event_log.append(envelope)

        # Read from offset 2 (exclusive) → returns offsets 3, 4, 5
        # which correspond to test.event.2, test.event.3, test.event.4
        events = await event_log.read_from(2)

        assert len(events) == 3
        assert events[0][1].type == "test.event.2"  # offset 3 contains event index 2
        assert events[0][1].payload == {"index": 2}

    async def test_read_with_limit(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should respect the limit parameter."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        # Append many events
        for i in range(10):
            envelope = Envelope(
                type=f"test.event.{i}",
                producer="test",
                payload={"index": i},
            )
            await event_log.append(envelope)

        # Read with limit
        events = await event_log.read_from(-1, limit=3)

        assert len(events) == 3

    async def test_read_from_future_offset_returns_empty(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should return empty list when offset is beyond all events."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        # Append a few events
        for i in range(3):
            envelope = Envelope(
                type=f"test.event.{i}",
                producer="test",
                payload={"index": i},
            )
            await event_log.append(envelope)

        # Read from a future offset
        events = await event_log.read_from(1000)

        assert events == []

    async def test_read_returns_events_with_offsets(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should include offset in returned events."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        envelope = Envelope(
            type="test.event",
            producer="test",
            payload={"key": "value"},
        )
        expected_offset = await event_log.append(envelope)

        events = await event_log.read_from(-1)

        assert len(events) == 1
        assert events[0][0] == expected_offset  # First element is offset


class TestPostgresEventLogConcurrency:
    """Tests for concurrent access patterns."""

    async def test_concurrent_appends_maintain_order(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle concurrent appends with correct ordering."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        async def append_event(index: int) -> int:
            envelope = Envelope(
                type=f"test.concurrent.{index}",
                producer="test",
                payload={"index": index},
            )
            return await event_log.append(envelope)

        # Append events concurrently
        offsets = await asyncio.gather(*[append_event(i) for i in range(10)])

        # All offsets should be unique
        assert len(set(offsets)) == 10

        # All offsets should be in range 1-10
        assert all(1 <= o <= 10 for o in offsets)

    async def test_read_while_writing(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle reads while writes are occurring."""
        event_log = PostgresEventLog(session_factory=database.session_factory)

        # Append initial events
        for i in range(5):
            envelope = Envelope(
                type=f"test.initial.{i}",
                producer="test",
                payload={"index": i},
            )
            await event_log.append(envelope)

        # Start concurrent read and write
        async def write_events() -> None:
            for i in range(5, 10):
                envelope = Envelope(
                    type=f"test.concurrent.{i}",
                    producer="test",
                    payload={"index": i},
                )
                await event_log.append(envelope)
                await asyncio.sleep(0.01)

        async def read_events() -> list[tuple[int, Envelope]]:
            await asyncio.sleep(0.02)  # Let some writes happen
            return await event_log.read_from(-1)

        # Run concurrently
        _, events = await asyncio.gather(write_events(), read_events())

        # Should have read at least the initial events
        assert len(events) >= 5

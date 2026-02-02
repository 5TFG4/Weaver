"""
Tests for SSE Broadcaster

MVP-3: SSE Real-time Push
TDD: Write tests first, then implement.
"""

from __future__ import annotations

import asyncio
import json

import pytest


class TestSSEBroadcasterSubscribe:
    """Tests for SSEBroadcaster.subscribe()."""

    async def test_returns_async_iterator(self) -> None:
        """subscribe() should return an async iterator."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()
        subscription = broadcaster.subscribe()

        assert hasattr(subscription, "__anext__")

    async def test_receives_published_events(self) -> None:
        """Subscriber should receive published events."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()
        received: list = []

        async def collect() -> None:
            async for event in broadcaster.subscribe():
                received.append(event)
                break  # Exit after first event

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)  # Let subscriber connect
        await broadcaster.publish("test.event", {"data": "hello"})
        await asyncio.wait_for(task, timeout=1.0)

        assert len(received) == 1
        assert received[0].event == "test.event"


class TestSSEBroadcasterPublish:
    """Tests for SSEBroadcaster.publish()."""

    async def test_increments_event_id(self) -> None:
        """publish() should increment event ID."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()
        # Need at least one subscriber for publish to work
        received: list = []

        async def collect() -> None:
            async for event in broadcaster.subscribe():
                received.append(event)
                if len(received) >= 2:
                    break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)

        await broadcaster.publish("event1", {})
        await broadcaster.publish("event2", {})

        await asyncio.wait_for(task, timeout=1.0)

        assert received[0].id == "1"
        assert received[1].id == "2"

    async def test_sends_to_all_clients(self) -> None:
        """publish() should send to all connected clients."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()
        received_1: list = []
        received_2: list = []

        async def collect_1() -> None:
            async for event in broadcaster.subscribe():
                received_1.append(event)
                break

        async def collect_2() -> None:
            async for event in broadcaster.subscribe():
                received_2.append(event)
                break

        task1 = asyncio.create_task(collect_1())
        task2 = asyncio.create_task(collect_2())
        await asyncio.sleep(0.01)

        await broadcaster.publish("broadcast", {"msg": "to all"})

        await asyncio.gather(task1, task2)

        assert len(received_1) == 1
        assert len(received_2) == 1

    async def test_event_has_correct_format(self) -> None:
        """Published event should have id, event, and data fields."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()
        received: list = []

        async def collect() -> None:
            async for event in broadcaster.subscribe():
                received.append(event)
                break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)
        await broadcaster.publish("test.type", {"key": "value"})
        await asyncio.wait_for(task, timeout=1.0)

        event = received[0]
        assert event.id is not None
        assert event.event == "test.type"
        # Data should be JSON
        data = json.loads(event.data)
        assert data["key"] == "value"


class TestSSEBroadcasterClientManagement:
    """Tests for SSE client connection management."""

    async def test_client_count_starts_at_zero(self) -> None:
        """Initial client count should be 0."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()

        assert broadcaster.client_count == 0

    async def test_client_count_increases_on_subscribe(self) -> None:
        """Client count should increase when subscribing."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()

        async def hold_connection() -> None:
            async for _ in broadcaster.subscribe():
                break

        task = asyncio.create_task(hold_connection())
        await asyncio.sleep(0.01)

        assert broadcaster.client_count == 1

        await broadcaster.publish("close", {})
        await task

    async def test_client_count_decreases_on_disconnect(self) -> None:
        """Client count should decrease when client disconnects."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = SSEBroadcaster()

        async def short_lived() -> None:
            async for _ in broadcaster.subscribe():
                break  # Disconnect immediately after first event

        task = asyncio.create_task(short_lived())
        await asyncio.sleep(0.01)
        assert broadcaster.client_count == 1

        await broadcaster.publish("trigger", {})
        await task
        await asyncio.sleep(0.01)

        assert broadcaster.client_count == 0

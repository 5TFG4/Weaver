"""Unit tests for PostgresEventLog dispatch behavior under subscriber mutation."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.events.log import PostgresEventLog
from src.events.protocol import Envelope


@pytest.mark.asyncio
async def test_dispatch_to_subscribers_handles_legacy_unsubscribe_during_dispatch() -> None:
    """Removing a legacy subscriber inside a callback should not skip remaining callbacks."""
    event_log = PostgresEventLog()
    envelope = Envelope(type="test.event", producer="test", payload={})

    calls: list[str] = []

    async def callback_one(_: Envelope) -> None:
        calls.append("one")
        unsubscribe_two()

    async def callback_two(_: Envelope) -> None:
        calls.append("two")

    await event_log.subscribe(callback_one)
    unsubscribe_two = await event_log.subscribe(callback_two)

    await event_log._dispatch_to_subscribers(envelope)

    assert calls == ["one", "two"]


@pytest.mark.asyncio
async def test_dispatch_to_subscribers_handles_filtered_unsubscribe_during_dispatch() -> None:
    """Removing a filtered subscription inside a callback should not break iteration."""
    event_log = PostgresEventLog()
    envelope = Envelope(type="test.event", producer="test", payload={})

    calls: list[str] = []

    async def callback_two(_: Envelope) -> None:
        calls.append("two")

    sub_two_id = await event_log.subscribe_filtered(
        event_types=["*"],
        callback=callback_two,
    )

    async def callback_one(_: Envelope) -> None:
        calls.append("one")
        await event_log.unsubscribe_by_id(sub_two_id)

    await event_log.subscribe_filtered(
        event_types=["*"],
        callback=callback_one,
    )

    await event_log._dispatch_to_subscribers(envelope)

    assert calls == ["two", "one"] or calls == ["one", "two"]


@pytest.mark.asyncio
async def test_process_notification_handles_filtered_unsubscribe_during_dispatch() -> None:
    """_process_notification should also tolerate filtered subscription mutation."""
    event_log = PostgresEventLog()
    envelope = Envelope(type="test.event", producer="test", payload={})
    event_log.read_from = AsyncMock(return_value=[(1, envelope)])

    calls: list[str] = []

    async def callback_two(_: Envelope) -> None:
        calls.append("two")

    sub_two_id = await event_log.subscribe_filtered(
        event_types=["*"],
        callback=callback_two,
    )

    async def callback_one(_: Envelope) -> None:
        calls.append("one")
        await event_log.unsubscribe_by_id(sub_two_id)

    await event_log.subscribe_filtered(
        event_types=["*"],
        callback=callback_one,
    )

    await event_log._process_notification(1)

    assert calls == ["two", "one"] or calls == ["one", "two"]

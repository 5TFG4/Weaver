"""
Tests for EventLog subscription functionality.

M5-1: EventLog Subscription MVP
TDD Phase: RED (Tests written before implementation)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from src.events.log import InMemoryEventLog
from src.events.protocol import Envelope

if TYPE_CHECKING:
    pass


class TestEventLogSubscription:
    """Tests for EventLog subscription functionality with filtering."""

    @pytest.fixture
    def event_log(self) -> InMemoryEventLog:
        """Create a fresh InMemoryEventLog for each test."""
        return InMemoryEventLog()

    @pytest.fixture
    def make_envelope(self) -> callable:
        """Factory for creating test envelopes."""

        def _make(
            event_type: str = "test.Event",
            run_id: str | None = None,
            payload: dict | None = None,
        ) -> Envelope:
            return Envelope(
                type=event_type,
                producer="test",
                payload=payload or {},
                run_id=run_id,
            )

        return _make

    # --- Test 1: Basic subscription with event types ---
    @pytest.mark.asyncio
    async def test_subscribe_with_event_types_returns_subscription_id(
        self, event_log: InMemoryEventLog
    ):
        """subscribe_filtered() returns a unique subscription ID."""
        callback = AsyncMock()

        sub_id = await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback,
        )

        assert sub_id is not None
        assert isinstance(sub_id, str)
        assert len(sub_id) > 0

    # --- Test 2: Subscriber receives matching events ---
    @pytest.mark.asyncio
    async def test_subscriber_receives_matching_events(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Subscriber receives events matching type filter."""
        received: list[Envelope] = []

        async def callback(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback,
        )

        envelope = make_envelope(event_type="test.Event", payload={"data": "value"})
        await event_log.append(envelope)

        assert len(received) == 1
        assert received[0].type == "test.Event"
        assert received[0].payload == {"data": "value"}

    # --- Test 3: Subscriber does NOT receive non-matching events ---
    @pytest.mark.asyncio
    async def test_subscriber_ignores_non_matching_events(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Subscriber does not receive events not in type filter."""
        received: list[Envelope] = []

        async def callback(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback,
        )

        # Append event with different type
        envelope = make_envelope(event_type="other.Event")
        await event_log.append(envelope)

        assert len(received) == 0

    # --- Test 4: Custom filter function ---
    @pytest.mark.asyncio
    async def test_subscribe_with_filter_fn(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Subscriber can filter by custom function."""
        received: list[Envelope] = []

        async def callback(envelope: Envelope) -> None:
            received.append(envelope)

        # Filter by run_id
        await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback,
            filter_fn=lambda e: e.run_id == "run-001",
        )

        # Should receive this (matching run_id)
        await event_log.append(make_envelope(event_type="test.Event", run_id="run-001"))
        # Should NOT receive this (different run_id)
        await event_log.append(make_envelope(event_type="test.Event", run_id="run-002"))

        assert len(received) == 1
        assert received[0].run_id == "run-001"

    # --- Test 5: Unsubscribe by ID stops delivery ---
    @pytest.mark.asyncio
    async def test_unsubscribe_by_id_stops_delivery(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Unsubscribing by ID stops event delivery."""
        received: list[Envelope] = []

        async def callback(envelope: Envelope) -> None:
            received.append(envelope)

        sub_id = await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback,
        )

        # Should receive this
        await event_log.append(make_envelope(event_type="test.Event"))
        assert len(received) == 1

        # Unsubscribe
        await event_log.unsubscribe_by_id(sub_id)

        # Should NOT receive this
        await event_log.append(make_envelope(event_type="test.Event"))
        assert len(received) == 1  # Still 1, not 2

    # --- Test 6: Multiple subscribers same event type ---
    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_event(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Multiple subscribers all receive the same event."""
        received_1: list[Envelope] = []
        received_2: list[Envelope] = []

        async def callback_1(envelope: Envelope) -> None:
            received_1.append(envelope)

        async def callback_2(envelope: Envelope) -> None:
            received_2.append(envelope)

        await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback_1,
        )
        await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback_2,
        )

        await event_log.append(make_envelope(event_type="test.Event"))

        assert len(received_1) == 1
        assert len(received_2) == 1

    # --- Test 7: Subscriber error doesn't break others ---
    @pytest.mark.asyncio
    async def test_subscriber_error_doesnt_break_others(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Error in one subscriber doesn't affect others."""
        received: list[Envelope] = []

        async def bad_callback(envelope: Envelope) -> None:
            raise ValueError("Intentional error")

        async def good_callback(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=bad_callback,
        )
        await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=good_callback,
        )

        # Should not raise, good_callback should still receive
        await event_log.append(make_envelope(event_type="test.Event"))

        assert len(received) == 1

    # --- Test 8: Wildcard subscription ---
    @pytest.mark.asyncio
    async def test_wildcard_subscription(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Subscriber with ['*'] receives all events."""
        received: list[Envelope] = []

        async def callback(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe_filtered(
            event_types=["*"],
            callback=callback,
        )

        await event_log.append(make_envelope(event_type="test.Event"))
        await event_log.append(make_envelope(event_type="other.Event"))
        await event_log.append(make_envelope(event_type="strategy.FetchWindow"))

        assert len(received) == 3

    # --- Test 9: Subscription with multiple types ---
    @pytest.mark.asyncio
    async def test_subscription_multiple_types(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Subscriber can listen to multiple event types."""
        received: list[Envelope] = []

        async def callback(envelope: Envelope) -> None:
            received.append(envelope)

        await event_log.subscribe_filtered(
            event_types=["type.A", "type.B"],
            callback=callback,
        )

        await event_log.append(make_envelope(event_type="type.A"))
        await event_log.append(make_envelope(event_type="type.B"))
        await event_log.append(make_envelope(event_type="type.C"))  # Not subscribed

        assert len(received) == 2
        assert {e.type for e in received} == {"type.A", "type.B"}

    # --- Test 10: Unsubscribe unknown ID is safe ---
    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_id_is_safe(self, event_log: InMemoryEventLog):
        """Unsubscribing with unknown ID doesn't raise."""
        # Should not raise
        await event_log.unsubscribe_by_id("unknown-subscription-id")

    # --- Test 11: Each subscription gets unique ID ---
    @pytest.mark.asyncio
    async def test_each_subscription_gets_unique_id(self, event_log: InMemoryEventLog):
        """Each subscription returns a different ID."""
        callback = AsyncMock()

        sub_id_1 = await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback,
        )
        sub_id_2 = await event_log.subscribe_filtered(
            event_types=["test.Event"],
            callback=callback,
        )

        assert sub_id_1 != sub_id_2

    # --- Test 12: Filter function with payload check ---
    @pytest.mark.asyncio
    async def test_filter_fn_with_payload_check(
        self, event_log: InMemoryEventLog, make_envelope
    ):
        """Filter function can check payload contents."""
        received: list[Envelope] = []

        async def callback(envelope: Envelope) -> None:
            received.append(envelope)

        # Only receive events where payload has specific key
        await event_log.subscribe_filtered(
            event_types=["data.WindowReady"],
            callback=callback,
            filter_fn=lambda e: e.payload.get("symbol") == "BTC/USD",
        )

        await event_log.append(
            make_envelope(
                event_type="data.WindowReady", payload={"symbol": "BTC/USD", "bars": []}
            )
        )
        await event_log.append(
            make_envelope(
                event_type="data.WindowReady", payload={"symbol": "ETH/USD", "bars": []}
            )
        )

        assert len(received) == 1
        assert received[0].payload["symbol"] == "BTC/USD"

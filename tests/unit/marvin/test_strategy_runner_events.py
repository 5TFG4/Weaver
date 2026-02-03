"""
Tests for StrategyRunner Event-Driven Data Flow

TDD tests for M5-2: data.WindowReady event handling.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.events.log import InMemoryEventLog
from src.events.protocol import Envelope
from src.events.types import DataEvents, StrategyEvents
from src.glados.clock.base import ClockTick
from src.marvin.base_strategy import BaseStrategy, StrategyAction
from src.marvin.strategy_runner import StrategyRunner

# Import DummyStrategy from fixtures instead of defining inline
from tests.fixtures.strategies import DummyStrategy


def make_tick(run_id: str = "run-001") -> ClockTick:
    """Factory for test clock ticks."""
    return ClockTick(
        run_id=run_id,
        ts=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        timeframe="1m",
        bar_index=0,
        is_backtest=True,
    )


class TestStrategyRunnerEventSubscription:
    """Tests for StrategyRunner event subscription behavior."""

    @pytest.fixture
    def event_log(self) -> InMemoryEventLog:
        """Create InMemoryEventLog for tests."""
        return InMemoryEventLog()

    @pytest.fixture
    def strategy(self) -> DummyStrategy:
        """Create test strategy."""
        return DummyStrategy()

    @pytest.fixture
    def runner(
        self, strategy: DummyStrategy, event_log: InMemoryEventLog
    ) -> StrategyRunner:
        """Create StrategyRunner with test dependencies."""
        return StrategyRunner(strategy=strategy, event_log=event_log)

    # -------------------------------------------------------------------------
    # Test 1: Runner subscribes to data.WindowReady on initialize
    # -------------------------------------------------------------------------
    async def test_initialize_subscribes_to_window_ready(
        self, runner: StrategyRunner, event_log: InMemoryEventLog
    ) -> None:
        """After initialize, runner is subscribed to data.WindowReady."""
        await runner.initialize("run-001", ["BTC/USD"])

        # Check subscription exists
        assert len(event_log._filtered_subscriptions) == 1
        sub = list(event_log._filtered_subscriptions.values())[0]
        assert DataEvents.WINDOW_READY in sub.event_types

    # -------------------------------------------------------------------------
    # Test 2: Runner receives WindowReady and calls strategy.on_data
    # -------------------------------------------------------------------------
    async def test_window_ready_calls_strategy_on_data(
        self,
        runner: StrategyRunner,
        strategy: DummyStrategy,
        event_log: InMemoryEventLog,
    ) -> None:
        """data.WindowReady event triggers strategy.on_data()."""
        await runner.initialize("run-001", ["BTC/USD"])

        # Emit WindowReady event
        await event_log.append(
            Envelope(
                type=DataEvents.WINDOW_READY,
                payload={"symbol": "BTC/USD", "bars": [{"close": "100"}]},
                run_id="run-001",
                producer="test",
            )
        )

        # Give event loop time to process async task
        await asyncio.sleep(0)

        # Strategy should have received the data
        assert len(strategy.received_data) == 1
        assert strategy.received_data[0]["symbol"] == "BTC/USD"

    # -------------------------------------------------------------------------
    # Test 3: Runner filters WindowReady by run_id
    # -------------------------------------------------------------------------
    async def test_filters_window_ready_by_run_id(
        self,
        runner: StrategyRunner,
        strategy: DummyStrategy,
        event_log: InMemoryEventLog,
    ) -> None:
        """Only receives data.WindowReady for own run_id."""
        await runner.initialize("run-001", ["BTC/USD"])

        # Event for different run
        await event_log.append(
            Envelope(
                type=DataEvents.WINDOW_READY,
                payload={"symbol": "BTC/USD", "bars": []},
                run_id="run-002",  # Different run!
                producer="test",
            )
        )

        # Should NOT call on_data
        assert len(strategy.received_data) == 0

    # -------------------------------------------------------------------------
    # Test 4: on_data result emits strategy.PlaceRequest
    # -------------------------------------------------------------------------
    async def test_on_data_emits_place_request(
        self,
        runner: StrategyRunner,
        strategy: DummyStrategy,
        event_log: InMemoryEventLog,
    ) -> None:
        """When strategy.on_data returns place_order, emit strategy.PlaceRequest."""
        strategy.data_actions = [
            StrategyAction(
                type="place_order",
                symbol="BTC/USD",
                side="buy",
                qty=Decimal("0.1"),
            )
        ]

        await runner.initialize("run-001", ["BTC/USD"])

        # Emit WindowReady
        await event_log.append(
            Envelope(
                type=DataEvents.WINDOW_READY,
                payload={"symbol": "BTC/USD", "bars": [{"close": "100"}]},
                run_id="run-001",
                producer="test",
            )
        )

        # Give event loop time to process async task
        await asyncio.sleep(0)

        # Check for PlaceRequest event
        events = await event_log.read_from(-1)
        place_requests = [e for _, e in events if e.type == StrategyEvents.PLACE_REQUEST]
        assert len(place_requests) == 1
        assert place_requests[0].payload["side"] == "buy"
        assert place_requests[0].payload["symbol"] == "BTC/USD"

    # -------------------------------------------------------------------------
    # Test 5: cleanup() unsubscribes from events
    # -------------------------------------------------------------------------
    async def test_cleanup_unsubscribes(
        self,
        runner: StrategyRunner,
        strategy: DummyStrategy,
        event_log: InMemoryEventLog,
    ) -> None:
        """cleanup() removes the WindowReady subscription."""
        await runner.initialize("run-001", ["BTC/USD"])
        assert len(event_log._filtered_subscriptions) == 1

        await runner.cleanup()

        # Subscription should be removed
        assert len(event_log._filtered_subscriptions) == 0

        # Events should not trigger on_data anymore
        await event_log.append(
            Envelope(
                type=DataEvents.WINDOW_READY,
                payload={"symbol": "BTC/USD", "bars": []},
                run_id="run-001",
                producer="test",
            )
        )

        # Give event loop time
        await asyncio.sleep(0)

        assert len(strategy.received_data) == 0

    # -------------------------------------------------------------------------
    # Test 6: Multiple WindowReady events are all delivered
    # -------------------------------------------------------------------------
    async def test_multiple_window_ready_events(
        self,
        runner: StrategyRunner,
        strategy: DummyStrategy,
        event_log: InMemoryEventLog,
    ) -> None:
        """Multiple WindowReady events are all delivered to strategy."""
        await runner.initialize("run-001", ["BTC/USD", "ETH/USD"])

        # Emit multiple events
        for symbol in ["BTC/USD", "ETH/USD"]:
            await event_log.append(
                Envelope(
                    type=DataEvents.WINDOW_READY,
                    payload={"symbol": symbol, "bars": []},
                    run_id="run-001",
                    producer="test",
                )
            )

        # Give event loop time to process async tasks
        await asyncio.sleep(0)

        assert len(strategy.received_data) == 2
        symbols = [d["symbol"] for d in strategy.received_data]
        assert "BTC/USD" in symbols
        assert "ETH/USD" in symbols

    # -------------------------------------------------------------------------
    # Test 7: on_tick emitting fetch_window creates strategy.FetchWindow event
    # -------------------------------------------------------------------------
    async def test_on_tick_emits_fetch_window_event(
        self,
        runner: StrategyRunner,
        strategy: DummyStrategy,
        event_log: InMemoryEventLog,
    ) -> None:
        """When strategy.on_tick returns fetch_window action, emit strategy.FetchWindow."""
        strategy.tick_actions = [
            StrategyAction(type="fetch_window", symbol="BTC/USD", lookback=20)
        ]

        await runner.initialize("run-001", ["BTC/USD"])
        await runner.on_tick(make_tick("run-001"))

        events = await event_log.read_from(-1)
        fetch_events = [e for _, e in events if e.type == StrategyEvents.FETCH_WINDOW]
        assert len(fetch_events) == 1
        assert fetch_events[0].payload["symbol"] == "BTC/USD"
        assert fetch_events[0].payload["lookback"] == 20

    # -------------------------------------------------------------------------
    # Test 8: Subscription ID is stored for cleanup
    # -------------------------------------------------------------------------
    async def test_subscription_id_stored(
        self, runner: StrategyRunner, event_log: InMemoryEventLog
    ) -> None:
        """Subscription ID is stored in runner for cleanup."""
        await runner.initialize("run-001", ["BTC/USD"])

        assert runner._subscription_id is not None
        assert runner._subscription_id in event_log._filtered_subscriptions

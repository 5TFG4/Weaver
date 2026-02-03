"""
Tests for GretaService Event Handling

TDD tests for M5-2: backtest.FetchWindow event handling.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.events.log import InMemoryEventLog
from src.events.protocol import Envelope
from src.events.types import BacktestEvents, DataEvents, OrderEvents
from src.greta.greta_service import GretaService
from src.walle.repositories.bar_repository import Bar


def make_bar(
    symbol: str = "BTC/USD",
    timestamp: datetime | None = None,
    close: Decimal = Decimal("100"),
) -> Bar:
    """Factory for test bars."""
    return Bar(
        symbol=symbol,
        timestamp=timestamp or datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        timeframe="1m",
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
        close=close,
        volume=Decimal("1000"),
    )


class TestGretaServiceEventSubscription:
    """Tests for GretaService event subscription behavior."""

    @pytest.fixture
    def event_log(self) -> InMemoryEventLog:
        """Create InMemoryEventLog for tests."""
        return InMemoryEventLog()

    @pytest.fixture
    def bar_repository(self) -> MagicMock:
        """Create mock bar repository."""
        repo = MagicMock()
        repo.get_bars = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def greta(
        self, event_log: InMemoryEventLog, bar_repository: MagicMock
    ) -> GretaService:
        """Create GretaService for tests."""
        return GretaService(
            run_id="run-001",
            bar_repository=bar_repository,
            event_log=event_log,
        )

    # -------------------------------------------------------------------------
    # Test 1: GretaService subscribes to backtest.FetchWindow on initialize
    # -------------------------------------------------------------------------
    async def test_initialize_subscribes_to_fetch_window(
        self, greta: GretaService, event_log: InMemoryEventLog
    ) -> None:
        """After initialize, greta subscribes to backtest.FetchWindow."""
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        # Check subscription exists
        assert len(event_log._filtered_subscriptions) == 1
        sub = list(event_log._filtered_subscriptions.values())[0]
        assert BacktestEvents.FETCH_WINDOW in sub.event_types

    # -------------------------------------------------------------------------
    # Test 2: FetchWindow triggers data.WindowReady
    # -------------------------------------------------------------------------
    async def test_fetch_window_emits_window_ready(
        self,
        greta: GretaService,
        event_log: InMemoryEventLog,
        bar_repository: MagicMock,
    ) -> None:
        """backtest.FetchWindow → emit data.WindowReady with bars."""
        # Setup bar cache
        bar = make_bar("BTC/USD")
        
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        # Manually add to cache for test
        greta._bar_cache["BTC/USD"] = {bar.timestamp: bar}

        # Emit FetchWindow event
        await event_log.append(
            Envelope(
                type=BacktestEvents.FETCH_WINDOW,
                payload={
                    "symbol": "BTC/USD",
                    "lookback": 10,
                    "as_of": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                },
                run_id="run-001",
                producer="test",
                corr_id="req-001",
            )
        )

        # Give event loop time to process async task
        await asyncio.sleep(0)

        # Should emit WindowReady
        events = await event_log.read_from(-1)
        window_ready = [e for _, e in events if e.type == DataEvents.WINDOW_READY]
        assert len(window_ready) == 1
        assert window_ready[0].payload["symbol"] == "BTC/USD"
        assert window_ready[0].corr_id == "req-001"

    # -------------------------------------------------------------------------
    # Test 3: FetchWindow filters by run_id
    # -------------------------------------------------------------------------
    async def test_filters_fetch_window_by_run_id(
        self,
        greta: GretaService,
        event_log: InMemoryEventLog,
    ) -> None:
        """Only handles backtest.FetchWindow for own run_id."""
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        events_before = len(await event_log.read_from(-1))

        # Event for different run
        await event_log.append(
            Envelope(
                type=BacktestEvents.FETCH_WINDOW,
                payload={"symbol": "BTC/USD", "lookback": 10},
                run_id="run-002",  # Different run!
                producer="test",
            )
        )

        # Should NOT emit WindowReady (only the original FetchWindow)
        events = await event_log.read_from(-1)
        window_ready = [e for _, e in events if e.type == DataEvents.WINDOW_READY]
        assert len(window_ready) == 0

    # -------------------------------------------------------------------------
    # Test 4: FetchWindow uses bar cache
    # -------------------------------------------------------------------------
    async def test_fetch_window_uses_bar_cache(
        self,
        greta: GretaService,
        event_log: InMemoryEventLog,
        bar_repository: MagicMock,
    ) -> None:
        """backtest.FetchWindow uses preloaded bar cache, not repository."""
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        # Add bars to cache
        bar = make_bar("BTC/USD")
        greta._bar_cache["BTC/USD"] = {bar.timestamp: bar}

        # Reset repository mock to track new calls
        bar_repository.get_bars.reset_mock()

        # Emit FetchWindow
        await event_log.append(
            Envelope(
                type=BacktestEvents.FETCH_WINDOW,
                payload={
                    "symbol": "BTC/USD",
                    "lookback": 1,
                    "as_of": bar.timestamp.isoformat(),
                },
                run_id="run-001",
                producer="test",
            )
        )

        # Should NOT call repository (used cache)
        bar_repository.get_bars.assert_not_called()

    # -------------------------------------------------------------------------
    # Test 5: WindowReady includes correct bars
    # -------------------------------------------------------------------------
    async def test_window_ready_includes_bars(
        self,
        greta: GretaService,
        event_log: InMemoryEventLog,
    ) -> None:
        """data.WindowReady payload includes requested bars."""
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        # Add multiple bars
        ts1 = datetime(2024, 1, 1, 9, 29, tzinfo=UTC)
        ts2 = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bar1 = make_bar("BTC/USD", ts1, Decimal("99"))
        bar2 = make_bar("BTC/USD", ts2, Decimal("100"))
        greta._bar_cache["BTC/USD"] = {ts1: bar1, ts2: bar2}

        # Emit FetchWindow with lookback=2
        await event_log.append(
            Envelope(
                type=BacktestEvents.FETCH_WINDOW,
                payload={
                    "symbol": "BTC/USD",
                    "lookback": 2,
                    "as_of": ts2.isoformat(),
                },
                run_id="run-001",
                producer="test",
            )
        )

        # Give event loop time to process
        await asyncio.sleep(0)

        events = await event_log.read_from(-1)
        window_ready = [e for _, e in events if e.type == DataEvents.WINDOW_READY]
        assert len(window_ready) == 1
        
        bars = window_ready[0].payload["bars"]
        assert len(bars) == 2

    # -------------------------------------------------------------------------
    # Test 6: Subscription ID stored for cleanup
    # -------------------------------------------------------------------------
    async def test_subscription_id_stored(
        self, greta: GretaService, event_log: InMemoryEventLog
    ) -> None:
        """Subscription ID is stored for cleanup."""
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        assert greta._subscription_id is not None
        assert greta._subscription_id in event_log._filtered_subscriptions

    # -------------------------------------------------------------------------
    # Test 7: Correlation ID preserved
    # -------------------------------------------------------------------------
    async def test_correlation_id_preserved(
        self,
        greta: GretaService,
        event_log: InMemoryEventLog,
    ) -> None:
        """WindowReady preserves correlation_id from FetchWindow."""
        await greta.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        bar = make_bar("BTC/USD")
        greta._bar_cache["BTC/USD"] = {bar.timestamp: bar}

        await event_log.append(
            Envelope(
                type=BacktestEvents.FETCH_WINDOW,
                payload={
                    "symbol": "BTC/USD",
                    "lookback": 1,
                    "as_of": bar.timestamp.isoformat(),
                },
                run_id="run-001",
                producer="test",
                corr_id="corr-12345",
            )
        )

        # Give event loop time to process
        await asyncio.sleep(0)

        events = await event_log.read_from(-1)
        window_ready = [e for _, e in events if e.type == DataEvents.WINDOW_READY]
        assert window_ready[0].corr_id == "corr-12345"

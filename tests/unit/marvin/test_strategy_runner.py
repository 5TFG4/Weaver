"""
Tests for StrategyRunner

Unit tests for the strategy execution runner.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio

from src.glados.clock.base import ClockTick
from src.marvin.base_strategy import ActionType, BaseStrategy, StrategyAction, StrategyOrderSide
from src.marvin.strategy_runner import StrategyRunner


def make_tick(
    timestamp: datetime | None = None,
    run_id: str = "test-run",
    timeframe: str = "1m",
    bar_index: int = 0,
) -> ClockTick:
    """Factory for test clock ticks."""
    return ClockTick(
        run_id=run_id,
        ts=timestamp or datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        timeframe=timeframe,
        bar_index=bar_index,
        is_backtest=True,
    )


class DummyStrategy(BaseStrategy):
    """Test strategy that returns configured actions."""

    def __init__(self, tick_actions: list[StrategyAction] | None = None) -> None:
        super().__init__()
        self.tick_actions = tick_actions or []
        self.data_actions: list[StrategyAction] = []
        self.received_ticks: list = []
        self.received_data: list = []

    async def on_tick(self, tick) -> list[StrategyAction]:
        self.received_ticks.append(tick)
        return self.tick_actions

    async def on_data(self, data: dict) -> list[StrategyAction]:
        self.received_data.append(data)
        return self.data_actions


class TestStrategyRunnerInit:
    """Tests for StrategyRunner initialization."""

    def test_requires_strategy(self) -> None:
        """StrategyRunner requires strategy at construction."""
        mock_event_log = MagicMock()
        strategy = DummyStrategy()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)

        assert runner._strategy is strategy

    def test_requires_event_log(self) -> None:
        """StrategyRunner requires event_log at construction."""
        strategy = DummyStrategy()
        mock_event_log = MagicMock()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)

        assert runner._event_log is mock_event_log

    def test_run_id_starts_none(self) -> None:
        """run_id is None before initialize()."""
        strategy = DummyStrategy()
        mock_event_log = MagicMock()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)

        assert runner.run_id is None


class TestStrategyRunnerInitialize:
    """Tests for StrategyRunner.initialize()."""

    @pytest_asyncio.fixture
    async def runner(self) -> StrategyRunner:
        """Create runner with mocked dependencies."""
        strategy = DummyStrategy()
        mock_event_log = AsyncMock()

        return StrategyRunner(strategy=strategy, event_log=mock_event_log)

    async def test_sets_run_id(self, runner: StrategyRunner) -> None:
        """initialize() sets run_id."""
        await runner.initialize(run_id="run-123", symbols=["BTC/USD"])

        assert runner.run_id == "run-123"

    async def test_stores_symbols(self, runner: StrategyRunner) -> None:
        """initialize() stores symbols."""
        await runner.initialize(run_id="run-123", symbols=["BTC/USD", "ETH/USD"])

        assert runner.symbols == ["BTC/USD", "ETH/USD"]

    async def test_calls_strategy_initialize(self, runner: StrategyRunner) -> None:
        """initialize() calls strategy.initialize()."""
        runner._strategy.initialize = AsyncMock()  # type: ignore

        await runner.initialize(run_id="run-123", symbols=["BTC/USD"])

        runner._strategy.initialize.assert_called_once_with(["BTC/USD"])


class TestStrategyRunnerOnTick:
    """Tests for StrategyRunner.on_tick()."""

    @pytest_asyncio.fixture
    async def initialized_runner(self) -> StrategyRunner:
        """Create initialized runner."""
        strategy = DummyStrategy(
            tick_actions=[
                StrategyAction(type=ActionType.FETCH_WINDOW, symbol="BTC/USD", lookback=10),
            ]
        )
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)
        await runner.initialize(run_id="run-123", symbols=["BTC/USD"])
        return runner

    async def test_passes_tick_to_strategy(
        self, initialized_runner: StrategyRunner
    ) -> None:
        """on_tick() passes tick to strategy."""
        tick = make_tick(timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC))

        await initialized_runner.on_tick(tick)

        strategy = cast(DummyStrategy, initialized_runner._strategy)
        assert tick in strategy.received_ticks

    async def test_emits_fetch_window_event(
        self, initialized_runner: StrategyRunner
    ) -> None:
        """on_tick() emits strategy.FetchWindow for fetch_window action."""
        tick = make_tick(timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC))

        await initialized_runner.on_tick(tick)

        event_log = cast(AsyncMock, initialized_runner._event_log)
        event_log.append.assert_called()
        call_args = event_log.append.call_args[0][0]
        assert call_args.type == "strategy.FetchWindow"
        assert call_args.run_id == "run-123"

    async def test_emits_place_request_event(self) -> None:
        """on_tick() emits strategy.PlaceRequest for place_order action."""
        strategy = DummyStrategy(
            tick_actions=[
                StrategyAction(
                    type=ActionType.PLACE_ORDER, symbol="BTC/USD", side=StrategyOrderSide.BUY, qty=Decimal("1")
                ),
            ]
        )
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)
        await runner.initialize(run_id="run-123", symbols=["BTC/USD"])

        tick = make_tick()
        await runner.on_tick(tick)

        mock_event_log.append.assert_called()
        call_args = mock_event_log.append.call_args[0][0]
        assert call_args.type == "strategy.PlaceRequest"

    async def test_handles_multiple_actions(self) -> None:
        """on_tick() handles multiple actions from strategy."""
        strategy = DummyStrategy(
            tick_actions=[
                StrategyAction(type=ActionType.FETCH_WINDOW, symbol="BTC/USD", lookback=10),
                StrategyAction(
                    type=ActionType.PLACE_ORDER, symbol="BTC/USD", side=StrategyOrderSide.BUY, qty=Decimal("1")
                ),
            ]
        )
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)
        await runner.initialize(run_id="run-123", symbols=["BTC/USD"])

        tick = make_tick()
        await runner.on_tick(tick)

        assert mock_event_log.append.call_count == 2


class TestStrategyRunnerOnDataReady:
    """Tests for StrategyRunner.on_data_ready()."""

    @pytest_asyncio.fixture
    async def initialized_runner(self) -> StrategyRunner:
        """Create initialized runner."""
        strategy = DummyStrategy()
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)
        await runner.initialize(run_id="run-123", symbols=["BTC/USD"])
        return runner

    async def test_passes_data_to_strategy(
        self, initialized_runner: StrategyRunner
    ) -> None:
        """on_data_ready() passes data payload to strategy."""
        envelope = MagicMock()
        envelope.payload = {"bars": []}

        await initialized_runner.on_data_ready(envelope)

        strategy = cast(DummyStrategy, initialized_runner._strategy)
        assert {"bars": []} in strategy.received_data

    async def test_emits_events_from_strategy_response(self) -> None:
        """on_data_ready() emits events from strategy's response."""
        strategy = DummyStrategy()
        strategy.data_actions = [
            StrategyAction(
                type=ActionType.PLACE_ORDER, symbol="BTC/USD", side=StrategyOrderSide.BUY, qty=Decimal("1")
            ),
        ]
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        runner = StrategyRunner(strategy=strategy, event_log=mock_event_log)
        await runner.initialize(run_id="run-123", symbols=["BTC/USD"])

        envelope = MagicMock()
        envelope.payload = {"bars": []}

        await runner.on_data_ready(envelope)

        mock_event_log.append.assert_called()
        call_args = mock_event_log.append.call_args[0][0]
        assert call_args.type == "strategy.PlaceRequest"

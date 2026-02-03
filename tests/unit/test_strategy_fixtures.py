"""
Tests for Test Strategy Fixtures

TDD tests for M5-5: Unified test strategy fixtures.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.glados.clock.base import ClockTick
from src.marvin.base_strategy import BaseStrategy, StrategyAction


def make_tick(run_id: str = "run-001") -> ClockTick:
    """Factory for test clock ticks."""
    return ClockTick(
        run_id=run_id,
        ts=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        timeframe="1m",
        bar_index=0,
        is_backtest=True,
    )


# =============================================================================
# DummyStrategy Tests
# =============================================================================


class TestDummyStrategy:
    """Tests for DummyStrategy fixture."""

    def test_is_base_strategy(self) -> None:
        """DummyStrategy should inherit from BaseStrategy."""
        from tests.fixtures.strategies import DummyStrategy

        strategy = DummyStrategy()
        assert isinstance(strategy, BaseStrategy)

    @pytest.mark.asyncio
    async def test_returns_configured_tick_actions(self) -> None:
        """DummyStrategy returns tick_actions when set."""
        from tests.fixtures.strategies import DummyStrategy

        strategy = DummyStrategy()
        strategy.tick_actions = [
            StrategyAction(type="fetch_window", symbol="BTC/USD", lookback=5)
        ]

        actions = await strategy.on_tick(make_tick())
        assert len(actions) == 1
        assert actions[0].type == "fetch_window"

    @pytest.mark.asyncio
    async def test_returns_configured_data_actions(self) -> None:
        """DummyStrategy returns data_actions when set."""
        from tests.fixtures.strategies import DummyStrategy

        strategy = DummyStrategy()
        strategy.data_actions = [
            StrategyAction(
                type="place_order",
                symbol="BTC/USD",
                side="buy",
                qty=Decimal("1.0"),
                order_type="market",
            )
        ]

        actions = await strategy.on_data({"bars": []})
        assert len(actions) == 1
        assert actions[0].type == "place_order"

    @pytest.mark.asyncio
    async def test_records_received_ticks(self) -> None:
        """DummyStrategy records ticks for assertions."""
        from tests.fixtures.strategies import DummyStrategy

        strategy = DummyStrategy()
        tick = make_tick()
        await strategy.on_tick(tick)

        assert len(strategy.received_ticks) == 1
        assert strategy.received_ticks[0] == tick

    @pytest.mark.asyncio
    async def test_records_received_data(self) -> None:
        """DummyStrategy records data for assertions."""
        from tests.fixtures.strategies import DummyStrategy

        strategy = DummyStrategy()
        data = {"bars": [{"close": Decimal("100")}]}
        await strategy.on_data(data)

        assert len(strategy.received_data) == 1
        assert strategy.received_data[0] == data


# =============================================================================
# SimpleTestStrategy Tests
# =============================================================================


class TestSimpleTestStrategy:
    """Tests for SimpleTestStrategy fixture."""

    def test_is_base_strategy(self) -> None:
        """SimpleTestStrategy should inherit from BaseStrategy."""
        from tests.fixtures.strategies import SimpleTestStrategy

        strategy = SimpleTestStrategy()
        assert isinstance(strategy, BaseStrategy)

    @pytest.mark.asyncio
    async def test_on_tick_returns_fetch_window(self) -> None:
        """SimpleTestStrategy requests data on tick."""
        from tests.fixtures.strategies import SimpleTestStrategy

        strategy = SimpleTestStrategy()
        await strategy.initialize(["BTC/USD"])

        actions = await strategy.on_tick(make_tick())
        assert len(actions) == 1
        assert actions[0].type == "fetch_window"


# =============================================================================
# MockStrategyLoader Tests
# =============================================================================


class TestMockStrategyLoader:
    """Tests for MockStrategyLoader fixture."""

    def test_returns_configured_strategy(self) -> None:
        """MockStrategyLoader returns the strategy it was given."""
        from tests.fixtures.strategies import DummyStrategy, MockStrategyLoader

        dummy = DummyStrategy()
        loader = MockStrategyLoader(strategy=dummy)

        loaded = loader.load("any-id")
        assert loaded is dummy

    def test_default_returns_simple_test_strategy(self) -> None:
        """MockStrategyLoader defaults to SimpleTestStrategy."""
        from tests.fixtures.strategies import MockStrategyLoader, SimpleTestStrategy

        loader = MockStrategyLoader()
        loaded = loader.load("any-id")

        assert isinstance(loaded, SimpleTestStrategy)

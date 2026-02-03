"""
Tests for SampleStrategy

Unit tests for the simple sample strategy.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest_asyncio

from src.glados.clock.base import ClockTick
from src.marvin.sample_strategy import SampleStrategy
from src.marvin.base_strategy import StrategyAction
from src.walle.repositories.bar_repository import Bar


def make_bar(
    timestamp: datetime | None = None,
    close: Decimal = Decimal("42000.00"),
) -> Bar:
    """Factory for test bars."""
    return Bar(
        symbol="BTC/USD",
        timeframe="1m",
        timestamp=timestamp or datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        open=close,
        high=close + Decimal("100"),
        low=close - Decimal("100"),
        close=close,
        volume=Decimal("100.00"),
    )


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


class TestSampleStrategyInit:
    """Tests for SampleStrategy initialization."""

    def test_creates_without_error(self) -> None:
        """SampleStrategy can be instantiated."""
        strategy = SampleStrategy()
        assert strategy is not None

    def test_no_position_initially(self) -> None:
        """SampleStrategy starts with no position."""
        strategy = SampleStrategy()
        assert strategy.has_position is False


class TestSampleStrategyOnTick:
    """Tests for SampleStrategy.on_tick()."""

    @pytest_asyncio.fixture
    async def strategy(self) -> SampleStrategy:
        """Create initialized strategy."""
        s = SampleStrategy()
        await s.initialize(["BTC/USD"])
        return s

    async def test_requests_data_window(self, strategy: SampleStrategy) -> None:
        """on_tick() always requests data window."""
        tick = make_tick(timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC))

        actions = await strategy.on_tick(tick)

        assert len(actions) == 1
        assert actions[0].type == "fetch_window"
        assert actions[0].symbol == "BTC/USD"

    async def test_requests_configured_lookback(self, strategy: SampleStrategy) -> None:
        """on_tick() uses configured lookback."""
        tick = make_tick(timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC))

        actions = await strategy.on_tick(tick)

        assert actions[0].lookback == 10  # default lookback


class TestSampleStrategyOnData:
    """Tests for SampleStrategy.on_data()."""

    @pytest_asyncio.fixture
    async def strategy(self) -> SampleStrategy:
        """Create initialized strategy."""
        s = SampleStrategy()
        await s.initialize(["BTC/USD"])
        return s

    async def test_no_action_with_insufficient_bars(
        self, strategy: SampleStrategy
    ) -> None:
        """Returns no action with fewer than 2 bars."""
        data = {"bars": [make_bar()]}

        actions = await strategy.on_data(data)

        assert len(actions) == 0

    async def test_buys_when_price_below_average(
        self, strategy: SampleStrategy
    ) -> None:
        """Buys when current price < 99% of average."""
        # Average of 42000 and 40000 = 41000
        # Current at 40000 is < 41000 * 0.99 = 40590
        bars = [
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                close=Decimal("42000"),
            ),
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 31, tzinfo=UTC),
                close=Decimal("40000"),
            ),
        ]
        data = {"bars": bars}

        actions = await strategy.on_data(data)

        assert len(actions) == 1
        assert actions[0].type == "place_order"
        assert actions[0].side == "buy"

    async def test_no_buy_when_already_has_position(
        self, strategy: SampleStrategy
    ) -> None:
        """Does not buy when already has position."""
        strategy._has_position = True
        bars = [
            make_bar(close=Decimal("42000")),
            make_bar(close=Decimal("40000")),
        ]
        data = {"bars": bars}

        actions = await strategy.on_data(data)

        assert len(actions) == 0

    async def test_sells_when_price_above_average(
        self, strategy: SampleStrategy
    ) -> None:
        """Sells when current price > 101% of average and has position."""
        strategy._has_position = True
        # Average of 40000 and 42000 = 41000
        # Current at 42000 is > 41000 * 1.01 = 41410
        bars = [
            make_bar(close=Decimal("40000")),
            make_bar(close=Decimal("42000")),
        ]
        data = {"bars": bars}

        actions = await strategy.on_data(data)

        assert len(actions) == 1
        assert actions[0].type == "place_order"
        assert actions[0].side == "sell"

    async def test_no_sell_when_no_position(self, strategy: SampleStrategy) -> None:
        """Does not sell when no position."""
        bars = [
            make_bar(close=Decimal("40000")),
            make_bar(close=Decimal("42000")),
        ]
        data = {"bars": bars}

        actions = await strategy.on_data(data)

        # No position, so no sell
        assert len(actions) == 0

    async def test_no_action_when_price_in_range(
        self, strategy: SampleStrategy
    ) -> None:
        """No action when price within 1% of average."""
        # Average close to current
        bars = [
            make_bar(close=Decimal("42000")),
            make_bar(close=Decimal("42050")),
        ]
        data = {"bars": bars}

        actions = await strategy.on_data(data)

        assert len(actions) == 0

"""
Tests for SMA Crossover Strategy

TDD tests for M5-3: SMA crossover strategy implementation.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.glados.clock.base import ClockTick
from src.marvin.base_strategy import StrategyAction


def make_tick(run_id: str = "run-001") -> ClockTick:
    """Factory for test clock ticks."""
    return ClockTick(
        run_id=run_id,
        ts=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        timeframe="1m",
        bar_index=0,
        is_backtest=True,
    )


def make_bars(closes: list[Decimal | int | float], symbol: str = "BTC/USD") -> list[dict]:
    """Create bar dicts from close prices."""
    return [
        {
            "timestamp": datetime(2024, 1, 1, 9, i, tzinfo=UTC).isoformat(),
            "symbol": symbol,
            "open": str(c),
            "high": str(c + 1),
            "low": str(c - 1),
            "close": str(c),
            "volume": "1000",
        }
        for i, c in enumerate(closes)
    ]


class TestSMAConfig:
    """Tests for SMAConfig dataclass."""

    def test_default_config_values(self) -> None:
        """SMAConfig has sensible defaults."""
        from src.marvin.strategies.sma_strategy import SMAConfig

        config = SMAConfig()

        assert config.fast_period == 5
        assert config.slow_period == 20
        assert config.qty == Decimal("1.0")

    def test_custom_config_values(self) -> None:
        """SMAConfig accepts custom values."""
        from src.marvin.strategies.sma_strategy import SMAConfig

        config = SMAConfig(fast_period=10, slow_period=50, qty=Decimal("2.5"))

        assert config.fast_period == 10
        assert config.slow_period == 50
        assert config.qty == Decimal("2.5")

    def test_config_validation_fast_less_than_slow(self) -> None:
        """Fast period must be less than slow period."""
        from src.marvin.strategies.sma_strategy import SMAConfig

        with pytest.raises(ValueError, match="fast_period must be less than slow_period"):
            SMAConfig(fast_period=20, slow_period=10)


class TestSMAStrategy:
    """Tests for SMA crossover strategy."""

    @pytest.fixture
    def strategy(self):
        """Create default SMA strategy."""
        from src.marvin.strategies.sma_strategy import SMAConfig, SMAStrategy

        return SMAStrategy(SMAConfig(fast_period=5, slow_period=10, qty=Decimal("1.0")))

    # -------------------------------------------------------------------------
    # Test 1: on_tick returns fetch_window action
    # -------------------------------------------------------------------------
    async def test_on_tick_returns_fetch_window_action(self, strategy) -> None:
        """on_tick returns fetch_window action with correct lookback."""
        await strategy.initialize(["BTC/USD"])
        actions = await strategy.on_tick(make_tick())

        assert len(actions) == 1
        assert actions[0].type == "fetch_window"
        assert actions[0].symbol == "BTC/USD"
        assert actions[0].lookback == 11  # slow_period + 1

    # -------------------------------------------------------------------------
    # Test 2: SMA calculation
    # -------------------------------------------------------------------------
    def test_calculate_sma_correctly(self, strategy) -> None:
        """SMA calculation is mathematically correct."""
        values = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40"), Decimal("50")]
        sma = strategy._calculate_sma(values, period=5)

        assert sma == Decimal("30")

    def test_calculate_sma_with_partial_data(self, strategy) -> None:
        """SMA uses available data if less than period."""
        values = [Decimal("10"), Decimal("20"), Decimal("30")]
        sma = strategy._calculate_sma(values, period=5)

        assert sma == Decimal("20")  # (10+20+30)/3

    # -------------------------------------------------------------------------
    # Test 3: Bullish crossover generates buy
    # -------------------------------------------------------------------------
    async def test_bullish_crossover_generates_buy(self, strategy) -> None:
        """Fast crossing above slow generates buy signal."""
        await strategy.initialize(["BTC/USD"])

        # First call: establish baseline where fast < slow
        # Prices: 10,11,12,13,14,15,16,17,18,19 (10 bars)
        # Fast SMA (last 5): (15+16+17+18+19)/5 = 17
        # Slow SMA (last 10): (10+11+12+13+14+15+16+17+18+19)/10 = 14.5
        # Fast > Slow, but no previous state, so no signal
        bars1 = make_bars([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        # Second call: establish fast < slow
        # Prices dropping: Fast=7, Slow=12 roughly
        bars2 = make_bars([10, 11, 12, 13, 14, 5, 6, 7, 8, 9])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        # Third call: bullish crossover (fast rises above slow)
        bars3 = make_bars([5, 6, 7, 8, 9, 20, 21, 22, 23, 24])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars3})

        assert len(actions) == 1
        assert actions[0].type == "place_order"
        assert actions[0].side == "buy"
        assert actions[0].symbol == "BTC/USD"
        assert actions[0].qty == Decimal("1.0")

    # -------------------------------------------------------------------------
    # Test 4: Bearish crossover generates sell
    # -------------------------------------------------------------------------
    async def test_bearish_crossover_generates_sell(self, strategy) -> None:
        """Fast crossing below slow generates sell signal when has position."""
        await strategy.initialize(["BTC/USD"])
        strategy._has_position = True  # Already have position

        # First: establish fast > slow
        bars1 = make_bars([10, 11, 12, 13, 14, 20, 21, 22, 23, 24])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        # Second: bearish crossover (fast drops below slow)
        bars2 = make_bars([20, 21, 22, 23, 24, 5, 6, 7, 8, 9])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        assert len(actions) == 1
        assert actions[0].type == "place_order"
        assert actions[0].side == "sell"

    # -------------------------------------------------------------------------
    # Test 5: No signal without crossover
    # -------------------------------------------------------------------------
    async def test_no_signal_without_crossover(self, strategy) -> None:
        """No signal when SMAs don't cross."""
        await strategy.initialize(["BTC/USD"])

        # Fast consistently > slow (no cross)
        bars = make_bars([10, 10, 10, 10, 10, 20, 20, 20, 20, 20])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars})
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars})

        assert len(actions) == 0

    # -------------------------------------------------------------------------
    # Test 6: Insufficient data no signal
    # -------------------------------------------------------------------------
    async def test_insufficient_data_no_signal(self, strategy) -> None:
        """No signal when bars < slow_period."""
        await strategy.initialize(["BTC/USD"])

        bars = make_bars([10, 20, 30])  # Only 3 bars
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars})

        assert len(actions) == 0

    # -------------------------------------------------------------------------
    # Test 7: Custom parameters respected
    # -------------------------------------------------------------------------
    async def test_custom_parameters_respected(self) -> None:
        """Strategy respects custom period/qty config."""
        from src.marvin.strategies.sma_strategy import SMAConfig, SMAStrategy

        config = SMAConfig(fast_period=3, slow_period=7, qty=Decimal("2.5"))
        strategy = SMAStrategy(config)
        await strategy.initialize(["ETH/USD"])

        actions = await strategy.on_tick(make_tick())
        assert actions[0].lookback == 8  # slow_period + 1
        assert actions[0].symbol == "ETH/USD"

    # -------------------------------------------------------------------------
    # Test 8: Only buys when no position
    # -------------------------------------------------------------------------
    async def test_only_buys_when_no_position(self, strategy) -> None:
        """Buy signal ignored if already has position."""
        await strategy.initialize(["BTC/USD"])
        strategy._has_position = True  # Already in

        # Establish fast < slow
        bars1 = make_bars([10, 11, 12, 13, 14, 5, 6, 7, 8, 9])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        # Bullish crossover
        bars2 = make_bars([5, 6, 7, 8, 9, 20, 21, 22, 23, 24])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        # Should NOT generate buy because already has position
        assert len(actions) == 0

    # -------------------------------------------------------------------------
    # Test 9: Only sells when has position
    # -------------------------------------------------------------------------
    async def test_only_sells_when_has_position(self, strategy) -> None:
        """Sell signal ignored if no position."""
        await strategy.initialize(["BTC/USD"])
        strategy._has_position = False  # No position

        # Establish fast > slow
        bars1 = make_bars([10, 11, 12, 13, 14, 20, 21, 22, 23, 24])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        # Bearish crossover
        bars2 = make_bars([20, 21, 22, 23, 24, 5, 6, 7, 8, 9])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        # Should NOT generate sell because no position
        assert len(actions) == 0

    # -------------------------------------------------------------------------
    # Test 10: First data no signal
    # -------------------------------------------------------------------------
    async def test_first_data_no_signal(self, strategy) -> None:
        """First on_data never generates signal (need previous for crossover)."""
        await strategy.initialize(["BTC/USD"])

        # Even with valid data, first call can't detect crossover
        bars = make_bars([10, 11, 12, 13, 14, 20, 21, 22, 23, 24])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars})

        assert len(actions) == 0

    # -------------------------------------------------------------------------
    # Test 11: Empty bars no error
    # -------------------------------------------------------------------------
    async def test_empty_bars_no_error(self, strategy) -> None:
        """Empty bars list doesn't raise error."""
        await strategy.initialize(["BTC/USD"])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": []})

        assert actions == []

    # -------------------------------------------------------------------------
    # Test 12: Position updated after trade
    # -------------------------------------------------------------------------
    async def test_position_updated_after_buy(self, strategy) -> None:
        """_has_position is True after generating buy signal."""
        await strategy.initialize(["BTC/USD"])

        # Establish fast < slow
        bars1 = make_bars([10, 11, 12, 13, 14, 5, 6, 7, 8, 9])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        assert strategy._has_position is False

        # Bullish crossover
        bars2 = make_bars([5, 6, 7, 8, 9, 20, 21, 22, 23, 24])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        assert strategy._has_position is True

    async def test_position_updated_after_sell(self, strategy) -> None:
        """_has_position is False after generating sell signal."""
        await strategy.initialize(["BTC/USD"])
        strategy._has_position = True

        # Establish fast > slow
        bars1 = make_bars([10, 11, 12, 13, 14, 20, 21, 22, 23, 24])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        # Bearish crossover
        bars2 = make_bars([20, 21, 22, 23, 24, 5, 6, 7, 8, 9])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        assert strategy._has_position is False

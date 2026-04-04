"""
Tests for SMA Crossover Strategy

TDD tests for M5-3: SMA crossover strategy implementation.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.glados.clock.base import ClockTick


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


class TestSMAStrategyInitialize:
    """Tests for SMAStrategy.initialize() reading config params."""

    async def test_initialize_reads_config_params(self) -> None:
        from src.marvin.strategies.sma_strategy import SMAStrategy

        strategy = SMAStrategy()
        await strategy.initialize(
            {
                "symbols": ["BTC/USD"],
                "fast_period": 8,
                "slow_period": 30,
                "qty": 2.5,
            }
        )
        assert strategy._sma_config.fast_period == 8
        assert strategy._sma_config.slow_period == 30
        assert strategy._sma_config.qty == Decimal("2.5")

    async def test_initialize_uses_defaults_when_no_params(self) -> None:
        from src.marvin.strategies.sma_strategy import SMAStrategy

        strategy = SMAStrategy()
        await strategy.initialize({"symbols": ["BTC/USD"]})
        assert strategy._sma_config.fast_period == 5
        assert strategy._sma_config.slow_period == 20
        assert strategy._sma_config.qty == Decimal("1.0")


class TestSMAStrategy:
    """Tests for SMA crossover strategy."""

    @pytest.fixture
    def strategy(self):
        """Create default SMA strategy (not yet initialized)."""
        from src.marvin.strategies.sma_strategy import SMAStrategy

        return SMAStrategy()

    @pytest.fixture
    def sma_config(self) -> dict:
        """Standard SMA config used across tests."""
        return {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}

    # -------------------------------------------------------------------------
    # Test 1: on_tick returns fetch_window action
    # -------------------------------------------------------------------------
    async def test_on_tick_returns_fetch_window_action(self, strategy) -> None:
        """on_tick returns fetch_window action with correct lookback."""
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )
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
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )

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
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )
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
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )

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
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )

        bars = make_bars([10, 20, 30])  # Only 3 bars
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars})

        assert len(actions) == 0

    # -------------------------------------------------------------------------
    # Test 7: Custom parameters respected
    # -------------------------------------------------------------------------
    async def test_custom_parameters_respected(self) -> None:
        """Strategy respects custom period/qty config."""
        from src.marvin.strategies.sma_strategy import SMAStrategy

        strategy = SMAStrategy()
        await strategy.initialize(
            {"symbols": ["ETH/USD"], "fast_period": 3, "slow_period": 7, "qty": 2.5}
        )

        actions = await strategy.on_tick(make_tick())
        assert actions[0].lookback == 8  # slow_period + 1
        assert actions[0].symbol == "ETH/USD"

    # -------------------------------------------------------------------------
    # Test 8: Only buys when no position
    # -------------------------------------------------------------------------
    async def test_only_buys_when_no_position(self, strategy) -> None:
        """Buy signal ignored if already has position."""
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )
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
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )
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
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )

        # Even with valid data, first call can't detect crossover
        bars = make_bars([10, 11, 12, 13, 14, 20, 21, 22, 23, 24])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars})

        assert len(actions) == 0

    # -------------------------------------------------------------------------
    # Test 11: Empty bars no error
    # -------------------------------------------------------------------------
    async def test_empty_bars_no_error(self, strategy) -> None:
        """Empty bars list doesn't raise error."""
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": []})

        assert actions == []

    # -------------------------------------------------------------------------
    # Test 12: Position updated after trade
    # -------------------------------------------------------------------------
    async def test_position_updated_after_buy(self, strategy) -> None:
        """_has_position is True after generating buy signal."""
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )

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
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )
        strategy._has_position = True

        # Establish fast > slow
        bars1 = make_bars([10, 11, 12, 13, 14, 20, 21, 22, 23, 24])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        # Bearish crossover
        bars2 = make_bars([20, 21, 22, 23, 24, 5, 6, 7, 8, 9])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        assert strategy._has_position is False


class TestSMABarDataclassSupport:
    """Regression: SMA strategy must handle Bar dataclass objects, not just dicts."""

    @pytest.fixture
    def strategy(self):
        from src.marvin.strategies.sma_strategy import SMAStrategy

        return SMAStrategy()

    def _make_bar_objects(self, closes: list[Decimal | int | float], symbol: str = "BTC/USD"):
        """Create Bar dataclass instances (as strategy_runner.on_data_ready produces)."""
        from src.walle.repositories.bar_repository import Bar

        return [
            Bar(
                symbol=symbol,
                timeframe="",
                timestamp=datetime(2024, 1, 1, 9, i, tzinfo=UTC),
                open=Decimal(str(c)),
                high=Decimal(str(c)) + 1,
                low=Decimal(str(c)) - 1,
                close=Decimal(str(c)),
                volume=Decimal("1000"),
            )
            for i, c in enumerate(closes)
        ]

    async def test_on_data_with_bar_dataclass_no_error(self, strategy) -> None:
        """on_data does not raise AttributeError when bars are Bar dataclasses."""
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )

        bars = self._make_bar_objects([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars})

        # First call: no crossover, just no error
        assert isinstance(actions, list)

    async def test_crossover_with_bar_dataclass(self, strategy) -> None:
        """SMA crossover detection works with Bar dataclass objects."""
        await strategy.initialize(
            {"symbols": ["BTC/USD"], "fast_period": 5, "slow_period": 10, "qty": 1.0}
        )

        # Establish fast > slow
        bars1 = self._make_bar_objects([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars1})

        # Establish fast < slow
        bars2 = self._make_bar_objects([10, 11, 12, 13, 14, 5, 6, 7, 8, 9])
        await strategy.on_data({"symbol": "BTC/USD", "bars": bars2})

        # Bullish crossover
        bars3 = self._make_bar_objects([5, 6, 7, 8, 9, 20, 21, 22, 23, 24])
        actions = await strategy.on_data({"symbol": "BTC/USD", "bars": bars3})

        assert len(actions) == 1
        assert actions[0].type == "place_order"
        assert actions[0].side == "buy"

    def test_extract_closes_from_bar_objects(self, strategy) -> None:
        """_extract_closes works with Bar dataclass objects."""
        bars = self._make_bar_objects([Decimal("100"), Decimal("200"), Decimal("300")])
        closes = strategy._extract_closes(bars)

        assert closes == [Decimal("100"), Decimal("200"), Decimal("300")]

    def test_extract_closes_from_dicts(self, strategy) -> None:
        """_extract_closes still works with dict bars (backtest path)."""
        bars = make_bars([100, 200, 300])
        closes = strategy._extract_closes(bars)

        assert closes == [Decimal("100"), Decimal("200"), Decimal("300")]


class TestSMAStrategyConfigSchema:
    """H2: Validate config_schema has enum on symbols.items for dropdown rendering."""

    def test_symbols_items_has_enum(self) -> None:
        from src.marvin.strategies.sma_strategy import STRATEGY_META

        schema = STRATEGY_META["config_schema"]
        items = schema["properties"]["symbols"]["items"]
        assert "enum" in items, "symbols.items must have enum for RJSF dropdown"
        assert isinstance(items["enum"], list)
        assert len(items["enum"]) >= 3

    def test_symbols_enum_contains_expected_tickers(self) -> None:
        from src.marvin.strategies.sma_strategy import STRATEGY_META

        enum = STRATEGY_META["config_schema"]["properties"]["symbols"]["items"]["enum"]
        for ticker in ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"]:
            assert ticker in enum, f"{ticker} missing from symbols enum"

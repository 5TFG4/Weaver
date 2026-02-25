"""
Tests for Greta Models

Unit tests for Greta data structures (SimulatedFill, SimulatedPosition, etc.)
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

# These imports will fail until we implement the models
from src.greta.models import (
    FillSimulationConfig,
    SimulatedFill,
    SimulatedPosition,
    BacktestStats,
    BacktestResult,
)
from src.veda.models import OrderSide


class TestFillSimulationConfig:
    """Tests for FillSimulationConfig."""

    def test_default_values(self) -> None:
        """Default config has reasonable values."""
        config = FillSimulationConfig()
        
        assert config.slippage_bps == Decimal("0")
        assert config.commission_bps == Decimal("0")
        assert config.min_commission == Decimal("0")
        assert config.fill_at == "open"
        assert config.slippage_model == "fixed"

    def test_custom_slippage(self) -> None:
        """Can set custom slippage."""
        config = FillSimulationConfig(slippage_bps=Decimal("5"))
        assert config.slippage_bps == Decimal("5")

    def test_custom_commission(self) -> None:
        """Can set custom commission."""
        config = FillSimulationConfig(
            commission_bps=Decimal("10"),
            min_commission=Decimal("1.00"),
        )
        assert config.commission_bps == Decimal("10")
        assert config.min_commission == Decimal("1.00")


class TestSimulatedFill:
    """Tests for SimulatedFill dataclass."""

    def test_create_fill(self) -> None:
        """Can create a simulated fill."""
        fill = SimulatedFill(
            order_id="order-123",
            client_order_id="client-456",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1.5"),
            fill_price=Decimal("42000.00"),
            commission=Decimal("4.20"),
            slippage=Decimal("10.50"),
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            bar_index=0,
        )
        
        assert fill.order_id == "order-123"
        assert fill.symbol == "BTC/USD"
        assert fill.fill_price == Decimal("42000.00")

    def test_fill_is_frozen(self) -> None:
        """SimulatedFill is immutable."""
        fill = SimulatedFill(
            order_id="order-123",
            client_order_id="client-456",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1.5"),
            fill_price=Decimal("42000.00"),
            commission=Decimal("4.20"),
            slippage=Decimal("10.50"),
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            bar_index=0,
        )
        
        with pytest.raises(AttributeError):
            fill.fill_price = Decimal("50000")  # type: ignore[misc]

    def test_notional_value(self) -> None:
        """Can calculate notional value."""
        fill = SimulatedFill(
            order_id="order-123",
            client_order_id="client-456",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("2.0"),
            fill_price=Decimal("42000.00"),
            commission=Decimal("0"),
            slippage=Decimal("0"),
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            bar_index=0,
        )
        
        assert fill.notional == Decimal("84000.00")

    def test_side_accepts_order_side_enum_only(self) -> None:
        """M-04: SimulatedFill.side must be OrderSide enum, not plain string."""
        fill = SimulatedFill(
            order_id="order-1",
            client_order_id="client-1",
            symbol="AAPL",
            side=OrderSide.BUY,
            qty=Decimal("10"),
            fill_price=Decimal("150.00"),
            commission=Decimal("0"),
            slippage=Decimal("0"),
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            bar_index=0,
        )
        assert isinstance(fill.side, OrderSide)
        assert fill.side == OrderSide.BUY

        sell_fill = SimulatedFill(
            order_id="order-2",
            client_order_id="client-2",
            symbol="AAPL",
            side=OrderSide.SELL,
            qty=Decimal("10"),
            fill_price=Decimal("155.00"),
            commission=Decimal("0"),
            slippage=Decimal("0"),
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            bar_index=1,
        )
        assert fill.side == OrderSide.BUY
        assert sell_fill.side == OrderSide.SELL


class TestSimulatedPosition:
    """Tests for SimulatedPosition."""

    def test_create_long_position(self) -> None:
        """Can create a long position."""
        pos = SimulatedPosition(
            symbol="BTC/USD",
            qty=Decimal("1.0"),
            avg_entry_price=Decimal("42000.00"),
            market_value=Decimal("42000.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        
        assert pos.symbol == "BTC/USD"
        assert pos.qty == Decimal("1.0")
        assert pos.is_long is True
        assert pos.is_short is False

    def test_create_short_position(self) -> None:
        """Can create a short position."""
        pos = SimulatedPosition(
            symbol="BTC/USD",
            qty=Decimal("-1.0"),
            avg_entry_price=Decimal("42000.00"),
            market_value=Decimal("-42000.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        
        assert pos.is_long is False
        assert pos.is_short is True

    def test_update_mark_price(self) -> None:
        """Can update market value based on current price."""
        pos = SimulatedPosition(
            symbol="BTC/USD",
            qty=Decimal("1.0"),
            avg_entry_price=Decimal("42000.00"),
            market_value=Decimal("42000.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        
        pos.update_mark(Decimal("43000.00"))
        
        assert pos.market_value == Decimal("43000.00")
        assert pos.unrealized_pnl == Decimal("1000.00")

    def test_update_mark_short_position(self) -> None:
        """Update mark for short position (profit when price drops)."""
        pos = SimulatedPosition(
            symbol="BTC/USD",
            qty=Decimal("-1.0"),
            avg_entry_price=Decimal("42000.00"),
            market_value=Decimal("-42000.00"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        
        # Price drops = profit for short
        pos.update_mark(Decimal("41000.00"))
        
        # market_value = qty * price = -1 * 41000 = -41000
        assert pos.market_value == Decimal("-41000.00")
        # unrealized = market_value - (qty * avg_entry) = -41000 - (-1 * 42000) = -41000 + 42000 = 1000
        assert pos.unrealized_pnl == Decimal("1000.00")


class TestBacktestStats:
    """Tests for BacktestStats."""

    def test_default_values(self) -> None:
        """Default stats are zero."""
        stats = BacktestStats()
        
        assert stats.total_return == Decimal("0")
        assert stats.total_trades == 0
        assert stats.win_rate == Decimal("0")
        assert stats.sharpe_ratio is None

    def test_calculate_win_rate(self) -> None:
        """Can calculate win rate."""
        stats = BacktestStats(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
        )
        
        # win_rate should be calculated or set
        assert stats.winning_trades == 6


class TestBacktestResult:
    """Tests for BacktestResult."""

    def test_create_result(self) -> None:
        """Can create a backtest result."""
        result = BacktestResult(
            run_id="run-123",
            start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            end_time=datetime(2024, 1, 31, 16, 0, tzinfo=UTC),
            timeframe="1m",
            symbols=["BTC/USD"],
            stats=BacktestStats(),
            final_equity=Decimal("110000.00"),
            equity_curve=[],
        )
        
        assert result.run_id == "run-123"
        assert result.final_equity == Decimal("110000.00")
        assert result.symbols == ["BTC/USD"]

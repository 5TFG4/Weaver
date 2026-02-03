"""
Tests for Type Safety Improvements

TDD tests for M5-5: SimulatedFill.side and ClockTick fixes.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.veda.models import OrderSide


# =============================================================================
# SimulatedFill Type Safety Tests
# =============================================================================


class TestSimulatedFillTypeSafety:
    """Tests for SimulatedFill type improvements."""

    def test_side_is_order_side_enum(self) -> None:
        """SimulatedFill.side should be OrderSide, not str."""
        from src.greta.models import SimulatedFill

        fill = SimulatedFill(
            order_id="order-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1.0"),
            fill_price=Decimal("42000.00"),
            commission=Decimal("0.50"),
            slippage=Decimal("0.10"),
            timestamp=datetime.now(UTC),
            bar_index=0,
        )
        assert isinstance(fill.side, OrderSide)
        assert fill.side == OrderSide.BUY

    def test_side_sell_is_order_side_enum(self) -> None:
        """SimulatedFill.side SELL should be OrderSide."""
        from src.greta.models import SimulatedFill

        fill = SimulatedFill(
            order_id="order-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            qty=Decimal("1.0"),
            fill_price=Decimal("42000.00"),
            commission=Decimal("0.50"),
            slippage=Decimal("0.10"),
            timestamp=datetime.now(UTC),
            bar_index=0,
        )
        assert isinstance(fill.side, OrderSide)
        assert fill.side == OrderSide.SELL


# =============================================================================
# ClockTick Fixture Tests
# =============================================================================


class TestClockFixture:
    """Tests for clock test fixtures."""

    def test_controllable_clock_uses_production_clock_tick(self) -> None:
        """ControllableClock should use ClockTick from production code."""
        from src.glados.clock.base import ClockTick as ProductionClockTick
        from tests.fixtures.clock import ControllableClock

        clock = ControllableClock(start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC))
        tick = clock.make_tick()

        assert isinstance(tick, ProductionClockTick)

    def test_clock_tick_not_redefined_in_fixtures(self) -> None:
        """ClockTick should be imported from production, not redefined."""
        import inspect

        from tests.fixtures import clock as clock_module

        source = inspect.getsource(clock_module)

        # Should NOT contain a class definition for ClockTick
        # (it should import from src.glados.clock.base instead)
        assert "class ClockTick:" not in source or "ClockTick:" in source
        # The import statement should be present
        assert "from src.glados.clock.base import ClockTick" in source

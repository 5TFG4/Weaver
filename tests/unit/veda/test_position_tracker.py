"""
Unit tests for PositionTracker

MVP-5: Position Tracker
- Tracks positions from fills
- Provides real-time position view
- Calculates P&L
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.veda.models import (
    Fill,
    OrderSide,
    Position,
    PositionSide,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_fill_buy() -> Fill:
    """Create a sample buy fill."""
    return Fill(
        id=str(uuid4()),
        order_id=str(uuid4()),
        qty=Decimal("1.0"),
        price=Decimal("42000.00"),
        commission=Decimal("10.00"),
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_fill_sell() -> Fill:
    """Create a sample sell fill."""
    return Fill(
        id=str(uuid4()),
        order_id=str(uuid4()),
        qty=Decimal("0.5"),
        price=Decimal("43000.00"),
        commission=Decimal("5.00"),
        timestamp=datetime.now(UTC),
    )


# ============================================================================
# Test: PositionTracker Interface
# ============================================================================


class TestPositionTrackerInterface:
    """Test that PositionTracker has the expected interface."""

    def test_position_tracker_exists(self) -> None:
        """PositionTracker class exists."""
        from src.veda.position_tracker import PositionTracker
        assert PositionTracker is not None

    def test_position_tracker_has_get_position_method(self) -> None:
        """PositionTracker has get_position method."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        assert hasattr(tracker, "get_position")

    def test_position_tracker_has_get_all_positions_method(self) -> None:
        """PositionTracker has get_all_positions method."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        assert hasattr(tracker, "get_all_positions")

    def test_position_tracker_has_apply_fill_method(self) -> None:
        """PositionTracker has apply_fill method."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        assert hasattr(tracker, "apply_fill")

    def test_position_tracker_has_sync_from_exchange_method(self) -> None:
        """PositionTracker has sync_from_exchange method."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        assert hasattr(tracker, "sync_from_exchange")


# ============================================================================
# Test: Position Tracking from Fills
# ============================================================================


class TestPositionTrackerApplyFill:
    """Test position tracking from fills."""

    def test_apply_fill_creates_position(self, sample_fill_buy: Fill) -> None:
        """Applying a fill creates a position."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, sample_fill_buy)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        assert position.symbol == "BTC/USD"

    def test_buy_fill_creates_long_position(self, sample_fill_buy: Fill) -> None:
        """Buy fill creates long position."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, sample_fill_buy)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        assert position.qty == Decimal("1.0")
        assert position.side == PositionSide.LONG

    def test_sell_fill_creates_short_position(self, sample_fill_sell: Fill) -> None:
        """Sell fill from flat creates short position."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        tracker.apply_fill("BTC/USD", OrderSide.SELL, sample_fill_sell)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        assert position.qty == Decimal("0.5")
        assert position.side == PositionSide.SHORT

    def test_buy_increases_long_position(self, sample_fill_buy: Fill) -> None:
        """Additional buy increases long position."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, sample_fill_buy)
        tracker.apply_fill("BTC/USD", OrderSide.BUY, sample_fill_buy)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        assert position.qty == Decimal("2.0")

    def test_sell_reduces_long_position(self) -> None:
        """Sell reduces long position."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        buy_fill = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("2.0"),
            price=Decimal("42000.00"),
            commission=Decimal("10.00"),
            timestamp=datetime.now(UTC),
        )
        sell_fill = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("0.5"),
            price=Decimal("43000.00"),
            commission=Decimal("5.00"),
            timestamp=datetime.now(UTC),
        )
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, buy_fill)
        tracker.apply_fill("BTC/USD", OrderSide.SELL, sell_fill)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        assert position.qty == Decimal("1.5")
        assert position.side == PositionSide.LONG

    def test_sell_flattens_position(self) -> None:
        """Sell can flatten position to zero."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        buy_fill = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("1.0"),
            price=Decimal("42000.00"),
            commission=Decimal("10.00"),
            timestamp=datetime.now(UTC),
        )
        sell_fill = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("1.0"),
            price=Decimal("43000.00"),
            commission=Decimal("5.00"),
            timestamp=datetime.now(UTC),
        )
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, buy_fill)
        tracker.apply_fill("BTC/USD", OrderSide.SELL, sell_fill)
        position = tracker.get_position("BTC/USD")
        
        # Flat position returns None
        assert position is None

    def test_sell_flips_position_to_short(self) -> None:
        """Sell beyond position flips to short."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        buy_fill = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("1.0"),
            price=Decimal("42000.00"),
            commission=Decimal("10.00"),
            timestamp=datetime.now(UTC),
        )
        sell_fill = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("2.0"),
            price=Decimal("43000.00"),
            commission=Decimal("5.00"),
            timestamp=datetime.now(UTC),
        )
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, buy_fill)
        tracker.apply_fill("BTC/USD", OrderSide.SELL, sell_fill)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        assert position.qty == Decimal("1.0")
        assert position.side == PositionSide.SHORT


# ============================================================================
# Test: Cost Basis Tracking
# ============================================================================


class TestPositionTrackerCostBasis:
    """Test cost basis and average price tracking."""

    def test_position_has_cost_basis(self) -> None:
        """Position tracks cost basis."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        fill = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("1.0"),
            price=Decimal("42000.00"),
            commission=Decimal("10.00"),
            timestamp=datetime.now(UTC),
        )
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, fill)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        assert position.avg_entry_price == Decimal("42000.00")

    def test_position_averages_cost_basis(self) -> None:
        """Multiple fills average cost basis."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        fill1 = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("1.0"),
            price=Decimal("40000.00"),
            commission=Decimal("10.00"),
            timestamp=datetime.now(UTC),
        )
        fill2 = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("1.0"),
            price=Decimal("44000.00"),
            commission=Decimal("10.00"),
            timestamp=datetime.now(UTC),
        )
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, fill1)
        tracker.apply_fill("BTC/USD", OrderSide.BUY, fill2)
        position = tracker.get_position("BTC/USD")
        
        assert position is not None
        # Average of 40k and 44k = 42k
        assert position.avg_entry_price == Decimal("42000.00")


# ============================================================================
# Test: Position Queries
# ============================================================================


class TestPositionTrackerQueries:
    """Test position query methods."""

    def test_get_position_returns_none_for_unknown(self) -> None:
        """get_position returns None for unknown symbol."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        position = tracker.get_position("UNKNOWN/USD")
        
        assert position is None

    def test_get_all_positions_returns_all(self) -> None:
        """get_all_positions returns all positions."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        fill_btc = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("1.0"),
            price=Decimal("42000.00"),
            commission=Decimal("10.00"),
            timestamp=datetime.now(UTC),
        )
        fill_eth = Fill(
            id=str(uuid4()),
            order_id=str(uuid4()),
            qty=Decimal("10.0"),
            price=Decimal("2500.00"),
            commission=Decimal("5.00"),
            timestamp=datetime.now(UTC),
        )
        
        tracker.apply_fill("BTC/USD", OrderSide.BUY, fill_btc)
        tracker.apply_fill("ETH/USD", OrderSide.BUY, fill_eth)
        
        positions = tracker.get_all_positions()
        
        assert len(positions) == 2
        symbols = {p.symbol for p in positions}
        assert "BTC/USD" in symbols
        assert "ETH/USD" in symbols

    def test_get_all_positions_empty_initially(self) -> None:
        """get_all_positions returns empty list initially."""
        from src.veda.position_tracker import PositionTracker
        tracker = PositionTracker()
        
        positions = tracker.get_all_positions()
        
        assert positions == []


# ============================================================================
# Test: Exchange Sync
# ============================================================================


class TestPositionTrackerSync:
    """Test sync from exchange."""

    async def test_sync_from_exchange_updates_positions(self) -> None:
        """sync_from_exchange updates local positions."""
        from src.veda.adapters.mock_adapter import MockExchangeAdapter
        from src.veda.position_tracker import PositionTracker
        
        adapter = MockExchangeAdapter()
        tracker = PositionTracker()
        
        # Mock adapter has no positions initially
        await tracker.sync_from_exchange(adapter)
        
        positions = tracker.get_all_positions()
        # Should complete without error
        assert isinstance(positions, list)

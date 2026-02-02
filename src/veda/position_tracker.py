"""
Position Tracker

Tracks positions from fills and syncs with exchange.
Provides real-time position view and P&L calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from src.veda.interfaces import ExchangeAdapter
from src.veda.models import (
    Fill,
    OrderSide,
    Position,
    PositionSide,
)


@dataclass
class TrackedPosition:
    """Internal mutable position state."""

    symbol: str
    qty: Decimal  # Positive = long, negative = short
    cost_basis: Decimal  # Total cost (qty * avg_price)


class PositionTracker:
    """
    Tracks positions from fills.

    Provides:
    - Real-time position view
    - Cost basis tracking
    - Average price calculation
    - Exchange sync
    """

    def __init__(self) -> None:
        """Initialize tracker with empty positions."""
        self._positions: dict[str, TrackedPosition] = {}

    # =========================================================================
    # Fill Processing
    # =========================================================================

    def apply_fill(self, symbol: str, side: OrderSide, fill: Fill) -> None:
        """
        Apply a fill to update position.

        Args:
            symbol: The symbol for the position
            side: The order side (BUY/SELL)
            fill: The fill to apply
        """
        # Get or create position
        pos = self._positions.get(symbol)
        if pos is None:
            pos = TrackedPosition(symbol=symbol, qty=Decimal("0"), cost_basis=Decimal("0"))
            self._positions[symbol] = pos

        # Calculate fill direction
        fill_qty = fill.qty if side == OrderSide.BUY else -fill.qty
        fill_cost = fill.qty * fill.price

        # Update position
        if pos.qty == Decimal("0"):
            # Opening new position
            pos.qty = fill_qty
            pos.cost_basis = fill_cost if side == OrderSide.BUY else fill_cost
        elif (pos.qty > 0 and side == OrderSide.BUY) or (pos.qty < 0 and side == OrderSide.SELL):
            # Adding to position - average cost
            new_qty = pos.qty + fill_qty
            if new_qty != 0:
                # Weighted average cost basis
                denom = abs(pos.qty) + fill.qty
                if denom == Decimal("0"):
                    raise ValueError(
                        "Invariant violated: denominator for cost basis calculation is zero "
                        f"(pos.qty={pos.qty}, fill.qty={fill.qty})"
                    )
                pos.cost_basis = (pos.cost_basis * abs(pos.qty) + fill_cost) / denom
            pos.qty = new_qty
        else:
            # Reducing or flipping position
            new_qty = pos.qty + fill_qty
            if new_qty == 0:
                # Fully closed - remove position
                del self._positions[symbol]
                return
            elif (pos.qty > 0 and new_qty < 0) or (pos.qty < 0 and new_qty > 0):
                # Flipped sides - reset cost basis to new side's fill price
                pos.qty = new_qty
                pos.cost_basis = fill.price
            else:
                # Just reduced - keep original cost basis
                pos.qty = new_qty

    # =========================================================================
    # Position Queries
    # =========================================================================

    def get_position(self, symbol: str) -> Position | None:
        """
        Get position for a symbol.

        Args:
            symbol: The symbol to look up

        Returns:
            Position if exists and non-zero, None otherwise
        """
        pos = self._positions.get(symbol)
        if pos is None:
            return None

        return Position(
            symbol=pos.symbol,
            qty=abs(pos.qty),
            side=PositionSide.LONG if pos.qty > 0 else PositionSide.SHORT,
            avg_entry_price=pos.cost_basis,
            market_value=Decimal("0"),  # Would need market data
            unrealized_pnl=Decimal("0"),  # Would need market data
            unrealized_pnl_percent=Decimal("0"),  # Would need market data
        )

    def get_all_positions(self) -> list[Position]:
        """
        Get all non-zero positions.

        Returns:
            List of Position instances
        """
        result = []
        for pos in self._positions.values():
            if pos.qty != Decimal("0"):
                result.append(Position(
                    symbol=pos.symbol,
                    qty=abs(pos.qty),
                    side=PositionSide.LONG if pos.qty > 0 else PositionSide.SHORT,
                    avg_entry_price=pos.cost_basis,
                    market_value=Decimal("0"),
                    unrealized_pnl=Decimal("0"),
                    unrealized_pnl_percent=Decimal("0"),
                ))
        return result

    # =========================================================================
    # Exchange Sync
    # =========================================================================

    async def sync_from_exchange(self, adapter: ExchangeAdapter) -> None:
        """
        Sync positions from exchange.

        Replaces local positions with exchange's view.

        Args:
            adapter: The exchange adapter to sync from
        """
        exchange_positions = await adapter.get_positions()
        
        # Clear local positions
        self._positions.clear()
        
        # Import exchange positions
        for pos in exchange_positions:
            qty = pos.qty if pos.side == PositionSide.LONG else -pos.qty
            self._positions[pos.symbol] = TrackedPosition(
                symbol=pos.symbol,
                qty=qty,
                cost_basis=pos.avg_entry_price,
            )

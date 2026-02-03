"""
Greta Data Models

Data structures for backtesting: fills, positions, stats, results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class FillSimulationConfig:
    """
    Configuration for fill simulation.
    
    Controls slippage, commission, and fill price behavior.
    """

    # Slippage settings
    slippage_bps: Decimal = Decimal("0")  # Basis points (1 bp = 0.01%)
    slippage_model: str = "fixed"  # "fixed" | "volume" | "volatility"

    # Commission settings
    commission_bps: Decimal = Decimal("0")  # Basis points on notional
    min_commission: Decimal = Decimal("0")  # Minimum commission per trade

    # Fill price settings
    fill_at: str = "open"  # "open" | "close" | "vwap" | "worst"


@dataclass(frozen=True)
class SimulatedFill:
    """
    Record of a simulated fill during backtest.
    
    Immutable to preserve backtest audit trail.
    
    Attributes:
        slippage: Total slippage cost (price_adjustment * qty), not per-unit.
                  Represents the total dollar impact of slippage on this fill.
    """

    order_id: str
    client_order_id: str
    symbol: str
    side: str  # "buy" | "sell" - TODO(M5): Change to OrderSide enum
    qty: Decimal
    fill_price: Decimal  # Price after slippage applied
    commission: Decimal  # Total commission for this fill
    slippage: Decimal  # Total slippage cost (price_adj * qty)
    timestamp: datetime
    bar_index: int

    @property
    def notional(self) -> Decimal:
        """Total notional value of the fill."""
        return self.qty * self.fill_price


@dataclass
class SimulatedPosition:
    """
    Simulated position during backtest.
    
    Mutable to allow mark-to-market updates.
    """

    symbol: str
    qty: Decimal
    avg_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal

    @property
    def is_long(self) -> bool:
        """True if position is long (positive qty)."""
        return self.qty > Decimal("0")

    @property
    def is_short(self) -> bool:
        """True if position is short (negative qty)."""
        return self.qty < Decimal("0")

    def update_mark(self, price: Decimal) -> None:
        """
        Update market value and unrealized P&L based on current price.
        
        Args:
            price: Current market price
        """
        self.market_value = self.qty * price
        self.unrealized_pnl = self.market_value - (self.qty * self.avg_entry_price)


@dataclass
class BacktestStats:
    """
    Comprehensive backtest statistics.
    
    Calculated at end of backtest from fills and equity curve.
    """

    # Returns
    total_return: Decimal = Decimal("0")
    total_return_pct: Decimal = Decimal("0")
    annualized_return: Decimal = Decimal("0")

    # Risk metrics
    sharpe_ratio: Decimal | None = None
    sortino_ratio: Decimal | None = None
    max_drawdown: Decimal = Decimal("0")
    max_drawdown_pct: Decimal = Decimal("0")

    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = Decimal("0")

    # Profit metrics
    avg_win: Decimal = Decimal("0")
    avg_loss: Decimal = Decimal("0")
    profit_factor: Decimal | None = None

    # Time in market
    total_bars: int = 0
    bars_in_position: int = 0

    # Costs
    total_commission: Decimal = Decimal("0")
    total_slippage: Decimal = Decimal("0")


@dataclass
class BacktestResult:
    """
    Complete backtest result.
    
    Contains all information about a completed backtest run.
    """

    run_id: str
    start_time: datetime
    end_time: datetime
    timeframe: str
    symbols: list[str]

    # Final state
    stats: BacktestStats
    final_equity: Decimal
    equity_curve: list[tuple[datetime, Decimal]]

    # Trade log
    fills: list[SimulatedFill] = field(default_factory=list)

    # Timing
    simulation_duration_ms: int = 0
    total_bars_processed: int = 0

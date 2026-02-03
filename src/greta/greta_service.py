"""
GretaService - Backtest Execution Environment

Per-run instance that simulates trading for backtests.
Each backtest run gets its own GretaService instance.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from src.events.protocol import Envelope
from src.greta.fill_simulator import DefaultFillSimulator
from src.greta.models import (
    BacktestResult,
    BacktestStats,
    FillSimulationConfig,
    SimulatedFill,
    SimulatedPosition,
)
from src.veda.models import OrderIntent, OrderSide, OrderStatus

if TYPE_CHECKING:
    from src.events.log import EventLog
    from src.walle.repositories.bar_repository import Bar, BarRepository


class GretaService:
    """
    Backtest execution environment for a SINGLE run.
    
    IMPORTANT: This is a PER-RUN instance, NOT a singleton!
    
    Each backtest run gets its own GretaService instance because:
    - Simulated positions must be isolated between runs
    - Equity curves are per-run
    - Pending orders are per-run
    - Multiple backtests can run in parallel
    
    Lifecycle:
    1. RunManager creates GretaService for a new backtest run
    2. GretaService.initialize() sets up symbols and timeframe
    3. Clock drives GretaService.advance_to() on each tick
    4. When run completes, GretaService.get_result() returns stats
    5. RunManager disposes the GretaService instance
    """

    def __init__(
        self,
        run_id: str,
        bar_repository: BarRepository,
        event_log: EventLog,
        fill_config: FillSimulationConfig | None = None,
        initial_cash: Decimal = Decimal("100000"),
    ) -> None:
        """
        Initialize GretaService for a specific run.
        
        Args:
            run_id: Unique identifier for this backtest run
            bar_repository: Shared singleton for historical bar data
            event_log: Shared singleton for event emission
            fill_config: Optional fill simulation configuration
            initial_cash: Starting cash for backtest
        """
        self._run_id = run_id
        self._bar_repo = bar_repository
        self._event_log = event_log
        self._fill_config = fill_config or FillSimulationConfig()
        self._fill_simulator = DefaultFillSimulator()
        self._initial_cash = initial_cash

        # Per-run simulation state
        self._symbols: list[str] = []
        self._timeframe: str = ""
        self._start: datetime | None = None
        self._end: datetime | None = None
        
        # Preloaded bar data: symbol -> {timestamp -> Bar}
        self._bar_cache: dict[str, dict[datetime, Bar]] = {}
        
        # Current state
        self._positions: dict[str, SimulatedPosition] = {}
        self._pending_orders: dict[str, OrderIntent] = {}
        self._fills: list[SimulatedFill] = []
        self._equity_curve: list[tuple[datetime, Decimal]] = []
        self._current_bars: dict[str, Bar] = {}
        self._cash: Decimal = initial_cash

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def run_id(self) -> str:
        """Get the run ID this service is bound to."""
        return self._run_id

    @property
    def symbols(self) -> list[str]:
        """Get configured symbols."""
        return self._symbols.copy()

    @property
    def timeframe(self) -> str:
        """Get configured timeframe."""
        return self._timeframe

    @property
    def positions(self) -> dict[str, SimulatedPosition]:
        """Get current positions (read-only copy)."""
        return self._positions.copy()

    @property
    def pending_orders(self) -> dict[str, OrderIntent]:
        """Get pending orders (read-only copy)."""
        return self._pending_orders.copy()

    @property
    def fills(self) -> list[SimulatedFill]:
        """Get all fills (read-only copy)."""
        return self._fills.copy()

    @property
    def equity_curve(self) -> list[tuple[datetime, Decimal]]:
        """Get equity curve (read-only copy)."""
        return self._equity_curve.copy()

    @property
    def current_bars(self) -> dict[str, Bar]:
        """Get current bars for all symbols."""
        return self._current_bars.copy()

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    async def initialize(
        self,
        symbols: list[str],
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> None:
        """
        Initialize for a backtest run.
        
        Preloads historical data and resets state.
        
        Args:
            symbols: List of symbols to trade
            timeframe: Bar timeframe (e.g., "1m", "5m")
            start: Backtest start time
            end: Backtest end time
        """
        self._symbols = symbols
        self._timeframe = timeframe
        self._start = start
        self._end = end

        # Reset state
        self._positions = {}
        self._pending_orders = {}
        self._fills = []
        self._equity_curve = []
        self._current_bars = {}
        self._cash = self._initial_cash
        self._bar_cache = {}

        # Preload bar data for all symbols
        for symbol in symbols:
            bars = await self._bar_repo.get_bars(symbol, timeframe, start, end)
            self._bar_cache[symbol] = {bar.timestamp: bar for bar in bars}

    async def advance_to(self, timestamp: datetime) -> None:
        """
        Advance simulation to a specific timestamp.
        
        Called by the clock on each tick. Processes:
        1. Update current bars
        2. Fill pending orders
        3. Update position marks
        4. Record equity curve
        
        Args:
            timestamp: The timestamp to advance to
        """
        # 1. Update current bars for this timestamp
        for symbol in self._symbols:
            if symbol in self._bar_cache:
                bar = self._bar_cache[symbol].get(timestamp)
                if bar:
                    self._current_bars[symbol] = bar

        # 2. Process pending orders (try to fill)
        await self._process_pending_orders(timestamp)

        # 3. Update position marks with current prices
        self._update_position_marks()

        # 4. Record equity curve point
        self._record_equity(timestamp)

    def get_result(self) -> BacktestResult:
        """
        Get the backtest result after completion.
        
        Returns:
            BacktestResult with stats, fills, and equity curve
        """
        stats = self._calculate_stats()
        
        return BacktestResult(
            run_id=self._run_id,
            start_time=self._start or datetime.now(),
            end_time=self._end or datetime.now(),
            timeframe=self._timeframe,
            symbols=self._symbols,
            stats=stats,
            final_equity=self._calculate_equity(),
            equity_curve=self._equity_curve.copy(),
            fills=self._fills.copy(),
            total_bars_processed=len(self._equity_curve),
        )

    # =========================================================================
    # Order Management
    # =========================================================================

    async def place_order(self, intent: OrderIntent) -> None:
        """
        Submit an order for simulation.
        
        Orders are queued and filled on the next advance_to() call.
        
        Args:
            intent: Order intent from strategy
        """
        order_id = str(uuid4())
        self._pending_orders[order_id] = intent

        # Emit orders.Placed event
        await self._emit_event(
            "orders.Placed",
            {
                "order_id": order_id,
                "client_order_id": intent.client_order_id,
                "symbol": intent.symbol,
                "side": intent.side.value,
                "order_type": intent.order_type.value,
                "qty": str(intent.qty),
                "status": OrderStatus.ACCEPTED.value,
            },
        )

    async def _process_pending_orders(self, timestamp: datetime) -> None:
        """Process all pending orders, attempting to fill them."""
        filled_order_ids = []

        for order_id, intent in self._pending_orders.items():
            # Get current bar for the symbol
            bar = self._current_bars.get(intent.symbol)
            if not bar:
                continue

            # Try to simulate fill
            fill = self._fill_simulator.simulate_fill(intent, bar, self._fill_config)
            
            if fill is not None:
                # Record fill
                self._fills.append(fill)
                filled_order_ids.append(order_id)

                # Update position
                self._apply_fill(fill)

                # Emit orders.Filled event
                await self._emit_event(
                    "orders.Filled",
                    {
                        "order_id": order_id,
                        "client_order_id": intent.client_order_id,
                        "symbol": fill.symbol,
                        "side": fill.side,
                        "qty": str(fill.qty),
                        "fill_price": str(fill.fill_price),
                        "commission": str(fill.commission),
                    },
                )

        # Remove filled orders from pending
        for order_id in filled_order_ids:
            del self._pending_orders[order_id]

    # =========================================================================
    # Position Helpers
    # =========================================================================

    @staticmethod
    def _is_adding_to_position(old_qty: Decimal, qty_change: Decimal) -> bool:
        """
        Check if a trade adds to an existing position (same direction).
        
        Both quantities have the same sign means we're adding:
        - Long position (old_qty > 0) + buy (qty_change > 0) = adding
        - Short position (old_qty < 0) + sell (qty_change < 0) = adding
        """
        return old_qty * qty_change > 0

    @staticmethod
    def _is_position_reversal(old_qty: Decimal, new_qty: Decimal) -> bool:
        """
        Check if a trade reverses the position direction.
        
        Signs differ means we crossed zero:
        - Long→Short: old_qty > 0, new_qty < 0
        - Short→Long: old_qty < 0, new_qty > 0
        
        Note:
            Caller must handle new_qty == 0 (position closed) before calling.
            When new_qty is zero, old_qty * new_qty == 0, returning False.
        """
        return old_qty * new_qty < 0

    def _apply_fill(self, fill: SimulatedFill) -> None:
        """Apply a fill to update positions and cash."""
        symbol = fill.symbol
        is_buy = fill.side == OrderSide.BUY.value
        qty_change = fill.qty if is_buy else -fill.qty
        notional = fill.qty * fill.fill_price

        # Update cash
        if is_buy:
            self._cash -= notional + fill.commission
        else:
            self._cash += notional - fill.commission

        # Update or create position
        if symbol in self._positions:
            pos = self._positions[symbol]
            old_qty = pos.qty
            new_qty = old_qty + qty_change

            if new_qty == Decimal("0"):
                # Position closed
                del self._positions[symbol]
            else:
                # Update position with appropriate entry price handling
                if self._is_adding_to_position(old_qty, qty_change):
                    # Adding to existing position - weighted average entry price
                    total_cost = pos.avg_entry_price * abs(old_qty) + fill.fill_price * fill.qty
                    pos.avg_entry_price = total_cost / abs(new_qty)
                elif self._is_position_reversal(old_qty, new_qty):
                    # Position reversed (long→short or short→long)
                    # The "excess" quantity forms new position at fill price
                    pos.avg_entry_price = fill.fill_price
                # else: Reducing position (partial close) - avg_entry_price unchanged
                
                pos.qty = new_qty
                pos.market_value = new_qty * fill.fill_price
        else:
            # New position
            self._positions[symbol] = SimulatedPosition(
                symbol=symbol,
                qty=qty_change,
                avg_entry_price=fill.fill_price,
                market_value=qty_change * fill.fill_price,
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
            )

    # =========================================================================
    # Position & Equity Tracking
    # =========================================================================

    def _update_position_marks(self) -> None:
        """Update all position market values with current prices."""
        for symbol, pos in self._positions.items():
            bar = self._current_bars.get(symbol)
            if bar:
                pos.update_mark(bar.close)

    def _calculate_equity(self) -> Decimal:
        """Calculate total equity (cash + positions)."""
        position_value = sum(
            pos.market_value for pos in self._positions.values()
        )
        return self._cash + position_value

    def _record_equity(self, timestamp: datetime) -> None:
        """Record current equity to equity curve."""
        equity = self._calculate_equity()
        self._equity_curve.append((timestamp, equity))

    def _calculate_stats(self) -> BacktestStats:
        """Calculate backtest statistics from fills and equity curve."""
        stats = BacktestStats()
        
        if not self._equity_curve:
            return stats

        # Basic stats
        stats.total_trades = len(self._fills)
        stats.total_bars = len(self._equity_curve)
        
        # Calculate return
        initial = self._initial_cash
        final = self._calculate_equity()
        stats.total_return = final - initial
        if initial > 0:
            stats.total_return_pct = (stats.total_return / initial) * 100

        # Calculate total costs
        stats.total_commission = sum(
            (f.commission for f in self._fills), Decimal("0")
        )
        stats.total_slippage = sum(
            (f.slippage for f in self._fills), Decimal("0")
        )

        # TODO: Calculate more advanced stats (Sharpe, drawdown, etc.)

        return stats

    # =========================================================================
    # Event Emission
    # =========================================================================

    async def _emit_event(self, event_type: str, payload: dict) -> None:
        """Emit an event to the event log."""
        envelope = Envelope(
            type=event_type,
            producer="greta.service",
            payload=payload,
            run_id=self._run_id,
        )
        await self._event_log.append(envelope)

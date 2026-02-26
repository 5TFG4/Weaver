"""
GretaService - Backtest Execution Environment

Per-run instance that simulates trading for backtests.
Each backtest run gets its own GretaService instance.
"""

from __future__ import annotations

import asyncio
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
from src.veda.models import OrderType, TimeInForce

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
        self._subscription_ids: list[str] = []

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

        # Subscribe to backtest.FetchWindow events for this run
        fetch_window_sub_id = await self._event_log.subscribe_filtered(
            event_types=["backtest.FetchWindow"],
            callback=self._on_fetch_window,
            filter_fn=lambda e: e.run_id == self._run_id,
        )

        # Subscribe to backtest.PlaceOrder events for this run
        place_order_sub_id = await self._event_log.subscribe_filtered(
            event_types=["backtest.PlaceOrder"],
            callback=self._on_place_order,
            filter_fn=lambda e: e.run_id == self._run_id,
        )
        self._subscription_ids = [fetch_window_sub_id, place_order_sub_id]

    async def cleanup(self) -> None:
        """Cleanup runtime subscriptions for this run.

        Safe to call multiple times.
        """
        if not self._subscription_ids:
            return

        for sub_id in self._subscription_ids:
            await self._event_log.unsubscribe_by_id(sub_id)
        self._subscription_ids = []

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

    def _on_fetch_window(self, envelope: Envelope) -> None:
        """
        Handle backtest.FetchWindow event (sync callback wrapper).
        
        Fetches bars from cache and emits data.WindowReady.
        Since EventLog callbacks are sync, we schedule the async work.
        """
        import asyncio

        asyncio.create_task(self._handle_fetch_window(envelope))

    async def _handle_fetch_window(self, envelope: Envelope) -> None:
        """
        Handle backtest.FetchWindow event.
        
        Fetches bars from cache and emits data.WindowReady.
        """
        from datetime import datetime as dt
        from dateutil.parser import isoparse

        payload = envelope.payload
        symbol = payload.get("symbol")
        lookback = payload.get("lookback", 10)
        as_of_str = payload.get("as_of")

        if not symbol:
            return

        # Get bars from cache
        bars: list[Bar] = []
        if symbol in self._bar_cache:
            symbol_bars = self._bar_cache[symbol]
            
            # Sort by timestamp and get last N bars up to as_of
            if as_of_str:
                as_of = isoparse(as_of_str)
                # Filter bars up to as_of time
                available_bars = sorted(
                    [b for b in symbol_bars.values() if b.timestamp <= as_of],
                    key=lambda b: b.timestamp,
                )
            else:
                available_bars = sorted(symbol_bars.values(), key=lambda b: b.timestamp)
            
            # Take last N bars
            bars = available_bars[-lookback:] if len(available_bars) >= lookback else available_bars

        # Emit data.WindowReady
        window_ready = Envelope(
            type="data.WindowReady",
            payload={
                "symbol": symbol,
                "bars": [
                    {
                        "timestamp": b.timestamp.isoformat(),
                        "open": str(b.open),
                        "high": str(b.high),
                        "low": str(b.low),
                        "close": str(b.close),
                        "volume": str(b.volume),
                    }
                    for b in bars
                ],
                "lookback": lookback,
            },
            run_id=self._run_id,
            producer="greta.service",
            corr_id=envelope.corr_id,
            causation_id=envelope.id,
        )
        await self._event_log.append(window_ready)

    def _on_place_order(self, envelope: Envelope) -> None:
        """
        Handle backtest.PlaceOrder event (sync callback wrapper).

        Since EventLog callbacks are sync, we schedule async work.
        """
        asyncio.create_task(self._handle_place_order(envelope))

    async def _handle_place_order(self, envelope: Envelope) -> None:
        """
        Handle backtest.PlaceOrder event.

        Converts routed order payload into OrderIntent and queues it
        through place_order() for simulation.
        """
        payload = envelope.payload

        try:
            side = OrderSide(payload["side"])
            order_type = OrderType(payload["order_type"])
            qty = Decimal(str(payload["qty"]))
        except (KeyError, ValueError):
            return

        client_order_id = payload.get("client_order_id") or f"backtest-{uuid4()}"
        time_in_force = TimeInForce(payload.get("time_in_force", TimeInForce.DAY.value))

        limit_price = payload.get("limit_price")
        stop_price = payload.get("stop_price")

        intent = OrderIntent(
            run_id=envelope.run_id or self._run_id,
            client_order_id=client_order_id,
            symbol=payload.get("symbol", ""),
            side=side,
            order_type=order_type,
            qty=qty,
            limit_price=Decimal(str(limit_price)) if limit_price is not None else None,
            stop_price=Decimal(str(stop_price)) if stop_price is not None else None,
            time_in_force=time_in_force,
        )
        await self.place_order(intent)

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
                        "side": fill.side.value,
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
        is_buy = fill.side == OrderSide.BUY
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

        # Win/loss analysis from round-trip trades
        self._compute_trade_stats(stats)

        # Risk metrics from equity curve
        self._compute_risk_metrics(stats)

        return stats

    def _compute_trade_stats(self, stats: BacktestStats) -> None:
        """Compute win/loss stats from paired buy/sell fills."""
        # Pair fills into round-trip trades: buy→sell or sell→buy
        # Group by symbol, pair in order
        from collections import defaultdict

        symbol_fills: dict[str, list[SimulatedFill]] = defaultdict(list)
        for fill in self._fills:
            symbol_fills[fill.symbol].append(fill)

        gross_profit = Decimal("0")
        gross_loss = Decimal("0")
        wins: list[Decimal] = []
        losses: list[Decimal] = []

        for symbol, fills in symbol_fills.items():
            i = 0
            while i + 1 < len(fills):
                entry = fills[i]
                exit_ = fills[i + 1]

                # Calculate P&L for this round-trip
                if entry.side == OrderSide.BUY:
                    pnl = (exit_.fill_price - entry.fill_price) * entry.qty
                else:
                    pnl = (entry.fill_price - exit_.fill_price) * entry.qty

                # Account for commissions
                pnl -= entry.commission + exit_.commission

                if pnl > Decimal("0"):
                    stats.winning_trades += 1
                    gross_profit += pnl
                    wins.append(pnl)
                elif pnl < Decimal("0"):
                    stats.losing_trades += 1
                    gross_loss += abs(pnl)
                    losses.append(pnl)

                i += 2

        total_round_trips = stats.winning_trades + stats.losing_trades
        if total_round_trips > 0:
            stats.win_rate = (Decimal(stats.winning_trades) / Decimal(total_round_trips)) * 100

        if wins:
            stats.avg_win = gross_profit / Decimal(len(wins))
        if losses:
            stats.avg_loss = gross_loss / Decimal(len(losses))

        if gross_loss > Decimal("0"):
            stats.profit_factor = gross_profit / gross_loss

    def _compute_risk_metrics(self, stats: BacktestStats) -> None:
        """Compute Sharpe ratio, Sortino ratio, and max drawdown from equity curve."""
        if len(self._equity_curve) < 2:
            return

        # Period returns from equity curve
        returns: list[Decimal] = []
        for i in range(1, len(self._equity_curve)):
            prev_equity = self._equity_curve[i - 1][1]
            curr_equity = self._equity_curve[i][1]
            if prev_equity != Decimal("0"):
                ret = (curr_equity - prev_equity) / abs(prev_equity)
                returns.append(ret)

        if not returns:
            return

        # Mean and std of returns
        n = Decimal(len(returns))
        mean_return = sum(returns) / n

        variance = sum((r - mean_return) ** 2 for r in returns) / n
        std_return = variance.sqrt() if hasattr(variance, 'sqrt') else Decimal(str(variance ** Decimal("0.5")))

        # Sharpe ratio (assuming risk-free rate = 0 for simplicity)
        if std_return > Decimal("0"):
            stats.sharpe_ratio = mean_return / std_return

        # Sortino ratio (downside deviation only)
        downside_returns = [r for r in returns if r < Decimal("0")]
        if downside_returns:
            downside_variance = sum(r ** 2 for r in downside_returns) / Decimal(len(downside_returns))
            downside_std = Decimal(str(downside_variance ** Decimal("0.5")))
            if downside_std > Decimal("0"):
                stats.sortino_ratio = mean_return / downside_std

        # Max drawdown from equity curve
        peak = self._equity_curve[0][1]
        max_dd = Decimal("0")

        for _, equity in self._equity_curve:
            if equity > peak:
                peak = equity
            dd = equity - peak  # negative when below peak
            if dd < max_dd:
                max_dd = dd

        stats.max_drawdown = max_dd
        if peak > Decimal("0"):
            stats.max_drawdown_pct = (max_dd / peak) * 100

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

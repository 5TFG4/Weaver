# M4: Greta Backtesting Engine

> **Status**: ✅ COMPLETED (2026-02-03)  
> **Prerequisite for**: M5 (Marvin Strategy Execution)  
> **Actual Effort**: ~8 hours (7 MVPs, 79 new tests)
> 
> ## Implementation Summary
> 
> All 7 MVPs completed with TDD methodology:
> - MVP-1: WallE BarRepository (16 tests)
> - MVP-2: Greta Models & FillSimulator (29 tests) 
> - MVP-3: GretaService (20 tests)
> - MVP-4: Marvin Skeleton (32 tests)
> - MVP-5: DomainRouter (12 tests)
> - MVP-6: Run Orchestration (10 tests)
> - MVP-7: Integration Test (5 tests)
> 
> ### Design Deviations & Notes
> 
> 1. **data.WindowReady flow**: Not fully implemented. GretaService preloads bars at initialize(),
>    but the strategy.FetchWindow → data.WindowReady event flow is not wired. Deferred to M5.
> 
> 2. **backtest.* events**: DomainRouter routes strategy.* → backtest.*, but Greta doesn't 
>    subscribe to backtest.* events yet. Current flow uses direct method calls via RunManager.
>    Full event-driven flow is a future enhancement.
> 
> 3. **Test fixtures**: `SimpleTestStrategy` and `MockStrategyLoader` live in 
>    `tests/integration/test_backtest_flow.py`. Consider extracting to `tests/fixtures/` in M5.

---

## ⚠️ Architecture Clarification: Module Collaboration

Before diving into design, it's critical to understand how modules collaborate:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    The Essence of Backtesting                           │
│                                                                         │
│  Backtest = Test Marvin's strategy performance using historical data    │
│                                                                         │
│  Therefore:                                                             │
│  - Marvin: Runs strategy code, emits strategy.* events                  │
│  - Greta: Simulates trading environment, handles backtest.* events      │
│  - WallE: Provides historical data (cached) or caches after fetch       │
│  - GLaDOS: Orchestrates everything, domain routing                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Multi-Run Architecture

The system must support multiple simultaneous runs:
- Multiple backtests running in parallel (different strategies, time ranges)
- Backtest + live trading simultaneously  
- Multiple live strategies (future)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Instance Model per Component                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SINGLETON (shared across all runs):                                    │
│  ├── EventLog         → Events tagged with run_id, shared infra        │
│  ├── BarRepository    → Historical data is immutable, share efficient  │
│  ├── DomainRouter     → Routes based on run_id lookup                  │
│  └── SSEBroadcaster   → Filters events by run_id for frontend          │
│                                                                         │
│  PER-RUN INSTANCE (isolated state per run):                             │
│  ├── GretaService     → Each backtest has own positions/orders/equity  │
│  ├── StrategyRunner   → Each strategy has own context and state        │
│  └── Clock            → Each run has own time progression              │
│                                                                         │
│  Why per-run for Greta/Marvin?                                          │
│  - Simulated positions must be isolated (Run A's fills ≠ Run B's)      │
│  - Each backtest may have different time ranges                         │
│  - Strategy state (indicators, signals) must not leak between runs     │
│  - Enables parallel backtests with independent failure isolation       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────────┐
                    │                   RunManager                         │
                    │            (manages all active runs)                 │
                    └─────────────────────────┬───────────────────────────┘
                                              │
          ┌───────────────────────────────────┼───────────────────────────────────┐
          │                                   │                                   │
          ▼                                   ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐           ┌─────────────────────┐
│  Run A (backtest)   │           │  Run B (backtest)   │           │  Run C (live)       │
│  run_id: "run-001"  │           │  run_id: "run-002"  │           │  run_id: "run-003"  │
├─────────────────────┤           ├─────────────────────┤           ├─────────────────────┤
│ GretaService A      │           │ GretaService B      │           │ (no Greta - live)   │
│ StrategyRunner A    │           │ StrategyRunner B    │           │ StrategyRunner C    │
│ BacktestClock A     │           │ BacktestClock B     │           │ RealtimeClock C     │
│ TestStrategy        │           │ SMAStrategy         │           │ SMAStrategy         │
└─────────────────────┘           └─────────────────────┘           └─────────────────────┘
          │                                   │                                   │
          └───────────────────────────────────┼───────────────────────────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │     Shared Singletons         │
                              ├───────────────────────────────┤
                              │ EventLog (events have run_id) │
                              │ BarRepository (shared data)   │
                              │ DomainRouter (routes by mode) │
                              └───────────────────────────────┘
```

### Correct Data Flow

```
                    ┌─────────────────────────────────────────────────────┐
                    │                     Marvin                          │
                    │  Strategy code runs here (unaware of live/backtest) │
                    │                                                     │
                    │  Receives clock.Tick ──────► Compute signals        │
                    │        │                          │                 │
                    │        │                          ▼                 │
                    │        │         emit strategy.FetchWindow          │
                    │        │                          │                 │
                    │        │     Receives data.WindowReady              │
                    │        │                          │                 │
                    │        │                          ▼                 │
                    │        │         emit strategy.PlaceRequest         │
                    │        │                          │                 │
                    │        │     Receives orders.Filled                 │
                    │        │                          │                 │
                    │        ▼                          ▼                 │
                    │  Next tick...               Update state            │
                    └────────────────────────────┬────────────────────────┘
                                                 │
                           strategy.FetchWindow  │  strategy.PlaceRequest
                                                 ▼
                    ┌─────────────────────────────────────────────────────┐
                    │               GLaDOS (Domain Router)                │
                    │                                                     │
                    │   if run.mode == BACKTEST:                          │
                    │       strategy.FetchWindow → backtest.FetchWindow   │
                    │       strategy.PlaceRequest → backtest.PlaceOrder   │
                    │   else:                                             │
                    │       strategy.FetchWindow → live.FetchWindow       │
                    │       strategy.PlaceRequest → live.PlaceOrder       │
                    │                                                     │
                    └──────────────┬──────────────────────┬───────────────┘
                                   │                      │
                       BACKTEST    │                      │  LIVE/PAPER
                                   ▼                      ▼
                    ┌──────────────────────┐  ┌──────────────────────┐
                    │        Greta         │  │        Veda          │
                    │                      │  │                      │
                    │  backtest.FetchWindow│  │  live.FetchWindow    │
                    │    → fetch from cache│  │    → fetch from API  │
                    │    → emit data.*     │  │    → emit data.*     │
                    │                      │  │                      │
                    │  backtest.PlaceOrder │  │  live.PlaceOrder     │
                    │    → simulate fill   │  │    → real order      │
                    │    → emit orders.*   │  │    → emit orders.*   │
                    │                      │  │                      │
                    └──────────┬───────────┘  └──────────┬───────────┘
                               │                         │
                               │    ┌────────────────────┘
                               │    │
                               ▼    ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                      WallE                          │
                    │                                                     │
                    │  - Store historical bars (for backtest)             │
                    │  - Persist order records                            │
                    │  - Persist backtest results                         │
                    │                                                     │
                    └─────────────────────────────────────────────────────┘
```

### Historical Data Sourcing Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  Historical Data Acquisition Strategy                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  At backtest start:                                                     │
│                                                                         │
│  1. Greta receives backtest.FetchWindow(symbol, start, end)             │
│                                                                         │
│  2. Check WallE cache:                                                  │
│     bars = await walle.bar_repository.get_bars(symbol, start, end)      │
│                                                                         │
│  3. If cache incomplete:                                                │
│     missing_ranges = calculate_missing(requested, cached)               │
│     for range in missing_ranges:                                        │
│         # Fetch via Veda adapter (but not calling Veda directly)        │
│         # Instead, through GLaDOS's MarketDataService                   │
│         bars = await market_data_service.fetch_historical(...)          │
│         await walle.bar_repository.save_bars(bars)                      │
│                                                                         │
│  4. Return complete data                                                │
│     emit data.WindowReady(bars)                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Key Points:
- Greta does NOT call ExchangeAdapter directly
- Historical data comes from WallE's BarRepository
- If data missing, GLaDOS's MarketDataService fetches and caches
- MarketDataService internally uses Veda's ExchangeAdapter
```

---

## Part A: Full Design

### A.1 Module Responsibilities (Revised)

```
┌─────────────────────────────────────────────────────────────────┐
│  Greta - Backtesting Execution Environment                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RESPONSIBILITIES:                                              │
│  ├── Handle backtest.* events routed from GLaDOS                │
│  ├── Provide historical data windows (from WallE cache)         │
│  ├── Simulate order fills (slippage, fees, market impact)       │
│  ├── Track simulated positions and P&L                          │
│  └── Emit data.* and orders.* events (same as Veda)             │
│                                                                 │
│  DOES NOT:                                                      │
│  ├── Run strategy code (that's Marvin)                          │
│  ├── Make real API calls (that's Veda)                          │
│  ├── Expose APIs (that's GLaDOS)                                │
│  ├── Persist data directly (that's WallE)                       │
│  └── Know which strategy is running                             │
│                                                                 │
│  KEY CONSTRAINT:                                                │
│  Same event interface as Veda - Marvin doesn't know the mode    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Minimal Marvin Implementation Required for M4                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  To test Greta, we need a minimal Marvin skeleton:              │
│  ├── Receive clock.Tick                                         │
│  ├── Emit strategy.FetchWindow                                  │
│  ├── Receive data.WindowReady                                   │
│  ├── Emit strategy.PlaceRequest (simple test strategy)          │
│  └── Receive orders.Filled/Rejected                             │
│                                                                 │
│  Full Marvin implementation is in M5                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### A.2 Architecture Integration (Revised)

```
                              clock.Tick
                                  │
                    ┌─────────────▼─────────────┐
                    │         Marvin            │
                    │   (Strategy Execution)    │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │  TestStrategy       │  │
                    │  │  (for M4 testing)   │  │
                    │  └─────────────────────┘  │
                    └─────────────┬─────────────┘
                                  │
                   strategy.FetchWindow / strategy.PlaceRequest
                                  │
                    ┌─────────────▼─────────────┐
                    │         GLaDOS            │
                    │    (Domain Routing)       │
                    │                           │
                    │  mode==BACKTEST?          │
                    │    strategy.* → backtest.*│
                    └─────────────┬─────────────┘
                                  │
                   backtest.FetchWindow / backtest.PlaceOrder
                                  │
                    ┌─────────────▼─────────────┐
                    │          Greta            │
                    │  (Backtest Environment)   │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │ FillSimulator       │  │
                    │  │ (slippage, fees)    │  │
                    │  └─────────────────────┘  │
                    │  ┌─────────────────────┐  │
                    │  │ PositionTracker     │  │
                    │  │ (simulated P&L)     │  │
                    │  └─────────────────────┘  │
                    └─────────────┬─────────────┘
                                  │
                         data.WindowReady / orders.Filled
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
        ▼                                                   ▼
┌───────────────┐                                   ┌───────────────┐
│    WallE      │                                   │   EventLog    │
│               │                                   │               │
│ BarRepository │◄── historical data ──────────────│   (Outbox)    │
│ (cached bars) │                                   │               │
└───────────────┘                                   └───────────────┘
        ▲                                                   │
        │                                                   │
        │ If cache miss, GLaDOS's                           │
        │ MarketDataService fetches & caches                ▼
        │                                           ┌───────────────┐
┌───────────────┐                                   │    Marvin     │
│ MarketData    │                                   │  (receives    │
│ Service       │                                   │   events)     │
│ (in GLaDOS)   │                                   └───────────────┘
└───────┬───────┘
        │
        ▼
┌───────────────┐
│    Veda       │
│ (adapter for  │
│ hist data)    │
└───────────────┘
```

### A.3 Clock Integration (Revised)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Complete Backtest Clock Flow                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  RunManager.start(run_id) where run.mode == BACKTEST:                   │
│                                                                         │
│  1. Create BacktestClock                                                │
│     clock = BacktestClock(start, end, timeframe)                        │
│                                                                         │
│  2. Initialize Greta (set run context)                                  │
│     await greta.initialize(run_id, symbols, ...)                        │
│                                                                         │
│  3. Initialize Marvin (load strategy)                                   │
│     await marvin.initialize(run_id, strategy_id, ...)                   │
│                                                                         │
│  4. Register tick handler chain                                         │
│     clock.on_tick(async (tick) => {                                     │
│         # 1. Greta updates current bar                                  │
│         await greta.advance_to(tick.ts)                                 │
│                                                                         │
│         # 2. Marvin processes tick (emits strategy events)              │
│         await marvin.on_tick(tick)                                      │
│                                                                         │
│         # 3. Greta processes pending orders (simulate fills)            │
│         await greta.process_pending_orders(tick.ts)                     │
│     })                                                                  │
│                                                                         │
│  5. Start clock                                                         │
│     await clock.start(run_id)                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Single Tick Processing Order:
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   BacktestClock                                                        │
│       │                                                                │
│       │  tick @ 09:31:00                                               │
│       ▼                                                                │
│   ┌────────────────┐                                                   │
│   │ Greta.advance  │  Update current_bars to 09:31:00                  │
│   │ _to(09:31:00)  │  Process previous tick's pending orders           │
│   └───────┬────────┘                                                   │
│           │                                                            │
│           │  emit data.WindowReady (if strategy requested data)        │
│           │  emit orders.Filled (if any orders filled)                 │
│           ▼                                                            │
│   ┌────────────────┐                                                   │
│   │ Marvin.on_tick │  Strategy processing                              │
│   │ (09:31:00)     │  - Receives data, orders events                   │
│   └───────┬────────┘  - Computes signals                               │
│           │           - emit strategy.PlaceRequest                     │
│           │                                                            │
│           │  (events go through GLaDOS router)                         │
│           ▼                                                            │
│   ┌────────────────┐                                                   │
│   │ Greta receives │  backtest.PlaceOrder → queue for next tick       │
│   │ routed events  │                                                   │
│   └───────┬────────┘                                                   │
│           │                                                            │
│           │  ack (if backpressure enabled)                             │
│           ▼                                                            │
│   BacktestClock advances to 09:32:00...                                │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    
    def update_mark(self, price: Decimal) -> None:
        """Update market value and unrealized P&L."""
        self.market_value = self.qty * price
        self.unrealized_pnl = self.market_value - (self.qty * self.avg_entry_price)


@dataclass 
class BacktestStats:
    """Comprehensive backtest statistics."""
    
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
    """Complete backtest result."""
    
    run_id: str
    start_time: datetime
    end_time: datetime
    timeframe: str
    symbols: list[str]
    
    # Final state
    stats: BacktestStats
    final_equity: Decimal
    equity_curve: list[tuple[datetime, Decimal]]  # (timestamp, equity)
    
    # Trade log
    fills: list[SimulatedFill] = field(default_factory=list)
    
    # Timing
    simulation_duration_ms: int = 0
    total_bars_processed: int = 0
```

### A.5 Service Interfaces

```python
# src/greta/interfaces.py

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from src.veda.models import Bar, OrderIntent, OrderState


class HistoricalDataProvider(ABC):
    """Interface for providing historical market data."""
    
    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Get historical bars for a symbol."""
    
    @abstractmethod
    async def preload(
        self,
        symbols: list[str],
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> None:
        """Preload data into cache for faster simulation."""


class FillSimulator(ABC):
    """Interface for simulating order fills."""
    
    @abstractmethod
    def simulate_fill(
        self,
        intent: OrderIntent,
        current_bar: Bar,
        config: "FillSimulationConfig",
    ) -> SimulatedFill | None:
        """
        Simulate a fill given current market conditions.
        
        Returns None if order cannot be filled (e.g., limit not reached).
        """


class BacktestEngine(ABC):
    """Interface for running backtests."""
    
    @abstractmethod
    async def run(
        self,
        run_id: str,
        symbols: list[str],
        timeframe: str,
        start: datetime,
        end: datetime,
        config: dict | None = None,
    ) -> BacktestResult:
        """Execute a full backtest."""
    
    @abstractmethod
    def on_tick(self, tick: "ClockTick") -> None:
        """Handle clock tick during backtest."""
```

### A.6 GretaService Design

```python
# src/greta/greta_service.py

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
    2. GretaService.initialize() preloads data
    3. Clock drives GretaService.advance_to() on each tick
    4. When run completes, GretaService.get_result() returns stats
    5. RunManager disposes the GretaService instance
    
    Orchestrates:
    - BarRepository (shared) for historical bar data
    - FillSimulator for order simulation
    - Internal position tracking (per-run)
    - EventLog (shared) for event emission (events tagged with run_id)
    
    Design Principles:
    1. Same event interface as VedaService
    2. Strategies don't know if live or backtest
    3. Clock drives simulation via advance_to()
    4. Complete isolation between concurrent runs
    """
    
    def __init__(
        self,
        run_id: str,  # Required - identifies which run this instance serves
        bar_repository: BarRepository,  # Shared singleton
        event_log: EventLog,  # Shared singleton
        fill_config: FillSimulationConfig | None = None,
    ) -> None:
        self._run_id = run_id  # This instance only serves this run
        self._bar_repo = bar_repository
        self._event_log = event_log
        self._fill_config = fill_config or FillSimulationConfig()
        self._fill_simulator = DefaultFillSimulator()
        
        # Per-run simulation state (isolated)
        self._symbols: list[str] = []
        self._timeframe: str = ""
        self._positions: dict[str, SimulatedPosition] = {}
        self._pending_orders: dict[str, OrderIntent] = {}
        self._fills: list[SimulatedFill] = []
        self._equity_curve: list[tuple[datetime, Decimal]] = []
        self._current_bars: dict[str, Bar] = {}  # symbol -> current bar
        
        # Stats
        self._stats = BacktestStats()
    
    async def initialize(
        self,
        run_id: str,
        symbols: list[str],
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> None:
        """Initialize for a new backtest run."""
        self._current_run_id = run_id
        self._positions = {}
        self._pending_orders = {}
        self._fills = []
        self._equity_curve = []
        self._stats = BacktestStats()
        
        # Preload historical data
        await self._data_provider.preload(symbols, timeframe, start, end)
    
    async def on_tick(self, tick: ClockTick) -> None:
        """
        Handle a clock tick.
        
        1. Update current bars for tick timestamp
        2. Process pending orders (simulate fills)
        3. Update positions with new prices
        4. Emit data.WindowReady for strategy
        5. Record equity curve point
        """
        # 1. Get bars for this tick
        for symbol in self._symbols:
            bar = await self._data_provider.get_bar_at(symbol, tick.ts)
            if bar:
                self._current_bars[symbol] = bar
        
        # 2. Process pending orders
        await self._process_pending_orders(tick)
        
        # 3. Update positions
        self._update_positions_mark()
        
        # 4. Emit data ready event
        await self._emit_data_ready(tick)
        
        # 5. Record equity
        self._record_equity(tick.ts)
    
    async def place_order(self, intent: OrderIntent) -> OrderState:
        """
        Submit an order for simulation.
        
        Market orders fill at next bar open.
        Limit orders wait until price condition met.
        """
        # Create order state (PENDING)
        state = self._create_order_state(intent)
        
        # For market orders: queue for fill at next tick
        # For limit orders: add to pending orders
        if intent.order_type == OrderType.MARKET:
            self._pending_orders[state.id] = intent
        else:
            self._pending_orders[state.id] = intent
        
        # Emit orders.Created
        await self._emit_order_event("orders.Created", state)
        
        return state
    
    def get_result(self) -> BacktestResult:
        """Get backtest result after completion."""
        self._stats = self._calculate_stats()
        return BacktestResult(
            run_id=self._current_run_id,
            stats=self._stats,
            final_equity=self._current_equity,
            equity_curve=self._equity_curve,
            fills=self._fills,
        )
```

### A.7 Fill Simulation Logic

```python
# src/greta/fill_simulator.py

class DefaultFillSimulator(FillSimulator):
    """
    Default fill simulator with slippage and fees.
    
    Fill Models:
    - MARKET orders: Fill at bar open/close + slippage
    - LIMIT BUY: Fill if low <= limit_price
    - LIMIT SELL: Fill if high >= limit_price
    - STOP orders: Trigger when price crosses stop_price
    """
    
    def simulate_fill(
        self,
        intent: OrderIntent,
        current_bar: Bar,
        config: FillSimulationConfig,
    ) -> SimulatedFill | None:
        """Simulate a fill given current bar."""
        
        # Determine base fill price
        if config.fill_at == "open":
            base_price = current_bar.open
        elif config.fill_at == "close":
            base_price = current_bar.close
        elif config.fill_at == "vwap":
            base_price = current_bar.vwap or current_bar.close
        else:  # "worst" - worst case for the trader
            base_price = self._worst_price(intent.side, current_bar)
        
        # Check if order can fill
        if intent.order_type == OrderType.LIMIT:
            if not self._limit_can_fill(intent, current_bar):
                return None
            base_price = intent.limit_price  # Fill at limit price
        
        elif intent.order_type == OrderType.STOP:
            if not self._stop_triggered(intent, current_bar):
                return None
            base_price = intent.stop_price  # Fill at stop price
        
        # Apply slippage (always unfavorable to trader)
        slippage = self._calculate_slippage(base_price, intent.side, config)
        fill_price = base_price + slippage if intent.side == OrderSide.BUY else base_price - slippage
        
        # Calculate commission
        commission = self._calculate_commission(intent.qty, fill_price, config)
        
        return SimulatedFill(
            order_id=intent.client_order_id,
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side.value,
            qty=intent.qty,
            fill_price=fill_price,
            commission=commission,
            slippage=abs(slippage * intent.qty),
            timestamp=current_bar.timestamp,
            bar_index=0,  # Set by caller
        )
    
    def _calculate_slippage(
        self,
        price: Decimal,
        side: OrderSide,
        config: FillSimulationConfig,
    ) -> Decimal:
        """Calculate slippage amount (always unfavorable)."""
        if config.slippage_model == "fixed":
            return price * (config.slippage_bps / Decimal("10000"))
        # Future: implement volume-based, volatility-based models
        return Decimal("0")
    
    def _calculate_commission(
        self,
        qty: Decimal,
        price: Decimal,
        config: FillSimulationConfig,
    ) -> Decimal:
        """Calculate commission."""
        notional = qty * price
        commission = notional * (config.commission_bps / Decimal("10000"))
        return max(commission, config.min_commission)
    
    def _limit_can_fill(self, intent: OrderIntent, bar: Bar) -> bool:
        """Check if limit order can fill given bar's range."""
        if intent.side == OrderSide.BUY:
            return bar.low <= intent.limit_price
        else:  # SELL
            return bar.high >= intent.limit_price
    
    def _stop_triggered(self, intent: OrderIntent, bar: Bar) -> bool:
        """Check if stop order is triggered."""
        if intent.side == OrderSide.BUY:
            return bar.high >= intent.stop_price
        else:  # SELL
            return bar.low <= intent.stop_price
```

### A.8 Historical Data Provider (MVP)

```python
# src/greta/data_provider.py

class CachedHistoricalDataProvider(HistoricalDataProvider):
    """
    Historical data provider with caching.
    
    MVP Implementation:
    - Uses Veda's ExchangeAdapter to fetch historical data
    - Caches all bars in memory during backtest
    - Provides O(1) lookup by timestamp
    
    Future:
    - SQLite/Parquet file caching
    - Incremental data fetching
    """
    
    def __init__(self, adapter: ExchangeAdapter) -> None:
        self._adapter = adapter
        # Cache: (symbol, timeframe) -> {timestamp: Bar}
        self._cache: dict[tuple[str, str], dict[datetime, Bar]] = {}
    
    async def preload(
        self,
        symbols: list[str],
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> None:
        """Preload all data for backtest period."""
        for symbol in symbols:
            bars = await self._adapter.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
            key = (symbol, timeframe)
            self._cache[key] = {bar.timestamp: bar for bar in bars}
    
    async def get_bar_at(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
    ) -> Bar | None:
        """Get bar at specific timestamp (O(1) from cache)."""
        key = (symbol, timeframe)
        if key not in self._cache:
            return None
        return self._cache[key].get(timestamp)
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Get bars in range from cache."""
        key = (symbol, timeframe)
        if key not in self._cache:
            return []
        
        return [
            bar for ts, bar in sorted(self._cache[key].items())
            if start <= ts <= end
        ]
```

### A.9 Integration with RunManager

```python
# Changes to src/glados/services/run_manager.py

class RunManager:
    """Updated to integrate with Clock and Greta."""
    
    def __init__(
        self,
        event_log: EventLog | None = None,
        veda_service: VedaService | None = None,
        greta_service: GretaService | None = None,
    ) -> None:
        self._runs: dict[str, Run] = {}
        self._event_log = event_log
        self._veda_service = veda_service
        self._greta_service = greta_service
        self._clocks: dict[str, BaseClock] = {}  # run_id -> clock
    
    async def start(self, run_id: str) -> Run:
        """Start a run with appropriate clock."""
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        
        if run.status != RunStatus.PENDING:
            raise RunNotStartableError(run_id, run.status.value)
        
        # Create and configure clock based on mode
        if run.mode == RunMode.BACKTEST:
            clock = BacktestClock(
                start_time=run.start_time,
                end_time=run.end_time,
                timeframe=run.timeframe,
            )
            # Initialize Greta
            await self._greta_service.initialize(
                run_id=run.id,
                symbols=run.symbols,
                timeframe=run.timeframe,
                start=run.start_time,
                end=run.end_time,
            )
            # Wire tick handler
            clock.on_tick(self._greta_service.on_tick)
        else:
            clock = RealtimeClock(timeframe=run.timeframe)
            # Wire to Veda (future)
        
        self._clocks[run_id] = clock
        
        # Update status
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        await self._emit_event(RunEvents.STARTED, run)
        
        # Start clock (non-blocking for realtime, blocking for backtest)
        asyncio.create_task(clock.start(run_id))
        
        return run
```

### A.10 Event Flow (Backtest)

```
                    ┌─────────────────────────────────────────────────────┐
                    │                    Backtest Run                      │
                    └─────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
            ┌───────▼───────┐         ┌───────▼───────┐         ┌───────▼───────┐
            │ 1. Initialize │         │ 2. Tick Loop  │         │ 3. Complete   │
            └───────┬───────┘         └───────┬───────┘         └───────┬───────┘
                    │                         │                         │
    run.Created ────┤     clock.Tick ─────────┤         run.Stopped ────┤
                    │     data.WindowReady ───┤                         │
                    │     orders.Filled ──────┤                         │
                    │     orders.Rejected ────┤                         │
                    ▼                         ▼                         ▼
```

### A.11 Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/greta/__init__.py` | Modify | Export GretaService, models |
| `src/greta/models.py` | Create | Backtest data models |
| `src/greta/interfaces.py` | Create | Abstract interfaces |
| `src/greta/greta_service.py` | Create | Main service class |
| `src/greta/fill_simulator.py` | Create | Fill simulation logic |
| `src/greta/data_provider.py` | Create | Historical data caching |
| `src/greta/stats_calculator.py` | Create | Performance metrics |
| `src/glados/services/run_manager.py` | Modify | Integrate clock + Greta |
| `src/glados/app.py` | Modify | Wire GretaService in lifespan |
| `src/glados/dependencies.py` | Modify | Add get_greta_service() |
| `src/events/types.py` | Modify | Add backtest-specific events |

---

## Part B: MVP Execution Plan (Revised)

### ⚠️ Important Architecture Note

M4's goal is to make the complete backtest flow work, which requires:

1. **Greta**: Simulates trading environment
2. **Marvin (minimal skeleton)**: Provides a runnable test strategy
3. **WallE**: Provides/caches historical data
4. **GLaDOS**: Orchestrates everything

Cannot implement Greta in isolation without module coordination!

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Complete Flow to Implement in M4                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  POST /runs { mode: "backtest", strategy_id: "test-sma" }               │
│      │                                                                  │
│      ▼                                                                  │
│  RunManager.create() → run.Created                                      │
│      │                                                                  │
│      ▼                                                                  │
│  POST /runs/{id}/start                                                  │
│      │                                                                  │
│      ▼                                                                  │
│  RunManager.start(run_id)                                               │
│      │                                                                  │
│      │  ┌─────────────────────────────────────────────────────────┐     │
│      │  │  CREATE PER-RUN INSTANCES (isolated for this run)       │     │
│      │  │                                                         │     │
│      │  │  greta = GretaService(                                  │     │
│      │  │      run_id=run.id,                                     │     │
│      │  │      bar_repository=self._bar_repo,  # shared singleton │     │
│      │  │      event_log=self._event_log,      # shared singleton │     │
│      │  │  )                                                      │     │
│      │  │                                                         │     │
│      │  │  strategy = self._strategy_loader.load(run.strategy_id) │     │
│      │  │  runner = StrategyRunner(                               │     │
│      │  │      run_id=run.id,                                     │     │
│      │  │      strategy=strategy,                                 │     │
│      │  │      event_log=self._event_log,      # shared singleton │     │
│      │  │  )                                                      │     │
│      │  │                                                         │     │
│      │  │  clock = BacktestClock(start, end, timeframe)           │     │
│      │  │                                                         │     │
│      │  │  # Store in per-run registry                            │     │
│      │  │  self._run_contexts[run.id] = RunContext(               │     │
│      │  │      greta=greta, runner=runner, clock=clock            │     │
│      │  │  )                                                      │     │
│      │  └─────────────────────────────────────────────────────────┘     │
│      │                                                                  │
│      ├── Initialize Greta (preload historical data)                     │
│      ├── Initialize Marvin (load strategy)                              │
│      └── Start tick loop                                                │
│              │                                                          │
│              ▼                                                          │
│          ┌─────────────────────────────────────────────┐                │
│          │  For each tick:                             │                │
│          │    1. Greta.advance_to(tick.ts)             │                │
│          │       - Update current bars                 │                │
│          │       - Fill pending orders                 │                │
│          │       - emit data.*, orders.* (with run_id) │                │
│          │                                             │                │
│          │    2. Marvin.on_tick(tick)                  │                │
│          │       - Receive data.WindowReady            │                │
│          │       - Run strategy logic                  │                │
│          │       - emit strategy.PlaceRequest          │                │
│          │                                             │                │
│          │    3. GLaDOS routes strategy.* → backtest.* │                │
│          │       - Greta queues orders for next tick   │                │
│          └─────────────────────────────────────────────┘                │
│              │                                                          │
│              ▼ (when clock.end reached)                                 │
│  run.Completed + BacktestResult                                         │
│      │                                                                  │
│      ▼                                                                  │
│  Cleanup: del self._run_contexts[run.id]  # dispose per-run instances   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Multi-Run Example:
┌─────────────────────────────────────────────────────────────────────────┐
│  User starts 3 runs simultaneously:                                     │
│                                                                         │
│  Run A: backtest SMA on BTC 2024-01-01 to 2024-06-30                   │
│  Run B: backtest RSI on ETH 2024-03-01 to 2024-09-30                   │
│  Run C: live trading SMA on BTC                                         │
│                                                                         │
│  RunManager._run_contexts = {                                           │
│      "run-A": RunContext(GretaService_A, StrategyRunner_A, Clock_A),   │
│      "run-B": RunContext(GretaService_B, StrategyRunner_B, Clock_B),   │
│      "run-C": RunContext(None, StrategyRunner_C, Clock_C),  # no Greta │
│  }                                                                      │
│                                                                         │
│  All runs share:                                                        │
│  - EventLog (events tagged with run_id for isolation)                  │
│  - BarRepository (historical data is immutable, safe to share)         │
│  - DomainRouter (looks up run mode to route correctly)                 │
│                                                                         │
│  Each run has isolated:                                                 │
│  - GretaService (positions, orders, equity specific to that run)       │
│  - StrategyRunner (strategy state specific to that run)                │
│  - Clock (time progression specific to that run)                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### MVP-1: WallE BarRepository (~2 hours)

**Goal**: Implement historical data storage layer (Greta fetches data from here).

**Why first**: Greta needs historical data, which should come from WallE, not direct exchange calls.

**Tasks**:
1. Create `src/walle/models.py` with `BarRecord` model
2. Create Alembic migration for `bars` table
3. Create `src/walle/repositories/bar_repository.py`
4. Implement `save_bars()` and `get_bars()` methods

**Schema**:
```python
# src/walle/models.py
class BarRecord(Base):
    __tablename__ = "bars"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[Decimal]
    high: Mapped[Decimal]
    low: Mapped[Decimal]
    close: Mapped[Decimal]
    volume: Mapped[Decimal]
    
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_bar'),
        Index('ix_bars_lookup', 'symbol', 'timeframe', 'timestamp'),
    )
```

**Tests**:
```python
# tests/unit/walle/test_bar_repository.py
class TestBarRepository:
    async def test_save_and_get_bars(self, session_factory):
        repo = BarRepository(session_factory)
        bars = [make_bar(ts=datetime(2024, 1, 1, 9, 30))]
        
        await repo.save_bars(bars)
        result = await repo.get_bars("BTC/USD", "1m", start, end)
        
        assert len(result) == 1
        assert result[0].close == bars[0].close
    
    async def test_get_bars_returns_sorted(self, session_factory):
        repo = BarRepository(session_factory)
        # Save out of order
        await repo.save_bars([bar3, bar1, bar2])
        
        result = await repo.get_bars(...)
        
        assert result[0].timestamp < result[1].timestamp < result[2].timestamp
```

**Exit Criteria**: BarRepository can store and query historical bars.

---

### MVP-2: Greta Models & FillSimulator (~2 hours)

**Goal**: Implement Greta's core data structures and fill simulation logic.

**Tasks**:
1. Create `src/greta/models.py` with all data classes
2. Create `src/greta/fill_simulator.py` with `DefaultFillSimulator`
3. Add backtest event types to `src/events/types.py`
4. Update `src/greta/__init__.py` with exports

**Tests**:
```python
# tests/unit/greta/test_fill_simulator.py
class TestDefaultFillSimulator:
    def test_market_buy_fills_with_slippage(self):
        simulator = DefaultFillSimulator()
        intent = make_order_intent(side=OrderSide.BUY, order_type=OrderType.MARKET)
        bar = make_bar(open=Decimal("42000"))
        config = FillSimulationConfig(slippage_bps=Decimal("5"))
        
        fill = simulator.simulate_fill(intent, bar, config)
        
        # Slippage is unfavorable: BUY pays more
        assert fill.fill_price > Decimal("42000")
        assert fill.slippage > Decimal("0")
    
    def test_limit_buy_fills_when_low_touches_limit(self):
        intent = make_order_intent(
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal("41000"),
        )
        bar = make_bar(low=Decimal("40900"))  # Low below limit
        
        fill = simulator.simulate_fill(intent, bar, config)
        
        assert fill is not None
        assert fill.fill_price == Decimal("41000")
    
    def test_limit_buy_no_fill_when_price_too_high(self):
        intent = make_order_intent(limit_price=Decimal("40000"))
        bar = make_bar(low=Decimal("41000"))  # Low above limit
        
        fill = simulator.simulate_fill(intent, bar, config)
        
        assert fill is None  # Cannot fill
```

**Exit Criteria**: Fill simulator correctly handles market/limit orders.

---

### MVP-3: GretaService Core (~2.5 hours)

**Goal**: Implement Greta main service, connected to WallE.

**Key Design**: GretaService fetches data from BarRepository, NOT directly from ExchangeAdapter.

**Tasks**:
1. Create `src/greta/greta_service.py`
2. Inject `BarRepository` (not ExchangeAdapter)
3. Implement `initialize()` - preload bars from WallE
4. Implement `advance_to(timestamp)` - update current bar, process orders
5. Implement `handle_place_order(intent)` - queue for simulation
6. Implement position tracking and event emission

```python
# src/greta/greta_service.py

class GretaService:
    """
    Backtest execution environment.
    
    Key difference from earlier design:
    - Gets data from BarRepository (WallE), NOT from ExchangeAdapter
    - If data not in WallE, GLaDOS's MarketDataService fetches and caches
    """
    
    def __init__(
        self,
        bar_repository: BarRepository,  # From WallE
        event_log: EventLog,
        fill_config: FillSimulationConfig | None = None,
    ) -> None:
        self._bar_repo = bar_repository
        self._event_log = event_log
        self._fill_simulator = DefaultFillSimulator()
        self._fill_config = fill_config or FillSimulationConfig()
        # ... rest of init
    
    async def initialize(self, run_id: str, symbols: list[str], ...) -> None:
        """Initialize for backtest run."""
        self._run_id = run_id
        self._symbols = symbols
        
        # Load ALL bars from WallE into memory for fast access
        for symbol in symbols:
            bars = await self._bar_repo.get_bars(symbol, timeframe, start, end)
            self._bar_cache[symbol] = {bar.timestamp: bar for bar in bars}
    
    async def advance_to(self, timestamp: datetime) -> None:
        """Advance simulation to timestamp."""
        # Update current bars
        for symbol in self._symbols:
            self._current_bars[symbol] = self._bar_cache[symbol].get(timestamp)
        
        # Process pending orders with new prices
        await self._process_pending_orders(timestamp)
    
    async def handle_place_order(self, event: Envelope) -> None:
        """Handle backtest.PlaceOrder event."""
        intent = OrderIntent.from_payload(event.payload)
        # Queue for processing at next tick
        self._pending_orders[intent.client_order_id] = intent
        # Emit orders.Created
        await self._emit_order_created(intent)
```

**Tests**:
```python
class TestGretaService:
    async def test_initialize_loads_bars_from_repository(self):
        bar_repo = MockBarRepository()
        bar_repo.set_bars("BTC/USD", [bar1, bar2, bar3])
        service = GretaService(bar_repo, event_log)
        
        await service.initialize("run-1", ["BTC/USD"], "1m", start, end)
        
        bar_repo.get_bars.assert_called_with("BTC/USD", "1m", start, end)
    
    async def test_advance_to_fills_market_orders(self):
        service = GretaService(bar_repo, event_log)
        await service.initialize(...)
        await service.handle_place_order(make_place_order_event())
        
        await service.advance_to(datetime(2024, 1, 1, 9, 31))
        
        events = await event_log.read(0, 10)
        assert any(e.type == "orders.Filled" for e in events)
```

**Exit Criteria**: GretaService loads data from WallE and processes orders.

---

### MVP-4: Marvin Skeleton (~2 hours)

**Goal**: Implement minimal Marvin skeleton to support backtest testing.

**Why needed**: Without Marvin emitting `strategy.*` events, backtest flow cannot complete.

**Tasks**:
1. Create `src/marvin/strategy_runner.py` - runs strategy code
2. Create `src/marvin/test_strategy.py` - simple test strategy
3. Implement tick handling and event emission
4. Connect to EventLog for receiving data events

```python
# src/marvin/strategy_runner.py

class StrategyRunner:
    """
    Runs strategy code in response to clock ticks.
    
    Mode-agnostic: doesn't know if backtest or live.
    """
    
    def __init__(
        self,
        strategy: "BaseStrategy",
        event_log: EventLog,
    ) -> None:
        self._strategy = strategy
        self._event_log = event_log
        self._run_id: str | None = None
    
    async def initialize(self, run_id: str, symbols: list[str]) -> None:
        """Initialize for a run."""
        self._run_id = run_id
        await self._strategy.initialize(symbols)
    
    async def on_tick(self, tick: ClockTick) -> None:
        """Handle clock tick."""
        # Strategy computes and may emit events
        actions = await self._strategy.on_tick(tick)
        
        for action in actions:
            if action.type == "fetch_window":
                await self._emit_fetch_window(action)
            elif action.type == "place_order":
                await self._emit_place_request(action)
    
    async def on_data_ready(self, event: Envelope) -> None:
        """Handle data.WindowReady event."""
        await self._strategy.on_data(event.payload)


# src/marvin/test_strategy.py

class TestStrategy(BaseStrategy):
    """
    Simple strategy for testing backtest flow.
    
    Logic: Buy when price drops 1%, sell when up 1%.
    """
    
    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]:
        actions = []
        
        # Request data window
        actions.append(StrategyAction(
            type="fetch_window",
            symbol="BTC/USD",
            lookback=10,
        ))
        
        return actions
    
    async def on_data(self, data: dict) -> list[StrategyAction]:
        # Simple logic: buy if current < avg, sell if current > avg
        bars = data["bars"]
        if len(bars) < 2:
            return []
        
        current = bars[-1].close
        avg = sum(b.close for b in bars) / len(bars)
        
        if current < avg * Decimal("0.99") and not self._has_position:
            return [StrategyAction(type="place_order", side="buy", qty=Decimal("1"))]
        elif current > avg * Decimal("1.01") and self._has_position:
            return [StrategyAction(type="place_order", side="sell", qty=Decimal("1"))]
        
        return []
```

**Tests**:
```python
class TestStrategyRunner:
    async def test_on_tick_emits_fetch_window(self):
        strategy = TestStrategy()
        runner = StrategyRunner(strategy, event_log)
        await runner.initialize("run-1", ["BTC/USD"])
        
        await runner.on_tick(make_tick())
        
        events = await event_log.read(0, 10)
        assert any(e.type == "strategy.FetchWindow" for e in events)
```

**Exit Criteria**: Marvin can run test strategy and emit events.

---

### MVP-5: GLaDOS Domain Router (~1.5 hours)

**Goal**: Implement strategy.* → backtest.* event routing.

**Tasks**:
1. Create `src/glados/services/domain_router.py`
2. Implement event routing based on run mode
3. Register router as event consumer

```python
# src/glados/services/domain_router.py

class DomainRouter:
    """
    Routes strategy events to appropriate domain.
    
    strategy.FetchWindow → live.FetchWindow (if live)
    strategy.FetchWindow → backtest.FetchWindow (if backtest)
    """
    
    def __init__(self, event_log: EventLog, run_manager: RunManager):
        self._event_log = event_log
        self._run_manager = run_manager
    
    async def route(self, event: Envelope) -> None:
        """Route strategy event to correct domain."""
        if not event.type.startswith("strategy."):
            return
        
        run = await self._run_manager.get(event.run_id)
        if run is None:
            return
        
        # Determine target domain
        if run.mode == RunMode.BACKTEST:
            target_domain = "backtest"
        else:
            target_domain = "live"
        
        # Rewrite event type
        new_type = event.type.replace("strategy.", f"{target_domain}.")
        
        # Emit routed event
        routed = Envelope(
            type=new_type,
            payload=event.payload,
            run_id=event.run_id,
            corr_id=event.corr_id,
            causation_id=event.id,
            producer="glados.router",
        )
        await self._event_log.append(routed)
```

**Tests**:
```python
class TestDomainRouter:
    async def test_routes_strategy_to_backtest(self):
        run_manager.create(RunCreate(mode=RunMode.BACKTEST, ...))
        router = DomainRouter(event_log, run_manager)
        
        event = make_event(type="strategy.FetchWindow", run_id=run.id)
        await router.route(event)
        
        events = await event_log.read(0, 10)
        assert any(e.type == "backtest.FetchWindow" for e in events)
```

**Exit Criteria**: Events are correctly routed.

---

### MVP-6: Run Orchestration (~2 hours)

**Goal**: Orchestrate complete backtest flow in RunManager.

**Tasks**:
1. Update `RunManager.start()` to orchestrate backtest
2. Create BacktestClock and wire tick handlers
3. Coordinate Greta ↔ Marvin ↔ Router
4. Handle completion

```python
# Updated src/glados/services/run_manager.py

async def start(self, run_id: str) -> Run:
    """Start a run with full orchestration."""
    run = self._runs[run_id]
    
    if run.mode == RunMode.BACKTEST:
        # 1. Create clock
        clock = BacktestClock(run.start_time, run.end_time, run.timeframe)
        
        # 2. Initialize Greta
        await self._greta_service.initialize(
            run.id, run.symbols, run.timeframe, run.start_time, run.end_time
        )
        
        # 3. Initialize Marvin with strategy
        strategy = self._strategy_loader.load(run.strategy_id)
        self._strategy_runners[run.id] = StrategyRunner(strategy, self._event_log)
        await self._strategy_runners[run.id].initialize(run.id, run.symbols)
        
        # 4. Wire tick handler
        async def on_tick(tick: ClockTick):
            # a. Greta advances (fills orders, updates prices)
            await self._greta_service.advance_to(tick.ts)
            
            # b. Marvin processes tick (emits strategy events)
            await self._strategy_runners[run.id].on_tick(tick)
            
            # c. Route events (strategy.* → backtest.*)
            # This happens automatically via event log consumption
        
        clock.on_tick(on_tick)
        
        # 5. Start (runs to completion for backtest)
        await clock.start(run.id)
        
        # 6. Backtest complete
        run.status = RunStatus.COMPLETED
        await self._emit_event(RunEvents.COMPLETED, run)
```

**Tests**:
```python
class TestRunManagerBacktest:
    async def test_start_backtest_runs_to_completion(self):
        run = await run_manager.create(RunCreate(
            strategy_id="test-strategy",
            mode=RunMode.BACKTEST,
            start_time=datetime(2024, 1, 1, 9, 30),
            end_time=datetime(2024, 1, 1, 10, 30),  # 1 hour
        ))
        
        await run_manager.start(run.id)
        
        # Backtest should complete (it's fast)
        updated = await run_manager.get(run.id)
        assert updated.status == RunStatus.COMPLETED
```

**Exit Criteria**: Complete backtest flow can run.

---

### MVP-7: Integration Test (~1.5 hours)

**Goal**: End-to-end verification of backtest flow.

**Tasks**:
1. Create `tests/integration/test_backtest_flow.py`
2. Test via API: create → start → verify completion
3. Verify events: run.Created → clock.Tick → orders.* → run.Completed
4. Verify stats calculated

**Tests**:
```python
# tests/integration/test_backtest_flow.py

class TestBacktestFlow:
    async def test_full_backtest_via_api(self, test_client, seed_historical_data):
        # Create run
        response = await test_client.post("/runs", json={
            "strategy_id": "test-strategy",
            "mode": "backtest",
            "symbols": ["BTC/USD"],
            "timeframe": "1m",
            "start_time": "2024-01-01T09:30:00Z",
            "end_time": "2024-01-01T10:30:00Z",
        })
        run_id = response.json()["id"]
        
        # Start run
        await test_client.post(f"/runs/{run_id}/start")
        
        # Wait for completion (backtest is fast)
        await asyncio.sleep(0.5)
        
        # Verify completed
        response = await test_client.get(f"/runs/{run_id}")
        assert response.json()["status"] == "completed"
    
    async def test_backtest_emits_correct_events(self, event_log, ...):
        # ... run backtest ...
        
        events = await event_log.read(0, 1000)
        event_types = [e.type for e in events]
        
        # Verify event sequence
        assert "run.Created" in event_types
        assert "run.Started" in event_types
        assert "clock.Tick" in event_types
        assert "strategy.FetchWindow" in event_types
        assert "backtest.FetchWindow" in event_types  # Routed
        assert "data.WindowReady" in event_types
        assert "run.Completed" in event_types
```

**Exit Criteria**: Complete backtest flow passes API test.

---

## Part C: Files to Create/Modify (Revised)

| File | Action | Description |
|------|--------|-------------|
| **WallE** | | |
| `src/walle/models.py` | Modify | Add `BarRecord` model |
| `src/walle/migrations/xxx_add_bars.py` | Create | Alembic migration |
| `src/walle/repositories/__init__.py` | Create | Repository exports |
| `src/walle/repositories/bar_repository.py` | Create | Bar data access |
| **Greta** | | |
| `src/greta/__init__.py` | Modify | Export GretaService, models |
| `src/greta/models.py` | Create | Backtest data models |
| `src/greta/fill_simulator.py` | Create | Fill simulation logic |
| `src/greta/greta_service.py` | Create | Main service (uses BarRepository) |
| **Marvin** | | |
| `src/marvin/__init__.py` | Modify | Export StrategyRunner |
| `src/marvin/base_strategy.py` | Create | Strategy base class |
| `src/marvin/strategy_runner.py` | Create | Runs strategy code |
| `src/marvin/test_strategy.py` | Create | Simple test strategy |
| **GLaDOS** | | |
| `src/glados/services/domain_router.py` | Create | Event routing |
| `src/glados/services/run_manager.py` | Modify | Orchestrate backtest |
| `src/glados/app.py` | Modify | Wire all services |
| `src/glados/dependencies.py` | Modify | Add getters |
| **Events** | | |
| `src/events/types.py` | Modify | Add backtest events |

---

## Part D: Entry/Exit Checklists (Revised)

### Entry Checklist (Before Starting M4)

- [x] All M3.5 tasks complete
- [x] Routes use `Depends()` from dependencies.py
- [x] `POST /runs` emits `runs.Created` event
- [x] SSE receives events from EventLog
- [x] All tests passing (507)
- [x] M4 design document reviewed ← **You are here**

### Exit Checklist (M4 Complete)

**WallE**:
- [ ] `bars` table exists (migration created)
- [ ] `BarRepository` can save/get bars

**Greta**:
- [ ] `GretaService` created and tested
- [ ] Fill simulator handles market/limit orders
- [ ] Gets data from `BarRepository` (not ExchangeAdapter directly)
- [ ] Emits `data.*` and `orders.*` events

**Marvin**:
- [ ] `StrategyRunner` handles tick events
- [ ] `TestStrategy` can emit strategy events
- [ ] Receives `data.WindowReady` and reacts

**GLaDOS**:
- [ ] `DomainRouter` routes `strategy.*` → `backtest.*`
- [ ] `RunManager.start()` orchestrates full flow
- [ ] BacktestClock wired correctly

**Integration**:
- [ ] `POST /runs` with mode=backtest works
- [ ] `POST /runs/{id}/start` runs to completion
- [ ] All events emitted in correct sequence
- [ ] Tests: **+70 new tests**, all passing

---

## Part E: Test Specifications Summary (Revised)

| MVP | Test File | Test Count |
|-----|-----------|------------|
| MVP-1 | `tests/unit/walle/test_bar_repository.py` | ~6 |
| MVP-2 | `tests/unit/greta/test_fill_simulator.py` | ~10 |
| MVP-3 | `tests/unit/greta/test_greta_service.py` | ~12 |
| MVP-4 | `tests/unit/marvin/test_strategy_runner.py` | ~8 |
| MVP-4 | `tests/unit/marvin/test_test_strategy.py` | ~6 |
| MVP-5 | `tests/unit/glados/services/test_domain_router.py` | ~8 |
| MVP-6 | `tests/unit/glados/services/test_run_manager_backtest.py` | ~10 |
| MVP-7 | `tests/integration/test_backtest_flow.py` | ~5 |
| | **Factories** | ~5 |
| **Total** | | **~70** |

---

## Appendix: Service Dependency Graph (Revised for Multi-Run)

```
                              ┌─────────────────────────────────────────┐
                              │              RunManager                 │
                              │  (manages multiple concurrent runs)     │
                              └──────────────────┬──────────────────────┘
                                                 │
                  ┌──────────────────────────────┼──────────────────────────────┐
                  │                              │                              │
                  ▼                              ▼                              ▼
    ┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
    │   RunContext (run-001)  │   │   RunContext (run-002)  │   │   RunContext (run-003)  │
    │   ─────────────────────────────────────────────────────────────────────────────────│
    │   mode: BACKTEST        │   │   mode: BACKTEST        │   │   mode: LIVE            │
    │   ┌─────────────────┐   │   │   ┌─────────────────┐   │   │   ┌─────────────────┐   │
    │   │ GretaService    │   │   │   │ GretaService    │   │   │   │ (no Greta)      │   │
    │   │ (per-run)       │   │   │   │ (per-run)       │   │   │   │                 │   │
    │   └─────────────────┘   │   │   └─────────────────┘   │   │   └─────────────────┘   │
    │   ┌─────────────────┐   │   │   ┌─────────────────┐   │   │   ┌─────────────────┐   │
    │   │ StrategyRunner  │   │   │   │ StrategyRunner  │   │   │   │ StrategyRunner  │   │
    │   │ (per-run)       │   │   │   │ (per-run)       │   │   │   │ (per-run)       │   │
    │   └─────────────────┘   │   │   └─────────────────┘   │   │   └─────────────────┘   │
    │   ┌─────────────────┐   │   │   ┌─────────────────┐   │   │   ┌─────────────────┐   │
    │   │ BacktestClock   │   │   │   │ BacktestClock   │   │   │   │ RealtimeClock   │   │
    │   │ (per-run)       │   │   │   │ (per-run)       │   │   │   │ (per-run)       │   │
    │   └─────────────────┘   │   │   └─────────────────┘   │   │   └─────────────────┘   │
    └───────────┬─────────────┘   └───────────┬─────────────┘   └───────────┬─────────────┘
                │                             │                             │
                └─────────────────────────────┼─────────────────────────────┘
                                              │
                          Events tagged with run_id for isolation
                                              │
                                              ▼
                        ┌─────────────────────────────────────────┐
                        │          SHARED SINGLETONS              │
                        ├─────────────────────────────────────────┤
                        │                                         │
                        │  ┌───────────────────────────────────┐  │
                        │  │ EventLog                          │  │
                        │  │ - Single outbox table             │  │
                        │  │ - Events have run_id field        │  │
                        │  │ - Consumers filter by run_id      │  │
                        │  └───────────────────────────────────┘  │
                        │                                         │
                        │  ┌───────────────────────────────────┐  │
                        │  │ BarRepository (WallE)             │  │
                        │  │ - Historical data is immutable    │  │
                        │  │ - Safe to share between runs      │  │
                        │  │ - Memory efficient                │  │
                        │  └───────────────────────────────────┘  │
                        │                                         │
                        │  ┌───────────────────────────────────┐  │
                        │  │ DomainRouter                      │  │
                        │  │ - Looks up run mode by run_id     │  │
                        │  │ - Routes strategy.* → backtest.*  │  │
                        │  │   or strategy.* → live.*          │  │
                        │  └───────────────────────────────────┘  │
                        │                                         │
                        │  ┌───────────────────────────────────┐  │
                        │  │ SSEBroadcaster                    │  │
                        │  │ - Clients subscribe by run_id     │  │
                        │  │ - Filters events per connection   │  │
                        │  └───────────────────────────────────┘  │
                        │                                         │
                        └─────────────────────────────────────────┘
```

### Why Per-Run Instances for Greta/Marvin?

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Per-Run Instance Justification                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  State that MUST be isolated (per-run):                                 │
│  ├── Simulated positions (Run A's BTC position ≠ Run B's)              │
│  ├── Pending orders (Run A's limit order ≠ Run B's)                    │
│  ├── Equity curve (each run tracks its own P&L)                        │
│  ├── Current bar pointer (backtests may be at different times)         │
│  ├── Strategy indicators (SMA state ≠ RSI state)                       │
│  └── Fill history (Run A's fills ≠ Run B's fills)                      │
│                                                                         │
│  Benefits of per-run instances:                                         │
│  ├── Complete isolation - no state leaks between runs                  │
│  ├── Independent failure - Run A crash doesn't affect Run B            │
│  ├── Parallel execution - multiple backtests run concurrently          │
│  ├── Simple cleanup - dispose instance when run completes              │
│  └── Easier testing - mock one instance without affecting others       │
│                                                                         │
│  State that CAN be shared (singleton):                                  │
│  ├── Historical bars - immutable data, read-only access                │
│  ├── Event log - events tagged with run_id for isolation               │
│  ├── Router - stateless, routes based on run_id lookup                 │
│  └── SSE - filters by run_id per client connection                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow for Historical Bars

```
                    At backtest initialization:
                    
                    GretaService.initialize()
                            │
                            ▼
                    BarRepository.get_bars(symbol, start, end)
                            │
                            ├─── If data in DB ───► return bars
                            │
                            └─── If data incomplete ───► ??? (out of M4 scope)
                            
                    M4 Assumption: Historical data already in database
                    (via seed script or prior caching)
                    
                    Future (M5+): Implement auto-fetch for missing data
                    - GLaDOS MarketDataService
                    - Calls Veda ExchangeAdapter
                    - Caches to WallE
```

---

## Appendix: Why This Design Is Correct

### Problems with Earlier Design

```
❌ Greta directly using ExchangeAdapter
   - Violates module boundaries
   - Greta shouldn't know how to call real APIs

❌ No Marvin participation
   - Backtesting's purpose is to test strategies
   - Without strategy execution, backtest is meaningless

❌ Unclear historical data source
   - No specification of where data comes from
   - No data caching consideration

❌ Single-instance Greta
   - Would require complex per-run state management
   - Risk of state leaking between concurrent runs
```

### Corrected Design

```
✅ Greta gets data from WallE (BarRepository)
   - Follows architecture: WallE is persistence layer
   - Greta only simulates, doesn't fetch data

✅ Marvin skeleton implementation
   - Provides test strategy
   - Complete event flow: Marvin → GLaDOS → Greta → Marvin

✅ GLaDOS Domain Router
   - Implements strategy.* → backtest.* routing
   - This is explicitly stated in architecture docs

✅ Complete collaboration flow
   - Clock → Greta (advance) → Marvin (tick) → Router → Greta (order)

✅ Per-run instances for Greta/Marvin
   - Complete state isolation between concurrent runs
   - Supports multiple backtests + live trading simultaneously
   - Simple lifecycle management (create on start, dispose on complete)
   - Each module only handles its own responsibility
```

---

*Created: 2026-02-03*
*Revised: 2026-02-03 (Architecture fix: Added Marvin skeleton, WallE integration, DomainRouter)*
*Revised: 2026-02-03 (Translated to English)*

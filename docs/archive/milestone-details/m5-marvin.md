# M5: Marvin Core (Strategy System)

> **Status**: ⏳ NEXT  
> **Prerequisite**: M4 (Greta Backtesting Engine) ✅  
> **Target**: SMA strategy backtested successfully + Plugin architecture complete  
> **Estimated Effort**: ~2-3 weeks (5 MVPs, ~80 tests)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Architecture Overview](#3-architecture-overview)
4. [Detailed Design](#4-detailed-design)
5. [MVP Implementation Plan](#5-mvp-implementation-plan)
6. [Test Strategy](#6-test-strategy)
7. [Entry & Exit Gates](#7-entry--exit-gates)
8. [Risk & Mitigations](#8-risk--mitigations)
9. [Appendix](#9-appendix)

---

## 1. Executive Summary

M5 completes the Marvin strategy core system with plugin architecture. This milestone focuses on:

1. **EventLog Subscription**: Enable event-driven communication between components
2. **Data Flow Completion**: Wire `strategy.FetchWindow` → `data.WindowReady` event chain
3. **SMA Strategy**: Implement configurable SMA crossover strategy
4. **Plugin Architecture**: Auto-discovery strategy loader (sideload support)
5. **Code Quality**: Fix M4 deferred items (type safety, test fixtures)

> **Note**: Live Trading (AlpacaAdapter, VedaService routing, Live Order Flow) moved to M6.

### Key Deliverables

| Deliverable | Description |
|-------------|-------------|
| EventLog subscription | Pub/sub mechanism for event-driven flow |
| data.WindowReady flow | Complete event-driven data fetching |
| SMA Strategy | Moving average crossover with configurable parameters |
| PluginStrategyLoader | Auto-discovery, dependency resolution, delete safety |
| Code quality fixes | Type safety, test fixtures extraction |

### Success Criteria

- EventLog supports subscribe/unsubscribe pattern
- SMA strategy runs complete backtest with trades
- Strategy files can be deleted without breaking system
- ~80 new tests added (total: ~711)

---

## 2. Goals & Non-Goals

### Goals (In Scope)

| ID | Goal | Priority | MVP |
|----|------|----------|-----|
| G1 | EventLog subscription mechanism | P0 | M5-1 |
| G2 | Complete data.WindowReady event flow | P0 | M5-2 |
| G3 | Implement SMA crossover strategy | P0 | M5-3 |
| G4 | Plugin architecture for strategies (sideload) | P0 | M5-4 |
| G5 | SimulatedFill.side → OrderSide enum | P1 | M5-5 |
| G6 | Extract test fixtures to tests/fixtures/ | P1 | M5-5 |
| G7 | Fix ClockTick duplicate definition | P1 | M5-5 |
| G8 | Clock Union type (backtest + realtime) | P1 | M5-5 |

### Non-Goals (Out of Scope - Moved to M6)

| Item | Moved To |
|------|----------|
| Plugin architecture for adapters | M6 |
| Initialize AlpacaAdapter with real clients | M6 |
| Wire VedaService to order routes | M6 |
| Live order flow (paper mode) | M6 |
| Run mode integration (RealtimeClock) | M6 |

### Deferred (M7+)

| Item | Reason |
|------|--------|
| Multiple simultaneous strategies | High complexity |
| Strategy optimization/hyperparameter tuning | Requires infrastructure |
| Advanced backtest stats (Sharpe, drawdown) | M8 polish |
| LISTEN/NOTIFY real-time | Nice-to-have |

---

## 2.1 Plugin Architecture Design (G13, G14)

### Core Principles

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Plugin Architecture Principles                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. ZERO HARDCODED IMPORTS                                              │
│     - Package __init__.py should NOT import specific plugins            │
│     - Plugins are discovered at runtime via directory scanning          │
│                                                                         │
│  2. SELF-DESCRIBING PLUGINS                                             │
│     - Each plugin declares its ID, dependencies, and metadata           │
│     - Uses class decorators or module-level constants                   │
│                                                                         │
│  3. DELETE = WORKS                                                      │
│     - Deleting a plugin file should NOT break the system                │
│     - System gracefully handles missing plugins                         │
│     - Only error if a REQUIRED dependency is missing                    │
│                                                                         │
│  4. DEPENDENCY RESOLUTION                                               │
│     - Plugins can depend on other plugins (strategy → strategy)         │
│     - Loader resolves and validates dependencies                        │
│     - Topological sort for load order                                   │
│                                                                         │
│  5. LAZY LOADING                                                        │
│     - Plugins loaded only when requested by strategy_id/adapter_id      │
│     - Reduces startup time and memory footprint                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Strategy Plugin Structure

```
src/marvin/
├── __init__.py              # Only exports base classes, NO strategy imports
├── base_strategy.py         # BaseStrategy ABC - the plugin interface
├── strategy_loader.py       # PluginStrategyLoader with auto-discovery
├── strategy_runner.py       # Executes loaded strategies
│
└── strategies/              # Plugin directory (sideloadable)
    ├── __init__.py          # Empty or minimal
    ├── sample_strategy.py   # DELETE THIS → system still works
    ├── sma_strategy.py      # DELETE THIS → system still works
    └── composite/           # Strategies that depend on others
        └── multi_sma.py     # Depends on sma_strategy
```

### Strategy Plugin Protocol

```python
# Each strategy file must define:

# Option A: Class decorator
@strategy(
    id="sma-crossover",
    name="SMA Crossover Strategy",
    version="1.0.0",
    dependencies=[],  # List of strategy_ids this depends on
    author="weaver",
    description="Simple moving average crossover strategy"
)
class SMAStrategy(BaseStrategy):
    ...

# Option B: Module-level constant (simpler)
STRATEGY_META = {
    "id": "sma-crossover",
    "name": "SMA Crossover Strategy", 
    "version": "1.0.0",
    "dependencies": [],
    "class": "SMAStrategy",
}

class SMAStrategy(BaseStrategy):
    ...
```

### Exchange Adapter Plugin Structure

```
src/veda/
├── __init__.py              # Only exports interfaces, NO adapter imports
├── interfaces.py            # ExchangeAdapter ABC - the plugin interface
├── adapter_loader.py        # PluginAdapterLoader with auto-discovery
│
└── adapters/                # Plugin directory (sideloadable)
    ├── __init__.py          # Empty or minimal
    ├── alpaca_adapter.py    # DELETE THIS → system still works (if not used)
    ├── mock_adapter.py      # Testing adapter
    └── future/
        ├── binance_adapter.py   # Future: Binance support
        └── coinbase_adapter.py  # Future: Coinbase support
```

### Adapter Plugin Protocol

```python
# Each adapter file must define:

ADAPTER_META = {
    "id": "alpaca",
    "name": "Alpaca Markets",
    "version": "1.0.0",
    "supported_features": ["stocks", "crypto", "paper_trading"],
    "class": "AlpacaAdapter",
}

class AlpacaAdapter(ExchangeAdapter):
    ...
```

### Plugin Loader Design

```python
# src/marvin/strategy_loader.py

class PluginStrategyLoader(StrategyLoader):
    """
    Auto-discovering strategy loader.
    
    Scans strategies/ directory for valid strategy plugins,
    resolves dependencies, and loads on demand.
    """
    
    def __init__(self, plugin_dir: Path | None = None):
        self._plugin_dir = plugin_dir or Path(__file__).parent / "strategies"
        self._registry: dict[str, StrategyMeta] = {}
        self._loaded: dict[str, type[BaseStrategy]] = {}
        self._scan_plugins()
    
    def _scan_plugins(self) -> None:
        """Scan plugin directory for strategy metadata (without importing)."""
        for py_file in self._plugin_dir.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                meta = self._extract_metadata(py_file)
                if meta:
                    self._registry[meta.id] = meta
            except Exception as e:
                # Log warning but don't fail - plugin is skipped
                logger.warning(f"Failed to scan {py_file}: {e}")
    
    def _extract_metadata(self, path: Path) -> StrategyMeta | None:
        """Extract STRATEGY_META from file without full import."""
        # Use AST parsing to read STRATEGY_META constant
        ...
    
    def list_available(self) -> list[StrategyMeta]:
        """List all discovered strategies."""
        return list(self._registry.values())
    
    def load(self, strategy_id: str) -> BaseStrategy:
        """Load strategy with dependency resolution."""
        if strategy_id not in self._registry:
            raise StrategyNotFoundError(f"Strategy not found: {strategy_id}")
        
        meta = self._registry[strategy_id]
        
        # Resolve dependencies first
        for dep_id in meta.dependencies:
            if dep_id not in self._loaded:
                self.load(dep_id)  # Recursive load
        
        # Now import and instantiate
        if strategy_id not in self._loaded:
            module = import_module(meta.module_path)
            strategy_class = getattr(module, meta.class_name)
            self._loaded[strategy_id] = strategy_class
        
        return self._loaded[strategy_id]()
```

### Dependency Example

```python
# src/marvin/strategies/composite/ensemble_strategy.py

STRATEGY_META = {
    "id": "ensemble-v1",
    "name": "Ensemble Strategy",
    "version": "1.0.0",
    "dependencies": ["sma-crossover", "rsi-oversold"],  # Requires these
    "class": "EnsembleStrategy",
}

class EnsembleStrategy(BaseStrategy):
    """
    Combines signals from multiple sub-strategies.
    
    Dependencies are automatically loaded by PluginStrategyLoader.
    """
    
    def __init__(self, loader: StrategyLoader):
        super().__init__()
        # Load dependent strategies
        self._sma = loader.load("sma-crossover")
        self._rsi = loader.load("rsi-oversold")
    
    async def on_data(self, data: dict) -> list[StrategyAction]:
        # Combine signals from sub-strategies
        sma_actions = await self._sma.on_data(data)
        rsi_actions = await self._rsi.on_data(data)
        
        # Only trade if both agree
        if sma_actions and rsi_actions:
            if sma_actions[0].side == rsi_actions[0].side:
                return sma_actions
        return []
```

### Delete Safety Validation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Delete Safety Matrix                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DELETE sample_strategy.py                                              │
│  ├── System starts? ✅ YES (no hardcoded import)                        │
│  ├── Other strategies work? ✅ YES                                      │
│  └── Error only if: Run requests strategy_id="sample"                   │
│                                                                         │
│  DELETE sma_strategy.py                                                 │
│  ├── System starts? ✅ YES                                              │
│  ├── ensemble_strategy works? ❌ NO (dependency missing)                │
│  └── Error message: "Strategy 'ensemble-v1' requires 'sma-crossover'"   │
│                                                                         │
│  DELETE alpaca_adapter.py                                               │
│  ├── System starts? ✅ YES                                              │
│  ├── Backtest works? ✅ YES (uses mock or greta)                        │
│  ├── Live trading works? ❌ NO (adapter missing)                        │
│  └── Error message: "Adapter 'alpaca' not found"                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Overview

### 3.1 Current State (Post-M4)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Current Flow (M4)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Clock.tick() ──► StrategyRunner.on_tick() ──► Strategy.on_tick()       │
│                           │                           │                 │
│                           │                    StrategyAction           │
│                           │                   (fetch_window)            │
│                           │                           │                 │
│                           ▼                           ▼                 │
│              RunManager._handle_strategy_action()                       │
│                           │                                             │
│                    DIRECT CALL (not event-driven)                       │
│                           │                                             │
│                           ▼                                             │
│              GretaService.get_window() ──► bars                         │
│                           │                                             │
│                    DIRECT CALL BACK                                     │
│                           │                                             │
│                           ▼                                             │
│              Strategy.on_data(bars) ──► StrategyAction(place_order)     │
│                           │                                             │
│                           ▼                                             │
│              GretaService.place_order() ──► SimulatedFill               │
│                                                                         │
│  ⚠️ PROBLEM: No events emitted! Direct method calls bypass EventLog    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Target State (M5)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Target Flow (M5)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Clock.tick() ──► StrategyRunner.on_tick() ──► Strategy.on_tick()       │
│                                                        │                │
│                                                 StrategyAction          │
│                                                (fetch_window)           │
│                                                        │                │
│                                                        ▼                │
│                                    emit strategy.FetchWindow            │
│                                                        │                │
│                                                        ▼                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DomainRouter                                  │   │
│  │   run.mode == BACKTEST → route to backtest.FetchWindow          │   │
│  │   run.mode == LIVE     → route to live.FetchWindow              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                     │                              │                    │
│            BACKTEST │                              │ LIVE               │
│                     ▼                              ▼                    │
│  ┌──────────────────────────┐      ┌──────────────────────────┐        │
│  │       GretaService       │      │       VedaService        │        │
│  │  handle backtest.*       │      │   handle live.*          │        │
│  │  fetch from BarRepo      │      │   fetch from Alpaca API  │        │
│  └────────────┬─────────────┘      └────────────┬─────────────┘        │
│               │                                  │                      │
│               └──────────────┬───────────────────┘                      │
│                              │                                          │
│                              ▼                                          │
│                    emit data.WindowReady                                │
│                              │                                          │
│                              ▼                                          │
│              StrategyRunner.on_data_ready() (subscribed)                │
│                              │                                          │
│                              ▼                                          │
│                    Strategy.on_data(payload)                            │
│                              │                                          │
│                       StrategyAction(place_order)                       │
│                              │                                          │
│                              ▼                                          │
│                    emit strategy.PlaceRequest                           │
│                              │                                          │
│                       (same routing pattern)                            │
│                              │                                          │
│                              ▼                                          │
│             Greta/Veda handles → emit orders.Filled                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Component Responsibilities

| Component | M4 State | M5 Target |
|-----------|----------|-----------|
| **StrategyRunner** | Emits strategy.* events ✅ | Subscribe to data.WindowReady |
| **DomainRouter** | Routes strategy.* → backtest.* ✅ | Add live.* routing |
| **GretaService** | Direct method calls | Subscribe to backtest.* events |
| **VedaService** | Created but unused | Subscribe to live.* events, wire to routes |
| **AlpacaAdapter** | Clients = None | Initialize real clients |
| **StrategyLoader** | Simple registry | File/config-based loading |

---

## 4. Detailed Design

### 4.1 Data Window Flow (strategy.FetchWindow → data.WindowReady)

#### Event Definitions

```python
# src/events/types.py - Already defined, need to USE them

class StrategyEvents:
    FETCH_WINDOW: Final[str] = "strategy.FetchWindow"
    PLACE_REQUEST: Final[str] = "strategy.PlaceRequest"
    DECISION_MADE: Final[str] = "strategy.DecisionMade"

class DataEvents:
    WINDOW_READY: Final[str] = "data.WindowReady"
    WINDOW_CHUNK: Final[str] = "data.WindowChunk"  # For large datasets
    WINDOW_COMPLETE: Final[str] = "data.WindowComplete"

class BacktestEvents:
    FETCH_WINDOW: Final[str] = "backtest.FetchWindow"
    PLACE_ORDER: Final[str] = "backtest.PlaceOrder"

class LiveEvents:
    FETCH_WINDOW: Final[str] = "live.FetchWindow"
    PLACE_ORDER: Final[str] = "live.PlaceOrder"
```

#### Payload Schemas

```python
# strategy.FetchWindow payload
{
    "run_id": "run-001",
    "symbol": "BTC/USD",
    "timeframe": "1m",
    "lookback": 20,  # Number of bars
    "end_time": "2024-01-01T10:00:00Z"  # Optional, defaults to current
}

# data.WindowReady payload
{
    "run_id": "run-001",
    "symbol": "BTC/USD",
    "timeframe": "1m",
    "bars": [
        {"timestamp": "...", "open": "100.0", "high": "101.0", ...},
        ...
    ],
    "request_id": "req-123"  # Correlation to original request
}
```

#### Sequence Diagram

```
┌──────────┐     ┌───────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Clock   │     │StrategyRunner │     │ DomainRouter│     │GretaService │     │BarRepository │
└────┬─────┘     └───────┬───────┘     └──────┬──────┘     └──────┬──────┘     └──────┬───────┘
     │                   │                    │                   │                   │
     │ tick()            │                    │                   │                   │
     │──────────────────>│                    │                   │                   │
     │                   │                    │                   │                   │
     │                   │ strategy.on_tick() │                   │                   │
     │                   │────────────────────│                   │                   │
     │                   │                    │                   │                   │
     │                   │ StrategyAction     │                   │                   │
     │                   │ (fetch_window)     │                   │                   │
     │                   │<───────────────────│                   │                   │
     │                   │                    │                   │                   │
     │                   │ emit strategy.FetchWindow              │                   │
     │                   │───────────────────>│                   │                   │
     │                   │                    │                   │                   │
     │                   │                    │ route to backtest.FetchWindow         │
     │                   │                    │──────────────────>│                   │
     │                   │                    │                   │                   │
     │                   │                    │                   │ get_bars()        │
     │                   │                    │                   │──────────────────>│
     │                   │                    │                   │                   │
     │                   │                    │                   │       bars        │
     │                   │                    │                   │<──────────────────│
     │                   │                    │                   │                   │
     │                   │                    │      emit data.WindowReady            │
     │                   │                    │<──────────────────│                   │
     │                   │                    │                   │                   │
     │                   │ deliver to subscriber                  │                   │
     │                   │<───────────────────│                   │                   │
     │                   │                    │                   │                   │
     │                   │ strategy.on_data() │                   │                   │
     │                   │────────────────────│                   │                   │
     │                   │                    │                   │                   │
```

#### Implementation Changes

**1. StrategyRunner - Add event subscription**

```python
# src/marvin/strategy_runner.py

class StrategyRunner:
    async def initialize(self, run_id: str, symbols: list[str]) -> None:
        self._run_id = run_id
        self._symbols = symbols
        await self._strategy.initialize(symbols)
        
        # Subscribe to data.WindowReady for this run
        await self._event_log.subscribe(
            event_types=[DataEvents.WINDOW_READY],
            callback=self._on_data_ready,
            filter_fn=lambda e: e.metadata.get("run_id") == self._run_id
        )
    
    async def _on_data_ready(self, envelope: Envelope) -> None:
        """Handle data.WindowReady event."""
        actions = await self._strategy.on_data(envelope.payload)
        for action in actions:
            await self._emit_action(action)
```

**2. GretaService - Subscribe to backtest.FetchWindow**

```python
# src/greta/greta_service.py

class GretaService:
    async def initialize(self, ...):
        # Existing initialization...
        
        # Subscribe to backtest events for this run
        await self._event_log.subscribe(
            event_types=[BacktestEvents.FETCH_WINDOW, BacktestEvents.PLACE_ORDER],
            callback=self._handle_backtest_event,
            filter_fn=lambda e: e.metadata.get("run_id") == self._run_id
        )
    
    async def _handle_backtest_event(self, envelope: Envelope) -> None:
        """Route backtest events to handlers."""
        if envelope.type == BacktestEvents.FETCH_WINDOW:
            await self._handle_fetch_window(envelope)
        elif envelope.type == BacktestEvents.PLACE_ORDER:
            await self._handle_place_order(envelope)
    
    async def _handle_fetch_window(self, envelope: Envelope) -> None:
        """Handle backtest.FetchWindow → emit data.WindowReady."""
        payload = envelope.payload
        bars = await self.get_window(
            symbol=payload["symbol"],
            lookback=payload["lookback"],
            end_time=payload.get("end_time")
        )
        
        await self._event_log.append(
            Envelope(
                type=DataEvents.WINDOW_READY,
                payload={
                    "run_id": self._run_id,
                    "symbol": payload["symbol"],
                    "bars": [bar.to_dict() for bar in bars],
                    "request_id": envelope.correlation_id
                },
                metadata={"run_id": self._run_id},
                correlation_id=envelope.correlation_id
            )
        )
```

**3. EventLog - Add subscription capability**

```python
# src/events/log.py

class EventLog(Protocol):
    async def subscribe(
        self,
        event_types: list[str],
        callback: Callable[[Envelope], Awaitable[None]],
        filter_fn: Callable[[Envelope], bool] | None = None
    ) -> str:
        """Subscribe to events. Returns subscription ID."""
        ...
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        ...
```

---

### 4.2 SMA Strategy Implementation

#### Strategy Design

```python
# src/marvin/strategies/sma_strategy.py

@dataclass
class SMAConfig:
    """SMA strategy configuration."""
    fast_period: int = 10
    slow_period: int = 20
    qty: Decimal = Decimal("0.1")
    
class SMAStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    
    - BUY when fast SMA crosses ABOVE slow SMA
    - SELL when fast SMA crosses BELOW slow SMA
    
    Requires lookback = slow_period + 1 bars for crossover detection.
    """
    
    def __init__(self, config: SMAConfig | None = None):
        super().__init__()
        self._config = config or SMAConfig()
        self._prev_fast: Decimal | None = None
        self._prev_slow: Decimal | None = None
    
    async def on_tick(self, tick) -> list[StrategyAction]:
        """Request data window on each tick."""
        return [
            StrategyAction(
                type="fetch_window",
                symbol=self._symbols[0],
                lookback=self._config.slow_period + 1
            )
        ]
    
    async def on_data(self, data: dict) -> list[StrategyAction]:
        """Calculate SMA crossover and generate signals."""
        bars = data.get("bars", [])
        if len(bars) < self._config.slow_period + 1:
            return []
        
        closes = [bar["close"] for bar in bars]
        
        # Calculate SMAs
        fast_sma = self._calculate_sma(closes, self._config.fast_period)
        slow_sma = self._calculate_sma(closes, self._config.slow_period)
        
        actions = []
        
        # Detect crossover
        if self._prev_fast is not None and self._prev_slow is not None:
            # Bullish crossover: fast crosses above slow
            if self._prev_fast <= self._prev_slow and fast_sma > slow_sma:
                if not self._has_position:
                    actions.append(StrategyAction(
                        type="place_order",
                        symbol=self._symbols[0],
                        side="buy",
                        qty=self._config.qty,
                        order_type="market"
                    ))
                    self._has_position = True
            
            # Bearish crossover: fast crosses below slow
            elif self._prev_fast >= self._prev_slow and fast_sma < slow_sma:
                if self._has_position:
                    actions.append(StrategyAction(
                        type="place_order",
                        symbol=self._symbols[0],
                        side="sell",
                        qty=self._config.qty,
                        order_type="market"
                    ))
                    self._has_position = False
        
        # Store for next comparison
        self._prev_fast = fast_sma
        self._prev_slow = slow_sma
        
        return actions
    
    def _calculate_sma(self, values: list, period: int) -> Decimal:
        """Calculate simple moving average of last N values."""
        recent = values[-period:]
        return sum(Decimal(str(v)) for v in recent) / period
```

#### Strategy Configuration Schema

```python
# src/marvin/strategy_config.py

@dataclass
class StrategyConfig:
    """Strategy configuration loaded from file/API."""
    strategy_id: str
    strategy_class: str  # e.g., "src.marvin.strategies.sma_strategy.SMAStrategy"
    params: dict[str, Any]  # Strategy-specific parameters
    
# Example YAML config:
# strategies:
#   - id: sma-btc
#     class: src.marvin.strategies.sma_strategy.SMAStrategy
#     params:
#       fast_period: 10
#       slow_period: 20
#       qty: "0.1"
```

---

### 4.3 Strategy Loader Enhancement

```python
# src/marvin/strategy_loader.py

from importlib import import_module
from pathlib import Path
import yaml

class ConfigurableStrategyLoader(StrategyLoader):
    """Load strategies from configuration file."""
    
    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path
        self._strategies: dict[str, StrategyConfig] = {}
        if config_path:
            self._load_config(config_path)
    
    def _load_config(self, path: Path) -> None:
        """Load strategy configurations from YAML."""
        with open(path) as f:
            config = yaml.safe_load(f)
        
        for entry in config.get("strategies", []):
            self._strategies[entry["id"]] = StrategyConfig(
                strategy_id=entry["id"],
                strategy_class=entry["class"],
                params=entry.get("params", {})
            )
    
    def register(self, strategy_id: str, config: StrategyConfig) -> None:
        """Register a strategy configuration programmatically."""
        self._strategies[strategy_id] = config
    
    def load(self, strategy_id: str) -> BaseStrategy:
        """Load and instantiate a strategy by ID."""
        if strategy_id not in self._strategies:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        config = self._strategies[strategy_id]
        
        # Dynamic import
        module_path, class_name = config.strategy_class.rsplit(".", 1)
        module = import_module(module_path)
        strategy_class = getattr(module, class_name)
        
        # Instantiate with params
        return strategy_class(**config.params)
```

---

### 4.4 Type Safety Improvements (Moved from Code Quality)

#### SimulatedFill.side → OrderSide

```python
# src/greta/models.py

from src.veda.models import OrderSide

@dataclass(frozen=True)
class SimulatedFill:
    """Record of a simulated fill during backtest."""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide  # Changed from str
    qty: Decimal
    fill_price: Decimal
    commission: Decimal
    slippage: Decimal
    timestamp: datetime
    bar_index: int
```

#### Fix ClockTick Duplicate

```python
# tests/fixtures/clock.py

# Remove local ClockTick definition
# Import from production code instead
from src.glados.clock.base import ClockTick

class ControllableClock:
    """Test clock for deterministic testing."""
    
    async def emit_tick(self, timestamp: datetime) -> ClockTick:
        tick = ClockTick(
            timestamp=timestamp,
            bar_open=timestamp,
            bar_close=timestamp + timedelta(minutes=1),
            timeframe="1m"
        )
        for callback in self._callbacks:
            await callback(tick)
        return tick
```

---

## 5. MVP Implementation Plan

> **Development Methodology**: TDD (Test-Driven Development)  
> **Pattern**: Write tests (RED) → Implement (GREEN) → Refactor (BLUE)

### MVP Overview

| MVP | Focus | Tests | Priority | Dependencies |
|-----|-------|-------|----------|--------------|
| M5-1 | EventLog Subscription | ~10 | P0 | - |
| M5-2 | data.WindowReady Flow | ~15 | P0 | M5-1 |
| M5-3 | SMA Strategy | ~12 | P0 | M5-2 |
| M5-4 | Plugin Strategy Loader | ~15 | P0 | M5-3 |
| M5-5 | Code Quality Fixes | ~8 | P1 | - |

**Estimated Total: ~60 new tests** (allowing for ~20 integration tests)

---

### M5-1: EventLog Subscription (~10 tests)

**Goal**: Add subscription capability to EventLog for event-driven communication.

**Why First**: This is the foundation for event-driven flow. Without subscription mechanism, components cannot react to events.

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/events/protocol.py` | Modify | Add Subscription dataclass |
| `src/events/log.py` | Modify | Add subscribe/unsubscribe to InMemoryEventLog |
| `src/events/log.py` | Modify | Add subscribe/unsubscribe to PostgresEventLog |
| `tests/unit/events/test_subscription.py` | Create | Subscription unit tests |
| `tests/integration/test_event_subscription.py` | Create | Postgres subscription tests |

#### TDD Test Cases (Write First)

```python
# tests/unit/events/test_subscription.py

import pytest
from src.events.log import InMemoryEventLog
from src.events.protocol import Envelope

class TestEventLogSubscription:
    """Tests for EventLog subscription functionality."""
    
    @pytest.fixture
    def event_log(self) -> InMemoryEventLog:
        return InMemoryEventLog()
    
    # --- Test 1: Basic subscription ---
    async def test_subscribe_returns_subscription_id(self, event_log):
        """subscribe() returns a unique subscription ID."""
        callback = AsyncMock()
        sub_id = await event_log.subscribe(
            event_types=["test.Event"],
            callback=callback
        )
        assert sub_id is not None
        assert isinstance(sub_id, str)
    
    # --- Test 2: Subscriber receives matching events ---
    async def test_subscriber_receives_matching_events(self, event_log):
        """Subscriber receives events matching type filter."""
        received = []
        async def callback(envelope):
            received.append(envelope)
        
        await event_log.subscribe(
            event_types=["test.Event"],
            callback=callback
        )
        
        envelope = Envelope(type="test.Event", payload={"data": "value"})
        await event_log.append(envelope)
        
        assert len(received) == 1
        assert received[0].type == "test.Event"
    
    # --- Test 3: Subscriber does NOT receive non-matching events ---
    async def test_subscriber_ignores_non_matching_events(self, event_log):
        """Subscriber does not receive events not in type filter."""
        received = []
        async def callback(envelope):
            received.append(envelope)
        
        await event_log.subscribe(
            event_types=["test.Event"],
            callback=callback
        )
        
        envelope = Envelope(type="other.Event", payload={})
        await event_log.append(envelope)
        
        assert len(received) == 0
    
    # --- Test 4: Custom filter function ---
    async def test_subscribe_with_filter_fn(self, event_log):
        """Subscriber can filter by custom function."""
        received = []
        async def callback(envelope):
            received.append(envelope)
        
        await event_log.subscribe(
            event_types=["test.Event"],
            callback=callback,
            filter_fn=lambda e: e.payload.get("run_id") == "run-001"
        )
        
        # Should receive this
        await event_log.append(Envelope(
            type="test.Event",
            payload={"run_id": "run-001"}
        ))
        # Should NOT receive this
        await event_log.append(Envelope(
            type="test.Event",
            payload={"run_id": "run-002"}
        ))
        
        assert len(received) == 1
        assert received[0].payload["run_id"] == "run-001"
    
    # --- Test 5: Unsubscribe stops delivery ---
    async def test_unsubscribe_stops_delivery(self, event_log):
        """Unsubscribed callback no longer receives events."""
        received = []
        async def callback(envelope):
            received.append(envelope)
        
        sub_id = await event_log.subscribe(
            event_types=["test.Event"],
            callback=callback
        )
        
        # Should receive
        await event_log.append(Envelope(type="test.Event", payload={}))
        assert len(received) == 1
        
        # Unsubscribe
        await event_log.unsubscribe(sub_id)
        
        # Should NOT receive
        await event_log.append(Envelope(type="test.Event", payload={}))
        assert len(received) == 1  # Still 1, not 2
    
    # --- Test 6: Multiple subscribers same event ---
    async def test_multiple_subscribers_same_event(self, event_log):
        """Multiple subscribers receive same event."""
        received_1 = []
        received_2 = []
        
        await event_log.subscribe(
            event_types=["test.Event"],
            callback=lambda e: received_1.append(e)
        )
        await event_log.subscribe(
            event_types=["test.Event"],
            callback=lambda e: received_2.append(e)
        )
        
        await event_log.append(Envelope(type="test.Event", payload={}))
        
        assert len(received_1) == 1
        assert len(received_2) == 1
    
    # --- Test 7: Subscriber error doesn't break others ---
    async def test_subscriber_error_doesnt_break_others(self, event_log):
        """Error in one subscriber doesn't affect others."""
        received = []
        
        async def bad_callback(e):
            raise ValueError("Intentional error")
        
        async def good_callback(e):
            received.append(e)
        
        await event_log.subscribe(event_types=["test.Event"], callback=bad_callback)
        await event_log.subscribe(event_types=["test.Event"], callback=good_callback)
        
        # Should not raise, good_callback should still receive
        await event_log.append(Envelope(type="test.Event", payload={}))
        
        assert len(received) == 1
    
    # --- Test 8: Wildcard subscription ---
    async def test_wildcard_subscription(self, event_log):
        """Subscriber with '*' receives all events."""
        received = []
        
        await event_log.subscribe(
            event_types=["*"],
            callback=lambda e: received.append(e)
        )
        
        await event_log.append(Envelope(type="test.Event", payload={}))
        await event_log.append(Envelope(type="other.Event", payload={}))
        
        assert len(received) == 2
    
    # --- Test 9: Subscription with multiple types ---
    async def test_subscription_multiple_types(self, event_log):
        """Subscriber can listen to multiple event types."""
        received = []
        
        await event_log.subscribe(
            event_types=["type.A", "type.B"],
            callback=lambda e: received.append(e)
        )
        
        await event_log.append(Envelope(type="type.A", payload={}))
        await event_log.append(Envelope(type="type.B", payload={}))
        await event_log.append(Envelope(type="type.C", payload={}))
        
        assert len(received) == 2
    
    # --- Test 10: Unsubscribe unknown ID is safe ---
    async def test_unsubscribe_unknown_id_is_safe(self, event_log):
        """Unsubscribing with unknown ID doesn't raise."""
        # Should not raise
        await event_log.unsubscribe("unknown-id")
```

#### Implementation (After Tests Pass)

```python
# src/events/protocol.py - Add Subscription dataclass

from dataclasses import dataclass, field
from typing import Callable, Awaitable
from uuid import uuid4

@dataclass
class Subscription:
    """Represents an event subscription."""
    id: str = field(default_factory=lambda: str(uuid4()))
    event_types: list[str] = field(default_factory=list)
    callback: Callable[[Envelope], Awaitable[None]] | None = None
    filter_fn: Callable[[Envelope], bool] | None = None


# src/events/log.py - Add to InMemoryEventLog

class InMemoryEventLog:
    def __init__(self):
        self._events: list[Envelope] = []
        self._subscriptions: dict[str, Subscription] = {}
    
    async def subscribe(
        self,
        event_types: list[str],
        callback: Callable[[Envelope], Awaitable[None]],
        filter_fn: Callable[[Envelope], bool] | None = None
    ) -> str:
        """Subscribe to events. Returns subscription ID."""
        sub = Subscription(
            event_types=event_types,
            callback=callback,
            filter_fn=filter_fn
        )
        self._subscriptions[sub.id] = sub
        return sub.id
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        self._subscriptions.pop(subscription_id, None)
    
    async def append(self, envelope: Envelope) -> int:
        """Append event and notify subscribers."""
        self._events.append(envelope)
        offset = len(self._events) - 1
        
        # Notify matching subscribers
        for sub in self._subscriptions.values():
            if self._matches(envelope, sub):
                try:
                    await sub.callback(envelope)
                except Exception as e:
                    logger.warning(f"Subscriber error: {e}")
        
        return offset
    
    def _matches(self, envelope: Envelope, sub: Subscription) -> bool:
        """Check if envelope matches subscription."""
        # Check event type
        if "*" not in sub.event_types and envelope.type not in sub.event_types:
            return False
        # Check custom filter
        if sub.filter_fn and not sub.filter_fn(envelope):
            return False
        return True
```

#### Definition of Done

- [ ] All 10 tests pass (unit)
- [ ] InMemoryEventLog subscription works
- [ ] PostgresEventLog subscription works (integration)
- [ ] No regressions in existing tests

---

### M5-2: data.WindowReady Flow (~15 tests)

**Goal**: Complete the event-driven data fetching flow.

**Why Second**: Builds on M5-1 subscription. This enables strategy-to-data-provider communication via events.

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/marvin/strategy_runner.py` | Modify | Subscribe to data.WindowReady |
| `src/greta/greta_service.py` | Modify | Subscribe to backtest.FetchWindow |
| `src/events/types.py` | Verify | Ensure event types defined |
| `tests/unit/marvin/test_strategy_runner_events.py` | Create | Event flow tests |
| `tests/unit/greta/test_greta_events.py` | Create | Greta event handler tests |
| `tests/integration/test_data_window_flow.py` | Create | E2E data flow test |

#### TDD Test Cases (Write First)

```python
# tests/unit/marvin/test_strategy_runner_events.py

class TestStrategyRunnerEvents:
    """Tests for StrategyRunner event-driven data flow."""
    
    @pytest.fixture
    def event_log(self):
        return InMemoryEventLog()
    
    @pytest.fixture
    def runner(self, event_log):
        strategy = Mock(spec=BaseStrategy)
        return StrategyRunner(strategy=strategy, event_log=event_log)
    
    # --- Test 1: on_tick emits strategy.FetchWindow ---
    async def test_on_tick_emits_fetch_window_event(self, runner, event_log):
        """When strategy returns fetch_window action, emit strategy.FetchWindow."""
        runner._strategy.on_tick = AsyncMock(return_value=[
            StrategyAction(type="fetch_window", symbol="BTC/USD", lookback=20)
        ])
        
        await runner.initialize("run-001", ["BTC/USD"])
        await runner.on_tick(ClockTick(timestamp=datetime.now(), ...))
        
        events = await event_log.read_from(0)
        assert len(events) == 1
        assert events[0].type == "strategy.FetchWindow"
        assert events[0].payload["symbol"] == "BTC/USD"
        assert events[0].payload["lookback"] == 20
    
    # --- Test 2: Runner subscribes to data.WindowReady ---
    async def test_runner_subscribes_to_window_ready(self, runner, event_log):
        """After initialize, runner is subscribed to data.WindowReady."""
        await runner.initialize("run-001", ["BTC/USD"])
        
        # Manually append a data.WindowReady event
        runner._strategy.on_data = AsyncMock(return_value=[])
        await event_log.append(Envelope(
            type="data.WindowReady",
            payload={"run_id": "run-001", "bars": []},
            metadata={"run_id": "run-001"}
        ))
        
        # Strategy.on_data should have been called
        runner._strategy.on_data.assert_called_once()
    
    # --- Test 3: Filters by run_id ---
    async def test_filters_window_ready_by_run_id(self, runner, event_log):
        """Only receives data.WindowReady for own run_id."""
        await runner.initialize("run-001", ["BTC/USD"])
        runner._strategy.on_data = AsyncMock(return_value=[])
        
        # Event for different run
        await event_log.append(Envelope(
            type="data.WindowReady",
            payload={"run_id": "run-002", "bars": []},
            metadata={"run_id": "run-002"}
        ))
        
        # Should NOT call on_data
        runner._strategy.on_data.assert_not_called()
    
    # --- Test 4: on_data emits place_request ---
    async def test_on_data_emits_place_request(self, runner, event_log):
        """When strategy.on_data returns place_order, emit strategy.PlaceRequest."""
        await runner.initialize("run-001", ["BTC/USD"])
        runner._strategy.on_data = AsyncMock(return_value=[
            StrategyAction(type="place_order", symbol="BTC/USD", side="buy", qty=Decimal("0.1"))
        ])
        
        # Simulate receiving WindowReady
        await event_log.append(Envelope(
            type="data.WindowReady",
            payload={"run_id": "run-001", "bars": [{"close": "100"}]},
            metadata={"run_id": "run-001"}
        ))
        
        events = [e for e in await event_log.read_from(0) if e.type == "strategy.PlaceRequest"]
        assert len(events) == 1
        assert events[0].payload["side"] == "buy"
    
    # --- Test 5: Cleanup unsubscribes ---
    async def test_cleanup_unsubscribes(self, runner, event_log):
        """cleanup() removes subscription."""
        await runner.initialize("run-001", ["BTC/USD"])
        await runner.cleanup()
        
        runner._strategy.on_data = AsyncMock()
        await event_log.append(Envelope(
            type="data.WindowReady",
            payload={"run_id": "run-001", "bars": []},
            metadata={"run_id": "run-001"}
        ))
        
        # Should NOT call after cleanup
        runner._strategy.on_data.assert_not_called()


# tests/unit/greta/test_greta_events.py

class TestGretaServiceEvents:
    """Tests for GretaService event handling."""
    
    @pytest.fixture
    def event_log(self):
        return InMemoryEventLog()
    
    @pytest.fixture
    def greta(self, event_log):
        bar_repo = Mock()
        return GretaService(
            run_id="run-001",
            event_log=event_log,
            bar_repository=bar_repo,
            fill_simulator=Mock()
        )
    
    # --- Test 6: Subscribes to backtest.FetchWindow ---
    async def test_subscribes_to_backtest_fetch_window(self, greta, event_log):
        """After initialize, greta subscribes to backtest.FetchWindow."""
        await greta.initialize()
        
        assert len(event_log._subscriptions) > 0
    
    # --- Test 7: Handles backtest.FetchWindow ---
    async def test_handles_fetch_window_emits_window_ready(self, greta, event_log):
        """backtest.FetchWindow → fetch bars → emit data.WindowReady."""
        greta._bar_repository.get_bars = AsyncMock(return_value=[
            Bar(symbol="BTC/USD", timestamp=datetime.now(), close=Decimal("100"), ...)
        ])
        
        await greta.initialize()
        
        # Emit backtest.FetchWindow
        await event_log.append(Envelope(
            type="backtest.FetchWindow",
            payload={"run_id": "run-001", "symbol": "BTC/USD", "lookback": 10},
            metadata={"run_id": "run-001"},
            correlation_id="req-001"
        ))
        
        # Should emit data.WindowReady
        events = [e for e in await event_log.read_from(0) if e.type == "data.WindowReady"]
        assert len(events) == 1
        assert events[0].payload["symbol"] == "BTC/USD"
        assert events[0].correlation_id == "req-001"
    
    # --- Test 8: Handles backtest.PlaceOrder ---
    async def test_handles_place_order_emits_filled(self, greta, event_log):
        """backtest.PlaceOrder → simulate fill → emit orders.Filled."""
        greta._fill_simulator.simulate = Mock(return_value=SimulatedFill(...))
        
        await greta.initialize()
        
        await event_log.append(Envelope(
            type="backtest.PlaceOrder",
            payload={"run_id": "run-001", "symbol": "BTC/USD", "side": "buy", "qty": "0.1"},
            metadata={"run_id": "run-001"}
        ))
        
        events = [e for e in await event_log.read_from(0) if e.type == "orders.Filled"]
        assert len(events) == 1
    
    # --- Test 9: Filters by run_id ---
    async def test_filters_by_run_id(self, greta, event_log):
        """Only handles events for own run_id."""
        greta._bar_repository.get_bars = AsyncMock()
        await greta.initialize()
        
        # Event for different run
        await event_log.append(Envelope(
            type="backtest.FetchWindow",
            payload={"run_id": "run-002", "symbol": "BTC/USD"},
            metadata={"run_id": "run-002"}
        ))
        
        # Should NOT call bar_repository
        greta._bar_repository.get_bars.assert_not_called()
    
    # --- Test 10: Uses bar cache ---
    async def test_fetch_window_uses_bar_cache(self, greta, event_log):
        """backtest.FetchWindow uses preloaded bar cache when available."""
        # Preload bars
        greta._bar_cache = {
            "BTC/USD": [Bar(...), Bar(...)]
        }
        
        await greta.initialize()
        
        await event_log.append(Envelope(
            type="backtest.FetchWindow",
            payload={"run_id": "run-001", "symbol": "BTC/USD", "lookback": 2},
            metadata={"run_id": "run-001"}
        ))
        
        # Should NOT call repository (used cache)
        greta._bar_repository.get_bars.assert_not_called()


# tests/integration/test_data_window_flow.py

class TestDataWindowFlowIntegration:
    """End-to-end tests for data window flow."""
    
    # --- Test 11-15: Integration scenarios ---
    async def test_full_fetch_window_to_on_data_flow(self):
        """Complete flow: tick → FetchWindow → WindowReady → on_data."""
        ...
    
    async def test_multiple_symbols_parallel_fetch(self):
        """Multiple symbols can fetch data in parallel."""
        ...
```

#### Implementation Sketch

```python
# src/marvin/strategy_runner.py - Add event subscription

class StrategyRunner:
    def __init__(self, strategy: BaseStrategy, event_log: EventLog):
        self._strategy = strategy
        self._event_log = event_log
        self._run_id: str | None = None
        self._subscription_id: str | None = None
    
    async def initialize(self, run_id: str, symbols: list[str]) -> None:
        self._run_id = run_id
        await self._strategy.initialize(symbols)
        
        # Subscribe to data.WindowReady
        self._subscription_id = await self._event_log.subscribe(
            event_types=["data.WindowReady"],
            callback=self._on_window_ready,
            filter_fn=lambda e: e.metadata.get("run_id") == self._run_id
        )
    
    async def cleanup(self) -> None:
        if self._subscription_id:
            await self._event_log.unsubscribe(self._subscription_id)
            self._subscription_id = None
    
    async def _on_window_ready(self, envelope: Envelope) -> None:
        """Handle data.WindowReady event."""
        actions = await self._strategy.on_data(envelope.payload)
        for action in actions:
            await self._emit_action(action)
```

#### Definition of Done

- [ ] All 15 tests pass
- [ ] StrategyRunner subscribes to data.WindowReady
- [ ] GretaService subscribes to backtest.FetchWindow
- [ ] Complete flow works: tick → FetchWindow → WindowReady → on_data
- [ ] Integration test passes

---

### M5-3: SMA Strategy (~12 tests)

**Goal**: Implement SMA crossover strategy with configurable parameters.

**Why Third**: Now that data flow works, we can implement a real strategy that uses it.

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/marvin/strategies/__init__.py` | Create | Empty package |
| `src/marvin/strategies/sma_strategy.py` | Create | SMA strategy implementation |
| `tests/unit/marvin/test_sma_strategy.py` | Create | SMA unit tests |
| `tests/integration/test_sma_backtest.py` | Create | SMA backtest integration |

#### TDD Test Cases (Write First)

```python
# tests/unit/marvin/test_sma_strategy.py

from decimal import Decimal
from src.marvin.strategies.sma_strategy import SMAStrategy, SMAConfig

class TestSMAStrategy:
    """Tests for SMA crossover strategy."""
    
    @pytest.fixture
    def strategy(self):
        return SMAStrategy(SMAConfig(fast_period=5, slow_period=10, qty=Decimal("1.0")))
    
    # --- Test 1: on_tick requests data ---
    async def test_on_tick_returns_fetch_window_action(self, strategy):
        """on_tick returns fetch_window action with correct lookback."""
        await strategy.initialize(["BTC/USD"])
        actions = await strategy.on_tick(ClockTick(...))
        
        assert len(actions) == 1
        assert actions[0].type == "fetch_window"
        assert actions[0].lookback == 11  # slow_period + 1
    
    # --- Test 2: SMA calculation ---
    async def test_calculate_sma_correctly(self, strategy):
        """SMA calculation is mathematically correct."""
        values = [10, 20, 30, 40, 50]  # avg = 30
        sma = strategy._calculate_sma(values, period=5)
        assert sma == Decimal("30")
    
    # --- Test 3: Bullish crossover buy ---
    async def test_bullish_crossover_generates_buy(self, strategy):
        """Fast crossing above slow generates buy signal."""
        await strategy.initialize(["BTC/USD"])
        
        # First call: establish baseline (no crossover yet)
        # fast < slow initially
        bars_initial = self._make_bars(closes=[
            10, 11, 12, 13, 14,  # fast avg = 12
            9, 10, 10, 10, 10, 10  # slow avg = 9.83
        ])
        await strategy.on_data({"bars": bars_initial})
        
        # Second call: fast crosses above slow
        bars_cross = self._make_bars(closes=[
            10, 11, 12, 20, 25,  # fast avg = 15.6
            9, 10, 10, 10, 10, 12  # slow avg = 10
        ])
        actions = await strategy.on_data({"bars": bars_cross})
        
        assert len(actions) == 1
        assert actions[0].type == "place_order"
        assert actions[0].side == "buy"
    
    # --- Test 4: Bearish crossover sell ---
    async def test_bearish_crossover_generates_sell(self, strategy):
        """Fast crossing below slow generates sell signal."""
        await strategy.initialize(["BTC/USD"])
        strategy._has_position = True
        
        # Establish baseline: fast > slow
        bars_initial = self._make_bars(closes=[
            20, 21, 22, 23, 24,  # fast high
            10, 10, 10, 10, 10, 10  # slow low
        ])
        await strategy.on_data({"bars": bars_initial})
        
        # Cross: fast drops below slow
        bars_cross = self._make_bars(closes=[
            5, 6, 7, 8, 9,  # fast drops
            10, 10, 10, 10, 10, 10
        ])
        actions = await strategy.on_data({"bars": bars_cross})
        
        assert len(actions) == 1
        assert actions[0].type == "place_order"
        assert actions[0].side == "sell"
    
    # --- Test 5: No signal without crossover ---
    async def test_no_signal_without_crossover(self, strategy):
        """No signal when SMAs don't cross."""
        await strategy.initialize(["BTC/USD"])
        
        # Both calls: fast > slow (no cross)
        bars = self._make_bars(closes=[20, 20, 20, 20, 20, 10, 10, 10, 10, 10, 10])
        await strategy.on_data({"bars": bars})
        actions = await strategy.on_data({"bars": bars})
        
        assert len(actions) == 0
    
    # --- Test 6: Insufficient data no signal ---
    async def test_insufficient_data_no_signal(self, strategy):
        """No signal when bars < slow_period."""
        await strategy.initialize(["BTC/USD"])
        
        bars = self._make_bars(closes=[10, 20, 30])  # Only 3 bars
        actions = await strategy.on_data({"bars": bars})
        
        assert len(actions) == 0
    
    # --- Test 7: Custom parameters ---
    async def test_custom_parameters_respected(self):
        """Strategy respects custom period/qty config."""
        config = SMAConfig(fast_period=3, slow_period=7, qty=Decimal("2.5"))
        strategy = SMAStrategy(config)
        await strategy.initialize(["ETH/USD"])
        
        actions = await strategy.on_tick(ClockTick(...))
        assert actions[0].lookback == 8  # slow + 1
    
    # --- Test 8: Position tracking ---
    async def test_only_buys_when_no_position(self, strategy):
        """Buy signal ignored if already has position."""
        await strategy.initialize(["BTC/USD"])
        strategy._has_position = True  # Already in
        
        # Create bullish crossover
        # ... but should NOT generate buy
        actions = await self._trigger_bullish_cross(strategy)
        
        assert len(actions) == 0
    
    # --- Test 9: Multiple symbols ---
    async def test_multiple_symbols_tracking(self):
        """Tracks position per symbol."""
        strategy = SMAStrategy()
        await strategy.initialize(["BTC/USD", "ETH/USD"])
        
        # Buy BTC
        # ... 
        # Should still be able to buy ETH
    
    # --- Test 10-12: Edge cases ---
    async def test_first_tick_no_signal(self, strategy):
        """First tick never generates signal (need previous for crossover)."""
        ...
    
    async def test_handles_decimal_prices(self, strategy):
        """Works correctly with Decimal prices."""
        ...
    
    async def test_empty_bars_no_error(self, strategy):
        """Empty bars list doesn't raise error."""
        await strategy.initialize(["BTC/USD"])
        actions = await strategy.on_data({"bars": []})
        assert actions == []


# tests/integration/test_sma_backtest.py

class TestSMABacktestIntegration:
    """Integration tests for SMA strategy backtest."""
    
    async def test_sma_backtest_produces_trades(self, db_session):
        """SMA strategy produces actual trades in backtest."""
        # Load bars with known crossovers
        # Run backtest
        # Verify trades were made
        ...
```

#### Definition of Done

- [ ] All 12 tests pass
- [ ] SMA strategy produces correct buy/sell signals
- [ ] Backtest produces actual trades
- [ ] Strategy is configurable (periods, qty)

---

### M5-4: Plugin Strategy Loader (~15 tests)

**Goal**: Implement plugin architecture for strategies with auto-discovery and dependency resolution.

**Why Fourth**: Now that we have working strategies (SMA), we can implement the plugin loader to manage them.

#### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/marvin/strategy_meta.py` | Create | StrategyMeta dataclass, @strategy decorator |
| `src/marvin/strategy_loader.py` | Rewrite | PluginStrategyLoader |
| `src/marvin/exceptions.py` | Create | StrategyNotFoundError, etc. |
| `src/marvin/__init__.py` | Modify | Remove hardcoded imports |
| `src/marvin/strategies/sample_strategy.py` | Move | Add STRATEGY_META |
| `src/marvin/strategies/sma_strategy.py` | Modify | Add STRATEGY_META |
| `tests/unit/marvin/test_plugin_loader.py` | Create | Plugin tests |

#### TDD Test Cases (Write First)

```python
# tests/unit/marvin/test_plugin_loader.py

from pathlib import Path
from src.marvin.strategy_loader import PluginStrategyLoader
from src.marvin.exceptions import StrategyNotFoundError, DependencyError

class TestPluginStrategyLoader:
    """Tests for plugin-based strategy loading."""
    
    @pytest.fixture
    def temp_plugin_dir(self, tmp_path):
        """Create temp directory with test strategy files."""
        plugin_dir = tmp_path / "strategies"
        plugin_dir.mkdir()
        
        # Create test strategy file
        (plugin_dir / "test_strategy.py").write_text('''
STRATEGY_META = {
    "id": "test-strategy",
    "name": "Test Strategy",
    "version": "1.0.0",
    "dependencies": [],
    "class": "TestStrategy",
}

from src.marvin.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        return plugin_dir
    
    @pytest.fixture
    def loader(self, temp_plugin_dir):
        return PluginStrategyLoader(plugin_dir=temp_plugin_dir)
    
    # --- Test 1: Discovers strategies ---
    def test_discovers_strategies_in_directory(self, loader):
        """Scans strategies/ directory and finds all plugins."""
        available = loader.list_available()
        assert len(available) >= 1
        assert any(s.id == "test-strategy" for s in available)
    
    # --- Test 2: Load by ID ---
    def test_load_strategy_by_id(self, loader):
        """Loads strategy by its declared ID."""
        strategy = loader.load("test-strategy")
        assert strategy is not None
        assert hasattr(strategy, "on_tick")
    
    # --- Test 3: Unknown strategy ---
    def test_unknown_strategy_raises_not_found(self, loader):
        """StrategyNotFoundError for unknown strategy_id."""
        with pytest.raises(StrategyNotFoundError) as exc:
            loader.load("nonexistent")
        assert "nonexistent" in str(exc.value)
    
    # --- Test 4: Extracts metadata without importing ---
    def test_extracts_metadata_without_importing(self, temp_plugin_dir):
        """Reads STRATEGY_META without full module import."""
        # Create file with import error
        (temp_plugin_dir / "broken.py").write_text('''
STRATEGY_META = {
    "id": "broken-strategy",
    "name": "Broken",
    "class": "BrokenStrategy",
}

import nonexistent_module  # This would fail on import
''')
        
        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        available = loader.list_available()
        
        # Should still discover metadata
        assert any(s.id == "broken-strategy" for s in available)
    
    # --- Test 5: Dependency resolution ---
    def test_resolves_dependencies(self, temp_plugin_dir):
        """Loads dependent strategies before requested strategy."""
        # Create base strategy
        (temp_plugin_dir / "base_sma.py").write_text('''
STRATEGY_META = {"id": "base-sma", "name": "Base SMA", "class": "BaseSMA", "dependencies": []}
from src.marvin.base_strategy import BaseStrategy
class BaseSMA(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        
        # Create dependent strategy
        (temp_plugin_dir / "ensemble.py").write_text('''
STRATEGY_META = {
    "id": "ensemble", 
    "name": "Ensemble", 
    "class": "Ensemble",
    "dependencies": ["base-sma"]
}
from src.marvin.base_strategy import BaseStrategy
class Ensemble(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        
        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        strategy = loader.load("ensemble")
        
        # base-sma should be loaded first
        assert "base-sma" in loader._loaded
    
    # --- Test 6: Missing dependency ---
    def test_missing_dependency_raises_error(self, temp_plugin_dir):
        """DependencyError if required strategy not found."""
        (temp_plugin_dir / "needs_missing.py").write_text('''
STRATEGY_META = {
    "id": "needs-missing",
    "name": "Needs Missing",
    "class": "NeedsMissing",
    "dependencies": ["does-not-exist"]
}
from src.marvin.base_strategy import BaseStrategy
class NeedsMissing(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        
        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        
        with pytest.raises(DependencyError) as exc:
            loader.load("needs-missing")
        assert "does-not-exist" in str(exc.value)
    
    # --- Test 7: Circular dependency ---
    def test_circular_dependency_detected(self, temp_plugin_dir):
        """CircularDependencyError for A→B→A cycles."""
        (temp_plugin_dir / "cycle_a.py").write_text('''
STRATEGY_META = {"id": "cycle-a", "name": "A", "class": "A", "dependencies": ["cycle-b"]}
from src.marvin.base_strategy import BaseStrategy
class A(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        (temp_plugin_dir / "cycle_b.py").write_text('''
STRATEGY_META = {"id": "cycle-b", "name": "B", "class": "B", "dependencies": ["cycle-a"]}
from src.marvin.base_strategy import BaseStrategy
class B(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        
        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        
        with pytest.raises(CircularDependencyError):
            loader.load("cycle-a")
    
    # --- Test 8: Deleted strategy not discovered ---
    def test_deleted_strategy_not_discovered(self, temp_plugin_dir):
        """Deleted .py file is not in available list."""
        # Create then delete
        file = temp_plugin_dir / "to_delete.py"
        file.write_text('''STRATEGY_META = {"id": "to-delete", "class": "X"}''')
        
        loader1 = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        assert any(s.id == "to-delete" for s in loader1.list_available())
        
        file.unlink()
        
        loader2 = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        assert not any(s.id == "to-delete" for s in loader2.list_available())
    
    # --- Test 9: System works after deletion ---
    def test_system_works_after_strategy_deleted(self, temp_plugin_dir):
        """Other strategies still load after one is deleted."""
        (temp_plugin_dir / "keeper.py").write_text('''
STRATEGY_META = {"id": "keeper", "class": "Keeper"}
from src.marvin.base_strategy import BaseStrategy
class Keeper(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        (temp_plugin_dir / "to_delete.py").write_text('''
STRATEGY_META = {"id": "to-delete", "class": "X"}
''')
        
        (temp_plugin_dir / "to_delete.py").unlink()
        
        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        strategy = loader.load("keeper")  # Should work
        assert strategy is not None
    
    # --- Test 10: Lazy loading ---
    def test_lazy_loading(self, temp_plugin_dir):
        """Strategy not imported until load() called."""
        # Strategy file has print to detect import
        (temp_plugin_dir / "lazy_test.py").write_text('''
STRATEGY_META = {"id": "lazy", "class": "Lazy"}
print("LAZY STRATEGY IMPORTED")  # Should only print on load()
from src.marvin.base_strategy import BaseStrategy
class Lazy(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        
        import io
        import sys
        captured = io.StringIO()
        sys.stdout = captured
        
        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        _ = loader.list_available()
        
        sys.stdout = sys.__stdout__
        assert "LAZY STRATEGY IMPORTED" not in captured.getvalue()
    
    # --- Test 11-15: Additional tests ---
    def test_ignores_files_starting_with_underscore(self, temp_plugin_dir):
        """Files like __init__.py are ignored."""
        ...
    
    def test_handles_syntax_error_gracefully(self, temp_plugin_dir):
        """Syntax error in plugin file doesn't crash loader."""
        ...
    
    def test_strategy_meta_without_dependencies_field(self, temp_plugin_dir):
        """STRATEGY_META without dependencies field defaults to []."""
        ...
```

#### Definition of Done

- [ ] All 15 tests pass
- [ ] Strategies discovered without full import (AST parsing)
- [ ] Dependencies resolved in correct order
- [ ] Circular dependencies detected
- [ ] System works after deleting strategy files

---

### M5-5: Code Quality Fixes (~8 tests)

**Goal**: Fix M4 deferred items - type safety and test fixtures.

**Why Last**: These are P1 improvements that don't block functionality.

#### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `src/greta/models.py` | Modify | SimulatedFill.side: str → OrderSide |
| `src/greta/fill_simulator.py` | Modify | Update to use OrderSide |
| `src/greta/greta_service.py` | Modify | Update comparisons |
| `tests/fixtures/clock.py` | Modify | Remove ClockTick duplicate |
| `tests/fixtures/strategy.py` | Create | Extract SimpleTestStrategy |
| `src/glados/services/run_manager.py` | Modify | Add Clock union type |

#### Test Cases

```python
# tests/unit/greta/test_type_safety.py

class TestSimulatedFillTypeSafety:
    """Tests for SimulatedFill type improvements."""
    
    def test_side_is_order_side_enum(self):
        """SimulatedFill.side is OrderSide, not str."""
        fill = SimulatedFill(
            order_id="123",
            side=OrderSide.BUY,  # Should be enum
            ...
        )
        assert isinstance(fill.side, OrderSide)
    
    def test_fill_simulator_returns_order_side(self):
        """FillSimulator returns fills with OrderSide."""
        ...


# tests/unit/test_clock_fixture.py

class TestClockFixture:
    """Tests for clock test fixtures."""
    
    def test_controllable_clock_uses_production_clock_tick(self):
        """ControllableClock uses ClockTick from production code."""
        from tests.fixtures.clock import ControllableClock
        from src.glados.clock.base import ClockTick
        
        clock = ControllableClock()
        tick = clock.make_tick(datetime.now())
        
        assert isinstance(tick, ClockTick)


# tests/unit/test_strategy_fixtures.py

class TestStrategyFixtures:
    """Tests for strategy test fixtures."""
    
    def test_simple_test_strategy_available(self):
        """SimpleTestStrategy is importable from fixtures."""
        from tests.fixtures.strategy import SimpleTestStrategy
        
        strategy = SimpleTestStrategy()
        assert hasattr(strategy, "on_tick")
        assert hasattr(strategy, "on_data")
```

#### Definition of Done

- [ ] All 8 tests pass
- [ ] SimulatedFill.side is OrderSide enum
- [ ] ClockTick imported from production code
- [ ] SimpleTestStrategy in tests/fixtures/strategy.py
- [ ] Clock type hint is Union[BacktestClock, RealtimeClock]

---

## 6. Test Strategy

### Test Pyramid

```
                    ┌─────────────────┐
                    │  E2E Tests (2)  │  ← Full backtest flow tests
                    │  test_e2e/      │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │  Integration Tests (~15)    │  ← Multi-component tests
              │  test_integration/          │
              └──────────────┬──────────────┘
                             │
    ┌────────────────────────┴────────────────────────┐
    │            Unit Tests (~45)                      │  ← Single component
    │            tests/unit/marvin/, events/, greta/  │
    └─────────────────────────────────────────────────┘
```

### Test Coverage Targets (M5)

| Module | Current | Target | MVP |
|--------|---------|--------|-----|
| Events | 33 | 45+ | M5-1 |
| Marvin | 32 | 55+ | M5-2, M5-3, M5-4 |
| Greta | 49 | 55+ | M5-2 |

### Test Fixtures to Create

```python
# tests/fixtures/strategy.py

class MockStrategy(BaseStrategy):
    """Configurable mock strategy for testing."""
    
    def __init__(self, actions: list[StrategyAction] | None = None):
        super().__init__()
        self._actions = actions or []
        self._tick_count = 0
    
    async def on_tick(self, tick) -> list[StrategyAction]:
        self._tick_count += 1
        return self._actions
    
    async def on_data(self, data: dict) -> list[StrategyAction]:
        return []

class SimpleTestStrategy(BaseStrategy):
    """Simple strategy that buys once."""
    # Move from test_backtest_flow.py

class MockStrategyLoader(StrategyLoader):
    """Mock loader for testing."""
    # Move from test_backtest_flow.py

def make_strategy_action(
    type: str = "fetch_window",
    symbol: str = "BTC/USD",
    **kwargs
) -> StrategyAction:
    """Factory for StrategyAction."""
```

---

## 7. Entry & Exit Gates

### Entry Gate (Before Starting M5)

- [x] M4 complete (631 tests passing)
- [x] GretaService handles backtest execution
- [x] Marvin skeleton with StrategyRunner + BaseStrategy
- [x] DomainRouter routes strategy.* → backtest.*
- [x] BacktestClock integrated with RunManager
- [x] Integration test passes (test_backtest_flow.py)

### Exit Gate (M5 Complete)

| Requirement | Verification |
|-------------|--------------|
| EventLog subscription implemented | Subscription tests pass |
| data.WindowReady flow implemented | Event chain test passes |
| SMA strategy executes backtest | Integration test with trades |
| Plugin Strategy Loader works | Auto-discovery tests pass |
| SimulatedFill uses OrderSide | Type check passes |
| Test fixtures extracted | Files exist in tests/fixtures/ |
| ClockTick duplicate fixed | Single import source |
| ~60 new tests | Test count ≥ 690 |

---

## 8. Risk & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Event subscription complexity | Medium | Medium | Simple callback model first |
| SMA calculation edge cases | Low | Medium | Comprehensive test cases |
| Plugin discovery complexity | Medium | Low | AST parsing for metadata |
| Test count estimation | Low | Medium | Allow ±10 variance |

---

## 9. Appendix

### A. File Change Summary

| Category | Files | Action |
|----------|-------|--------|
| Events | log.py, protocol.py | Modify |
| Marvin | strategy_runner.py, strategy_loader.py | Modify |
| Marvin | strategies/sma_strategy.py | Create |
| Marvin | strategy_meta.py, exceptions.py | Create |
| Greta | greta_service.py, models.py, fill_simulator.py | Modify |
| GLaDOS | routes/orders.py, dependencies.py, run_manager.py | Modify |
| Tests | ~10 new test files | Create |
| Fixtures | fixtures/strategy.py | Create |

### B. Dependency Additions

```toml
# pyproject.toml additions (if not present)
# No new dependencies required for M5
# alpaca-py will be added in M6 (Live Trading)
```

### C. Related Documents

| Document | Link |
|----------|------|
| M4 Design | [m4-greta.md](m4-greta.md) |
| M6 Design (Live Trading) | [m6-live-trading.md](m6-live-trading.md) |
| Events Spec | [events.md](../../architecture/events.md) |
| Roadmap | [roadmap.md](../../architecture/roadmap.md) |
| Audit Findings | [AUDIT_FINDINGS.md](../../AUDIT_FINDINGS.md) |
| Milestone Plan | [MILESTONE_PLAN.md](../../MILESTONE_PLAN.md) |

---

*Last Updated: 2025-02-03 (M5 design updated - Live Trading moved to M6)*

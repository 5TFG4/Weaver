# Weaver System Functional Specification

> **Document Type**: System Specification
> **Purpose**: Comprehensively describe the design intent, architecture, module responsibilities, deployment model, and core terminology of the Weaver system.
> **Related Documents**:
>
> - [Backend Functional Specification](SPEC_BACKEND.md) — API, Services, Data Models
> - [Frontend Functional Specification](SPEC_FRONTEND.md) — Pages, Components, Interactions
> - [Data Flows & Events Specification](SPEC_FLOWS.md) — End-to-End Flows, Event System

---

## 1. System Positioning

Weaver is an **automated quantitative trading system** that supports strategy development, historical backtesting, paper trading, and live trading.

Core philosophy: **One set of strategy code, three execution modes**. Strategy developers write the strategy logic once and can run it across backtest, paper, and live modes without modifying any code. The system automatically routes the strategy's trading intent to the corresponding execution engine via the event routing mechanism.

---

## 2. Three Execution Modes

| Mode         | English  | Clock                        | Execution Engine            | Data Source                                                  | Real Money Involved           |
| ------------ | -------- | ---------------------------- | --------------------------- | ------------------------------------------------------------ | ----------------------------- |
| **Backtest** | Backtest | BacktestClock (fast-forward) | Greta (simulated execution) | Database cache + on-demand pull from exchange historical API | No                            |
| **Paper**    | Paper    | RealtimeClock (real-time)    | Veda → Exchange paper API   | Exchange real-time/historical market data API                | No (exchange sandbox account) |
| **Live**     | Live     | RealtimeClock (real-time)    | Veda → Exchange live API    | Exchange real-time/historical market data API                | **Yes**                       |

### 2.1 Backtest Mode in Detail

- BacktestClock iterates through every bar within the strategy's configured time range at maximum speed
- Each bar triggers one strategy decision cycle
- Data retrieval: prioritizes reading from the database `bars` table cache; on cache miss, pulls on-demand via the exchange historical data API and writes to cache
- Greta engine simulates order execution (including slippage and commission models)
- After completion, produces BacktestResult: equity curve, Sharpe ratio, max drawdown, win rate, and other statistical metrics
- Initial capital: $100,000 (default, overridable via strategy config)
- Does not involve any exchange trading API calls (may only call historical data API)
- **Execution boundaries are controlled by the clock**: BacktestClock naturally terminates after completing the time range; the strategy itself is not responsible for controlling when to stop

### 2.2 Paper Mode in Detail

- Uses RealtimeClock to trigger the strategy at real-time pace
- The strategy requests data from the system via `FETCH_WINDOW`; the system retrieves it from the exchange's historical/real-time market data API
- Trading instructions are sent via Veda to the exchange's paper trading API
- No real money involved, but uses real market data and exchange simulated matching
- **Runs continuously**: once started, the strategy runs indefinitely until the user manually stops it or an exception occurs

### 2.3 Live Mode in Detail

- Identical code path and data flow as paper mode
- Only difference: uses the exchange's live API credentials
- Involves real funds; orders are submitted to the real exchange
- **Runs continuously**: same as paper mode, runs until stopped

### 2.4 Strategy Execution Lifecycle Principles

- **Live/Paper modes**: after startup, the strategy **runs indefinitely** with no preset termination condition. The clock continues to tick at the bar interval, and the strategy continuously receives data and makes decisions. Only two ways to stop: user manually stops it, or a runtime exception causes the system to stop.
- **Backtest mode**: the clock naturally terminates after traversing the specified time range. This is a **clock-controlled stop**, not a strategy-controlled one.
- **Strategy self-termination**: a strategy can declare "I'm done" (by returning a special `STOP_RUN` action), but this is an exceptional case, not the normal design pattern.

---

## 3. System Architecture

### 3.1 Architecture Style: Modulith (Modular Monolith)

Weaver adopts a **modular monolith architecture**: all modules run within the same Python process but achieve loose coupling through clear module boundaries and event-driven communication.

```
┌──────────────────────────────────────────────────────────────────┐
│                       Weaver Process (Python)                     │
│                                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  GLaDOS   │  │  Marvin   │  │   Greta  │  │   Veda   │          │
│  │ Control   │  │ Strategy  │  │ Backtest │  │ Trading  │          │
│  │  Plane    │  │  Engine   │  │  Engine  │  │  Engine  │          │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘          │
│        │            │             │             │                 │
│        └────────────┴─────────────┴─────────────┘                 │
│                        │  Event Bus  │                              │
│                    ┌───┴───────────┴───┐                           │
│                    │   Events (Event System) │                     │
│                    └───────┬───────────┘                           │
│                            │                                       │
│               ┌────────────┴────────────┐                          │
│               │     WallE (Persistence Layer)  │                   │
│               └─────────────────────────┘                          │
│                                                                    │
│  ┌──────────────────────────────────────────────┐                  │
│  │         Exchange Adapters Layer                 │                │
│  │  ┌────────┐  ┌────────┐  ┌────────┐          │                  │
│  │  │ Alpaca │  │Binance │  │  ...   │          │                  │
│  │  └────────┘  └────────┘  └────────┘          │                  │
│  └──────────────────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   Haro (React Frontend, Separate Container)       │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Module Responsibilities Overview

| Module                | Code Location        | Responsibilities                                                                                 | Instance Model            |
| --------------------- | -------------------- | ------------------------------------------------------------------------------------------------ | ------------------------- |
| **GLaDOS**            | `src/glados/`        | Control plane: REST API, run management, clock scheduling, dependency injection, SSE broadcast   | Singleton                 |
| **Marvin**            | `src/marvin/`        | Strategy engine: strategy discovery & loading, strategy execution, action→event translation      | **Per-Run Instance**      |
| **Greta**             | `src/greta/`         | Backtest engine: historical data replay, simulated fills, position tracking, equity calculation  | **Per-Run Instance**      |
| **Veda**              | `src/veda/`          | Trading engine: exchange adapter management, order routing, position tracking, order persistence | Singleton                 |
| **Events**            | `src/events/`        | Event system: event envelopes, event log, subscription dispatch, consumer offsets                | Singleton                 |
| **WallE**             | `src/walle/`         | Persistence layer: database models, repository interfaces, Alembic migrations                    | Singleton                 |
| **Haro**              | `haro/`              | React frontend: dashboard, run management, order viewing, SSE real-time updates                  | Separate Container        |
| **Exchange Adapters** | `src/veda/adapters/` | Concrete implementations for each exchange, loaded via plugin mechanism                          | One Instance per Exchange |

### 3.3 Per-Run vs Singleton

This is one of the most critical concepts for understanding Weaver:

**Per-Run Instance**: Each time a trading run (Run) is created, the system allocates independent component instances for it. State is completely isolated between multiple runs.

- `StrategyRunner`: Each Run has its own strategy executor
- `GretaService`: Each backtest Run has its own simulation engine (independent positions, capital, equity curve)
- `BaseClock`: Each Run has its own clock (BacktestClock for backtests, RealtimeClock for live trading)

**Singleton**: The following components are globally unique, shared by all Runs:

- `EventLog`: Event bus (events from different Runs are distinguished by `run_id` tags)
- `BarRepository`: Historical bar cache (immutable data, shared by all runs)
- `DomainRouter`: Event router
- `SSEBroadcaster`: SSE broadcaster
- `VedaService`: Trading service (manages all exchange adapters, shared by all live/paper Runs)

### 3.4 Multi-Exchange Architecture

The system is not bound to any specific exchange. Exchanges are integrated through **plugin adapters**, with each adapter implementing the unified `ExchangeAdapter` protocol.

**Design Principles**:

- The system can load multiple exchange adapters simultaneously (e.g., Alpaca + Binance)
- Each exchange can hold multiple sets of credentials (e.g., Alpaca live + paper)
- Strategies declare which exchanges they use and for what purpose via config

**How Strategies Use Exchanges**:

| Scenario                  | Description                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| Single exchange, standard | Strategy fetches data from Alpaca, places orders on Alpaca                                  |
| Cross-exchange data+trade | Strategy fetches BTC quotes from Binance for decisions, places orders on Alpaca for BTC ETF |
| Multi-exchange trading    | Strategy places orders simultaneously on Alpaca and Binance for arbitrage                   |
| Data source only          | An exchange is used solely for market data, no trading                                      |

**Adapter Discovery**: Uses the same plugin mechanism as strategies (`PluginAdapterLoader`), AST-scanning the adapter directory and registering via `ADAPTER_META` metadata.

---

## 4. Core Concept Glossary

### 4.1 Run

The complete lifecycle of a single strategy execution. Each Run has a unique UUID identifier (`id`, auto-generated by the system; users don't need to worry about it).

**Run State Machine**:

```
PENDING ──start──→ RUNNING ──stop──→ STOPPED
                       │
                       ├──(clock ends / strategy declares completion)──→ COMPLETED
                       │
                       └──(exception)──→ ERROR
```

- `PENDING`: Created, awaiting start
- `RUNNING`: Executing (clock is ticking, strategy is making decisions)
- `STOPPED`: Manually stopped by user
- `COMPLETED`: Naturally finished (backtest clock exhausted the time range; or strategy proactively declared completion)
- `ERROR`: Exception occurred during execution

**Run Attributes**:

| Field         | Type      | Description                                                                                                                 |
| ------------- | --------- | --------------------------------------------------------------------------------------------------------------------------- |
| `id`          | UUID      | System auto-generated unique identifier, different for each execution                                                       |
| `strategy_id` | string    | Strategy identifier, corresponds to `STRATEGY_META.id` (e.g., `sma-crossover`). User selects from available strategies list |
| `mode`        | enum      | `backtest` / `paper` / `live`                                                                                               |
| `status`      | enum      | See state machine above                                                                                                     |
| `config`      | dict      | **All strategy configuration parameters** (see §4.2 for details)                                                            |
| `created_at`  | datetime  | Creation time                                                                                                               |
| `started_at`  | datetime? | Start time                                                                                                                  |
| `stopped_at`  | datetime? | Stop time                                                                                                                   |

**Key Design Decision**: `symbols` (trading instruments) and `timeframe` (bar period) **are NOT top-level Run attributes**. They belong to the strategy's `config`, because:

- Different strategies require completely different instruments (some track 3 crypto pairs, others track all S&P 500 constituents)
- Instruments may be dynamic (tracking index constituent changes)
- Different strategies may need multiple timeframes (watching both 1h and 1d simultaneously)
- These are essentially the strategy's internal business logic, not universal run-level attributes

### 4.2 Strategy

A strategy is user-defined trading logic. Each strategy is a Python class inheriting from `BaseStrategy`.

**Strategy Interface**:

```python
class BaseStrategy(ABC):
    async def initialize(self, config: dict) -> None
        """Initialization. Called once when the Run starts.
        The strategy reads all parameters it needs from config: instrument list, timeframe,
        indicator parameters, exchange selection, etc."""

    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]
        """Triggered on each bar, returns a list of strategy actions.
        The strategy requests the data it needs here (any instrument, any timeframe)."""

    async def on_data(self, data: Any) -> list[StrategyAction]
        """Triggered when requested data is received, returns a list of strategy actions.
        The strategy analyzes data and makes trading decisions here."""
```

**Strategy Actions** (StrategyAction):

| Action         | Meaning                                                                    | Subsequent Processing                           |
| -------------- | -------------------------------------------------------------------------- | ----------------------------------------------- |
| `FETCH_WINDOW` | Request data (instrument, timeframe, lookback length, optional exchange)   | System fetches data then calls back `on_data()` |
| `PLACE_ORDER`  | Request order (instrument, side, quantity, type, price, optional exchange) | System routes order to specified exchange       |
| `STOP_RUN`     | Strategy proactively declares run completion (exceptional, not normal)     | System stops clock, status → COMPLETED          |

**Strategy Config Examples**:

```python
# SMA Crossover strategy config
{
    "symbols": ["BTC/USD", "ETH/USD"],
    "timeframe": "1h",
    "fast_period": 10,
    "slow_period": 20,
    "qty": 0.1,
    "exchange": "alpaca"          # Use Alpaca exchange
}

# S&P 500 tracking strategy config
{
    "universe": "sp500",           # Dynamic instruments: track S&P 500 constituents
    "rebalance_frequency": "monthly",
    "data_exchange": "alpaca",     # Fetch quotes from Alpaca
    "trade_exchange": "alpaca",    # Place orders on Alpaca
    "timeframe": "1d"
}

# Cross-exchange arbitrage strategy config
{
    "symbol": "BTC/USD",
    "exchanges": ["binance", "alpaca"],  # Monitor two exchanges simultaneously
    "spread_threshold": 0.005,
    "timeframe": "1m"
}

# Backtest-specific parameters (also passed via config)
{
    "symbols": ["BTC/USD"],
    "timeframe": "1h",
    "backtest_start": "2025-01-01T00:00:00Z",
    "backtest_end": "2025-12-31T23:59:59Z",
    "initial_cash": 50000
}
```

**Strategy Discovery**: The system uses AST (Abstract Syntax Tree) scanning of the `src/marvin/strategies/` directory, discovering strategies without importing them. Each strategy file must contain a `STRATEGY_META` dictionary. The backend provides a `GET /api/v1/strategies` endpoint, and the frontend presents strategies in a dropdown for user selection.

**STRATEGY_META Format**:

```python
STRATEGY_META = {
    "id": "sma-crossover",         # Unique identifier, Run's strategy_id corresponds to this value
    "class_name": "SMAStrategy",
    "name": "SMA Crossover Strategy",
    "version": "1.0",
    "description": "SMA crossover strategy: buy on golden cross, sell on death cross",
    "config_schema": {             # Optional: describes config structure for frontend dynamic form rendering
        "symbols": {"type": "list[str]", "required": True},
        "timeframe": {"type": "str", "default": "1h"},
        "fast_period": {"type": "int", "default": 10},
        "slow_period": {"type": "int", "default": 20},
    }
}
```

**Currently Available Strategies**:

| ID              | Name           | Logic                                                                  |
| --------------- | -------------- | ---------------------------------------------------------------------- |
| `sample`        | SampleStrategy | Mean reversion: buy when price < 99% of mean, sell when > 101% of mean |
| `sma-crossover` | SMAStrategy    | SMA crossover: buy on golden cross, sell on death cross                |

### 4.3 Exchange

An exchange is an external interface point for data and trading. The system interacts with any number of exchanges through the `ExchangeAdapter` abstraction layer.

**Exchanges Provide Two Types of Capabilities**:

| Capability  | Description                                                | Example                               |
| ----------- | ---------------------------------------------------------- | ------------------------------------- |
| **Data**    | Provides historical bars, real-time quotes, trade data     | Fetch the last 20 1h bars for BTC/USD |
| **Trading** | Submit orders, query orders, cancel orders, view positions | Submit a market buy order             |

Strategies can mix capabilities from different exchanges (fetch data from A, trade on B).

**Exchange Adapter Lifecycle**:

1. At system startup, `PluginAdapterLoader` scans and registers all available adapters
2. Based on credentials in the config file, instantiates and connects configured adapters
3. At runtime, strategies specify which adapter to use via the `exchange` parameter in `FETCH_WINDOW` and `PLACE_ORDER` actions
4. At system shutdown, disconnects all adapter connections

### 4.4 Clock

The clock controls the execution rhythm of strategies. Each tick represents the arrival of a time point.

| Clock Type      | Applicable Mode | Behavior                                                                                                                                                      |
| --------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BacktestClock` | Backtest        | No waiting, traverses time range at maximum speed; supports backpressure (waits for strategy to finish before next tick); auto-completes when time range ends |
| `RealtimeClock` | Paper / Live    | Aligns to real clock bar boundaries (e.g., every minute on the minute); precision target ±50ms; **never auto-stops**                                          |

**ClockTick Contents**:

| Field         | Description                                                                                |
| ------------- | ------------------------------------------------------------------------------------------ |
| `run_id`      | Owning Run                                                                                 |
| `ts`          | Current tick's time point (backtest = simulated time, live = real time)                    |
| `timeframe`   | Clock's base period (note: strategy can request data of different periods in FETCH_WINDOW) |
| `bar_index`   | Sequence number (starting from 0)                                                          |
| `is_backtest` | Whether in backtest mode (for logging only, strategy should not depend on this value)      |

**About Timeframe**: The clock's `timeframe` determines tick frequency (how often the strategy is triggered). But strategies can request data of any timeframe in `FETCH_WINDOW` — a strategy might request both 1h and 1d bars at a 1m tick frequency for multi-timeframe analysis.

### 4.5 Order

An order is the complete representation of a trading instruction.

**Order Types**:

| Type         | Description                                                |
| ------------ | ---------------------------------------------------------- |
| `MARKET`     | Market order, executes immediately at current market price |
| `LIMIT`      | Limit order, only executes when specified price is reached |
| `STOP`       | Stop order, becomes a market order when price is triggered |
| `STOP_LIMIT` | Stop-limit order                                           |

**Order State Machine**:

```
PENDING → SUBMITTING → SUBMITTED → ACCEPTED → FILLED
                                       │
                                       ├→ PARTIALLY_FILLED → FILLED
                                       ├→ CANCELLED
                                       ├→ REJECTED
                                       └→ EXPIRED
```

**Order Side**: `BUY` / `SELL`

**Order Exchange Affiliation**: Each order is associated with a specific exchange adapter instance. Order submission, query, and cancellation are all completed through that adapter.

### 4.6 Bar (Candlestick)

A bar represents the price summary for a single time period.

| Field       | Description          |
| ----------- | -------------------- |
| `symbol`    | Trading instrument   |
| `timeframe` | Period               |
| `timestamp` | Bar start time       |
| `open`      | Open price           |
| `high`      | High price           |
| `low`       | Low price            |
| `close`     | Close price          |
| `volume`    | Volume               |
| `exchange`  | Data source exchange |

### 4.7 Event

All communication between modules in the system is achieved through events. Each event is encapsulated in an **Envelope**.

**Envelope Fields**:

| Field          | Description                                                     |
| -------------- | --------------------------------------------------------------- |
| `id`           | Unique event ID (UUID)                                          |
| `kind`         | `evt` (event) or `cmd` (command)                                |
| `type`         | Event type (e.g., `strategy.FetchWindow`, `orders.Filled`)      |
| `version`      | Schema version                                                  |
| `run_id`       | Associated Run ID                                               |
| `corr_id`      | Correlation ID, used to trace the same request chain            |
| `causation_id` | Causation ID, points to the previous event that caused this one |
| `trace_id`     | Distributed trace ID                                            |
| `ts`           | UTC timestamp                                                   |
| `producer`     | Producer module name                                            |
| `payload`      | Event-specific data (dict)                                      |

### 4.8 Fill

A (partial) execution record of an order.

| Field        | Description      |
| ------------ | ---------------- |
| `order_id`   | Associated order |
| `qty`        | Fill quantity    |
| `price`      | Fill price       |
| `commission` | Commission       |
| `timestamp`  | Fill time        |

---

## 5. Deployment Architecture

### 5.1 Container Topology

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   frontend_dev   │  │   backend_dev    │  │     db_dev       │
│   (Vite / Nginx) │  │  (FastAPI/Uvicorn)│  │  (PostgreSQL 16) │
│   Port: 13579    │  │   Port: 18919    │  │   Port: 15432    │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         └─────────── Docker Compose Network ─────────┘
```

| Environment | Compose File             | Frontend                     | Backend                | DB Port  |
| ----------- | ------------------------ | ---------------------------- | ---------------------- | -------- |
| Development | `docker-compose.dev.yml` | Vite dev server (hot reload) | uvicorn --reload       | 15432    |
| Production  | `docker-compose.yml`     | Nginx static assets          | uvicorn (multi-worker) | 25432    |
| E2E Test    | `docker-compose.e2e.yml` | Built static assets          | Built and running      | Isolated |

### 5.2 Environment Variables

Injected via `docker/.env` file (generated by `init-env.sh` from the `example.env` template).

**Key Variables**:

| Variable                  | Description                  |
| ------------------------- | ---------------------------- |
| `DB_URL`                  | PostgreSQL connection string |
| `ALPACA_PAPER_API_KEY`    | Alpaca paper trading API Key |
| `ALPACA_PAPER_API_SECRET` | Alpaca paper trading Secret  |
| `ALPACA_LIVE_API_KEY`     | Alpaca live trading API Key  |
| `ALPACA_LIVE_API_SECRET`  | Alpaca live trading Secret   |
| `VITE_API_BASE`           | Frontend API base path       |

_Note: Exchange credential variables will expand as new adapters are added (e.g., `BINANCE_API_KEY`, etc.)._

### 5.3 Database

The database is a **required dependency** for system operation; there is no production scenario without a database.

`InMemoryEventLog` and other in-memory alternatives are used **only for unit tests** and are not intended as a production runtime option.

---

## 6. Database Schema

| Table              | Purpose                            | Write Frequency  | Mutability         |
| ------------------ | ---------------------------------- | ---------------- | ------------------ |
| `outbox`           | Event sourcing (all domain events) | Per event        | Append-only        |
| `consumer_offsets` | Consumer progress tracking         | Per consumption  | Updatable          |
| `bars`             | Historical bar data cache          | On data fetch    | Immutable (Upsert) |
| `veda_orders`      | Live/paper order status            | On order/update  | Updatable          |
| `runs`             | Run metadata (for crash recovery)  | On status change | Updatable          |
| `fills`            | Fill record audit                  | Per fill         | Append-only        |

---

## 7. Security & Reliability

### 7.1 Idempotency

- Orders are idempotent via `client_order_id`: the same `client_order_id` will not result in duplicate orders
- Events are deduplicated via `id` and `corr_id`

### 7.2 Crash Recovery

At startup, `RunManager.recover()` loads unfinished Runs from the database:

- Runs previously in `RUNNING` status → marked as `ERROR` (unclean shutdown)
- Runs previously in `PENDING` status → kept as-is (user can restart)

### 7.3 Event Reliability

Uses the **Outbox Pattern**: business operations and event writes are completed in the same database transaction, ensuring consistency.
After commit, subscribers are notified via PostgreSQL `LISTEN/NOTIFY`.

### 7.4 Run Isolation

- All events carry `run_id`
- Subscribers can filter by `run_id`
- Per-run components (Greta, StrategyRunner, Clock) are completely independent
- Multiple Runs can execute concurrently without interference

---

## 8. Architecture Invariants

These are rules that should **never be violated** in the system design:

1. **Single EventLog**: All components share one event log instance (distinguished by `run_id`)
2. **VedaService as Trading Entry Point**: External code does not directly call OrderManager or ExchangeAdapter
3. **Session per Request**: No long-lived database sessions
4. **SSE Receives All Events**: EventLog → SSEBroadcaster connection is always maintained
5. **Database Required**: Production runs must have a database (in-memory alternatives are for testing only)
6. **No Module-Level Singletons**: All services are obtained through dependency injection
7. **Multi-Run Concurrency**: Per-run instances vs singletons are clearly separated
8. **Run Isolation**: Events always carry run_id; consumers filter by run_id
9. **Plugin Architecture**: Strategies and exchange adapters are hot-pluggable, no hardcoded imports required
10. **Exchange Agnostic**: The system core does not depend on any specific exchange; all exchanges connect through a unified adapter protocol
11. **Strategy Autonomy**: Business parameters such as instruments, timeframes, and exchange selection are managed internally by strategies, not enforced at the system level

---

## 9. Document Navigation

| Document                             | Content                                                                  |
| ------------------------------------ | ------------------------------------------------------------------------ |
| **This Document** (SYSTEM_SPEC.md)   | System overview, architecture, terminology                               |
| [SPEC_BACKEND.md](SPEC_BACKEND.md)   | Backend API endpoints, service layer, data models, config system         |
| [SPEC_FRONTEND.md](SPEC_FRONTEND.md) | Frontend pages, components, interaction design, state management         |
| [SPEC_FLOWS.md](SPEC_FLOWS.md)       | End-to-end data flows, event routing, order lifecycle, sequence diagrams |

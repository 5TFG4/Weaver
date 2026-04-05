# Weaver Backend Functional Specification

> **Document type**: Backend Specification
> **Covers**: All REST API endpoints, service layer logic, data models, configuration system
> **Related documents**: [System Overview](SYSTEM_SPEC.md) · [Frontend Specification](SPEC_FRONTEND.md) · [Data Flow Specification](SPEC_FLOWS.md)

---

## Table of Contents

1. [REST API Endpoints](#1-rest-api-endpoints)
2. [Service Layer](#2-service-layer)
3. [Strategy System (Marvin)](#3-strategy-system-marvin)
4. [Backtesting Engine (Greta)](#4-backtesting-engine-greta)
5. [Trading Engine (Veda)](#5-trading-engine-veda)
6. [Event System (Events)](#6-event-system-events)
7. [Persistence Layer (WallE)](#7-persistence-layer-walle)
8. [Clock System](#8-clock-system)
9. [Configuration System](#9-configuration-system)
10. [Application Startup and Shutdown](#10-application-startup-and-shutdown)

---

## 1. REST API Endpoints

Base path: `/api/v1`

### 1.1 Health Check

#### `GET /api/v1/healthz`

Check whether the backend service is alive.

| Item            | Details                                  |
| --------------- | ---------------------------------------- |
| Request params  | None                                     |
| Response status | `200 OK`                                 |
| Response body   | `{ "status": "ok", "version": "0.1.0" }` |
| Frontend usage  | Dashboard polls every 30 seconds         |
| Dependencies    | None (always available)                  |

---

### 1.2 Runs (Run Management)

#### `POST /api/v1/runs` — Create Run

Create a new trading run with initial status `PENDING`.

**Request body** (`RunCreate`):

| Field         | Type   | Required | Description                                                                                                                                         |
| ------------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `strategy_id` | string | ✅       | Strategy identifier, corresponds to `STRATEGY_META.id` (e.g., `sma-crossover`). Frontend selects from `GET /strategies` dropdown                    |
| `mode`        | enum   | ✅       | `backtest` / `paper` / `live`                                                                                                                       |
| `config`      | dict   | ✅       | All strategy configuration parameters (including symbols, timeframe, backtest time range, exchange selection, etc., defined by the strategy itself) |

**About config**: Parameters like `symbols`, `timeframe`, `start_time`/`end_time` are no longer top-level fields of Run, but are unified into `config` for the strategy to interpret internally. Different strategies require completely different parameters (see SYSTEM_SPEC §4.2 for config examples).

**Processing flow**:

1. Generate UUID as `run_id`
2. Set status to `PENDING`
3. Emit `run.Created` event
4. If database is available, persist to `runs` table

**Response**: `201 Created` → `RunResponse`

**Validations that should exist but are currently missing**:

- ⚠️ Does not validate whether `strategy_id` exists (error deferred to startup) — should validate against the list returned by `GET /strategies`

---

#### `POST /api/v1/runs/{run_id}/start` — Start Run

Start a PENDING run, transitioning it to RUNNING.

**Precondition**: Run status must be `PENDING`

**Processing flow**:

1. Validate Run exists and status is PENDING (otherwise `409 Conflict`)
2. Set status to `RUNNING`, record `started_at`
3. Emit `run.Started` event
4. Branch by mode:
   - **Backtest**: Call `_start_backtest()` — synchronous execution, blocks until completion
   - **Live/Paper**: Call `_start_live()` — asynchronous background execution

**Response**: `200 OK` → `RunResponse`

**Failure scenarios**:

| Scenario                         | Result                                                              |
| -------------------------------- | ------------------------------------------------------------------- |
| Run does not exist               | `404 Not Found`                                                     |
| Status is not PENDING            | `409 Conflict`                                                      |
| Invalid strategy ID              | `500 Internal Server Error` (StrategyNotFoundError)                 |
| Backtest missing time range      | Strategy reads from config during initialization, errors if missing |
| `bars` cache is empty (backtest) | System fetches data on demand from exchange history API             |

---

#### `POST /api/v1/runs/{run_id}/stop` — Stop Run

Stop a running Run.

**Processing flow**:

1. Find Run
2. Execute cleanup sequence (`_cleanup_run_context`):
   - Stop clock (stop producing ticks)
   - Drain pending async tasks
   - Clean up StrategyRunner (cancel event subscriptions)
   - Clean up GretaService (if backtest)
   - Remove RunContext
3. Set status to `STOPPED`

**Response**: `200 OK` → `RunResponse`

---

#### `GET /api/v1/runs` — List Runs

**Query parameters**:

| Parameter   | Type   | Default | Description      |
| ----------- | ------ | ------- | ---------------- |
| `page`      | int    | 1       | Page number      |
| `page_size` | int    | 20      | Items per page   |
| `status`    | string | None    | Filter by status |

**Response**: `200 OK` → `RunListResponse { items[], total, page, page_size }`

**Note**: Pagination is implemented in-memory (fetch all then slice), suitable for small-to-medium scale data.

---

#### `GET /api/v1/runs/{run_id}` — Get Single Run

**Response**: `200 OK` → `RunResponse`, or `404 Not Found`

---

### 1.3 Orders (Order Management)

#### `POST /api/v1/orders` — Create Order

Manually create a trading order (direct order placement, not through a strategy).

**Precondition**: VedaService is initialized (requires exchange credentials + database)

**Request body** (`OrderCreate`):

| Field             | Type   | Required | Description                                     |
| ----------------- | ------ | -------- | ----------------------------------------------- |
| `run_id`          | string | ✅       | Associated Run ID                               |
| `client_order_id` | string | ✅       | Idempotency key                                 |
| `symbol`          | string | ✅       | Trading instrument                              |
| `side`            | enum   | ✅       | `buy` / `sell`                                  |
| `order_type`      | enum   | ✅       | `market` / `limit` / `stop` / `stop_limit`      |
| `qty`             | string | ✅       | Quantity                                        |
| `limit_price`     | string | No       | Limit price                                     |
| `stop_price`      | string | No       | Stop price                                      |
| `time_in_force`   | string | ✅       | Time in force (`day`/`gtc`/`ioc`/`fok`)         |
| `extended_hours`  | bool   | No       | Whether to allow pre-market/after-hours trading |

**Processing flow**:

1. Check VedaService is available (otherwise `503`)
2. Map OrderCreate to OrderIntent
3. Call `veda_service.place_order(intent)`
4. VedaService → OrderManager → ExchangeAdapter → Exchange (routed to exchange specified in strategy config)
5. Persist to `veda_orders` table
6. Emit `orders.Created` or `orders.Rejected` event

**Response**: `201 Created` → `OrderResponse`

---

#### `GET /api/v1/orders` — List Orders

**Query parameters**:

| Parameter   | Type   | Default | Description      |
| ----------- | ------ | ------- | ---------------- |
| `run_id`    | string | None    | Filter by Run    |
| `status`    | string | None    | Filter by status |
| `page`      | int    | 1       | Page number      |
| `page_size` | int    | 50      | Items per page   |

**Fallback behavior**: When VedaService is unavailable, falls back to MockOrderService (returns hardcoded mock data). Only for UI development.

---

#### `GET /api/v1/orders/{order_id}` — Get Single Order

**Response**: `200 OK` → `OrderResponse`, or `404 Not Found`

---

#### `DELETE /api/v1/orders/{order_id}` — Cancel Order

Cancel an active order.

**Processing flow**:

1. VedaService calls `cancel_order()`
2. Send cancellation request to exchange via ExchangeAdapter
3. Update local state + persist
4. Emit `orders.Cancelled` event

**Response**: `204 No Content`

---

#### `POST /api/v1/orders/{order_id}/sync` — Sync Order Status

Pull the latest order status from the exchange and update locally.

**Processing flow**:

1. VedaService calls `sync_order(client_order_id)`
2. Query current status from exchange via ExchangeAdapter
3. Update local OrderState + database
4. If status changed, emit corresponding event

**Response**: `200 OK` → `OrderResponse`

**Purpose**: Manually check whether an order has been filled on the exchange, in the absence of an automatic fill confirmation mechanism.

---

### 1.4 Strategies (Strategy Listing)

#### `GET /api/v1/strategies` — List Available Strategies

Return metadata for all strategies discovered by `PluginStrategyLoader`, for frontend dropdown selection.

**Response**: `200 OK` → `StrategyListResponse`

```json
{
  "items": [
    {
      "id": "sma-crossover",
      "name": "SMA Crossover Strategy",
      "version": "1.0",
      "description": "SMA crossover strategy: buy on golden cross, sell on death cross",
      "config_schema": {
        "symbols": { "type": "list[str]", "required": true },
        "timeframe": { "type": "str", "default": "1h" },
        "fast_period": { "type": "int", "default": 10 },
        "slow_period": { "type": "int", "default": 20 }
      }
    }
  ]
}
```

The frontend uses `config_schema` to dynamically render strategy configuration forms.

---

### 1.5 Candlestick Data

#### `GET /api/v1/candles` — Get Candlesticks

**Query parameters**:

| Parameter   | Type   | Required | Description                   |
| ----------- | ------ | -------- | ----------------------------- |
| `symbol`    | string | ✅       | Trading instrument            |
| `timeframe` | string | ✅       | Candlestick period            |
| `limit`     | int    | No       | Number to return, default 100 |

**⚠️ Current status**: Returns fake data generated by MockMarketDataService (random walk), not real market data. Should fetch real data from exchange adapters.

---

### 1.6 SSE Event Stream

#### `GET /api/v1/events/stream` — Server-Sent Events

**Query parameters**:

| Parameter | Type   | Description                                     |
| --------- | ------ | ----------------------------------------------- |
| `run_id`  | string | Optional, receive only events for specified Run |

**Behavior**:

- Establish a persistent SSE connection
- Push all domain events to the frontend in real time
- Support filtering by `run_id` (only events with `run_id` in payload pass through)
- System events without `run_id` always pass through
- Events that fail JSON parsing always pass through (not dropped)

**Event format**:

```
event: orders.Filled
data: {"id": "...", "type": "orders.Filled", "payload": {...}}
```

---

## 2. Service Layer

### 2.1 RunManager (Run Manager)

| Method               | Responsibility                                                           |
| -------------------- | ------------------------------------------------------------------------ |
| `create(run_create)` | Create Run, generate UUID, status PENDING, emit event, persist           |
| `start(run_id)`      | Start Run, load strategy, create per-run components, begin execution     |
| `stop(run_id)`       | Stop Run, clean up all per-run components                                |
| `get(run_id)`        | Query Run                                                                |
| `list(status?)`      | List Runs (optionally filter by status)                                  |
| `recover()`          | Recover Runs from database on startup (RUNNING→ERROR, PENDING preserved) |

**RunContext** (context held by each running Run):

| Field           | Description                            |
| --------------- | -------------------------------------- |
| `greta`         | GretaService instance (backtest only)  |
| `runner`        | StrategyRunner instance                |
| `clock`         | BaseClock instance                     |
| `pending_tasks` | Set of async tasks spawned by this Run |

### 2.2 DomainRouter (Domain Router)

Routes generic events emitted by strategies to the correct domain.

**Routing rules**:

| Source event            | Backtest mode target   | Live/Paper mode target |
| ----------------------- | ---------------------- | ---------------------- |
| `strategy.FetchWindow`  | `backtest.FetchWindow` | `live.FetchWindow`     |
| `strategy.PlaceRequest` | `backtest.PlaceOrder`  | `live.PlaceOrder`      |

**Processing logic**:

1. Only process events in the `strategy.*` namespace
2. Look up the Run's mode by `run_id`
3. Rewrite event type (preserving causal chain: `corr_id`, `causation_id`)
4. Append to EventLog

**Significance**: This is the core mechanism for "one set of strategy code running in three modes." Strategies only emit `strategy.*` events and have no knowledge of which mode they are running in.

### 2.3 SSEBroadcaster (SSE Broadcaster)

Manages multiple frontend SSE connections, broadcasting events to all connected clients.

| Configuration         | Value                                |
| --------------------- | ------------------------------------ |
| Per-client queue size | 100 items                            |
| Full queue policy     | Drop new events (non-blocking)       |
| Client registration   | `subscribe()` returns async iterator |

### 2.4 MockOrderService

Fallback replacement when VedaService is unavailable. Returns 2 hardcoded mock order records.
Only for demos and UI development, does not perform any real trading.

### 2.5 MockMarketDataService

Returns fake candlestick data based on random walk. Base price $42,000.
⚠️ Currently the only provider for `GET /candles` and live/paper data requests.

---

## 3. Strategy System (Marvin)

### 3.1 Strategy Interface

All strategies must inherit from `BaseStrategy` and implement three methods:

```python
class MyStrategy(BaseStrategy):
    async def initialize(self, config: dict) -> None:
        """Called once when the Run starts. Reads all required parameters from config:
        instrument list, timeframe, indicator parameters, exchange selection, etc."""

    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]:
        """Triggered on each candlestick. Typically returns FETCH_WINDOW to request data.
        Strategy can request any instrument, any timeframe, and specify any exchange."""

    async def on_data(self, data: Any) -> list[StrategyAction]:
        """Triggered after receiving requested data. Analyzes data and decides whether to place orders.
        Can specify target exchange when placing orders."""
```

### 3.2 Strategy Execution Loop

Complete strategy execution flow for one candlestick:

```
Clock tick
  → StrategyRunner.on_tick(tick)
    → strategy.on_tick(tick)
      → Returns [FETCH_WINDOW(symbol="BTC/USD", lookback=20, exchange="alpaca")]
        → StrategyRunner emits strategy.FetchWindow event
          → DomainRouter routes to backtest.FetchWindow or live.FetchWindow
            → Greta/MarketData returns data (backtest reads cache first, fetches on demand on cache miss), emits data.WindowReady event
              → StrategyRunner.on_data_ready() receives
                → Deserializes raw dict into Bar objects
                  → strategy.on_data(bars)
                    → Returns [PLACE_ORDER(side=BUY, qty=0.1, type=MARKET, exchange="alpaca")]
                      → StrategyRunner emits strategy.PlaceRequest event
                        → DomainRouter routes to execution engine
```

### 3.3 Strategy Discovery Mechanism (PluginStrategyLoader)

- Scans the `src/marvin/strategies/` directory
- Uses Python AST (Abstract Syntax Tree) to parse each `.py` file
- Extracts the `STRATEGY_META` constant (no module import required)
- Supports dependency resolution and circular dependency detection
- Only actually imports the strategy class when `load(strategy_id)` is called

**STRATEGY_META format**:

```python
STRATEGY_META = {
    "id": "sma-crossover",
    "class_name": "SMAStrategy",
    "name": "SMA Crossover Strategy",
    "version": "1.0",
    "description": "Buy on golden cross, sell on death cross",
    "config_schema": {             # Describes config structure, for frontend to dynamically render forms
        "symbols": {"type": "list[str]", "required": True},
        "timeframe": {"type": "str", "default": "1h"},
        "fast_period": {"type": "int", "default": 10},
        "slow_period": {"type": "int", "default": 20},
        "exchange": {"type": "str", "default": "alpaca"},
    }
}
```

### 3.4 StrategyRunner

Per-run instance, responsible for:

1. Initializing the strategy and subscribing to `data.WindowReady` events (filtered by `run_id`)
2. Executing strategy logic on each tick
3. Translating StrategyActions returned by the strategy into events
4. Receiving data events, deserializing them, and passing to the strategy
5. Canceling all event subscriptions during cleanup

**Bar deserialization**: Greta serializes Bar objects into dictionaries when emitting `data.WindowReady`. StrategyRunner's `on_data_ready()` is responsible for restoring these dictionaries back into Bar objects (including Decimal fields and datetime timestamps), ensuring strategies can access properties like `bar.close`.

---

## 4. Backtesting Engine (Greta)

### 4.1 Instance Model

Each backtest Run creates an independent `GretaService` instance with fully isolated:

- Simulated positions (independent per instrument)
- Pending order queue
- Fill records
- Cash balance (initial $100,000)
- Equity curve

Shared dependencies: `BarRepository` (read-only, historical candlesticks) and `EventLog` (event bus).

### 4.2 Lifecycle

#### Initialization (`initialize`)

1. Reset all per-run mutable state
2. Preload candlesticks for the specified time range and instruments from `BarRepository` into memory cache; fetch on demand via exchange history API on cache miss and write to database
3. Subscribe to `backtest.FetchWindow` and `backtest.PlaceOrder` events (filtered by `run_id`)

#### Time Advancement (`advance_to`)

Called once per tick, simulating time advancement to the current candlestick:

1. Update current candlestick data
2. Check whether all pending orders trigger a fill
3. Recalculate position market value at current price
4. Record equity curve point

#### Cleanup

- Cancel event subscriptions
- Return BacktestResult (statistics + equity curve + fill records)
- Instance is discarded by RunManager

### 4.3 Simulated Fills (DefaultFillSimulator)

#### Fill Determination Logic

| Order type   | Fill condition           | Fill price                                                   |
| ------------ | ------------------------ | ------------------------------------------------------------ |
| Market order | Fills immediately        | Candlestick open price (configurable: open/close/vwap/worst) |
| Limit Buy    | `bar.low ≤ limit_price`  | `limit_price`                                                |
| Limit Sell   | `bar.high ≥ limit_price` | `limit_price`                                                |
| Stop Buy     | `bar.high ≥ stop_price`  | `stop_price`                                                 |
| Stop Sell    | `bar.low ≤ stop_price`   | `stop_price`                                                 |

#### Cost Model

| Parameter  | Description                               | Calculation                                                     |
| ---------- | ----------------------------------------- | --------------------------------------------------------------- |
| Slippage   | Simulates price deviation in real trading | `price × (slippage_bps / 10000)`, direction always adverse      |
| Commission | Trading fees                              | `notional × (commission_bps / 10000)`, minimum `min_commission` |

**Configuration** (`FillSimulationConfig`):

- `slippage_bps`: Slippage in basis points
- `commission_bps`: Commission in basis points
- `min_commission`: Minimum commission
- `fill_at`: Market order fill reference price (`open` / `close` / `vwap` / `worst`)

### 4.4 Position Tracking (SimulatedPosition)

| Operation                     | Handling                                               |
| ----------------------------- | ------------------------------------------------------ |
| New position                  | Record direction, quantity, entry avg price            |
| Add to position               | Calculate new avg price by weighted average            |
| Partial close                 | Reduce quantity, calculate realized P&L proportionally |
| Full close                    | Clear position, record realized P&L                    |
| Reverse (e.g., long to short) | Close long first, then open short                      |

Cash is adjusted on each fill:

- Buy: Decrease by `notional + commission`
- Sell: Increase by `notional - commission`

### 4.5 Backtest Result (BacktestResult)

Complete statistical report computed at the end of a backtest:

| Metric             | Description                               |
| ------------------ | ----------------------------------------- |
| `total_return`     | Total return amount                       |
| `total_return_pct` | Total return percentage                   |
| `final_equity`     | Final equity                              |
| `sharpe_ratio`     | Sharpe ratio (non-annualized, per period) |
| `sortino_ratio`    | Sortino ratio                             |
| `max_drawdown`     | Maximum drawdown                          |
| `win_rate`         | Win rate                                  |
| `profit_factor`    | Profit factor                             |
| `total_commission` | Total commission                          |
| `total_slippage`   | Total slippage cost                       |

Trade statistics use **FIFO batch matching** to calculate per-trade P&L.

### 4.6 Event Interactions

| Direction | Event                  | Description                               |
| --------- | ---------------------- | ----------------------------------------- |
| Inbound   | `backtest.FetchWindow` | Strategy requests historical data window  |
| Inbound   | `backtest.PlaceOrder`  | Strategy requests order placement         |
| Outbound  | `data.WindowReady`     | Returns requested candlestick data        |
| Outbound  | `orders.Created`       | Order created                             |
| Outbound  | `orders.Filled`        | Order filled                              |
| Outbound  | `orders.Rejected`      | Order rejected (e.g., insufficient funds) |

---

## 5. Trading Engine (Veda)

### 5.1 ExchangeAdapter Protocol

Abstract interface for exchange adapters; all adapters must implement:

| Method group | Method                             | Description                      |
| ------------ | ---------------------------------- | -------------------------------- |
| Connection   | `connect()`                        | Establish connection to exchange |
| Orders       | `submit_order(intent)`             | Submit order                     |
| Orders       | `cancel_order(exchange_id)`        | Cancel order                     |
| Orders       | `get_order(exchange_id)`           | Query order status               |
| Account      | `get_account()`                    | Get account information          |
| Positions    | `get_positions()`                  | Get current positions            |
| Market data  | `get_bars(symbol, timeframe, ...)` | Get historical candlesticks      |
| Market data  | `get_latest_quote(symbol)`         | Get latest quote                 |
| Bulk         | `cancel_all_orders()`              | Cancel all orders                |
| Bulk         | `close_all_positions()`            | Close all positions              |

### 5.2 AlpacaAdapter

Concrete implementation for the Alpaca exchange (currently the only real adapter in the system; more exchange adapters can be added later).

**Connection**:

- Create `TradingClient` (trading)
- Create `StockHistoricalDataClient` (stock historical data)
- Create `CryptoHistoricalDataClient` (cryptocurrency historical data)
- Verify account status is ACTIVE

**Order submission**:

- Map OrderIntent to Alpaca SDK request types
- Submit asynchronously via `asyncio.to_thread` (SDK is synchronous)
- Return `OrderSubmitResult` (containing exchange-assigned `exchange_order_id`)

**Dual credential system**:

- Supports simultaneous configuration of live and paper Alpaca credentials
- Selected via `AlpacaConfig.get_credentials(mode)`

### 5.3 MockExchangeAdapter

Mock adapter for testing.

- Market orders fill immediately (BTC/USD=$42000, ETH/USD=$2500)
- Limit orders remain in ACCEPTED status
- Configurable rejection behavior
- Idempotent submission

### 5.4 VedaService

Main entry point for the Veda module, singleton, initialized at application startup. Manages all registered exchange adapters and routes orders to the exchange specified by the strategy.

| Method                          | Responsibility                                                                    |
| ------------------------------- | --------------------------------------------------------------------------------- |
| `connect()`                     | Initialize all configured ExchangeAdapters (e.g., Alpaca, Binance, etc.)          |
| `place_order(intent)`           | Place order: idempotency check → submit to exchange → persist → emit event        |
| `sync_order(client_order_id)`   | Pull latest status from exchange and update locally                               |
| `cancel_order(client_order_id)` | Cancel order                                                                      |
| `list_orders(run_id?, status?)` | List orders                                                                       |
| `handle_place_order(envelope)`  | Event handler: responds to `live.PlaceOrder` events to automatically place orders |

### 5.5 OrderManager

Local order state tracking.

- Maintains `client_order_id → OrderState` mapping
- Guarantees idempotency via `client_order_id` (same ID will not be submitted to exchange twice)
- Wraps ExchangeAdapter's submit/cancel/query operations

### 5.6 PositionTracker

Tracks position state.

- Updates positions based on fill records (quantity, avg price, cost basis)
- Handles adding to position, reducing position, reversing position
- ⚠️ Currently not synchronized with actual exchange positions

### 5.7 OrderRepository

Order persistence repository.

- `save(order_state)` — Upsert to `veda_orders` table
- `get_by_client_order_id()` — Query by idempotency key
- `list(run_id?, status?)` — List query

---

## 6. Event System (Events)

### 6.1 Event Namespaces

| Namespace    | Events                                                                 | Producer           | Description                   |
| ------------ | ---------------------------------------------------------------------- | ------------------ | ----------------------------- |
| `strategy.*` | FetchWindow, PlaceRequest, DecisionMade                                | StrategyRunner     | Strategy's generic intents    |
| `backtest.*` | FetchWindow, PlaceOrder                                                | DomainRouter       | Routed backtest commands      |
| `live.*`     | FetchWindow, PlaceOrder                                                | DomainRouter       | Routed live commands          |
| `data.*`     | WindowReady, WindowChunk, WindowComplete                               | Greta / MarketData | Data responses                |
| `orders.*`   | Created, Placed, Filled, PartiallyFilled, Cancelled, Rejected, Expired | Greta / Veda       | Order lifecycle               |
| `run.*`      | Created, Started, Stopped, Completed, Error, Heartbeat                 | RunManager         | Run lifecycle                 |
| `clock.*`    | Tick                                                                   | Clock              | Clock tick                    |
| `market.*`   | Quote, Trade, Bar                                                      | Market data source | Real-time quotes              |
| `ui.*`       | RunUpdated, OrderUpdated, PositionUpdated                              | System             | Frontend update notifications |

### 6.2 Event Log Implementation

Two implementations:

| Implementation     | Use case   | Persistent | Mechanism                    |
| ------------------ | ---------- | ---------- | ---------------------------- |
| `InMemoryEventLog` | Unit tests | No         | In-memory list               |
| `PostgresEventLog` | Production | Yes        | outbox table + LISTEN/NOTIFY |

**Outbox pattern how it works**:

1. Business operations and event writes are completed within the same database transaction
2. After transaction commit, subscribers are notified via PostgreSQL `pg_notify()`
3. Subscribers receive notifications directly in-process (no polling needed)

### 6.3 Subscription API

```python
# Subscribe to a specific event type
unsubscribe = event_log.subscribe("orders.Filled", handler)

# Subscribe with run_id filter
unsubscribe = event_log.subscribe(
    "data.WindowReady",
    handler,
    filter_run_id="some-run-id"
)
```

### 6.4 Consumer Offsets

`EventConsumer` provides at-least-once delivery guarantee:

- Maintains `last_offset` for each consumer
- Continues consuming from the last read position
- `InMemoryOffsetStore` or `PostgresOffsetStore`

---

## 7. Persistence Layer (WallE)

### 7.1 Database Models

#### OutboxEvent

```
outbox (event sourcing table)
├── id: BigInteger (PK, auto-increment)
├── type: String (event type, indexed)
├── payload: JSONB (event data)
└── created_at: DateTime (creation time, indexed)
    Index: (type, created_at)
```

#### BarRecord

```
bars (historical candlestick table)
├── id: BigInteger (PK)
├── symbol: String (trading instrument)
├── timeframe: String (candlestick period)
├── timestamp: DateTime (candlestick time)
├── open: Numeric (open price)
├── high: Numeric (high price)
├── low: Numeric (low price)
├── close: Numeric (close price)
└── volume: Numeric (volume)
    Unique constraint: (symbol, timeframe, timestamp)
```

#### VedaOrder

```
veda_orders (order state table)
├── id: String (PK, client_order_id)
├── client_order_id: String (unique)
├── exchange_order_id: String (nullable)
├── run_id: String
├── symbol, side, order_type, qty, limit_price, stop_price
├── time_in_force, filled_qty, filled_avg_price
├── status: String
├── reject_reason: String (nullable)
├── created_at, submitted_at, filled_at
    Indexes: (run_id, status), (symbol, status)
```

#### RunRecord

```
runs (run metadata table)
├── id: String (PK, UUID)
├── strategy_id, mode, status
├── config: JSONB (all strategy configuration parameters, including symbols/timeframe/backtest range, etc.)
├── created_at, started_at, stopped_at
    Index: (status, created_at)
```

#### FillRecord

```
fills (fill audit table)
├── id: BigInteger (PK)
├── order_id: String (associated order)
├── price: Numeric
├── quantity: Numeric
└── filled_at: DateTime
    Index: (order_id, filled_at)
```

### 7.2 Repository Interfaces

| Repository        | Operations                                                              | Characteristics                  |
| ----------------- | ----------------------------------------------------------------------- | -------------------------------- |
| `BarRepository`   | save_bars(upsert), get_bars(range query), get_bar_count, get_latest_bar | Singleton, immutable data shared |
| `RunRepository`   | save, get, list                                                         | Used for crash recovery          |
| `FillRepository`  | save, list_by_order                                                     | Append-only, audit trail         |
| `OrderRepository` | save(upsert), get_by_client_order_id, list                              | Mutable state snapshot           |

### 7.3 Migration Management

Using Alembic:

| Migration                   | Contents                  |
| --------------------------- | ------------------------- |
| `001_initial_tables`        | outbox + consumer_offsets |
| `add_veda_orders_table`     | veda_orders               |
| `add_bars_table`            | bars                      |
| `add_runs_and_fills_tables` | runs + fills              |

---

## 8. Clock System

### 8.1 BaseClock Interface

| Method              | Description                                     |
| ------------------- | ----------------------------------------------- |
| `start(run_id)`     | Start emitting ticks                            |
| `stop()`            | Stop the clock                                  |
| `wait()`            | Wait for natural completion or cancellation     |
| `current_time()`    | Return current time (real or simulated)         |
| `on_tick(callback)` | Register tick callback, returns cancel function |
| `is_running`        | Property: whether running                       |
| `tick_count`        | Property: number of ticks emitted               |

Callback timeout: Defaults to 30 seconds. On timeout, the callback is skipped (does not block the entire clock).

### 8.2 BacktestClock

| Feature        | Description                                                      |
| -------------- | ---------------------------------------------------------------- |
| Speed          | No sleep, advances at maximum speed                              |
| Determinism    | Same input produces same tick sequence                           |
| Backpressure   | Can be enabled, waits for strategy confirmation before advancing |
| Error property | `clock.error` exposes exceptions caught during tick processing   |
| Progress       | `clock.progress` → 0.0 ~ 1.0                                     |

### 8.3 RealtimeClock

| Feature        | Description                                                              |
| -------------- | ------------------------------------------------------------------------ |
| Alignment      | Aligns to candlestick boundaries (e.g., 1m = every minute on the minute) |
| Precision      | Target ±50ms                                                             |
| Sleep strategy | Long sleep when far from boundary, precise sleep when close              |
| Tick time      | Uses scheduled time (not actual emission time)                           |

### 8.4 Clock Factory

```python
config = ClockConfig(
    timeframe=strategy_config.get("timeframe", "1h"),
    backtest_start=strategy_config.get("backtest_start"),  # Has value → BacktestClock
    backtest_end=strategy_config.get("backtest_end"),      # No value → RealtimeClock
)
clock = create_clock(config)
```

---

## 9. Configuration System

Based on pydantic-settings, loaded from environment variables.

### 9.1 Sub-configurations

| Config class     | Contents                                         |
| ---------------- | ------------------------------------------------ |
| `DatabaseConfig` | DB_URL, connection pool size, SQL echo           |
| `AlpacaConfig`   | Live + Paper dual API credentials                |
| `ServerConfig`   | Host, port, worker count, log level              |
| `EventConfig`    | Batch size, polling interval, retention days     |
| `TradingConfig`  | Default timeframe, concurrent orders, rate limit |
| `SecurityConfig` | Auth requirement, API Token, Key Header          |

### 9.2 Exchange Adapter Configuration

Each exchange adapter has its own config class. Using Alpaca as an example:

```python
class AlpacaConfig:
    live_api_key: str
    live_api_secret: str
    live_base_url: str

    paper_api_key: str
    paper_api_secret: str
    paper_base_url: str

    def get_credentials(mode) → AlpacaCredentials
    # mode=PAPER → Returns paper credentials
    # mode=LIVE → Returns live credentials
```

_Note: As new exchange adapters are added, corresponding config classes will be added (e.g., `BinanceConfig`)._

---

## 10. Application Startup and Shutdown

### 10.1 Startup Sequence

```
1. Create always-available services
   ├── MockOrderService (UI development fallback only)
   ├── MockMarketDataService (testing fallback only)
   └── SSEBroadcaster

2. Initialize database (DB_URL must be configured)
   ├── Database.init()
   ├── Alembic migrations
   └── Create PostgresEventLog

3. Initialize exchange adapters
   ├── Scan exchanges with configured credentials
   ├── Create corresponding ExchangeAdapter instances (e.g., AlpacaAdapter)
   ├── Create VedaService (manages all adapters)
   └── Each adapter.connect()

4. Create runtime components
   ├── PluginStrategyLoader
   ├── RunManager (inject: EventLog, BarRepository, RunRepository, StrategyLoader)
   └── DomainRouter (inject: EventLog, RunManager)

5. Connect event subscriptions
   ├── SSEBroadcaster subscribes to EventLog (all events → SSE push)
   ├── DomainRouter subscribes to strategy.* events
   └── MarketDataService subscribes to live.FetchWindow events

6. Crash recovery
   └── RunManager.recover() (recover unfinished Runs from database)
```

### 10.2 Shutdown Sequence

```
1. Cancel all event subscriptions
2. Stop all running Runs
3. Close database connections
```

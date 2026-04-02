# Weaver Production Test Review

> **Purpose**: Comprehensive system state assessment for production readiness.
> Covers every feature end-to-end, identifies gaps between implementation and usability,
> and documents what works, what doesn't, and what's missing.
>
> **Created**: 2026-04-01
> **Context**: Branch `prod-test`, post-M11. All 1137 automated tests pass.
> This document captures findings from manual inspection of every module, every
> API endpoint, every frontend page, and the database state.

---

## Table of Contents

1. [System Summary](#1-system-summary)
2. [Frontend (Haro) — Page-by-Page Audit](#2-frontend-haro--page-by-page-audit)
3. [Backend API — Endpoint-by-Endpoint Audit](#3-backend-api--endpoint-by-endpoint-audit)
4. [Strategy System (Marvin) — Audit](#4-strategy-system-marvin--audit)
5. [Backtest Engine (Greta) — Audit](#5-backtest-engine-greta--audit)
6. [Live/Paper Trading (Veda) — Audit](#6-livepaper-trading-veda--audit)
7. [Event System — Audit](#7-event-system--audit)
8. [Persistence (WallE) — Audit](#8-persistence-walle--audit)
9. [Data Pipeline — Audit](#9-data-pipeline--audit)
10. [End-to-End Flow Analysis](#10-end-to-end-flow-analysis)
11. [Gap Summary](#11-gap-summary)
12. [Discussion Topics](#12-discussion-topics)

---

## 1. System Summary

Weaver is an automated trading system supporting three execution modes with a
single strategy codebase:

| Mode         | Clock                        | Fill Engine             | Exchange     | Data Source               |
| ------------ | ---------------------------- | ----------------------- | ------------ | ------------------------- |
| **Backtest** | BacktestClock (fast-forward) | Greta (simulated fills) | None         | `bars` table (historical) |
| **Paper**    | RealtimeClock (wall-clock)   | Veda → Alpaca Paper API | Alpaca Paper | ❌ MockMarketDataService  |
| **Live**     | RealtimeClock (wall-clock)   | Veda → Alpaca Live API  | Alpaca Live  | ❌ MockMarketDataService  |

### Current Dev Stack Status (as of 2026-04-01)

| Service                              | Container    | Port  | Status     |
| ------------------------------------ | ------------ | ----- | ---------- |
| Backend (FastAPI + uvicorn --reload) | backend_dev  | 18919 | ✅ Running |
| Frontend (Vite dev server)           | frontend_dev | 13579 | ✅ Running |
| PostgreSQL 16                        | db_dev       | 15432 | ✅ Healthy |

Access: `http://<server-ip>:13579/dashboard` (frontend), `http://<server-ip>:18919/docs` (Swagger UI)

### Database State

| Table         | Row Count | Notes                                                  |
| ------------- | --------- | ------------------------------------------------------ |
| `bars`        | **0**     | No historical data loaded                              |
| `runs`        | 2         | Both PENDING, strategy_id = "TEST" / "TEST2" (invalid) |
| `veda_orders` | 0         | —                                                      |
| `fills`       | 0         | —                                                      |
| `outbox`      | 2         | run.Created events for the 2 test runs                 |

---

## 2. Frontend (Haro) — Page-by-Page Audit

### 2.1 Dashboard (`/dashboard`)

**What works:**

- 4 stat cards render: Active Runs, Total Runs, Total Orders, API Status
- API Status polls `/healthz` every 30s, shows green "Online" when backend is up
- Recent Activity feed shows last 5 runs with strategy name, symbols, status badge, relative time
- Loading state shows shimmer placeholders
- Error state shows red error message

**What doesn't work / is misleading:**

- Active Runs count only checks `status === "running"` — currently always 0 because
  there's no way to start a run from the UI (see §2.2)
- Total Orders always 0 because no orders have been placed (see §6)

**Missing features:**

- No equity curve chart, no P&L summary, no portfolio overview
- No strategy performance comparison
- No market data display (current prices, charts)

### 2.2 Runs Page (`/runs`)

**What works:**

- Runs table renders with correct columns (ID, Strategy, Symbols, Mode, Status, Created, Actions)
- "New Run" button opens inline CreateRunForm
- CreateRunForm has 4 fields: Strategy (text), Mode (dropdown), Symbols (text), Timeframe (dropdown)
- Stop button appears for running/pending runs with optimistic UI
- Deep-link mode: `/runs/:runId` fetches single run
- Empty state with "No runs yet" message
- Toast notifications on success/error

**Critical gaps:**

| Gap                                 | Impact                                                                                                                                                                  | Severity              |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **No Start button**                 | Created runs stay PENDING forever. `useStartRun()` hook exists, `POST /runs/{id}/start` endpoint exists, but no UI element calls it.                                    | 🔴 Blocker            |
| **No start_time / end_time inputs** | Backtest mode requires time range, but form doesn't expose these fields. `RunCreate` schema supports them, UI doesn't.                                                  | 🔴 Blocker (backtest) |
| **No config input**                 | SMA strategy accepts `fast_period`, `slow_period`, `qty` config. No way to pass config from UI.                                                                         | 🟡 Medium             |
| **Strategy ID is free-text**        | User must type exact strategy ID (`sample` or `sma-crossover`). No dropdown, no autocomplete, no validation. If you type "TEST" it creates the run but start will fail. | 🟡 Medium             |
| **No strategy list API**            | `PluginStrategyLoader.list_available()` method exists but no REST endpoint exposes it. Frontend can't show a dropdown of valid strategies.                              | 🟡 Medium             |
| **No backtest results display**     | After backtest completes, `BacktestResult` (equity curve, stats, fills) is computed in Greta but there's no API to retrieve it and no UI to show it.                    | 🟡 Medium             |
| **No run detail page**              | Deep-link shows single run in the same table format. No dedicated detail view with orders, fills, equity curve, events for that run.                                    | 🟠 Low-Medium         |

### 2.3 Orders Page (`/orders`)

**What works:**

- Orders table with all columns (ID, Symbol, Side, Type, Qty, Price, Status, Time)
- Side badges: green "buy" / red "sell"
- Status filter dropdown (All, Pending, Submitted, Accepted, Partial, Filled, Cancelled, Rejected, Expired)
- URL param `?run_id=xxx` pre-filters orders to a run
- Click any row → OrderDetailModal with 15+ fields in 2-column grid
- OrderDetailModal shows reject reason in red box if applicable
- Empty state displayed correctly

**Gaps:**

| Gap                          | Impact                                                                                                                                             | Severity  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **No Order Sync button**     | `POST /orders/{id}/sync` endpoint exists, `syncOrder()` API function may exist, but no UI button to trigger it. This was a key feature of this PR. | 🟡 Medium |
| **No Cancel Order button**   | `useCancelOrder()` hook defined, `DELETE /orders/{id}` endpoint exists, but no UI element uses it.                                                 | 🟡 Medium |
| **No manual order creation** | `POST /orders` endpoint exists for manually placing orders through Veda, but no "New Order" button exists in the UI.                               | 🟠 Low    |

### 2.4 SSE Real-Time Updates

**What works:**

- EventSource connects to `/api/v1/events/stream`
- Auto-reconnect after 3s on connection loss
- Connection status indicator in header (green dot "Connected" / red dot "Disconnected")
- Event-to-cache-invalidation mapping:

| SSE Event          | Action                              |
| ------------------ | ----------------------------------- |
| `run.Started`      | Refresh runs list + success toast   |
| `run.Stopped`      | Refresh runs list + info toast      |
| `run.Completed`    | Refresh runs list + success toast   |
| `run.Error`        | Refresh runs list + error toast     |
| `orders.Created`   | Refresh orders list + info toast    |
| `orders.Filled`    | Refresh orders list + success toast |
| `orders.Rejected`  | Refresh orders list + error toast   |
| `orders.Cancelled` | Refresh orders list + info toast    |

**Gaps:**

- No SSE event for `run.Created` handling (cache not auto-refreshed when another client creates a run)
- No SSE events for backtest progress (completion %, current simulated time)

### 2.5 Layout & Navigation

**What works:**

- Dark theme (slate-900 background), consistent across all pages
- Sidebar with 3 nav items: Dashboard, Runs, Orders (with active highlighting)
- Header with Weaver logo and SSE connection indicator
- Toast notification system (bottom-right, auto-dismiss 5s, color-coded by type)
- Responsive grid layouts

**Gaps:**

- No Settings page (can't view/edit Alpaca credentials, DB status, strategy config)
- No Logs / Events page (can't see raw event stream)
- No Candles / Charts page (candles endpoint exists but no chart visualization)

---

## 3. Backend API — Endpoint-by-Endpoint Audit

### 3.1 Health (`GET /api/v1/healthz`)

✅ **Working**. Returns `{"status": "ok", "version": "0.1.0"}`.

No issues.

### 3.2 Runs

#### `POST /api/v1/runs` — Create Run

✅ **Working**. Creates run with UUID, PENDING status, emits `run.Created`, persists to DB.

**Schema:** `RunCreate { strategy_id, mode, symbols[], timeframe?, start_time?, end_time?, config? }`

Issues:

- Accepts any `strategy_id` string without validation. The error only surfaces later
  when `start` is called and `PluginStrategyLoader.load()` fails.
- No upfront validation of `start_time`/`end_time` for backtest mode (e.g., end before start,
  missing entirely for backtest). The error surfaces later at start time.

#### `POST /api/v1/runs/{id}/start` — Start Run

⚠️ **Backend works, but no UI trigger.**

Flow:

1. Validates run is PENDING (409 Conflict otherwise)
2. Sets status = RUNNING, emits `run.Started`
3. Dispatches to `_start_backtest()` or `_start_live()` based on mode
4. Backtest: loads strategy → creates GretaService + StrategyRunner + BacktestClock → runs to completion
5. Live/Paper: loads strategy → creates StrategyRunner + RealtimeClock → clock runs in background

Failure modes:

- Invalid `strategy_id` → `StrategyNotFoundError` → 404 or 500 depending on where it's caught
- Backtest with missing `start_time`/`end_time` → error during clock creation
- Backtest with empty `bars` table → strategy gets empty windows, likely no trades, runs to completion with no activity

#### `POST /api/v1/runs/{id}/stop` — Stop Run

✅ **Working.** Cleanup is ordered: stop clock → drain tasks → cleanup runner → cleanup greta → remove context.

#### `GET /api/v1/runs` — List Runs

✅ **Working.** Returns paginated list from in-memory `_runs` dict. Supports `status` filter.

Note: Pagination is in-memory (fetch all, slice). Fine for expected scale.

#### `GET /api/v1/runs/{id}` — Get Run

✅ **Working.** In-memory lookup.

### 3.3 Orders

#### `POST /api/v1/orders` — Create Order

⚠️ **Partially working.** Returns 503 if VedaService is not initialized (no Alpaca credentials or DB).
When Veda is available, creates order through `VedaService.place_order()` which submits to exchange adapter.

#### `GET /api/v1/orders` — List Orders

✅ **Working.** Delegates to VedaService (if available) or MockOrderService. Supports `run_id` and `status` filters.

#### `GET /api/v1/orders/{id}` — Get Order

✅ **Working.** VedaService checks in-memory OrderManager first, falls back to repository.

#### `DELETE /api/v1/orders/{id}` — Cancel Order

⚠️ **Backend works, no UI trigger.** Calls `VedaService.cancel_order()` → adapter → exchange.

#### `POST /api/v1/orders/{id}/sync` — Sync Order

⚠️ **Backend works, no UI trigger.** Calls `VedaService.sync_order()` → fetches current status from
exchange adapter → updates local state + DB. This is the new feature from this PR.

### 3.4 SSE (`GET /api/v1/events/stream`)

✅ **Working.** Server-Sent Events stream. Supports optional `run_id` query param for filtering.
Uses SSEBroadcaster subscribed to EventLog.

### 3.5 Candles (`GET /api/v1/candles`)

⚠️ **Returns mock data.** Hard-coded OHLCV from `MockMarketDataService`. Not connected to
real exchange data or the `bars` table. Params: `symbol`, `timeframe`, `limit`.

---

## 4. Strategy System (Marvin) — Audit

### 4.1 Strategy Discovery

✅ **Working.** `PluginStrategyLoader` scans `src/marvin/strategies/` using AST (no import needed).
Each strategy file must have a `STRATEGY_META` dict at module level.

Currently discovered strategies:

| ID              | Class            | File                 | Description                                                |
| --------------- | ---------------- | -------------------- | ---------------------------------------------------------- |
| `sample`        | `SampleStrategy` | `sample_strategy.py` | Mean-reversion: buy when price < 99% avg, sell when > 101% |
| `sma-crossover` | `SMAStrategy`    | `sma_strategy.py`    | SMA crossover: buy on golden cross, sell on death cross    |

### 4.2 Strategy Interface (`BaseStrategy`)

```python
class BaseStrategy(ABC):
    async def initialize(self, symbols: list[str]) -> None
    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]   # Called every clock tick
    async def on_data(self, data: Any) -> list[StrategyAction]         # Called when data arrives
```

`StrategyAction` types:

- `FETCH_WINDOW` — request N historical bars for a symbol
- `PLACE_ORDER` — request an order (side, qty, type, prices)

### 4.3 Strategy Execution Bridge (`StrategyRunner`)

Per-run instance. Translates between strategy actions and the event system:

- `strategy.on_tick()` returns `[FetchWindow(...)]` → emits `strategy.FetchWindow` event
- Receives `data.WindowReady` → deserializes bars → calls `strategy.on_data()` → emits `strategy.PlaceRequest`

**Important**: Bar deserialization in `on_data_ready()` converts raw dicts from event payload
into `Bar` dataclass objects. This was fixed in M11 (previously passed raw dicts, causing
attribute access failures in strategies that expected `bar.close` instead of `bar["close"]`).

### 4.4 Gaps

| Gap                                        | Impact                                                                                                                     |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **No REST endpoint for strategy list**     | Frontend can't show a dropdown of available strategies. `list_available()` exists on the loader but isn't exposed via API. |
| **No strategy parameter schema endpoint**  | Frontend can't render a dynamic config form for strategy-specific parameters (e.g., SMA fast/slow periods).                |
| **No strategy validation on run creation** | `POST /runs` accepts any `strategy_id`. Error only at start time.                                                          |
| **Only 2 strategies**                      | Limited for real testing. Both are simple single-indicator strategies.                                                     |
| **No custom strategy upload**              | Must place `.py` files in `src/marvin/strategies/` and restart. No runtime addition.                                       |

---

## 5. Backtest Engine (Greta) — Audit

### 5.1 Architecture

Each backtest run creates its own `GretaService` instance with:

- Isolated positions, pending orders, fills, cash, equity curve
- Initial cash: $100,000 (hardcoded default)
- Bar data preloaded from `bars` table into memory cache at `initialize()`

### 5.2 Fill Simulation (`DefaultFillSimulator`)

| Order Type | Fill Logic                                                   |
| ---------- | ------------------------------------------------------------ |
| Market     | Fill at bar open price (configurable: open/close/vwap/worst) |
| Limit Buy  | Fills if `bar.low <= limit_price`, at limit_price            |
| Limit Sell | Fills if `bar.high >= limit_price`, at limit_price           |
| Stop Buy   | Triggers if `bar.high >= stop_price`, fills at stop_price    |
| Stop Sell  | Triggers if `bar.low <= stop_price`, fills at stop_price     |

Cost model:

- **Slippage**: `price × (slippage_bps / 10000)`, always unfavorable direction
- **Commission**: `notional × (commission_bps / 10000)`, with `min_commission` floor

### 5.3 Position Tracking

Supports: new position, add to position (weighted avg cost), partial close,
full close, reversal (long→short or short→long). Cash adjusted on every fill.

### 5.4 Results (`BacktestResult`)

Computed at run completion:

- Total return, final equity, equity curve (list of timestamped values)
- Sharpe ratio, Sortino ratio (non-annualized)
- Max drawdown
- Win rate, profit factor
- FIFO lot matching for round-trip trade P&L

### 5.5 Gaps

| Gap                                   | Impact                                                                                                                                                      | Severity   |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| **`bars` table is empty**             | Backtest has zero data to work with. Will run but produce zero trades.                                                                                      | 🔴 Blocker |
| **No data ingestion pipeline**        | No script/command/API to download historical bars from Alpaca (or any source) into the `bars` table.                                                        | 🔴 Blocker |
| **No API to retrieve BacktestResult** | `greta.get_result()` computes stats, but no endpoint returns them. Results are computed and discarded (only the terminal `run.Completed` event is emitted). | 🟡 Medium  |
| **No equity curve visualization**     | Even if results were retrievable, frontend has no chart component.                                                                                          | 🟡 Medium  |
| **No configurable initial cash**      | Hardcoded $100,000. No UI or API to change it.                                                                                                              | 🟠 Low     |
| **Stop-limit orders not supported**   | `FillSimulator` handles market, limit, stop — but not stop-limit.                                                                                           | 🟠 Low     |

---

## 6. Live/Paper Trading (Veda) — Audit

### 6.1 Exchange Adapter

**AlpacaAdapter** connects to Alpaca's API:

- `connect()`: Creates `TradingClient`, `StockHistoricalDataClient`, `CryptoHistoricalDataClient`, verifies account ACTIVE
- `submit_order()`: Maps to Alpaca SDK request types, submits via `asyncio.to_thread`
- `cancel_order()`: Cancel by exchange order ID
- `get_order()`: Fetch current order status from exchange

**MockExchangeAdapter** for testing:

- Market orders fill immediately at mock price (BTC/USD=$42000, ETH/USD=$2500)
- Limit orders stay ACCEPTED
- Configurable rejections

### 6.2 VedaService

Singleton service wired at app startup (if Alpaca credentials configured):

- `place_order(intent)` → idempotency check → submit to adapter → persist → emit event
- `sync_order(client_order_id)` → fetch from exchange → update local + DB (NEW in this PR)
- `cancel_order(client_order_id)` → cancel via adapter → persist → emit event
- `list_orders(run_id?, status?)` → from repository or OrderManager
- `handle_place_order(envelope)` → event handler for `live.PlaceOrder`

### 6.3 Order Lifecycle (Live/Paper)

```
Strategy → strategy.PlaceRequest
        → DomainRouter → live.PlaceOrder
        → VedaService.handle_place_order()
        → OrderManager.submit_order()
        → AlpacaAdapter.submit_order()
        → Alpaca Exchange API
        → OrderSubmitResult returned
        → Persist to veda_orders table
        → Emit orders.Created / orders.Rejected
        → (Later) sync_order() to refresh status from exchange
```

### 6.4 Gaps

| Gap                                    | Impact                                                                                                                                                                                                                                                                                | Severity    |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| **MarketDataService is mock**          | `live.FetchWindow` events are handled by `MockMarketDataService` which returns hardcoded fake candles. Strategies running in paper/live mode receive fabricated data, not real market prices. Orders submitted to Alpaca are real, but the strategy decisions are based on fake data. | 🔴 Critical |
| **No real-time market data streaming** | No WebSocket connection to Alpaca for real-time quotes/bars. The RealtimeClock ticks at bar boundaries, but the data fed to strategies is mock.                                                                                                                                       | 🔴 Critical |
| **No fill confirmation loop**          | After submitting to Alpaca, there's no automatic polling or WebSocket listener to detect when orders are filled. Must manually call `sync_order()`.                                                                                                                                   | 🟡 Medium   |
| **No position tracking from exchange** | VedaService has a `PositionTracker` but it's not synced with Alpaca's actual positions. No `GET /positions` endpoint.                                                                                                                                                                 | 🟡 Medium   |
| **Alpaca credentials in .env**         | Credentials are configured and non-placeholder (verified). Paper trading should work if an order is manually submitted.                                                                                                                                                               | ✅ OK       |

---

## 7. Event System — Audit

### 7.1 Architecture

Outbox pattern with PostgreSQL LISTEN/NOTIFY:

- `PostgresEventLog`: Same-transaction append to `outbox` table + `pg_notify()`
- `InMemoryEventLog`: For tests and no-DB mode
- `Envelope` (frozen dataclass): id, type, run_id, corr_id, causation_id, trace_id, payload

### 7.2 Event Types

| Namespace    | Events                                                        | Producer                               |
| ------------ | ------------------------------------------------------------- | -------------------------------------- |
| `strategy.*` | FetchWindow, PlaceRequest, DecisionMade                       | StrategyRunner                         |
| `backtest.*` | FetchWindow, PlaceOrder                                       | DomainRouter (routed from strategy.\*) |
| `live.*`     | FetchWindow, PlaceOrder                                       | DomainRouter (routed from strategy.\*) |
| `data.*`     | WindowReady, WindowChunk, WindowComplete                      | Greta / MarketDataService              |
| `orders.*`   | Created, Placed, Filled, PartiallyFilled, Cancelled, Rejected | Greta / Veda                           |
| `run.*`      | Created, Started, Stopped, Completed, Error, Heartbeat        | RunManager                             |
| `clock.Tick` | —                                                             | Clock                                  |

### 7.3 DomainRouter

The key decoupling mechanism. Strategies emit generic `strategy.*` events.
DomainRouter looks up the run's mode and re-emits with the correct domain prefix:

```
strategy.FetchWindow  → backtest.FetchWindow   (mode=backtest)
strategy.FetchWindow  → live.FetchWindow        (mode=live|paper)
strategy.PlaceRequest → backtest.PlaceOrder     (mode=backtest)
strategy.PlaceRequest → live.PlaceOrder         (mode=live|paper)
```

This is why strategies don't need to know whether they're in backtest or live mode.

### 7.4 Status

✅ **Working correctly.** Event-driven architecture is solid. SSE broadcaster
receives events and pushes to frontend. Causation chain (corr_id, causation_id)
is maintained throughout.

---

## 8. Persistence (WallE) — Audit

### 8.1 Database Schema

| Table              | Purpose                                                 | Status              |
| ------------------ | ------------------------------------------------------- | ------------------- |
| `outbox`           | Event sourcing outbox (type, JSONB payload, created_at) | ✅ Working          |
| `consumer_offsets` | At-least-once delivery tracking                         | ✅ Working          |
| `bars`             | Historical OHLCV (unique on symbol+timeframe+timestamp) | ⚠️ Empty            |
| `veda_orders`      | Durable order state (all fields + status)               | ✅ Working (0 rows) |
| `runs`             | Run state for restart recovery                          | ✅ Working (2 rows) |
| `fills`            | Immutable fill audit trail                              | ✅ Working (0 rows) |

### 8.2 Repositories

- `BarRepository`: `save_bars()` (upsert), `get_bars()` (range query), `get_bar_count()`, `get_latest_bar()` — **Singleton** (immutable data)
- `RunRepository`: `save()`, `get()`, `list()` — for crash recovery
- `FillRepository`: `save()`, `list_by_order()` — append-only audit trail
- `OrderRepository` (in Veda): `save()`, `get_by_client_order_id()`, `list()` — mutable order tracking

### 8.3 Recovery

On startup, `RunManager.recover()` loads PENDING and RUNNING runs from `RunRepository`.
Previously-RUNNING runs (from a crash) are moved to ERROR status. PENDING runs are
restored as-is (user can start them again).

---

## 9. Data Pipeline — Audit

### 9.1 Current State

**There is no data pipeline.**

The `bars` table exists. `BarRepository.save_bars()` supports upserting bar data.
But there is no mechanism to populate the table:

- No script to download historical bars from Alpaca
- No CLI command to fetch and store bars
- No scheduled job to periodically pull new bars
- No API endpoint to trigger bar ingestion
- The Alpaca adapter creates `StockHistoricalDataClient` and `CryptoHistoricalDataClient`
  at connect time, but these clients are never used for bar ingestion

### 9.2 Impact

| Scenario       | What Happens                                                                                                                                                                 |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Backtest**   | GretaService preloads bars from empty table → empty cache → strategy receives empty windows → zero trades → run completes with $100,000 unchanged                            |
| **Live/Paper** | `live.FetchWindow` handled by MockMarketDataService → fake data → strategy makes decisions on fake prices → orders submitted with real money on Alpaca based on fake signals |

### 9.3 What Needs to Exist

At minimum, one of:

1. A CLI script: `python -m src.tools.fetch_bars --symbol BTC/USD --timeframe 1h --start 2025-01-01 --end 2026-04-01`
2. An API endpoint: `POST /api/v1/bars/fetch` with symbol/timeframe/range params
3. A management command wired into the Alpaca historical data client

The Alpaca SDK clients are already created in `AlpacaAdapter.connect()`:

```python
self._stock_data_client = StockHistoricalDataClient(api_key, secret_key)
self._crypto_data_client = CryptoHistoricalDataClient(api_key, secret_key)
```

These could be used to fetch real historical bars and store them via `BarRepository.save_bars()`.

---

## 10. End-to-End Flow Analysis

### 10.1 Flow: Create and Run a Backtest (Current Reality)

```
1. User opens http://<ip>:13579/runs
2. Clicks "+ New Run"
3. Types strategy: "sma-crossover"
4. Selects Mode: Backtest
5. Types symbols: "BTC/USD"
6. Selects timeframe: 1h
7. ❌ CANNOT enter start_time / end_time (fields not in UI)
8. Clicks "Create" → POST /runs → Run created (PENDING)
9. ❌ CANNOT click "Start" (no Start button in UI)
10. ❌ Even if started via API, bars table is empty → zero trades

To test via curl:
  curl -X POST http://<ip>:18919/api/v1/runs \
    -H "Content-Type: application/json" \
    -d '{"strategy_id":"sma-crossover","mode":"backtest","symbols":["BTC/USD"],"timeframe":"1h","start_time":"2025-01-01T00:00:00Z","end_time":"2025-02-01T00:00:00Z"}'

  curl -X POST http://<ip>:18919/api/v1/runs/<run_id>/start

  → Strategy loads OK
  → BacktestClock ticks from Jan 1 to Feb 1
  → GretaService preloads bars → 0 bars found
  → Strategy requests windows → empty responses
  → No trades generated
  → Run completes with status=COMPLETED, equity unchanged at $100,000
  → No way to see the results (no API endpoint for BacktestResult)
```

### 10.2 Flow: Create and Run Paper Trading (Current Reality)

```
1. User creates run with mode=Paper via UI (or curl)
2. Start via curl: POST /runs/<id>/start
3. RealtimeClock starts ticking at real 1h boundaries
4. On each tick:
   a. Strategy requests FetchWindow
   b. DomainRouter routes to live.FetchWindow
   c. MockMarketDataService returns FAKE bar data
   d. Strategy analyzes FAKE data → maybe emits PlaceOrder
   e. DomainRouter routes to live.PlaceOrder
   f. VedaService submits to Alpaca Paper API
   g. ⚠️ REAL order placed on Alpaca based on FAKE data
5. Order appears in /orders page
6. No automatic fill detection — must call sync_order() manually (no UI for this)
```

### 10.3 Flow: What a Working Backtest Should Look Like

```
1. Historical bars for BTC/USD 1h loaded into bars table (e.g., 1 year of data)
2. User creates backtest run with start_time, end_time, strategy config
3. User clicks Start
4. BacktestClock fast-forwards through every 1h bar
5. Strategy receives real historical data, makes trading decisions
6. GretaService simulates fills with slippage + commission
7. Position tracking, equity curve recorded at each tick
8. Run completes → BacktestResult computed
9. UI shows: equity curve chart, trade list, stats (Sharpe, drawdown, win rate)
10. User can compare across multiple backtests
```

---

## 11. Gap Summary

### 🔴 Blockers (Cannot do meaningful testing without fixing)

| #   | Gap                                | Component                | What's Needed                                                   |
| --- | ---------------------------------- | ------------------------ | --------------------------------------------------------------- |
| B1  | **No Start button**                | Frontend (RunsPage)      | Add Start button for PENDING runs, calling `useStartRun()`      |
| B2  | **No backtest time range inputs**  | Frontend (CreateRunForm) | Add start_time/end_time date pickers, shown when mode=backtest  |
| B3  | **Empty bars table**               | Data Pipeline            | Build a bar ingestion script using Alpaca's historical data API |
| B4  | **Mock market data in live/paper** | Veda / MarketDataService | Replace MockMarketDataService with real Alpaca data fetching    |

### 🟡 Important (System works but key features missing)

| #   | Gap                        | Component                   | What's Needed                                                      |
| --- | -------------------------- | --------------------------- | ------------------------------------------------------------------ |
| I1  | No Order Sync UI           | Frontend (OrdersPage)       | Add "Sync" button per order row, calling POST /orders/{id}/sync    |
| I2  | No Cancel Order UI         | Frontend (OrdersPage)       | Add "Cancel" button for active orders                              |
| I3  | No strategy list API       | Backend (routes)            | `GET /api/v1/strategies` → list available strategies with metadata |
| I4  | Strategy selector dropdown | Frontend (CreateRunForm)    | Fetch strategy list, show dropdown instead of free-text            |
| I5  | No backtest results API    | Backend (routes/RunManager) | Store BacktestResult, expose via `GET /runs/{id}/result`           |
| I6  | No backtest results UI     | Frontend                    | Equity curve chart, stats table, trade list                        |
| I7  | No fill confirmation loop  | Veda                        | Polling or WebSocket listener for fill events from exchange        |
| I8  | Strategy config UI         | Frontend (CreateRunForm)    | Dynamic form based on strategy's config schema                     |

### 🟠 Nice-to-Have (Polish & UX)

| #   | Gap                                       | Component        |
| --- | ----------------------------------------- | ---------------- |
| N1  | Run detail page with orders/events/equity | Frontend         |
| N2  | Settings page (credentials, DB status)    | Frontend         |
| N3  | Event log viewer                          | Frontend         |
| N4  | Candlestick chart component               | Frontend         |
| N5  | Strategy validation on run creation       | Backend          |
| N6  | Configurable initial cash for backtest    | Backend/Frontend |
| N7  | Position tracking from exchange           | Veda             |

---

## 12. Discussion Topics

### Topic 1: Priority Order for Blockers

What should we fix first? Suggested order:

1. **B1 (Start button)** — Smallest change, unlocks testing everything else
2. **B3 (Bar data ingestion)** — Needed for any meaningful backtest
3. **B2 (Time range inputs)** — Needed to configure backtests from UI
4. **B4 (Real market data)** — Most complex, needed for live/paper to be meaningful

### Topic 2: Bar Data Strategy

How should we get historical bar data?

- Option A: One-time CLI script using Alpaca historical API
- Option B: API endpoint that triggers fetching (callable from UI)
- Option C: Scheduled background job that continuously pulls new bars
- Option D: All of the above (script for backfill, scheduled for ongoing)

What symbols and timeframes to support initially?

### Topic 3: Live/Paper Market Data

The MockMarketDataService is the biggest architectural gap for live/paper mode.
Options:

- Option A: Use Alpaca's REST historical bars API on each `live.FetchWindow` request
- Option B: WebSocket streaming from Alpaca into the bars table, then query locally
- Option C: Direct REST call per tick (simplest, some latency)

### Topic 4: Backtest Results Persistence

Currently `BacktestResult` is computed in memory and discarded.

- Should we store it in DB? (new table: `backtest_results`)
- Should we compute it on-the-fly from fills + equity snapshots?
- What stats does the UI need to display?

### Topic 5: Order Sync vs Streaming

Current approach: manual `sync_order()` call to check exchange status.
Better approach: Alpaca WebSocket for real-time order updates.

- Is manual sync sufficient for now?
- Should we build the WebSocket listener as a priority?

### Topic 6: Scope of This Branch

This branch (`prod-test`) currently has:

- Order sync backend endpoint (working)
- CI/CD improvements (working)
- E2E test reliability fixes (working)

But the system itself has fundamental gaps (no Start button, no data, mock market data)
that prevent meaningful manual testing. How much should we fix before merging?

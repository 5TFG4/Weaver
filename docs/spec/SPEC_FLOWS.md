# Weaver Data Flow & Event Specification

> **Document Type**: End-to-end Data Flow & Event Interaction Specification
> **Covers**: Complete execution flows for each run mode, event routing mechanisms, order lifecycle, data pipelines
> **Related Documents**: [System Overview](SYSTEM_SPEC.md) · [Backend Specification](SPEC_BACKEND.md) · [Frontend Specification](SPEC_FRONTEND.md)

---

## Table of Contents

1. [Core Event Routing Mechanism](#1-core-event-routing-mechanism)
2. [Backtest Mode Complete Flow](#2-backtest-mode-complete-flow)
3. [Paper/Live Trading Mode Complete Flow](#3-paperlive-trading-mode-complete-flow)
4. [Order Lifecycle](#4-order-lifecycle)
5. [Data Pipeline](#5-data-pipeline)
6. [SSE Real-time Push Flow](#6-sse-real-time-push-flow)
7. [Crash Recovery Flow](#7-crash-recovery-flow)
8. [Concurrency & Isolation](#8-concurrency--isolation)

---

## 1. Core Event Routing Mechanism

### 1.1 Why DomainRouter Is Needed

Weaver's core design goal is **one strategy codebase running in three modes**. A strategy should not know whether it is running in backtest or live trading.

To achieve this goal, the system introduces the **DomainRouter**:

```
Strategy emits generic events → DomainRouter routes based on Run mode → Routes to the correct domain

strategy.FetchWindow ──→ DomainRouter ──→ backtest.FetchWindow  (backtest)
                                     └──→ live.FetchWindow      (paper/live)

strategy.PlaceRequest ──→ DomainRouter ──→ backtest.PlaceOrder  (backtest)
                                      └──→ live.PlaceOrder      (paper/live)
```

### 1.2 Routing Decision Logic

```python
async def route(event: Envelope):
    # 1. Only process events in the strategy.* namespace
    if not event.type.startswith("strategy."):
        return

    # 2. Extract run_id, look up the Run's mode
    run = run_manager.get(event.run_id)
    mode = run.mode  # backtest / paper / live

    # 3. Determine target domain
    if mode == "backtest":
        domain = "backtest"
    else:  # paper or live
        domain = "live"

    # 4. Map event type
    #    strategy.FetchWindow → FetchWindow
    #    strategy.PlaceRequest → PlaceOrder
    action = EVENT_TYPE_MAPPING[event.type]

    # 5. Create new event, preserving causal chain
    routed = Envelope(
        type=f"{domain}.{action}",
        run_id=event.run_id,
        corr_id=event.corr_id,
        causation_id=event.id,    # Points to the original strategy event
        payload=event.payload,
    )

    # 6. Append to event log
    event_log.append(routed)
```

### 1.3 Event Subscription Wiring (Established at Application Startup)

```
┌──────────────────────────────────────────────────────────┐
│                     EventLog (Event Bus)                   │
│                                                            │
│  Subscriptions:                                            │
│                                                            │
│  strategy.* ────→ DomainRouter.route()                     │
│                     → Emits backtest.* or live.*            │
│                                                            │
│  backtest.FetchWindow ──→ GretaService.handle()            │
│  backtest.PlaceOrder ───→ GretaService.handle()            │
│                                                            │
│  live.FetchWindow ──→ MarketDataService.handle()           │
│  (Fetches data from the designated exchange's historical/  │
│   real-time API)                                           │
│                                                            │
│  live.PlaceOrder ───→ VedaService.handle_place_order()     │
│  (Routes to the exchange adapter specified by strategy)    │
│                                                            │
│  data.WindowReady ──→ StrategyRunner.on_data_ready()       │
│                                                            │
│  All events ──→ SSEBroadcaster.publish()                   │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Backtest Mode Complete Flow

### 2.1 Overview Sequence

```
User                  Frontend            Backend (RunManager)      Marvin              Greta              Database
 │                    │                    │                       │                    │                    │
 │ Create backtest run│                    │                       │                    │                    │
 ├─── POST /runs ────→│                    │                       │                    │                    │
 │                    ├─── createRun() ───→│                       │                    │                    │
 │                    │                    ├─ Generate UUID         │                    │                    │
 │                    │                    ├─ Status=PENDING        │                    │                    │
 │                    │                    ├─ Emit run.Created ─────────────────────────────────────→ outbox │
 │                    │◁── Run (PENDING) ──┤                       │                    │                    │
 │                    │                    │                       │                    │                    │
 │ Start run          │                    │                       │                    │                    │
 ├── POST /runs/start→│                    │                       │                    │                    │
 │                    ├─── startRun() ────→│                       │                    │                    │
 │                    │                    ├─ Status=RUNNING        │                    │                    │
 │                    │                    ├─ Emit run.Started      │                    │                    │
 │                    │                    │                       │                    │                    │
 │                    │                    ├─ Load strategy ────────→│ PluginStrategyLoader│                    │
 │                    │                    │                       │ load("sma-crossover")                    │
 │                    │                    │                       │◁─ SMAStrategy instance│                    │
 │                    │                    │                       │                    │                    │
 │                    │                    ├─ Create GretaService ───────────────────────→│                    │
 │                    │                    │                       │                    ├─ Preload bars ──→│
 │                    │                    │                       │                    │  (Cache first,   │
 │                    │                    │                       │                    │   fetch from     │
 │                    │                    │                       │                    │   exchange on    │
 │                    │                    │                       │                    │   cache miss)    │
 │                    │                    │                       │                    │◁── Bar data ─────┤
 │                    │                    │                       │                    ├─ Subscribe events│
 │                    │                    │                       │                    │                │
 │                    │                    ├─ Create StrategyRunner ─→│                    │                │
 │                    │                    │                       ├─ Initialize strategy│                │
 │                    │                    │                       ├─ Subscribe data.WindowReady           │
 │                    │                    │                       │                    │                │
 │                    │                    ├─ Create BacktestClock   │                    │                │
 │                    │                    ├─ Register tick callbacks:│                    │                │
 │                    │                    │   1. greta.advance_to()│                    │                │
 │                    │                    │   2. runner.on_tick()  │                    │                │
 │                    │                    │                       │                    │                │
 │                    │                    ├─ clock.start() ───────────→ tick loop starts │                │
```

### 2.2 Single Bar Execution Loop

This is the core loop repeated for each bar during backtesting:

```
BacktestClock                 GretaService              StrategyRunner            Strategy            EventLog
    │                             │                          │                      │                    │
    ├─ emit tick(ts=2025-01-01)   │                          │                      │                    │
    │                             │                          │                      │                    │
    │  [Callback1] advance_to(ts)→│                          │                      │                    │
    │                             ├─ Update current bar      │                      │                    │
    │                             ├─ Check if pending orders fill  │                │                    │
    │                             ├─ Mark-to-market position value │                │                    │
    │                             ├─ Record equity curve point     │                │                    │
    │                             │                          │                      │                    │
    │  [Callback2] on_tick(tick) ──────────────────────────→│                      │                    │
    │                             │                          ├─ strategy.on_tick(tick)→│                    │
    │                             │                          │                      ├─ Analyze tick signal│
    │                             │                          │◁─ [FETCH_WINDOW] ────┤                    │
    │                             │                          │                      │                    │
    │                             │                          ├─ Emit strategy.FetchWindow ──────────────→│
    │                             │                          │                      │                    │
    │                             │                          │                      │    DomainRouter     │
    │                             │                          │                      │    Routes to:       │
    │                             │                          │                      │  backtest.FetchWindow│
    │                             │                          │                      │                    │
    │                             │◁────────── backtest.FetchWindow ────────────────────────────────────┤
    │                             │                          │                      │                    │
    │                             ├─ Fetch bar window from cache (fetch on demand on cache miss)
    │                             ├─ Emit data.WindowReady ──────────────────────────────────────────→│
    │                             │                          │                      │                    │
    │                             │                          │◁─── data.WindowReady ─────────────────────┤
    │                             │                          │                      │                    │
    │                             │                          ├─ dict → Bar deserialize│                    │
    │                             │                          ├─ strategy.on_data(bars)→│                    │
    │                             │                          │                      ├─ Analyze bar data   │
    │                             │                          │                      ├─ Decide whether to  │
    │                             │                          │                      │  place an order      │
    │                             │                          │◁─ [PLACE_ORDER] ─────┤                    │
    │                             │                          │                      │                    │
    │                             │                          ├─ Emit strategy.PlaceRequest ─────────────→│
    │                             │                          │                      │                    │
    │                             │                          │                      │  DomainRouter routes:│
    │                             │                          │                      │  backtest.PlaceOrder │
    │                             │                          │                      │                    │
    │                             │◁────────── backtest.PlaceOrder ─────────────────────────────────────┤
    │                             │                          │                      │                    │
    │                             ├─ Create simulated order   │                      │                    │
    │                             ├─ Emit orders.Created ────────────────────────────────────────────→│
    │                             │                          │                      │                    │
    │  (Next bar)                  │                          │                      │                    │
    ├─ emit tick(ts=2025-01-01 01:00)                        │                      │                    │
    │                             │                          │                      │                    │
    │  [Callback1] advance_to(ts)→│                          │                      │                    │
    │                             ├─ Check pending orders from│                      │                    │
    │                             │  previous tick            │                      │                    │
    │                             │  If conditions match → simulate fill             │                    │
    │                             ├─ Emit orders.Filled ─────────────────────────────────────────────→│
    │                             ├─ Update positions and funds│                      │                    │
    ...                           ...                        ...                    ...
```

### 2.3 Backtest Completion

```
BacktestClock (all bars traversed)       RunManager                    GretaService
    │                                   │                             │
    ├─ tick loop ends                    │                             │
    ├─ clock.wait() returns              │                             │
    │                                   │                             │
    │                                   ├─ Drain pending tasks        │
    │                                   ├─ Check clock.error          │
    │                                   │  (No exception → COMPLETED)  │
    │                                   │  (Exception → ERROR)         │
    │                                   │                             │
    │                                   ├─ Set status = COMPLETED      │
    │                                   ├─ Emit run.Completed          │
    │                                   │                             │
    │                                   ├─ _cleanup_run_context()     │
    │                                   │  ├─ clock.stop()             │
    │                                   │  ├─ Drain pending_tasks      │
    │                                   │  ├─ runner.cleanup()  (unsubscribe)
    │                                   │  ├─ greta.cleanup()   ─────→│
    │                                   │  │                          ├─ Unsubscribe
    │                                   │  │                          ├─ Return BacktestResult
    │                                   │  └─ Remove RunContext        │
```

**BacktestResult contains**:

- Equity curve (time series)
- All fill records
- Statistical metrics (Sharpe, drawdown, win rate, etc.)
- ⚠️ Currently not persisted after computation, and no API endpoint to query it

---

## 3. Paper/Live Trading Mode Complete Flow

### 3.1 Overview Sequence

Key differences from backtest mode:

- The clock is **RealtimeClock** (ticks at real time, **never stops automatically** — strategy runs continuously until user stops or an error occurs)
- Data source uses **MarketDataService** (should connect to exchange historical/real-time API; ⚠️ currently Mock)
- Orders are submitted via **VedaService → Exchange Adapter** (routes to the exchange specified in strategy config)
- `_start_live()` is **asynchronous** — the clock runs in the background, API returns immediately

```
User           Frontend        RunManager           StrategyRunner        VedaService          Exchange
 │              │                │                       │                    │                  │
 │ Start paper  │                │                       │                    │                  │
 │ trading run  │                │                       │                    │                  │
 ├── POST start→│                │                       │                    │                  │
 │              ├── startRun() ─→│                       │                    │                  │
 │              │                ├─ Status=RUNNING        │                    │                  │
 │              │                ├─ Load strategy         │                    │                  │
 │              │                ├─ Create StrategyRunner→│                    │                  │
 │              │                ├─ Create RealtimeClock  │                    │                  │
 │              │                ├─ Register tick callbacks│                    │                  │
 │              │                ├─ clock.start() ───→ Runs in background     │                  │
 │              │◁── Run ────────┤ (API returns immediately)│                    │                  │
 │              │                │                       │                    │                  │
 │              │                │  ... Wait until next bar boundary ...      │                  │
 │              │                │                       │                    │                  │
 │              │            tick│(every minute/hour on the dot)              │                  │
 │              │                │                       │                    │                  │
 │              │                ├─ on_tick(tick) ────────→│                    │                  │
 │              │                │                       ├─ strategy.on_tick()  │                  │
 │              │                │                       │◁── [FETCH_WINDOW]    │                  │
 │              │                │                       ├─ Emit strategy.FetchWindow             │
 │              │                │                       │                    │                  │
 │              │                │                       │  DomainRouter → live.FetchWindow       │
 │              │                │                       │                    │                  │
 │              │                │               MarketDataService            │                  │
 │              │                │              ◁── live.FetchWindow          │                  │
 │              │                │              ⚠️ Returns MOCK data (should fetch from exchange API)
 │              │                │              Emit data.WindowReady          │                  │
 │              │                │                       │                    │                  │
 │              │                │                       │◁── data.WindowReady │                  │
 │              │                │                       ├─ strategy.on_data()  │                  │
 │              │                │                       │◁── [PLACE_ORDER]     │                  │
 │              │                │                       ├─ Emit strategy.PlaceRequest            │
 │              │                │                       │                    │                  │
 │              │                │                       │  DomainRouter → live.PlaceOrder        │
 │              │                │                       │                    │                  │
 │              │                │                       │                    │◁── live.PlaceOrder│
 │              │                │                       │                    ├── place_order()  │
 │              │                │                       │                    │                  │
 │              │                │                       │               OrderManager             │
 │              │                │                       │                    ├── submit_order() │
 │              │                │                       │                    │                  │
 │              │                │                       │              ExchangeAdapter           │
 │              │                │                       │   (Routes to the exchange specified    │
 │              │                │                       │    in strategy config)                 │
 │              │                │                       │                    ├── submit_order()─→│
 │              │                │                       │                    │                  ├─ Match
 │              │                │                       │                    │◁── OrderResult ──┤
 │              │                │                       │                    │                  │
 │              │                │                       │                    ├── Persist to DB   │
 │              │                │                       │                    ├── Emit orders.Created
 │              │                │                       │                    │                  │
 │              │                │        ... Wait for next bar ...          │                  │
```

### 3.2 Difference Between Live and Paper Trading

The code path is exactly the same; the only difference is during initialization:

```python
# ExchangeAdapter selects credentials based on mode
# Using Alpaca as an example:
mode == PAPER → Returns paper_api_key, paper_api_secret, paper_base_url
mode == LIVE  → Returns live_api_key, live_api_secret, live_base_url
```

Paper mode sends to the exchange's simulated environment (no real money involved).
Live mode sends to the exchange's production environment (**real money involved**).

### 3.3 ⚠️ Critical Defects in Current Implementation

| Issue                          | Description                                                                                                                    | Severity     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| MockMarketDataService          | `live.FetchWindow` events are handled by a Mock service, returning fake data (should fetch real market data from exchange API) | 🔴 Critical  |
| No automatic fill confirmation | After placing an order, fills are not automatically detected; must manually call `sync_order()`                                | 🟡 Important |
| Strategy decides on fake data  | Mock returns random bars → strategy analyzes fake data → places **real** orders (to real exchange)                             | 🔴 Critical  |

---

## 4. Order Lifecycle

### 4.1 Order Flow in Backtest Mode

```
Strategy emits PLACE_ORDER
  → StrategyRunner emits strategy.PlaceRequest
    → DomainRouter → backtest.PlaceOrder
      → GretaService receives
        → Creates simulated order, emits orders.Created
        → In the next advance_to(), checks fill conditions:
          ├─ Market order: fills immediately (at current bar's open price)
          ├─ Limit buy: bar low ≤ limit price → fills
          ├─ Limit sell: bar high ≥ limit price → fills
          ├─ Stop buy: bar high ≥ stop price → triggers
          └─ Stop sell: bar low ≤ stop price → triggers
        → If filled:
          ├─ Calculate fill price (with slippage)
          ├─ Calculate commission
          ├─ Update positions
          ├─ Adjust funds
          ├─ Emit orders.Filled
        → If not filled: pending order remains, waiting for subsequent bars
```

### 4.2 Order Flow in Paper/Live Trading Mode

```
Strategy emits PLACE_ORDER
  → StrategyRunner emits strategy.PlaceRequest
    → DomainRouter → live.PlaceOrder
      → VedaService.handle_place_order()
        → Create OrderIntent
        → OrderManager.submit_order()
          → Idempotency check (client_order_id)
          → ExchangeAdapter.submit_order() (routes to exchange specified in strategy config)
            → Submit order via exchange API
            → Returns OrderSubmitResult (including exchange_order_id)
          → Update local OrderState (status: SUBMITTED)
        → OrderRepository.save() (persist to database)
        → Emit orders.Created

      Later (manual sync):
        → POST /orders/{id}/sync
          → VedaService.sync_order()
            → ExchangeAdapter.get_order()
              → Query latest status from exchange
            → If status changed:
              ├─ Update local OrderState
              ├─ Persist
              └─ Emit corresponding event (orders.Filled / orders.Cancelled, etc.)
```

### 4.3 Order State Transition Diagram

```
                     ┌──────────────────────────────────────────────┐
                     │                                              │
                     ▼                                              │
PENDING ──→ SUBMITTING ──→ SUBMITTED ──→ ACCEPTED ──→ FILLED       │
                                           │                        │
                                           ├──→ PARTIALLY_FILLED ──┘
                                           │        │
                                           │        └──→ FILLED
                                           │
                                           ├──→ CANCELLED
                                           │
                                           ├──→ REJECTED
                                           │
                                           └──→ EXPIRED
```

| Status             | Meaning                          | Can transition to                            |
| ------------------ | -------------------------------- | -------------------------------------------- |
| `PENDING`          | Created, awaiting submission     | SUBMITTING                                   |
| `SUBMITTING`       | Being submitted to exchange      | SUBMITTED, REJECTED                          |
| `SUBMITTED`        | Submitted, awaiting confirmation | ACCEPTED, REJECTED                           |
| `ACCEPTED`         | Accepted by exchange             | FILLED, PARTIALLY_FILLED, CANCELLED, EXPIRED |
| `PARTIALLY_FILLED` | Partially filled                 | FILLED, CANCELLED                            |
| `FILLED`           | Fully filled (terminal state)    | —                                            |
| `CANCELLED`        | Cancelled (terminal state)       | —                                            |
| `REJECTED`         | Rejected (terminal state)        | —                                            |
| `EXPIRED`          | Expired (terminal state)         | —                                            |

### 4.4 Idempotency Mechanism

Each order has a `client_order_id` (a unique identifier generated by the client).

- OrderManager maintains a `client_order_id → OrderState` mapping
- Duplicate `client_order_id` will not be resubmitted to the exchange
- Returns the existing OrderState

This ensures: network retries will not cause duplicate order submissions.

---

## 5. Data Pipeline

### 5.1 Backtest Data Flow

```
Exchange Historical API / Cached Data  Database                GretaService            Strategy
      │                      │                       │                      │
      │                      │ bars table (cache)     │                      │
      │                      │ ┌─────────────────┐   │                      │
      │                      │ │symbol│tf│ts│OHLCV│   │                      │
      │                      │ └─────────────────┘   │                      │
      │                      │                       │                      │
      │     Preload at init  │                        │                      │
      │                      │◁── get_bars(range) ───┤                      │
      │  (Cache hit)          │──→ bars[] ────────────→│ In-memory cache     │
      │                      │                       │                      │
      │  (On cache miss)      │                       │                      │
      │◁─── fetch_bars() ────┼───────────────────────┤                      │
      │──→ bars[] ──────────→│ save_bars(upsert) ───→│ In-memory cache     │
      │                      │                       │                      │
      │                                              │  Strategy requests   │
      │                                              │  window              │
      │                              backtest.FetchWindow ◁─────────────────┤
      │                                              │                      │
      │                                              ├─ Read from cache     │
      │                                              ├─ Emit data.WindowReady│
      │                                                        │            │
      │                                              ◁─────────┘            │
      │                                              │                      │
      │                                              │   Bar[] ────────────→│
```

### 5.2 Paper/Live Trading Data Flow (Intended Design vs Current Implementation)

#### Intended Design

```
Exchange Historical/Real-time API     MarketDataService              Strategy
      │                              │                           │
      │                              │◁── live.FetchWindow ──────┤
      │◁── get_bars(symbol,tf,n) ────┤  (Routes to exchange      │
      │                              │   specified by strategy)   │
      │──→ bars[] ──────────────────→│                           │
      │                              ├─ Emit data.WindowReady ──→│
      │                              │                           ├─ Analyze real data
      │                              │                           ├─ Make trading decisions
```

#### ⚠️ Current Implementation

```
MockMarketDataService (hardcoded fake data)  Strategy
      │                                    │
      │◁── live.FetchWindow ───────────────┤
      ├─ Generate random bars               │
      ├─ Emit data.WindowReady ───────────→│
      │                                    ├─ Analyze **fake** data
      │                                    ├─ Make trading decisions
      │                                    ├─ Place **real** orders based on fake data ←── The problem
```

### 5.3 Data Fetching Mechanism

The `bars` table serves as a cache layer, populated on demand in backtest mode.

**Interfaces provided by BarRepository**:

```python
# Bulk write (Upsert semantics, updates when same symbol+timeframe+timestamp)
await bar_repo.save_bars(bars: list[Bar])

# Range query
bars = await bar_repo.get_bars(symbol, timeframe, start, end)

# Count
count = await bar_repo.get_bar_count(symbol, timeframe)

# Latest bar
latest = await bar_repo.get_latest_bar(symbol, timeframe)
```

**Data interface provided by ExchangeAdapter**:

```python
# All exchange adapters implement get_bars()
bars = await adapter.get_bars(symbol, timeframe, start, end, limit)
```

**Data fetching strategy**:

| Scenario             | Behavior                                                                                 |
| -------------------- | ---------------------------------------------------------------------------------------- |
| Backtest: cache hit  | Read directly from `bars` table, zero latency                                            |
| Backtest: cache miss | Fetch via exchange adapter → write to `bars` table → return data                         |
| Live/Paper           | Fetch in real-time via exchange adapter each time (no caching, to ensure data freshness) |

**Additional data tools** (optional):

| Approach     | Description                                                                     | Priority |
| ------------ | ------------------------------------------------------------------------------- | -------- |
| CLI script   | `python -m src.tools.fetch_bars --symbol BTC/USD --tf 1h --start ... --end ...` | Medium   |
| API endpoint | `POST /api/v1/bars/fetch` to trigger preloading                                 | Low      |

---

## 6. SSE Real-time Push Flow

### 6.1 Complete Chain from Event Generation to Frontend Display

```
Business operation (e.g., order filled successfully)
  │
  ├─ EventLog.append(Envelope)          ← Event write
  │   ├─ Persist to outbox table
  │   └─ pg_notify() notifies subscribers
  │
  ├─ SSEBroadcaster (subscribed to EventLog) ← Broadcast
  │   ├─ Receives event
  │   ├─ Formats as ServerSentEvent
  │   └─ Pushes to all connected client queues
  │
  ├─ SSE connection transport           ← Network
  │   └─ event: orders.Filled
  │      data: {"id":"...","type":"orders.Filled","payload":{...}}
  │
  ├─ useSSE Hook (frontend)            ← Receive
  │   ├─ EventSource.onmessage
  │   ├─ Parse event type
  │   ├─ Match handling rules
  │   │
  │   ├─ invalidateQueries(["orders"])  ← Cache invalidation
  │   └─ addNotification("success", "Order filled")  ← Notification
  │
  ├─ React Query                        ← Auto re-fetch
  │   └─ Automatically re-requests GET /orders
  │
  └─ UI update                          ← Render
      ├─ Order table auto-refreshes
      └─ Toast notification appears
```

### 6.2 SSE Filtering Mechanism

When the frontend connects to SSE with a `run_id` parameter:

```python
GET /api/v1/events/stream?run_id=abc-123

# Server-side filtering logic:
def _should_include_event(event, run_id):
    if run_id is None:
        return True  # No filtering

    try:
        data = json.loads(event.data)
        event_run_id = data.get("payload", {}).get("run_id")

        if event_run_id is None:
            return True  # System events always pass through

        return event_run_id == run_id  # Only pass matching events
    except:
        return True  # Parse failures also pass through (don't discard)
```

---

## 7. Crash Recovery Flow

### 7.1 Scenario: Backend Process Unexpectedly Exits and Restarts

```
State before restart:
  Run A: RUNNING (strategy is executing)
  Run B: PENDING (created, not started)
  Run C: COMPLETED (finished)

After restart, RunManager.recover() executes:
  1. Load all Runs with status ∈ {PENDING, RUNNING} from RunRepository
  2. For each RUNNING Run (e.g., Run A):
     → Change status to ERROR (not a clean shutdown, cannot auto-recover execution state)
     → Emit run.Error event
  3. For each PENDING Run (e.g., Run B):
     → Restore to memory, keep PENDING
     → User can re-start
  4. COMPLETED/STOPPED/ERROR Runs are not processed
  5. Return the number of recovered Runs
```

### 7.2 Order Recovery

The latest order status can be synced with the exchange via `sync_order()`.
The exchange may have filled orders during the crash period — sync can discover and update local state.

---

## 8. Concurrency & Isolation

### 8.1 Multi-Run Concurrency Model

```
Run A (backtest, sma-crossover, BTC/USD)     Run B (paper, sample, ETH/USD)
┌─────────────────────────────┐              ┌─────────────────────────────┐
│ BacktestClock (fast-forward)│              │ RealtimeClock (wall-clock)  │
│ GretaService (independent   │              │ (No Greta, uses VedaService)│
│  positions/funds)           │              │ StrategyRunner (Sample)     │
│ StrategyRunner (SMAStrategy)│              │ Events: run_id = "bbb"      │
│ Events: run_id = "aaa"      │              └─────────────────────────────┘
└─────────────────────────────┘                         │
          │                                             │
          └──────────── Shared EventLog ───────────────┘
                    (Events distinguished by run_id)
```

### 8.2 Isolation Guarantees

| Isolation Point    | Mechanism                                                           |
| ------------------ | ------------------------------------------------------------------- |
| Event isolation    | All events carry `run_id`; subscribers can filter by `run_id`       |
| State isolation    | Per-run components (Greta, Runner, Clock) are independent instances |
| Data isolation     | GretaService's positions/funds/equity curve are fully independent   |
| Time isolation     | Each Run has its own clock, no mutual interference                  |
| Concurrency safety | Per-run `asyncio.Lock` prevents operation races within the same Run |

### 8.3 Shared Resource Access

| Shared Resource | Concurrency Safety Measure                                            |
| --------------- | --------------------------------------------------------------------- |
| EventLog        | Append operations are atomic (database transaction or in-memory lock) |
| BarRepository   | Read-only access, immutable data                                      |
| VedaService     | OrderManager is idempotent via client_order_id                        |
| SSEBroadcaster  | `put_nowait` is non-blocking, drops on full queue                     |

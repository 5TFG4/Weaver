# M14: Live Monitoring - Design Framework & Decision Points

> **Document Charter**
> **Primary role**: M14 milestone design & decision framework.
> **Status**: DECISIONS LOCKED — all owner decisions recorded; ready for implementation.
> **Prerequisite**: M13 complete.
> **Key inputs**: `docs/MILESTONE_PLAN.md` section 8b, codebase review, Alpaca API docs.
> **Branch**: TBD

---

## Table of Contents

1. [Background & Scope](#1-background--scope)
2. [Current System Snapshot](#2-current-system-snapshot)
3. [Boundaries & Principles](#3-boundaries--principles)
4. [Dependency Graph](#4-dependency-graph)
5. [Backend Decision Package](#5-backend-decision-package)
6. [Frontend Decision Package](#6-frontend-decision-package)
7. [External Research Notes](#7-external-research-notes)
8. [Test Impact](#8-test-impact)
9. [Decision Summary](#9-decision-summary)
10. [Recommended Default Path](#10-recommended-default-path)

---

## 1. Background & Scope

### 1.1 Why M14 Exists

M13 closed the loop for **backtest** runs: create → execute → inspect results.

M14 does the same for **live/paper** runs. Today a user can start a paper trading run, but there is no way to see what is actually happening: no positions, no fills, no account balance, no live charts. The "monitoring" half of the trading workflow is completely absent.

M14 bridges this gap: give the live/paper run detail page a dedicated monitoring surface with real-time data.

### 1.2 Official M14 Scope

Per `docs/MILESTONE_PLAN.md`:

| Task  | Layer    | Description                                                | Audit ref |
| ----- | -------- | ---------------------------------------------------------- | --------- |
| 14-1  | Backend  | `GET /runs/{id}/positions` endpoint (from PositionTracker) | A-2       |
| 14-2  | Backend  | `GET /runs/{id}/fills` endpoint (from FillRepository)      | A-4       |
| 14-3  | Backend  | `GET /account` endpoint (from ExchangeAdapter)             | A-3       |
| 14-4  | Backend  | `GET /events` historical query endpoint (from EventLog)    | A-5       |
| 14-5  | Backend  | Candles endpoint wired to real data source                 | B-7       |
| 14-6  | Backend  | `FillRecord` add `commission` and `symbol` fields          | B-8       |
| 14-7  | Backend  | `OrderResponse` add `cancelled_at` field                   | B-11      |
| 14-8  | Frontend | Detail page Monitoring tab: positions table, P&L card      | —         |
| 14-9  | Frontend | Real-time fill stream on detail page                       | —         |
| 14-10 | Frontend | Dashboard: check all 4 queries for error state             | C4        |
| 14-11 | Frontend | SSE: add `run.Created` event listener                      | M8        |

**Exit gate**: Start paper trading → detail page shows live positions, P&L, recent fills. Dashboard errors surface correctly.

### 1.3 What This Document Does

This document is for **owner decision-making**, not implementation.

For each task, it:

- summarizes the real constraints from the current codebase,
- enumerates viable options,
- compares pros and cons,
- identifies which options preserve flexibility for M15–M17,
- provides a provisional recommendation without locking the decision.

This version also includes a post-review correction pass, where recommendations
have been tightened to better match the current architecture and common industry
implementation patterns.

---

## 2. Current System Snapshot

### 2.1 Backend Position & Fill Infrastructure

| Area                  | Current State                                                                                                                                   | Evidence                                    |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| PositionTracker       | In-memory tracker: `apply_fill()`, `get_all_positions()`, `get_position()`                                                                      | `src/veda/position_tracker.py`              |
| Position model        | Dataclass: symbol, qty, side, avg_entry_price, market_value, unrealized_pnl/pct                                                                 | `src/veda/models.py` L171                   |
| VedaService           | Has `get_positions()`, `get_account()` accessors — but NOT scoped per run                                                                       | `src/veda/veda_service.py`                  |
| FillRepository        | Only `save()` and `list_by_order(order_id)` — no `list_by_run_id()` or exchange-fill dedupe helper                                              | `src/walle/repositories/fill_repository.py` |
| FillRecord            | Missing `commission` and `symbol` columns; `exchange_fill_id` exists but is not yet used as the canonical dedupe key                            | `src/walle/models.py` L229                  |
| Live fill persistence | `record_fill()` and `get_fills()` exist, but the current live/paper flow does not automatically call `record_fill()`                            | `src/veda/veda_service.py`                  |
| ExchangeAdapter       | Abstract: `get_account()`, `get_positions()`, `get_bars()` all defined                                                                          | `src/veda/interfaces.py`                    |
| AccountInfo           | Dataclass: account_id, buying_power, cash, portfolio_value, currency, status                                                                    | `src/veda/models.py` L160                   |
| RunContext (live)     | `greta: None, runner: StrategyRunner, clock: RealtimeClock` — no VedaService reference and no dedicated background-task lane for reconciliation | `src/glados/services/run_manager.py` L60    |

### 2.2 Backend API & Event Infrastructure

| Area              | Current State                                                                                                                                                                                                | Evidence                                                  |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- | ---------------------------- |
| Candles route     | `GET /api/v1/candles` — hardcoded to `MockMarketDataService` (fake data)                                                                                                                                     | `src/glados/routes/candles.py`                            |
| Candles contract  | Current route only accepts `symbol`, `timeframe`, `limit` — no explicit `start`/`end`                                                                                                                        | `src/glados/routes/candles.py`                            |
| EventLog          | `read_from(offset, limit)` and `subscribe_filtered()` exist                                                                                                                                                  | `src/events/log.py`                                       |
| SSE broadcaster   | Publishes events to all clients; SSE route supports `?run_id=` filtering                                                                                                                                     | `src/glados/sse_broadcaster.py`                           |
| Live order events | Veda path explicitly emits `orders.Created`, `orders.Rejected`, `orders.Cancelled`; `orders.PartiallyFilled` and `orders.Filled` exist in the event taxonomy but are not yet emitted end-to-end in live flow | `src/veda/veda_service.py`, `src/events/types.py`         |
| Order sync        | `VedaService.sync_order()` updates aggregate order state, but it is only exposed via manual REST sync today — there is no automatic background caller                                                        | `src/veda/veda_service.py`, `src/glados/routes/orders.py` |
| OrderResponse     | Missing `cancelled_at` field (exists in DB model `VedaOrder` and domain `OrderState`)                                                                                                                        | `src/glados/schemas.py`                                   |
| Dependencies      | `get_veda_service()` returns `VedaService                                                                                                                                                                    | None`; DI pattern established                             | `src/glados/dependencies.py` |

### 2.3 Frontend Infrastructure

| Area             | Current State                                                                                                     | Evidence                           |
| ---------------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| RunDetailPage    | Shows backtest results only; no tabs; `showResults` gated on `status==completed && mode==backtest`                | `haro/src/pages/RunDetailPage.tsx` |
| SSE hook         | Handles `run.Started/Stopped/Completed/Error`, `orders.Created/Filled/Rejected/Cancelled`                         | `haro/src/hooks/useSSE.ts`         |
| SSE missing      | No `run.Created` listener; no `orders.PartiallyFilled` handler; `orders.Filled` currently ignores payload details | `haro/src/hooks/useSSE.ts` L141    |
| Dashboard errors | Only checks `runsQuery.isError`; ignores `activeRunsQuery`, `ordersQuery`, `healthQuery`                          | `haro/src/pages/Dashboard.tsx` L29 |
| Charting         | Recharts already installed (from M13 equity curve)                                                                | `haro/package.json`                |
| Type system      | `Order` interface missing `cancelled_at`                                                                          | `haro/src/api/types.ts`            |
| API hooks        | `useRuns`, `useOrders`, `useHealth`, `useRunResults` exist                                                        | `haro/src/hooks/`                  |

---

## 3. Boundaries & Principles

### 3.1 M14 Boundaries

**In scope**: monitoring UI on the live/paper run detail page — positions,
fills, account, and chart data.

**Review correction**: unless the owner explicitly chooses to fund true
run-scoped position/account attribution, M14 should be treated as
**account-scoped monitoring anchored to a run page**, not as durable per-run
portfolio history.

**Out of scope** (later milestones):

- Cross-run comparison or performance columns on list pages — M16
- Sort/filter on list pages — M15
- Export endpoints — M17
- Strategy versioning — M16
- Risk enforcement — M17

### 3.2 Design Principles

1. **Live data first**: positions and account info should come from the exchange adapter (Alpaca) in real-time, not just from internal tracking.
2. **Run scoping**: positions/fills endpoints should be scoped to a run where possible, not global account state.
3. **Dual-mode detail page**: the run detail page should gracefully handle both backtest and live/paper runs.
4. **Reuse SSE infrastructure**: real-time fill stream should use the existing SSE pattern, not introduce WebSocket or polling.
5. **Schema-first**: continue the M13 pattern of typed Pydantic schemas → typed TS interfaces.
6. **Resource honesty**: do not present account-wide data as if it were truly
   owned by a single run unless we actually persist or derive run-scoped state.

### 3.3 Post-Review Corrections

The initial draft was directionally correct, but several recommendations needed
to be tightened after a code review of the live/paper path.

1. **Positions semantics must be clarified first**. The milestone wording says
   "from PositionTracker", while Alpaca positions are account-wide. These are
   different products and should not be conflated.
2. **14-2 and 14-9 need a shared backend prerequisite**. A repository JOIN is
   not enough; live/paper runs still need automatic fill ingestion,
   persistence, and emission of `orders.PartiallyFilled` / `orders.Filled`.
3. **RunManager lifecycle needs a dedicated background-task lane**. The
   current `pending_tasks` contract is for drain-to-completion work created by
   strategy execution, not for indefinite reconciliation pollers.
4. **14-5 needs a stronger API contract**. A real candles endpoint for charts
   should expose `start` and `end`; `limit`-only is not enough for predictable
   monitoring windows.
5. **14-4 should default to deferred**. Historical event browsing is useful,
   but it is not required to hit the M14 exit gate if fills are served by
   `GET /runs/{id}/fills` plus SSE refresh.

---

## 4. Dependency Graph

```
14-6 FillRecord fields ─────┐
                            ├──> Live fill reconciliation backbone ──┬──> 14-2 fills endpoint
RunManager live task wiring ─┘                                        └──> 14-9 fill stream

14-1 positions endpoint ──────────────────────────────────────────────┐
                                                                      ├──> 14-8 monitoring tab
14-3 account endpoint ────────────────────────────────────────────────┤
                                                                      │
14-5 candles wired ───────────────────────────────────────────────────┘

14-7 cancelled_at ──> (independent schema fix)

14-4 events endpoint ──> deferred by default

14-10 dashboard errors ──> (independent frontend fix)

14-11 run.Created SSE ──> (independent frontend fix)
```

**Key takeaway**:

- 14-6 (FillRecord migration) blocks 14-2 (fills endpoint).
- 14-1, 14-2, 14-3 all feed into 14-8 (monitoring tab).
- 14-4, 14-9 are related but 14-9 can use SSE directly without 14-4.
- 14-7, 14-10, 14-11 are independent fixes with no blockers.

---

## 5. Backend Decision Package

### 5.1 Task 14-1: Positions Endpoint

#### 5.1.1 Current State

`PositionTracker` tracks positions in-memory from fills. `ExchangeAdapter.get_positions()` fetches from the exchange directly. `VedaService` wraps both. But:

- `VedaService` is a singleton — not scoped per run.
- `PositionTracker` is per-VedaService instance, not per-run.
- For paper trading, Alpaca's paper API returns real account positions (shared across all runs).

There is therefore a critical design distinction:

- **true run-scoped positions**: what this run opened or currently holds;
- **account-scoped positions on a run page**: what the trading account holds
  while the user is viewing this run.

These should not be treated as interchangeable.

#### 5.1.2 Industry Guidance

Microsoft's REST API guidance recommends modeling URIs around real business
resources, keeping relationships simple, and avoiding contracts that mirror
implementation accidents. Applied here:

- if the resource is truly **account-owned**, a canonical URI like
  `/account/positions` is the honest shape;
- if the resource is truly **run-owned**, the backend needs real run-scoped
  state, not just a route that says so.

#### 5.1.3 Decision Point D-14-1: Position Semantics

**Option A: True run-scoped positions from `PositionTracker` (or persisted run snapshot)**

Route: `GET /api/v1/runs/{id}/positions` → resolve run-owned position state.

| Pros                                      | Cons                                                           |
| ----------------------------------------- | -------------------------------------------------------------- |
| Matches milestone wording most closely    | Current architecture does not persist or expose this cleanly   |
| Honest run contract                       | `RunContext` does not currently hold Veda/PositionTracker refs |
| Better fit for future M16 run attribution | In-memory tracker is lost after stop/restart                   |
|                                           | Unrealized P&L still needs market prices                       |

**Option B: Canonical account-scoped positions via `ExchangeAdapter.get_positions()` (recommended default path)**

Canonical route: `GET /api/v1/account/positions`.
Optional UI convenience alias: `GET /api/v1/runs/{id}/positions`, explicitly documented as account-scoped data.

| Pros                                            | Cons                                                 |
| ----------------------------------------------- | ---------------------------------------------------- |
| Honest to Alpaca's resource model               | Not per-run attribution                              |
| Real exchange data — what the user actually has | If multiple runs trade different symbols, all show   |
| Simplest useful monitoring experience           | Requires owner acceptance that M14 is account-scoped |
| Best match for a canonical REST resource        |                                                      |

**Option C: Hybrid — show exchange positions, annotate with run-level tracking**

Merge `ExchangeAdapter.get_positions()` for account-level truth with `PositionTracker` for per-run fill attribution.

| Pros                                           | Cons                                       |
| ---------------------------------------------- | ------------------------------------------ |
| Best of both worlds                            | Most complex to implement                  |
| Real P&L from exchange + run-level attribution | Mapping logic between two position sources |
|                                                | Premature for single-run usage patterns    |

**Revised provisional recommendation**: Option B as the canonical contract.
If the owner wants to preserve the original task wording, keep
`GET /runs/{id}/positions` only as a thin alias and explicitly document the
response as **account-scoped** rather than true run-owned state.

> **Owner decision**: **B**. Upgrade to **C** (hybrid mode) in M16, adding
> PositionTracker for per-run fill attribution at that point.

#### 5.1.4 Decision Point D-14-1B: Positions Endpoint URL Shape

**Option A: Canonical `GET /account/positions` plus optional run-page alias (recommended)**

| Pros                                                    | Cons                               |
| ------------------------------------------------------- | ---------------------------------- |
| Keeps canonical resource honest                         | Slightly more frontend composition |
| Aligns with Microsoft REST guidance on simple resources | Adds one more endpoint             |
| Still allows run-detail page UX                         |                                    |

**Option B: Only `GET /runs/{id}/positions`**

| Pros                                 | Cons                                          |
| ------------------------------------ | --------------------------------------------- |
| Consistent with run-detail page URLs | Resource contract becomes misleading          |
| Simpler frontend wiring              | Hides account-wide semantics behind a run URI |

**Option C: Both `/account/positions` and `/runs/{id}/positions` as first-class endpoints**

| Pros                             | Cons                    |
| -------------------------------- | ----------------------- |
| Maximum flexibility              | Duplicate API surface   |
| Gives clean migration path later | Higher maintenance cost |

**Revised provisional recommendation**: Option A.

---

### 5.2 Task 14-2: Fills Endpoint

#### 5.2.1 Current State

`FillRepository.list_by_order(order_id)` exists but there is no `list_by_run_id()`. `FillRecord` lacks `commission` and `symbol` columns (task 14-6 dependency). The repository can persist fills, but the current live/paper path does not automatically call `record_fill()`, and `sync_order()` is only triggered manually.

#### 5.2.2 Execution Correction: Live Fills Need an Automatic Backbone

This was the largest gap found in plan review.

Without an automatic ingestion path:

- 14-2 can expose only historical or manually-synced fills,
- 14-9 has no trustworthy live event to invalidate against,
- `_hydrate_fills()` remains mostly theoretical for paper/live runs.

**Recommended default path for M14**: use Alpaca trading account activities via
authenticated REST polling, not a new broker trade-event SSE client.

Why this path fits the current architecture:

- Weaver already has trading-account credentials and an Alpaca trading adapter.
- External broker SSE would introduce a second long-lived network client,
  reconnect logic, backpressure handling, and lifecycle management that the
  current runtime does not otherwise need.
- Alpaca account activities already provide the fields M14 needs for a fill
  audit trail: `id`, `order_id`, `symbol`, `side`, `qty`, `price`,
  `transaction_time`, `leaves_qty`, `cum_qty`, `order_status`, and `type`
  (`partial_fill` or `fill`).

**Minimal backbone contract**:

1. Add a normalized trade-activity model and `ExchangeAdapter.list_trade_activities(after, until=None, page_size=100)`.
2. Implement that adapter method in `AlpacaAdapter` with an authenticated
   `httpx` call to `GET /v2/account/activities/FILL?direction=asc&page_size=100`.
3. Match `activity.order_id` to local `OrderState.exchange_order_id` for the
   run's persisted orders.
4. Persist `FillRecord` idempotently using Alpaca `activity.id` as the
   canonical fill identifier (`id` and `exchange_fill_id`).
5. Emit `orders.PartiallyFilled` for `type == "partial_fill"` and
   `orders.Filled` for `type == "fill"`, then call `sync_order()` to refresh
   aggregate order state.
6. Run this from a RunManager-managed background task for each live/paper run.

Because the activity endpoint is paginated and polling windows may overlap, the
implementation should be intentionally idempotent. The easiest M14-safe rule is
to treat Alpaca `activity.id` as the canonical persisted fill key.

#### 5.2.3 Decision Point D-14-2: Fills Query Strategy

**Option A: Add `list_by_run_id()` via JOIN on orders table (recommended)**

SQL: `SELECT fills.* FROM fills JOIN orders ON fills.order_id = orders.id WHERE orders.run_id = :run_id ORDER BY fills.filled_at DESC`.

| Pros                                     | Cons                                          |
| ---------------------------------------- | --------------------------------------------- |
| Run-scoped fills without denormalization | Requires JOIN — slightly more complex query   |
| data model stays normalized              | Need to verify orders table has run_id column |
| Natural for run detail page              |                                               |

**Option B: Add `run_id` column directly to `FillRecord`**

| Pros                                     | Cons                                       |
| ---------------------------------------- | ------------------------------------------ |
| Simplest query: `WHERE run_id = :run_id` | Denormalization — run_id already on orders |
| No JOIN needed                           | Extra migration + data backfill needed     |
| Faster queries                           | Violates DRY                               |

**Option C: Query fills via order_ids from OrderRepository**

Two-step: fetch order IDs for run → fetch fills for those orders.

| Pros                    | Cons                                  |
| ----------------------- | ------------------------------------- |
| No schema change needed | N+1 query risk (or complex IN clause) |
| Reuses existing methods | Fragile pagination                    |

**Provisional recommendation**: Option A. JOIN is the standard relational approach and avoids denormalization. The query complexity is trivial.

**Execution note**: this query strategy only becomes useful once the live fill
backbone above is in place. Do not implement 14-2 as if the repository already
contains live fills.

---

### 5.3 Task 14-3: Account Endpoint

#### 5.3.1 Current State

`ExchangeAdapter.get_account()` returns `AccountInfo(account_id, buying_power, cash, portfolio_value, currency, status)`. `VedaService` wraps this. No REST endpoint exists.

#### 5.3.2 Decision Point D-14-3: Account Endpoint Scope

**Option A: Global `GET /api/v1/account` (recommended)**

| Pros                                  | Cons                                        |
| ------------------------------------- | ------------------------------------------- |
| Matches Alpaca semantics: one account | Not run-scoped                              |
| Clean REST semantics                  | Might confuse if we later add multi-account |
| Simple implementation                 |                                             |

**Option B: Run-scoped `GET /api/v1/runs/{id}/account`**

| Pros                                    | Cons                        |
| --------------------------------------- | --------------------------- |
| Consistent with run-detail page pattern | Account is not run-specific |
| Run validation gives security context   | Misleading URL semantics    |

**Option C: Embed account info in positions response**

Return `{ account: {...}, positions: [...] }` from a single endpoint.

| Pros                           | Cons                                  |
| ------------------------------ | ------------------------------------- |
| One request for monitoring tab | Couples unrelated concerns            |
| Simpler frontend data fetching | Harder to cache/invalidate separately |

**Provisional recommendation**: Option A. Account is fundamentally global. The monitoring tab can call two endpoints: one for account, one for positions.

---

### 5.4 Task 14-4: Events Historical Query Endpoint

#### 5.4.1 Current State

`EventLog.read_from(offset, limit)` reads events from a given offset. `subscribe_filtered()` supports type filtering. But no REST endpoint exposes event history.

#### 5.4.2 Decision Point D-14-4: Events Endpoint Design

**Option A: Simple paginated query `GET /api/v1/events?run_id=&type=&offset=&limit=`**

| Pros                                    | Cons                                              |
| --------------------------------------- | ------------------------------------------------- |
| Directly maps to `EventLog.read_from()` | May need filtering by run_id at application level |
| Useful for debugging and audit          | Potentially large result sets                     |
| Enables frontend event history view     | Event payloads vary by type                       |

**Option B: Type-specific query endpoints (e.g. `/events/fills`, `/events/orders`)**

| Pros                           | Cons                            |
| ------------------------------ | ------------------------------- |
| Typed responses per event type | Many endpoints to maintain      |
| Cleaner OpenAPI documentation  | Duplicates fill/order endpoints |

**Option C: Defer to M15 — use SSE for live, existing endpoints for history**

| Pros                                  | Cons                         |
| ------------------------------------- | ---------------------------- |
| Less work in M14                      | No event history UI          |
| SSE already provides real-time events | Loses audit trail visibility |

**Revised provisional recommendation**: Option C by default.
Defer 14-4 to M15 unless the owner explicitly wants an event-history browser in
M14. For the M14 exit gate, `GET /runs/{id}/fills` plus SSE refresh is enough.

> **Owner decision**: **C** — confirmed deferred to M15.

#### 5.4.3 Supplementary Decision: Is 14-4 required for 14-9?

**Observation**: Task 14-9 (real-time fill stream) can be implemented purely via SSE `orders.PartiallyFilled` / `orders.Filled` events. The fill stream on the detail page only needs:

1. Historical fills (already loaded from 14-2 `GET /runs/{id}/fills`)
2. Live new fills (from SSE fill events → TanStack Query invalidation)

If that's sufficient, task 14-4 becomes a "nice-to-have" for M14 and could be deferred.

**Review outcome**: default to defer.

---

### 5.5 Task 14-5: Candles Endpoint Wired to Real Data

#### 5.5.1 Current State

`GET /api/v1/candles` is implemented but returns fake data from `MockMarketDataService`. The real data path exists: `ExchangeAdapter.get_bars(symbol, timeframe, start, end, limit)`. Alpaca's data API (`data.alpaca.markets/v2/stocks/bars`) provides historical bars with symbol, timeframe, start/end timestamps, limit, and pagination.

The current REST contract is underspecified for real charting because it does
not expose `start` or `end` query parameters.

#### 5.5.2 Decision Point D-14-5: Candles Data Source Routing

**Option A: Replace MockMarketDataService with Alpaca adapter and extend the contract with `start`/`end` (recommended)**

Inject `ExchangeAdapter` into candles route; call `adapter.get_bars()`.

| Pros                                             | Cons                                      |
| ------------------------------------------------ | ----------------------------------------- |
| Real market data for chart display               | Requires Alpaca credentials               |
| Simple: swap one dependency                      | API rate limits from Alpaca data endpoint |
| Alpaca data API provides stock bars directly     | Need to handle credential-absent fallback |
| Explicit time window matches industry chart APIs | Requires a small contract expansion       |

**Option B: Dual-source: ExchangeAdapter for live, BarRepository for historical**

Route checks run mode:

- Live/paper: `ExchangeAdapter.get_bars()` from Alpaca
- Backtest: `BarRepository` from local DB (WallE data)

| Pros                                 | Cons                                                 |
| ------------------------------------ | ---------------------------------------------------- |
| Works for both run types             | More complex routing logic                           |
| Backtest doesn't need live API calls | BarRepository uses different data format than Alpaca |
| Optimal data source per context      |                                                      |

**Option C: Create MarketDataService interface + implementations**

Abstract `MarketDataService` protocol with `AlpacaMarketDataService` and `MockMarketDataService` implementations.

| Pros                          | Cons                                         |
| ----------------------------- | -------------------------------------------- |
| Clean abstraction boundary    | More code for M14 scope                      |
| Testable with mocks           | May be premature if only Alpaca is supported |
| Follows PluginAdapter pattern |                                              |

**Revised provisional recommendation**: Option A.
Do not ship a "real" candles endpoint without `start` and `end`; Alpaca's own
bars API is fundamentally range-based.

#### 5.5.3 Decision Point D-14-5B: Candles Endpoint URL

**Option A: Keep existing `GET /api/v1/candles?symbol=&timeframe=`**

| Pros                                   | Cons           |
| -------------------------------------- | -------------- |
| No breaking change                     | Not run-scoped |
| Already consumed by frontend (if used) |                |

**Option B: Add `GET /api/v1/runs/{id}/candles?symbol=&timeframe=`**

| Pros                                         | Cons                                      |
| -------------------------------------------- | ----------------------------------------- |
| Run-scoped, can auto-set date range from run | Candles are market data, not run-specific |
| Cleaner for detail page context              | Unusual REST semantics                    |

**Revised provisional recommendation**: Option A, but extend the existing
generic endpoint to accept `start` and `end` explicitly.

#### 5.5.4 Decision Point D-14-5C: Candles Query Contract

**Option A: Add `start` and `end` now (recommended)**

| Pros                                                    | Cons                              |
| ------------------------------------------------------- | --------------------------------- |
| Matches Alpaca and most industry chart APIs             | Slightly larger API surface       |
| Deterministic chart windows                             | Requires route and client updates |
| Works for both monitoring and future backfill use cases |                                   |

**Option B: Keep `limit`-only in M14**

| Pros                    | Cons                                   |
| ----------------------- | -------------------------------------- |
| Lowest immediate change | Poor fit for real monitoring windows   |
|                         | Hard to align chart with run lifecycle |

**Option C: Infer time window from run server-side**

| Pros                 | Cons                                       |
| -------------------- | ------------------------------------------ |
| Less work for client | Couples market data route to run semantics |
|                      | Harder to reuse elsewhere                  |

**Revised provisional recommendation**: Option A.

---

### 5.6 Task 14-6: FillRecord Migration

#### 5.6.1 Current State

`FillRecord` columns: `id`, `order_id`, `price`, `quantity`, `side`, `filled_at`, `exchange_fill_id`. Missing: `commission` (Decimal), `symbol` (String).

The domain model `Fill` in `veda/models.py` already has `commission: Decimal` but NOT `symbol`. Alpaca trading account activities provide `symbol`, but they do **not** provide a reliable per-fill commission field in the standard trading payload, so M14 should keep `commission` nullable in persistence and avoid synthesizing fake non-null values.

#### 5.6.2 Decision Point D-14-6: Migration Approach

**Option A: Add both columns as nullable with defaults (recommended)**

```python
commission: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

| Pros                                            | Cons                                       |
| ----------------------------------------------- | ------------------------------------------ |
| Backward compatible — existing fills unaffected | Nullable means queries need to handle None |
| Simple Alembic migration                        | Old fills won't have symbol data           |
| Can backfill from orders table later            |                                            |

**Option B: Non-nullable with data migration backfill**

| Pros           | Cons                                                |
| -------------- | --------------------------------------------------- |
| Cleaner schema | Complex migration — must backfill from orders table |
|                | Risky if orders table doesn't have all needed data  |

**Provisional recommendation**: Option A. Nullable columns are safe. New fills will populate both fields; old fills can be backfilled in a future maintenance pass.

#### 5.6.3 Supplementary: Should `Fill` domain model also add `symbol`?

Yes. The `Fill` dataclass in `veda/models.py` should add `symbol: str | None = None` to match the persistence layer and enable per-symbol fill reporting. `_hydrate_fills()` should then map `record.symbol` and use `record.commission or Decimal("0")` instead of hardcoding commission for every hydrated fill.

---

### 5.7 Task 14-7: OrderResponse `cancelled_at` Field

#### 5.7.1 Current State

- DB model `VedaOrder`: has `cancelled_at` column.
- Domain model `OrderState`: has `cancelled_at: datetime | None`.
- API schema `OrderResponse`: **missing** `cancelled_at`.
- Frontend type `Order`: **missing** `cancelled_at`.

#### 5.7.2 Approach

This is straightforward — no decision needed, just execution:

1. Add `cancelled_at: datetime | None = None` to `OrderResponse` schema.
2. Map `cancelled_at` from `OrderState` in the route conversion function.
3. Add `cancelled_at?: string` to frontend `Order` interface.

No alternative options — this is a schema alignment fix.

---

## 6. Frontend Decision Package

### 6.1 Task 14-8: Monitoring Tab

#### 6.1.1 Current State

`RunDetailPage` currently shows:

- Header with run metadata + status badge
- Backtest results (stats card, equity chart, trade log) — only for `mode==backtest && status==completed`
- Placeholder text for non-backtest or non-completed runs

No tab system exists.

#### 6.1.2 Decision Point D-14-8A: Tab Strategy

**Option A: Simple conditional sections based on run mode**

No actual tab UI — show different content blocks based on `run.mode`:

- Backtest completed: show results sections (existing)
- Live/paper running: show monitoring sections (new)
- Live/paper completed: show both?

| Pros                                | Cons                                          |
| ----------------------------------- | --------------------------------------------- |
| Simplest implementation             | No user control over what to see              |
| Matches current page structure      | Doesn't scale if both views apply to same run |
| No third-party tab component needed |                                               |

**Option B: Full tab system with headlessui Tab component**

Use `@headlessui/react` `Tab` (already installed from M12-B a11y work) with:

- Tab "Results" (backtest only)
- Tab "Monitoring" (live/paper only, or both)
- Tab "Events" (all modes, future)

| Pros                            | Cons                                      |
| ------------------------------- | ----------------------------------------- |
| Clean UX, discoverable          | More implementation work                  |
| A11y handled by headlessui      | Which tabs show varies by mode + status   |
| Scales for future M15–M16 needs | Tab state management (URL hash or local?) |

**Option C: Route-based sub-pages (`/runs/:id/results`, `/runs/:id/monitoring`)**

| Pros                      | Cons                    |
| ------------------------- | ----------------------- |
| Clean URLs, deep-linkable | Heavier routing changes |
| Lazy loading per sub-page | Overkill for 2 views    |

**Provisional recommendation**: Option B. `@headlessui/react` is already installed; the Tab component gives us accessible tabs with minimal code. The UX is significantly better than conditional blocks.

#### 6.1.3 Decision Point D-14-8B: Polling vs SSE for Position/Account Updates

**Option A: Polling via TanStack Query `refetchInterval` (recommended)**

```ts
useQuery({
  queryKey: ["runs", runId, "positions"],
  queryFn: () => fetchPositions(runId),
  refetchInterval: 5000, // 5 seconds
  enabled: run?.status === "running",
});
```

| Pros                                           | Cons                           |
| ---------------------------------------------- | ------------------------------ |
| TanStack Query native, already used everywhere | Extra HTTP requests every 5s   |
| Simple: just set refetchInterval               | Not truly real-time (5s delay) |
| Auto-stops when run isn't running              |                                |
| Server-side is simple REST                     |                                |

**Option B: Dedicated SSE events for positions and account changes**

Backend publishes `account.Updated`, `positions.Changed` events.

| Pros                        | Cons                                          |
| --------------------------- | --------------------------------------------- |
| True real-time              | Backend needs to emit new event types         |
| No polling overhead         | PositionTracker doesn't currently emit events |
| Consistent with fill stream | More infrastructure for marginal UX benefit   |

**Provisional recommendation**: Option A. Positions and account aren't microsecond-critical. 5-second polling is standard for trading dashboards and dramatically simpler than adding new SSE event types.

> **Owner decision**: **A**. Confirmed: 5-second polling only affects browser
> UI display refresh rate, not backend strategy execution latency (strategies
> access data directly via VedaService → ExchangeAdapter, not through
> frontend REST polling).

#### 6.1.4 Decision Point D-14-8C: Monitoring Tab Components

Components needed:

1. **PositionsTable**: symbol, qty, side, avg_entry_price, market_value, unrealized_pnl, unrealized_pnl_percent
2. **AccountCard / P&L Card**: buying_power, cash, portfolio_value, status

**Option A: Simple table + stat card (recommended)**

Reuse existing patterns:

- `PositionsTable`: same structure as `OrderTable` (data table with columns)
- `AccountCard`: same structure as `BacktestStatsCard` (labeled values in grid)

| Pros                                        | Cons                        |
| ------------------------------------------- | --------------------------- |
| Consistent with existing component patterns | No P&L chart (just numbers) |
| Fast to implement                           |                             |
| Reuses Tailwind patterns                    |                             |

**Option B: Rich monitoring dashboard with mini P&L chart**

Add a small equity-over-time chart for the live run using Recharts.

| Pros                         | Cons                                                    |
| ---------------------------- | ------------------------------------------------------- |
| More visually informative    | Needs historical portfolio values (Alpaca has this API) |
| Better monitoring experience | More API integration work                               |

**Provisional recommendation**: Option A for M14. Table + card gives the core monitoring view. A mini equity chart can be added in M16 when strategy comparison becomes relevant.

> **Owner decision**: **A** — can upgrade to B later if needed.

---

### 6.2 Task 14-9: Real-time Fill Stream

#### 6.2.1 Current State

SSE hook already listens for `orders.Filled` but doesn't parse the event data
(just shows a generic "Order filled" toast), and it does not handle
`orders.PartiallyFilled` at all. TanStack Query invalidation for `["orders"]`
already happens on fill.

However, the backend prerequisite is not fully locked yet: the live/paper Veda
path explicitly emits `orders.Created`, `orders.Rejected`, and
`orders.Cancelled`, but the fill-event chain should be treated as an explicit
prerequisite rather than assumed.

#### 6.2.2 Decision Point D-14-9: Fill Stream Implementation

**Option A: SSE → TanStack Query invalidation → re-fetch fills endpoint (recommended after backend prerequisite)**

On `orders.PartiallyFilled` or `orders.Filled` event:

1. Invalidate `["runs", runId, "fills"]` query key
2. TanStack Query auto-refetches from `GET /runs/{id}/fills`
3. Fill table updates

| Pros                                            | Cons                                 |
| ----------------------------------------------- | ------------------------------------ |
| Leverages existing SSE + React Query pattern    | Extra HTTP request per fill event    |
| Source of truth is always the DB (via endpoint) | Very slight delay (fetch round-trip) |
| Simple: 2 lines of code in useSSE               |                                      |
| No state sync issues                            |                                      |

**Option B: Poll `GET /runs/{id}/fills` every 3-5s while run is active**

| Pros                                     | Cons                        |
| ---------------------------------------- | --------------------------- |
| No dependence on a live fill-event chain | Extra periodic HTTP traffic |
| Very robust as a fallback                | Not truly real-time         |
| Easy to add and remove later             |                             |

**Option C: SSE → optimistic append to fill list in React Query cache**

Parse fill data from SSE event, inject directly into cached query data.

| Pros                    | Cons                                     |
| ----------------------- | ---------------------------------------- |
| Truly instant UI update | Cache can drift from server state        |
| No extra HTTP request   | Must handle SSE payload format carefully |
|                         | Complex cache manipulation               |

**Revised provisional recommendation**: Option A if M14 explicitly adds the
missing partial/full fill event path; otherwise use Option B as a temporary
fallback. Avoid optimistic cache writes as the default.

> **Owner decision**: **A** — requires completing the
> `orders.PartiallyFilled` / `orders.Filled` backend event chain in Phase 1
> as an explicit prerequisite.

---

### 6.3 Task 14-10: Dashboard Error Handling

#### 6.3.1 Current State

```typescript
const isError = runsQuery.isError; // Only checks ONE of FOUR queries
```

`activeRunsQuery.isError`, `ordersQuery.isError`, and `healthQuery.isError` are silently ignored.

#### 6.3.2 Decision Point D-14-10: Error Display Strategy

**Option A: Aggregate error check — show dashboard error if ANY query fails**

```typescript
const isError =
  runsQuery.isError ||
  activeRunsQuery.isError ||
  ordersQuery.isError ||
  healthQuery.isError;
```

| Pros                                        | Cons                                                      |
| ------------------------------------------- | --------------------------------------------------------- |
| Simple — one error state for the whole page | May be too aggressive (health failing ≠ dashboard broken) |
| User immediately knows something's wrong    | Single error message can't distinguish sources            |

**Option B: Per-card error states**

Each `StatCard` independently shows error or data based on its own query.

| Pros                                               | Cons                                        |
| -------------------------------------------------- | ------------------------------------------- |
| Granular: health failure doesn't kill runs display | More UI complexity                          |
| Partial data is still useful                       | Need error variant for `StatCard` component |
| Most informative for user                          |                                             |

**Option C: Split — critical errors block page, non-critical show inline warnings**

If `runsQuery` fails → full page error. If `healthQuery` fails → warning banner or card-level indicator.

| Pros               | Cons                                        |
| ------------------ | ------------------------------------------- |
| Balanced UX        | Need to define "critical" vs "non-critical" |
| Doesn't over-block | Slightly more complex                       |

**Provisional recommendation**: Option B. Per-card error states are the most user-friendly and align with dashboard best practices. Each StatCard should handle its own `isError` state with a fallback display.

---

### 6.4 Task 14-11: SSE `run.Created` Listener

#### 6.4.1 Current State

`RunEvents.CREATED` is defined in `src/events/types.py`. The SSE hook handles `run.Started`, `run.Stopped`, `run.Completed`, `run.Error` but NOT `run.Created`.

#### 6.4.2 Approach

This is straightforward — no decision needed:

1. Add `addEventListener("run.Created", ...)` in `useSSE.ts`
2. Invalidate `["runs"]` queries
3. Show info toast: "Run {run_id} created"

Pattern is identical to existing `run.Started` handler.

**Verification**: `RunManager.create()` already emits `RunEvents.CREATED`, so
this task is frontend-only.

---

## 7. External Research Notes

### 7.1 Microsoft REST Guidance

Microsoft's REST API guidance recommends:

- model URIs around real business resources, not implementation details;
- keep resource relationships simple;
- use nested resources only when the ownership relationship is real;
- avoid chatty APIs, but also avoid lying about what a resource actually is.

Applied to M14:

- `account` and `account/positions` are natural canonical resources for Alpaca-backed monitoring;
- a run-scoped URI is appropriate only if Weaver truly owns run-scoped state;
- combining related data for a page is fine, but the canonical resource model should stay honest.

### 7.2 TanStack Query Guidance

TanStack Query recommends targeted invalidation plus background refetching over
manual normalized-cache mutation. It also treats polling via
`refetchInterval` as a first-class pattern.

Applied to M14:

- positions/account are good polling candidates;
- fills are a good SSE-triggered invalidation candidate;
- optimistic cache writes should not be the default when the server is already
  the durable source of truth.

### 7.3 Alpaca API — Positions

Alpaca's `GET /v2/positions` returns all open positions for the account with:

- `symbol`, `asset_class`, `qty`, `side` (long/short)
- `avg_entry_price`, `market_value`, `cost_basis`
- `unrealized_pl`, `unrealized_plpc` (percent)
- `current_price`, `lastday_price`, `change_today`

This maps well to Weaver's `Position` dataclass. Key difference: Alpaca returns
**account-wide open positions**, not run-attributed positions. Closed positions
drop out of this API, so it is a poor source for historical per-run views.

### 7.4 Alpaca API — Account

Alpaca's `GET /v2/account` returns:

- `account_number`, `status`, `currency`, `buying_power`, `cash`, `portfolio_value`
- Plus many fields we don't use in M14: `long_market_value`, `short_market_value`, `equity`, `last_equity`, `daytrading_buying_power`, etc.

Our `AccountInfo` dataclass covers the essential fields. No change needed.

### 7.5 Alpaca API — Historical Bars

Alpaca's `GET /v2/stocks/bars` accepts:

- `symbols` (comma-separated)
- `timeframe` (e.g. `1Min`, `5Min`, `1Hour`, `1Day`)
- `start`, `end` (RFC-3339)
- `limit` (max 10000)
- `adjustment` (raw, split, dividend, all)
- `feed` (sip, iex)
- `sort` (asc, desc)

Returns OHLCV with `{ t, o, h, l, c, v, n, vw }` (timestamp, open, high, low, close, volume, trade_count, vwap).

This maps directly to `ExchangeAdapter.get_bars()` → `Bar` dataclass. The `MockMarketDataService.Candle` type in candles route needs to be replaced with or mapped from `Bar`.

### 7.6 Alpaca Timeframe Format

Alpaca uses formats like `1Min`, `5Min`, `1Hour`, `1Day` — NOT `1m`, `5m`, `1h`, `1d`. Our system uses the latter format. A mapping function is needed in `AlpacaAdapter.get_bars()`, or the candles endpoint must normalize.

---

## 8. Test Impact

### 8.1 Estimated Test Coverage

| Task                           | Area     | Estimated New Tests                                                                |
| ------------------------------ | -------- | ---------------------------------------------------------------------------------- |
| Foundation: live fill backbone | Backend  | 12–18 (adapter parse, reconciliation dedupe, event emission, RunManager lifecycle) |
| 14-1                           | Backend  | 8–12 (route + schema + mock adapter)                                               |
| 14-2                           | Backend  | 8–12 (route + repository JOIN + schema)                                            |
| 14-3                           | Backend  | 5–8 (route + schema)                                                               |
| 14-4                           | Backend  | 0–12 (0 if deferred; 8–12 if kept in M14)                                          |
| 14-5                           | Backend  | 6–10 (route refactor + time-window defaults + adapter integration)                 |
| 14-6                           | Backend  | 3–5 (model + migration)                                                            |
| 14-7                           | Backend  | 2–3 (schema field)                                                                 |
| 14-8                           | Frontend | 15–20 (tab, positions table, account card, stale-test replacement)                 |
| 14-9                           | Frontend | 6–10 (SSE handler for partial/full fills + fill refresh)                           |
| 14-10                          | Frontend | 5–8 (dashboard error states)                                                       |
| 14-11                          | Frontend | 2–3 (SSE handler)                                                                  |
| **Total**                      |          | **~69–119 new/updated tests**                                                      |

### 8.2 Existing Tests at Risk

- Candles route tests (if any) need refactoring for real data source.
- Dashboard tests need update for per-card error handling.
- SSE hook tests need new event handlers.

---

## 9. Decision Summary

| Decision | Question                 | Options                                                                                            | Provisional                      | Owner decision                                                                                   |
| -------- | ------------------------ | -------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------ |
| D-14-1   | Position semantics       | A: True run-scoped tracker/snapshot, B: Canonical account-scoped positions, C: Hybrid              | B                                | **B** — upgrade to C (hybrid: Alpaca positions + run attribution) in M16                         |
| D-14-1B  | Positions endpoint URL   | A: `/account/positions` + optional alias, B: `/runs/{id}/positions` only, C: both first-class      | A                                | **A**                                                                                            |
| D-14-2A  | Live fill ingestion path | A: Alpaca account-activities reconciliation, B: Broker trade-event SSE client, C: Manual sync only | A                                | **A** — M14 uses account activities + RunManager-managed background polling                      |
| D-14-2   | Fills query strategy     | A: JOIN, B: Denorm run_id, C: Two-step                                                             | A                                | **A**                                                                                            |
| D-14-3   | Account endpoint scope   | A: Global, B: Run-scoped, C: Embedded                                                              | A                                | **A**                                                                                            |
| D-14-4   | Events endpoint design   | A: Paginated query, B: Per-type endpoints, C: Defer                                                | C                                | **C** — deferred to M15                                                                          |
| D-14-5   | Candles data source      | A: Alpaca swap, B: Dual-source, C: Abstract                                                        | A                                | **A**                                                                                            |
| D-14-5B  | Candles endpoint URL     | A: Keep existing, B: Run-scoped                                                                    | A                                | **A**                                                                                            |
| D-14-5C  | Candles query contract   | A: Add `start`/`end` now, B: Keep limit-only, C: Infer from run                                    | A                                | **A**                                                                                            |
| D-14-6   | FillRecord migration     | A: Nullable, B: Non-null + backfill                                                                | A                                | **A**                                                                                            |
| D-14-8A  | Tab strategy             | A: Conditional sections, B: headlessui Tabs, C: Sub-routes                                         | B                                | **B**                                                                                            |
| D-14-8B  | Position/account updates | A: Polling, B: SSE events                                                                          | A                                | **A** — 5s polling only affects UI display refresh, not strategy execution latency               |
| D-14-8C  | Monitoring components    | A: Simple table+card, B: Rich with chart                                                           | A                                | **A** — can upgrade to B later if needed                                                         |
| D-14-9   | Fill stream mechanism    | A: SSE→invalidate→refetch, B: short polling fallback, C: optimistic cache                          | A if prerequisite exists, else B | **A** — requires completing `orders.PartiallyFilled` / `orders.Filled` backend event chain first |
| D-14-10  | Dashboard error display  | A: Aggregate, B: Per-card, C: Split                                                                | B                                | **B**                                                                                            |

---

## 10. Recommended Default Path

If no decisions are changed, the default implementation order would be:

**Phase 0: Scope Lock**

1. Lock M14 as **account-scoped monitoring on a run page**, not durable run-owned portfolio history.

**Phase 1: Live Fill Backbone & Schema Foundation** 2. 14-6: FillRecord migration (`commission`, `symbol`) 3. Add normalized trade-activity model + Alpaca account-activities adapter call 4. Add RunManager-managed live reconciliation task, idempotent fill persistence, and `orders.PartiallyFilled` / `orders.Filled` emission 5. 14-7: OrderResponse `cancelled_at` (independent schema fix)

**Phase 2: Backend Endpoints** 6. 14-3: Account endpoint (global) 7. 14-1: Positions endpoint with canonical account semantics (`/account/positions`, optional run-page alias) 8. 14-2: Fills endpoint (JOIN query) 9. 14-5: Candles wired to Alpaca with explicit `start`/`end` contract and no silent real→mock downgrade 10. 14-4: Events endpoint only if the owner explicitly keeps it in M14

**Phase 3: Frontend** 11. 14-11: `run.Created` SSE listener (quick win) 12. 14-10: Dashboard per-card error states (quick win) 13. 14-8: Monitoring tab with headlessui Tabs + PositionsTable + AccountCard 14. 14-9: Fill stream via `orders.PartiallyFilled` / `orders.Filled` invalidation

This ordering ensures each phase builds on the previous and no task is blocked.

---

---

# PART II — EXECUTION PLAN

> **Convention**: Each phase follows TDD red-green-refactor.
> Write tests FIRST → see them fail → implement → see them pass.
>
> **Branch**: `feature/m14-live-monitoring`

---

## 11. Pre-Flight Checklist

```bash
# 1. Backend tests pass
cd /weaver && python -m pytest tests/unit/ -x -q

# 2. Frontend tests pass
cd /weaver/haro && npx vitest run

# 3. TypeScript compiles
cd /weaver/haro && npx tsc --noEmit

# 4. Create branch
cd /weaver && git checkout -b feature/m14-live-monitoring
```

---

## 12. Implementation Order

```
Phase 0  Test Infrastructure
  conftest updates, factories, MSW handlers for new endpoints,
  and replacement of stale frontend assertions

Phase 1  Live Fill Backbone & Schema Foundation
  14-6 migration → Alpaca trade activities client → Veda reconciliation,
  persistence, and partial/full fill events → RunManager task lifecycle → 14-7

Phase 2  Backend Endpoints  (14-3 → 14-1 → 14-2 → 14-5)
  account → positions → fills → candles

Phase 3  Frontend Quick Wins  (14-11 → 14-10)
  run.Created SSE → dashboard per-card errors

Phase 4  Frontend Feature  (14-8 → 14-9)
  monitoring tab → fill stream
```

Rationale:

- Phase 0 ensures all test infrastructure is ready and removes assertions that
  are no longer correct after the UI contract changes.
- Phase 1 establishes the missing live fill backbone before any route or UI is
  allowed to assume that fills exist for live/paper runs.
- Phase 2 builds all backend endpoints in dependency order.
- Phase 3 clears two independent, small frontend tasks.
- Phase 4 builds the monitoring tab consuming all new endpoints and event flows.

---

## 12a. Phase 0 — Test Infrastructure Updates

### 12a.1 Backend: GLaDOS Conftest Updates

**`tests/unit/glados/conftest.py`** — The `client` fixture must expose a
mock `VedaService` for new route tests that require it.

No structural change needed: the existing `app.state.veda_service = None`
pattern is correct. Individual test classes will inject a mock `VedaService`
when needed, following the pattern in `test_orders.py`.

### 12a.2 Backend: New Test Factories

**`tests/factories/orders.py`** — add helper functions for creating test
position and fill data:

```python
def create_sample_position(
    symbol: str = "AAPL",
    qty: str = "100",
    side: str = "long",
    avg_entry_price: str = "150.00",
    market_value: str = "15500.00",
    unrealized_pnl: str = "500.00",
    unrealized_pnl_percent: str = "3.33",
) -> dict[str, str]:
    """Create a sample position dict for test assertions."""
    return {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "avg_entry_price": avg_entry_price,
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_percent": unrealized_pnl_percent,
    }


def create_sample_account_info(
    account_id: str = "test-account-001",
    buying_power: str = "50000.00",
    cash: str = "25000.00",
    portfolio_value: str = "75000.00",
    currency: str = "USD",
    account_status: str = "ACTIVE",
) -> dict[str, str]:
    """Create a sample account info dict for test assertions."""
    return {
        "account_id": account_id,
        "buying_power": buying_power,
        "cash": cash,
        "portfolio_value": portfolio_value,
        "currency": currency,
        "status": account_status,
    }
```

### 12a.3 Frontend: MSW Handlers for New Endpoints

**`haro/tests/mocks/handlers.ts`** — add handlers for the new M14 endpoints:

```typescript
// M14: Account endpoint
http.get("/api/v1/account", () => {
  return HttpResponse.json({
    account_id: "test-account-001",
    buying_power: "50000.00",
    cash: "25000.00",
    portfolio_value: "75000.00",
    currency: "USD",
    status: "ACTIVE",
  });
}),

// M14: Positions endpoint
http.get("/api/v1/account/positions", () => {
  return HttpResponse.json({
    items: [
      {
        symbol: "AAPL",
        qty: "100",
        side: "long",
        avg_entry_price: "150.00",
        market_value: "15500.00",
        unrealized_pnl: "500.00",
        unrealized_pnl_percent: "3.33",
      },
    ],
  });
}),

// M14: Fills endpoint
http.get("/api/v1/runs/:runId/fills", () => {
  return HttpResponse.json({
    items: [
      {
        id: "fill-001",
        order_id: "order-001",
        symbol: "AAPL",
        price: "150.25",
        quantity: "100",
        side: "buy",
        commission: "1.00",
        filled_at: "2026-04-07T10:30:00Z",
      },
    ],
    total: 1,
  });
}),
```

### 12a.4 Frontend: New TypeScript Interfaces

**`haro/src/api/types.ts`** — add new M14 types:

```typescript
// M14: Position (account-scoped)
export interface Position {
  symbol: string;
  qty: string;
  side: "long" | "short";
  avg_entry_price: string;
  market_value: string;
  unrealized_pnl: string;
  unrealized_pnl_percent: string;
}

export interface PositionListResponse {
  items: Position[];
}

// M14: Account info
export interface AccountInfo {
  account_id: string;
  buying_power: string;
  cash: string;
  portfolio_value: string;
  currency: string;
  status: string;
}

// M14: Fill record
export interface Fill {
  id: string;
  order_id: string;
  symbol: string | null;
  price: string;
  quantity: string;
  side: string;
  commission: string | null;
  filled_at: string;
}

export interface FillListResponse {
  items: Fill[];
  total: number;
}
```

Also add `cancelled_at` to the existing `Order` interface:

```typescript
export interface Order {
  // ... existing fields ...
  cancelled_at?: string; // M14-7
}
```

---

## 13. Phase 1 — Live Fill Backbone & Schema Foundation

### 13.1 Foundation Prerequisite: Live Fill Reconciliation + Event Chain

**Decision**: D-14-2A 🔒 Option A — Alpaca account activities polling via the
existing trading account, not a new broker trade-event SSE client.

> This is the explicit gap uncovered during plan review. Until this backbone
> exists, live/paper runs can place orders, but they do not automatically
> persist fills or emit `orders.PartiallyFilled` / `orders.Filled`.

**Files to modify**:

| File                                             | What                                                                                                                     |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `src/veda/interfaces.py`                         | Add normalized trade-activity model + `list_trade_activities()` contract                                                 |
| `src/veda/adapters/alpaca_adapter.py`            | Implement authenticated `GET /v2/account/activities/FILL` mapping via `httpx`                                            |
| `src/veda/veda_service.py`                       | Add one-shot reconciliation helper, fill persistence, and fill-event emission; hydrate persisted `symbol` / `commission` |
| `src/glados/services/run_manager.py`             | Accept optional `veda_service`, add `background_tasks` to `RunContext`, start/cancel live reconciler tasks               |
| `src/glados/app.py`                              | Pass `veda_service` into `RunManager`                                                                                    |
| `tests/unit/veda/test_alpaca_adapter.py`         | Add account-activities parsing tests                                                                                     |
| `tests/unit/veda/test_fill_persistence.py`       | Extend from wiring tests to reconciliation + dedupe                                                                      |
| `tests/unit/veda/test_live_order_flow.py`        | Assert partial/full fill events are emitted                                                                              |
| `tests/unit/glados/services/test_run_manager.py` | Assert live reconciler task starts and is cancelled during cleanup                                                       |
| `tests/factories/runs.py`                        | Update `create_run_manager_with_deps(...)` for the new constructor argument                                              |

#### 13.1.1 Tests (RED)

Use the existing test files rather than inventing a parallel test tree.

**`tests/unit/veda/test_alpaca_adapter.py`** — add focused mapping tests for
account-activities payloads:

```python
async def test_list_trade_activities_maps_partial_fill_payload(...) -> None:
  activities = await adapter.list_trade_activities(after=start)
  activity = activities[0]
  assert activity.activity_id == "20220304135420898::2b9e..."
  assert activity.order_id == "cddf433b-1a41-497d-ae31-50b1fee56fff"
  assert activity.symbol == "AMZN"
  assert activity.activity_type == "partial_fill"
  assert activity.order_status == OrderStatus.PARTIALLY_FILLED

async def test_list_trade_activities_maps_fill_payload(...) -> None:
  activities = await adapter.list_trade_activities(after=start)
  assert activities[-1].activity_type == "fill"
  assert activities[-1].order_status == OrderStatus.FILLED
```

**`tests/unit/veda/test_fill_persistence.py`** — extend the existing suite from
simple save/get wiring into real reconciliation behavior:

```python
async def test_reconcile_run_fills_once_persists_new_fill(...) -> None:
  updated_after = await service.reconcile_run_fills_once(
    run_id="run-001",
    after=datetime(2026, 4, 7, 10, 0, tzinfo=UTC),
  )

  mock_fill_repo.save.assert_awaited_once()
  saved_fill = mock_fill_repo.save.await_args.args[0]
  assert saved_fill.id == "activity-001"
  assert saved_fill.exchange_fill_id == "activity-001"
  assert saved_fill.symbol == "AAPL"
  assert saved_fill.commission is None
  assert updated_after >= datetime(2026, 4, 7, 10, 30, tzinfo=UTC)

async def test_reconcile_run_fills_once_skips_duplicate_activity(...) -> None:
  mock_fill_repo.list_by_order.return_value = [
    FillRecord(id="activity-001", order_id="order-001", ...),
  ]

  await service.reconcile_run_fills_once(run_id="run-001", after=start)
  mock_fill_repo.save.assert_not_awaited()
```

**`tests/unit/veda/test_live_order_flow.py`** — assert event emission,
including partial fills:

```python
async def test_reconcile_emits_partially_filled_event(...) -> None:
  await service.reconcile_run_fills_once(run_id="run-123", after=start)
  envelope = mock_event_log.append.await_args_list[0].args[0]
  assert envelope.type == "orders.PartiallyFilled"

async def test_reconcile_emits_filled_event(...) -> None:
  await service.reconcile_run_fills_once(run_id="run-123", after=start)
  emitted_types = [call.args[0].type for call in mock_event_log.append.await_args_list]
  assert "orders.Filled" in emitted_types
```

**`tests/unit/glados/services/test_run_manager.py`** — the lifecycle tests must
cover the new long-lived poller explicitly:

```python
async def test_start_live_registers_fill_reconciler_background_task(...) -> None:
  await run_manager.start(run.id)
  ctx = run_manager._run_contexts[run.id]
  assert len(ctx.background_tasks) == 1

async def test_cleanup_cancels_background_tasks_before_pending_tasks(...) -> None:
  await run_manager.start(run.id)
  ctx = run_manager._run_contexts[run.id]
  background_tasks = set(ctx.background_tasks)
  await run_manager.stop(run.id)
  assert all(task.cancelled() or task.done() for task in background_tasks)
```

#### 13.1.2 Implement (GREEN)

**`src/veda/interfaces.py`** — add a normalized trade-activity model and a new
adapter contract:

```python
@dataclass(frozen=True)
class TradeActivity:
  activity_id: str
  order_id: str
  symbol: str
  side: OrderSide
  qty: Decimal
  price: Decimal
  transaction_time: datetime
  leaves_qty: Decimal
  cum_qty: Decimal
  order_status: OrderStatus
  activity_type: str  # "partial_fill" | "fill"

@abstractmethod
async def list_trade_activities(
  self,
  after: datetime,
  until: datetime | None = None,
  page_size: int = 100,
) -> list[TradeActivity]:
  ...
```

**`src/veda/adapters/alpaca_adapter.py`** — implement
`list_trade_activities()` using the trading account endpoint, not Broker API
credentials:

```python
base_url = self.PAPER_TRADING_URL if self._paper else self.LIVE_TRADING_URL
url = f"{base_url}/v2/account/activities/FILL"

async with httpx.AsyncClient(timeout=10.0) as client:
  response = await client.get(
    url,
    headers={
      "APCA-API-KEY-ID": self._api_key,
      "APCA-API-SECRET-KEY": self._api_secret,
    },
    params={
      "after": after.isoformat(),
      "until": until.isoformat() if until else None,
      "direction": "asc",
      "page_size": page_size,
    },
  )
```

Map these fields exactly: `id`, `order_id`, `symbol`, `side`, `qty`, `price`,
`transaction_time`, `leaves_qty`, `cum_qty`, `order_status`, `type`.

**`src/veda/veda_service.py`** — add a one-shot reconciliation helper instead
of burying the whole algorithm inside RunManager:

```python
async def reconcile_run_fills_once(self, run_id: str, after: datetime) -> datetime:
  """Poll broker trade activities, persist new fills, emit fill events, and
  return the next cursor timestamp."""
```

Implementation rules:

1. Load persisted orders for `run_id` and index them by `exchange_order_id`.
2. Fetch trade activities in ascending order from the adapter.
3. Ignore activities whose `order_id` does not map to this run; that is normal
   when the paper account has unrelated activity.
4. Persist new fills with `id = activity.activity_id` and
   `exchange_fill_id = activity.activity_id` for idempotency.
5. Persist `symbol = activity.symbol` and `commission = None` when Alpaca does
   not provide a commission.
6. Emit `orders.PartiallyFilled` for `activity_type == "partial_fill"` and
   `orders.Filled` for `activity_type == "fill"`.
7. Call `sync_order(client_order_id)` after a matched activity so the order's
   aggregate status / filled quantities stay aligned.

For cursor safety, use a small overlap window on each poll (for example, query
from `cursor - 2s`) and rely on the canonical activity ID for dedupe. This is
safer than assuming Alpaca activity timestamps are unique to the microsecond.

**`src/glados/services/run_manager.py`** — the poller must not live inside
`pending_tasks`. Add a separate set:

```python
@dataclass
class RunContext:
  greta: GretaService | None
  runner: StrategyRunner
  clock: BaseClock
  pending_tasks: set[asyncio.Task[Any]] = field(default_factory=set)
  background_tasks: set[asyncio.Task[Any]] = field(default_factory=set)
```

Then:

- add `veda_service: VedaService | None = None` to `RunManager.__init__`,
- when `_start_live()` succeeds and `veda_service` is available, create a
  background task for the reconciliation loop and store it in
  `ctx.background_tasks`,
- in `_cleanup_run_context()`, cancel and await `background_tasks` **before**
  draining `pending_tasks`.

This ordering is critical. The current `stop()` flow calls cleanup before the
run status is flipped to `STOPPED`, so a long-lived loop that waits on status
changes will hang. Explicit task cancellation avoids that trap.

**`src/glados/app.py`** — pass `veda_service` into `RunManager` so live/paper
runtime wiring owns the poller lifecycle.

---

### 13.2 Task 14-6: FillRecord Migration (`commission` + `symbol`)

**Decision**: D-14-6 🔒 Option A — nullable columns.

> `FillRecord` currently has: `id`, `order_id`, `price`, `quantity`, `side`,
> `filled_at`, `exchange_fill_id`. Both `commission` and `symbol` are missing.
> The domain model `Fill` in `veda/models.py` has `commission` but not `symbol`.

**Files to modify**:

| File                  | What                                                  |
| --------------------- | ----------------------------------------------------- |
| `src/walle/models.py` | Add `commission` and `symbol` columns to `FillRecord` |
| `src/veda/models.py`  | Add `symbol` field to `Fill` dataclass                |
| Alembic migration     | New migration for the two columns                     |

#### 13.2.1 Tests (RED)

**`tests/unit/walle/test_fill_repository.py`** — add to `TestFillRecordModel`:

```python
def test_has_commission_column(self) -> None:
    """FillRecord has commission column (M14-6)."""
    mapper = inspect(FillRecord)
    column_names = {c.key for c in mapper.columns}
    assert "commission" in column_names

def test_has_symbol_column(self) -> None:
    """FillRecord has symbol column (M14-6)."""
    mapper = inspect(FillRecord)
    column_names = {c.key for c in mapper.columns}
    assert "symbol" in column_names

def test_commission_is_nullable(self) -> None:
    """commission column allows NULL for backward compat."""
    table = cast(Table, FillRecord.__table__)
    col = table.c.commission
    assert col.nullable is True

def test_symbol_is_nullable(self) -> None:
    """symbol column allows NULL for backward compat."""
    table = cast(Table, FillRecord.__table__)
    col = table.c.symbol
    assert col.nullable is True
```

**`tests/unit/veda/test_models.py`** — add:

```python
def test_fill_has_symbol_field(self) -> None:
    """Fill dataclass has symbol field (M14-6)."""
    fill = Fill(
        id="f1", order_id="o1", qty=Decimal("1.0"),
        price=Decimal("100.0"), commission=Decimal("0.5"),
        timestamp=datetime.now(UTC), symbol="AAPL",
    )
    assert fill.symbol == "AAPL"

def test_fill_symbol_defaults_to_none(self) -> None:
    """Fill symbol defaults to None for backward compat."""
    fill = Fill(
        id="f1", order_id="o1", qty=Decimal("1.0"),
        price=Decimal("100.0"), commission=Decimal("0.5"),
        timestamp=datetime.now(UTC),
    )
    assert fill.symbol is None
```

```bash
python -m pytest tests/unit/walle/test_fill_repository.py::TestFillRecordModel::test_has_commission_column -x
# expect FAILED — column does not exist
```

#### 13.2.2 Implement (GREEN)

**`src/walle/models.py`** — add to `FillRecord` class, after `exchange_fill_id`:

```python
commission: Mapped[Decimal | None] = mapped_column(
    Numeric(18, 8), nullable=True
)
symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

**`src/veda/models.py`** — add to `Fill` dataclass, after `timestamp`:

```python
symbol: str | None = None
```

**`src/veda/veda_service.py`** — update `_hydrate_fills()` so persisted M14
fields actually flow back into the domain model:

```python
Fill(
  id=record.id,
  order_id=record.order_id,
  qty=record.quantity,
  price=record.price,
  commission=record.commission or Decimal("0"),
  timestamp=record.filled_at,
  symbol=record.symbol,
)
```

**Alembic migration**:

```bash
cd /weaver && alembic revision --autogenerate -m "add commission and symbol to fills"
```

Review the generated migration, then:

```bash
# Apply against dev DB (if available)
cd /weaver && alembic upgrade head
```

```bash
python -m pytest tests/unit/walle/test_fill_repository.py -x -q
python -m pytest tests/unit/veda/test_models.py -x -q
# expect PASS
```

---

### 13.3 Task 14-7: `cancelled_at` on OrderResponse

**No decision needed** — schema alignment fix.

> DB model `VedaOrder` has `cancelled_at`. Domain model `OrderState` has
> `cancelled_at`. `OrderResponse` schema and frontend `Order` type are missing it.

**Files to modify**:

| File                          | What                                         |
| ----------------------------- | -------------------------------------------- |
| `src/glados/schemas.py`       | Add `cancelled_at` to `OrderResponse`        |
| `src/glados/routes/orders.py` | Map `cancelled_at` in `_state_to_response()` |
| `haro/src/api/types.ts`       | Add `cancelled_at` to `Order` interface      |

#### 13.3.1 Tests (RED)

**`tests/unit/glados/test_schemas.py`** — add:

```python
def test_order_response_has_cancelled_at(self) -> None:
    """OrderResponse includes cancelled_at field (M14-7)."""
    from src.glados.schemas import OrderResponse
    fields = OrderResponse.model_fields
    assert "cancelled_at" in fields
```

**`tests/unit/glados/routes/test_orders.py`** — add to or create a test
class for Veda-backed order responses:

```python
def test_order_response_includes_cancelled_at(self, client: TestClient) -> None:
    """Order response JSON includes cancelled_at (M14-7)."""
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock

    mock_veda = AsyncMock()
    order_state = _make_order_state("ord-1")
    order_state.cancelled_at = datetime(2026, 4, 7, 12, 0, 0, tzinfo=UTC)
    mock_veda.list_orders.return_value = [order_state]
    client.app.state.veda_service = mock_veda

    response = client.get("/api/v1/orders")
    data = response.json()
    assert data["items"][0]["cancelled_at"] is not None

    client.app.state.veda_service = None
```

```bash
python -m pytest tests/unit/glados/test_schemas.py::test_order_response_has_cancelled_at -x
# expect FAILED
```

#### 13.3.2 Implement (GREEN)

**`src/glados/schemas.py`** — add to `OrderResponse`, after `filled_at`:

```python
cancelled_at: datetime | None = None
```

**`src/glados/routes/orders.py`** — in `_state_to_response()`, add:

```python
cancelled_at=state.cancelled_at,
```

**`haro/src/api/types.ts`** — add to `Order` interface, after `filled_at?`:

```typescript
cancelled_at?: string;
```

```bash
python -m pytest tests/unit/glados/test_schemas.py -x -q
python -m pytest tests/unit/glados/routes/test_orders.py -x -q
# expect PASS
```

---

## 14. Phase 2 — Backend Endpoints

### 14.1 Task 14-3: Account Endpoint

**Decision**: D-14-3 🔒 Option A — Global `GET /api/v1/account`.

> `VedaService.get_account()` returns `AccountInfo` via
> `ExchangeAdapter.get_account()`. No REST route exists.

**Files to create/modify**:

| File                                       | What                         |
| ------------------------------------------ | ---------------------------- |
| `src/glados/schemas.py`                    | Add `AccountResponse` schema |
| `src/glados/routes/account.py`             | **New file** — account route |
| `src/glados/app.py`                        | Include account router       |
| `tests/unit/glados/routes/test_account.py` | **New file** — tests         |

#### 14.1.1 Tests (RED)

**`tests/unit/glados/routes/test_account.py`** (new file):

```python
"""
Tests for Account Endpoint

M14-3: GET /api/v1/account
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.veda.models import AccountInfo


class TestAccountEndpoint:
    """Tests for GET /api/v1/account."""

    def test_returns_503_when_veda_not_configured(
        self, client: TestClient
    ) -> None:
        """Account endpoint returns 503 when VedaService is None."""
        response = client.get("/api/v1/account")
        assert response.status_code == 503

    def test_returns_200_with_account_info(
        self, client: TestClient
    ) -> None:
        """Account endpoint returns account info from VedaService."""
        mock_veda = AsyncMock()
        mock_veda.get_account.return_value = AccountInfo(
            account_id="PA-001",
            buying_power=Decimal("50000"),
            cash=Decimal("25000"),
            portfolio_value=Decimal("75000"),
            currency="USD",
            status="ACTIVE",
        )
        client.app.state.veda_service = mock_veda

        response = client.get("/api/v1/account")
        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == "PA-001"
        assert data["buying_power"] == "50000"
        assert data["portfolio_value"] == "75000"
        assert data["currency"] == "USD"
        assert data["status"] == "ACTIVE"

        client.app.state.veda_service = None

    def test_response_has_all_fields(self, client: TestClient) -> None:
        """Account response includes all AccountInfo fields."""
        mock_veda = AsyncMock()
        mock_veda.get_account.return_value = AccountInfo(
            account_id="PA-001",
            buying_power=Decimal("50000"),
            cash=Decimal("25000"),
            portfolio_value=Decimal("75000"),
            currency="USD",
            status="ACTIVE",
        )
        client.app.state.veda_service = mock_veda

        response = client.get("/api/v1/account")
        data = response.json()
        expected_fields = {
            "account_id", "buying_power", "cash",
            "portfolio_value", "currency", "status",
        }
        assert expected_fields == set(data.keys())

        client.app.state.veda_service = None
```

```bash
python -m pytest tests/unit/glados/routes/test_account.py -x
# expect FAILED — 404 (route doesn't exist)
```

#### 14.1.2 Implement (GREEN)

**`src/glados/schemas.py`** — add:

```python
class AccountResponse(BaseModel):
    """Account information response."""
    account_id: str
    buying_power: str
    cash: str
    portfolio_value: str
    currency: str
    status: str
```

**`src/glados/routes/account.py`** (new file):

```python
"""
Account Routes

M14-3: REST endpoint for account information.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.glados.dependencies import get_veda_service
from src.glados.schemas import AccountResponse
from src.veda import VedaService

router = APIRouter(prefix="/api/v1/account", tags=["account"])


def _require_veda_service(
    veda_service: VedaService | None = Depends(get_veda_service),
) -> VedaService:
    if veda_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trading service not configured",
        )
    return veda_service


@router.get("", response_model=AccountResponse)
async def get_account(
    veda_service: VedaService = Depends(_require_veda_service),
) -> AccountResponse:
    """Get account information from exchange adapter."""
    account = await veda_service.get_account()
    return AccountResponse(
        account_id=account.account_id,
        buying_power=str(account.buying_power),
        cash=str(account.cash),
        portfolio_value=str(account.portfolio_value),
        currency=account.currency,
        status=account.status,
    )
```

**`src/glados/app.py`** — add import and include:

```python
from src.glados.routes.account import router as account_router
# ... in router registration:
app.include_router(account_router)
```

```bash
python -m pytest tests/unit/glados/routes/test_account.py -x -q
# expect PASS
```

---

### 14.2 Task 14-1: Positions Endpoint

**Decision**: D-14-1 🔒 Option B (account-scoped), D-14-1B 🔒 Option A
(`/account/positions` canonical).

> `VedaService.get_positions()` delegates to `PositionTracker.get_all_positions()`,
> which returns in-memory data. `ExchangeAdapter.get_positions()` fetches
> real account positions from Alpaca. For M14, the canonical endpoint calls
> `ExchangeAdapter.get_positions()` directly via `VedaService`.
>
> **Gap**: `VedaService.get_positions()` currently calls
> `self._position_tracker.get_all_positions()` (in-memory), not the adapter.
> For M14 account-scoped semantics, we need a new method or direct adapter
> access.

**Approach**: Add `get_exchange_positions()` method to `VedaService` that
delegates to `self._adapter.get_positions()`. The existing `get_positions()`
stays as-is for future run-scoped use (M16).

**Files to create/modify**:

| File                                             | What                                           |
| ------------------------------------------------ | ---------------------------------------------- |
| `src/veda/veda_service.py`                       | Add `get_exchange_positions()` method          |
| `src/glados/schemas.py`                          | Add `PositionResponse`, `PositionListResponse` |
| `src/glados/routes/account.py`                   | Add positions sub-route                        |
| `tests/unit/glados/routes/test_account.py`       | Add positions tests                            |
| `tests/unit/veda/test_veda_service_positions.py` | **New** — VedaService adapter delegate test    |

#### 14.2.1 Tests (RED)

**`tests/unit/veda/test_veda_service_positions.py`** (new file):

```python
"""
Tests for VedaService exchange position delegation.

M14-1: Account-scoped positions from ExchangeAdapter.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.veda.models import Position, PositionSide


class TestVedaServiceExchangePositions:
    """VedaService.get_exchange_positions() delegates to adapter."""

    @pytest.fixture
    def mock_adapter(self) -> AsyncMock:
        adapter = AsyncMock()
        adapter.get_positions.return_value = [
            Position(
                symbol="AAPL",
                qty=Decimal("100"),
                side=PositionSide.LONG,
                avg_entry_price=Decimal("150.00"),
                market_value=Decimal("15500.00"),
                unrealized_pnl=Decimal("500.00"),
                unrealized_pnl_percent=Decimal("3.33"),
            ),
        ]
        return adapter

    @pytest.fixture
    def veda_service(self, mock_adapter: AsyncMock) -> "VedaService":
        from src.veda.veda_service import VedaService
        return VedaService(
            adapter=mock_adapter,
            event_log=AsyncMock(),
            repository=AsyncMock(),
            config=MagicMock(),
        )

    async def test_get_exchange_positions_delegates_to_adapter(
        self, veda_service, mock_adapter
    ) -> None:
        positions = await veda_service.get_exchange_positions()
        mock_adapter.get_positions.assert_called_once()
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"

    async def test_get_exchange_positions_returns_list(
        self, veda_service, mock_adapter
    ) -> None:
        mock_adapter.get_positions.return_value = []
        positions = await veda_service.get_exchange_positions()
        assert positions == []
```

**`tests/unit/glados/routes/test_account.py`** — add positions test class:

```python
class TestPositionsEndpoint:
    """Tests for GET /api/v1/account/positions."""

    def test_returns_503_when_veda_not_configured(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/account/positions")
        assert response.status_code == 503

    def test_returns_200_with_positions(self, client: TestClient) -> None:
        mock_veda = AsyncMock()
        mock_veda.get_exchange_positions.return_value = [
            Position(
                symbol="AAPL",
                qty=Decimal("100"),
                side=PositionSide.LONG,
                avg_entry_price=Decimal("150.00"),
                market_value=Decimal("15500.00"),
                unrealized_pnl=Decimal("500.00"),
                unrealized_pnl_percent=Decimal("3.33"),
            ),
        ]
        client.app.state.veda_service = mock_veda

        response = client.get("/api/v1/account/positions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        pos = data["items"][0]
        assert pos["symbol"] == "AAPL"
        assert pos["qty"] == "100"
        assert pos["side"] == "long"

        client.app.state.veda_service = None

    def test_returns_empty_list_when_no_positions(
        self, client: TestClient
    ) -> None:
        mock_veda = AsyncMock()
        mock_veda.get_exchange_positions.return_value = []
        client.app.state.veda_service = mock_veda

        response = client.get("/api/v1/account/positions")
        data = response.json()
        assert data["items"] == []

        client.app.state.veda_service = None
```

```bash
python -m pytest tests/unit/veda/test_veda_service_positions.py -x
# expect FAILED — no get_exchange_positions method
```

#### 14.2.2 Implement (GREEN)

**`src/veda/veda_service.py`** — add method after `get_account()`:

```python
async def get_exchange_positions(self) -> list[Position]:
    """Get all positions from the exchange adapter (account-scoped)."""
    return await self._adapter.get_positions()
```

**`src/glados/schemas.py`** — add:

```python
class PositionResponse(BaseModel):
    """Single position response."""
    symbol: str
    qty: str
    side: str
    avg_entry_price: str
    market_value: str
    unrealized_pnl: str
    unrealized_pnl_percent: str


class PositionListResponse(BaseModel):
    """List of positions response."""
    items: list[PositionResponse]
```

**`src/glados/routes/account.py`** — add positions route:

```python
from src.glados.schemas import AccountResponse, PositionListResponse, PositionResponse

@router.get("/positions", response_model=PositionListResponse)
async def get_positions(
    veda_service: VedaService = Depends(_require_veda_service),
) -> PositionListResponse:
    """Get account positions from exchange adapter."""
    positions = await veda_service.get_exchange_positions()
    return PositionListResponse(
        items=[
            PositionResponse(
                symbol=p.symbol,
                qty=str(p.qty),
                side=p.side.value,
                avg_entry_price=str(p.avg_entry_price),
                market_value=str(p.market_value),
                unrealized_pnl=str(p.unrealized_pnl),
                unrealized_pnl_percent=str(p.unrealized_pnl_percent),
            )
            for p in positions
        ]
    )
```

```bash
python -m pytest tests/unit/glados/routes/test_account.py -x -q
python -m pytest tests/unit/veda/test_veda_service_positions.py -x -q
# expect PASS
```

---

### 14.3 Task 14-2: Fills Endpoint

**Decision**: D-14-2 🔒 Option A — JOIN through orders table.

> `FillRepository` only has `list_by_order()`. We need `list_by_run_id()` that
> JOINs through `veda_orders` on `fills.order_id = veda_orders.id WHERE
veda_orders.run_id = :run_id`.
>
> **Important**: this phase assumes the Phase 1 reconciliation backbone already
> persists live fills. The route is not a substitute for live fill ingestion.

**Files to create/modify**:

| File                                        | What                                   |
| ------------------------------------------- | -------------------------------------- |
| `src/walle/repositories/fill_repository.py` | Add `list_by_run_id()` method          |
| `src/glados/schemas.py`                     | Add `FillResponse`, `FillListResponse` |
| `src/glados/routes/fills.py`                | **New file** — fills route             |
| `src/glados/app.py`                         | Include fills router                   |
| `tests/unit/walle/test_fill_repository.py`  | Add interface tests                    |
| `tests/unit/glados/routes/test_fills.py`    | **New file** — route tests             |

#### 14.3.1 Tests (RED)

**`tests/unit/walle/test_fill_repository.py`** — add to
`TestFillRepositoryInterface`:

```python
def test_repository_has_list_by_run_id_method(self) -> None:
    """FillRepository has async list_by_run_id() method (M14-2)."""
    from src.walle.repositories.fill_repository import FillRepository

    assert hasattr(FillRepository, "list_by_run_id")
    assert callable(FillRepository.list_by_run_id)
    assert py_inspect.iscoroutinefunction(FillRepository.list_by_run_id)
```

**`tests/unit/glados/routes/test_fills.py`** (new file):

```python
"""
Tests for Fills Endpoint

M14-2: GET /api/v1/runs/{run_id}/fills
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.walle.models import FillRecord


class TestFillsEndpoint:
    """Tests for GET /api/v1/runs/{run_id}/fills."""

    def test_returns_200(self, client: TestClient) -> None:
        """Fills endpoint returns 200."""
        mock_fill_repo = AsyncMock()
        mock_fill_repo.list_by_run_id.return_value = []
        client.app.state.fill_repository = mock_fill_repo

        response = client.get("/api/v1/runs/run-1/fills")
        assert response.status_code == 200

        client.app.state.fill_repository = None

    def test_returns_fills_for_run(self, client: TestClient) -> None:
        """Returns fills joined through orders for a specific run."""
        mock_fill_repo = AsyncMock()
        mock_fill_repo.list_by_run_id.return_value = [
            FillRecord(
                id="fill-001",
                order_id="order-001",
                price=Decimal("150.25"),
                quantity=Decimal("100"),
                side="buy",
                filled_at=datetime(2026, 4, 7, 10, 30, tzinfo=UTC),
                commission=Decimal("1.00"),
                symbol="AAPL",
            ),
        ]
        client.app.state.fill_repository = mock_fill_repo

        response = client.get("/api/v1/runs/run-1/fills")
        data = response.json()
        assert len(data["items"]) == 1
        fill = data["items"][0]
        assert fill["symbol"] == "AAPL"
        assert fill["price"] == "150.25"
        assert fill["side"] == "buy"

        client.app.state.fill_repository = None

    def test_passes_run_id_to_repository(
        self, client: TestClient
    ) -> None:
        """Fills endpoint passes run_id to repository."""
        mock_fill_repo = AsyncMock()
        mock_fill_repo.list_by_run_id.return_value = []
        client.app.state.fill_repository = mock_fill_repo

        client.get("/api/v1/runs/test-run-123/fills")
        mock_fill_repo.list_by_run_id.assert_called_once_with("test-run-123")

        client.app.state.fill_repository = None

    def test_returns_503_when_repository_not_available(
        self, client: TestClient
    ) -> None:
        """Fills endpoint returns 503 when fill repository is not configured."""
        client.app.state.fill_repository = None
        response = client.get("/api/v1/runs/run-1/fills")
        assert response.status_code == 503
```

```bash
python -m pytest tests/unit/walle/test_fill_repository.py::TestFillRepositoryInterface::test_repository_has_list_by_run_id_method -x
# expect FAILED
```

#### 14.3.2 Implement (GREEN)

**`src/walle/repositories/fill_repository.py`** — add method:

```python
async def list_by_run_id(self, run_id: str) -> list[FillRecord]:
    """List all fills for a run via JOIN on veda_orders."""
    from src.walle.models import VedaOrder

    async with self._session_factory() as session:
        stmt = (
            select(FillRecord)
            .join(VedaOrder, FillRecord.order_id == VedaOrder.id)
            .where(VedaOrder.run_id == run_id)
            .order_by(FillRecord.filled_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
```

**`src/glados/schemas.py`** — add:

```python
class FillResponse(BaseModel):
    """Single fill response."""
    id: str
    order_id: str
    symbol: str | None = None
    price: str
    quantity: str
    side: str
    commission: str | None = None
    filled_at: datetime
    exchange_fill_id: str | None = None


class FillListResponse(BaseModel):
    """List of fills response."""
    items: list[FillResponse]
    total: int
```

**`src/glados/routes/fills.py`** (new file):

```python
"""
Fills Routes

M14-2: REST endpoint for run-scoped fills.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Request

from src.glados.schemas import FillListResponse, FillResponse

router = APIRouter(prefix="/api/v1/runs", tags=["fills"])


def _get_fill_repository(request: Request):
    repo = getattr(request.app.state, "fill_repository", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fill repository not configured",
        )
    return repo


@router.get("/{run_id}/fills", response_model=FillListResponse)
async def get_fills_for_run(
    run_id: str,
    fill_repository=Depends(_get_fill_repository),
) -> FillListResponse:
    """Get all fills for a specific run (via JOIN on orders)."""
    fills = await fill_repository.list_by_run_id(run_id)
    return FillListResponse(
        items=[
            FillResponse(
                id=f.id,
                order_id=f.order_id,
                symbol=f.symbol,
                price=str(f.price),
                quantity=str(f.quantity),
                side=f.side,
                commission=str(f.commission) if f.commission else None,
                filled_at=f.filled_at,
                exchange_fill_id=f.exchange_fill_id,
            )
            for f in fills
        ],
        total=len(fills),
    )
```

**`src/glados/app.py`** — add import and include:

```python
from src.glados.routes.fills import router as fills_router
app.include_router(fills_router)
```

**`src/glados/dependencies.py`** — add:

```python
def get_fill_repository(request: Request):
    return getattr(request.app.state, "fill_repository", None)
```

**`src/glados/app.py`** lifespan — ensure `fill_repository` is set on
`app.state`. Check if it's already created during VedaService setup. If
not, create it from the session factory:

```python
app.state.fill_repository = FillRepository(session_factory=database.session_factory)
```

```bash
python -m pytest tests/unit/walle/test_fill_repository.py -x -q
python -m pytest tests/unit/glados/routes/test_fills.py -x -q
# expect PASS
```

---

### 14.4 Task 14-5: Candles Wired to Real Data

**Decision**: D-14-5 🔒 Option A (Alpaca swap), D-14-5B 🔒 Option A (keep
existing URL), D-14-5C 🔒 Option A (add `start`/`end` now).

> Current: `GET /api/v1/candles` uses `MockMarketDataService`.
> Target: swap to `ExchangeAdapter.get_bars()`, add `start`/`end` params,
> keep `limit` as optional, and derive a deterministic real-data window when
> `start` is omitted.

**Files to modify**:

| File                                       | What                                                           |
| ------------------------------------------ | -------------------------------------------------------------- |
| `src/glados/routes/candles.py`             | Replace mock dependency with VedaService adapter               |
| `src/glados/schemas.py`                    | Update `CandleResponse` if needed, update `CandleListResponse` |
| `tests/unit/glados/routes/test_candles.py` | Update tests for new params and real adapter                   |

#### 14.4.1 Tests (RED)

**`tests/unit/glados/routes/test_candles.py`** — update existing tests
and add new ones:

```python
class TestCandlesEndpointM14:
  """M14-5: Candles wired to real data with start/end contract."""

  def test_accepts_start_param(self, client: TestClient) -> None:
    """GET /candles accepts start datetime param."""
    response = client.get(
      "/api/v1/candles?symbol=AAPL&timeframe=1m"
      "&start=2026-04-01T09:30:00Z"
    )
    assert response.status_code in (200, 503)

  def test_accepts_end_param(self, client: TestClient) -> None:
    """GET /candles accepts end datetime param."""
    response = client.get(
      "/api/v1/candles?symbol=AAPL&timeframe=1m"
      "&start=2026-04-01T09:30:00Z&end=2026-04-01T16:00:00Z"
    )
    assert response.status_code in (200, 503)

  def test_returns_200_with_veda_service(self, client: TestClient) -> None:
    """Candles returns 200 when VedaService is configured."""
    from datetime import UTC, datetime
    from decimal import Decimal
    from unittest.mock import AsyncMock

    from src.veda.models import Bar

    mock_veda = AsyncMock()
    mock_veda.get_bars = AsyncMock(
      return_value=[
        Bar(
          symbol="AAPL",
          timestamp=datetime(2026, 4, 7, 10, 0, tzinfo=UTC),
          open=Decimal("150.00"),
          high=Decimal("151.00"),
          low=Decimal("149.50"),
          close=Decimal("150.75"),
          volume=Decimal("10000"),
          trade_count=500,
          vwap=Decimal("150.40"),
        ),
      ]
    )
    client.app.state.veda_service = mock_veda

    response = client.get(
      "/api/v1/candles?symbol=AAPL&timeframe=1m"
      "&start=2026-04-07T09:30:00Z"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["symbol"] == "AAPL"

    client.app.state.veda_service = None

  def test_uses_real_data_when_start_is_omitted(
    self, client: TestClient
  ) -> None:
    """VedaService path stays on real data even when start is omitted."""
    from datetime import UTC, datetime
    from decimal import Decimal
    from unittest.mock import AsyncMock

    from src.veda.models import Bar

    mock_veda = AsyncMock()
    mock_veda.get_bars = AsyncMock(
      return_value=[
        Bar(
          symbol="AAPL",
          timestamp=datetime(2026, 4, 7, 10, 0, tzinfo=UTC),
          open=Decimal("150.00"),
          high=Decimal("151.00"),
          low=Decimal("149.50"),
          close=Decimal("150.75"),
          volume=Decimal("10000"),
          trade_count=500,
          vwap=Decimal("150.40"),
        ),
      ]
    )
    client.app.state.veda_service = mock_veda

    response = client.get("/api/v1/candles?symbol=AAPL&timeframe=1m&limit=5")
    assert response.status_code == 200
    mock_veda.get_bars.assert_awaited_once()

    client.app.state.veda_service = None

    def test_falls_back_to_mock_when_no_veda(
        self, client: TestClient
    ) -> None:
        """When VedaService is None, candles still works via MockMarketDataService."""
        response = client.get(
            "/api/v1/candles?symbol=AAPL&timeframe=1m&limit=5"
        )
        assert response.status_code == 200
```

```bash
python -m pytest tests/unit/glados/routes/test_candles.py::TestCandlesEndpointM14 -x
# expect FAILED — start/end params not accepted
```

#### 14.4.2 Implement (GREEN)

**`src/glados/routes/candles.py`** — rewrite the route:

```python
"""
Candles Routes

REST endpoints for market data queries.
M14-5: Wired to real data source via ExchangeAdapter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query

from src.glados.dependencies import get_market_data_service, get_veda_service
from src.glados.schemas import CandleListResponse, CandleResponse
from src.glados.services.market_data_service import Candle, MockMarketDataService
from src.veda import VedaService

router = APIRouter(prefix="/api/v1/candles", tags=["candles"])


def _candle_to_response(candle: Candle) -> CandleResponse:
    """Convert internal Candle to CandleResponse."""
    return CandleResponse(
        symbol=candle.symbol,
        timeframe=candle.timeframe,
        timestamp=candle.timestamp,
        open=str(candle.open),
        high=str(candle.high),
        low=str(candle.low),
        close=str(candle.close),
        volume=str(candle.volume),
        trade_count=candle.trade_count,
    )


def _bar_to_response(bar, timeframe: str) -> CandleResponse:
    """Convert Veda Bar to CandleResponse."""
    return CandleResponse(
        symbol=bar.symbol,
        timeframe=timeframe,
        timestamp=bar.timestamp,
        open=str(bar.open),
        high=str(bar.high),
        low=str(bar.low),
        close=str(bar.close),
        volume=str(bar.volume),
        trade_count=bar.trade_count,
    )


def _timeframe_to_delta(timeframe: str) -> timedelta:
    mapping = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "1d": timedelta(days=1),
    }
    return mapping.get(timeframe, timedelta(minutes=1))


def _resolve_window(
    timeframe: str,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> tuple[datetime, datetime | None]:
    """Resolve a deterministic real-data window for chart queries."""
    resolved_end = end or datetime.now(UTC)
    if start is not None:
        return start, end
    return resolved_end - (_timeframe_to_delta(timeframe) * limit), resolved_end


@router.get("", response_model=CandleListResponse)
async def get_candles(
    symbol: str = Query(..., description="Trading symbol (e.g., AAPL)"),
    timeframe: str = Query(
        ..., description="Candle timeframe (e.g., 1m, 5m, 1h, 1d)"
    ),
    start: datetime | None = Query(
        default=None, description="Start datetime (RFC-3339)"
    ),
    end: datetime | None = Query(
        default=None, description="End datetime (RFC-3339)"
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    veda_service: VedaService | None = Depends(get_veda_service),
    market_data_service: MockMarketDataService = Depends(
        get_market_data_service
    ),
) -> CandleListResponse:
    """
    Get OHLCV candles.

    M14: Uses ExchangeAdapter when available, falls back to mock data.
    """
  if veda_service is not None:
    resolved_start, resolved_end = _resolve_window(
      timeframe=timeframe,
      start=start,
      end=end,
      limit=limit,
    )
    bars = await veda_service.get_bars(
      symbol=symbol,
      timeframe=timeframe,
      start=resolved_start,
      end=resolved_end,
      limit=limit,
    )
    return CandleListResponse(
      symbol=symbol,
      timeframe=timeframe,
      items=[_bar_to_response(b, timeframe) for b in bars],
    )
  else:
    candles = await market_data_service.get_candles(
      symbol=symbol,
      timeframe=timeframe,
      limit=limit,
    )
    return CandleListResponse(
      symbol=symbol,
      timeframe=timeframe,
      items=[_candle_to_response(c) for c in candles],
    )
```

**`src/veda/veda_service.py`** — add `get_bars()` method if it doesn't
exist:

```python
async def get_bars(
    self,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime | None = None,
    limit: int | None = None,
) -> list[Bar]:
    """Get historical bars from the exchange adapter."""
    return await self._adapter.get_bars(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        limit=limit,
    )
```

```bash
python -m pytest tests/unit/glados/routes/test_candles.py -x -q
# expect PASS (all old + new tests)
```

---

## 15. Phase 3 — Frontend Quick Wins

### 15.1 Task 14-11: SSE `run.Created` Listener

**No decision needed** — implementation pattern identical to existing events.

> `RunEvents.CREATED` is emitted by `RunManager.create()`. Frontend SSE hook
> does not handle `run.Created`.

**Files to modify**:

| File                                    | What                             |
| --------------------------------------- | -------------------------------- |
| `haro/src/hooks/useSSE.ts`              | Add `run.Created` event listener |
| `haro/tests/unit/hooks/useSSE.test.tsx` | Add test for `run.Created`       |

#### 15.1.1 Tests (RED)

**`haro/tests/unit/hooks/useSSE.test.tsx`** — add:

```typescript
it("handles run.Created event with query invalidation", () => {
  const { result } = renderHook(() => useSSE(), {
    wrapper: createWrapper(),
  });

  act(() => {
    MockEventSource.latest().simulateOpen();
  });

  act(() => {
    MockEventSource.latest().simulateEvent("run.Created", {
      run_id: "new-run",
    });
  });

  const notifications = useNotificationStore.getState().notifications;
  expect(notifications.length).toBeGreaterThan(0);
  expect(notifications[0].message).toContain("new-run");
});
```

```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useSSE.test.tsx
# expect FAILED — no run.Created handler
```

#### 15.1.2 Implement (GREEN)

**`haro/src/hooks/useSSE.ts`** — add after the `run.Error` handler block:

```typescript
eventSource.addEventListener("run.Created", (event: MessageEvent) => {
  const data = safeParse(event.data);
  const runId = data?.run_id ?? "unknown";
  queryClient.invalidateQueries({ queryKey: ["runs"] });
  addNotification({
    type: "info",
    message: `Run ${runId} created`,
  });
});
```

```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useSSE.test.tsx
# expect PASS
```

---

### 15.2 Task 14-10: Dashboard Per-Card Error States

**Decision**: D-14-10 🔒 Option B — per-card error states.

> Current: `const isError = runsQuery.isError` — only checks one of four
> queries. Dashboard should show per-card error indicators.

**Files to modify**:

| File                                       | What                       |
| ------------------------------------------ | -------------------------- |
| `haro/src/pages/Dashboard.tsx`             | Per-card error propagation |
| `haro/src/components/common/StatCard.tsx`  | Add `isError` prop variant |
| `haro/tests/unit/pages/Dashboard.test.tsx` | Add per-card error tests   |

#### 15.2.1 Tests (RED)

Before adding new assertions, delete or rewrite the old full-page
`dashboard-error` test. Per-card error states mean the dashboard no longer has
one aggregate error panel for every failure mode.

**`haro/tests/unit/pages/Dashboard.test.tsx`** — add:

```typescript
it("shows error on individual stat card when health query fails", async () => {
  server.use(
    http.get("/api/v1/healthz", () =>
      HttpResponse.json({ detail: "Service unavailable" }, { status: 503 }),
    ),
  );

  render(<Dashboard />);

  await waitFor(() => {
    const healthCard = screen.getByTestId("stat-card-system");
    expect(healthCard).toHaveAttribute("data-error", "true");
  });
});

it("still shows runs data when health query fails", async () => {
  server.use(
    http.get("/api/v1/healthz", () =>
      HttpResponse.json({ detail: "down" }, { status: 503 }),
    ),
  );

  render(<Dashboard />);

  await waitFor(() => {
    expect(screen.getByTestId("stat-card-total-runs")).toBeInTheDocument();
  });
});

it("shows error on runs card when runs query fails", async () => {
  server.use(
    http.get("/api/v1/runs", () =>
      HttpResponse.json({ detail: "error" }, { status: 500 }),
    ),
  );

  render(<Dashboard />);

  await waitFor(() => {
    const runsCards = screen.getAllByTestId(/stat-card/);
    const errorCards = runsCards.filter(
      (c) => c.getAttribute("data-error") === "true",
    );
    expect(errorCards.length).toBeGreaterThan(0);
  });
});
```

```bash
cd /weaver/haro && npx vitest run tests/unit/pages/Dashboard.test.tsx
# expect FAILED
```

#### 15.2.2 Implement (GREEN)

**`haro/src/components/common/StatCard.tsx`** — add `isError` prop:

```tsx
interface StatCardProps {
  // ... existing props
  isError?: boolean;
  "data-testid"?: string;
}

export function StatCard({ isError, ...props }: StatCardProps) {
  return (
    <div
      data-testid={props["data-testid"]}
      data-error={isError ? "true" : undefined}
      className={/* existing classes */}
    >
      {isError ? (
        <div className="text-red-400 text-sm">Unable to load</div>
      ) : (
        /* existing content */
      )}
    </div>
  );
}
```

**`haro/src/pages/Dashboard.tsx`** — replace aggregate error check with
per-card error props:

```tsx
// Remove: const isError = runsQuery.isError;
// Remove: aggregate error display block

// Pass isError to each StatCard:
<StatCard
  data-testid="stat-card-total-runs"
  isError={runsQuery.isError}
  // ...
/>
<StatCard
  data-testid="stat-card-active-runs"
  isError={activeRunsQuery.isError}
  // ...
/>
<StatCard
  data-testid="stat-card-orders"
  isError={ordersQuery.isError}
  // ...
/>
<StatCard
  data-testid="stat-card-system"
  isError={healthQuery.isError}
  // ...
/>
```

```bash
cd /weaver/haro && npx vitest run tests/unit/pages/Dashboard.test.tsx
# expect PASS
```

---

## 16. Phase 4 — Frontend Feature

### 16.1 Task 14-8: Monitoring Tab

**Decision**: D-14-8A 🔒 Option B (headlessui Tabs), D-14-8B 🔒 Option A
(polling), D-14-8C 🔒 Option A (simple table + card).

> The RunDetailPage needs a tabbed interface:
>
> - "Results" tab: existing backtest result content (mode=backtest, status=completed)
> - "Monitoring" tab: positions table + account card while active, plus recent fills
> - For stopped/completed live/paper runs, keep the Monitoring tab available for
>   historical fills, but disable live polling and show an explanatory note.

**Files to create/modify**:

| File                                                      | What                                          |
| --------------------------------------------------------- | --------------------------------------------- |
| `haro/src/api/account.ts`                                 | **New** — API functions for account/positions |
| `haro/src/api/fills.ts`                                   | **New** — API function for fills              |
| `haro/src/hooks/useAccount.ts`                            | **New** — hooks for account + positions       |
| `haro/src/hooks/useFills.ts`                              | **New** — hook for run fills                  |
| `haro/src/components/runs/PositionsTable.tsx`             | **New** — positions table                     |
| `haro/src/components/runs/AccountCard.tsx`                | **New** — account info card                   |
| `haro/src/components/runs/MonitoringTab.tsx`              | **New** — monitoring tab content              |
| `haro/src/pages/RunDetailPage.tsx`                        | Refactor to use headlessui Tabs               |
| `haro/tests/unit/components/runs/PositionsTable.test.tsx` | **New**                                       |
| `haro/tests/unit/components/runs/AccountCard.test.tsx`    | **New**                                       |
| `haro/tests/unit/pages/RunDetailPage.test.tsx`            | Update for tabs                               |
| `haro/tests/unit/hooks/useAccount.test.tsx`               | **New**                                       |

#### 16.1.1 API Layer

**`haro/src/api/account.ts`** (new file):

```typescript
import { get } from "./client";
import type { AccountInfo, PositionListResponse } from "./types";

export async function fetchAccount(): Promise<AccountInfo> {
  return get<AccountInfo>("/account");
}

export async function fetchPositions(): Promise<PositionListResponse> {
  return get<PositionListResponse>("/account/positions");
}
```

**`haro/src/api/fills.ts`** (new file):

```typescript
import { get } from "./client";
import type { FillListResponse } from "./types";

export async function fetchFills(runId: string): Promise<FillListResponse> {
  return get<FillListResponse>(`/runs/${runId}/fills`);
}
```

#### 16.1.2 Hooks

**`haro/src/hooks/useAccount.ts`** (new file):

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchAccount, fetchPositions } from "../api/account";

export const accountKeys = {
  all: ["account"] as const,
  info: () => [...accountKeys.all, "info"] as const,
  positions: () => [...accountKeys.all, "positions"] as const,
};

export function useAccount(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: accountKeys.info(),
    queryFn: fetchAccount,
    enabled: options?.enabled ?? true,
  });
}

export function usePositions(options?: {
  enabled?: boolean;
  refetchInterval?: number | false;
}) {
  return useQuery({
    queryKey: accountKeys.positions(),
    queryFn: fetchPositions,
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? false,
  });
}
```

**`haro/src/hooks/useFills.ts`** (new file):

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchFills } from "../api/fills";

export const fillKeys = {
  all: ["fills"] as const,
  byRun: (runId: string) => [...fillKeys.all, "run", runId] as const,
};

export function useFills(runId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: fillKeys.byRun(runId),
    queryFn: () => fetchFills(runId),
    enabled: (options?.enabled ?? true) && Boolean(runId),
  });
}
```

#### 16.1.3 Component Tests (RED)

**`haro/tests/unit/components/runs/PositionsTable.test.tsx`** (new file):

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "../../../utils";
import { PositionsTable } from "../../../../src/components/runs/PositionsTable";

const mockPositions = [
  {
    symbol: "AAPL",
    qty: "100",
    side: "long" as const,
    avg_entry_price: "150.00",
    market_value: "15500.00",
    unrealized_pnl: "500.00",
    unrealized_pnl_percent: "3.33",
  },
  {
    symbol: "MSFT",
    qty: "50",
    side: "long" as const,
    avg_entry_price: "380.00",
    market_value: "19250.00",
    unrealized_pnl: "250.00",
    unrealized_pnl_percent: "1.32",
  },
];

describe("PositionsTable", () => {
  it("renders table with position data", () => {
    render(<PositionsTable positions={mockPositions} />);
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("MSFT")).toBeInTheDocument();
  });

  it("shows column headers", () => {
    render(<PositionsTable positions={mockPositions} />);
    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("Qty")).toBeInTheDocument();
    expect(screen.getByText("Side")).toBeInTheDocument();
    expect(screen.getByText("Avg Entry")).toBeInTheDocument();
    expect(screen.getByText("Market Value")).toBeInTheDocument();
    expect(screen.getByText("P&L")).toBeInTheDocument();
  });

  it("shows empty state when no positions", () => {
    render(<PositionsTable positions={[]} />);
    expect(screen.getByTestId("positions-empty")).toBeInTheDocument();
  });

  it("has correct test id", () => {
    render(<PositionsTable positions={mockPositions} />);
    expect(screen.getByTestId("positions-table")).toBeInTheDocument();
  });

  it("renders P&L with color coding", () => {
    render(<PositionsTable positions={mockPositions} />);
    const pnlCells = screen.getAllByTestId(/position-pnl/);
    expect(pnlCells.length).toBe(2);
  });
});
```

**`haro/tests/unit/components/runs/AccountCard.test.tsx`** (new file):

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "../../../utils";
import { AccountCard } from "../../../../src/components/runs/AccountCard";

const mockAccount = {
  account_id: "PA-001",
  buying_power: "50000.00",
  cash: "25000.00",
  portfolio_value: "75000.00",
  currency: "USD",
  status: "ACTIVE",
};

describe("AccountCard", () => {
  it("renders account information", () => {
    render(<AccountCard account={mockAccount} />);
    expect(screen.getByTestId("account-card")).toBeInTheDocument();
  });

  it("shows portfolio value", () => {
    render(<AccountCard account={mockAccount} />);
    expect(screen.getByText(/75,000/)).toBeInTheDocument();
  });

  it("shows buying power", () => {
    render(<AccountCard account={mockAccount} />);
    expect(screen.getByText(/50,000/)).toBeInTheDocument();
  });

  it("shows cash", () => {
    render(<AccountCard account={mockAccount} />);
    expect(screen.getByText(/25,000/)).toBeInTheDocument();
  });

  it("shows account status", () => {
    render(<AccountCard account={mockAccount} />);
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<AccountCard account={null} isLoading />);
    expect(screen.getByTestId("account-card-loading")).toBeInTheDocument();
  });
});
```

#### 16.1.4 Components (GREEN)

**`haro/src/components/runs/PositionsTable.tsx`** (new file):

```tsx
import type { Position } from "../../api/types";

interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <div
        data-testid="positions-empty"
        className="bg-slate-800 rounded-lg border border-slate-700 p-8 text-center"
      >
        <p className="text-slate-400">No open positions</p>
      </div>
    );
  }

  return (
    <div
      data-testid="positions-table"
      className="bg-slate-800 rounded-lg border border-slate-700 overflow-x-auto"
    >
      <table className="w-full">
        <thead className="bg-slate-700/50">
          <tr>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Symbol
            </th>
            <th className="text-right px-6 py-3 text-sm font-medium text-slate-300">
              Qty
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Side
            </th>
            <th className="text-right px-6 py-3 text-sm font-medium text-slate-300">
              Avg Entry
            </th>
            <th className="text-right px-6 py-3 text-sm font-medium text-slate-300">
              Market Value
            </th>
            <th className="text-right px-6 py-3 text-sm font-medium text-slate-300">
              P&L
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {positions.map((pos) => {
            const pnl = parseFloat(pos.unrealized_pnl);
            const pnlColor =
              pnl > 0
                ? "text-green-400"
                : pnl < 0
                  ? "text-red-400"
                  : "text-slate-300";
            return (
              <tr key={pos.symbol} className="hover:bg-slate-700/30">
                <td className="px-6 py-4 text-sm font-mono text-slate-200">
                  {pos.symbol}
                </td>
                <td className="px-6 py-4 text-sm text-right text-slate-200">
                  {pos.qty}
                </td>
                <td className="px-6 py-4 text-sm text-slate-200">{pos.side}</td>
                <td className="px-6 py-4 text-sm text-right text-slate-200">
                  ${pos.avg_entry_price}
                </td>
                <td className="px-6 py-4 text-sm text-right text-slate-200">
                  ${pos.market_value}
                </td>
                <td
                  data-testid={`position-pnl-${pos.symbol}`}
                  className={`px-6 py-4 text-sm text-right ${pnlColor}`}
                >
                  {pnl >= 0 ? "+" : ""}
                  {pos.unrealized_pnl} ({pos.unrealized_pnl_percent}%)
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

**`haro/src/components/runs/AccountCard.tsx`** (new file):

```tsx
import type { AccountInfo } from "../../api/types";

interface AccountCardProps {
  account: AccountInfo | null;
  isLoading?: boolean;
}

function formatCurrency(value: string): string {
  return parseFloat(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function AccountCard({ account, isLoading }: AccountCardProps) {
  if (isLoading) {
    return (
      <div
        data-testid="account-card-loading"
        className="bg-slate-800 rounded-lg border border-slate-700 p-6 animate-pulse"
      >
        <div className="h-4 bg-slate-700 rounded w-1/3 mb-4" />
        <div className="grid grid-cols-3 gap-4">
          <div className="h-8 bg-slate-700 rounded" />
          <div className="h-8 bg-slate-700 rounded" />
          <div className="h-8 bg-slate-700 rounded" />
        </div>
      </div>
    );
  }

  if (!account) return null;

  return (
    <div
      data-testid="account-card"
      className="bg-slate-800 rounded-lg border border-slate-700 p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-200">Account</h3>
        <span className="text-xs px-2 py-1 rounded bg-green-900/50 text-green-400">
          {account.status}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-6">
        <div>
          <p className="text-sm text-slate-400">Portfolio Value</p>
          <p className="text-xl font-semibold text-slate-100">
            ${formatCurrency(account.portfolio_value)}
          </p>
        </div>
        <div>
          <p className="text-sm text-slate-400">Buying Power</p>
          <p className="text-xl font-semibold text-slate-100">
            ${formatCurrency(account.buying_power)}
          </p>
        </div>
        <div>
          <p className="text-sm text-slate-400">Cash</p>
          <p className="text-xl font-semibold text-slate-100">
            ${formatCurrency(account.cash)}
          </p>
        </div>
      </div>
    </div>
  );
}
```

**`haro/src/components/runs/MonitoringTab.tsx`** (new file):

```tsx
import { useAccount, usePositions } from "../../hooks/useAccount";
import { useFills } from "../../hooks/useFills";
import { AccountCard } from "./AccountCard";
import { PositionsTable } from "./PositionsTable";

interface MonitoringTabProps {
  runId: string;
  isRunning: boolean;
}

export function MonitoringTab({ runId, isRunning }: MonitoringTabProps) {
  const accountQuery = useAccount({
    enabled: isRunning,
  });
  const positionsQuery = usePositions({
    enabled: isRunning,
    refetchInterval: isRunning ? 5000 : false,
  });
  const fillsQuery = useFills(runId, { enabled: true });

  return (
    <div data-testid="monitoring-tab" className="space-y-6">
      <AccountCard
        account={accountQuery.data ?? null}
        isLoading={accountQuery.isLoading && isRunning}
      />
      <div>
        <h3 className="text-lg font-semibold text-slate-200 mb-3">Positions</h3>
        <PositionsTable positions={positionsQuery.data?.items ?? []} />
      </div>
      {fillsQuery.data && fillsQuery.data.items.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-slate-200 mb-3">
            Recent Fills ({fillsQuery.data.total})
          </h3>
          <div
            data-testid="fills-table"
            className="bg-slate-800 rounded-lg border border-slate-700 overflow-x-auto"
          >
            <table className="w-full">
              <thead className="bg-slate-700/50">
                <tr>
                  <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                    Symbol
                  </th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
                    Side
                  </th>
                  <th className="text-right px-6 py-3 text-sm font-medium text-slate-300">
                    Qty
                  </th>
                  <th className="text-right px-6 py-3 text-sm font-medium text-slate-300">
                    Price
                  </th>
                  <th className="text-right px-6 py-3 text-sm font-medium text-slate-300">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {fillsQuery.data.items.map((fill) => (
                  <tr key={fill.id} className="hover:bg-slate-700/30">
                    <td className="px-6 py-4 text-sm font-mono text-slate-200">
                      {fill.symbol ?? "—"}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-200">
                      {fill.side}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-slate-200">
                      {fill.quantity}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-slate-200">
                      ${fill.price}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-slate-400">
                      {new Date(fill.filled_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {!isRunning && (
        <p className="text-sm text-slate-400">
          Live monitoring is only available while the run is active. Historical
          fills are shown above.
        </p>
      )}
    </div>
  );
}
```

#### 16.1.5 RunDetailPage Refactor

**`haro/src/pages/RunDetailPage.tsx`** — replace conditional rendering
with headlessui Tab system.

The key structural change:

```tsx
import { Tab, TabGroup, TabList, TabPanel, TabPanels } from "@headlessui/react";
import { MonitoringTab } from "../components/runs/MonitoringTab";

// Inside the component, after the header/metadata section:
const isLivePaper = run.mode === "live" || run.mode === "paper";
const isBacktest = run.mode === "backtest";
const isRunning = run.status === "running";
const isCompleted = run.status === "completed";

// Build tab list dynamically:
const tabs = [];
if (isBacktest && isCompleted) {
  tabs.push({ label: "Results", key: "results" });
}
if (isLivePaper) {
  tabs.push({ label: "Monitoring", key: "monitoring" });
}

// If no tabs applicable, show placeholder

// Render with TabGroup:
<TabGroup>
  <TabList className="flex space-x-1 rounded-lg bg-slate-800 p-1">
    {tabs.map((tab) => (
      <Tab
        key={tab.key}
        className={({ selected }) =>
          `w-full rounded-lg py-2.5 text-sm font-medium leading-5
          ${
            selected
              ? "bg-slate-700 text-white shadow"
              : "text-slate-400 hover:text-white hover:bg-slate-700/30"
          }`
        }
      >
        {tab.label}
      </Tab>
    ))}
  </TabList>
  <TabPanels className="mt-4">
    {tabs.map((tab) => (
      <TabPanel key={tab.key}>
        {tab.key === "results" && results && (
          <>
            <BacktestStatsCard result={results} />
            <EquityCurveChart data={results.equity_curve} />
            <TradeLogTable fills={results.fills} />
          </>
        )}
        {tab.key === "monitoring" && (
          <MonitoringTab runId={run.id} isRunning={isRunning} />
        )}
      </TabPanel>
    ))}
  </TabPanels>
</TabGroup>;
```

**`haro/tests/unit/pages/RunDetailPage.test.tsx`** — update for tabs:

```typescript
it("shows monitoring tab for running paper run", async () => {
  server.use(
    http.get("/api/v1/runs/:id", () =>
      HttpResponse.json({
        id: "run-paper",
        strategy_id: "sma-crossover",
        mode: "paper",
        status: "running",
        config: {},
        created_at: "2026-04-07T10:00:00Z",
        started_at: "2026-04-07T10:01:00Z",
      }),
    ),
  );
  renderWithRoute("run-paper");
  await waitFor(() => {
    expect(screen.getByText("Monitoring")).toBeInTheDocument();
  });
});

it("shows results tab for completed backtest run", async () => {
  renderWithRoute("run-1");
  await waitFor(() => {
    expect(screen.getByText("Results")).toBeInTheDocument();
  });
});
```

Replace the old test that asserted a running paper run shows
"Results will appear here once the run completes." That placeholder is no
longer valid once Monitoring exists.

```bash
cd /weaver/haro && npx vitest run tests/unit/pages/RunDetailPage.test.tsx
cd /weaver/haro && npx vitest run tests/unit/components/runs/
# expect PASS
```

---

### 16.2 Task 14-9: Fill Stream via SSE Invalidation

**Decision**: D-14-9 🔒 Option A — SSE `orders.PartiallyFilled` /
`orders.Filled` → invalidate fill-derived queries.

> When an `orders.PartiallyFilled` or `orders.Filled` SSE event arrives,
> invalidate the fills query for the run so TanStack Query re-fetches from
> `GET /runs/{id}/fills`.
>
> **Prerequisite**: The live path must emit both events from the Phase 1
> reconciliation backbone. Do not leave partial fills invisible in the UI.

**Files to modify**:

| File                                    | What                                                                 |
| --------------------------------------- | -------------------------------------------------------------------- |
| `haro/src/hooks/useSSE.ts`              | Extend partial/full fill handlers to invalidate fill-derived queries |
| `haro/tests/unit/hooks/useSSE.test.tsx` | Add fills invalidation test                                          |

#### 16.2.1 Tests (RED)

**`haro/tests/unit/hooks/useSSE.test.tsx`** — add:

```typescript
it.each(["orders.PartiallyFilled", "orders.Filled"])(
  "invalidates fill-derived queries on %s",
  (eventType) => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    act(() => {
      MockEventSource.latest().simulateEvent(eventType, {
        order_id: "ord-1",
        run_id: "run-1",
        symbol: "AAPL",
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["fills"] }),
    );
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["account"] }),
    );
  },
);
```

```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useSSE.test.tsx
# expect FAILED — fills not invalidated
```

#### 16.2.2 Implement (GREEN)

**`haro/src/hooks/useSSE.ts`** — handle both partial and full fills through a
shared invalidation helper:

```typescript
const invalidateFillDerivedQueries = () => {
  queryClient.invalidateQueries({ queryKey: ["orders"] });
  queryClient.invalidateQueries({ queryKey: ["fills"] });
  queryClient.invalidateQueries({ queryKey: ["account"] });
};

eventSource.addEventListener(
  "orders.PartiallyFilled",
  (event: MessageEvent) => {
    const data = safeParse(event.data);
    invalidateFillDerivedQueries();
    addNotification({
      type: "info",
      message: data?.symbol
        ? `Partial fill: ${data.symbol}`
        : "Order partially filled",
    });
  },
);

eventSource.addEventListener("orders.Filled", (event: MessageEvent) => {
  const data = safeParse(event.data);
  invalidateFillDerivedQueries();
  addNotification({
    type: "success",
    message: data?.symbol ? `Order filled: ${data.symbol}` : "Order filled",
  });
});
```

Because `accountKeys.info()` and `accountKeys.positions()` share the
`["account"]` prefix, one invalidation refreshes both the account card and the
positions table.

```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useSSE.test.tsx
# expect PASS
```

---

## 17. Post-Flight Verification

### 17.1 Full Test Suite

```bash
# Backend
cd /weaver && python -m pytest tests/unit/ -x -q

# Frontend
cd /weaver/haro && npx vitest run

# TypeScript compile check
cd /weaver/haro && npx tsc --noEmit

# Lint
cd /weaver && python -m ruff check src/ tests/
cd /weaver/haro && npx eslint src/
```

### 17.2 Expected New Test Count

| Task                       | Area     | New Tests                                                  |
| -------------------------- | -------- | ---------------------------------------------------------- |
| Live fill backbone         | Backend  | 13 (adapter 4 + reconciliation 5 + RunManager lifecycle 4) |
| 14-6 FillRecord migration  | Backend  | 4 (model columns)                                          |
| 14-6 Fill symbol           | Backend  | 2 (domain model)                                           |
| 14-7 cancelled_at          | Backend  | 2 (schema + route)                                         |
| 14-3 Account endpoint      | Backend  | 3 (503, 200, fields)                                       |
| 14-1 Positions endpoint    | Backend  | 5 (VedaService 2 + route 3)                                |
| 14-2 Fills endpoint        | Backend  | 5 (interface 1 + route 4)                                  |
| 14-5 Candles M14           | Backend  | 5 (start, end, veda, inferred window, fallback)            |
| 14-11 run.Created SSE      | Frontend | 1                                                          |
| 14-10 Dashboard errors     | Frontend | 3 (plus replace old aggregate error assertion)             |
| 14-8 PositionsTable        | Frontend | 5                                                          |
| 14-8 AccountCard           | Frontend | 6                                                          |
| 14-8 RunDetailPage tabs    | Frontend | 4                                                          |
| 14-9 Fill SSE invalidation | Frontend | 2                                                          |
| **Total**                  |          | **~57–59 new/updated tests**                               |

### 17.3 Exit Gate Checklist

- [ ] `GET /api/v1/account` returns real account info (or 503 without creds)
- [ ] `GET /api/v1/account/positions` returns exchange positions
- [ ] Live/paper runs start a fill-reconciliation background task and cleanup cancels it cleanly
- [ ] Live fill reconciliation persists new fills idempotently from Alpaca account activities
- [ ] `GET /api/v1/runs/{id}/fills` returns run-scoped fills via JOIN
- [ ] `GET /api/v1/candles` accepts `start`/`end` and returns real bars (with VedaService)
- [ ] `GET /api/v1/candles` still uses real bars when `start` is omitted and VedaService is available
- [ ] `GET /api/v1/candles` falls back to mock without VedaService
- [ ] `OrderResponse` includes `cancelled_at`
- [ ] `FillRecord` has `commission` and `symbol` columns
- [ ] `Fill` domain model has `symbol` field
- [ ] RunDetailPage shows "Results" tab for completed backtest
- [ ] RunDetailPage shows "Monitoring" tab for live/paper runs
- [ ] Monitoring tab shows PositionsTable + AccountCard with 5s polling
- [ ] Monitoring tab shows recent fills
- [ ] SSE `run.Created` event triggers query invalidation + toast
- [ ] SSE `orders.PartiallyFilled` and `orders.Filled` invalidate fills, orders, and account queries
- [ ] Dashboard shows per-card error states
- [ ] All existing tests still pass
- [ ] TypeScript compiles without errors
- [ ] ruff + eslint pass

---

## 18. File Change Summary

### New Files

| File                                                      | Purpose                                |
| --------------------------------------------------------- | -------------------------------------- |
| `src/glados/routes/account.py`                            | Account + positions endpoints          |
| `src/glados/routes/fills.py`                              | Fills endpoint                         |
| `tests/unit/glados/routes/test_account.py`                | Account + positions route tests        |
| `tests/unit/glados/routes/test_fills.py`                  | Fills route tests                      |
| `tests/unit/veda/test_veda_service_positions.py`          | VedaService adapter delegation tests   |
| `haro/src/api/account.ts`                                 | Account + positions API functions      |
| `haro/src/api/fills.ts`                                   | Fills API function                     |
| `haro/src/hooks/useAccount.ts`                            | Account + positions hooks              |
| `haro/src/hooks/useFills.ts`                              | Fills hook                             |
| `haro/src/components/runs/PositionsTable.tsx`             | Positions table component              |
| `haro/src/components/runs/AccountCard.tsx`                | Account info card component            |
| `haro/src/components/runs/MonitoringTab.tsx`              | Monitoring tab content                 |
| `haro/tests/unit/components/runs/PositionsTable.test.tsx` | PositionsTable tests                   |
| `haro/tests/unit/components/runs/AccountCard.test.tsx`    | AccountCard tests                      |
| `haro/tests/unit/hooks/useAccount.test.tsx`               | Account hooks tests                    |
| Alembic migration                                         | `commission` + `symbol` on fills table |

### Modified Files

| File                                             | What changed                                                                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `src/walle/models.py`                            | `FillRecord` + `commission`, `symbol` columns                                                                                         |
| `src/veda/models.py`                             | `Fill` + `symbol` field                                                                                                               |
| `src/veda/interfaces.py`                         | + normalized trade-activity model and `list_trade_activities()` contract                                                              |
| `src/veda/adapters/alpaca_adapter.py`            | + Alpaca account-activities client for live fill reconciliation                                                                       |
| `src/veda/veda_service.py`                       | + live fill reconciliation helper, hydrated fill mapping, `get_exchange_positions()`, `get_bars()`                                    |
| `src/glados/schemas.py`                          | + `AccountResponse`, `PositionResponse`, `PositionListResponse`, `FillResponse`, `FillListResponse`; `OrderResponse` + `cancelled_at` |
| `src/glados/routes/candles.py`                   | Rewritten: VedaService → adapter, `start`/`end` params                                                                                |
| `src/glados/routes/orders.py`                    | `_state_to_response` + `cancelled_at` mapping                                                                                         |
| `src/glados/services/run_manager.py`             | + VedaService injection, live reconciliation task wiring, background-task cleanup                                                     |
| `src/glados/app.py`                              | + account_router, fills_router includes; + fill_repository on app.state; + VedaService passed into RunManager                         |
| `src/glados/dependencies.py`                     | + `get_fill_repository`                                                                                                               |
| `haro/src/api/types.ts`                          | + `Position`, `PositionListResponse`, `AccountInfo`, `Fill`, `FillListResponse`; `Order` + `cancelled_at`                             |
| `haro/src/hooks/useSSE.ts`                       | + `run.Created` handler; `orders.PartiallyFilled` / `orders.Filled` + fills/account invalidation                                      |
| `haro/src/pages/RunDetailPage.tsx`               | Refactored to headlessui Tabs + MonitoringTab                                                                                         |
| `haro/src/pages/Dashboard.tsx`                   | Per-card error states                                                                                                                 |
| `haro/src/components/common/StatCard.tsx`        | + `isError` prop                                                                                                                      |
| `haro/tests/mocks/handlers.ts`                   | + account, positions, fills handlers                                                                                                  |
| `haro/tests/unit/hooks/useSSE.test.tsx`          | + run.Created, fills invalidation tests                                                                                               |
| `haro/tests/unit/pages/RunDetailPage.test.tsx`   | + tabs tests                                                                                                                          |
| `haro/tests/unit/pages/Dashboard.test.tsx`       | + per-card error tests                                                                                                                |
| `tests/unit/veda/test_alpaca_adapter.py`         | + account-activities mapping tests                                                                                                    |
| `tests/unit/walle/test_fill_repository.py`       | + commission/symbol/list_by_run_id tests                                                                                              |
| `tests/unit/veda/test_models.py`                 | + Fill symbol tests                                                                                                                   |
| `tests/unit/veda/test_fill_persistence.py`       | + reconciliation and idempotent fill persistence tests                                                                                |
| `tests/unit/veda/test_live_order_flow.py`        | + partial/full fill event emission tests                                                                                              |
| `tests/unit/glados/services/test_run_manager.py` | + live reconciliation task lifecycle tests                                                                                            |
| `tests/unit/glados/test_schemas.py`              | + cancelled_at test                                                                                                                   |
| `tests/unit/glados/routes/test_orders.py`        | + cancelled_at response test                                                                                                          |
| `tests/unit/glados/routes/test_candles.py`       | + M14 start/end tests                                                                                                                 |
| `tests/factories/orders.py`                      | + position/account factory helpers                                                                                                    |
| `tests/factories/runs.py`                        | + RunManager factory support for injected VedaService                                                                                 |

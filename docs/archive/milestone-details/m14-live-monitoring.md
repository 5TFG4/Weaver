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

| Area               | Current State                                                                           | Evidence                                               |
| ------------------ | --------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| PositionTracker    | In-memory tracker: `apply_fill()`, `get_all_positions()`, `get_position()`              | `src/veda/position_tracker.py`                         |
| Position model     | Dataclass: symbol, qty, side, avg_entry_price, market_value, unrealized_pnl/pct         | `src/veda/models.py` L171                              |
| VedaService        | Has `get_positions()`, `get_account()` accessors — but NOT scoped per run               | `src/veda/veda_service.py`                             |
| FillRepository     | Only `save()` and `list_by_order(order_id)` — no `list_by_run_id()`                     | `src/walle/repositories/fill_repository.py`            |
| FillRecord         | Missing `commission` and `symbol` columns                                               | `src/walle/models.py` L229                             |
| ExchangeAdapter    | Abstract: `get_account()`, `get_positions()`, `get_bars()` all defined                  | `src/veda/interfaces.py`                               |
| AccountInfo        | Dataclass: account_id, buying_power, cash, portfolio_value, currency, status             | `src/veda/models.py` L160                              |
| RunContext (live)  | `greta: None, runner: StrategyRunner, clock: RealtimeClock` — no VedaService reference  | `src/glados/services/run_manager.py` L60               |

### 2.2 Backend API & Event Infrastructure

| Area              | Current State                                                                             | Evidence                                         |
| ----------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Candles route     | `GET /api/v1/candles` — hardcoded to `MockMarketDataService` (fake data)                  | `src/glados/routes/candles.py`                   |
| Candles contract  | Current route only accepts `symbol`, `timeframe`, `limit` — no explicit `start`/`end`     | `src/glados/routes/candles.py`                   |
| EventLog          | `read_from(offset, limit)` and `subscribe_filtered()` exist                               | `src/events/log.py`                              |
| SSE broadcaster   | Publishes events to all clients; SSE route supports `?run_id=` filtering                  | `src/glados/sse_broadcaster.py`                  |
| Live order events | Veda path explicitly emits `orders.Created`, `orders.Rejected`, `orders.Cancelled`; filled-event chain is not yet explicit end-to-end | `src/veda/veda_service.py` |
| OrderResponse     | Missing `cancelled_at` field (exists in DB model `VedaOrder` and domain `OrderState`)     | `src/glados/schemas.py`                          |
| Dependencies      | `get_veda_service()` returns `VedaService | None`; DI pattern established                 | `src/glados/dependencies.py`                     |

### 2.3 Frontend Infrastructure

| Area               | Current State                                                                            | Evidence                                          |
| ------------------ | ---------------------------------------------------------------------------------------- | ------------------------------------------------- |
| RunDetailPage      | Shows backtest results only; no tabs; `showResults` gated on `status==completed && mode==backtest` | `haro/src/pages/RunDetailPage.tsx`         |
| SSE hook           | Handles `run.Started/Stopped/Completed/Error`, `orders.Created/Filled/Rejected/Cancelled` | `haro/src/hooks/useSSE.ts`                        |
| SSE missing        | No `run.Created` listener; no `orders.Filled` data parsing (currently ignores payload)   | `haro/src/hooks/useSSE.ts` L141                   |
| Dashboard errors   | Only checks `runsQuery.isError`; ignores `activeRunsQuery`, `ordersQuery`, `healthQuery` | `haro/src/pages/Dashboard.tsx` L29                |
| Charting           | Recharts already installed (from M13 equity curve)                                        | `haro/package.json`                               |
| Type system        | `Order` interface missing `cancelled_at`                                                  | `haro/src/api/types.ts`                           |
| API hooks          | `useRuns`, `useOrders`, `useHealth`, `useRunResults` exist                                | `haro/src/hooks/`                                 |

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
2. **14-9 needs a backend prerequisite**. Frontend SSE invalidation is a good
  pattern, but the live/paper path still needs an explicit `orders.Filled`
  emission path or an equivalent fill-state transition event.
3. **14-5 needs a stronger API contract**. A real candles endpoint for charts
  should expose `start` and `end`; `limit`-only is not enough for predictable
  monitoring windows.
4. **14-4 should default to deferred**. Historical event browsing is useful,
  but it is not required to hit the M14 exit gate if fills are served by
  `GET /runs/{id}/fills` plus SSE refresh.

---

## 4. Dependency Graph

```
14-6 FillRecord fields ──> 14-2 fills endpoint ──┐
                                                  │
14-1 positions endpoint ──────────────────────────┤
                                                  ├──> 14-8 monitoring tab
14-3 account endpoint ────────────────────────────┤
                                                  │
14-5 candles wired ───────────────────────────────┘

14-7 cancelled_at ──> (independent schema fix)

14-4 events endpoint ──> 14-9 fill stream (or via SSE directly)

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

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Matches milestone wording most closely                  | Current architecture does not persist or expose this cleanly |
| Honest run contract                                     | `RunContext` does not currently hold Veda/PositionTracker refs |
| Better fit for future M16 run attribution               | In-memory tracker is lost after stop/restart             |
|                                                         | Unrealized P&L still needs market prices                 |

**Option B: Canonical account-scoped positions via `ExchangeAdapter.get_positions()` (recommended default path)**

Canonical route: `GET /api/v1/account/positions`.
Optional UI convenience alias: `GET /api/v1/runs/{id}/positions`, explicitly documented as account-scoped data.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Honest to Alpaca's resource model                       | Not per-run attribution                                  |
| Real exchange data — what the user actually has         | If multiple runs trade different symbols, all show       |
| Simplest useful monitoring experience                   | Requires owner acceptance that M14 is account-scoped     |
| Best match for a canonical REST resource                |                                                          |

**Option C: Hybrid — show exchange positions, annotate with run-level tracking**

Merge `ExchangeAdapter.get_positions()` for account-level truth with `PositionTracker` for per-run fill attribution.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Best of both worlds                                     | Most complex to implement                                |
| Real P&L from exchange + run-level attribution          | Mapping logic between two position sources               |
|                                                         | Premature for single-run usage patterns                  |

**Revised provisional recommendation**: Option B as the canonical contract.
If the owner wants to preserve the original task wording, keep
`GET /runs/{id}/positions` only as a thin alias and explicitly document the
response as **account-scoped** rather than true run-owned state.

> **Owner decision**: **B**. M16 升级到 **C**（混合模式），届时加入
> PositionTracker 做 per-run fill 归因标注。

#### 5.1.4 Decision Point D-14-1B: Positions Endpoint URL Shape

**Option A: Canonical `GET /account/positions` plus optional run-page alias (recommended)**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Keeps canonical resource honest                         | Slightly more frontend composition                       |
| Aligns with Microsoft REST guidance on simple resources | Adds one more endpoint                                   |
| Still allows run-detail page UX                         |                                                          |

**Option B: Only `GET /runs/{id}/positions`**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Consistent with run-detail page URLs                    | Resource contract becomes misleading                     |
| Simpler frontend wiring                                 | Hides account-wide semantics behind a run URI            |

**Option C: Both `/account/positions` and `/runs/{id}/positions` as first-class endpoints**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Maximum flexibility                                     | Duplicate API surface                                    |
| Gives clean migration path later                        | Higher maintenance cost                                  |

**Revised provisional recommendation**: Option A.

---

### 5.2 Task 14-2: Fills Endpoint

#### 5.2.1 Current State

`FillRepository.list_by_order(order_id)` exists but there is no `list_by_run_id()`. `FillRecord` lacks `commission` and `symbol` columns (task 14-6 dependency). Fills are persisted via `FillRepository.save()` during order lifecycle.

#### 5.2.2 Decision Point D-14-2: Fills Query Strategy

**Option A: Add `list_by_run_id()` via JOIN on orders table (recommended)**

SQL: `SELECT fills.* FROM fills JOIN orders ON fills.order_id = orders.id WHERE orders.run_id = :run_id ORDER BY fills.filled_at DESC`.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Run-scoped fills without denormalization                 | Requires JOIN — slightly more complex query              |
| data model stays normalized                              | Need to verify orders table has run_id column            |
| Natural for run detail page                              |                                                          |

**Option B: Add `run_id` column directly to `FillRecord`**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Simplest query: `WHERE run_id = :run_id`                | Denormalization — run_id already on orders               |
| No JOIN needed                                          | Extra migration + data backfill needed                   |
| Faster queries                                          | Violates DRY                                             |

**Option C: Query fills via order_ids from OrderRepository**

Two-step: fetch order IDs for run → fetch fills for those orders.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| No schema change needed                                 | N+1 query risk (or complex IN clause)                    |
| Reuses existing methods                                 | Fragile pagination                                       |

**Provisional recommendation**: Option A. JOIN is the standard relational approach and avoids denormalization. The query complexity is trivial.

---

### 5.3 Task 14-3: Account Endpoint

#### 5.3.1 Current State

`ExchangeAdapter.get_account()` returns `AccountInfo(account_id, buying_power, cash, portfolio_value, currency, status)`. `VedaService` wraps this. No REST endpoint exists.

#### 5.3.2 Decision Point D-14-3: Account Endpoint Scope

**Option A: Global `GET /api/v1/account` (recommended)**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Matches Alpaca semantics: one account                   | Not run-scoped                                           |
| Clean REST semantics                                    | Might confuse if we later add multi-account              |
| Simple implementation                                   |                                                          |

**Option B: Run-scoped `GET /api/v1/runs/{id}/account`**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Consistent with run-detail page pattern                 | Account is not run-specific                              |
| Run validation gives security context                   | Misleading URL semantics                                 |

**Option C: Embed account info in positions response**

Return `{ account: {...}, positions: [...] }` from a single endpoint.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| One request for monitoring tab                          | Couples unrelated concerns                               |
| Simpler frontend data fetching                          | Harder to cache/invalidate separately                    |

**Provisional recommendation**: Option A. Account is fundamentally global. The monitoring tab can call two endpoints: one for account, one for positions.

---

### 5.4 Task 14-4: Events Historical Query Endpoint

#### 5.4.1 Current State

`EventLog.read_from(offset, limit)` reads events from a given offset. `subscribe_filtered()` supports type filtering. But no REST endpoint exposes event history.

#### 5.4.2 Decision Point D-14-4: Events Endpoint Design

**Option A: Simple paginated query `GET /api/v1/events?run_id=&type=&offset=&limit=`**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Directly maps to `EventLog.read_from()`                 | May need filtering by run_id at application level        |
| Useful for debugging and audit                          | Potentially large result sets                            |
| Enables frontend event history view                     | Event payloads vary by type                              |

**Option B: Type-specific query endpoints (e.g. `/events/fills`, `/events/orders`)**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Typed responses per event type                          | Many endpoints to maintain                               |
| Cleaner OpenAPI documentation                           | Duplicates fill/order endpoints                          |

**Option C: Defer to M15 — use SSE for live, existing endpoints for history**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Less work in M14                                        | No event history UI                                      |
| SSE already provides real-time events                   | Loses audit trail visibility                             |

**Revised provisional recommendation**: Option C by default.
Defer 14-4 to M15 unless the owner explicitly wants an event-history browser in
M14. For the M14 exit gate, `GET /runs/{id}/fills` plus SSE refresh is enough.

> **Owner decision**: **C** — 确认延期到 M15。

#### 5.4.3 Supplementary Decision: Is 14-4 required for 14-9?

**Observation**: Task 14-9 (real-time fill stream) can be implemented purely via SSE `orders.Filled` events. The fill stream on the detail page only needs:
1. Historical fills (already loaded from 14-2 `GET /runs/{id}/fills`)
2. Live new fills (from SSE `orders.Filled` events → TanStack Query invalidation)

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

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Real market data for chart display                      | Requires Alpaca credentials                              |
| Simple: swap one dependency                             | API rate limits from Alpaca data endpoint                |
| Alpaca data API provides stock bars directly            | Need to handle credential-absent fallback                |
| Explicit time window matches industry chart APIs        | Requires a small contract expansion                      |

**Option B: Dual-source: ExchangeAdapter for live, BarRepository for historical**

Route checks run mode:
- Live/paper: `ExchangeAdapter.get_bars()` from Alpaca
- Backtest: `BarRepository` from local DB (WallE data)

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Works for both run types                                | More complex routing logic                               |
| Backtest doesn't need live API calls                    | BarRepository uses different data format than Alpaca     |
| Optimal data source per context                         |                                                          |

**Option C: Create MarketDataService interface + implementations**

Abstract `MarketDataService` protocol with `AlpacaMarketDataService` and `MockMarketDataService` implementations.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Clean abstraction boundary                              | More code for M14 scope                                  |
| Testable with mocks                                     | May be premature if only Alpaca is supported             |
| Follows PluginAdapter pattern                           |                                                          |

**Revised provisional recommendation**: Option A.
Do not ship a "real" candles endpoint without `start` and `end`; Alpaca's own
bars API is fundamentally range-based.

#### 5.5.3 Decision Point D-14-5B: Candles Endpoint URL

**Option A: Keep existing `GET /api/v1/candles?symbol=&timeframe=`**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| No breaking change                                     | Not run-scoped                                           |
| Already consumed by frontend (if used)                 |                                                          |

**Option B: Add `GET /api/v1/runs/{id}/candles?symbol=&timeframe=`**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Run-scoped, can auto-set date range from run            | Candles are market data, not run-specific                |
| Cleaner for detail page context                         | Unusual REST semantics                                   |

**Revised provisional recommendation**: Option A, but extend the existing
generic endpoint to accept `start` and `end` explicitly.

#### 5.5.4 Decision Point D-14-5C: Candles Query Contract

**Option A: Add `start` and `end` now (recommended)**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Matches Alpaca and most industry chart APIs             | Slightly larger API surface                              |
| Deterministic chart windows                             | Requires route and client updates                        |
| Works for both monitoring and future backfill use cases |                                                          |

**Option B: Keep `limit`-only in M14**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Lowest immediate change                                 | Poor fit for real monitoring windows                     |
|                                                         | Hard to align chart with run lifecycle                   |

**Option C: Infer time window from run server-side**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Less work for client                                    | Couples market data route to run semantics               |
|                                                         | Harder to reuse elsewhere                                |

**Revised provisional recommendation**: Option A.

---

### 5.6 Task 14-6: FillRecord Migration

#### 5.6.1 Current State

`FillRecord` columns: `id`, `order_id`, `price`, `quantity`, `side`, `filled_at`, `exchange_fill_id`. Missing: `commission` (Decimal), `symbol` (String).

The domain model `Fill` in `veda/models.py` already has `commission: Decimal` but NOT `symbol`. The Alpaca fill events should provide both.

#### 5.6.2 Decision Point D-14-6: Migration Approach

**Option A: Add both columns as nullable with defaults (recommended)**

```python
commission: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Backward compatible — existing fills unaffected         | Nullable means queries need to handle None               |
| Simple Alembic migration                                | Old fills won't have symbol data                         |
| Can backfill from orders table later                    |                                                          |

**Option B: Non-nullable with data migration backfill**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Cleaner schema                                          | Complex migration — must backfill from orders table      |
|                                                         | Risky if orders table doesn't have all needed data       |

**Provisional recommendation**: Option A. Nullable columns are safe. New fills will populate both fields; old fills can be backfilled in a future maintenance pass.

#### 5.6.3 Supplementary: Should `Fill` domain model also add `symbol`?

Yes. The `Fill` dataclass in `veda/models.py` should add `symbol: str` to match the persistence layer and enable per-symbol fill reporting. This is a minor change.

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

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Simplest implementation                                 | No user control over what to see                         |
| Matches current page structure                          | Doesn't scale if both views apply to same run            |
| No third-party tab component needed                     |                                                          |

**Option B: Full tab system with headlessui Tab component**

Use `@headlessui/react` `Tab` (already installed from M12-B a11y work) with:
- Tab "Results" (backtest only)
- Tab "Monitoring" (live/paper only, or both)
- Tab "Events" (all modes, future)

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Clean UX, discoverable                                  | More implementation work                                 |
| A11y handled by headlessui                              | Which tabs show varies by mode + status                  |
| Scales for future M15–M16 needs                         | Tab state management (URL hash or local?)                |

**Option C: Route-based sub-pages (`/runs/:id/results`, `/runs/:id/monitoring`)**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Clean URLs, deep-linkable                               | Heavier routing changes                                  |
| Lazy loading per sub-page                               | Overkill for 2 views                                     |

**Provisional recommendation**: Option B. `@headlessui/react` is already installed; the Tab component gives us accessible tabs with minimal code. The UX is significantly better than conditional blocks.

#### 6.1.3 Decision Point D-14-8B: Polling vs SSE for Position/Account Updates

**Option A: Polling via TanStack Query `refetchInterval` (recommended)**

```ts
useQuery({
  queryKey: ["runs", runId, "positions"],
  queryFn: () => fetchPositions(runId),
  refetchInterval: 5000, // 5 seconds
  enabled: run?.status === "running",
})
```

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| TanStack Query native, already used everywhere          | Extra HTTP requests every 5s                             |
| Simple: just set refetchInterval                        | Not truly real-time (5s delay)                           |
| Auto-stops when run isn't running                       |                                                          |
| Server-side is simple REST                              |                                                          |

**Option B: Dedicated SSE events for positions and account changes**

Backend publishes `account.Updated`, `positions.Changed` events.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| True real-time                                          | Backend needs to emit new event types                    |
| No polling overhead                                     | PositionTracker doesn't currently emit events            |
| Consistent with fill stream                             | More infrastructure for marginal UX benefit              |

**Provisional recommendation**: Option A. Positions and account aren't microsecond-critical. 5-second polling is standard for trading dashboards and dramatically simpler than adding new SSE event types.

> **Owner decision**: **A**. 确认 5 秒轮询仅影响浏览器 UI 展示刷新频率，
> 不影响后端策略的执行延迟（策略直接通过 VedaService → ExchangeAdapter
> 获取数据，不经过前端 REST 轮询）。

#### 6.1.4 Decision Point D-14-8C: Monitoring Tab Components

Components needed:
1. **PositionsTable**: symbol, qty, side, avg_entry_price, market_value, unrealized_pnl, unrealized_pnl_percent
2. **AccountCard / P&L Card**: buying_power, cash, portfolio_value, status

**Option A: Simple table + stat card (recommended)**

Reuse existing patterns:
- `PositionsTable`: same structure as `OrderTable` (data table with columns)
- `AccountCard`: same structure as `BacktestStatsCard` (labeled values in grid)

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Consistent with existing component patterns             | No P&L chart (just numbers)                              |
| Fast to implement                                       |                                                          |
| Reuses Tailwind patterns                                |                                                          |

**Option B: Rich monitoring dashboard with mini P&L chart**

Add a small equity-over-time chart for the live run using Recharts.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| More visually informative                               | Needs historical portfolio values (Alpaca has this API)  |
| Better monitoring experience                            | More API integration work                                |

**Provisional recommendation**: Option A for M14. Table + card gives the core monitoring view. A mini equity chart can be added in M16 when strategy comparison becomes relevant.

> **Owner decision**: **A**，后续有需要可升级到 B。

---

### 6.2 Task 14-9: Real-time Fill Stream

#### 6.2.1 Current State

SSE hook already listens for `orders.Filled` but doesn't parse the event data
(just shows a generic "Order filled" toast). TanStack Query invalidation for
`["orders"]` already happens on fill.

However, the backend prerequisite is not fully locked yet: the live/paper Veda
path explicitly emits `orders.Created`, `orders.Rejected`, and
`orders.Cancelled`, but the `orders.Filled` emission chain should be treated as
an explicit prerequisite rather than assumed.

#### 6.2.2 Decision Point D-14-9: Fill Stream Implementation

**Option A: SSE → TanStack Query invalidation → re-fetch fills endpoint (recommended after backend prerequisite)**

On `orders.Filled` event:
1. Invalidate `["runs", runId, "fills"]` query key
2. TanStack Query auto-refetches from `GET /runs/{id}/fills`
3. Fill table updates

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Leverages existing SSE + React Query pattern            | Extra HTTP request per fill event                        |
| Source of truth is always the DB (via endpoint)         | Very slight delay (fetch round-trip)                     |
| Simple: 2 lines of code in useSSE                       |                                                          |
| No state sync issues                                    |                                                          |

**Option B: Poll `GET /runs/{id}/fills` every 3-5s while run is active**

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| No dependence on a live `orders.Filled` event chain     | Extra periodic HTTP traffic                              |
| Very robust as a fallback                               | Not truly real-time                                      |
| Easy to add and remove later                            |                                                          |

**Option C: SSE → optimistic append to fill list in React Query cache**

Parse fill data from SSE event, inject directly into cached query data.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Truly instant UI update                                 | Cache can drift from server state                        |
| No extra HTTP request                                   | Must handle SSE payload format carefully                 |
|                                                         | Complex cache manipulation                               |

**Revised provisional recommendation**: Option A if M14 explicitly adds the
missing live `orders.Filled` event path; otherwise use Option B as a temporary
fallback. Avoid optimistic cache writes as the default.

> **Owner decision**: **A** — 需先在 Phase 1 补全 `orders.Filled` 后端事件链
> 作为显式前置条件。

---

### 6.3 Task 14-10: Dashboard Error Handling

#### 6.3.1 Current State

```typescript
const isError = runsQuery.isError;  // Only checks ONE of FOUR queries
```

`activeRunsQuery.isError`, `ordersQuery.isError`, and `healthQuery.isError` are silently ignored.

#### 6.3.2 Decision Point D-14-10: Error Display Strategy

**Option A: Aggregate error check — show dashboard error if ANY query fails**

```typescript
const isError = runsQuery.isError || activeRunsQuery.isError || ordersQuery.isError || healthQuery.isError;
```

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Simple — one error state for the whole page             | May be too aggressive (health failing ≠ dashboard broken)|
| User immediately knows something's wrong                | Single error message can't distinguish sources           |

**Option B: Per-card error states**

Each `StatCard` independently shows error or data based on its own query.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Granular: health failure doesn't kill runs display      | More UI complexity                                       |
| Partial data is still useful                            | Need error variant for `StatCard` component              |
| Most informative for user                               |                                                          |

**Option C: Split — critical errors block page, non-critical show inline warnings**

If `runsQuery` fails → full page error. If `healthQuery` fails → warning banner or card-level indicator.

| Pros                                                    | Cons                                                     |
| ------------------------------------------------------- | -------------------------------------------------------- |
| Balanced UX                                             | Need to define "critical" vs "non-critical"              |
| Doesn't over-block                                      | Slightly more complex                                    |

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

| Task  | Area      | Estimated New Tests |
| ----- | --------- | ------------------- |
| 14-1  | Backend   | 8–12 (route + schema + mock adapter) |
| 14-2  | Backend   | 8–12 (route + repository JOIN + schema) |
| 14-3  | Backend   | 5–8 (route + schema)  |
| 14-4  | Backend   | 0–12 (0 if deferred; 8–12 if kept in M14) |
| 14-5  | Backend   | 5–8 (route refactor + adapter integration) |
| 14-6  | Backend   | 3–5 (model + migration) |
| 14-7  | Backend   | 2–3 (schema field) |
| 14-8  | Frontend  | 15–20 (tab, positions table, account card) |
| 14-9  | Frontend  | 5–10 (SSE handler + fill refresh + possible fallback polling) |
| 14-10 | Frontend  | 5–8 (dashboard error states) |
| 14-11 | Frontend  | 2–3 (SSE handler) |
| **Total** |       | **~58–99 new tests** |

### 8.2 Existing Tests at Risk

- Candles route tests (if any) need refactoring for real data source.
- Dashboard tests need update for per-card error handling.
- SSE hook tests need new event handlers.

---

## 9. Decision Summary

| Decision | Question | Options | Provisional | Owner decision |
| -------- | -------- | ------- | ----------- | -------------- |
| D-14-1   | Position semantics | A: True run-scoped tracker/snapshot, B: Canonical account-scoped positions, C: Hybrid | B | **B** — M16 升级到 C（混合模式：Alpaca 仓位 + run 归因） |
| D-14-1B  | Positions endpoint URL | A: `/account/positions` + optional alias, B: `/runs/{id}/positions` only, C: both first-class | A | **A** |
| D-14-2   | Fills query strategy | A: JOIN, B: Denorm run_id, C: Two-step | A | **A** |
| D-14-3   | Account endpoint scope | A: Global, B: Run-scoped, C: Embedded | A | **A** |
| D-14-4   | Events endpoint design | A: Paginated query, B: Per-type endpoints, C: Defer | C | **C** — 延期到 M15 |
| D-14-5   | Candles data source | A: Alpaca swap, B: Dual-source, C: Abstract | A | **A** |
| D-14-5B  | Candles endpoint URL | A: Keep existing, B: Run-scoped | A | **A** |
| D-14-5C  | Candles query contract | A: Add `start`/`end` now, B: Keep limit-only, C: Infer from run | A | **A** |
| D-14-6   | FillRecord migration | A: Nullable, B: Non-null + backfill | A | **A** |
| D-14-8A  | Tab strategy | A: Conditional sections, B: headlessui Tabs, C: Sub-routes | B | **B** |
| D-14-8B  | Position/account updates | A: Polling, B: SSE events | A | **A** — 5s 轮询仅影响 UI 展示刷新，不影响策略执行延迟 |
| D-14-8C  | Monitoring components | A: Simple table+card, B: Rich with chart | A | **A** — 后续有需要可升级到 B |
| D-14-9   | Fill stream mechanism | A: SSE→invalidate→refetch, B: short polling fallback, C: optimistic cache | A if prerequisite exists, else B | **A** — 需先补全 `orders.Filled` 后端事件链 |
| D-14-10  | Dashboard error display | A: Aggregate, B: Per-card, C: Split | B | **B** |

---

## 10. Recommended Default Path

If no decisions are changed, the default implementation order would be:

**Phase 0: Scope Lock**
1. Lock M14 as **account-scoped monitoring on a run page**, not durable run-owned portfolio history.

**Phase 1: Schema & Migration (foundation)**
2. 14-6: FillRecord migration (unblocks 14-2)
3. 14-7: OrderResponse `cancelled_at` (independent)
4. Add explicit live/paper `orders.Filled` emission path or choose polling fallback for 14-9.

**Phase 2: Backend Endpoints**
5. 14-3: Account endpoint (global)
6. 14-1: Positions endpoint with canonical account semantics (`/account/positions`, optional run-page alias)
7. 14-2: Fills endpoint (JOIN query)
8. 14-5: Candles wired to Alpaca with explicit `start`/`end` contract
9. 14-4: Events endpoint only if the owner explicitly keeps it in M14

**Phase 3: Frontend**
10. 14-11: `run.Created` SSE listener (quick win)
11. 14-10: Dashboard per-card error states (quick win)
12. 14-8: Monitoring tab with headlessui Tabs + PositionsTable + AccountCard
13. 14-9: Fill stream via SSE invalidation, or short polling fallback until live filled-event chain exists

This ordering ensures each phase builds on the previous and no task is blocked.

# Weaver System Audit

**Date**: 2026-04-04
**Scope**: Full stack — backend (src/), frontend (haro/src/), API layer, data model
**Total issues**: 63+ across 4 severity tiers

---

## Executive Summary

**Core thesis: Weaver is a lifecycle manager, not a trading platform.**

The system manages the _lifecycle_ of runs (create, start, stop) and records
their _artifacts_ (orders). But a quantitative trading platform's value comes
from:

1. **Research** — run experiments, see results, iterate on parameters
2. **Monitoring** — watch live positions, P&L, exposure in real time
3. **Analysis** — understand why trades happened, compare strategies
4. **Risk** — enforce limits, prevent catastrophic losses

The system executes runs but cannot show their results. It places orders but
cannot show positions. It tracks status but not outcomes. It manages lifecycle
but not value.

The fix is not a longer list of endpoints. It is a shift in what the system
considers its primary output: not "a run was completed" but "here is what the
strategy produced."

Issues are organized by domain. Each section includes structural design
problems, missing backend/API capabilities, and frontend bugs — unified under
the domain they impact.

---

## 1. Data Model: No Concept of "Results"

**This is the deepest structural problem.** A `Run` knows its inputs (config)
and its state (status). It does not know its outputs (results).

```typescript
interface Run {
  id: string;
  strategy_id: string;
  mode: RunMode;
  status: RunStatus;
  config: Record<string, unknown>; // inputs
  created_at: string;
  started_at?: string;
  stopped_at?: string;
  // no results, no metrics, no performance — void return type
}
```

The backend computes rich results (`BacktestResult` with 16 metrics, equity
curve, fill log) but the data model has no place to put them. This is not a
missing field — it is a missing _concept_. The system was designed around
lifecycle management without considering that the lifecycle exists to produce
an output.

This radiates outward into every user journey:

- The frontend cannot show results (nowhere to get them).
- Strategy comparison is impossible (nothing to compare).
- The dashboard cannot show performance (no data source).
- The activity feed is meaningless ("run completed" vs "run completed with
  12.3% return and 1.8 Sharpe").

### Backend: results pipeline is severed

`GretaService.get_result()` computes a `BacktestResult` with 16 statistical
metrics, a timestamped equity curve, and a full fill log. `RunManager` never
calls it — the data is garbage-collected when the `RunContext` is cleaned up.

```python
# src/glados/services/run_manager.py
async def _start_backtest(self, run):
    greta = GretaService(...)
    runner = StrategyRunner(...)
    clock = BacktestClock(...)
    await clock.run()                    # backtest executes
    # greta.get_result() is NEVER called
    # BacktestResult is silently lost
    run.status = "completed"
```

**File**: `src/greta/greta_service.py` (~L388), `src/glados/services/run_manager.py` (~L157)

### Related issues in this domain

| ID  | Severity     | Issue                                                                         | Layer   |
| --- | ------------ | ----------------------------------------------------------------------------- | ------- |
| A-1 | **Critical** | Backtest results computed but not exposed via API                             | Backend |
| A-6 | Medium       | Backtest simulated positions discarded on cleanup (persist alongside results) | Backend |
| C-5 | Medium       | No export endpoint (CSV/JSON) for results, fills, equity curves               | Backend |
| C-6 | Medium       | No cross-run performance comparison endpoint                                  | Backend |
| C-7 | Medium       | No benchmark tracking (vs SPY, no alpha/beta/IR)                              | Backend |

### Impact: "Run a backtest and see results" is broken

This is the primary use case of a quant platform. After a backtest completes,
the user sees a status badge change to "completed" and a toast notification.
That is the entire experience. No performance summary, no equity curve, no
trade list, no charts. Zero charting libraries are imported in the frontend.

---

## 2. Entity Design: Run Conflates Three Different Things

The system uses a single `Run` entity for backtests, paper trading, and live
trading. They share the same table, API, UI row, and state machine.

But these are categorically different activities:

|             | Backtest                             | Paper/Live                                |
| ----------- | ------------------------------------ | ----------------------------------------- |
| Nature      | An experiment — run once, get result | An ongoing deployment — runs indefinitely |
| User intent | "What would have happened?"          | "Make money now"                          |
| Lifecycle   | Seconds/minutes, then done forever   | Days/weeks/months, monitored continuously |
| Key output  | Statistical report (return, Sharpe)  | Current state (positions, P&L, exposure)  |
| Volume      | Dozens per day during research       | 1–3 at any time                           |
| Management  | Delete freely, compare, iterate      | Monitor carefully, intervene if needed    |

By cramming them into one entity:

- **Backtests lose their "result" identity.** A backtest's purpose IS its
  result. But `Run` has no result field. The status says "completed" and
  that's it.
- **Live runs lose their "monitoring" identity.** A live run needs a dedicated
  view: current positions, P&L curve, open orders, recent fills. Instead it
  gets the same table row as a backtest.
- **The list becomes unusable.** 80 backtests and 2 live strategies in the
  same flat paginated list with no mode-based partitioning.

### Config-as-opaque-blob defeats the system's purpose

`config` is typed as `Record<string, unknown>` / `dict[str, Any]`. The system
cannot:

- Show what parameters were used in a readable way
- Compare configs between runs ("what changed?")
- Pre-fill a clone form
- Validate at the API layer (backtest dates checked only at runtime)

Every strategy has a `config_schema` (JSON Schema). The backend validates
against it at creation time. The frontend renders it via RJSF. The system
_knows_ the schema — then throws that knowledge away immediately.

### Related issues in this domain

| ID  | Severity | Issue                                                           | Layer    |
| --- | -------- | --------------------------------------------------------------- | -------- |
| C-1 | High     | No run deletion or archival; runs accumulate forever            | Backend  |
| B-9 | Medium   | No run config update or clone                                   | Backend  |
| C-3 | High     | No strategy versioning — modified code not tracked between runs | Backend  |
| m1  | Minor    | Stale backtest dates leak into non-backtest configs             | Frontend |
| m3  | Minor    | Unsafe `as` casts for config fields in runs table               | Frontend |

---

## 3. Information Architecture: Run-Centric vs Strategy-Centric

The entire UI is organized around individual runs. But the user's mental model
is centered on _strategies_:

- "How is my SMA Crossover strategy performing?"
- "What's the best config for my mean-reversion strategy?"
- "Has my strategy improved since I changed the lookback window?"

These questions are **unanswerable**. There is no strategy-level view. You
cannot ask "show me all backtests of strategy X sorted by Sharpe ratio."

```
User's mental model:              What the system shows:

Strategy                          Runs (flat list)
├── Backtest #1 (result)          Orders (flat list)
├── Backtest #2 (result)          Dashboard (4 numbers)
├── Backtest #3 (result)
└── Live deployment
    ├── Positions
    ├── Orders
    └── P&L
```

### Three disconnected list pages

The frontend has three pages: Dashboard, Runs, Orders. These are independent
flat lists with no cross-referencing. The user must maintain mental mapping
between them. Every page is a dead end.

- `/runs/:runId` renders the same `RunsPage` component filtered to one row —
  it is not a detail page with tabs, results, charts, or order history.
- No link from a run to its orders.
- No link from an order to its run (plain text run ID in modal).
- No drill-down from dashboard to specific runs.
- Activity feed items are not clickable.

### Related issues in this domain

| ID  | Severity | Issue                                                             | Layer    |
| --- | -------- | ----------------------------------------------------------------- | -------- |
| M7  | Major    | Run IDs are plain text, not clickable links                       | Frontend |
| M6  | Major    | No "View Orders" link per run                                     | Frontend |
| M4  | Major    | OrderDetailModal: run ID is plain text, not link                  | Frontend |
| M5  | Major    | OrderTable missing `run_id` column                                | Frontend |
| M1  | Major    | OrdersPage `runIdFilter` has no setter — filter is a one-way trap | Frontend |
| m2  | Minor    | No run ID filter input despite URL param support                  | Frontend |
| B-2 | Medium   | Runs not filterable by `strategy_id`                              | Backend  |
| B-5 | Low      | Strategies endpoint returns untyped `list[dict]`, no pagination   | Backend  |
| B-3 | Medium   | No sorting on any list endpoint                                   | Backend  |

---

## 4. Workflow: Create-Then-Start Is Broken for Backtests

The current backtest flow:

1. Click "+ New Run"
2. Fill out form (strategy, mode, config, dates)
3. Submit → run created in `pending` status
4. Find the run in the table
5. Click "Start" → wait for completion
6. See... a "completed" badge

The two-step flow is borrowed from deployment systems (Docker, Kubernetes). But
a backtest is not a deployment — it is a **computation**. The correct analogy
is a database query or a CI job: submit and get a result.

Worse, `pending` creates a landmine: backtest date validation happens at start
time, not creation time. The user gets a 201 success, then a mysterious failure
on start.

### Related issues in this domain

| ID  | Severity     | Issue                                                                 | Layer    |
| --- | ------------ | --------------------------------------------------------------------- | -------- |
| C1  | **Critical** | Backtest date inputs have no `required` attribute                     | Frontend |
| C2  | **Critical** | Backtest date inputs are uncontrolled (no `value` binding)            | Frontend |
| B-4 | High         | Backtest date validation deferred to runtime — after run is persisted | Backend  |
| M9  | Major        | CreateRunForm: no success notification                                | Frontend |
| M10 | Major        | No loading/error state for strategies dropdown                        | Frontend |
| C-8 | Medium       | No scheduling or recurring runs                                       | Backend  |

---

## 5. Real-Time Data & Monitoring

SSE is the only state sync mechanism, but it is **ephemeral**. If you miss an
event, it is gone. Combined with:

- Backtest results only existing in memory during execution
- Error messages only appearing in SSE toasts that auto-dismiss
- No event history API
- No persistent record of transient state

The system is ephemeral by default. If you run a backtest and your laptop
sleeps, you miss the result forever. If a live run errors while you're at
lunch, you come back to a red badge with no explanation.

A trading platform needs to be the opposite: a **reliable record of truth**.
SSE should augment persistent state, not replace it.

### Five data categories have no API exposure

| Data             | Produced by         | Stored in               | API endpoint    | Frontend? |
| ---------------- | ------------------- | ----------------------- | --------------- | --------- |
| Backtest results | GretaService        | **Nowhere — discarded** | **None**        | ❌        |
| Positions        | PositionTracker     | In-memory only          | **None**        | ❌        |
| Account info     | ExchangeAdapter     | Not stored              | **None**        | ❌        |
| Fills            | VedaService / Greta | `fills` table / memory  | **None**        | ❌        |
| Event history    | All services        | `outbox` table          | SSE stream only | ❌        |

### Related issues in this domain

| ID  | Severity     | Issue                                                             | Layer    |
| --- | ------------ | ----------------------------------------------------------------- | -------- |
| A-2 | **Critical** | Positions computed but no REST endpoint                           | Backend  |
| A-3 | High         | Account info (equity, buying power) — no endpoint                 | Backend  |
| A-4 | High         | Fill history persisted but no REST endpoint                       | Backend  |
| A-5 | Medium       | Event history queryable in DB but only exposed via SSE            | Backend  |
| B-7 | High         | Candles endpoint returns mock data only                           | Backend  |
| C-4 | High         | No bar data ingestion API (backtesting without data is useless)   | Backend  |
| C4  | **Critical** | Dashboard error state ignores 3 of 4 queries                      | Frontend |
| M8  | Major        | Missing `run.Created` SSE event listener                          | Frontend |
| m5  | Minor        | `orders.Filled` handler ignores event data — generic notification | Frontend |
| m7  | Minor        | No SSE reconnection backoff or retry limit                        | Frontend |
| m9  | Minor        | ConnectionStatus flashes "Disconnected" on initial load           | Frontend |
| m10 | Minor        | `staleTime` of 1 minute may hide staleness during SSE outages     | Frontend |

### Impact: "Monitor a live/paper trading run" is broken

After starting a live run, the user sees: a `running` badge and SSE toasts
when orders fire. No positions, no P&L, no account info, no live activity
stream. The dashboard's `ActivityFeed` shows recent _runs_, not orders,
fills, or signals.

---

## 6. Safety & Risk Management

**For a system that can place real orders with real money, this is dangerous.**

`TradingConfig` defines `max_concurrent_orders` and `rate_limit_per_minute`,
but **neither is enforced anywhere**. No position size limits, no max drawdown
circuit breaker, no daily loss limit, no per-symbol exposure cap.

### Related issues in this domain

| ID   | Severity     | Issue                                                         | Layer   |
| ---- | ------------ | ------------------------------------------------------------- | ------- |
| C-2  | **Critical** | No risk management enforcement despite config fields existing | Backend |
| B-8  | Medium       | `FillRecord` missing commission and symbol fields             | Backend |
| B-11 | Low          | Missing `cancelled_at` in `OrderResponse` schema              | Backend |

---

## 7. Decision Intelligence & Transparency

The order lifecycle is well-modeled (placed → submitted → filled/rejected).
But there is no record of _why_ any order was placed. The
`strategy.DecisionMade` event type exists but is never emitted.

For a quant system, "why" matters more than "what":

- "Why did the strategy buy SPY at 3:42 PM?"
- "What indicator values led to this decision?"
- "What market conditions triggered this trade?"

Without decision context, the system is an order management system with extra
steps.

### Related issues in this domain

| ID   | Severity | Issue                                                         | Layer   |
| ---- | -------- | ------------------------------------------------------------- | ------- |
| C-10 | Low      | No strategy diagnostics API                                   | Backend |
| B-1  | High     | `RunResponse` missing `error` field (DB has it, API omits it) | Backend |

### Impact: "Debug why my strategy made a trade" is impossible

The `OrderDetailModal` shows comprehensive order fields but no signal/reason
field, no market data context, no event trail. The backend stores events with
causal chains (`causation_id`, `corr_id`), but there is no API to query them.

---

## 8. API Engineering Quality

Issues that are not structural design problems but reduce the usability and
reliability of existing endpoints.

| ID   | Severity | Issue                                                                | Layer    |
| ---- | -------- | -------------------------------------------------------------------- | -------- |
| B-6  | Medium   | In-memory pagination is O(n) per page — DB filtering not pushed down | Backend  |
| B-10 | Low      | Health endpoint returns hardcoded values, no readiness check         | Backend  |
| C-9  | Medium   | No observability endpoint (`/metrics`)                               | Backend  |
| M11  | Major    | API barrel file missing `strategies` export                          | Frontend |

---

## 9. Frontend Code Quality

Implementation bugs that don't stem from design problems. These are fixable
without rethinking architecture.

### Critical

| ID  | Issue                                                                                                                  | File           |
| --- | ---------------------------------------------------------------------------------------------------------------------- | -------------- |
| C3  | Optimistic status overrides (`startedIds`, `stoppedIds`) are never cleared — permanently wrong status after Start/Stop | `RunsPage.tsx` |

### Major

| ID  | Issue                                                                       | File               |
| --- | --------------------------------------------------------------------------- | ------------------ |
| M2  | Stop button has no `disabled` guard — double-click fires duplicate requests | `RunsPage.tsx`     |
| M3  | ActivityFeed displays `strategy_id` twice                                   | `ActivityFeed.tsx` |

### Minor

| ID  | Issue                                                 | File                   |
| --- | ----------------------------------------------------- | ---------------------- |
| m4  | `OrderStatusBadge` returns `null` silently            | `OrderStatusBadge.tsx` |
| m6  | Color dot uses fragile `text-` → `bg-` string replace | `ActivityFeed.tsx`     |
| m8  | Pagination buttons have no `aria-label`               | `Pagination.tsx`       |

---

## Severity Summary

| Category                    | Critical | High  | Medium | Low   | Total         |
| --------------------------- | -------- | ----- | ------ | ----- | ------------- |
| 1. Data Model & Results     | 1        | —     | 4      | —     | 5             |
| 2. Entity Design            | —        | 2     | 1      | —     | 5 (+2 minor)  |
| 3. Information Architecture | —        | —     | 3      | 1     | 9 (+1 minor)  |
| 4. Workflow                 | 2        | 1     | 1      | —     | 6             |
| 5. Real-Time & Monitoring   | 2        | 3     | 2      | —     | 12 (+4 minor) |
| 6. Safety & Risk            | 1        | —     | 1      | 1     | 3             |
| 7. Decision Intelligence    | —        | 1     | —      | 1     | 2             |
| 8. API Quality              | —        | —     | 2      | 1     | 4             |
| 9. Frontend Code Quality    | 1        | —     | —      | —     | 6             |
| **Total**                   | **7**    | **7** | **14** | **4** | **52+**       |

> Some issues from the original audit have been merged where they describe the
> same root cause from different perspectives (e.g. A-1 and Journey 1 are the
> same problem). The 63 original item count included cross-references.

---

## Priority Roadmap

### Phase 1 — Make backtest results visible (highest impact, unlocks research)

| Task | Layer    | Description                                                        |
| ---- | -------- | ------------------------------------------------------------------ |
| 1a   | Backend  | Call `greta.get_result()` after backtest completion; persist to DB |
| 1b   | Backend  | Add `backtest_results` table (or JSONB on `runs`)                  |
| 1c   | Backend  | Add `GET /runs/{id}/results` endpoint                              |
| 1d   | Frontend | Create run detail page (`/runs/:runId`) with results panel         |
| 1e   | Frontend | Add charting library; render equity curve                          |
| 1f   | Frontend | Add trade log table on run detail page                             |
| 1g   | Frontend | Add `error` field to `Run` type; display on detail page            |

### Phase 2 — Enable live monitoring (unlocks monitoring)

| Task | Layer    | Description                                  |
| ---- | -------- | -------------------------------------------- |
| 2a   | Backend  | Add `GET /runs/{id}/positions` endpoint      |
| 2b   | Backend  | Add `GET /runs/{id}/fills` endpoint          |
| 2c   | Backend  | Add `GET /account` endpoint                  |
| 2d   | Frontend | Add positions panel on run detail page       |
| 2e   | Frontend | Add P&L summary card                         |
| 2f   | Frontend | Add real-time fill stream on run detail page |

### Phase 3 — Enable strategy iteration (unlocks analysis)

| Task | Layer    | Description                                                  |
| ---- | -------- | ------------------------------------------------------------ |
| 3a   | Frontend | Add performance columns to runs table (return, Sharpe, etc.) |
| 3b   | Frontend | Add column sorting (TanStack Table)                          |
| 3c   | Frontend | Add "Clone Run" button (pre-fill from existing run)          |
| 3d   | Frontend | Add run comparison view (side-by-side charts + stats)        |

### Phase 4 — Connect navigation (unlocks usability)

| Task | Layer    | Description                                    |
| ---- | -------- | ---------------------------------------------- |
| 4a   | Frontend | Make run IDs clickable links to `/runs/:runId` |
| 4b   | Frontend | Add "View Orders" link per run row             |
| 4c   | Frontend | Make `OrderDetailModal` run ID a link          |
| 4d   | Frontend | Make `ActivityFeed` items clickable            |
| 4e   | Frontend | Add breadcrumbs to run detail page             |

### Phase 5 — Fix code-level bugs

All Critical/Major frontend issues from §4 and §9.

### Phase 6 — Safety & risk (unlocks live trading safety)

| Task | Layer   | Description                                           |
| ---- | ------- | ----------------------------------------------------- |
| 6a   | Backend | Enforce `max_concurrent_orders` in VedaService        |
| 6b   | Backend | Enforce `rate_limit_per_minute` in order submission   |
| 6c   | Backend | Add position size limits and drawdown circuit breaker |
| 6d   | Backend | Add daily loss limit enforcement                      |

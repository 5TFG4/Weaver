# M13: Backtest Results - Design Framework & Decision Points

> **Document Charter**
> **Primary role**: M13 milestone design & execution plan.
> **Status**: DECISIONS LOCKED — execution plan active.
> **Prerequisite**: M12-B complete.
> **Key inputs**: `docs/MILESTONE_PLAN.md` section 8b, `docs/UI_AUDIT.md`, codebase review, official library documentation.
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

### 1.1 Why M13 Exists

M13 is the first milestone in the System Audit phase. Its purpose is narrow but critical: make the core research workflow actually work end-to-end.

Today, Weaver can:

- create a backtest run,
- execute the backtest runtime,
- compute a rich `BacktestResult`,
- emit lifecycle events.

But it still cannot reliably do the one thing a quant user expects:

> run a backtest and inspect the result afterwards.

That is the gap M13 closes.

### 1.2 Official M13 Scope

Per `docs/MILESTONE_PLAN.md`, M13 contains the following tasks:

| Task  | Layer    | Description                                                                                |
| ----- | -------- | ------------------------------------------------------------------------------------------ |
| 13-1  | Backend  | `_start_backtest()` calls `greta.get_result()`; persist result + simulated positions to DB |
| 13-2  | Backend  | New `backtest_results` table (or JSONB column on `runs`)                                   |
| 13-3  | Backend  | `GET /runs/{id}/results` endpoint                                                          |
| 13-4  | Backend  | Add `error` field to `RunResponse` schema                                                  |
| 13-5  | Backend  | Validate backtest dates at creation time                                                   |
| 13-6  | Frontend | Fix backtest form: `required` + controlled `value` binding                                 |
| 13-7  | Frontend | Create `/runs/:runId` detail page with Results tab                                         |
| 13-8  | Frontend | Add charting library; render equity curve                                                  |
| 13-9  | Frontend | Add trade log table on detail page                                                         |
| 13-10 | Frontend | Add success toast on run creation                                                          |

### 1.3 What This Document Does

This is not an implementation playbook yet.

This document is for owner decision-making:

- summarize the real constraints from the current codebase,
- enumerate viable options per task,
- compare pros and cons,
- identify which options preserve flexibility for M14-M17,
- provide a default recommendation without locking the decision.

---

## 2. Current System Snapshot

### 2.1 Backend Reality Today

The current result pipeline is partially built but severed before persistence.

| Area                | Current state                                                                                    | Evidence                                                      |
| ------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| Result computation  | `GretaService.get_result()` already returns `BacktestResult` with stats, equity curve, and fills | `src/greta/greta_service.py`                                  |
| Result persistence  | No repository or table stores backtest result output                                             | no `backtest_results` model/repository exists                 |
| Run completion      | `RunManager._start_backtest()` marks run `COMPLETED` or `ERROR`, then cleans up runtime context  | `src/glados/services/run_manager.py`                          |
| Simulated positions | Exist inside Greta runtime only; lost after cleanup                                              | `src/greta/models.py`, `src/greta/greta_service.py`           |
| Run error storage   | DB model already has `runs.error` column                                                         | `src/walle/models.py`                                         |
| Error exposure      | Internal `Run` dataclass and API `RunResponse` do not expose `error`                             | `src/glados/services/run_manager.py`, `src/glados/schemas.py` |
| Results API         | No `GET /runs/{id}/results` route exists                                                         | `src/glados/routes/runs.py`                                   |

### 2.2 Frontend Reality Today

The frontend has enough infrastructure to build M13 quickly, but not enough to show results yet.

| Area             | Current state                                                                                               | Evidence                                                                       |
| ---------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Run detail route | `/runs/:runId` exists, but renders `RunsPage`, not a real detail view                                       | `haro/src/App.tsx`                                                             |
| Run form dates   | `datetime-local` inputs are uncontrolled and not marked `required`                                          | `haro/src/components/runs/CreateRunForm.tsx`                                   |
| Time semantics   | Browser sends naive local timestamps from `datetime-local`; backend tests use timezone-aware ISO strings    | `CreateRunForm.tsx`, `tests/unit/glados/test_run_manager_backtest.py`          |
| Toast system     | Already exists via Zustand store + `Toast` component                                                        | `haro/src/stores/notificationStore.ts`, `haro/src/components/common/Toast.tsx` |
| Charting         | No charting dependency is installed                                                                         | `haro/package.json`                                                            |
| Table reuse      | Existing `OrderTable` is order-centric, clickable, and modal-oriented; it is not shaped for simulated fills | `haro/src/components/orders/OrderTable.tsx`                                    |

### 2.3 Existing Test Surface

Relevant test coverage already exists around the core parts of M13.

| Test area                | Current coverage                                                         | Notes                                          |
| ------------------------ | ------------------------------------------------------------------------ | ---------------------------------------------- |
| Greta result model       | Unit tests cover `BacktestResult`, equity curve, fills, Sharpe, drawdown | good foundation                                |
| RunManager backtest flow | Unit tests cover completion and missing `backtest_start` failure         | currently validates too late                   |
| Runs routes              | Tests exist for create/get/list/start/stop                               | results route absent                           |
| Runs persistence         | `RunRecord` and `RunRepository` tests already exist                      | pattern can be copied for a results repository |

---

## 3. Boundaries & Principles

### 3.1 M13 Boundaries

M13 should stay focused on completed backtest results.

Out of scope for this milestone:

- live/paper monitoring UX (`positions`, real-time P&L, live fills) - M14,
- strategy-level comparison and performance columns on list pages - M16,
- export endpoints - M17,
- merging create + start into one action - M16,
- general run navigation cleanup across all pages - M15.

### 3.2 Design Principles

The options below are evaluated against these principles:

1. **Durability first**: results must survive process cleanup, page reloads, and missed SSE events.
2. **Backtest-specific identity**: a backtest result should not be forced into a live-run mental model.
3. **Low regret for M14-M16**: M13 should not block monitoring tabs, list sorting, or comparison later.
4. **Thin frontend state**: TanStack Query + route params + typed payloads should remain the main pattern.
5. **Avoid fake flexibility**: prefer the smallest real abstraction that can carry the next 2-3 milestones.

---

## 4. Dependency Graph

```
13-2 persistence model ──┐
13-1 capture point ──────┼──> 13-3 results endpoint ──> 13-7 detail page ──> 13-8 chart
                         │                               └────────────────────> 13-9 trade log
13-4 error field ────────┘

13-5 creation-time date validation ──> 13-6 backtest form behavior

13-10 success toast is independent, but UX should match 13-7 routing choice.
```

Key takeaway:

- The main architectural decisions are backend result modeling and detail-page routing.
- Chart and trade log decisions should be made after endpoint payload shape is chosen.

---

## 5. Backend Decision Package

## 5.1 Task 13-1: Where Should Result Capture Happen?

### 5.1.1 Current State

`RunManager._start_backtest()` currently:

1. initializes `GretaService`, `StrategyRunner`, and `BacktestClock`,
2. runs the clock,
3. drains pending tasks,
4. sets terminal status,
5. cleans up runtime context.

It never calls `greta.get_result()`.

That means the only safe moment to capture the result is **after the backtest finished successfully but before cleanup destroys the runtime state**.

### 5.1.2 Decision Point D-13-1: Result Capture Owner

**Option A: Capture and persist synchronously inside `RunManager._start_backtest()` (recommended)**

Flow:

1. backtest completes,
2. `clock.error` and drained task errors are checked,
3. if successful, call `greta.get_result()`,
4. persist result before `_cleanup_run_context()`.

| Pros                                                                                | Cons                                             |
| ----------------------------------------------------------------------------------- | ------------------------------------------------ |
| Deterministic - result is saved in the same lifecycle path that marks run completed | `RunManager` becomes aware of result persistence |
| Easy to test with existing backtest tests                                           | Slightly more code in one method                 |
| No race with cleanup or event delivery                                              |                                                  |
| Failure semantics are clear: persistence failure can mark run `ERROR`               |                                                  |

**Option B: Let `GretaService` persist results directly**

| Pros                                                        | Cons                                             |
| ----------------------------------------------------------- | ------------------------------------------------ |
| Keeps persistence close to the component that owns the data | Pushes repository concerns into Greta            |
| `GretaService` knows result structure best                  | Violates current service boundaries              |
|                                                             | Harder to reuse Greta outside DB-backed contexts |

**Option C: Emit a terminal event and persist asynchronously in a consumer**

| Pros                           | Cons                                                           |
| ------------------------------ | -------------------------------------------------------------- |
| More event-driven architecture | Result payload is not currently in the event stream            |
| Keeps `RunManager` thinner     | Requires either bloating events or shared runtime state access |
|                                | Eventual consistency is a poor fit for the primary user output |
|                                | More moving parts for little M13 value                         |

**Provisional recommendation**: Option A.

The result is the main output of a backtest, not a secondary side effect. It should be captured in the same synchronous control path that decides whether the run is `COMPLETED` or `ERROR`.

---

## 5.2 Task 13-2: How Should Backtest Results Be Stored?

### 5.2.1 Current State

The codebase already uses PostgreSQL `JSONB` for `runs.config`, and the SQLAlchemy setup maps `dict[str, Any]` to `JSONB` in `Base.type_annotation_map`.

This means M13 has three realistic storage families.

### 5.2.2 Decision Point D-13-2: Result Persistence Model

**Option A: Dedicated `backtest_results` table with JSONB payload columns (recommended)**

Suggested shape:

- `run_id` one-to-one key,
- scalar metadata columns (`start_time`, `end_time`, `timeframe`, `final_equity`),
- JSONB columns for `stats`, `equity_curve`, `fills`, `final_positions`.

| Pros                                                                             | Cons                                                |
| -------------------------------------------------------------------------------- | --------------------------------------------------- |
| Cleanly separates run lifecycle from backtest output                             | One new model, repository, and migration            |
| Preserves a real domain concept: a backtest result is not just more run metadata | Slightly more code than adding one column to `runs` |
| Keeps `runs` table from becoming a mixed blob for backtest-only fields           |                                                     |
| Compatible with future joins and filtering in M15-M16                            |                                                     |
| Flexible enough for current payload size without over-normalizing                |                                                     |

**Option B: Add a JSONB `result` column directly on `runs`**

| Pros                                               | Cons                                                                      |
| -------------------------------------------------- | ------------------------------------------------------------------------- |
| Lowest migration cost                              | Conflates lifecycle entity with backtest-only output                      |
| Simple repository changes - only `RunRecord` grows | Makes live/paper runs carry backtest-only schema baggage                  |
| One query can fetch run + result                   | Harder to evolve toward strategy comparison and backtest-specific queries |
|                                                    | `runs` becomes an increasingly opaque bucket                              |

**Option C: Fully normalized model (`backtest_results` + child tables for equity points/fills/positions)**

| Pros                                                           | Cons                                      |
| -------------------------------------------------------------- | ----------------------------------------- |
| Best queryability and analytics flexibility                    | Highest implementation and migration cost |
| Best long-run fit for giant backtests and comparison workloads | Overbuild for M13 exit gate               |
| Could reuse future list sorting and analytics more directly    | Would likely pull M14-M16 work into M13   |

**Provisional recommendation**: Option A.

It is the best balance between domain clarity and M13 delivery speed.

### 5.2.2a Review Note: Complete Field Inventory

> **Added during design review.**

The "Suggested shape" above lists `stats`, `equity_curve`, `fills`, `final_positions`, but actual `BacktestResult` (in `src/greta/models.py`) also carries:

- `run_id: str`
- `symbols: list[str]`
- `simulation_duration_ms: int`
- `total_bars_processed: int`

These metadata fields are useful for debugging and future comparison views (M16). The table design should account for them explicitly — for example, `simulation_duration_ms` and `total_bars_processed` can be scalar columns, while `symbols` should be stored as an array-capable field or inside a JSONB metadata section.

### 5.2.2b Review Note: Migration Strategy

> **Added during design review.**

The project already uses Alembic (`alembic.ini` exists at workspace root). Creating a `backtest_results` table requires a migration. Open questions:

- Should M13 use `alembic revision --autogenerate` or hand-write the migration?
- Is the existing `runs.error` column already tracked in a migration, or was it added via manual DDL? If the latter, a reconciliation step may be needed.
- Recommendation: use `--autogenerate` for the new table, but review the generated migration manually before applying.

### 5.2.3 Decision Point D-13-2B: How Should Final Simulated Positions Be Stored?

This is a separate decision from the top-level result table choice.

> **⚠️ Review Warning: Data Source Gap**
>
> All three options below assume `final_positions` data is available at result capture time. However, `BacktestResult` currently has **no `final_positions` field**. Its fields are: `run_id`, `start_time`, `end_time`, `timeframe`, `symbols`, `stats`, `final_equity`, `equity_curve`, `fills`, `simulation_duration_ms`, `total_bars_processed`.
>
> To persist final positions, M13 must first **produce** them. Two paths:
>
> 1. Add a `final_positions` field to `BacktestResult` and populate it from `VedaService`'s portfolio state inside `GretaService.get_result()`.
> 2. Reconstruct positions from `fills` at persistence time in `RunManager`.
>
> This prerequisite work should be sized and sequenced before choosing a storage option. If neither path is tractable within M13 scope, `final_positions` persistence should be deferred to a later milestone.

**Option A: Store `final_positions` as JSONB inside the result row (recommended)**

| Pros                                                                                    | Cons                          |
| --------------------------------------------------------------------------------------- | ----------------------------- |
| Smallest change that satisfies A-6                                                      | Not query-optimized by symbol |
| Matches how the detail page will consume data                                           |                               |
| Avoids inventing a separate position table before there is a positions UI for backtests |                               |

**Option B: Add a `backtest_positions` table**

| Pros                                                        | Cons                                  |
| ----------------------------------------------------------- | ------------------------------------- |
| Better if future queries need per-symbol position snapshots | More migration and repository surface |
| Cleaner if positions become first-class entities later      | No immediate M13 UI needs justify it  |

**Option C: Reconstruct final positions from fills on demand**

| Pros                                | Cons                                                           |
| ----------------------------------- | -------------------------------------------------------------- |
| No extra storage                    | Rebuild cost every request                                     |
| Single source of truth in fill data | Drops explicit audit trail of end-state                        |
|                                     | Conflicts with M13 task wording to persist simulated positions |

**Provisional recommendation**: Option A.

Store final positions explicitly, but keep them embedded until a query-driven use case appears.

---

## 5.3 Task 13-3: What Should `GET /runs/{id}/results` Return?

### 5.3.1 Current State

`/runs` routes currently expose only lifecycle state. There is no results contract in either Pydantic or frontend TypeScript types.

### 5.3.2 Decision Point D-13-3: Results Endpoint Shape

**Option A: One aggregate payload with all M13 data (recommended)**

Suggested response sections:

- `run` summary (id, strategy_id, mode, status, timestamps, error),
- `stats`,
- `final_equity`,
- `equity_curve`,
- `fills`,
- `final_positions`.

| Pros                                   | Cons                                                     |
| -------------------------------------- | -------------------------------------------------------- |
| One request powers the M13 detail page | Payload can grow for long backtests                      |
| Simplest frontend data flow            | Some data may be fetched even if not immediately visible |
| Matches M13 exit gate exactly          |                                                          |

**Option B: Summary-only endpoint, with later subordinate endpoints for curve/fills**

| Pros                           | Cons                                      |
| ------------------------------ | ----------------------------------------- |
| Smaller initial payload        | M13 immediately needs curve and fills     |
| Better for very large datasets | Forces frontend orchestration early       |
|                                | Moves M14-style endpoint fan-out into M13 |

**Option C: Aggregate endpoint with `include=` query parameter**

Example: `GET /runs/{id}/results?include=equity_curve,fills`

| Pros                                                           | Cons                                         |
| -------------------------------------------------------------- | -------------------------------------------- |
| Gives future flexibility without multiple routes               | More complexity in both backend and frontend |
| Lets M13 fetch everything while leaving room to optimize later | Premature sophistication for current scale   |

**Provisional recommendation**: Option A.

Start with the honest payload that the page actually needs. If result size later becomes a problem, that is when to split endpoints or add selective includes.

### 5.3.3 Review Note: HTTP Status Semantics

> **Added during design review.**

The endpoint shape decision above does not cover what the endpoint returns in non-happy-path scenarios. This matters because the frontend `useQuery` error/loading/empty states depend on it.

| Scenario                                                   | Suggested HTTP status                                         | Response body                                                                   |
| ---------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Run does not exist                                         | `404 Not Found`                                               | standard error body                                                             |
| Run exists, not yet completed (PENDING/RUNNING)            | `404 Not Found` with descriptive message, or `204 No Content` | D-13-3B choice below                                                            |
| Run completed, result persisted                            | `200 OK`                                                      | full result payload                                                             |
| Run transitions to ERROR because result persistence failed | `404 Not Found` (result row absent)                           | standard error body; run's `error` field should explain the persistence failure |
| Run in ERROR status                                        | `404 Not Found` (no result to return)                         | standard error body                                                             |

**Decision Point D-13-3B: What should `GET /runs/{id}/results` return when the run exists but has no result yet?**

**Option A: Return `404 Not Found` with a message like "run has not completed yet" (recommended)**

- Simple for frontend: `isError` means "no results to show", page can branch on run status from `GET /runs/{id}`.
- Consistent with REST semantics: the results resource does not exist.

**Option B: Return `204 No Content`**

- Distinguishes "run not found" from "run found, no results yet".
- More nuanced, but frontend needs to handle an extra state.

**Provisional recommendation**: Option A. Frontend can always fetch run status separately to distinguish "not found" from "not ready".

---

## 5.4 Task 13-4: How Should Run Errors Be Exposed?

### 5.4.1 Current State

`RunRecord` already has an `error` column, but:

- internal `Run` dataclass has no `error`,
- `_persist_run()` does not populate error text,
- `RunResponse` has no `error` field,
- frontend `Run` type has no `error` field.

So task 13-4 is not just schema work. It is a state propagation gap.

### 5.4.2 Decision Point D-13-4: Error Propagation Strategy

**Option A: Make `error` a first-class nullable field on `Run`, `RunRecord`, and `RunResponse` (recommended)**

| Pros                                                      | Cons                                         |
| --------------------------------------------------------- | -------------------------------------------- |
| Aligns in-memory state, DB state, and API contract        | Requires touching backend and frontend types |
| Lets list/detail pages show the same durable error source |                                              |
| Simplifies future UX on failed runs                       |                                              |

**Option B: Keep error only in DB, enrich `GET /runs/{id}` from repository reads**

| Pros                                          | Cons                                           |
| --------------------------------------------- | ---------------------------------------------- |
| Avoids changing internal `Run` dataclass much | In-memory truth and persisted truth diverge    |
|                                               | Harder to reason about during active execution |

**Option C: Treat SSE `run.Error` as the only user-visible error channel**

| Pros                  | Cons                                       |
| --------------------- | ------------------------------------------ |
| Lowest backend change | Not durable                                |
|                       | User can miss it entirely                  |
|                       | Contradicts M13 goal of inspectable output |

**Provisional recommendation**: Option A.

---

## 5.5 Task 13-5: When and Where Should Backtest Date Validation Happen?

### 5.5.1 Current State

Backtest date validation currently happens too late.

`RunManager.create()` validates strategy config against JSON Schema, but `_start_backtest()` still does runtime checks for:

- missing `backtest_start`,
- missing `backtest_end`,
- ISO parsing via `datetime.fromisoformat()`.

This means a user can receive HTTP 201, then later fail on start.

### 5.5.2 Decision Point D-13-5A: Validation Layer

**Option A: Validate in `RunManager.create()` only**

| Pros                                           | Cons                                             |
| ---------------------------------------------- | ------------------------------------------------ |
| Close to current logic                         | Validation stays outside request schema contract |
| Easy to add semantic checks before persistence | Less explicit API model behavior                 |

**Option B: Validate in `RunCreate` Pydantic model only**

| Pros                                             | Cons                                                                       |
| ------------------------------------------------ | -------------------------------------------------------------------------- |
| Clear API contract                               | `config` is intentionally opaque and strategy-shaped                       |
| 422 responses are natural for bad request bodies | Hard to express all semantic checks elegantly inside a generic config dict |

**Option C: Hybrid - structural checks in Pydantic, semantic checks in `RunManager.create()` (recommended)**

Suggested split:

- Pydantic: if `mode == backtest`, require both date keys to exist and be parseable,
- RunManager: validate ordering (`start < end`), optional future horizon limits, and any normalization.

| Pros                                                       | Cons                          |
| ---------------------------------------------------------- | ----------------------------- |
| Best error quality for API users                           | Slight duplication of concern |
| Keeps semantic checks near business logic                  |                               |
| Scales better if more backtest creation rules appear later |                               |

**Provisional recommendation**: Option C.

### 5.5.3 Decision Point D-13-5B: Time Semantics

This is easy to miss but important.

Frontend `datetime-local` inputs emit naive timestamps like `2026-04-05T10:30`.
Backend tests and current backtest initialization expect timezone-aware ISO strings like `2024-01-01T09:30:00+00:00`.

**Option A: Keep local datetime inputs, convert to UTC ISO string on submit (recommended)**

| Pros                                | Cons                                                      |
| ----------------------------------- | --------------------------------------------------------- |
| Best browser UX                     | Requires explicit conversion logic in frontend            |
| Preserves user-local input behavior | Users may not realize stored times are UTC unless labeled |

**Option B: Require raw ISO 8601 strings with offsets**

| Pros                   | Cons            |
| ---------------------- | --------------- |
| Most explicit contract | Poor UX         |
| No hidden conversion   | Easy to mistype |

**Option C: Add timezone selector next to local datetime inputs**

| Pros                                            | Cons                     |
| ----------------------------------------------- | ------------------------ |
| Most explicit user control                      | More UI complexity       |
| Future-proof if multi-timezone workflows matter | Overkill for current app |

**Provisional recommendation**: Option A, with explicit label text such as "stored as UTC".

> **Review Note: Backend Timezone Parsing Contract**
>
> Added during design review. Regardless of which frontend option is chosen, the backend must define how it handles incoming date strings:
>
> - If the string has no offset (e.g. `2026-04-05T10:30`), should the backend reject it (422), assume UTC, or assume a configured default timezone?
> - Recommendation: **reject naive strings** at the Pydantic validation layer (D-13-5A Option C), requiring an explicit offset or `Z` suffix. This avoids silent misinterpretation and keeps the contract unambiguous. The frontend conversion in Option A should always append `Z` or `+00:00`.

---

## 6. Frontend Decision Package

## 6.1 Task 13-6: How Should the Backtest Form Be Fixed?

### 6.1.1 Current State

`CreateRunForm` already keeps `configData` in state, but backtest date inputs:

- do not bind `value`,
- do not set `required`,
- write raw `datetime-local` strings into config,
- live outside the schema-driven RJSF form.

### 6.1.2 Decision Point D-13-6: Form Architecture

**Option A: Keep dedicated backtest date controls, but make them controlled and normalized (recommended)**

Suggested shape:

- local `backtestStart` / `backtestEnd` state,
- `value` bound to state,
- `required` enabled,
- submit path converts local input to UTC ISO,
- `configData` receives normalized strings.

| Pros                                           | Cons                                          |
| ---------------------------------------------- | --------------------------------------------- |
| Smallest fix for the exact bug                 | Backtest fields remain partially outside RJSF |
| Keeps strategy `config_schema` ownership clean | Two form styles coexist                       |
| Easy to reason about with current code         |                                               |

**Option B: Build a synthetic schema that merges backtest fields into RJSF**

| Pros                                       | Cons                                                     |
| ------------------------------------------ | -------------------------------------------------------- |
| One rendering system for all fields        | More schema plumbing                                     |
| Centralizes validation and required fields | Backtest lifecycle fields are not really strategy config |
|                                            | Harder to keep mode-specific fields clean                |

**Option C: Replace current mixed form with explicit mode-specific subforms**

| Pros                                          | Cons                                |
| --------------------------------------------- | ----------------------------------- |
| Cleanest long-term UI architecture            | Largest rewrite                     |
| Better if live/paper/backtest diverge further | Too much for the narrow M13 bug fix |

**Provisional recommendation**: Option A.

This is the right M13 move. It fixes correctness without prematurely rebuilding the form stack.

---

## 6.2 Task 13-7: What Should `/runs/:runId` Become?

### 6.2.1 Current State

`App.tsx` routes `/runs/:runId` to `RunsPage`, which just renders a one-row filtered list. This is not a detail page.

### 6.2.2 Decision Point D-13-7: Detail Page Routing Strategy

**Option A: Create a dedicated `RunDetailPage` with an internal Results tab (recommended)**

| Pros                                                          | Cons                                            |
| ------------------------------------------------------------- | ----------------------------------------------- |
| Establishes the right page concept immediately                | One new page component and route wiring         |
| Natural foundation for M14 Monitoring tab and M15 breadcrumbs | Slightly more work than branching in `RunsPage` |
| Avoids further overloading `RunsPage`                         |                                                 |

**Option B: Keep `RunsPage`, but branch deep-link mode into a detail layout**

| Pros                                  | Cons                                              |
| ------------------------------------- | ------------------------------------------------- |
| Fewer new files                       | Preserves an already confused page responsibility |
| Can reuse some existing hooks quickly | Harder to evolve cleanly in M14/M15               |

**Option C: Introduce nested routes now (`/runs/:runId/results`, `/runs/:runId/monitoring`)**

| Pros                                      | Cons                                      |
| ----------------------------------------- | ----------------------------------------- |
| Strong long-term information architecture | More routing ceremony than M13 needs      |
| Good fit for future tabs as real routes   | Extra complexity before enough tabs exist |

**Provisional recommendation**: Option A.

### 6.2.3 Review Note: Detail Page Data Fetching Strategy

> **Added during design review.**

Regardless of routing choice, the detail page needs a clear data fetching plan. Open questions:

1. **One query or two?** Should the page fetch `GET /runs/{id}` and `GET /runs/{id}/results` separately, or does the results endpoint already include enough run metadata (see D-13-3 Option A's `run` summary section) to avoid a second call?
2. **Conditional fetching**: If the run is still `PENDING` or `RUNNING`, the results endpoint will return 404. TanStack Query's `enabled` option should gate the results query on `run.status === 'COMPLETED'`.
3. **Live updates**: While a run is `RUNNING`, should the detail page poll `GET /runs/{id}` for status changes, or listen to SSE for the terminal event? SSE is already wired for run lifecycle events, so it may be more natural.
4. **Recommended approach for M13**: Fetch run via `useRun(runId)`, conditionally fetch results via `useRunResults(runId, { enabled: run?.status === 'COMPLETED' })`. Listen to SSE for status transitions to trigger query invalidation. This keeps TanStack Query as the single data source while leveraging existing SSE infrastructure.

---

## 6.3 Task 13-8: Which Chart Library Should M13 Use?

### 6.3.1 Current State

The frontend has no chart dependency installed yet.

M13 needs only one chart initially: an equity curve line chart.

### 6.3.2 Decision Point D-13-8: Charting Library

**Option A: Recharts (recommended)**

External research:

- official guide positions it as straightforward for SPA installation,
- React-component API is close to current Haro style,
- good fit for moderate-size time series.

| Pros                                                   | Cons                                    |
| ------------------------------------------------------ | --------------------------------------- |
| Lowest conceptual overhead for React developers        | SVG-based, less ideal for huge datasets |
| Composable API maps well to a simple equity curve card | Less feature-rich than ECharts          |
| Easy styling for current dashboard aesthetic           |                                         |

**Option B: Chart.js via `react-chartjs-2`**

External research:

- official docs emphasize canvas rendering and large dataset performance,
- React integration is wrapper-based rather than component-native.

| Pros                                          | Cons                                                  |
| --------------------------------------------- | ----------------------------------------------------- |
| Better performance ceiling than SVG libraries | Requires wrapper package for ergonomic React use      |
| Large community and strong defaults           | Less natural to compose in JSX-heavy UI               |
| Tree-shakable                                 | Styling is more config-centric than component-centric |

**Option C: Apache ECharts via React wrapper**

External research:

- official site emphasizes 20+ chart types, Canvas/SVG rendering, progressive rendering, and accessibility features.

| Pros                                                                  | Cons                                          |
| --------------------------------------------------------------------- | --------------------------------------------- |
| Highest capability ceiling                                            | Heavier mental model and integration cost     |
| Strong future potential for advanced analytics views                  | Overpowered for one simple equity line in M13 |
| Good if zooming/brush/multi-series analytics are near-term priorities |                                               |

**Provisional recommendation**: Option A.

Choose Recharts if M13 wants speed and clarity.
Choose Chart.js only if large backtests are expected immediately.
Choose ECharts only if the owner already knows M16 comparison views will be visualization-heavy.

---

## 6.4 Task 13-9: How Should the Trade Log Be Rendered?

### 6.4.1 Current State

M13 trade log data will come from simulated fills, not from live/paper orders.

Existing `OrderTable` expects `Order` rows and click-to-open modal behavior. A backtest trade log needs columns such as:

- timestamp,
- symbol,
- side,
- qty,
- fill price,
- commission,
- slippage,
- maybe bar index.

### 6.4.2 Decision Point D-13-9: Trade Log Table Strategy

**Option A: Build a dedicated `BacktestTradeLogTable` for simulated fills (recommended)**

| Pros                                             | Cons                |
| ------------------------------------------------ | ------------------- |
| Correct row model for the data                   | One extra component |
| No forced compatibility with live order concepts |                     |
| Easier to add backtest-only columns              |                     |

**Option B: Generalize `OrderTable` into a shared execution table**

| Pros                     | Cons                                            |
| ------------------------ | ----------------------------------------------- |
| Potential reuse later    | Pulls refactor cost into M13                    |
| Could unify visual style | Order rows and fill rows are not the same thing |
|                          | Existing modal behavior becomes awkward         |

**Option C: Introduce TanStack Table for the trade log immediately**

| Pros                                    | Cons                                                     |
| --------------------------------------- | -------------------------------------------------------- |
| Better if sorting/filtering arrive soon | Extra abstraction for a simple first table               |
| Foundation for richer analytics later   | Current app already uses simple HTML tables successfully |

**Provisional recommendation**: Option A.

Keep M13 honest: a backtest fill log is not an order list.

---

## 6.5 Task 13-10: What Is the Right Success Feedback After Create?

### 6.5.1 Current State

The frontend already has notification infrastructure. `useCreateRun()` currently invalidates queries on success but does not show a success message.

### 6.5.2 Decision Point D-13-10: Create Success UX

**Option A: Show an immediate success toast in `useCreateRun.onSuccess` and stay on the current page (recommended default)**

| Pros                         | Cons                                         |
| ---------------------------- | -------------------------------------------- |
| Minimal change               | Does not shorten the path to the result page |
| Uses existing store directly |                                              |
| Matches task wording exactly |                                              |

**Option B: Show success toast and navigate to the new run detail page**

| Pros                                   | Cons                                                                           |
| -------------------------------------- | ------------------------------------------------------------------------------ |
| Better end-to-end research flow        | Requires coordinating create response, route change, and detail-page readiness |
| Makes the new page visible immediately | Slightly more opinionated UX                                                   |

**Option C: Wait for SSE `run.Created` to trigger the toast**

| Pros                     | Cons                                                               |
| ------------------------ | ------------------------------------------------------------------ |
| Event-driven consistency | Delayed or duplicated feedback risk                                |
|                          | SSE is unnecessary for a mutation the client itself just initiated |

**Provisional recommendation**: Option A if keeping M13 lean.

If owner wants the cleanest research flow, Option B is the better UX path once `RunDetailPage` exists.

> **Review Note: Create/Start Separation Undermines Option B**
>
> Added during design review. Option B says "navigate to the new run detail page" after create. But M13 does not merge create and start into one action (that is deferred to M16). So the actual sequence would be:
>
> 1. User clicks Create → `POST /runs` returns `run_id` with status `PENDING`.
> 2. Navigate to `/runs/{run_id}` → detail page shows a run that has not started yet. No results exist.
> 3. User must go back or find a "Start" button on the detail page.
>
> This means Option B's value proposition ("makes the new page visible immediately") is misleading — the page would show an empty/pending state, not results. For Option B to deliver a good UX, `RunDetailPage` would need to handle the pre-start state gracefully (e.g., prominent "Start Backtest" button, or status banner). This is doable but adds scope.
>
> If the owner wants Option B, budget a small detail-page pre-start state design into M13.

---

## 7. External Research Notes

### 7.1 SQLAlchemy + PostgreSQL JSONB

Official SQLAlchemy 2.0 PostgreSQL docs confirm:

- `JSONB` is fully supported,
- it provides containment and key/path operators,
- it is suitable when payload structure is flexible,
- in-place mutations are not auto-detected by the ORM unless mutable helpers are used.

Why this matters for M13:

- JSONB is a viable storage format for `stats`, `equity_curve`, `fills`, and `final_positions`.
- Since M13 persistence will likely save fresh records rather than mutate loaded ones in place, JSONB change tracking is not a blocker.

### 7.2 Charting Libraries

Research summary:

| Library  | External signal                                                   | Best fit               |
| -------- | ----------------------------------------------------------------- | ---------------------- |
| Recharts | simple SPA install, React-component style API                     | fastest M13 delivery   |
| Chart.js | canvas performance, strong defaults, React wrapper ecosystem      | larger datasets        |
| ECharts  | 20+ chart types, Canvas/SVG, progressive rendering, accessibility | future-heavy analytics |

Conclusion:

- If M13 is only an equity line chart, Recharts is the best fit.
- If the owner already expects large datasets or comparison dashboards soon, Chart.js or ECharts may be worth the extra complexity.

---

## 8. Test Impact

The chosen path will affect the following test layers.

### 8.1 Backend

- `RunManager` tests: result capture, persistence success, persistence failure, error field population.
- Route tests: `GET /runs/{id}/results`, `RunResponse.error` serialization.
- Repository tests: new results repository model and CRUD behavior.
- Integration tests: create backtest -> start -> fetch results -> confirm payload.

### 8.2 Frontend

- `CreateRunForm` tests: controlled values, required fields, UTC normalization.
- `useCreateRun` tests: success toast behavior.
- detail-page tests: loading/error/results states.
- chart tests: render smoke test rather than pixel-level assertion.
- trade-log table tests: rows and formatting from fill payload.

### 8.3 E2E

M13 likely deserves at least one e2e happy path after implementation:

1. create backtest,
2. start backtest,
3. open run detail,
4. verify stats card, chart presence, and fill rows.

---

## 9. Decision Summary

| Task  | Decision                | Options                                                         | Provisional recommendation                              |
| ----- | ----------------------- | --------------------------------------------------------------- | ------------------------------------------------------- |
| 13-1  | result capture owner    | RunManager / Greta / async consumer                             | RunManager synchronous capture                          |
| 13-2  | result storage model    | dedicated table / `runs.result` / normalized child tables       | dedicated `backtest_results` table                      |
| 13-2  | final positions storage | JSONB in result / separate table / reconstruct from fills       | JSONB in result row ⚠️ data source gap                  |
| 13-3  | endpoint shape          | aggregate / split endpoints / aggregate with `include=`         | aggregate payload                                       |
| 13-3  | HTTP status semantics   | 404 for missing results / 204 No Content                        | 404 with message                                        |
| 13-4  | error exposure          | first-class run field / DB-only enrich / SSE only               | first-class run field                                   |
| 13-5  | validation layer        | RunManager / Pydantic / hybrid                                  | hybrid                                                  |
| 13-5  | time semantics          | local input -> UTC / raw ISO / timezone selector                | local input -> UTC                                      |
| 13-6  | form architecture       | controlled dedicated fields / merged RJSF / mode subforms       | controlled dedicated fields                             |
| 13-7  | detail page routing     | dedicated page / branch in RunsPage / nested routes             | dedicated page                                          |
| 13-8  | chart library           | Recharts / Chart.js / ECharts                                   | Recharts                                                |
| 13-9  | trade log table         | dedicated fill table / generalized order table / TanStack Table | dedicated fill table                                    |
| 13-10 | create success UX       | toast only / toast + navigate / SSE-driven                      | toast only (or navigate if owner prefers stronger flow) |

---

## 10. Recommended Default Path

If the owner wants the least-regret, fastest path through M13, the default path should be:

1. Capture `BacktestResult` synchronously in `RunManager._start_backtest()`.
2. Persist to a dedicated `backtest_results` table.
3. Store `stats`, `equity_curve`, `fills`, `symbols`, `simulation_duration_ms`, `total_bars_processed`, and (if data source is resolved) `final_positions` as JSONB payload sections inside that row.
4. Add `error` as a first-class nullable run field end-to-end.
5. Validate backtest dates at creation time using a hybrid request-schema + manager validation strategy.
6. Keep the current mixed form architecture, but make backtest date inputs controlled and normalize them to UTC on submit.
7. Introduce a dedicated `RunDetailPage` with a Results tab.
8. Use Recharts for the initial equity curve.
9. Build a dedicated fill-log table for simulated trades.
10. Add immediate success toast on create; optionally upgrade to toast + navigate once detail-page UX is implemented.

This path is not the absolute smallest patch count, but it is the best balance of:

- correctness,
- M13 delivery speed,
- alignment with the audit,
- low conflict with M14 and M16.

---

## 11. Owner Decisions — LOCKED

All decisions locked on 2026-04-05.

| #   | Decision          | Choice                                                                                             |
| --- | ----------------- | -------------------------------------------------------------------------------------------------- |
| 1   | Result storage    | Dedicated `backtest_results` table (Option A)                                                      |
| 2   | Endpoint shape    | One aggregate payload (Option A)                                                                   |
| 3   | Date validation   | Hybrid: Pydantic structural + RunManager semantic (Option C)                                       |
| 4   | Detail page       | Dedicated `RunDetailPage` (Option A)                                                               |
| 5   | Chart library     | Recharts (Option A)                                                                                |
| 6   | Post-create UX    | Toast only, stay on list page (Option A)                                                           |
| 7   | `final_positions` | **Deferred out of M13**. Fills are persisted; positions can be reconstructed. Natural home is M14. |
| 8   | Naive datetime    | Backend rejects naive strings (no offset) with 422. Frontend appends `Z`.                          |

---

## 12. Design Review Log

> **Review date**: 2026-04-05
> **Reviewer**: automated design review
> **Codebase verification**: 14/14 factual claims confirmed accurate.

### Findings integrated into this document:

| #   | Section | Finding                                                                                                                                   | Severity |
| --- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| R-1 | 5.2.2a  | `BacktestResult` has fields (`symbols`, `simulation_duration_ms`, `total_bars_processed`) not reflected in original suggested table shape | Medium   |
| R-2 | 5.2.2b  | No discussion of Alembic migration strategy for new table                                                                                 | Low      |
| R-3 | 5.2.3   | `final_positions` assumed available but does not exist on `BacktestResult` — data source gap                                              | **High** |
| R-4 | 5.3.3   | HTTP status semantics for results endpoint not specified                                                                                  | Medium   |
| R-5 | 6.2.3   | Detail page data fetching strategy (conditional queries, SSE) not discussed                                                               | Medium   |
| R-6 | 6.5.2   | Option B (toast + navigate) undermined by create/start separation                                                                         | Medium   |
| R-7 | 5.5.3   | Backend timezone parsing contract not specified                                                                                           | Low      |
| R-8 | 11      | Two additional owner decisions added (items 7-8)                                                                                          | —        |

---

# PART II — EXECUTION PLAN

> **Convention**: Each phase follows TDD red-green-refactor.
> Write tests FIRST → see them fail → implement → see them pass.
>
> **Branch**: `m13-backtest-results`

---

## 13. Pre-Flight Checklist

```bash
# 1. Backend tests pass
cd /weaver && python -m pytest tests/unit/ -x -q

# 2. Frontend tests pass
cd /weaver/haro && npx vitest run

# 3. TypeScript compiles
cd /weaver/haro && npx tsc --noEmit

# 4. Create branch
cd /weaver && git checkout -b m13-backtest-results
```

---

## 14. Implementation Order

```
Phase 1  Backend Foundation  (13-4 → 13-2 → 13-1)
  error field → result table + migration → capture and persist

Phase 2  Backend API  (13-5, 13-3)
  date validation → results endpoint

Phase 3  Frontend Fixes  (13-6, 13-10)
  form dates → success toast

Phase 4  Frontend Feature  (13-7, 13-8, 13-9)
  install Recharts → detail page + chart + trade log
```

Rationale:

- Phase 1 establishes the data pipeline end-to-end.
- Phase 2 exposes it via the API. Both verified with backend tests alone.
- Phase 3 fixes existing bugs that don't need the new API.
- Phase 4 builds the new UI consuming the results endpoint.

---

## 14a. Phase 0 — Test Infrastructure Updates

> Before writing any M13 test, these shared fixtures must be updated so
> `result_repository` is available everywhere tests need it.

### 14a.1 Factory: `create_run_manager_with_deps()`

**`tests/factories/runs.py`** — add `result_repository` parameter:

At the function signature (L278), change:

```python
def create_run_manager_with_deps(
    event_log: Any | None = None,
    bar_repository: Any | None = None,
    strategy_loader: Any | None = None,
) -> RunManager:
```

to:

```python
def create_run_manager_with_deps(
    event_log: Any | None = None,
    bar_repository: Any | None = None,
    strategy_loader: Any | None = None,
    result_repository: Any | None = None,
) -> RunManager:
```

Before the `return RunManager(...)` block, add:

```python
    # Create result repository if not provided
    if result_repository is None:
        result_repository = AsyncMock()
        result_repository.save = AsyncMock()
        result_repository.get_by_run_id = AsyncMock(return_value=None)
```

Update the return statement:

```python
    return RunManager(
        event_log=event_log,
        bar_repository=bar_repository,
        strategy_loader=strategy_loader,
        result_repository=result_repository,
    )
```

### 14a.2 Conftest: `client` fixture

**`tests/unit/glados/conftest.py`** — seed `result_repository` in `app.state`:

After `app.state.veda_service = None` (L48), add:

```python
        from unittest.mock import AsyncMock
        mock_result_repo = AsyncMock()
        mock_result_repo.save = AsyncMock()
        mock_result_repo.get_by_run_id = AsyncMock(return_value=None)
        app.state.result_repository = mock_result_repo
```

> This makes `TestResultsEndpoint` (§16.2.1) work: the `Depends(get_result_repository)`
> dependency reads from `app.state.result_repository`.

### 14a.3 RunManager constructor (implementation prereq)

**`src/glados/services/run_manager.py`** — `__init__` must accept
`result_repository` (currently only has `event_log`, `bar_repository`,
`strategy_loader`, `run_repository`). Add parameter:

```python
    def __init__(
        self,
        event_log: EventLog | None = None,
        bar_repository: BarRepository | None = None,
        strategy_loader: StrategyLoader | None = None,
        run_repository: RunRepository | None = None,
        result_repository: ResultRepository | None = None,  # M13
    ) -> None:
```

And in body: `self._result_repository = result_repository`.

---

## 15. Phase 1 — Backend Foundation

### 15.1 Task 13-4: `error` Field on Run Pipeline

**Decision**: D-13-4 🔒 Option A — first-class nullable field end-to-end.

> `RunRecord.error` already exists in the DB model (`src/walle/models.py` L183).
> The gap is: `Run` dataclass has no `error`; `_persist_run()` never maps it;
> `RunResponse` never returns it; `_start_backtest()` never sets it.

**Files to modify**:

| File                                          | What                                   |
| --------------------------------------------- | -------------------------------------- |
| `src/glados/services/run_manager.py` L49      | Add `error` to `Run` dataclass         |
| `src/glados/services/run_manager.py` L146     | Map `error` in `_persist_run()`        |
| `src/glados/services/run_manager.py` L449     | Set `run.error` in `_start_backtest()` |
| `src/glados/schemas.py` RunResponse           | Add `error: str \| None = None`        |
| `src/glados/routes/runs.py` \_run_to_response | Add `error=run.error`                  |
| `haro/src/api/types.ts` Run                   | Add `error?: string \| null`           |

#### 15.1.1 Tests (RED)

**`tests/unit/glados/test_run_manager_backtest.py`** — add:

```python
class TestRunErrorField:
    """M13-4: error field propagation."""

    async def test_run_dataclass_has_error_field(self):
        from src.glados.services.run_manager import Run
        run = Run(
            id="test", strategy_id="s1", mode=RunMode.BACKTEST,
            status=RunStatus.PENDING, config={},
            created_at=datetime.now(UTC),
        )
        assert run.error is None

    async def test_run_with_error_set(self):
        from src.glados.services.run_manager import Run
        run = Run(
            id="test", strategy_id="s1", mode=RunMode.BACKTEST,
            status=RunStatus.ERROR, config={},
            created_at=datetime.now(UTC),
            error="Something went wrong",
        )
        assert run.error == "Something went wrong"

    async def test_persist_run_includes_error(self, run_manager):
        from src.glados.services.run_manager import Run
        run = Run(
            id="err-run", strategy_id="s1", mode=RunMode.BACKTEST,
            status=RunStatus.ERROR, config={},
            created_at=datetime.now(UTC),
            error="Backtest date parse failed",
        )
        await run_manager._persist_run(run)
        record = run_manager._run_repository.save.call_args[0][0]
        assert record.error == "Backtest date parse failed"
```

**`tests/unit/glados/routes/test_runs.py`** — add:

```python
class TestRunResponseErrorField:
    """M13-4: RunResponse includes error."""

    def test_run_response_includes_error_field(self, client):
        response = client.get("/api/v1/runs/run-1")
        data = response.json()
        assert "error" in data
```

```bash
python -m pytest tests/unit/glados/test_run_manager_backtest.py::TestRunErrorField -x
# expect ImportError / AttributeError
```

#### 15.1.2 Implement (GREEN)

**`src/glados/services/run_manager.py`** — `Run` dataclass, add after `stopped_at` (L50):

```python
    error: str | None = None
```

**`src/glados/services/run_manager.py`** — `_persist_run()`, add after `stopped_at=run.stopped_at,` (L146):

```python
            error=run.error,
```

**`src/glados/services/run_manager.py`** — `_start_backtest()`, after the `error_msg` line (L450):

```python
                run.error = error_msg
```

**`src/glados/schemas.py`** — `RunResponse`, add after `stopped_at`:

```python
    error: str | None = None
```

**`src/glados/routes/runs.py`** — `_run_to_response()`, add keyword arg:

```python
        error=run.error,
```

**`haro/src/api/types.ts`** — `Run` interface, add after `stopped_at?`:

```typescript
  error?: string | null;
```

```bash
python -m pytest tests/unit/glados/test_run_manager_backtest.py::TestRunErrorField -x
python -m pytest tests/unit/glados/routes/test_runs.py::TestRunResponseErrorField -x
# expect pass
```

---

### 15.2 Task 13-2: `backtest_results` Table and Repository

**Decision**: D-13-2 🔒 Option A — dedicated table. `final_positions` deferred to M14.

#### 15.2.1 Model Tests (RED)

**New file**: `tests/unit/walle/test_result_repository.py`

```python
"""BacktestResultRecord model and ResultRepository tests."""
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import inspect as sa_inspect
from src.walle.models import BacktestResultRecord, Base


class TestBacktestResultRecordModel:

    def test_tablename(self):
        assert BacktestResultRecord.__tablename__ == "backtest_results"

    def test_columns_exist(self):
        mapper = sa_inspect(BacktestResultRecord)
        names = {c.key for c in mapper.mapper.columns}
        expected = {
            "run_id", "start_time", "end_time", "timeframe", "symbols",
            "final_equity", "simulation_duration_ms", "total_bars_processed",
            "stats", "equity_curve", "fills", "created_at",
        }
        assert expected.issubset(names)

    def test_run_id_is_primary_key(self):
        mapper = sa_inspect(BacktestResultRecord)
        pk = [c.name for c in mapper.mapper.primary_key]
        assert pk == ["run_id"]

    def test_registered_in_base_metadata(self):
        assert "backtest_results" in Base.metadata.tables
```

```bash
python -m pytest tests/unit/walle/test_result_repository.py -x
# expect ImportError
```

#### 15.2.2 Model Implementation (GREEN)

**`src/walle/models.py`** — add before `FillRecord` (insert after `RunRecord.__repr__`, around L194):

> The model goes between `RunRecord` and `FillRecord`. Because `Base` already
> maps `dict[str, Any]` → `JSONB`, we just annotate as `dict[str, Any]`.

```python
class BacktestResultRecord(Base):
    """
    Persisted backtest result — one-to-one with RunRecord.

    Stores the complete output of a completed backtest: stats,
    equity curve, fills, and metadata. Created by M13.
    """

    __tablename__ = "backtest_results"

    run_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    symbols: Mapped[dict[str, Any]] = mapped_column(nullable=False)      # list[str] as JSONB
    final_equity: Mapped[str] = mapped_column(String(50), nullable=False) # Decimal as string
    simulation_duration_ms: Mapped[int] = mapped_column(nullable=False, default=0)
    total_bars_processed: Mapped[int] = mapped_column(nullable=False, default=0)
    stats: Mapped[dict[str, Any]] = mapped_column(nullable=False)        # BacktestStats as dict
    equity_curve: Mapped[dict[str, Any]] = mapped_column(nullable=False) # list[{t, equity}]
    fills: Mapped[dict[str, Any]] = mapped_column(nullable=False)        # list[fill_dict]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<BacktestResultRecord run_id={self.run_id}>"
```

```bash
python -m pytest tests/unit/walle/test_result_repository.py::TestBacktestResultRecordModel -x
# expect pass
```

#### 15.2.3 Repository Tests (RED)

Append to `tests/unit/walle/test_result_repository.py`:

```python
class TestResultRepositoryInterface:

    def test_constructor_accepts_session_factory(self):
        from src.walle.repositories.result_repository import ResultRepository
        repo = ResultRepository(session_factory=MagicMock())
        assert repo._session_factory is not None

    def test_has_save_method(self):
        from src.walle.repositories.result_repository import ResultRepository
        assert callable(getattr(ResultRepository, "save", None))

    def test_has_get_by_run_id_method(self):
        from src.walle.repositories.result_repository import ResultRepository
        assert callable(getattr(ResultRepository, "get_by_run_id", None))
```

```bash
python -m pytest tests/unit/walle/test_result_repository.py::TestResultRepositoryInterface -x
# expect ImportError
```

#### 15.2.4 Repository Implementation (GREEN)

**New file**: `src/walle/repositories/result_repository.py`

```python
"""ResultRepository — CRUD for BacktestResultRecord."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.walle.models import BacktestResultRecord


class ResultRepository:
    """Repository for backtest result persistence."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, record: BacktestResultRecord) -> None:
        async with self._session_factory() as session:
            await session.merge(record)
            await session.commit()

    async def get_by_run_id(self, run_id: str) -> BacktestResultRecord | None:
        async with self._session_factory() as session:
            stmt = select(BacktestResultRecord).where(
                BacktestResultRecord.run_id == run_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
```

```bash
python -m pytest tests/unit/walle/test_result_repository.py -x
# expect pass
```

#### 15.2.5 Alembic Migration

```bash
cd /weaver
DB_URL="postgresql+asyncpg://weaver:weaver_dev_password@localhost:5432/weaverdb" \
  alembic revision --autogenerate -m "add_backtest_results_table"
```

Review the generated file, then apply:

```bash
DB_URL="..." alembic upgrade head
```

#### 15.2.6 Wire at Startup

**`src/glados/app.py`** — after `run_repository = RunRepository(...)` (around L155):

```python
        from src.walle.repositories.result_repository import ResultRepository
        result_repository = ResultRepository(database.session_factory)
```

Update RunManager init (around L157):

```python
    run_manager = RunManager(
        event_log=event_log,
        bar_repository=bar_repository,
        strategy_loader=strategy_loader,
        run_repository=run_repository,
        result_repository=result_repository,  # NEW
    )
```

Add to app state:

```python
    app.state.result_repository = result_repository
```

**`src/glados/services/run_manager.py`** — `__init__()`, add param (after `run_repository`):

```python
        result_repository: ResultRepository | None = None,
```

Store it:

```python
        self._result_repository = result_repository
```

Add import at top:

```python
from src.walle.repositories.result_repository import ResultRepository
```

---

### 15.3 Task 13-1: Capture and Persist Result

**Decision**: D-13-1 🔒 Option A — synchronous in `_start_backtest`, before cleanup.

#### 15.3.1 Tests (RED)

**`tests/unit/glados/test_run_manager_backtest.py`** — add:

> These tests need the `manager_with_deps` fixture to include
> `result_repository=AsyncMock()`. Update the fixture in
> `TestRunManagerBacktestStart` (or create an identical one in
> `TestResultCapture`) by adding `result_repository` to the
> `RunManager(...)` constructor call, matching §14a.1.

```python
class TestResultCapture:
    """M13-1: capture and persist backtest result."""

    @pytest_asyncio.fixture
    async def manager_with_deps(self) -> RunManager:
        """Create manager with mocked dependencies including result_repository."""
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])

        mock_strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.initialize = AsyncMock()
        mock_strategy.on_tick = AsyncMock(return_value=[])
        mock_strategy_loader.load = MagicMock(return_value=mock_strategy)
        mock_strategy_loader.get_meta = MagicMock(return_value=None)

        mock_result_repo = AsyncMock()
        mock_result_repo.save = AsyncMock()
        mock_result_repo.get_by_run_id = AsyncMock(return_value=None)

        return RunManager(
            event_log=mock_event_log,
            bar_repository=mock_bar_repo,
            strategy_loader=mock_strategy_loader,
            result_repository=mock_result_repo,
        )

    async def test_completed_backtest_persists_result(self, manager_with_deps: RunManager) -> None:
        """result_repository.save() called on successful backtest."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )
        await manager_with_deps.start(run.id)
        assert manager_with_deps._result_repository.save.called
        record = manager_with_deps._result_repository.save.call_args[0][0]
        assert record.run_id == run.id

    async def test_result_record_has_correct_fields(self, manager_with_deps: RunManager) -> None:
        """Persisted record contains stats, equity_curve, fills."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )
        await manager_with_deps.start(run.id)
        record = manager_with_deps._result_repository.save.call_args[0][0]
        assert record.timeframe == "1m"
        assert isinstance(record.stats, dict)
        assert isinstance(record.equity_curve, list)
        assert isinstance(record.fills, list)

    async def test_result_persistence_failure_marks_error(self, manager_with_deps: RunManager) -> None:
        """If _persist_result fails, run should transition to ERROR."""
        manager_with_deps._result_repository.save.side_effect = Exception("DB fail")
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )
        await manager_with_deps.start(run.id)
        updated = await manager_with_deps.get(run.id)
        assert updated.status == RunStatus.ERROR
        assert "DB fail" in updated.error

    async def test_failed_backtest_does_not_capture(self, manager_with_deps: RunManager) -> None:
        """ERROR backtest should NOT persist results."""
        # Make strategy.on_tick raise to simulate failure
        mock_strategy = manager_with_deps._strategy_loader.load.return_value
        mock_strategy.on_tick.side_effect = RuntimeError("Strategy crash")
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )
        await manager_with_deps.start(run.id)
        assert not manager_with_deps._result_repository.save.called

    async def test_result_repository_none_skips_persist(self, manager_with_deps: RunManager) -> None:
        """If result_repository is None, _persist_result is a no-op."""
        manager_with_deps._result_repository = None
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )
        # Should not raise
        await manager_with_deps.start(run.id)
        assert run.status == RunStatus.COMPLETED
```

```bash
python -m pytest tests/unit/glados/test_run_manager_backtest.py::TestResultCapture -x
# expect failures (no _persist_result exists)
```

#### 15.3.2 Implement (GREEN)

**`src/glados/services/run_manager.py`** — add method after `_persist_run()`:

```python
    async def _persist_result(self, result: BacktestResult) -> None:
        """Persist a backtest result to the result repository."""
        if self._result_repository is None:
            return
        from src.walle.models import BacktestResultRecord

        record = BacktestResultRecord(
            run_id=result.run_id,
            start_time=result.start_time,
            end_time=result.end_time,
            timeframe=result.timeframe,
            symbols=result.symbols,
            final_equity=str(result.final_equity),
            simulation_duration_ms=result.simulation_duration_ms,
            total_bars_processed=result.total_bars_processed,
            stats={
                "total_return": str(result.stats.total_return),
                "total_return_pct": str(result.stats.total_return_pct),
                "annualized_return": str(result.stats.annualized_return),
                "sharpe_ratio": str(result.stats.sharpe_ratio) if result.stats.sharpe_ratio is not None else None,
                "sortino_ratio": str(result.stats.sortino_ratio) if result.stats.sortino_ratio is not None else None,
                "max_drawdown": str(result.stats.max_drawdown),
                "max_drawdown_pct": str(result.stats.max_drawdown_pct),
                "total_trades": result.stats.total_trades,
                "winning_trades": result.stats.winning_trades,
                "losing_trades": result.stats.losing_trades,
                "win_rate": str(result.stats.win_rate),
                "avg_win": str(result.stats.avg_win),
                "avg_loss": str(result.stats.avg_loss),
                "profit_factor": str(result.stats.profit_factor) if result.stats.profit_factor is not None else None,
                "total_bars": result.stats.total_bars,
                "bars_in_position": result.stats.bars_in_position,
                "total_commission": str(result.stats.total_commission),
                "total_slippage": str(result.stats.total_slippage),
            },
            equity_curve=[
                {"t": point[0].isoformat(), "equity": str(point[1])}
                for point in result.equity_curve
            ],
            fills=[
                {
                    "order_id": f.order_id,
                    "client_order_id": f.client_order_id,
                    "symbol": f.symbol,
                    "side": f.side.value,
                    "qty": str(f.qty),
                    "fill_price": str(f.fill_price),
                    "commission": str(f.commission),
                    "slippage": str(f.slippage),
                    "timestamp": f.timestamp.isoformat(),
                    "bar_index": f.bar_index,
                }
                for f in result.fills
            ],
        )
        await self._result_repository.save(record)
```

Add import at top:

```python
from src.greta.models import BacktestResult
```

**`src/glados/services/run_manager.py`** — modify `_start_backtest()`.

Find the `else` block that sets `run.status = RunStatus.COMPLETED` (around L452).
Replace:

```python
            else:
                run.status = RunStatus.COMPLETED
```

With:

```python
            else:
                run.status = RunStatus.COMPLETED
                # M13-1: capture and persist result before cleanup
                try:
                    bt_result = ctx.greta.get_result()
                    await self._persist_result(bt_result)
                except Exception as persist_err:
                    run.status = RunStatus.ERROR
                    run.error = f"Result persistence failed: {persist_err}"
                    logger.error(
                        "Backtest %s result persistence failed: %s",
                        run.id, persist_err,
                    )
```

```bash
python -m pytest tests/unit/glados/test_run_manager_backtest.py -x -q
python -m pytest tests/unit/walle/test_result_repository.py -x -q
# expect all pass
```

---

## 16. Phase 2 — Backend API

### 16.1 Task 13-5: Validate Backtest Dates

**Decisions**: D-13-5A 🔒 Option C (hybrid), D-13-5B 🔒 Option A (reject naive).

**Files to modify**:

| File                                          | What                                           |
| --------------------------------------------- | ---------------------------------------------- |
| `src/glados/schemas.py` RunCreate             | Pydantic `model_validator` — structural checks |
| `src/glados/services/run_manager.py` create() | Semantic check: end > start                    |
| `src/glados/routes/runs.py` create_run        | Catch ValueError → 422                         |

#### 16.1.1 Tests (RED)

**`tests/unit/glados/routes/test_runs.py`** — add:

```python
class TestBacktestDateValidation:
    """M13-5: validate dates at creation time."""

    def test_missing_start_returns_422(self, client):
        resp = client.post("/api/v1/runs", json={
            "strategy_id": "test", "mode": "backtest",
            "config": {"symbols": ["BTC/USD"], "timeframe": "1m",
                       "backtest_end": "2024-01-01T16:00:00Z"},
        })
        assert resp.status_code == 422

    def test_missing_end_returns_422(self, client):
        resp = client.post("/api/v1/runs", json={
            "strategy_id": "test", "mode": "backtest",
            "config": {"symbols": ["BTC/USD"], "timeframe": "1m",
                       "backtest_start": "2024-01-01T09:30:00Z"},
        })
        assert resp.status_code == 422

    def test_naive_datetime_returns_422(self, client):
        resp = client.post("/api/v1/runs", json={
            "strategy_id": "test", "mode": "backtest",
            "config": {"symbols": ["BTC/USD"], "timeframe": "1m",
                       "backtest_start": "2024-01-01T09:30:00",
                       "backtest_end": "2024-01-01T16:00:00"},
        })
        assert resp.status_code == 422

    def test_end_before_start_returns_422(self, client):
        resp = client.post("/api/v1/runs", json={
            "strategy_id": "test", "mode": "backtest",
            "config": {"symbols": ["BTC/USD"], "timeframe": "1m",
                       "backtest_start": "2024-01-02T09:30:00Z",
                       "backtest_end": "2024-01-01T16:00:00Z"},
        })
        assert resp.status_code == 422

    def test_valid_dates_returns_201(self, client):
        resp = client.post("/api/v1/runs", json={
            "strategy_id": "test", "mode": "backtest",
            "config": {"symbols": ["BTC/USD"], "timeframe": "1m",
                       "backtest_start": "2024-01-01T09:30:00Z",
                       "backtest_end": "2024-01-01T16:00:00Z"},
        })
        assert resp.status_code == 201

    def test_paper_mode_skips_date_validation(self, client):
        resp = client.post("/api/v1/runs", json={
            "strategy_id": "test", "mode": "paper",
            "config": {"symbols": ["BTC/USD"], "timeframe": "1m"},
        })
        assert resp.status_code == 201
```

#### 16.1.2 Implement (GREEN)

**`src/glados/schemas.py`** — add `model_validator` to `RunCreate`:

```python
from pydantic import model_validator

class RunCreate(BaseModel):
    # ... existing fields ...

    @model_validator(mode="after")
    def validate_backtest_dates(self) -> RunCreate:
        if self.mode != RunMode.BACKTEST:
            return self
        config = self.config
        for key in ("backtest_start", "backtest_end"):
            value = config.get(key)
            if value is None:
                raise ValueError(f"Backtest mode requires '{key}' in config")
            try:
                dt = datetime.fromisoformat(str(value))
            except (ValueError, TypeError) as e:
                raise ValueError(f"'{key}' is not a valid ISO datetime: {value}") from e
            if dt.tzinfo is None:
                raise ValueError(
                    f"'{key}' must include timezone (append 'Z' for UTC). Got: {value}"
                )
        return self
```

**`src/glados/services/run_manager.py`** — in `create()`, after JSON Schema check, before `Run(...)`:

```python
        # M13-5: Semantic date validation for backtest
        if request.mode == RunMode.BACKTEST:
            start_dt = datetime.fromisoformat(str(request.config["backtest_start"]))
            end_dt = datetime.fromisoformat(str(request.config["backtest_end"]))
            if end_dt <= start_dt:
                raise ValueError("backtest_end must be after backtest_start")
```

**`src/glados/routes/runs.py`** — wrap `create()` call in `create_run`:

```python
    try:
        run = await run_manager.create(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
```

(Add `from fastapi import HTTPException` if not present.)

```bash
python -m pytest tests/unit/glados/routes/test_runs.py::TestBacktestDateValidation -x
```

---

### 16.2 Task 13-3: Results Endpoint

**Decisions**: D-13-3 🔒 Option A (aggregate), D-13-3B 🔒 Option A (404 for missing).

#### 16.2.1 Tests (RED)

**`tests/unit/glados/routes/test_runs.py`** — add:

> The `client` fixture already seeds `app.state.result_repository` as an
> `AsyncMock` (§14a.2). `TestResultsEndpoint` needs the mock to return
> real data for "run-1" and `None` otherwise. Use a `@pytest.fixture(autouse=True)`
> to wire this per-class:

````python
from unittest.mock import MagicMock

class TestResultsEndpoint:
    """M13-3: GET /runs/{id}/results."""

    @pytest.fixture(autouse=True)
    def _seed_result_repo(self, client):
        """Seed result_repository with a mock BacktestResultRecord for run-1."""
        mock_record = MagicMock()
        mock_record.run_id = "run-1"
        mock_record.start_time = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        mock_record.end_time = datetime(2024, 1, 1, 16, 0, tzinfo=UTC)
        mock_record.timeframe = "1m"
        mock_record.symbols = ["BTC/USD"]
        mock_record.final_equity = "102500.00"
        mock_record.simulation_duration_ms = 150
        mock_record.total_bars_processed = 390
        mock_record.stats = {
            "total_return": "2500.00", "total_return_pct": "2.50",
            "annualized_return": "125.00", "sharpe_ratio": "1.85",
            "sortino_ratio": "2.10", "max_drawdown": "1200.00",
            "max_drawdown_pct": "1.17", "total_trades": 8,
            "winning_trades": 5, "losing_trades": 3,
            "win_rate": "62.50", "avg_win": "800.00", "avg_loss": "333.33",
            "profit_factor": "2.40", "total_bars": 390,
            "bars_in_position": 210, "total_commission": "16.00",
            "total_slippage": "8.50",
        }
        mock_record.equity_curve = [
            {"t": "2024-01-01T09:30:00Z", "equity": "100000.00"},
            {"t": "2024-01-01T16:00:00Z", "equity": "102500.00"},
        ]
        mock_record.fills = [
            {"order_id": "o1", "client_order_id": "co1", "symbol": "BTC/USD",
             "side": "buy", "qty": "0.5", "fill_price": "43000.00",
             "commission": "2.00", "slippage": "1.00",
             "timestamp": "2024-01-01T09:35:00Z", "bar_index": 5},
        ]

        async def mock_get_by_run_id(run_id: str):
            return mock_record if run_id == "run-1" else None

        repo = client.app.state.result_repository
        repo.get_by_run_id = AsyncMock(side_effect=mock_get_by_run_id)

    def test_missing_run_returns_404(self, client):
        resp = client.get("/api/v1/runs/nonexistent/results")
        assert resp.status_code == 404

    def test_no_result_returns_404(self, client):
        resp = client.get("/api/v1/runs/run-2/results")  # running, no result
        assert resp.status_code == 404

    def test_happy_path_returns_200(self, client):
        resp = client.get("/api/v1/runs/run-1/results")
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "equity_curve" in data
        assert "fills" in data

    def test_response_shape(self, client):
        resp = client.get("/api/v1/runs/run-1/results")
        data = resp.json()
        assert data["run_id"] == "run-1"
        assert "start_time" in data
        assert "end_time" in data
        assert "final_equity" in data
        assert data["final_equity"] == "102500.00"

    def test_stats_fields_present(self, client):
        resp = client.get("/api/v1/runs/run-1/results")
        stats = resp.json()["stats"]
        expected_keys = {
            "total_return", "total_return_pct", "sharpe_ratio",
            "max_drawdown", "total_trades", "win_rate", "profit_factor",
        }
        assert expected_keys.issubset(stats.keys())

    def test_equity_curve_is_list(self, client):
        resp = client.get("/api/v1/runs/run-1/results")
        curve = resp.json()["equity_curve"]
        assert isinstance(curve, list)
        assert len(curve) == 2
        assert "t" in curve[0]
        assert "equity" in curve[0]

#### 16.2.2 Schemas Implementation

**`src/glados/schemas.py`** — add after existing schemas:

```python
class BacktestStatsResponse(BaseModel):
    total_return: str
    total_return_pct: str
    annualized_return: str
    sharpe_ratio: str | None = None
    sortino_ratio: str | None = None
    max_drawdown: str
    max_drawdown_pct: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: str
    avg_win: str
    avg_loss: str
    profit_factor: str | None = None
    total_bars: int
    bars_in_position: int
    total_commission: str
    total_slippage: str


class SimulatedFillResponse(BaseModel):
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    qty: str
    fill_price: str
    commission: str
    slippage: str
    timestamp: str
    bar_index: int


class EquityCurvePoint(BaseModel):
    t: str
    equity: str


class BacktestResultResponse(BaseModel):
    run_id: str
    start_time: datetime
    end_time: datetime
    timeframe: str
    symbols: list[str]
    final_equity: str
    simulation_duration_ms: int
    total_bars_processed: int
    stats: BacktestStatsResponse
    equity_curve: list[EquityCurvePoint]
    fills: list[SimulatedFillResponse]
````

#### 16.2.3 Dependency

**`src/glados/dependencies.py`** — add:

```python
from src.walle.repositories.result_repository import ResultRepository

def get_result_repository(request: Request) -> ResultRepository:
    return request.app.state.result_repository
```

#### 16.2.4 Route

**`src/glados/routes/runs.py`** — add endpoint:

```python
from src.glados.schemas import BacktestResultResponse
from src.glados.dependencies import get_result_repository
from src.walle.repositories.result_repository import ResultRepository

@router.get("/{run_id}/results", response_model=BacktestResultResponse)
async def get_run_results(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
    result_repository: ResultRepository = Depends(get_result_repository),
) -> BacktestResultResponse:
    run = await run_manager.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    record = await result_repository.get_by_run_id(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No results for run {run_id}")

    return BacktestResultResponse(
        run_id=record.run_id,
        start_time=record.start_time,
        end_time=record.end_time,
        timeframe=record.timeframe,
        symbols=record.symbols,
        final_equity=record.final_equity,
        simulation_duration_ms=record.simulation_duration_ms,
        total_bars_processed=record.total_bars_processed,
        stats=record.stats,
        equity_curve=record.equity_curve,
        fills=record.fills,
    )
```

```bash
python -m pytest tests/unit/glados/routes/test_runs.py -x -q
# Full backend regression:
python -m pytest tests/unit/ -x -q
```

---

## 17. Phase 3 — Frontend Fixes

### 17.1 Task 13-6: Fix Backtest Form Dates

**Decision**: D-13-6 🔒 Option A — controlled fields + UTC.

**File**: `haro/src/components/runs/CreateRunForm.tsx`

#### 17.1.1 Tests (RED)

**`haro/tests/unit/components/CreateRunForm.test.tsx`** — add:

```typescript
describe("CreateRunForm — M13-6 backtest dates", () => {
  it("date inputs have required attribute", async () => {
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/mode/i), "backtest");
    expect(screen.getByLabelText(/start.*date/i)).toHaveAttribute("required");
    expect(screen.getByLabelText(/end.*date/i)).toHaveAttribute("required");
  });

  it("date inputs are controlled", async () => {
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/mode/i), "backtest");
    const input = screen.getByLabelText(/start.*date/i) as HTMLInputElement;
    await user.type(input, "2024-01-01T09:30");
    expect(input.value).toBe("2024-01-01T09:30");
  });

  it("submitted dates have timezone suffix", async () => {
    const onSubmit = vi.fn();
    render(<CreateRunForm onSubmit={onSubmit} onCancel={vi.fn()} />);
    const user = userEvent.setup();

    // Select backtest mode
    await user.selectOptions(screen.getByLabelText(/mode/i), "backtest");
    // Select strategy
    await waitFor(() => {
      expect(screen.getByLabelText(/strategy/i)).toBeInTheDocument();
    });
    await user.selectOptions(screen.getByLabelText(/strategy/i), "sma-crossover");

    // Fill in required fields
    const startInput = screen.getByLabelText(/start.*date/i) as HTMLInputElement;
    const endInput = screen.getByLabelText(/end.*date/i) as HTMLInputElement;
    await user.type(startInput, "2024-01-01T09:30");
    await user.type(endInput, "2024-01-01T16:00");

    // Submit
    await user.click(screen.getByRole("button", { name: /create/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalled());

    const submitted = onSubmit.mock.calls[0][0];
    expect(submitted.config.backtest_start).toMatch(/Z$|[+-]\d{2}:\d{2}$/);
    expect(submitted.config.backtest_end).toMatch(/Z$|[+-]\d{2}:\d{2}$/);
  });

  it("hides date fields when mode is paper", async () => {
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/mode/i), "paper");
    expect(screen.queryByLabelText(/start.*date/i)).not.toBeInTheDocument();
  });
});
```

#### 17.1.2 Implement (GREEN)

**`haro/src/components/runs/CreateRunForm.tsx`**:

1. Add state:

```typescript
const [backtestStart, setBacktestStart] = useState("");
const [backtestEnd, setBacktestEnd] = useState("");
```

2. Add helper:

```typescript
function toUTCISO(localValue: string): string {
  return localValue ? `${localValue}:00Z` : "";
}
```

3. Replace uncontrolled date `<input>` elements with controlled ones using
   `value`, `onChange`, and `required` attributes. On change, also update
   config data via `setConfigData` with `toUTCISO(e.target.value)`.

```bash
cd /weaver/haro && npx vitest run tests/unit/components/CreateRunForm.test.tsx
```

---

### 17.2 Task 13-10: Success Toast

**Decision**: D-13-10 🔒 Option A — toast only, stay on list.

**File**: `haro/src/hooks/useRuns.ts`

#### 17.2.1 Test (RED)

**`haro/tests/unit/hooks/useRuns.test.tsx`** — add:

```typescript
describe("useCreateRun — M13-10 success toast", () => {
  it("shows success notification on creation", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useCreateRun(), { wrapper });
    await act(async () => {
      result.current.mutate({
        strategy_id: "sma-crossover",
        mode: "backtest",
        config: { symbols: ["BTC/USD"], timeframe: "1m" },
      });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe("success");
  });
});
```

#### 17.2.2 Implement (GREEN)

**`haro/src/hooks/useRuns.ts`** — in `useCreateRun`, update `onSuccess`:

```typescript
import { useNotificationStore } from "../stores/notificationStore";

// Inside useCreateRun:
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: runKeys.lists() });
  useNotificationStore.getState().addNotification({
    type: "success",
    message: "Run created successfully",
  });
},
```

```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useRuns.test.tsx
```

---

## 18. Phase 4 — Frontend Feature

### 18.0 Install Recharts

```bash
cd /weaver/haro && npm install recharts react-is
```

> `react-is` is a peer dep of Recharts. Verify `package.json` updated.

### 18.1 Add Frontend Types, API, Hook, MSW Handler

#### 18.1.1 Types

**`haro/src/api/types.ts`** — append:

```typescript
// ── Backtest Results (M13) ──────────────────────────────────

export interface BacktestStats {
  total_return: string;
  total_return_pct: string;
  annualized_return: string;
  sharpe_ratio: string | null;
  sortino_ratio: string | null;
  max_drawdown: string;
  max_drawdown_pct: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;
  avg_win: string;
  avg_loss: string;
  profit_factor: string | null;
  total_bars: number;
  bars_in_position: number;
  total_commission: string;
  total_slippage: string;
}

export interface SimulatedFill {
  order_id: string;
  client_order_id: string;
  symbol: string;
  side: string;
  qty: string;
  fill_price: string;
  commission: string;
  slippage: string;
  timestamp: string;
  bar_index: number;
}

export interface EquityCurvePoint {
  t: string;
  equity: string;
}

export interface BacktestResult {
  run_id: string;
  start_time: string;
  end_time: string;
  timeframe: string;
  symbols: string[];
  final_equity: string;
  simulation_duration_ms: number;
  total_bars_processed: number;
  stats: BacktestStats;
  equity_curve: EquityCurvePoint[];
  fills: SimulatedFill[];
}
```

#### 18.1.2 API Function

**`haro/src/api/runs.ts`** — add import + function:

```typescript
import type { BacktestResult } from "./types";

export async function fetchRunResults(runId: string): Promise<BacktestResult> {
  return get<BacktestResult>(`/runs/${runId}/results`);
}
```

#### 18.1.3 Hook

**`haro/src/hooks/useRuns.ts`** — add key factory entry + hook:

```typescript
export const runKeys = {
  // ... existing
  results: (id: string) => [...runKeys.all, "results", id] as const,
};

export function useRunResults(runId: string, options?: { enabled?: boolean }) {
  return useQuery<BacktestResult>({
    queryKey: runKeys.results(runId),
    queryFn: () => fetchRunResults(runId),
    enabled: options?.enabled ?? true,
  });
}
```

#### 18.1.4 MSW Mock Data & Handler

**`haro/tests/mocks/handlers.ts`** — add mock data + handler:

```typescript
export const mockBacktestResult: BacktestResult = {
  run_id: "run-1",
  start_time: "2024-01-01T09:30:00Z",
  end_time: "2024-01-01T16:00:00Z",
  timeframe: "1m",
  symbols: ["BTC/USD"],
  final_equity: "102500.00",
  simulation_duration_ms: 150,
  total_bars_processed: 390,
  stats: {
    total_return: "2500.00",
    total_return_pct: "2.50",
    annualized_return: "125.00",
    sharpe_ratio: "1.85",
    sortino_ratio: "2.10",
    max_drawdown: "1200.00",
    max_drawdown_pct: "1.17",
    total_trades: 8,
    winning_trades: 5,
    losing_trades: 3,
    win_rate: "62.50",
    avg_win: "800.00",
    avg_loss: "333.33",
    profit_factor: "2.40",
    total_bars: 390,
    bars_in_position: 210,
    total_commission: "16.00",
    total_slippage: "8.50",
  },
  equity_curve: [
    { t: "2024-01-01T09:30:00Z", equity: "100000.00" },
    { t: "2024-01-01T12:00:00Z", equity: "101500.00" },
    { t: "2024-01-01T16:00:00Z", equity: "102500.00" },
  ],
  fills: [
    {
      order_id: "o1", client_order_id: "co1", symbol: "BTC/USD",
      side: "buy", qty: "0.5", fill_price: "43000.00",
      commission: "2.00", slippage: "1.00",
      timestamp: "2024-01-01T09:35:00Z", bar_index: 5,
    },
    {
      order_id: "o2", client_order_id: "co2", symbol: "BTC/USD",
      side: "sell", qty: "0.5", fill_price: "43500.00",
      commission: "2.00", slippage: "1.00",
      timestamp: "2024-01-01T11:00:00Z", bar_index: 90,
    },
  ],
};

// Add to handlers array:
http.get("/api/v1/runs/:runId/results", ({ params }) => {
  const runId = params.runId as string;
  if (runId === "run-1") return HttpResponse.json(mockBacktestResult);
  return new HttpResponse(null, { status: 404 });
}),
```

#### 18.1.5 Hook Test

**`haro/tests/unit/hooks/useRuns.test.tsx`** — add:

```typescript
describe("useRunResults", () => {
  it("fetches results for completed run", async () => {
    const { result } = renderHook(() => useRunResults("run-1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.stats.total_trades).toBe(8);
  });

  it("returns error for missing run", async () => {
    const { result } = renderHook(() => useRunResults("nonexistent"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("respects enabled=false", () => {
    const { result } = renderHook(
      () => useRunResults("run-1", { enabled: false }),
      { wrapper: createWrapper() },
    );
    expect(result.current.fetchStatus).toBe("idle");
  });
});
```

---

### 18.2 Task 13-8: Equity Curve Chart

**Decision**: D-13-8 🔒 Recharts.

**New file**: `haro/src/components/results/EquityCurveChart.tsx`

```tsx
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { EquityCurvePoint } from "../../api/types";

interface Props {
  data: EquityCurvePoint[];
}

export function EquityCurveChart({ data }: Props) {
  const chartData = data.map((p) => ({
    time: new Date(p.t).toLocaleString(),
    equity: parseFloat(p.equity),
  }));

  if (chartData.length === 0)
    return <div className="text-gray-400">No equity data</div>;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-lg font-semibold text-white mb-4">Equity Curve</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
          <YAxis
            stroke="#9CA3AF"
            fontSize={12}
            tickFormatter={(v: number) => `$${v.toLocaleString()}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1F2937",
              border: "1px solid #374151",
              borderRadius: "0.375rem",
              color: "#F9FAFB",
            }}
            formatter={(v: number) => [`$${v.toLocaleString()}`, "Equity"]}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**Test**: `haro/tests/unit/components/EquityCurveChart.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "../../utils";
import { EquityCurveChart } from "../../../src/components/results/EquityCurveChart";

describe("EquityCurveChart", () => {
  it("renders heading", () => {
    render(
      <EquityCurveChart
        data={[
          { t: "2024-01-01T09:30:00Z", equity: "100000" },
          { t: "2024-01-01T10:00:00Z", equity: "101000" },
        ]}
      />,
    );
    expect(screen.getByText("Equity Curve")).toBeInTheDocument();
  });

  it("shows empty message when no data", () => {
    render(<EquityCurveChart data={[]} />);
    expect(screen.getByText(/no equity data/i)).toBeInTheDocument();
  });
});
```

> **jsdom note**: `ResponsiveContainer` needs `ResizeObserver`. If tests
> fail, add to `haro/tests/setup.ts`:
>
> ```typescript
> global.ResizeObserver = class {
>   observe() {}
>   unobserve() {}
>   disconnect() {}
> };
> ```

---

### 18.3 Task 13-9: Trade Log Table

**Decision**: D-13-9 🔒 Option A — dedicated `BacktestTradeLogTable`.

**New file**: `haro/src/components/results/BacktestTradeLogTable.tsx`

```tsx
import type { SimulatedFill } from "../../api/types";

interface Props {
  fills: SimulatedFill[];
}

export function BacktestTradeLogTable({ fills }: Props) {
  if (fills.length === 0) return <div className="text-gray-400">No trades</div>;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-lg font-semibold text-white mb-4">
        Trade Log ({fills.length} fills)
      </h2>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm text-left text-gray-300">
          <thead className="text-xs uppercase text-gray-500 border-b border-gray-700">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Symbol</th>
              <th className="px-3 py-2">Side</th>
              <th className="px-3 py-2 text-right">Qty</th>
              <th className="px-3 py-2 text-right">Price</th>
              <th className="px-3 py-2 text-right">Commission</th>
              <th className="px-3 py-2 text-right">Slippage</th>
              <th className="px-3 py-2 text-right">Bar</th>
            </tr>
          </thead>
          <tbody>
            {fills.map((f, i) => (
              <tr
                key={`${f.order_id}-${i}`}
                className="border-b border-gray-700/50 hover:bg-gray-700/30"
              >
                <td className="px-3 py-2 whitespace-nowrap">
                  {new Date(f.timestamp).toLocaleString()}
                </td>
                <td className="px-3 py-2">{f.symbol}</td>
                <td
                  className={`px-3 py-2 font-medium ${
                    f.side === "buy" ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {f.side.toUpperCase()}
                </td>
                <td className="px-3 py-2 text-right">{f.qty}</td>
                <td className="px-3 py-2 text-right">${f.fill_price}</td>
                <td className="px-3 py-2 text-right">${f.commission}</td>
                <td className="px-3 py-2 text-right">${f.slippage}</td>
                <td className="px-3 py-2 text-right">{f.bar_index}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

**Test**: `haro/tests/unit/components/BacktestTradeLogTable.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "../../utils";
import { BacktestTradeLogTable } from "../../../src/components/results/BacktestTradeLogTable";
import { mockBacktestResult } from "../../mocks/handlers";

describe("BacktestTradeLogTable", () => {
  it("renders fills as rows", () => {
    render(<BacktestTradeLogTable fills={mockBacktestResult.fills} />);
    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getByText("BUY")).toBeInTheDocument();
    expect(screen.getByText(/2 fills/)).toBeInTheDocument();
  });

  it("shows empty message", () => {
    render(<BacktestTradeLogTable fills={[]} />);
    expect(screen.getByText(/no trades/i)).toBeInTheDocument();
  });

  it("colors BUY green and SELL red", () => {
    render(<BacktestTradeLogTable fills={mockBacktestResult.fills} />);
    expect(screen.getByText("BUY").className).toContain("text-green-400");
    expect(screen.getByText("SELL").className).toContain("text-red-400");
  });
});
```

---

### 18.4 Stats Card

**New file**: `haro/src/components/results/BacktestStatsCard.tsx`

```tsx
import type { BacktestStats } from "../../api/types";

interface Props {
  stats: BacktestStats;
  finalEquity: string;
}

export function BacktestStatsCard({ stats, finalEquity }: Props) {
  const items = [
    {
      label: "Final Equity",
      value: `$${parseFloat(finalEquity).toLocaleString()}`,
    },
    {
      label: "Total Return",
      value: `${stats.total_return_pct}%`,
      color:
        parseFloat(stats.total_return_pct) >= 0
          ? "text-green-400"
          : "text-red-400",
    },
    { label: "Sharpe Ratio", value: stats.sharpe_ratio ?? "N/A" },
    { label: "Max Drawdown", value: `${stats.max_drawdown_pct}%` },
    { label: "Total Trades", value: String(stats.total_trades) },
    { label: "Win Rate", value: `${stats.win_rate}%` },
    { label: "Profit Factor", value: stats.profit_factor ?? "N/A" },
    { label: "Sortino Ratio", value: stats.sortino_ratio ?? "N/A" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {items.map((item) => (
        <div key={item.label} className="bg-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase">{item.label}</p>
          <p
            className={`text-lg font-semibold mt-1 ${item.color ?? "text-white"}`}
          >
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}
```

**Test**: `haro/tests/unit/components/BacktestStatsCard.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "../../utils";
import { BacktestStatsCard } from "../../../src/components/results/BacktestStatsCard";
import { mockBacktestResult } from "../../mocks/handlers";

describe("BacktestStatsCard", () => {
  it("renders all 8 stat cards", () => {
    render(
      <BacktestStatsCard
        stats={mockBacktestResult.stats}
        finalEquity={mockBacktestResult.final_equity}
      />,
    );
    expect(screen.getByText("Final Equity")).toBeInTheDocument();
    expect(screen.getByText("Total Return")).toBeInTheDocument();
    expect(screen.getByText("Sharpe Ratio")).toBeInTheDocument();
    expect(screen.getByText("Max Drawdown")).toBeInTheDocument();
    expect(screen.getByText("Total Trades")).toBeInTheDocument();
    expect(screen.getByText("Win Rate")).toBeInTheDocument();
    expect(screen.getByText("Profit Factor")).toBeInTheDocument();
    expect(screen.getByText("Sortino Ratio")).toBeInTheDocument();
  });

  it("formats final equity with dollar sign", () => {
    render(
      <BacktestStatsCard
        stats={mockBacktestResult.stats}
        finalEquity="102500.00"
      />,
    );
    expect(screen.getByText("$102,500")).toBeInTheDocument();
  });

  it("shows positive return in green", () => {
    render(
      <BacktestStatsCard
        stats={mockBacktestResult.stats}
        finalEquity="102500.00"
      />,
    );
    const returnEl = screen.getByText("2.50%");
    expect(returnEl.className).toContain("text-green-400");
  });

  it("shows negative return in red", () => {
    const negativeStats = {
      ...mockBacktestResult.stats,
      total_return_pct: "-3.20",
    };
    render(<BacktestStatsCard stats={negativeStats} finalEquity="96800.00" />);
    const returnEl = screen.getByText("-3.20%");
    expect(returnEl.className).toContain("text-red-400");
  });

  it("shows N/A for null sharpe_ratio", () => {
    const noSharpe = { ...mockBacktestResult.stats, sharpe_ratio: null };
    render(<BacktestStatsCard stats={noSharpe} finalEquity="100000" />);
    // Two N/A values expected when sharpe is null (sharpe + any other nulls)
    const naElements = screen.getAllByText("N/A");
    expect(naElements.length).toBeGreaterThanOrEqual(1);
  });
});
```

---

### 18.5 Task 13-7: RunDetailPage

**Decision**: D-13-7 🔒 Option A — dedicated page.

**New file**: `haro/src/pages/RunDetailPage.tsx`

```tsx
import { useParams, Link } from "react-router-dom";
import { useRun, useRunResults } from "../hooks/useRuns";
import { EquityCurveChart } from "../components/results/EquityCurveChart";
import { BacktestTradeLogTable } from "../components/results/BacktestTradeLogTable";
import { BacktestStatsCard } from "../components/results/BacktestStatsCard";

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const { data: run, isLoading, isError } = useRun(runId!);
  const { data: results, isLoading: resultsLoading } = useRunResults(runId!, {
    enabled: run?.status === "completed",
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading...</div>;
  if (isError || !run) {
    return (
      <div className="p-6">
        <p className="text-red-400">Run not found</p>
        <Link
          to="/runs"
          className="text-blue-400 hover:underline mt-2 inline-block"
        >
          ← Back to runs
        </Link>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <Link to="/runs" className="text-blue-400 hover:underline text-sm">
          ← Runs
        </Link>
        <h1 className="text-2xl font-bold text-white mt-1">Run {run.id}</h1>
        <p className="text-gray-400 text-sm">
          {run.strategy_id} · {run.mode} ·{" "}
          <span
            className={
              run.status === "completed"
                ? "text-green-400"
                : run.status === "error"
                  ? "text-red-400"
                  : run.status === "running"
                    ? "text-blue-400"
                    : "text-gray-400"
            }
          >
            {run.status}
          </span>
        </p>
        {run.error && (
          <p className="text-red-400 text-sm mt-1">Error: {run.error}</p>
        )}
      </div>

      {run.status === "completed" && resultsLoading && (
        <div className="text-gray-400">Loading results...</div>
      )}

      {results && (
        <>
          <BacktestStatsCard
            stats={results.stats}
            finalEquity={results.final_equity}
          />
          <div data-testid="equity-curve-chart">
            <EquityCurveChart data={results.equity_curve} />
          </div>
          <BacktestTradeLogTable fills={results.fills} />
        </>
      )}

      {run.status !== "completed" && run.status !== "error" && (
        <div className="text-gray-400">
          Run is {run.status}. Results appear when the backtest completes.
        </div>
      )}
    </div>
  );
}
```

**`haro/src/App.tsx`** — update `/runs/:runId` route:

```tsx
import { RunDetailPage } from "./pages/RunDetailPage";
// Replace the existing route element for /runs/:runId:
<Route path="/runs/:runId" element={<RunDetailPage />} />;
```

**Test**: `haro/tests/unit/pages/RunDetailPage.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "../../utils";
import { RunDetailPage } from "../../../src/pages/RunDetailPage";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

function renderPage(runId: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/runs/${runId}`]}>
        <Routes>
          <Route path="/runs/:runId" element={<RunDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RunDetailPage", () => {
  it("shows run ID", async () => {
    renderPage("run-1");
    await waitFor(() => expect(screen.getByText(/run-1/i)).toBeInTheDocument());
  });

  it("shows stats for completed run", async () => {
    renderPage("run-1");
    await waitFor(() =>
      expect(screen.getByText(/total return/i)).toBeInTheDocument(),
    );
  });

  it("shows equity chart", async () => {
    renderPage("run-1");
    await waitFor(() =>
      expect(screen.getByTestId("equity-curve-chart")).toBeInTheDocument(),
    );
  });

  it("shows trade log", async () => {
    renderPage("run-1");
    await waitFor(() =>
      expect(screen.getByText("BTC/USD")).toBeInTheDocument(),
    );
  });

  it("shows not found for bad ID", async () => {
    renderPage("nonexistent");
    await waitFor(() =>
      expect(screen.getByText(/not found/i)).toBeInTheDocument(),
    );
  });
});
```

---

### 18.6 SSE Results Invalidation

**`haro/src/hooks/useSSE.ts`** — in the `run.Completed` listener, add:

```typescript
queryClient.invalidateQueries({ queryKey: ["runs", "results", data.run_id] });
```

---

## 19. Post-Flight Verification

### 19.1 Full Test Suite

```bash
# Backend
cd /weaver && python -m pytest tests/unit/ -x -q

# Frontend
cd /weaver/haro && npx vitest run

# TypeScript
cd /weaver/haro && npx tsc --noEmit
```

### 19.2 Expected Test Counts

| Suite         | Before | New | Expected |
| ------------- | ------ | --- | -------- |
| Backend unit  | ~987   | ~29 | ~1016    |
| Frontend unit | ~109   | ~23 | ~132     |

**Backend breakdown (29 new):**

| Class                           | File                           | Count |
| ------------------------------- | ------------------------------ | ----- |
| `TestRunErrorField`             | `test_run_manager_backtest.py` | 3     |
| `TestRunResponseErrorField`     | `routes/test_runs.py`          | 1     |
| `TestBacktestResultRecordModel` | `test_result_repository.py`    | 4     |
| `TestResultRepositoryInterface` | `test_result_repository.py`    | 3     |
| `TestResultCapture`             | `test_run_manager_backtest.py` | 6     |
| `TestBacktestDateValidation`    | `routes/test_runs.py`          | 6     |
| `TestResultsEndpoint`           | `routes/test_runs.py`          | 6     |

**Frontend breakdown (23 new):**

| describe block             | File                             | Count |
| -------------------------- | -------------------------------- | ----- |
| CreateRunForm dates        | `CreateRunForm.test.tsx`         | 4     |
| useCreateRun success toast | `useRuns.test.tsx`               | 1     |
| useRunResults              | `useRuns.test.tsx`               | 3     |
| EquityCurveChart           | `EquityCurveChart.test.tsx`      | 2     |
| BacktestTradeLogTable      | `BacktestTradeLogTable.test.tsx` | 3     |
| BacktestStatsCard          | `BacktestStatsCard.test.tsx`     | 5     |
| RunDetailPage              | `RunDetailPage.test.tsx`         | 5     |

### 19.3 Exit Gate Checklist

| #   | Criterion                                  | Verification                        |
| --- | ------------------------------------------ | ----------------------------------- |
| 1   | Result captured after completion           | `TestResultCapture` passes          |
| 2   | Result persisted to `backtest_results`     | Repository + manager tests pass     |
| 3   | `GET /runs/{id}/results` returns aggregate | `TestResultsEndpoint` passes        |
| 4   | `RunResponse` includes `error`             | Route test + type check             |
| 5   | Backtest dates validated at creation       | `TestBacktestDateValidation` passes |
| 6   | Form dates controlled + required + UTC     | Form component tests pass           |
| 7   | `/runs/:runId` → RunDetailPage             | Page tests pass                     |
| 8   | Equity curve renders via Recharts          | Chart component test passes         |
| 9   | Trade log shows fills                      | Trade log component test passes     |
| 10  | Toast on run creation                      | Hook test passes                    |
| 11  | All existing tests pass                    | Full regression                     |
| 12  | TypeScript clean                           | `tsc --noEmit` exits 0              |

---

## 20. File Change Summary

### New Files

| File                                                        | Purpose                  |
| ----------------------------------------------------------- | ------------------------ |
| `src/walle/repositories/result_repository.py`               | `ResultRepository` CRUD  |
| `src/walle/migrations/versions/..._add_backtest_results.py` | Alembic migration        |
| `tests/unit/walle/test_result_repository.py`                | Model + repository tests |
| `haro/src/pages/RunDetailPage.tsx`                          | Run detail page          |
| `haro/src/components/results/EquityCurveChart.tsx`          | Equity curve chart       |
| `haro/src/components/results/BacktestTradeLogTable.tsx`     | Trade log table          |
| `haro/src/components/results/BacktestStatsCard.tsx`         | Stats grid card          |
| `haro/tests/unit/pages/RunDetailPage.test.tsx`              | Detail page tests        |
| `haro/tests/unit/components/EquityCurveChart.test.tsx`      | Chart tests              |
| `haro/tests/unit/components/BacktestTradeLogTable.test.tsx` | Trade log tests          |
| `haro/tests/unit/components/BacktestStatsCard.test.tsx`     | Stats card tests         |

### Modified Files

| File                                         | Changes                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `src/glados/services/run_manager.py`         | `Run.error`, `_persist_result()`, result capture, date validation, `result_repository` param |
| `src/glados/schemas.py`                      | `RunResponse.error`, date validator, result response schemas                                 |
| `src/glados/routes/runs.py`                  | Results endpoint, ValueError→422                                                             |
| `src/glados/dependencies.py`                 | `get_result_repository()`                                                                    |
| `src/glados/app.py`                          | Wire `ResultRepository`                                                                      |
| `src/walle/models.py`                        | `BacktestResultRecord` model                                                                 |
| `haro/src/api/types.ts`                      | Result types, `Run.error`                                                                    |
| `haro/src/api/runs.ts`                       | `fetchRunResults()`                                                                          |
| `haro/src/hooks/useRuns.ts`                  | `useRunResults()`, success toast                                                             |
| `haro/src/hooks/useSSE.ts`                   | Results invalidation                                                                         |
| `haro/src/App.tsx`                           | Route → RunDetailPage                                                                        |
| `haro/src/components/runs/CreateRunForm.tsx` | Controlled date inputs                                                                       |
| `haro/package.json`                          | `recharts`, `react-is`                                                                       |
| `haro/tests/mocks/handlers.ts`               | Results mock + handler                                                                       |
| `tests/factories/runs.py`                    | Add `result_repository` param                                                                |
| `tests/unit/glados/conftest.py`              | Seed `result_repository` in `app.state`                                                      |

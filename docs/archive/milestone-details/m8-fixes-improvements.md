# M8: Critical Fixes & Improvements — Detailed Implementation Plan

> **Document Charter**  
> **Primary role**: M8 milestone detailed implementation guide.  
> **Authoritative for**: M8 task breakdown, file-level change specs, test requirements, and execution order.  
> **Not authoritative for**: milestone summary status (use `MILESTONE_PLAN.md`).

> **Status**: 🔄 ACTIVE (started 2026-02-19; M8-Q core tasks completed on 2026-02-25)  
> **Prerequisite**: M7 ✅ (894 tests: 808 backend + 86 frontend)  
> **Target**: ~40–50 new tests → cumulative ~934–944  
> **Estimated Effort**: 1.5–2 weeks  
> **Design Decisions**: All 5 (D-1–D-5) locked ✅  
> **Key Inputs**: `DESIGN_AUDIT.md`, `INDEPENDENT_DESIGN_REVIEW.md`, `DESIGN_REVIEW_PLAN.md`

---

## Table of Contents

1. [Summary of Review Findings](#1-summary-of-review-findings)
2. [Undecided Items — Resolution Status](#2-undecided-items--resolution-status)
3. [Execution Order & Dependencies](#3-execution-order--dependencies)
4. [M8-P0: Critical Contract Fixes](#4-m8-p0-critical-contract-fixes)
5. [M8-P1: Runtime Wiring (Packages A/B/C)](#5-m8-p1-runtime-wiring-packages-abc)
6. [M8-Q: Code Quality & P1 Fixes](#6-m8-q-code-quality--p1-fixes)
7. [M8-D: Documentation](#7-m8-d-documentation)
8. [Exit Gate](#8-exit-gate)

---

## 1. Summary of Review Findings

### 1.1 Issue Registry (all sources consolidated)

| ID   | Issue                                                           | Sev    | Phase    | Status  |
| ---- | --------------------------------------------------------------- | ------ | -------- | ------- |
| C-01 | SSE event casing mismatch (`run.Started` vs `run.started`)      | **P0** | M8-P0    | ✅ Done |
| C-02 | Missing `POST /runs/{id}/start` route                           | **P0** | M8-P0    | ✅ Done |
| C-03 | Health endpoint path mismatch (`/healthz` vs `/api/v1/healthz`) | **P0** | M8-P0    | ✅ Done |
| C-04 | Order read/write source split (GET=Mock, POST=Veda)             | **P0** | M8-P0    | ✅ Done |
| N-01 | PostgresEventLog `append()` never dispatches to subscribers     | **P0** | M8-P1-B  | ✅ Done |
| N-02 | `_start_live()` zero error handling — ghost zombie runs         | **P0** | M8-P0    | ✅ Done |
| N-07 | InMemory vs Postgres EventLog behavioral parity broken          | **P0** | M8-P1-B  | ✅ Done |
| —    | DomainRouter not wired in app lifespan                          | **P0** | M8-P1-B  | ✅ Done |
| —    | RunManager missing `bar_repository` / `strategy_loader`         | **P0** | M8-P1-A  | ✅ Done |
| —    | Per-run cleanup not guaranteed on stop/complete                 | **P0** | M8-P1-A  | ✅ Done |
| N-03 | Fill history lost on persistence round-trip                     | **P1** | M8-Q     | ✅ Done |
| N-04 | AlpacaAdapter blocks event loop — sync SDK in async             | **P1** | M8-Q     | ✅ Done |
| N-06 | SSE has no run_id filtering                                     | **P1** | M8-Q     | ✅ Done |
| N-09 | `time_in_force` default inconsistency                           | **P1** | M8-P0    | ✅ Done |
| N-10 | Frontend sends pagination params backend ignores                | **P1** | M8-Q     | ✅ Done |
| N-05 | StrategyAction stringly-typed                                   | **P2** | M8-Q     | ✅ Done |
| N-08 | BacktestResult stats mostly zeros                               | **P2** | M8-Q     | ✅ Done |
| M-01 | `ALL_EVENT_TYPES` missing 3 events                              | **P0** | M8-P0    | ✅ Done |
| M-02 | No server-side pagination/filtering                             | 🟡     | M8-Q     | ✅ Done |
| M-03 | Frontend `orders.Cancelled` not handled                         | 🟡     | M8-P0    | ✅ Done |
| M-04 | `SimulatedFill.side` still `str` not `OrderSide`                | 🟡     | M8-Q     | ✅ Done |
| M-05 | PositionTracker market values always zero                       | 🟡     | Deferred | —       |
| M-06 | SSE event format undocumented                                   | 🟡     | M8-D     | ⏳ Open |
| M-07 | Unused `/runs/:runId` route param in frontend                   | 🟡     | M8-Q     | ✅ Done |
| L-01 | 3 orphan/dead files                                             | 🟢     | M8-Q     | ✅ Done |
| L-02 | 3 outstanding TODO/FIXME                                        | 🟢     | M8-Q     | ✅ Done |
| L-03 | Dual `Bar` type definitions                                     | 🟢     | M8-D     | ⏳ Open |
| L-04 | veda.md env var names mismatch                                  | 🟢     | M8-D     | ⏳ Open |
| L-05 | veda.md OrderStatus enum incomplete                             | 🟢     | M8-D     | ⏳ Open |

### 1.2 Design Decisions — All Locked ✅

| #   | Question                                          | Chosen Option                                 | Rationale                                                                |
| --- | ------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------ |
| D-1 | PostgresEventLog subscriber dispatch model        | **(a)** Direct dispatch in append + pg_notify | Ensures behavioral parity with InMemoryEventLog for in-process consumers |
| D-2 | Should runs be persisted to database?             | **(b)** Add runs table                        | Enables restart recovery and durable run history                         |
| D-3 | Should fills be persisted separately?             | **(b)** Separate fills table                  | Fill history is audit-critical for trading ops                           |
| D-4 | DomainRouter: standalone or inline in RunManager? | **(a)** Separate wired singleton              | Cleaner separation; can serve multiple RunManagers                       |
| D-5 | SSE run_id filtering?                             | **(a)** Yes, via query param                  | Frontend can focus on a specific run's events                            |

**No remaining undecided decisions.** All 5 design decisions (D-1–D-5) were locked on 2026-02-19 before M8 execution began.

---

## 2. Undecided Items — Resolution Status

All major design decisions are resolved. The following implementation-level micro-decisions remain and are resolved inline in each task section below:

| Item                                        | Resolution                                                                                                        |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Health path: add prefix or change frontend? | **Add `/api/v1` prefix to health router** (aligns with all other routes, simpler than special-casing the client)  |
| SSE casing: change frontend or backend?     | **Change frontend to match backend PascalCase** (backend constants already used everywhere in tests; less churn)  |
| `time_in_force` default: "day" or "gtc"?    | **"day"** (safer default for most orders; matches schema; update VedaService handler to use schema default)       |
| Package B implementation: B1 or B2?         | **B1 (direct app-lifespan wiring)** for now — only 3 consumers; reassess at 10+ (per independent review advice)   |
| No-DB publish/stream policy?                | **Wire InMemoryEventLog in app lifespan** when no DB_URL; SSE works in-memory mode without persistence guarantees |
| Mock fallback in no-DB mode for orders?     | **Yes** — MockOrderService remains the read/write source when VedaService is `None` (degraded mode)               |

---

## 3. Execution Order & Dependencies

```
M8-P0: Critical Contract Fixes (no deps, do first)
  ├── C-01  SSE casing fix
  ├── C-02  Start route + tests
  ├── C-03  Health path fix
  ├── C-04  Order source unification
  ├── N-02  _start_live error handling
  ├── N-09  time_in_force unification
  ├── M-01  ALL_EVENT_TYPES completeness
  └── M-03  orders.Cancelled listener
      │
      ▼
M8-P1: Runtime Wiring (depends on P0)
  ├── Package A: Run Lifecycle (depends on C-02)
  │   ├── A.1  Inject RunManager dependencies
  │   ├── A.2  Per-run cleanup guarantees
  │   └── A.3  Integration: start → run → stop lifecycle
  ├── Package B: Event Pipeline (depends on M-01)
  │   ├── B.1  PostgresEventLog direct dispatch (D-1)
  │   ├── B.2  Wire DomainRouter in lifespan (D-4)
  │   ├── B.3  Wire InMemoryEventLog in no-DB mode
  │   └── B.4  Integration: event → subscriber → SSE
  └── Package C: Data Source Unification (depends on C-04)
      ├── C.1  Unify list/get orders to VedaService (DB mode)
      └── C.2  Integration: write → read order parity
          │
          ▼
M8-Q: Code Quality & P1 Fixes (depends on P0, parallel with P1)
  ├── N-03  Fills table + persistence (D-3)
  ├── D-2   Runs table for restart recovery
  ├── N-04  AlpacaAdapter async wrapping
  ├── N-06  SSE run_id filtering (D-5)
  ├── N-10  Server-side pagination
  ├── M-04  SimulatedFill.side enum
  ├── N-05  StrategyAction enum refactor
  ├── N-08  Backtest stats computation
  ├── M-07  RunsPage runId param
  ├── L-01  Delete orphan files
  └── L-02  Resolve TODOs
      │
      ▼
M8-D: Documentation (after P0+P1, parallel with Q)
  ├── Create greta.md, marvin.md, walle.md
  ├── SSE wire format doc
  ├── Error handling strategy doc
  ├── Fix ARCHITECTURE.md false claims
  └── Fix veda.md env vars + OrderStatus
```

---

## 4. M8-P0: Critical Contract Fixes

> **Estimated Tests**: ~15  
> **Priority**: Must complete before any other M8 work  
> **Principle**: TDD — write failing test first, then fix code

### 4.1 C-01: SSE Event Casing Fix

**Problem**: Frontend `useSSE.ts` listens for `run.started` (lowercase) but backend emits `run.Started` (PascalCase). SSE `addEventListener` is case-sensitive — 4/7 listeners are dead.

**Decision**: Change frontend to match backend PascalCase.

**Files to modify**:
| File | Change |
|------|--------|
| `haro/src/hooks/useSSE.ts` | Lines 68, 76, 84, 92: change `run.started` → `run.Started`, `run.stopped` → `run.Stopped`, `run.completed` → `run.Completed`, `run.error` → `run.Error` |
| `haro/tests/unit/hooks/useSSE.test.tsx` | Update all test expectations to use PascalCase event names |

**Implementation Steps**:

1. RED: Update tests to expect PascalCase event names → tests fail
2. GREEN: Update `useSSE.ts` event listeners to PascalCase
3. REFACTOR: Add a comment documenting the PascalCase convention for SSE events

**Tests** (~2):

- `test: run SSE events use PascalCase matching backend (run.Started, run.Stopped, run.Completed, run.Error)`
- `test: order SSE events remain PascalCase (orders.Created, orders.Filled, orders.Rejected)`

---

### 4.2 C-02: Add `POST /runs/{id}/start` Route

**Problem**: Frontend `startRun(runId)` calls `POST /api/v1/runs/{runId}/start`, but the backend has no such route. `RunManager.start()` exists but is unrouted.

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/routes/runs.py` | Add `@router.post("/{run_id}/start")` handler calling `run_manager.start(run_id)` |
| `src/glados/schemas.py` | Add `RunStartResponse` schema if needed (or reuse `RunResponse`) |

**Implementation Steps**:

1. RED: Write test for `POST /runs/{run_id}/start` in `tests/unit/glados/routes/test_runs.py`
2. GREEN: Add route handler in `routes/runs.py`:
   ```python
   @router.post("/{run_id}/start", response_model=RunResponse)
   async def start_run(
       run_id: str,
       run_manager: RunManager = Depends(get_run_manager),
   ) -> RunResponse:
       run = await run_manager.start(run_id)
       if run is None:
           raise HTTPException(status_code=404, detail="Run not found")
       return _run_to_response(run)
   ```
3. REFACTOR: Ensure `start()` returns the Run object; add error handling for already-running

**Tests** (~3):

- `test: POST /runs/{id}/start returns 200 + RunResponse with RUNNING status`
- `test: POST /runs/{id}/start with unknown id returns 404`
- `test: POST /runs/{id}/start on already-running run returns 409`

---

### 4.3 C-03: Fix Health Endpoint Path

**Problem**: Backend registers health at `/healthz` (no prefix). Frontend prepends `/api/v1` → calls `/api/v1/healthz` → 404.

**Decision**: Add `/api/v1` prefix to health router (consistent with all other routes).

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/routes/health.py` | Change `APIRouter()` to `APIRouter(prefix="/api/v1")` or change route to `"/api/v1/healthz"` |
| `src/glados/app.py` | Verify health_router registration (may need `prefix="/api/v1"` in `include_router`) |
| `tests/unit/glados/routes/test_health.py` | Update test paths from `/healthz` to `/api/v1/healthz` |

**Implementation Steps**:

1. RED: Update tests to call `/api/v1/healthz` → tests fail
2. GREEN: Update health router prefix
3. Verify: Ensure frontend `api/health.ts` call path resolves correctly

**Tests** (~2):

- `test: GET /api/v1/healthz returns 200 with status=ok`
- `test: health response includes version string`

---

### 4.4 C-04: Unify Order Read/Write Sources

**Problem**: `POST /orders` and `DELETE /orders/{id}` use `VedaService`, but `GET /orders` and `GET /orders/{id}` use `MockOrderService`. Orders created via Veda are invisible to list/get.

**Decision**: When `VedaService` is configured (DB mode), use it for all operations. When `None` (no-DB mode), fall back to `MockOrderService` for reads (degraded mode).

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/routes/orders.py` | Update `list_orders` and `get_order` to try VedaService first, fall back to MockOrderService |

**Implementation Steps**:

1. RED: Write test — create order via VedaService, then list orders → expect the created order appears
2. GREEN: Update `list_orders()`:
   ```python
   @router.get("", response_model=OrderListResponse)
   async def list_orders(
       run_id: str | None = None,
       veda_service: VedaService | None = Depends(get_veda_service),
       order_service: MockOrderService = Depends(get_order_service),
   ) -> OrderListResponse:
       if veda_service is not None:
           orders = await veda_service.list_orders(run_id=run_id)
           return OrderListResponse(
               orders=[_state_to_response(o) for o in orders],
               total=len(orders),
           )
       # Fallback: degraded mode (no DB)
       orders = order_service.get_orders()
       return OrderListResponse(
           orders=[_order_to_response(o) for o in orders],
           total=len(orders),
       )
   ```
3. Same pattern for `get_order()`
4. REFACTOR: Add comment explaining DB vs no-DB fallback

**Tests** (~3):

- `test: GET /orders uses VedaService when configured`
- `test: GET /orders falls back to MockOrderService when VedaService is None`
- `test: GET /orders/{id} uses VedaService when configured`

---

### 4.5 N-02: Add Error Handling to `_start_live()`

**Problem**: `_start_live()` has no try/except. If the clock or runner fails, the run stays RUNNING forever (zombie run). Compare with `_start_backtest()` which has proper error handling.

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/services/run_manager.py` | Wrap `_start_live()` body in try/except/finally matching `_start_backtest()` pattern |

**Implementation Steps**:

1. RED: Write test — inject a strategy that raises during live run → expect run transitions to ERROR
2. GREEN: Add try/except/finally to `_start_live()`:
   ```python
   async def _start_live(self, run: Run, context: RunContext) -> None:
       try:
           await context.clock.start()
           # ... existing live run logic
       except Exception as e:
           run.status = RunStatus.ERROR
           run.error = str(e)
           await self._emit_event(RunEvents.ERROR, run, {"error": str(e)})
       finally:
           # Cleanup: stop clock, remove context
           if context.clock:
               await context.clock.stop()
           self._contexts.pop(run.id, None)
   ```
3. REFACTOR: Extract common error handling into a shared helper if `_start_backtest` and `_start_live` patterns are identical enough

**Tests** (~3):

- `test: _start_live error → run transitions to ERROR status`
- `test: _start_live error → emits run.Error event`
- `test: _start_live error → cleanup removes context (no zombie run)`

---

### 4.6 N-09: Unify `time_in_force` Default

**Problem**: `schemas.py` OrderCreate defaults to `"day"`, but VedaService handler uses `"gtc"`.

**Decision**: Use `"day"` as the default (safer for most orders).

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/services/veda_service.py` (or order handler) | Change default `time_in_force` from `"gtc"` to `"day"` or read from schema/request |

**Implementation Steps**:

1. RED: Write test asserting default time_in_force is "day"
2. GREEN: Update VedaService to use the value from the request (which defaults to "day" via schema)
3. REFACTOR: Ensure the schema default is the single source of truth

**Tests** (~1):

- `test: order placed without explicit time_in_force uses "day" default`

---

### 4.7 M-01: Complete `ALL_EVENT_TYPES` Set

**Problem**: `ALL_EVENT_TYPES` in `src/events/types.py` is missing `RunEvents.CREATED`, `RunEvents.COMPLETED`, and `OrderEvents.CREATED`.

**Files to modify**:
| File | Change |
|------|--------|
| `src/events/types.py` | Add the 3 missing events to `ALL_EVENT_TYPES` set (near line 182) |
| `tests/unit/events/test_types.py` | Add test verifying ALL_EVENT_TYPES contains all defined event constants |

**Implementation Steps**:

1. RED: Write test that collects all event constants from all Event classes and asserts they're all in `ALL_EVENT_TYPES`
2. GREEN: Add missing events to the set
3. REFACTOR: Consider generating `ALL_EVENT_TYPES` dynamically from the Event classes to prevent future drift

**Tests** (~1):

- `test: ALL_EVENT_TYPES contains every event constant from all Event classes`

---

### 4.8 M-03: Add `orders.Cancelled` SSE Listener

**Problem**: Backend emits `orders.Cancelled` on cancel, but frontend doesn't listen for it.

**Files to modify**:
| File | Change |
|------|--------|
| `haro/src/hooks/useSSE.ts` | Add `addEventListener("orders.Cancelled", ...)` with toast + query invalidation |
| `haro/tests/unit/hooks/useSSE.test.tsx` | Add test for Cancelled event |

**Implementation Steps**:

1. RED: Write test expecting `orders.Cancelled` SSE listener
2. GREEN: Add listener matching existing `orders.Created` / `orders.Filled` pattern
3. Display toast: "Order cancelled" with order details

**Tests** (~1):

- `test: orders.Cancelled SSE event triggers toast and invalidates orders query`

---

### M8-P0 Summary

| Task                    | Tests   | Files Modified                          |
| ----------------------- | ------- | --------------------------------------- |
| C-01 SSE casing         | 2       | `useSSE.ts`, `useSSE.test.tsx`          |
| C-02 Start route        | 3       | `routes/runs.py`, `test_runs.py`        |
| C-03 Health path        | 2       | `health.py`, `app.py`, `test_health.py` |
| C-04 Order unification  | 3       | `routes/orders.py`, `test_orders.py`    |
| N-02 \_start_live error | 3       | `run_manager.py`, `test_run_manager.py` |
| N-09 time_in_force      | 1       | `veda_service.py`, test                 |
| M-01 ALL_EVENT_TYPES    | 1       | `types.py`, `test_types.py`             |
| M-03 Cancelled listener | 1       | `useSSE.ts`, `useSSE.test.tsx`          |
| **Total**               | **~16** |                                         |

---

## 5. M8-P1: Runtime Wiring (Packages A/B/C)

> **Estimated Tests**: ~20  
> **Depends on**: M8-P0 complete  
> **Design Decisions Applied**: D-1, D-4

### 5.1 Package A: Run Lifecycle (A2 — Lifecycle-First)

> **Issues resolved**: C-02 (route exists from P0), RunManager DI, per-run cleanup  
> **Chosen approach**: A2 — treat start route + DI readiness + cleanup as one cohesive change

#### A.1 Inject RunManager Runtime Dependencies

**Problem**: `app.py` creates `RunManager(event_log=event_log)` but never passes `strategy_loader` or `bar_repository`, so `start()` cannot actually execute runs.

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/app.py` | Create `PluginStrategyLoader` and `BarRepository` in lifespan; pass to `RunManager` |
| `src/glados/dependencies.py` | Add `get_strategy_loader()` and `get_bar_repository()` if needed by routes |
| `src/glados/services/run_manager.py` | Ensure constructor validates required dependencies |

**Implementation Steps**:

1. RED: Integration test — create run + start via route → expect no "missing dependency" error
2. GREEN: Update `app.py` lifespan:

   ```python
   # In lifespan:
   strategy_loader = PluginStrategyLoader(strategies_dir=strategies_path)
   bar_repository = BarRepository(session_factory) if database else None

   run_manager = RunManager(
       event_log=event_log,
       bar_repository=bar_repository,
       strategy_loader=strategy_loader,
   )
   app.state.run_manager = run_manager
   ```

3. Add readiness check in `RunManager.start()`:
   ```python
   if mode == "backtest" and self._bar_repository is None:
       raise RuntimeError("Backtest requires bar_repository (DB mode)")
   if self._strategy_loader is None:
       raise RuntimeError("No strategy_loader configured")
   ```

**Tests** (~3):

- `test: RunManager.start() raises if strategy_loader is None`
- `test: RunManager.start(mode=backtest) raises if bar_repository is None`
- `test: RunManager with all dependencies can start a run`

#### A.2 Per-Run Cleanup Guarantees

**Problem**: When a run stops/completes/errors, cleanup (unsubscribe event listeners, stop clock, release runner resources) is not guaranteed.

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/services/run_manager.py` | Add `_cleanup_run(run_id)` method called from stop/complete/error paths |

**Implementation Steps**:

1. RED: Test — run completes → verify subscriptions are removed, context is deleted, clock is stopped
2. GREEN: Add cleanup method:
   ```python
   async def _cleanup_run(self, run_id: str) -> None:
       context = self._contexts.pop(run_id, None)
       if context is None:
           return
       if context.clock:
           await context.clock.stop()
       if context.runner:
           await context.runner.cleanup()
       # Unsubscribe any event listeners for this run
       if context.subscription_ids:
           for sub_id in context.subscription_ids:
               self._event_log.unsubscribe_by_id(sub_id)
   ```
3. Call `_cleanup_run()` from `stop()`, `_start_backtest()` finally block, `_start_live()` finally block

**Tests** (~3):

- `test: stop run → clock stopped + context removed`
- `test: backtest completion → cleanup called automatically`
- `test: live run error → cleanup called (no leaked subscriptions)`

#### A.3 Integration: Run Lifecycle Test

**Files to create**:
| File | Purpose |
|------|---------|
| `tests/integration/test_run_lifecycle.py` | End-to-end run lifecycle |

**Tests** (~2):

- `test: integration — create → start → complete full backtest lifecycle`
- `test: integration — create → start → stop live run lifecycle`

---

### 5.2 Package B: Event Pipeline Wiring (B1 — Direct App-Lifespan)

> **Issues resolved**: N-01, N-07, DomainRouter wiring  
> **Chosen approach**: B1 — direct app-lifespan wiring (3 consumers, reassess at 10+)

#### B.1 PostgresEventLog Direct Subscriber Dispatch (D-1)

**Problem**: `InMemoryEventLog.append()` directly calls subscriber callbacks. `PostgresEventLog.append()` only writes to DB + `pg_notify()`. In-process subscribers never fire in DB mode.

**Decision D-1**: Add direct subscriber dispatch inside `PostgresEventLog.append()`, in addition to `pg_notify()`.

**Files to modify**:
| File | Change |
|------|--------|
| `src/events/log.py` | In `PostgresEventLog.append()`, after DB write, dispatch to subscriber callbacks (same as InMemoryEventLog pattern) |

**Implementation Steps**:

1. RED: Integration test — append event to PostgresEventLog → verify subscriber callback fires
2. GREEN: Add subscriber dispatch in `PostgresEventLog.append()`:

   ```python
   async def append(self, envelope: Envelope) -> None:
       # 1. Write to database
       async with self._session_factory() as session:
           event = OutboxEvent(...)
           session.add(event)
           await session.commit()
           # pg_notify for cross-process
           await session.execute(text("SELECT pg_notify(...)"))

       # 2. Direct in-process subscriber dispatch (D-1)
       async with self._subscriber_lock:
           for sub in self._subscribers:
               if sub.matches(envelope):
                   try:
                       await sub.callback(envelope)
                   except Exception:
                       logger.exception("Subscriber error")
   ```

3. REFACTOR: Extract subscriber dispatch loop into a shared `_dispatch_to_subscribers()` method used by both EventLog implementations

**Tests** (~3):

- `test: PostgresEventLog.append() fires subscriber callbacks`
- `test: PostgresEventLog.append() filters subscribers by event type`
- `test: subscriber error does not prevent other subscribers from receiving events`

#### B.2 Wire DomainRouter in App Lifespan (D-4)

**Problem**: `DomainRouter` is implemented but never instantiated/wired in `app.py`. Strategy `strategy.*` events are never routed to `backtest.*` / `live.*` events.

**Decision D-4**: DomainRouter as standalone wired singleton (not inline in RunManager).

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/app.py` | Create `DomainRouter` in lifespan, subscribe it to EventLog, store in `app.state` |
| `src/glados/dependencies.py` | Add `get_domain_router()` dependency |

**Implementation Steps**:

1. RED: Integration test — emit `strategy.FetchWindow` → expect `backtest.FetchWindow` appears
2. GREEN: In `app.py` lifespan:

   ```python
   domain_router = DomainRouter(event_log=event_log)
   await domain_router.setup()  # Subscribe to strategy.* events
   app.state.domain_router = domain_router

   # Cleanup on shutdown
   yield
   await domain_router.teardown()
   ```

**Tests** (~2):

- `test: DomainRouter wired in lifespan and receives events`
- `test: strategy.FetchWindow routed to backtest.FetchWindow`

#### B.3 Wire InMemoryEventLog in No-DB Mode

**Problem**: When no `DB_URL` is set, `event_log` is `None` → SSE and all event-driven features are completely dead.

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/app.py` | When no `DB_URL`, create `InMemoryEventLog()` instead of `None` |

**Implementation Steps**:

1. RED: Test — create app without DB_URL → verify `event_log` is `InMemoryEventLog` (not None)
2. GREEN: Update `app.py`:
   ```python
   if db_url:
       event_log = PostgresEventLog(session_factory)
   else:
       event_log = InMemoryEventLog()  # Degraded but functional
   ```

**Tests** (~1):

- `test: no DB_URL → InMemoryEventLog is created and SSEBroadcaster receives events`

#### B.4 Integration: Event → Subscriber → SSE

**Files to create**:
| File | Purpose |
|------|---------|
| `tests/integration/test_event_pipeline.py` | Event pipeline end-to-end |

**Tests** (~2):

- `test: integration — append event → SSEBroadcaster.publish() called`
- `test: integration — DomainRouter routes strategy → backtest events end-to-end`

---

### 5.3 Package C: Data Source Unification (C1 — Hard Unify)

> **Issues resolved**: C-04 (route change done in P0), full integration  
> **Chosen approach**: C1 — hard unify to durable source in DB mode

#### C.1 Full Read/Write Parity via VedaService

Builds on P0 C-04 route change. Ensures VedaService `list_orders()` and `get_order()` return consistent data from the durable store.

**Files to modify**:
| File | Change |
|------|--------|
| `src/veda/veda_service.py` | Ensure `list_orders()` queries repository (not just in-memory state) |
| `src/veda/persistence.py` | Ensure `OrderRepository.list()` returns all orders with correct mapping |

**Tests** (~2):

- `test: VedaService.list_orders() returns orders from repository in DB mode`
- `test: VedaService.get_order() returns order from repository when not in memory`

#### C.2 Integration: Write → Read Parity

**Tests** (~2):

- `test: integration — place order via VedaService → list orders returns it`
- `test: integration — cancel order → list orders shows cancelled status`

---

### M8-P1 Summary

| Package             | Tests   | Focus                                     |
| ------------------- | ------- | ----------------------------------------- |
| A: Run Lifecycle    | 8       | DI, cleanup, lifecycle integration        |
| B: Event Pipeline   | 8       | Dispatch parity, DomainRouter, no-DB mode |
| C: Data Unification | 4       | Read/write parity, repository integration |
| **Total**           | **~20** |                                           |

---

## 6. M8-Q: Code Quality & P1 Fixes

> **Estimated Tests**: ~10–15  
> **Can run parallel with M8-P1** (independent fixes)

### 6.0 Progress Snapshot (2026-02-26, code-verified)

| Item                                  | Status  | Notes                                                                                       |
| ------------------------------------- | ------- | ------------------------------------------------------------------------------------------- |
| D-2 (runs table + repository)         | ✅ Done | model/repo/migration + app lifespan wiring (`RunRepository` inject + `recover()`) completed |
| D-3 / N-03 (fills table + repository) | ✅ Done | model/repo/migration + VedaService fill hydration on repository reads completed             |
| N-04 (Alpaca async wrapping)          | ✅ Done | sync SDK calls wrapped with `asyncio.to_thread()`                                           |
| N-06 / D-5 (SSE run_id filtering)     | ✅ Done | backend SSE query-param filtering added                                                     |
| N-10 / M-02 (pagination)              | ✅ Done | runs/orders support `page` + `page_size`                                                    |
| M-04 (SimulatedFill.side enum)        | ✅ Done | `str` -> `OrderSide`                                                                        |
| N-05 (StrategyAction enum refactor)   | ✅ Done | stringly typed fields replaced with enums                                                   |
| N-08 (backtest stats)                 | ✅ Done | Sharpe/Sortino/max-drawdown/win metrics implemented                                         |
| L-01 / L-02 (cleanup)                 | ✅ Done | dead files removed + TODOs resolved                                                         |
| M-07 (RunsPage runId param)           | ✅ Done | `/runs/:runId` deep-link wired in App + RunsPage param handling                             |

### 6.1 D-2: Add Runs Table (Schema Migration)

**Purpose**: Persist run state to database for restart recovery.

**Files to create/modify**:
| File | Change |
|------|--------|
| `src/walle/models.py` | Add `RunRecord` SQLAlchemy model |
| `src/walle/repositories/run_repository.py` (new) | Create `RunRepository` with CRUD operations |
| Alembic migration | Add `runs` table migration |
| `src/glados/services/run_manager.py` | Optionally persist runs via RunRepository |

**Schema**:

```sql
CREATE TABLE runs (
    id          VARCHAR PRIMARY KEY,
    strategy_id VARCHAR NOT NULL,
    mode        VARCHAR NOT NULL,    -- backtest/paper/live
    status      VARCHAR NOT NULL,    -- pending/running/stopped/completed/error
    symbols     JSONB,
    timeframe   VARCHAR,
    config      JSONB,
    error       TEXT,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at  TIMESTAMP WITH TIME ZONE,
    stopped_at  TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

**Tests** (~3):

- `test: RunRepository.save() persists run to DB`
- `test: RunRepository.get(id) retrieves run`
- `test: RunRepository.list() returns all runs`

**Status**: ✅ Done (model/repository/migration + app startup wiring for `RunRepository` + `recover()` completed)

### 6.2 D-3/N-03: Add Fills Table + Persistence

**Purpose**: Persist fill history (currently lost on round-trip).

**Files to create/modify**:
| File | Change |
|------|--------|
| `src/walle/models.py` | Add `FillRecord` SQLAlchemy model |
| `src/walle/repositories/fill_repository.py` (new) | Create `FillRepository` |
| `src/veda/persistence.py` | Update `OrderRepository` to save/load fills |
| Alembic migration | Add `fills` table migration |

**Schema**:

```sql
CREATE TABLE fills (
    id          VARCHAR PRIMARY KEY,
    order_id    VARCHAR NOT NULL REFERENCES orders(id),
    price       DECIMAL NOT NULL,
    quantity    DECIMAL NOT NULL,
    side        VARCHAR NOT NULL,
    filled_at   TIMESTAMP WITH TIME ZONE NOT NULL,
    exchange_fill_id VARCHAR
);
```

**Tests** (~2):

- `test: order persistence round-trip includes fills`
- `test: FillRepository.list_by_order(order_id) returns fills`

**Status**: ✅ Done (model/repository/migration completed; fill round-trip hydration implemented in VedaService read paths)

### 6.3 N-04: AlpacaAdapter Async Wrapping

**Problem**: Alpaca SDK is synchronous, called from async context → blocks event loop.

**Files to modify**:
| File | Change |
|------|--------|
| `src/veda/adapters/alpaca_adapter.py` | Wrap all sync SDK calls in `asyncio.to_thread()` |

**Implementation**:

```python
async def submit_order(self, intent: OrderIntent) -> ExchangeOrderResult:
    result = await asyncio.to_thread(
        self._trading_client.submit_order, order_data
    )
    return self._map_result(result)
```

**Tests** (~2):

- `test: submit_order runs in thread pool (does not block event loop)`
- `test: get_account runs in thread pool`

### 6.4 N-06/D-5: SSE run_id Filtering

**Problem**: SSE broadcasts all events. Frontend can't filter by run_id.

**Decision D-5**: Add `run_id` query parameter to SSE endpoint.

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/routes/sse.py` | Add optional `run_id: str = None` query param; filter events before sending |
| `haro/src/hooks/useSSE.ts` | Accept optional `runId` prop for filtered stream |

**Tests** (~2):

- `test: SSE with run_id query param only sends events for that run`
- `test: SSE without run_id sends all events (backward compatible)`

### 6.5 N-10/M-02: Server-Side Pagination

**Problem**: Frontend sends `page`, `page_size` but backend ignores them.

**Files to modify**:
| File | Change |
|------|--------|
| `src/glados/routes/runs.py` | Accept `page`, `page_size` query params; apply offset/limit |
| `src/glados/routes/orders.py` | Same |

**Tests** (~2):

- `test: GET /runs with page=2&page_size=10 returns correct slice`
- `test: GET /orders with page_size returns limited results`

### 6.6 M-04: SimulatedFill.side Enum Fix

**Files to modify**:
| File | Change |
|------|--------|
| `src/greta/models.py` | Change `side: str` to `side: OrderSide` (line 49) |
| Remove TODO comment |

**Tests** (~1):

- `test: SimulatedFill.side accepts OrderSide enum values only`

### 6.7 N-05: StrategyAction Enum Refactor

**Files to modify**:
| File | Change |
|------|--------|
| `src/marvin/base_strategy.py` | Refactor `StrategyAction` from stringly-typed to proper enum |

**Tests** (~1):

- `test: StrategyAction type-checks at construction`

### 6.8 N-08: Backtest Stats Computation

**Files to modify**:
| File | Change |
|------|--------|
| `src/greta/greta_service.py` | Implement Sharpe ratio, Sortino ratio, max drawdown calculations |

**Tests** (~2):

- `test: Sharpe ratio computed correctly from returns`
- `test: max drawdown computed from equity curve`

### 6.9 M-07: RunsPage runId Parameter

**Decision**: Wire `runId` URL param to filter the runs page (useful for deep-linking).

**Files to modify**:
| File | Change |
|------|--------|
| `haro/src/pages/RunsPage.tsx` | Read `runId` from URL params; if present, show single run detail |

**Status**: ⏳ Open

### 6.10 L-01: Delete Orphan Files

```bash
rm src/models.py
rm src/constants.py
rm src/veda/base_api_handler.py
```

**Status**: ✅ Done

### 6.11 L-02: Resolve TODO/FIXME Comments

| Location                         | TODO                       | Resolution                           |
| -------------------------------- | -------------------------- | ------------------------------------ |
| `src/__main__.py:13`             | "Implement proper startup" | Implement or document as intentional |
| `src/greta/greta_service.py:504` | "Calculate advanced stats" | Resolved by N-08                     |
| `src/greta/models.py:49`         | "Change to OrderSide enum" | Resolved by M-04                     |

**Status**: ✅ Done

---

### M8-Q Summary

| Task                   | Tests   | Status                           |
| ---------------------- | ------- | -------------------------------- |
| D-2 Runs table         | 3       | ✅ Done                          |
| D-3/N-03 Fills table   | 2       | ✅ Done                          |
| N-04 Async wrapping    | 2       | ✅ Done                          |
| N-06/D-5 SSE filtering | 2       | ✅ Done                          |
| N-10/M-02 Pagination   | 2       | ✅ Done                          |
| M-04 Side enum         | 1       | ✅ Done                          |
| N-05 StrategyAction    | 1       | ✅ Done                          |
| N-08 Backtest stats    | 2       | ✅ Done                          |
| L-01/L-02 Cleanup      | 0       | ✅ Done                          |
| M-07 RunsPage runId    | 0       | ✅ Done                          |
| **Total**              | **~15** | **10 done / 0 partial / 0 open** |

---

## 7. M8-D: Documentation

> **No new tests** — documentation-only phase  
> **Depends on**: M8-P0 + M8-P1 (code must be final before documenting)

### 7.1 Architecture Docs to Create

| Document                      | Content Source                | Key Sections                                                           |
| ----------------------------- | ----------------------------- | ---------------------------------------------------------------------- |
| `docs/architecture/greta.md`  | Promote from M4 milestone doc | Backtest flow, simulator, fill model, per-run lifecycle                |
| `docs/architecture/marvin.md` | Promote from M5 milestone doc | Strategy loading, StrategyRunner, plugin architecture                  |
| `docs/architecture/walle.md`  | New                           | Schema design, repository pattern, migration strategy, table inventory |

**Completion Snapshot (2026-02-26)**:

- ✅ `docs/architecture/greta.md` created
- ✅ `docs/architecture/marvin.md` created
- ✅ `docs/architecture/walle.md` created

### 7.2 Docs to Update

| Document                      | Change                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------- |
| `docs/architecture/api.md`    | Add `POST /runs/{id}/start`; fix health path; add SSE event format section      |
| `docs/architecture/events.md` | Add SSE wire format spec (event/data field shapes)                              |
| `docs/architecture/veda.md`   | Fix env var names (L-04); add `submitting`/`submitted` to OrderStatus (L-05)    |
| `docs/ARCHITECTURE.md`        | Fix §5 false claim about SSE run_id filtering (was N-06; now D-5 implements it) |
| `MILESTONE_PLAN.md`           | Update test counts after M8 completion                                          |
| `TEST_COVERAGE.md`            | Update test counts and coverage numbers                                         |

**Completion Snapshot (2026-02-26)**:

- ✅ `docs/architecture/api.md` updated (start route, health path, SSE/event mapping, error strategy)
- ✅ `docs/architecture/events.md` updated (SSE wire format section)
- ✅ `docs/architecture/veda.md` updated for env var and `OrderStatus` drift
- ✅ `docs/ARCHITECTURE.md` updated (module quick links + runtime-aligned claims)
- ✅ `docs/MILESTONE_PLAN.md` updated (M8-D/doc gate status)
- 🟡 `docs/TEST_COVERAGE.md` updated to latest test snapshot; coverage gate remains pending

### 7.3 New Documentation Sections

| Topic                   | Location                               | Content                                                                         |
| ----------------------- | -------------------------------------- | ------------------------------------------------------------------------------- |
| SSE Wire Format         | `docs/architecture/events.md` §new     | Exact SSE `event:` and `data:` field format, examples per event type            |
| Error Handling Strategy | `docs/architecture/api.md` §new        | Exception hierarchy, HTTP status code mapping, event pipeline error propagation |
| Degraded Mode Matrix    | `docs/architecture/deployment.md` §new | DB-on vs DB-off feature matrix (what works, what doesn't)                       |

---

## 8. Exit Gate

### 8.1 Definition of Done

All items must pass for M8 to close:

- [ ] All P0 critical issues resolved (C-01–C-04, N-01, N-02, N-07)
- [ ] Design decisions D-1 through D-5 implemented
- [ ] DomainRouter wired into runtime lifecycle
- [ ] RunManager dependencies fully injected (strategy_loader, bar_repository)
- [ ] Per-run cleanup guarantees tested
- [ ] EventLog dispatch parity between InMemory and Postgres
- [ ] Order read/write unified to VedaService (DB mode)
- [ ] No-DB mode uses InMemoryEventLog (not None)
- [ ] All TODO/FIXME cleaned up (L-02)
- [ ] Orphan files deleted (L-01)
- [ ] Architecture docs created (greta.md, marvin.md, walle.md)
- [ ] All docs accurate post-M8 changes
- [ ] Full test suite green: ≥934 tests (808+ backend + 86+ frontend)
- [ ] Code coverage ≥80% for critical modules

### 8.1.1 Current Exit Snapshot (2026-02-26)

- [x] All P0 critical issues resolved (C-01–C-04, N-01, N-02, N-07)
- [x] Design decisions D-1 through D-5 implemented
- [x] DomainRouter wired into runtime lifecycle
- [x] RunManager dependencies fully injected (strategy_loader, bar_repository)
- [x] Per-run cleanup guarantees tested
- [x] EventLog dispatch parity between InMemory and Postgres
- [x] Order read/write unified to VedaService (DB mode)
- [x] No-DB mode uses InMemoryEventLog (not None)
- [x] All TODO/FIXME cleaned up (L-02)
- [x] Orphan files deleted (L-01)
- [x] Architecture docs created (greta.md, marvin.md, walle.md)
- [x] All docs accurate post-M8 changes
- [x] Full test suite green: 992 tests (904 backend + 88 frontend)
- [x] Code coverage ≥80% for critical modules (pytest-cov: 89.73%)

### 8.2 Test Count Target

| Source    | Before M8 | M8 Added   | After M8     |
| --------- | --------- | ---------- | ------------ |
| Backend   | 808       | ~40–50     | ~848–858     |
| Frontend  | 86        | ~4         | ~90          |
| **Total** | **894**   | **~44–54** | **~938–948** |

### 8.3 Commit Strategy

```
M8-P0-C01: fix(haro): align SSE event casing to PascalCase
M8-P0-C02: feat(glados): add POST /runs/{id}/start route
M8-P0-C03: fix(glados): move health endpoint to /api/v1/healthz
M8-P0-C04: fix(glados): unify order read/write to VedaService
M8-P0-N02: fix(glados): add error handling to _start_live
M8-P0-N09: fix(veda): unify time_in_force default to "day"
M8-P0-M01: fix(events): complete ALL_EVENT_TYPES set
M8-P0-M03: feat(haro): add orders.Cancelled SSE listener
M8-P1-A:   feat(glados): inject RunManager dependencies + cleanup guarantees
M8-P1-B:   feat(events): PostgresEventLog direct dispatch + DomainRouter wiring
M8-P1-C:   feat(glados): unify order data source + read/write parity
M8-Q-D2:   feat(walle): add runs table + repository
M8-Q-D3:   feat(walle): add fills table + persistence
M8-Q-N04:  fix(veda): wrap AlpacaAdapter sync SDK in asyncio.to_thread
M8-Q-N06:  feat(glados): SSE run_id query param filtering
M8-Q-*:    chore: code quality cleanup (dead files, TODOs, type fixes)
M8-D:      docs: architecture docs (greta, marvin, walle) + updates
```

---

_Last Updated: 2026-02-26_  
_Status: M8 Complete (P0/P1/Q/D delivered; exit gate passed)_  
_Prerequisites: M7 ✅ (894 tests), D-1–D-5 decisions locked and implemented in M8_

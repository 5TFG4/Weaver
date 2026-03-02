# Design Audit Report & M8 Quality Gate

> **Document Charter**  
> **Primary role**: M8-R closeout snapshot for design-code-test quality gate.  
> **Authoritative for**: current closeout status and remaining release-gate items.  
> **Not authoritative for**: historical closed-finding narrative (use `AUDIT_FINDINGS.md`).

> **Audit Date**: 2026-02-26 (final closeout)  
> **Scope**: Full project — design docs ↔ code ↔ tests cross-validation  
> **Branch**: `improvements`  
> **Purpose**: Quality gate closeout for M8 (all phases complete)  
> **Status**: M8 ✅ Complete (all R0/R1/R2/R3 phases delivered and verified)

> **Closeout Note (2026-02-26)**: All M8 phases complete. R0 deployment blockers resolved (replaced gunicorn command with uvicorn, Dockerfile CMD fixed, smoke tests added). Sections 2–8 retained as audit baseline. Next milestone: M9 (E2E Tests).

---

## Table of Contents

1. [Audit Standards & Criteria](#1-audit-standards--criteria)
2. [Critical Findings (Must Fix Before M8)](#2-critical-findings)
3. [Medium Findings (Fix During M8)](#3-medium-findings)
4. [Low/Informational Findings](#4-lowinformational-findings)
5. [Design Document Consistency](#5-design-document-consistency)
6. [Code vs Design Verification Matrix](#6-code-vs-design-verification-matrix)
7. [Test Coverage Accuracy](#7-test-coverage-accuracy)
8. [Pre-M8 Checklist](#8-pre-m8-checklist)

---

## 1. Audit Standards & Criteria

### 1.1 What This Audit Checks

| Category                                  | Check                                                       | Pass Criteria                                                         |
| ----------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------- |
| **D1: Doc-Code Alignment**                | Every interface/endpoint documented matches actual code     | Zero undocumented endpoints; zero documented-but-missing endpoints    |
| **D2: Doc-Doc Consistency**               | No contradictions between architecture docs                 | Same names, types, env vars, event names across all docs              |
| **D3: Code-Test Alignment**               | Every public method/endpoint has test coverage              | No untested public endpoints; test assertions match expected behavior |
| **D4: Type Safety**                       | Frontend types match backend schemas exactly                | Enum values, field names, optionality all match                       |
| **D5: Event Model Integrity**             | Event names consistent across emitters, listeners, and docs | Exact string match; no casing mismatches                              |
| **D6: Dead Code**                         | No orphan files, unused imports, or unreferenced modules    | Zero files that are never imported/used                               |
| **D7: Architecture Invariant Compliance** | Code follows the 9 documented invariants                    | No violations of singleton/per-run rules, DI patterns, etc.           |
| **D8: TODO/FIXME Tracking**               | All TODO/FIXME items are tracked in milestone plan          | Every inline TODO has a corresponding M8 task                         |
| **D9: Test Count Accuracy**               | Documented test counts match actual counts                  | ±2 tolerance                                                          |
| **D10: API Contract**                     | Frontend API calls match backend route signatures           | Endpoint paths, HTTP methods, request/response shapes all match       |

### 1.2 Severity Levels

| Level           | Definition                                  | Action Required                |
| --------------- | ------------------------------------------- | ------------------------------ |
| 🔴 **CRITICAL** | Will cause runtime failure in production    | Must fix before M8 starts      |
| 🟡 **MEDIUM**   | Functional gap or significant inconsistency | Fix during M8                  |
| 🟢 **LOW**      | Cleanup, minor inconsistency, or cosmetic   | Fix during M8-4 (Code Quality) |
| ℹ️ **INFO**     | Informational only, no action needed        | Document for awareness         |

---

## 2. Critical Findings (Must Fix Before M8)

### 2.1 🔴 C-01: SSE Event Name Casing Mismatch

**Criteria Violated**: D5 (Event Model Integrity), D10 (API Contract)

**Problem**: The backend emits run events with **PascalCase** verbs (e.g., `run.Started`), but the frontend listens for **lowercase** verbs (e.g., `run.started`). SSE `addEventListener` is **case-sensitive** — these will never match.

| Backend Emits (via `RunEvents.*`) | Frontend Listens For | Match?        |
| --------------------------------- | -------------------- | ------------- |
| `run.Started`                     | `run.started`        | ❌ **BROKEN** |
| `run.Stopped`                     | `run.stopped`        | ❌ **BROKEN** |
| `run.Completed`                   | `run.completed`      | ❌ **BROKEN** |
| `run.Error`                       | `run.error`          | ❌ **BROKEN** |
| `orders.Created`                  | `orders.Created`     | ✅ OK         |
| `orders.Filled`                   | `orders.Filled`      | ✅ OK         |
| `orders.Rejected`                 | `orders.Rejected`    | ✅ OK         |

**Evidence**:

- Backend: `src/events/types.py` line 144 → `STARTED = "run.Started"`
- Backend: `src/glados/services/run_manager.py` line 205 → `await self._emit_event(RunEvents.STARTED, run)`
- Frontend: `haro/src/hooks/useSSE.ts` line 62 → `addEventListener("run.started", ...)`

**Impact**: All SSE-driven run status updates in the frontend will be **completely silent**. Dashboard and RunsPage will never receive real-time updates for run lifecycle events.

**Fix**: Either change frontend to listen for `run.Started` etc. (matching backend), or change backend constants to lowercase. **Recommend aligning frontend to backend** since backend constants are already used throughout tests.

---

### 2.2 🔴 C-02: Missing `POST /runs/{id}/start` Backend Route

**Criteria Violated**: D1 (Doc-Code Alignment), D10 (API Contract)

**Problem**: The frontend defines `startRun(runId)` calling `POST /api/v1/runs/{runId}/start`, and the hook `useStartRun()` uses it. However, the backend `routes/runs.py` has **no `/start` endpoint**. Only `create`, `get`, `list`, and `stop` routes exist.

The `RunManager.start()` method exists in the service layer but is never exposed via REST.

**Evidence**:

- Frontend: `haro/src/api/runs.ts` → `startRun(runId): post("/runs/${runId}/start")`
- Frontend: `haro/src/hooks/useRuns.ts` → `useStartRun()` hook
- Backend: `src/glados/routes/runs.py` → No `@router.post("/{run_id}/start")` exists
- Backend: `src/glados/services/run_manager.py` line 171 → `async def start()` exists but is unrouted

**Impact**: The `useStartRun` hook will always receive a 404/405 error. Runs created via the UI will remain in PENDING status forever — they can never be started.

**Fix**: Add a `POST /{run_id}/start` route in `routes/runs.py` that calls `run_manager.start(run_id)`.

---

### 2.3 🔴 C-03: Health Endpoint Path Mismatch

**Criteria Violated**: D10 (API Contract)

**Problem**: The backend health route is registered at `/healthz` (no prefix), but the frontend API client prepends `/api/v1` to all paths, so it calls `/api/v1/healthz`.

**Evidence**:

- Backend: `src/glados/routes/health.py` line 16 → `@router.get("/healthz")` with `router = APIRouter()` (no prefix)
- Backend: `src/glados/app.py` line 190 → `app.include_router(health_router)` (no prefix)
- Frontend: `haro/src/api/client.ts` line 10 → `API_BASE = "/api/v1"`
- Frontend: `haro/src/api/health.ts` line 13 → `get<HealthResponse>("/healthz")` → resolves to `/api/v1/healthz`

**Impact**: In dev mode, the Vite proxy forwards `/api/*` to the backend — but `/api/v1/healthz` will 404 because the backend registers it at `/healthz`. In production (Nginx), the same mismatch occurs. The Dashboard page's "API Status" stat card will always show an error state.

**Fix**: Either:

- (a) Move health route to `/api/v1/healthz` (add prefix to router), or
- (b) Change frontend to call `/healthz` directly (bypass `API_BASE`)

---

### 2.4 🔴 C-04: Split Order Data Sources (GET vs POST)

**Criteria Violated**: D7 (Architecture Invariant Compliance)

**Problem**: The `POST /orders` and `DELETE /orders/{id}` routes use `VedaService` (real order management), but `GET /orders` and `GET /orders/{id}` use `MockOrderService` (hardcoded mock data). Orders created via VedaService are **invisible** to the list/get endpoints.

**Evidence**:

- `src/glados/routes/orders.py` line 103 → `create_order` uses `veda_service.place_order()`
- `src/glados/routes/orders.py` line 148 → `list_orders` uses `order_service` (MockOrderService)
- `src/glados/routes/orders.py` line 163 → `get_order` uses `order_service` (MockOrderService)

**Impact**: Any order placed through the API will be persisted via VedaService but never returned by list/get endpoints. The frontend will always show the 2 hardcoded mock orders instead of real ones.

**Fix**: Update `list_orders` and `get_order` to use `VedaService.list_orders()` / `VedaService.get_order()` when VedaService is configured, falling back to MockOrderService only when no trading credentials are available.

---

## 3. Medium Findings (Fix During M8)

### 3.1 🟡 M-01: `ALL_EVENT_TYPES` Missing 3 Event Types

**Criteria Violated**: D5 (Event Model Integrity)

**Problem**: The validation set `ALL_EVENT_TYPES` in `src/events/types.py` is missing 3 events that are actively emitted by the system:

| Missing Event    | Emitted By                     | Line                 |
| ---------------- | ------------------------------ | -------------------- |
| `run.Created`    | `RunManager.create()`          | `run_manager.py:144` |
| `run.Completed`  | `RunManager._start_backtest()` | `run_manager.py:326` |
| `orders.Created` | `VedaService.place_order()`    | `veda_service.py`    |

**Impact**: If event validation is enforced, these events would be rejected as invalid.

---

### 3.2 🟡 M-02: No Server-Side Pagination/Filtering

**Criteria Violated**: D10 (API Contract)

**Problem**: The frontend sends `page`, `page_size`, and `status` query parameters for both runs and orders list endpoints, but the backend ignores them all.

| Frontend Sends                | Backend Accepts | Backend Uses        |
| ----------------------------- | --------------- | ------------------- |
| `page`, `page_size`, `status` | (ignored)       | Returns all items   |
| `run_id` (orders)             | `run_id`        | ✅ Actually filters |

**Impact**: Currently functional because data volumes are small. Will become a performance problem with many runs/orders. The `page_size` in `RunListResponse`/`OrderListResponse` will always be wrong (hardcoded/default).

---

### 3.3 🟡 M-03: Frontend `orders.Cancelled` Event Not Handled

**Criteria Violated**: D10 (API Contract)

**Problem**: The backend emits `orders.Cancelled` events (via `VedaService.cancel_order()`), but the frontend SSE hook doesn't listen for it.

**Impact**: When a user cancels an order, the UI won't show a toast notification and won't auto-refresh the orders list. The user must manually refresh to see the cancellation.

---

### 3.4 🟡 M-04: `SimulatedFill.side` Still Using `str` Instead of `OrderSide` Enum

**Criteria Violated**: D8 (TODO/FIXME Tracking)

**Problem**: `src/greta/models.py` line 49 has `side: str` with a TODO comment from M5 to change to `OrderSide` enum. This was flagged in the original audit and assigned to M5-5, but never completed.

---

### 3.5 🟡 M-05: PositionTracker Market Values Always Zero

**Criteria Violated**: D1 (Doc-Code Alignment)

**Problem**: `PositionTracker.get_position()` returns positions where `market_value`, `unrealized_pnl`, and `unrealized_pnl_percent` are hardcoded to `Decimal("0")`. The tracker never receives market data to calculate these values.

**Impact**: Position display in any future UI/API will show zero P&L for all positions.

---

### 3.6 🟡 M-06: SSE Event Format Undocumented

**Criteria Violated**: D2 (Doc-Doc Consistency)

**Problem**: The SSE broadcaster sends events with `event_type` as the SSE event name and the event payload as the data field. However, the exact format (especially `event:` and `data:` fields) is undocumented. The frontend `useSSE.ts` parses `e.data` but the actual shape received from `SSEBroadcaster.publish()` → `routes/sse.py` → `EventSourceResponse` is not specified anywhere.

---

### 3.7 🟡 M-07: Unused Route Parameter `/runs/:runId`

**Criteria Violated**: D3 (Code-Test Alignment)

**Problem**: `App.tsx` defines `<Route path="/runs/:runId" element={<RunsPage />} />` but `RunsPage` never reads the `runId` URL parameter. The route exists but serves no purpose different from `/runs`.

---

## 4. Low/Informational Findings

### 4.1 🟢 L-01: 3 Orphan/Dead Files

**Criteria Violated**: D6 (Dead Code)

| File                           | Status        | Evidence                                                         |
| ------------------------------ | ------------- | ---------------------------------------------------------------- |
| `src/models.py`                | Dead code     | Contains standalone `Trade` class. Zero imports across codebase. |
| `src/constants.py`             | Dead code     | Contains `ALPACA = "alpaca"`. Zero imports across codebase.      |
| `src/veda/base_api_handler.py` | Legacy orphan | From pre-M6 architecture. Zero imports.                          |

**Fix**: Delete all three files.

---

### 4.2 🟢 L-02: 3 Outstanding TODO/FIXME Comments

| Location                         | TODO Text                                                      | Assigned To            |
| -------------------------------- | -------------------------------------------------------------- | ---------------------- |
| `src/__main__.py:13`             | `TODO: Implement proper startup once modules are ready`        | M8-4                   |
| `src/greta/greta_service.py:504` | `TODO: Calculate more advanced stats (Sharpe, drawdown, etc.)` | M8-4                   |
| `src/greta/models.py:49`         | `TODO(M5): Change to OrderSide enum`                           | M8-4 (overdue from M5) |

---

### 4.3 🟢 L-03: Dual `Bar` Type Definitions

**Problem**: Two different `Bar` dataclasses exist:

| Location                                   | Fields                                | Used By                        |
| ------------------------------------------ | ------------------------------------- | ------------------------------ |
| `src/walle/repositories/bar_repository.py` | 7 fields (no `trade_count`, `vwap`)   | BarRepository, GretaService    |
| `src/veda/models.py`                       | 9 fields (with `trade_count`, `vwap`) | ExchangeAdapter, AlpacaAdapter |

**Impact**: Potential confusion. Not a bug since they serve different contexts (persistence vs. exchange), but should be documented or unified.

---

### 4.4 🟢 L-04: Veda.md Environment Variable Names Don't Match Code

**Criteria Violated**: D2 (Doc-Doc Consistency)

| What veda.md Says     | What config.py Uses       |
| --------------------- | ------------------------- |
| `ALPACA_PAPER_KEY`    | `ALPACA_PAPER_API_KEY`    |
| `ALPACA_PAPER_SECRET` | `ALPACA_PAPER_API_SECRET` |
| `ALPACA_LIVE_KEY`     | `ALPACA_LIVE_API_KEY`     |
| `ALPACA_LIVE_SECRET`  | `ALPACA_LIVE_API_SECRET`  |

---

### 4.5 🟢 L-05: Veda.md OrderStatus Enum Missing Values

**Problem**: The `veda.md` documentation shows `OrderStatus` with 7 values, but the actual code in `src/veda/models.py` has **9 values** (also includes `SUBMITTING` and `SUBMITTED`).

| In Docs     | In Code      | Status               |
| ----------- | ------------ | -------------------- |
| `pending`   | `pending`    | ✅                   |
| —           | `submitting` | ❌ Missing from docs |
| —           | `submitted`  | ❌ Missing from docs |
| `accepted`  | `accepted`   | ✅                   |
| `partial`   | `partial`    | ✅                   |
| `filled`    | `filled`     | ✅                   |
| `cancelled` | `cancelled`  | ✅                   |
| `rejected`  | `rejected`   | ✅                   |
| `expired`   | `expired`    | ✅                   |

---

### 4.6 ℹ️ I-01: Empty `src/utils/` Directory in Frontend

`haro/src/utils/` exists but is empty. Not a problem, but can be removed if not planned for use.

---

### 4.7 ℹ️ I-02: Unused Hooks

`useRun(runId)` and `useOrder(orderId)` hooks are defined but never used by any page component. They may be intended for future use (e.g., run detail page).

---

### 4.8 ℹ️ I-03: api.md Documents `POST /api/v1/orders` but Design Context Shows SSE Events Pattern

The `api.md` doc at §3.3 shows the SSE event mapping table, which correctly documents 7 events. The actual implementation matches, except for the casing issue noted in C-01.

---

## 5. Design Document Consistency

### 5.1 Cross-Document Verification

| Document A                      | Document B                  | Consistent?  | Issue                                                                                 |
| ------------------------------- | --------------------------- | ------------ | ------------------------------------------------------------------------------------- |
| `events.md` §2 Namespaces       | `types.py` constants        | ⚠️ Partial   | events.md shows `orders.Created` but it's missing from `ALL_EVENT_TYPES` (M-01)       |
| `events.md` §8 Subscription API | `log.py` InMemoryEventLog   | ✅ Match     | `subscribe_filtered()` API matches exactly                                            |
| `api.md` §1 Endpoints           | `routes/*.py` actual routes | ❌ Mismatch  | Missing `POST /start` route (C-02); health path wrong (C-03)                          |
| `api.md` §3.3 SSE Events        | `useSSE.ts` listeners       | ❌ Mismatch  | Run event casing (C-01)                                                               |
| `api.md` §3.5 TypeScript Types  | `types.ts` actual types     | ✅ Match     | All types aligned                                                                     |
| `veda.md` §2 ExchangeAdapter    | `interfaces.py` protocol    | ✅ Match     | All methods present                                                                   |
| `veda.md` §3 Plugin System      | `adapter_loader.py` code    | ✅ Match     | AST discovery matches                                                                 |
| `veda.md` §8 Env Vars           | `config.py` AlpacaConfig    | ❌ Mismatch  | Var names differ (L-04)                                                               |
| `clock.md` §1 BaseClock         | `clock/base.py` class       | ✅ Match     | Interface matches                                                                     |
| `clock.md` §5 ClockTick         | `clock/base.py` dataclass   | ✅ Match     | Fields match                                                                          |
| `config.md` §2 Credentials      | `config.py` AlpacaConfig    | ✅ Match     | Dual credential pattern implemented                                                   |
| `DEVELOPMENT.md` §5 Testing     | Actual test structure       | ✅ Match     | Pyramid pattern observed                                                              |
| `MILESTONE_PLAN.md` test counts | Actual test counts          | ⚠️ Minor     | Docs say 808 backend, actual is 809 (1 off)                                           |
| `roadmap.md` §4 Invariants      | Actual code                 | ⚠️ Violation | Invariant #2 (VedaService as entry) violated by MockOrderService in GET routes (C-04) |

### 5.2 Architecture Invariant Compliance

| #   | Invariant                                        | Compliant? | Notes                                                   |
| --- | ------------------------------------------------ | ---------- | ------------------------------------------------------- |
| 1   | Single EventLog                                  | ✅         | All components share one instance                       |
| 2   | VedaService as entry (not OrderManager directly) | ⚠️         | GET orders still routes through MockOrderService (C-04) |
| 3   | Session per request                              | ✅         | FastAPI DI provides per-request sessions                |
| 4   | SSE receives all events                          | ✅         | EventLog → SSEBroadcaster subscription in lifespan      |
| 5   | Graceful degradation (works without DB_URL)      | ✅         | Conditional initialization in `app.py`                  |
| 6   | No module singletons                             | ✅         | All services via DI (old singleton pattern removed)     |
| 7   | Multi-Run Support                                | ✅         | Per-run GretaService/StrategyRunner/Clock instances     |
| 8   | Run Isolation                                    | ✅         | Events carry `run_id`; consumers filter                 |
| 9   | Plugin Architecture                              | ✅         | AST-based discovery for strategies and adapters         |

---

## 6. Code vs Design Verification Matrix

### 6.1 Backend Endpoints

| Documented Endpoint            | Route File          | Implemented?   | Test File               | Tested?      |
| ------------------------------ | ------------------- | -------------- | ----------------------- | ------------ |
| `GET /healthz`                 | `routes/health.py`  | ✅             | `test_health.py`        | ✅ (4 tests) |
| `GET /api/v1/runs`             | `routes/runs.py`    | ✅             | `test_runs.py`          | ✅           |
| `POST /api/v1/runs`            | `routes/runs.py`    | ✅             | `test_runs.py`          | ✅           |
| `GET /api/v1/runs/{id}`        | `routes/runs.py`    | ✅             | `test_runs.py`          | ✅           |
| `POST /api/v1/runs/{id}/start` | —                   | ❌ **MISSING** | —                       | ❌           |
| `POST /api/v1/runs/{id}/stop`  | `routes/runs.py`    | ✅             | `test_runs.py`          | ✅           |
| `GET /api/v1/orders`           | `routes/orders.py`  | ✅ (via Mock)  | `test_orders.py`        | ✅           |
| `POST /api/v1/orders`          | `routes/orders.py`  | ✅ (via Veda)  | `test_order_routing.py` | ✅           |
| `GET /api/v1/orders/{id}`      | `routes/orders.py`  | ✅ (via Mock)  | `test_orders.py`        | ✅           |
| `DELETE /api/v1/orders/{id}`   | `routes/orders.py`  | ✅ (via Veda)  | `test_order_routing.py` | ✅           |
| `GET /api/v1/candles`          | `routes/candles.py` | ✅             | `test_candles.py`       | ✅           |
| `GET /api/v1/events/stream`    | `routes/sse.py`     | ✅             | `test_sse.py`           | ✅           |

### 6.2 Frontend Pages vs Design

| Page           | Documented?   | Implemented? | Tests?           |
| -------------- | ------------- | ------------ | ---------------- |
| Dashboard      | ✅ (M7-3)     | ✅           | ✅ 7 tests       |
| RunsPage       | ✅ (M7-4)     | ✅           | ✅ 14 tests      |
| OrdersPage     | ✅ (M7-5)     | ✅           | ✅ 7 tests       |
| NotFound (404) | Not specified | ✅           | ✅ (in App.test) |

### 6.3 Module Interface Compliance

| Module          | Documented Interface                                                                               | Code Matches? | Notes                                                    |
| --------------- | -------------------------------------------------------------------------------------------------- | ------------- | -------------------------------------------------------- |
| EventLog        | `append`, `read_from`, `subscribe`, `subscribe_filtered`, `unsubscribe_by_id`, `get_latest_offset` | ✅            | Both InMemory and Postgres implement all methods         |
| ExchangeAdapter | 14 abstract methods                                                                                | ✅            | Both AlpacaAdapter and MockAdapter implement all methods |
| BaseClock       | `start`, `stop`, `current_time`, `on_tick`                                                         | ✅            | Both BacktestClock and RealtimeClock implement           |
| BaseStrategy    | `initialize`, `on_tick`, `on_data`                                                                 | ✅            | SMAStrategy and SampleStrategy implement                 |
| StrategyLoader  | `load(strategy_id)`                                                                                | ✅            | SimpleStrategyLoader and PluginStrategyLoader implement  |
| AdapterLoader   | `load(adapter_id, **kwargs)`                                                                       | ✅            | PluginAdapterLoader implements                           |

---

## 7. Test Coverage Accuracy

### 7.1 Claimed vs Actual Test Counts

| Source              | Claims                          | Actual                          | Delta |
| ------------------- | ------------------------------- | ------------------------------- | ----- |
| `ARCHITECTURE.md`   | 808 backend + 86 frontend = 894 | 808 backend + 86 frontend = 894 | 0     |
| `TEST_COVERAGE.md`  | 808 backend + 86 frontend       | 808 backend + 86 frontend       | 0     |
| `roadmap.md`        | 808 backend                     | 808 backend                     | 0     |
| `MILESTONE_PLAN.md` | 808 backend + 86 frontend       | 808 backend + 86 frontend       | 0     |

**Verified**: 2026-02-19 via `pytest --co -q` and `vitest --run`.

### 7.2 Test Type Distribution (Actual)

| Type        | Backend | Frontend | Total   |
| ----------- | ------- | -------- | ------- |
| Unit        | 764     | 86       | 850     |
| Integration | 44      | 0        | 44      |
| E2E         | 0       | 0        | 0       |
| **Total**   | **808** | **86**   | **894** |

---

## 8. M8 Execution Checklist (Fixes & Improvements)

### 8.1 Phase 0: Critical Contract Fixes (M8-P0) — Must Fix First

- [ ] **C-01**: Fix SSE event name casing — align frontend `useSSE.ts` to use `run.Started`, `run.Stopped`, `run.Completed`, `run.Error` (match backend)
- [ ] **C-02**: Add `POST /api/v1/runs/{run_id}/start` route in `routes/runs.py`
- [ ] **C-03**: Fix health endpoint path — add `/api/v1` prefix to health router or change frontend
- [ ] **C-04**: Update `GET /orders` and `GET /orders/{id}` to use VedaService when available (fall back to MockOrderService)
- [ ] **N-02**: Add error handling to `_start_live` (copy `_start_backtest` pattern)
- [ ] **N-09**: Unify `time_in_force` defaults
- [ ] **M-01**: Add missing events to `ALL_EVENT_TYPES`
- [ ] **M-03**: Add `orders.Cancelled` listener to frontend `useSSE.ts`

### 8.2 Phase 1: Runtime Wiring (M8-P1)

- [ ] **N-01/N-07**: Fix EventLog subscriber dispatch parity (Package B + D-1)
- [ ] Wire DomainRouter as standalone singleton (Package B + D-4)
- [ ] Inject RunManager runtime dependencies (Package A)
- [ ] Per-run cleanup guarantees (Package A)
- [ ] Unify order read/write sources (Package C)

### 8.3 Code Quality & P1 Fixes (M8-Q)

- [x] **M-02**: Add server-side pagination/filtering to runs and orders list endpoints
- [x] **M-04**: Change `SimulatedFill.side` from `str` to `OrderSide` enum
- [x] **M-07**: Kept `/runs/:runId` deep-link route and wired `useParams` handling in RunsPage
- [x] **N-03**: Add Fills table + persist fill history (D-3) — FillRecord, FillRepository, VedaService wiring, migration
- [x] **N-04**: Wrap AlpacaAdapter sync SDK in `asyncio.to_thread()`
- [x] **N-06**: Add `run_id` query param to SSE endpoint (D-5)
- [x] **N-10**: Implement server-side pagination or remove UI
- [x] **D-2**: Add Runs table for restart recovery — RunRecord, RunRepository, RunManager persistence + recover(), migration

### 8.4 Documentation (M8-D)

- [ ] Create `docs/architecture/greta.md`
- [ ] Create `docs/architecture/marvin.md`
- [ ] Create `docs/architecture/walle.md`
- [ ] Document SSE event wire format
- [ ] Document error handling strategy
- [ ] Fix ARCHITECTURE.md §5 false SSE run_id claim
- [ ] Update veda.md env var names (L-04) and OrderStatus enum (L-05)

### 8.5 Code Cleanup (Low)

- [ ] **L-01**: Delete orphan files: `src/models.py`, `src/constants.py`, `src/veda/base_api_handler.py`
- [ ] **L-02**: Resolve 3 TODO/FIXME comments
- [ ] **L-03**: Document or unify dual `Bar` types

### 8.6 Commit & Merge Checklist

- [ ] Apply M8-P0 critical fixes on `haro_update`
- [ ] Run full test suite (both backend and frontend)
- [ ] Update test counts in docs after each phase
- [ ] Merge to `main` after M8 complete

---

## 9. M9 Checklist (E2E Tests & Release Prep)

### 9.1 E2E Setup

- [ ] Configure Playwright
- [ ] Setup test database + Docker Compose for E2E
- [ ] Basic page load tests

### 9.2 E2E User Flows

- [ ] Create backtest run → view progress → view results
- [ ] Create paper run → monitor status → stop run
- [ ] View generated orders after backtest
- [ ] Dashboard reflects active run count

### 9.3 Release Polish

- [ ] Deployment guide (production Docker Compose)
- [ ] Final cross-doc consistency check
- [ ] Smoke test: fresh deploy → create run → verify

---

## Appendix A: File Inventory

### Orphan Files (safe to delete)

```
src/models.py              # Standalone Trade class, 0 imports
src/constants.py           # ALPACA = "alpaca", 0 imports
src/veda/base_api_handler.py  # Legacy pre-M6, 0 imports
```

### Key Files (M7-6 SSE — committed on haro_update)

```
haro/src/components/common/ConnectionStatus.tsx  (new)
haro/src/components/common/Toast.tsx            (new)
haro/src/hooks/useSSE.ts                        (new)
haro/src/stores/notificationStore.ts            (new)
haro/tests/unit/components/Toast.test.tsx       (new)
haro/tests/unit/hooks/useSSE.test.tsx           (new)
haro/tests/unit/stores/notificationStore.test.ts (new)
+ 6 modified files (App.tsx, Layout.tsx, Header.tsx, etc.)
+ 5 modified docs
```

---

_Generated: 2026-02-15_
_Updated: 2026-02-19 (M7 closed, M8 = fixes & improvements, M9 = E2E tests)_

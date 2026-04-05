# Weaver Milestone Plan (2026-02-19)

> **Document Charter**
> **Primary role**: authoritative milestone execution plan and current status.
> **Authoritative for**: milestone progress, task breakdown, timeline, and risks.
> **Not authoritative for**: historical full audit trail (use `AUDIT_FINDINGS.md`).

> **Current State**: M7 ✅ Formally Closed · M8 ✅ Complete · M9 ✅ Complete · M10 ✅ Complete · M11 ✅ Complete · **M12 ✅ Complete** · **M12-B ✅ Complete**
> **Tests (latest verified)**: 987 backend unit + 50 integration + 109 frontend + 33 E2E = 1179 passed (2026-04-03)
> **Active Milestone**: **M13** (Backtest Results) — next up
> **Remaining Backlog**: E-3, R-1, R-2
> **Planned**: M13 (Backtest Results) → M14 (Live Monitoring) → M15 (Navigation & Fixes) → M16 (Strategy Iteration) → M17 (Risk & Production)
> **Completed**: All planned milestones (M5–M12), CI audit Waves 1–4, PR #15 merged, PR #16 (M11)

---

## Executive Summary

All pending tasks have been consolidated and reorganized into 7 milestones (M5–M11).
M7 is formally closed as of 2026-02-19. M8 is complete as of 2026-02-26. M9 (CI) is complete. M10 (E2E Tests) is complete as of 2026-03-16 with 23 Playwright E2E tests. **M11 (Runtime Robustness & UX Polish) is complete** as of 2026-03-24 — fixed backtest async race, added concurrency safety, strategy error propagation, frontend error feedback, unified dev environment, and bar dict→Bar deserialization in StrategyRunner. Post-PR-review fixes: extracted shared Alpaca credential helper, added public `BacktestClock.error` property, hardened CI scripts to reject all arguments. 48 new tests added (1137 total).

**Post-M10 CI Audit** (2026-03-21 – 2026-03-22): ✅ All 4 waves complete. Waves 1–3 added 10 E2E tests, 6 Alpaca integration tests, and frontend coverage reporting. Wave 4 fixed 2 production bugs (submit_order/list_orders SDK contract mismatch), CI path resolution, and mock hardening. Post-Wave 4 hardening: GitHub Actions upgraded to Node.js 24, npm dependency vulnerabilities patched (flatted, undici), workflow permissions locked to least-privilege, coverage artifacts removed from git. PR #15 merged to main with all 5 CI workflows green. See `CI_TEST_AUDIT.md` for full details.

| Milestone | Name               | Core Objective                                             | Tests | Status                                |
| --------- | ------------------ | ---------------------------------------------------------- | ----- | ------------------------------------- |
| **M5**    | Marvin Core        | Strategy system + Plugin architecture                      | 74    | ✅ DONE                               |
| **M6**    | Live Trading       | Paper/Live trading flow                                    | 101   | ✅ DONE (808 total)                   |
| **M7**    | Haro Frontend      | React UI + SSE                                             | 86    | ✅ DONE (894 total)                   |
| **M8**    | Fixes & Improve    | Critical fixes + Runtime wiring + Quality                  | 129   | ✅ DONE (historical cumulative: 1023) |
| **M9**    | CI Deployment      | PR quality gates + container smoke + branch protection     | -     | ✅ COMPLETE                           |
| **M10**   | E2E & Release Prep | End-to-end tests + Final polish                            | 23    | ✅ DONE (1055 total)                  |
| **M11**   | Runtime Robustness | Async race fix + Concurrency safety + UX polish + Dev env  | 48    | ✅ DONE (1137 total)                  |
| **M12**   | Spec Alignment     | Run config refactor + Strategy API + RJSF dynamic forms    | 42    | ✅ DONE (1179 total)                  |
| **M12-B** | Frontend Hardening | SSE safety + Symbols UX + a11y + Pagination + Dead code    | ~20   | ✅ COMPLETE                           |
| **M13**   | Backtest Results   | Persist results + Results API + Detail page + Equity chart | —     | 📋 PLANNED                            |
| **M14**   | Live Monitoring    | Positions/fills/account API + Monitoring UI + Real candles | —     | 📋 PLANNED                            |
| **M15**   | Navigation & Fixes | Linked navigation + Sort/filter + All frontend bug fixes   | —     | 📋 PLANNED                            |
| **M16**   | Strategy Iteration | Versioning + Clone + Comparison + One-click backtest       | —     | 📋 PLANNED                            |
| **M17**   | Risk & Production  | Risk enforcement + Data ingest + Export + Observability    | —     | 📋 PLANNED                            |

**M12 Complete** (42 tests added): Run config refactor (S1), strategy interface (S2+S3), config_schema metadata (S4+S6), production safety (S8), backtest config source (S9), frontend full-stack alignment (S11-S15). RJSF dynamic forms with custom Tailwind templates. See [m12-spec-alignment.md](archive/milestone-details/m12-spec-alignment.md).

**M12-B Complete** (Frontend Hardening): SSE JSON.parse safety (H1), symbols enum dropdown (H2), dead code cleanup (H3), modal a11y with @headlessui/react (H4), table overflow-x-auto (H5 partial — OrderTable done, RunsPage rows deferred to M15), pagination component (H6), responsive sidebar (H7) deferred. Design docs at [m12b-frontend-hardening.md](archive/milestone-details/m12b-frontend-hardening.md) and [m12b-execution.md](archive/milestone-details/m12b-execution.md).

**M6 Complete** (101 tests added):

1. ✅ PluginAdapterLoader (mirrors PluginStrategyLoader pattern)
2. ✅ AdapterMeta dataclass with features support
3. ✅ AlpacaAdapter connect()/disconnect()/is_connected
4. ✅ VedaService wired to order routes
5. ✅ Live order flow with events + persistence
6. ✅ RealtimeClock for live runs

**M7 Complete** (86 tests):

- M7-0: Dev Environment Setup ✅
- M7-1: React App Scaffold ✅ (8 tests)
- M7-2: API Client Layer ✅ (9 tests)
- M7-3: Dashboard Page ✅ (15 tests)
- M7-4: Runs Page ✅ (14 tests)
- M7-5: Orders Page ✅ (17 tests)
- M7-6: SSE Integration ✅ (23 tests)

---

## 1. M5: Marvin Core (Strategy System) ✅ COMPLETE

> **Goal**: Complete strategy loading, execution, and backtest core flow
> **Status**: ✅ COMPLETE (74 tests, 705 total)
> **Prerequisite**: M4 ✅
> **Estimated Effort**: 2-3 weeks

### 1.1 Exit Gate (Definition of Done)

- [ ] EventLog subscription mechanism completed
- [ ] data.WindowReady event flow completed
- [ ] SMA strategy implemented and backtested successfully
- [ ] PluginStrategyLoader implemented (auto-discovery)
- [ ] System works after deleting strategy files

### 1.2 MVP Breakdown

| MVP  | Focus                  | Tests | Dependencies |
| ---- | ---------------------- | ----- | ------------ |
| M5-1 | EventLog Subscription  | ~10   | -            |
| M5-2 | data.WindowReady Flow  | ~15   | M5-1         |
| M5-3 | SMA Strategy           | ~12   | M5-2         |
| M5-4 | Plugin Strategy Loader | ~15   | M5-3         |
| M5-5 | Code Quality (Marvin)  | ~8    | -            |

### 1.3 Detailed Tasks

#### M5-1: EventLog Subscription (~10 tests)

```
- [ ] Add subscribe()/unsubscribe() to EventLog protocol
- [ ] Implement subscription in InMemoryEventLog
- [ ] Implement subscription in PostgresEventLog
- [ ] Test: multiple subscribers receive events
- [ ] Test: unsubscribed consumer stops receiving
```

#### M5-2: data.WindowReady Flow (~15 tests)

```
- [ ] StrategyRunner subscribes to data.WindowReady
- [ ] GretaService subscribes to backtest.FetchWindow (M4 deferred)
- [ ] GretaService emits data.WindowReady
- [ ] Test: complete FetchWindow → WindowReady chain
- [ ] Test: error handling when no data available
```

#### M5-3: SMA Strategy (~12 tests)

```
- [ ] Create src/marvin/strategies/ directory
- [ ] Implement SMAStrategy (dual moving average crossover)
- [ ] Configurable parameters: fast_period, slow_period
- [ ] Test: SMA calculation correctness
- [ ] Test: crossover signal generation
- [ ] Integration test: SMA backtest produces trades
```

#### M5-4: Plugin Strategy Loader (~15 tests)

```
- [ ] Create StrategyMeta dataclass
- [ ] Create @strategy decorator (optional)
- [ ] Implement PluginStrategyLoader (directory scanning)
- [ ] Dependency resolution (topological sort)
- [ ] Add STRATEGY_META to sample_strategy.py
- [ ] Remove hardcoded imports from __init__.py
- [ ] Test: discover strategies in directory
- [ ] Test: load by ID
- [ ] Test: dependency resolution
- [ ] Test: deleted strategy = system works
- [ ] Test: missing dependency error
```

#### M5-5: Code Quality - Marvin (~8 tests)

```
- [ ] SimulatedFill.side: str → OrderSide enum
- [ ] Extract SimpleTestStrategy to fixtures
- [ ] Extract MockStrategyLoader to fixtures
- [ ] Fix ClockTick duplicate definition
- [ ] Clock Union type (BacktestClock | RealtimeClock)
```

---

## 2. M6: Live Trading

> **Goal**: Complete paper/live trading full flow
> **Prerequisite**: M5 ✅
> **Estimated Effort**: 1.5-2 weeks
> **Design Doc**: [m6-live-trading.md](archive/milestone-details/m6-live-trading.md)

### 2.1 Exit Gate (Definition of Done)

- [x] PluginAdapterLoader with auto-discovery (mirrors strategy pattern) ✅ 2026-02-04
- [x] AlpacaAdapter `connect()` initializes real clients ✅ 2026-02-04
- [x] VedaService wired to order routes (replaces MockOrderService) ✅ 2026-02-04
- [x] Paper Trading orders persist + emit events ✅ 2026-02-04
- [x] Live Run uses RealtimeClock ✅ 2026-02-04
- [x] ~91 new tests (target: 770+) → actual: 806 ✅

### 2.2 MVP Breakdown

| MVP  | Focus                    | Tests | Dependencies |
| ---- | ------------------------ | ----- | ------------ |
| M6-1 | PluginAdapterLoader      | 40 ✅ | -            |
| M6-2 | AlpacaAdapter Connection | 23 ✅ | M6-1 ✅      |
| M6-3 | VedaService Routing      | 13 ✅ | M6-2 ✅      |
| M6-4 | Live Order Flow          | 15 ✅ | M6-3 ✅      |
| M6-5 | Run Mode Integration     | 10 ✅ | M6-4 ✅      |

### 2.3 Detailed Tasks

#### M6-1: PluginAdapterLoader ✅ COMPLETE (40 tests)

**Files**: `adapter_meta.py`, `adapter_loader.py` (CREATED), adapters/\*.py (MODIFIED)

```
- [x] Create AdapterMeta dataclass (id, name, version, class_name, features)
- [x] Implement PluginAdapterLoader with AST-based metadata extraction
- [x] Add ADAPTER_META to alpaca_adapter.py
- [x] Add ADAPTER_META to mock_adapter.py
- [x] Test: discover adapters in directory
- [x] Test: load adapter by ID
- [x] Test: pass credentials to adapter constructor
- [x] Test: unknown adapter raises AdapterNotFoundError
- [x] Test: extracts metadata without importing (AST)
- [x] Test: get_metadata(), supports_feature()
- [x] Test: empty directory returns empty list
- [x] Test: skip private files (_*)
```

#### M6-2: AlpacaAdapter Connection ✅ COMPLETE (23 tests)

**Files**: `adapters/alpaca_adapter.py` (MODIFIED)

```
- [x] Add connect() method
- [x] Initialize TradingClient with api_key, secret_key, paper
- [x] Initialize CryptoHistoricalDataClient
- [x] Initialize StockHistoricalDataClient
- [x] Verify connection via account status check
- [x] Add is_connected property
- [x] Add disconnect() method
- [x] Add _require_connection() guard
- [x] Test: connect creates all clients
- [x] Test: connect verifies account ACTIVE
- [x] Test: inactive account raises ConnectionError
- [x] Test: connect idempotent
- [x] Test: disconnect clears clients
- [x] Test: submit_order requires connection
- [ ] Test: paper/live mode flag passed correctly
```

#### M6-3: VedaService Routing ✅ COMPLETE (13 tests)

**Files**: `routes/orders.py` (MODIFIED), `schemas.py` (MODIFIED)

```
- [x] Add OrderCreate schema to schemas.py
- [x] Add POST /orders endpoint using VedaService
- [x] Add DELETE /orders/{id} endpoint for cancel
- [x] Handle 503 when VedaService not configured
- [x] _state_to_response() converter
- [x] _require_veda_service() dependency
- [x] Test: create_order calls VedaService.place_order
- [x] Test: intent fields mapped correctly
- [x] Test: returns OrderResponse
- [x] Test: 422 for invalid input
- [x] Test: 503 when no VedaService
- [x] Test: cancel_order calls VedaService
- [x] Test: cancel nonexistent returns 404
```

#### M6-4: Live Order Flow ✅ COMPLETE (15 tests)

**Files**: `veda_service.py` (MODIFIED), `interfaces.py` (MODIFIED), `mock_adapter.py` (MODIFIED)

```
- [x] Add VedaService.connect() method
- [x] Add VedaService.disconnect() method
- [x] Add VedaService.is_connected property
- [x] Add connect/disconnect/is_connected to ExchangeAdapter interface
- [x] Add connect/disconnect/is_connected to MockExchangeAdapter
- [x] Fix place_order idempotency (only persist/emit once)
- [x] Test: VedaService has connect/disconnect/is_connected
- [x] Test: connect/disconnect delegate to adapter
- [x] Test: place_order persists to database
- [x] Test: place_order emits orders.Created event
- [x] Test: rejected order emits orders.Rejected event
- [x] Test: event includes exchange_order_id
- [x] Test: get_order from local state
- [x] Test: get_order falls back to repository
- [x] Test: list_orders / list_orders(run_id)
- [x] Test: idempotent submission
```

#### M6-5: Run Mode Integration ✅ COMPLETE (10 tests)

**Files**: `run_manager.py` (MODIFIED)

```
- [x] Update RunContext.clock type to BaseClock (Union)
- [x] Import RealtimeClock in run_manager.py
- [x] Implement _start_live() method for live/paper runs
- [x] Live/paper runs use RealtimeClock
- [x] Live runs stay RUNNING (context preserved)
- [x] Test: backtest uses BacktestClock
- [x] Test: live mode uses RealtimeClock
- [x] Test: paper mode uses RealtimeClock
- [x] Test: realtime clock uses current time
- [x] Test: backtest clock uses simulated time
- [x] Test: run.Started event includes mode
- [x] Test: stop live run stops clock
- [x] Test: cannot start already running
- [x] Test: run mode persisted on create
- [x] Test: run mode retrievable after get
```

---

## 3. M7: Haro Frontend

> **Goal**: React frontend to display trading status and data
> **Prerequisite**: M6 ✅
> **Estimated Effort**: 1.5-2 weeks
> **Design Document**: [m7-haro-frontend.md](archive/milestone-details/m7-haro-frontend.md)

### 3.1 Exit Gate (Definition of Done)

- [x] React app builds and runs in Docker container ✅
- [x] Dashboard displays system status and active runs ✅
- [x] Can create, view, and stop runs via UI ✅
- [x] Orders page shows order list with status ✅
- [x] SSE delivers real-time updates to UI ✅ 2026-02-06
- [x] 86 tests passing (unit + integration) ✅
- [x] TypeScript strict mode, no `any` types ✅

### 3.2 MVP Breakdown

| MVP  | Focus                 | Tests | Dependencies |
| ---- | --------------------- | ----- | ------------ |
| M7-0 | Dev Environment Setup | 0     | ✅           |
| M7-1 | React App Scaffold    | 8 ✅  | M7-0 ✅      |
| M7-2 | API Client Layer      | 9 ✅  | M7-1 ✅      |
| M7-3 | Dashboard Page        | 15 ✅ | M7-2 ✅      |
| M7-4 | Runs Page             | 14 ✅ | M7-3 ✅      |
| M7-5 | Orders Page           | 17 ✅ | M7-4 ✅      |
| M7-6 | SSE Integration       | 23 ✅ | M7-5 ✅      |

### 3.3 Technology Stack (Actual)

| Category  | Designed                 | Actual                          |
| --------- | ------------------------ | ------------------------------- |
| Framework | React 18 + TypeScript    | React 19.2 + TypeScript 5.9     |
| Build     | Vite 5                   | Vite 7.2                        |
| Routing   | React Router 6           | React Router 7.13               |
| State     | TanStack Query + Zustand | TanStack Query 5.90 + Zustand 5 |
| Styling   | Tailwind CSS + shadcn/ui | Tailwind CSS 4.1 (no shadcn/ui) |
| Testing   | Vitest + RTL + MSW       | Vitest 4 + RTL 16 + MSW 2.12    |

### 3.4 Dev Environment (Option 3: Hybrid)

```
┌─────────────────────────────────────────────────────────────┐
│  VS Code (backend_dev container)                            │
│  - Edit Python (src/) + React (haro/) in one window         │
│  - Python 3.13 + Node.js 20 (for IDE support)               │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│ backend_dev     │◀─────────│ frontend_dev    │
│ uvicorn :8000   │  proxy   │ vite :3000      │
│ (runs backend)  │          │ (runs frontend) │
└─────────────────┘          └─────────────────┘
```

See [design doc §3](archive/milestone-details/m7-haro-frontend.md#3-development-environment-setup) for full details.

---

## 4. M8: Critical Fixes & Improvements

> **Goal**: Fix all P0 critical issues, wire runtime pipeline, improve code quality
> **Prerequisite**: M7 ✅
> **Estimated Effort**: 1.5–2 weeks
> **Status**: ✅ COMPLETE
> **Key Input**: [INDEPENDENT_DESIGN_REVIEW.md](INDEPENDENT_DESIGN_REVIEW.md) (N-01–N-10, D-1–D-5)

### 4.1 Exit Gate (Definition of Done)

- [x] All P0 critical issues resolved (C-01–C-04, N-01/N-02/N-07)
- [x] Design decisions D-1 through D-5 implemented
- [x] DomainRouter wired into runtime lifecycle
- [x] RunManager dependencies fully injected
- [x] Code coverage ≥80% (pytest-cov: 89.78%)
- [x] All TODO/FIXME cleaned up
- [x] Documentation complete and accurate

### 4.2 MVP Breakdown

| MVP   | Focus                           | Est. Tests | Dependencies | Status |
| ----- | ------------------------------- | ---------- | ------------ | ------ |
| M8-P0 | Critical Contract Fixes         | ~15        | -            | ✅     |
| M8-P1 | Runtime Wiring (Packages A/B/C) | ~20        | M8-P0        | ✅     |
| M8-Q  | Code Quality & P1 Fixes         | 17         | M8-P0        | ✅     |
| M8-D  | Documentation                   | -          | M8-P1        | ✅     |

### 4.3 Detailed Tasks

#### M8-P0: Critical Contract Fixes (~15 tests)

**Priority**: Must fix before any other M8 work.

```
- [x] C-01: Fix SSE event casing — align frontend useSSE.ts to PascalCase
        (run.Started, run.Stopped, run.Completed, run.Error)
- [x] C-02: Add POST /api/v1/runs/{run_id}/start route + tests
- [x] C-03: Fix health endpoint path — add /api/v1 prefix or adjust frontend
- [x] C-04: Unify order read/write to VedaService (fallback to Mock when unconfigured)
- [x] N-02: Add error handling to _start_live (copy _start_backtest pattern)
- [x] N-09: Unify time_in_force defaults (schema vs handler)
- [x] M-01: Add missing events to ALL_EVENT_TYPES
        (RunEvents.CREATED, RunEvents.COMPLETED, OrderEvents.CREATED)
- [x] M-03: Add orders.Cancelled listener to frontend useSSE.ts
```

#### M8-P1: Runtime Wiring — Packages A/B/C (~20 tests)

**Requires**: Design decisions D-1, D-4 locked.

**Package A — Run Lifecycle (chosen: A2 lifecycle-first):**

```
- [x] Inject RunManager runtime dependencies (strategy_loader, bar_repository)
- [x] Per-run cleanup guarantees (stop/complete/error paths)
- [x] Integration test: start → run → stop lifecycle
- [x] Integration test: error during run → proper cleanup
```

**Package B — Event Pipeline Wiring (chosen: B2, with B1 fallback):**

```
- [x] D-1: Add direct subscriber dispatch in PostgresEventLog.append()
        (matching InMemoryEventLog behavior for in-process consumers)
- [x] D-4: Wire DomainRouter as standalone singleton in app lifespan
- [x] Integration test: append event → subscriber fires → SSEBroadcaster receives
- [x] Integration test: strategy.FetchWindow → DomainRouter → backtest.FetchWindow
```

**Package C — Data Source Unification (chosen: C1 hard unify):**

```
- [x] Unify orders list/get to VedaService in DB mode
- [x] Explicit non-durable semantics in no-DB mode
- [x] Integration test: write order → read order (same source)
```

#### M8-Q: Code Quality & P1 Fixes (~10 tests)

**Code Quality:**

```
- [x] L-01: Delete orphan files (src/models.py, src/constants.py, src/veda/base_api_handler.py)
- [x] L-02: Resolve 3 TODO/FIXME comments
- [x] M-04: Change SimulatedFill.side from str to OrderSide enum
- [x] N-05: Refactor StrategyAction to proper enum/union type
- [x] N-08: Compute advanced backtest stats (Sharpe, Sortino, max drawdown)
- [x] Fix Pylance/mypy warnings + strict type checking
- [x] Remove unused code
```

**P1 Standalone Fixes:**

```
- [x] N-03: Add Fills table + persist fill history (D-3: separate fills table) ✅ FillRecord + FillRepository + VedaService wiring + migration
- [x] N-04: Wrap AlpacaAdapter sync SDK in asyncio.to_thread()
- [x] N-06: Add run_id query param to SSE endpoint (D-5)
- [x] N-10: Implement server-side pagination or remove pagination UI
- [x] D-2: Add Runs table for restart recovery ✅ RunRecord + RunRepository + RunManager persistence + recover() + migration
- [x] M-07: Keep /runs/:runId deep-link route and wire RunsPage useParams handling
```

#### M8-D: Documentation

```
- [x] Create docs/architecture/greta.md (promote from milestone doc)
- [x] Create docs/architecture/marvin.md (promote from milestone doc)
- [x] Create docs/architecture/walle.md (schema, repos, migrations)
- [x] Document SSE event wire format (events.md §1.1)
- [x] Document error handling strategy (api.md §6)
- [x] Fix ARCHITECTURE.md §5 SSE run_id filtering (now accurate after D-5)
- [x] L-04: Fix env var names in veda.md to match config.py
- [x] L-05: Update OrderStatus enum docs to include submitting/submitted
- [x] Update README with usage instructions
- [ ] Strategy development guide (deferred to M10-4)
- [ ] Exchange adapter development guide (deferred to M10-4)
```

### 4.4 Design Decisions (All Locked)

| #   | Question                                          | Chosen Option                                 | Status    |
| --- | ------------------------------------------------- | --------------------------------------------- | --------- |
| D-1 | PostgresEventLog subscriber dispatch model        | **(a)** Direct dispatch in append + pg_notify | 🔒 Locked |
| D-2 | Should runs be persisted to database?             | **(b)** Add runs table                        | 🔒 Locked |
| D-3 | Should fills be persisted separately?             | **(b)** Separate fills table                  | 🔒 Locked |
| D-4 | DomainRouter: standalone or inline in RunManager? | **(a)** Separate wired singleton              | 🔒 Locked |
| D-5 | SSE run_id filtering?                             | **(a)** Yes, via query param                  | 🔒 Locked |

### 4.5 M8-R: Audit Closeout Plan (TDD + MVP, planning only)

> **Purpose**: final closeout of deployment blockers + runtime/doc consistency before M9.
> **Style**: TDD + MVP phased execution (RED → GREEN → REFACTOR).
> **Detailed plan document**: [archive/milestone-details/m8-fixes-improvements.md](archive/milestone-details/m8-fixes-improvements.md#9-m8-r-audit-closeout-plan-tdd--mvp-planning-only)
> **Audit baseline**: [M8_FINAL_PYRAMID_REVIEW.md](M8_FINAL_PYRAMID_REVIEW.md)

#### 4.5.1 High-Level Phases

| Phase | Focus                                        | Severity | Status |
| ----- | -------------------------------------------- | -------- | ------ |
| M8-R0 | Release blockers (compose/docker boot path)  | P0       | ✅     |
| M8-R1 | Runtime consistency (run status persistence) | P1       | ✅     |
| M8-R2 | Documentation authority sync                 | P1       | ✅     |
| M8-R3 | Contract hardening decisions                 | P2       | ✅     |

#### 4.5.2 M8-R Exit Gate (Summary)

- [x] P0 deployment blockers closed and smoke-verified
- [x] Run state persistence consistency verified by tests
- [x] Execution-layer docs synchronized and stale markers cleared
- [x] P2 items either implemented or formally deferred with rationale

#### 4.5.3 M8-R3 Closeout Decisions (2026-02-26)

- R-08 implemented: runs/orders list endpoints now enforce server-side `status` filtering contract (with existing pagination/filter semantics preserved).
- R-09 implemented: `RunManager` teardown now uses explicit per-run cleanup order (clock stop → `StrategyRunner.cleanup()` → `GretaService.cleanup()` when present).

---

## 5. M9: CI Deployment Pipeline

> **Goal**: establish stable PR quality gates and container smoke verification before E2E expansion
> **Prerequisite**: M8 ✅
> **Estimated Effort**: 1 week
> **Status**: ✅ COMPLETE
> **Design Doc**: [m9-ci-pipeline.md](archive/milestone-details/m9-ci-pipeline.md)

### 5.1 Exit Gate (Definition of Done)

- [x] Backend CI fast lane is green on PR (`ruff` + `mypy` + unit tests) ✅
- [x] Frontend CI fast lane is green on PR (`lint` + `test` + `build`) ✅
- [x] Compose smoke workflow runs in CI for docker/runtime-affecting changes ✅
- [x] Branch protection requires core CI checks before merge ✅
- [x] CI troubleshooting/runbook documented in README or DEVELOPMENT docs ✅

### 5.2 MVP Breakdown

| MVP  | Focus                              | Est. Tests | Dependencies |
| ---- | ---------------------------------- | ---------- | ------------ |
| M9-1 | Backend Fast CI (lint/type/unit)   | -          | -            |
| M9-2 | Frontend Fast CI (lint/test/build) | -          | M9-1         |
| M9-3 | Container Smoke CI Integration     | -          | M9-1, M9-2   |
| M9-4 | Branch Protection + CI Governance  | -          | M9-3         |

### 5.3 Detailed Tasks

#### M9-1: Backend Fast CI

```
- [x] Add/verify backend CI workflow (Python 3.13) ✅ .github/workflows/backend-ci.yml
- [x] Run ruff + mypy as required checks ✅
- [x] Run pytest unit scope (exclude container marker) ✅
- [x] Add dependency caching to reduce CI duration ✅
```

#### M9-2: Frontend Fast CI

```
- [x] Add/verify frontend CI workflow (Node 20) ✅ .github/workflows/frontend-ci.yml
- [x] Run npm lint + test + build ✅
- [x] Cache npm dependencies ✅
- [x] Fail fast on TypeScript or build regressions ✅
```

#### M9-3: Container Smoke Integration

```
- [x] Keep/extend compose-smoke workflow for runtime-affecting PRs ✅
- [x] Ensure logs are surfaced as CI artifacts on failure ✅
- [x] Validate API health + frontend availability checks in CI ✅
```

#### M9-4: Branch Protection + Governance

```
- [x] Define required checks for PR merge ✅
- [x] Document rerun/debug process for failed jobs ✅
- [x] Mark optional jobs (e.g., full integration suite) vs required checks ✅
```

---

## 6. M10: E2E Tests & Release Preparation

> **Goal**: Full end-to-end test coverage + final release polish
> **Prerequisite**: M9 ✅
> **Estimated Effort**: 1.5–2 weeks
> **Status**: ✅ COMPLETE
> **Design Doc**: [m10-e2e-release.md](archive/milestone-details/m10-e2e-release.md)

### 6.1 Exit Gate (Definition of Done)

- [x] Playwright installed in test-runner container (docker/e2e/Dockerfile)
- [x] `docker-compose.e2e.yml` starts isolated test stack with test_runner service
- [x] E2E tests pass (33 tests): navigation, backtest, paper, orders, orders lifecycle, SSE
- [x] Full user workflow validated end-to-end (browser-based, containerized)
- [ ] Production deployment guide complete (deferred to backlog)
- [ ] Strategy & adapter development guides complete (deferred to backlog)
- [x] All doc test counts updated to final numbers
- [x] E2E CI workflow runs on PR (`.github/workflows/e2e.yml`)
- [ ] Performance baselines documented (deferred to backlog)

### 6.2 MVP Breakdown

| MVP   | Focus                          | Est. Tests | Dependencies |
| ----- | ------------------------------ | ---------- | ------------ |
| M10-0 | E2E Infrastructure Setup       | 0          | -            |
| M10-1 | Core Navigation & Health       | ~6         | M10-0        |
| M10-2 | E2E Backtest Flow              | ~7         | M10-0        |
| M10-3 | E2E Live/Paper Flow            | ~5         | M10-0        |
| M10-4 | E2E Orders & SSE               | ~7         | M10-0        |
| M10-5 | Release Polish & Documentation | 0          | M10-1–M10-4  |

### 6.3 Detailed Tasks

#### M10-0: E2E Infrastructure Setup

```
- [x] Add playwright + pytest-playwright to requirements.dev.txt
- [x] Create docker/e2e/Dockerfile (test-runner: Python 3.13 + Playwright + Chromium)
- [x] Create docker-compose.e2e.yml (isolated stack with test_runner container)
- [x] Create tests/e2e/helpers.py (API client, constants, Docker-internal URLs)
- [x] Create tests/e2e/conftest.py (health-check fixtures, direct DB cleanup)
- [x] Create scripts/ci/e2e-local.sh (containerized test runner)
- [x] Configure pyproject.toml base_url for Playwright (Docker internal DNS)
```

#### M10-1: Core Navigation & Health (6 tests) ✅

```
- [x] Root redirects to /dashboard
- [x] Dashboard page loads with stat cards
- [x] Runs page loads
- [x] Orders page loads
- [x] 404 page for unknown routes
- [x] Sidebar navigation between pages
```

#### M10-2: E2E Backtest Flow (6 tests) ✅

```
- [x] Create backtest run via UI form
- [x] API-created run visible in UI
- [x] Start backtest → completes
- [x] Run detail deep-link view
- [x] Dashboard reflects run counts
- [x] Multiple backtests listed
```

#### M10-3: E2E Live/Paper Flow (5 tests) ✅

```
- [x] Create paper run → visible on runs page
- [x] Start paper run → shows RUNNING status
- [x] Dashboard shows active run count
- [x] Stop paper run → shows STOPPED status
- [x] Error state displayed correctly
```

#### M10-4: E2E Orders & SSE (6 tests) ✅

```
- [x] Orders page renders mock data
- [x] Order detail modal
- [x] SSE connection status shows "Connected"
- [x] SSE delivers real-time UI updates (no page reload needed)
- [x] SSE reconnects after interruption
- [x] SSE delivers run status change events
```

#### M10-5: Release Polish & Documentation ✅

```
- [ ] Production deployment guide in docs/architecture/deployment.md (deferred)
- [ ] Strategy development guide (deferred)
- [ ] Adapter development guide (deferred)
- [x] Update all doc test counts post-M10
- [ ] Cross-doc consistency check (deferred)
- [ ] Performance baselines documented (deferred)
- [ ] E2E CI workflow (.github/workflows/e2e.yml) (deferred)
- [ ] Smoke test: fresh deploy → create run → verify (deferred)
```

---

## 7. M11: Runtime Robustness & UX Polish

> **Goal**: Fix backtest async race (B-3), add concurrency safety (B-2), strategy error propagation (R-3), UX error feedback (F-2), and unify dev environment (B-8/B-9/B-10)
> **Prerequisite**: M10 ✅
> **Estimated Effort**: 2–3 weeks
> **Status**: ✅ COMPLETE
> **Design Doc**: [m11-runtime-robustness.md](archive/milestone-details/m11-runtime-robustness.md)

### 7.1 Exit Gate (Definition of Done)

- [x] All 5 design decisions (D-1–D-5) locked ✅ (2026-03-23)
- [x] Dev container has Docker CLI + socket mount; `check-all.sh` runs full CI inside container ✅ (M11-0)
- [x] Backtest order events (`orders.Placed`, `orders.Filled`) reach outbox — 3 xfail E2E tests pass ✅ (M11-1)
- [x] Strategy runtime errors produce `RunStatus.ERROR` + proper cleanup ✅ (M11-2)
- [x] Concurrent `start()`/`stop()` calls are safe (no state corruption) ✅ (M11-3)
- [x] `CreateRunForm` shows error toast on API failure ✅ (M11-4)
- [x] Alpaca integration tests skip correctly with placeholder credentials ✅ (M11-5)
- [x] All xfail markers removed from E2E tests ✅ (M11-5)
- [x] All CI workflows green ✅
- [x] 48 new tests (target was ~18) ✅

### 7.2 PR Review Fixes (Post-M11 Completion)

PR #16 review addressed the following:

- **Bar deserialization fix**: `StrategyRunner.on_data_ready()` now converts bar dicts from `data.WindowReady` payload into `Bar` objects with `Decimal` fields and `datetime` timestamps. This was the root cause of E2E `Events: []` failures.
- **Shared Alpaca credential helper**: Extracted `has_real_alpaca_creds()` to `tests/alpaca_helpers.py`, used by both unit and integration tests.
- **Public `BacktestClock.error` property**: Added `@property error` to `BacktestClock`, replacing direct `_error` attribute access in `RunManager` and tests.
- **CI scripts hardened**: All 4 CI scripts (`check-all.sh`, `check-local.sh`, `e2e-local.sh`, `compose-smoke-local.sh`) reject all arguments — no shortcuts allowed.
- **Docker socket comment**: Added inline comment explaining `/var/run/docker.sock` bind-mount purpose.
- **Pre-commit note**: Added dev container requirement comment to `.pre-commit-config.yaml`.

### 7.3 MVP Breakdown

| MVP   | Focus                                   | Est. Tests | Dependencies | Status |
| ----- | --------------------------------------- | ---------- | ------------ | ------ |
| M11-0 | Dev Container Unification (B-8, B-9)    | 0          | D-4, D-5     | ✅     |
| M11-1 | Backtest Async Race Fix (B-3)           | 18         | D-1          | ✅     |
| M11-2 | Strategy Error Propagation (R-3)        | 10         | D-3, M11-1   | ✅     |
| M11-3 | Concurrent Run Safety (B-2)             | 8          | D-2, M11-1   | ✅     |
| M11-4 | CreateRunForm Error Feedback (F-2)      | 4          | - (parallel) | ✅     |
| M11-5 | Cleanup & Exit Gate (B-10, xfail, docs) | 5+2        | M11-1        | ✅     |

### 7.3 Design Decisions (All Locked — 2026-03-23)

| #   | Question                            | Chosen Option                        | Status    |
| --- | ----------------------------------- | ------------------------------------ | --------- |
| D-1 | Backtest task drain strategy        | **(a)** Task registry in RunContext  | 🔒 Locked |
| D-2 | Concurrent run protection scope     | **(a)** Per-run asyncio.Lock         | 🔒 Locked |
| D-3 | Strategy error propagation boundary | **(a)** Fail fast → ERROR + cleanup  | 🔒 Locked |
| D-4 | Dev container Docker socket access  | **(a)** Bind-mount Docker socket     | 🔒 Locked |
| D-5 | check-local.sh rewrite strategy     | **(b)** Two scripts: wrapper + inner | 🔒 Locked |

**See [detailed design doc](archive/milestone-details/m11-runtime-robustness.md) §3 for full trade-off analysis of each decision.**

### 7.4 Execution Order

```
M11-0: Dev Container (B-8 + B-9) ── D-4, D-5 must lock
    │ (not a hard blocker, but provides better debug env)
    ▼
M11-1: Backtest Async Race (B-3) ── D-1 must lock ← highest priority
    │
    ├─► M11-2: Error Propagation (R-3) ── D-3 must lock
    │
    └─► M11-3: Concurrent Safety (B-2) ── D-2 must lock
         │
M11-4: Frontend Error Feedback (F-2) ── independent, can run in parallel
         │
         ▼
M11-5: Cleanup (B-10 + xfail removal + docs)
```

---

## 8. Backlog (Deferred Tasks)

The following tasks have been incorporated into milestones or deferred:

### Incorporated into Milestones (M5–M10)

| Task                               | Source     | Assigned To |
| ---------------------------------- | ---------- | ----------- |
| EventLog subscription              | AUDIT 1.7  | M5-1        |
| GretaService subscribe FetchWindow | M4 defer   | M5-2        |
| SimulatedFill.side enum            | M4 note #4 | M5-5        |
| ClockTick duplicate                | M4 note #5 | M5-5        |
| AlpacaAdapter init                 | AUDIT 1.4  | M6-2        |
| VedaService routing                | AUDIT 1.3  | M6-3        |
| Sharpe ratio                       | greta TODO | M8-Q        |
| Max drawdown                       | greta TODO | M8-Q        |

### Incorporated into M11

| Task                                     | Source             | Assigned To |
| ---------------------------------------- | ------------------ | ----------- |
| Backtest async race fix (B-3)            | CI Audit §7.7      | M11-1       |
| Strategy runtime error propagation (R-3) | Independent Review | M11-2       |
| Concurrent run operation safety (B-2)    | Independent Review | M11-3       |
| CreateRunForm error feedback (F-2)       | CI Audit §7.7      | M11-4       |
| Dev container unification (B-8)          | CI Audit §7.7      | M11-0       |
| Local CI rewrite (B-9)                   | CI Audit §7.7      | M11-0       |
| Alpaca test skip placeholder fix (B-10)  | CI Audit §7.7      | M11-5       |

### Incorporated into M12

| Task                                    | Source           | Assigned To |
| --------------------------------------- | ---------------- | ----------- |
| Run config refactor (S1)                | PROD_TEST_REVIEW | M12 Phase 1 |
| Strategy interface refactor (S2+S3)     | PROD_TEST_REVIEW | M12 Phase 2 |
| Strategy metadata & API (S4+S6)         | PROD_TEST_REVIEW | M12 Phase 3 |
| Production safety (S8)                  | PROD_TEST_REVIEW | M12 Phase 4 |
| Backtest config source (S9)             | PROD_TEST_REVIEW | M12 Phase 5 |
| Frontend full-stack alignment (S11-S15) | PROD_TEST_REVIEW | M12 Phase 6 |

### Incorporated into M12-B — ✅ COMPLETE

| Task                           | Source         | Assigned To   | Status                                             |
| ------------------------------ | -------------- | ------------- | -------------------------------------------------- |
| SSE JSON.parse safety (H1)     | Frontend Audit | M12-B Phase 1 | ✅ Done                                            |
| Symbols enum dropdown (H2)     | Frontend Audit | M12-B Phase 2 | ✅ Done                                            |
| Dead code cleanup (H3)         | Frontend Audit | M12-B Phase 3 | ✅ Done                                            |
| Modal accessibility (H4)       | Frontend Audit | M12-B Phase 4 | ✅ Done                                            |
| Table overflow + keyboard (H5) | Frontend Audit | M12-B Phase 5 | ⚠️ Partial (RunsPage row keyboard deferred to M15) |
| Pagination UI (H6)             | Frontend Audit | M12-B Phase 6 | ✅ Done                                            |
| Responsive sidebar (H7)        | Frontend Audit | M12-B Phase 7 | Deferred (desktop-primary)                         |

### Deferred (M13+)

The following were originally in the M13+ backlog. Items marked ✦ have been
absorbed into the new M13–M17 plan below; remaining items stay in backlog.

| Task                             | Reason                                     | Status       |
| -------------------------------- | ------------------------------------------ | ------------ |
| Pagination/filtering E2E (E-3)   | M12-B adds pagination UI; E2E tests in M13 | Backlog      |
| Connection resilience (R-1)      | Requires retry/circuit-breaker design      | Backlog      |
| Multi-symbol backtests (R-2)     | Requires Greta/WallE architectural changes | Backlog      |
| Multi-exchange support (S5+S10)  | VedaService dict + Bar exchange field      | Backlog      |
| Backtest on-demand fetch (S7)    | Depends on multi-exchange (S5)             | Backlog      |
| Dynamic symbols API (/symbols)   | Depends on exchange adapter integration    | Backlog      |
| Multiple simultaneous strategies | High complexity, future enhancement        | Backlog      |
| Strategy optimization            | Requires more infrastructure               | Backlog      |
| Real money trading               | Requires more security measures            | → M17 prereq |
| WebSocket streaming              | Polling sufficient for MVP                 | Backlog      |

---

## 8b. M13–M17: System Audit Milestones

Source: `docs/UI_AUDIT.md` — full-stack audit identifying 52+ issues across
9 domains. These milestones address every finding in priority order.

### M13 — Backtest Results End-to-End

**Goal**: Make the core quant workflow work: run backtest → see results.

| Task  | Layer    | Description                                                                                | Audit ref |
| ----- | -------- | ------------------------------------------------------------------------------------------ | --------- |
| 13-1  | Backend  | `_start_backtest()` calls `greta.get_result()`; persist result + simulated positions to DB | A-1, A-6  |
| 13-2  | Backend  | New `backtest_results` table (or JSONB column on `runs`)                                   | —         |
| 13-3  | Backend  | `GET /runs/{id}/results` endpoint                                                          | —         |
| 13-4  | Backend  | Add `error` field to `RunResponse` schema                                                  | B-1       |
| 13-5  | Backend  | Validate backtest dates at creation time (not deferred to start)                           | B-4       |
| 13-6  | Frontend | Fix backtest form: `required` + controlled `value` binding                                 | C1, C2    |
| 13-7  | Frontend | Create `/runs/:runId` detail page with Results tab                                         | —         |
| 13-8  | Frontend | Add charting library; render equity curve                                                  | —         |
| 13-9  | Frontend | Add trade log table on detail page                                                         | —         |
| 13-10 | Frontend | Add success toast on run creation                                                          | M9        |

**Exit gate**: User creates backtest → dates validated → run executes → detail
page shows return, Sharpe, max drawdown, equity curve, and fill list.

---

### M14 — Live/Paper Monitoring

**Goal**: Give paper/live runs a dedicated monitoring view with real data.

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

**Exit gate**: Start paper trading → detail page shows live positions, P&L,
recent fills. Dashboard errors surface correctly.

---

### M15 — Navigation & Frontend Fixes

**Goal**: Connect the three disconnected pages; fix all remaining UI bugs.

| Task  | Layer    | Description                                                                    | Audit ref    |
| ----- | -------- | ------------------------------------------------------------------------------ | ------------ |
| 15-1  | Backend  | `GET /runs` add `strategy_id` query parameter                                  | B-2          |
| 15-2  | Backend  | List endpoints add `sort_by` / `order` parameters                              | B-3          |
| 15-3  | Backend  | Push pagination to DB (stop in-memory slicing)                                 | B-6          |
| 15-4  | Frontend | Run IDs → clickable `<Link>` to `/runs/:runId`                                 | M7           |
| 15-5  | Frontend | Add "View Orders" link per run row                                             | M6           |
| 15-6  | Frontend | `OrderDetailModal` run_id → link                                               | M4           |
| 15-7  | Frontend | `OrderTable` add `run_id` column                                               | M5           |
| 15-8  | Frontend | `OrdersPage` filter: add setter + clear button                                 | M1, m2       |
| 15-9  | Frontend | ActivityFeed items → clickable                                                 | —            |
| 15-10 | Frontend | Detail page breadcrumbs                                                        | —            |
| 15-11 | Frontend | Fix optimistic status overrides (clear on refetch)                             | C3           |
| 15-12 | Frontend | Stop button: add `disabled={isPending}`                                        | M2           |
| 15-13 | Frontend | ActivityFeed: fix duplicate `strategy_id` display                              | M3           |
| 15-14 | Frontend | Strategies dropdown: loading/error state                                       | M10          |
| 15-15 | Frontend | Barrel file: add `strategies` export                                           | M11          |
| 15-16 | Frontend | Minor fixes batch: m1, m3, m4, m5, m6, m7, m8, m9, m10                         | m1–m10       |
| 15-17 | Frontend | RunsPage table rows: add `tabIndex`, `role="button"`, `onKeyDown` keyboard nav | H5 remainder |

**Exit gate**: All pages cross-linked. No dead-end navigation. All
Critical/Major/Minor frontend bugs from audit resolved. Tables
keyboard-navigable. Pagination functional.

---

### M16 — Strategy Iteration & Research Workflow

**Goal**: Elevate from running one-off experiments to systematic research.

| Task  | Layer    | Description                                                  | Audit ref |
| ----- | -------- | ------------------------------------------------------------ | --------- |
| 16-1  | Backend  | Record strategy version on run creation                      | C-3       |
| 16-2  | Backend  | `POST /runs/{id}/clone` (or frontend pre-fill from existing) | B-9       |
| 16-3  | Backend  | Cross-run performance comparison endpoint                    | C-6       |
| 16-4  | Backend  | `GET /strategies` → typed response model + pagination        | B-5       |
| 16-5  | Frontend | Runs table: add performance columns (return, Sharpe, etc.)   | —         |
| 16-6  | Frontend | TanStack Table column sorting                                | —         |
| 16-7  | Frontend | "Clone Run" button (pre-fill CreateRunForm)                  | —         |
| 16-8  | Frontend | Strategy-level grouping/filter view                          | —         |
| 16-9  | Frontend | Backtest comparison view (side-by-side charts + stats)       | —         |
| 16-10 | Frontend | Backtests: merge create + start into single action           | D-3       |

**Exit gate**: Select strategy → view all backtests sorted by Sharpe → clone →
tweak param → one-click run → side-by-side comparison with previous.

---

### M17 — Risk Management & Production Hardening

**Goal**: Make the system safe for real money and long-term operation.

| Task  | Layer   | Description                                              | Audit ref |
| ----- | ------- | -------------------------------------------------------- | --------- |
| 17-1  | Backend | Enforce `max_concurrent_orders`                          | C-2       |
| 17-2  | Backend | Enforce `rate_limit_per_minute`                          | C-2       |
| 17-3  | Backend | Position size limits + max drawdown circuit breaker      | C-2       |
| 17-4  | Backend | Daily loss limit enforcement                             | C-2       |
| 17-5  | Backend | Run deletion / soft-delete / archival                    | C-1       |
| 17-6  | Backend | Bar data ingestion API                                   | C-4       |
| 17-7  | Backend | Results/fills/equity export (CSV/JSON)                   | C-5       |
| 17-8  | Backend | Benchmark comparison (alpha, beta, IR vs SPY)            | C-7       |
| 17-9  | Backend | Health endpoint: check real dependencies                 | B-10      |
| 17-10 | Backend | `/metrics` observability endpoint                        | C-9       |
| 17-11 | Backend | Strategy diagnostics API + `DecisionMade` event emission | C-10      |
| 17-12 | Backend | Run scheduling / recurring runs                          | C-8       |

**Exit gate**: Risk limits enforced end-to-end. Can ingest data, export results,
monitor system health. Safe for paper → live graduation.

---

## 9. Timeline

```
Week 1-2   │██████████████████████│ M5: Marvin Core          ✅
Week 3-4   │██████████████████│     M6: Live Trading         ✅
Week 5-6   │██████████████████│     M7: Haro Frontend        ✅
Week 7-8   │██████████████████████│ M8: Fixes & Improve      ✅
Week 9     │████████████│           M9: CI Deployment         ✅
Week 10    │████████████│           M10: E2E & Release        ✅
Week 11-12 │██████████████████│     M11: Runtime Robustness  ✅
Week 13-14 │██████████████████████│ M12: Spec Alignment        ✅
Week 15    │████████████│           M12-B: Frontend Hardening  ✅
           │                       ─── System Audit Phase ───
Week 15-16 │██████████████████████│ M13: Backtest Results      📋
Week 18-19 │██████████████████│     M14: Live Monitoring       📋
Week 20-21 │██████████████████████│ M15: Navigation & Fixes    📋
Week 22-23 │██████████████████│     M16: Strategy Iteration    📋
Week 24-26 │██████████████████████│ M17: Risk & Production     📋
```

### Key Dependencies

```
M4 (Done)
    │
    ▼
M5: Marvin Core ─────┐
    │                │
    ▼                ▼
M6: Live Trading ────┤
    │                │
    ▼                ▼
M7: Haro Frontend ───┤
    │                │
    ▼                ▼
M8: Fixes & Improve ─┤
    │                │
    ▼                ▼
M9: CI Deployment
    │
    ▼
M10: E2E & Release
    │
    ▼
M11: Runtime Robustness
    │
    ▼
M12: Spec Alignment
    │
    ▼
M12: Spec Alignment
    │
    ▼
M12-B: Frontend Hardening
    │
    ▼
    ─── System Audit Phase ───
    │
    ▼
M13: Backtest Results ────┐
    │                     │
    ├─────────────────────┤
    │                     │
    ▼                     ▼
M14: Live Monitoring   M15: Navigation & Fixes
    │                     │
    ├─────────────────────┤
    │                     │
    ▼                     ▼
M16: Strategy Iteration   │
    │                     │
    ▼                     │
M17: Risk & Production ◄──┘
```

---

## 10. Risks & Mitigations

| Risk                           | Probability | Impact | Mitigation                                    |
| ------------------------------ | ----------- | ------ | --------------------------------------------- |
| Alpaca API changes             | Low         | High   | Abstraction layer isolation, quick adaptation |
| Frontend development delay     | Medium      | Medium | Backend can complete first, CLI as fallback   |
| CI runtime too long            | Medium      | Medium | Split fast lanes + cache + selective triggers |
| Flaky E2E tests                | Medium      | Low    | Retry mechanism, isolated test environment    |
| Plugin architecture complexity | Low         | Medium | AST parsing has mature solutions              |

---

## 11. Success Metrics

### Test Count

| Milestone | New Tests | Cumulative |
| --------- | --------- | ---------- |
| M4 (Done) | -         | 631        |
| M5        | 74        | 705        |
| M6        | 101       | 808 ¹      |
| M7        | 86        | 894        |
| M8        | 129       | 1023       |
| M9        | -         | 1033       |
| M10       | ~20–30    | ~1053–1063 |
| M11       | ~18       | ~1107      |

¹ Backend count is 808; some docs historically reported 806/809 due to timing.

### Coverage Targets

| Module  | Target |
| ------- | ------ |
| events/ | 90%    |
| glados/ | 85%    |
| veda/   | 85%    |
| greta/  | 90%    |
| marvin/ | 85%    |
| walle/  | 80%    |
| haro/   | 75%    |

---

_Last Updated: 2026-03-23_
_M7 Formally Closed: 2026-02-19_
_M8 Complete: 2026-02-26_
_Total Tests (latest verified): 1089 passed (2026-03-22)_
_M8 Scope: Critical fixes + Improvements (129 tests added; all gates passed)_
_M9 Scope: CI deployment pipeline + merge gates_
_M10 Scope: E2E tests + Release prep (33 E2E tests)_
_M11 Scope: Runtime robustness + UX polish + Dev env unification (~18 tests, ~2–3 weeks)_

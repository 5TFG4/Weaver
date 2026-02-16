# Independent Design Review — Full System Audit

> **Document Charter**  
> **Primary role**: detailed analysis narrative for Segment 6 independent audit.  
> **Authoritative for**: module-by-module deep analysis, alignment matrices, cross-cutting verification evidence.  
> **Not authoritative for**: finding IDs, action queue, or design decisions — those are controlled in `DESIGN_REVIEW_PLAN.md` §6.7, §7, §9.5.

> **Reviewer**: Independent fresh-start review  
> **Date**: 2026-02-16  
> **Scope**: Full system — architecture docs, code, tests, cross-cutting concerns  
> **Method**: Bottom-up code reading + top-down documentation validation, deliberately ignoring prior review conclusions until final cross-check  
> **Constraint**: Documentation-only — no code changes

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Direction Assessment](#2-architecture-direction-assessment)
3. [Critical Issues (New Findings + Confirmed)](#3-critical-issues)
4. [Significant Design Concerns (Newly Identified)](#4-significant-design-concerns)
5. [Design-Code Alignment Matrix](#5-design-code-alignment-matrix)
6. [Module-by-Module Deep Review](#6-module-by-module-deep-review)
7. [Cross-Cutting Invariant Verification](#7-cross-cutting-invariant-verification)
8. [Documentation Quality & Consistency](#8-documentation-quality--consistency)
9. [Risk Assessment & Priority Ordering](#9-risk-assessment--priority-ordering)
10. [Recommendations](#10-recommendations)
11. [Comparison with Existing Reviews](#11-comparison-with-existing-reviews)

---

## 1. Executive Summary

### Overall Verdict: Architecture Direction is Sound; Implementation Has Structural Gaps

The Weaver system's **architectural design is well-reasoned** for its stated goal of a local 24/7 automated trading system. The modulith pattern, event-driven decoupling, per-run isolation model, and plugin architecture are all appropriate choices. The documentation is remarkably thorough and self-aware.

However, there is a **fundamental gap between design intent and runtime reality** that is deeper than the existing reviews have fully articulated. The system has:

- **A well-designed event-driven architecture** that is **not actually wired end-to-end at runtime**
- **Correct module boundaries** with **broken cross-module communication**
- **Comprehensive test coverage (895 tests)** that mostly tests modules in isolation without validating the critical integration seams

The existing reviews (DESIGN_AUDIT.md, AUDIT_FINDINGS.md, DESIGN_REVIEW_PLAN.md) have identified most of the critical surface-level issues (SSE casing, missing start route, health path, mock order service). My fresh review **confirms all of those findings** and adds several **new structural concerns** that prior reviews have not fully surfaced.

### Key New Findings

| #    | Finding                                                                                                                                                                    | Severity | Category          |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------- |
| N-01 | **PostgresEventLog subscriber dispatch is entirely broken** — not just "pool missing" but architecturally impossible without pool                                          | P0       | Runtime wiring    |
| N-02 | **RunManager.\_start_live has zero error handling** — background clock failures leave ghost runs                                                                           | P0       | Reliability       |
| N-03 | **Fill history lost on persistence round-trip** — OrderState.fills not persisted                                                                                           | P1       | Data integrity    |
| N-04 | **AlpacaAdapter blocks the event loop** — sync SDK calls in async context                                                                                                  | P1       | Reliability       |
| N-05 | **StrategyAction uses stringly-typed tagged union** — no compile-time safety for action types                                                                              | P2       | Type safety       |
| N-06 | **SSE has no run_id filtering** despite architecture doc claiming it                                                                                                       | P1       | Contract drift    |
| N-07 | **InMemoryEventLog vs PostgresEventLog have different dispatch semantics** — subscribers fire synchronously on append in memory but only through LISTEN/NOTIFY in Postgres | P0       | Behavioral parity |
| N-08 | **BacktestResult stats are mostly zeros** — Sharpe, Sortino, max drawdown never computed                                                                                   | P2       | Completeness      |
| N-09 | **time_in_force default inconsistency** — schema says "day", VedaService handler says "gtc"                                                                                | P1       | Contract          |
| N-10 | **Frontend RunListResponse expects pagination fields backend doesn't return**                                                                                              | P1       | Contract          |

---

## 2. Architecture Direction Assessment

### 2.1 What is Correct and Well-Designed

**Modulith choice** — For a local, single-machine trading system, the modulith is the right call. The domain package separation (GLaDOS/Veda/Greta/Marvin/WallE/Events) provides clear ownership boundaries without the operational complexity of microservices.

**Per-run vs Singleton split** — The instance model is correctly designed:

- Per-run: GretaService, StrategyRunner, Clock — each run isolated
- Singleton: EventLog, BarRepository, DomainRouter, SSEBroadcaster — shared infrastructure with run_id tagging

This is the right architectural decomposition for multi-run concurrency.

**Event envelope design** — The Envelope dataclass with `id/corr_id/causation_id/trace_id/run_id` provides a solid identity chain. The namespace convention (`strategy.*`, `live.*`, `backtest.*`, `data.*`, etc.) maps cleanly to module boundaries.

**Plugin architecture** — AST-based strategy/adapter discovery is elegant and prevents import-time side effects. The STRATEGY_META/ADAPTER_META dict convention is simple and extensible.

**Dual credential design** — Supporting live and paper as simultaneous separate runs (not time-switching) is the right model for A/B testing and risk management.

**Clock abstraction** — The strategy pattern with BacktestClock (fast-forward) and RealtimeClock (wall-aligned) with a factory function is clean. Callback timeout protection (30s default) prevents stuck backtests.

**Frontend three-layer architecture** — The client.ts → domain modules → React Query hooks pattern is well-structured for testing and separation of concerns.

### 2.2 Architectural Concerns

**The "two architecture problem" is partially resolved but leaves echoes** — The legacy files (glados.py, veda.py, walle.py, etc.) were deleted in Batch 0. However, some design decisions still carry the scent of the old architecture:

1. `MockOrderService` persisting as a read-path dependency is a remnant of pre-VedaService thinking
2. The health check returning a hardcoded status without checking actual service health
3. The SSE route not using FastAPI Depends() — suggesting it was written before the DI refactor

**Event-driven design vs synchronous reality** — The architecture document describes an event-driven system with DomainRouter routing `strategy.*` → `live.*`/`backtest.*` events. In code, StrategyRunner emits `strategy.FetchWindow` events and GretaService subscribes to `backtest.FetchWindow` events. But **the DomainRouter is not wired into the app lifecycle**, so this routing never happens in production. The backtest integration test works only because the test wires the router manually.

---

## 3. Critical Issues (New Findings + Confirmed)

### 3.1 N-01: PostgresEventLog Subscriber Dispatch is Architecturally Broken (P0 — NEW)

**Previous reviews said**: "LISTEN/NOTIFY pool missing, needs wiring"
**What I found**: The problem is deeper than missing wiring — there's a **semantic gap** between the two EventLog implementations.

- `InMemoryEventLog.append()` **directly calls** all subscriber callbacks synchronously within the `append` method
- `PostgresEventLog.append()` **does not call** subscriber callbacks at all. It only issues a `pg_notify()`. Subscribers are only called through the `_listen_loop` → `_on_notify` → `_process_notification` chain, which requires an asyncpg pool.

This means:

1. All unit tests using `InMemoryEventLog` demonstrate event flow working
2. Any production/integration path using `PostgresEventLog` without a pool has **zero subscriber delivery**
3. Even with a pool, the delivery semantic differs: InMemory is synchronous/immediate, Postgres is async with DB round-trip

**Impact**: The SSE bridge, GretaService subscriptions, StrategyRunner subscriptions — anything that uses `subscribe()` or `subscribe_filtered()` — is non-functional with PostgresEventLog in the current setup.

**Recommendation**: This is the most critical architectural issue. Options:

- (a) Add direct subscriber dispatch in `PostgresEventLog.append()` (matching InMemory behavior) AND keep pg_notify for cross-process cases
- (b) Always provide an asyncpg pool — but this still leaves a latency/ordering difference
- (c) Create a `HybridEventLog` that dispatches locally and persists to DB

### 3.2 N-02: \_start_live Has Zero Error Handling (P0 — NEW)

`RunManager._start_backtest()` has proper try/except/finally:

- Catches exceptions → sets status to ERROR
- Finally block removes RunContext and sets stopped_at

`RunManager._start_live()` has **none of this**. The clock starts in a background task. If the clock or strategy throws an exception:

- Run status stays RUNNING forever
- RunContext is never cleaned up (memory leak)
- No error event is emitted
- The user sees a "running" indicator with no activity

This is a **long-running reliability violation** — the #1 stated design goal. Over days/weeks of operation, failed live runs will accumulate as zombie entries.

### 3.3 Confirmed Critical Issues from Prior Reviews

| ID   | Issue                                                         | Status    | My Assessment                                                                                                         |
| ---- | ------------------------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------- |
| C-01 | SSE event name casing mismatch (run.started vs run.Started)   | Confirmed | **Verified in code.** All 4 run event listeners in useSSE.ts are dead.                                                |
| C-02 | Missing POST /runs/{id}/start backend route                   | Confirmed | **Verified.** Frontend `startRun()` will always 404.                                                                  |
| C-03 | Health endpoint path mismatch (/healthz without /api/v1)      | Confirmed | **Verified in app.py.** Health router has no prefix, mounted bare. Frontend prepends /api/v1.                         |
| C-04 | Split order data sources (GET vs POST use different services) | Confirmed | **Verified in routes/orders.py.** list_orders and get_order use MockOrderService while create/cancel use VedaService. |

---

## 4. Significant Design Concerns (Newly Identified)

### 4.1 N-03: Fill History Lost on Persistence Round-Trip (P1)

`OrderState` has a `fills: list[Fill]` field tracking individual fill executions. However:

- `order_state_to_veda_order()` in persistence.py does **not** map fills to any DB column
- `veda_order_to_order_state()` creates OrderState with `fills=[]`

All fill history is lost when an order is saved and reloaded. After a service restart, the full order state is available but the fill-by-fill breakdown is gone. For a trading system, this is a significant data integrity issue — fills are audit-critical.

### 4.2 N-04: AlpacaAdapter Blocks Event Loop (P1)

`AlpacaAdapter.connect()` calls `self._trading_client.get_account()` which is the synchronous Alpaca SDK. This is inside an `async def connect()` method. In a single-worker asyncio application, this blocks the entire event loop during the SDK's HTTP roundtrip — potentially 1-5 seconds.

All other adapter methods (`submit_order`, `get_bars`, etc.) likely have the same issue since they delegate to the sync SDK.

**Fix**: Wrap all sync SDK calls in `asyncio.to_thread()`.

### 4.3 N-06: SSE Has No run_id Filtering (P1)

The architecture document (ARCHITECTURE.md §5) states:

> "SSEBroadcaster (filters by run_id for clients)"

The actual implementation in `sse_broadcaster.py` and `routes/sse.py` has **no run_id filtering**. All clients receive all events for all runs. This means:

- If two backtests run concurrently, a user watching one will see event notifications from both
- In a future multi-user scenario, all users would see all events

The SSE endpoint doesn't even accept a `run_id` query parameter.

### 4.4 N-07: InMemoryEventLog vs PostgresEventLog Behavioral Parity (P0)

Beyond the subscriber dispatch issue (N-01), there are additional behavioral differences:

| Behavior                      | InMemoryEventLog        | PostgresEventLog             |
| ----------------------------- | ----------------------- | ---------------------------- |
| Subscriber dispatch on append | Synchronous, in-process | Only via LISTEN/NOTIFY async |
| Offset semantics              | List index (0-based)    | DB sequence (1-based)        |
| subscribe() return            | Unsubscribe function    | Unsubscribe function         |
| subscribe_filtered()          | Works immediately       | Never fires without pool     |
| Thread safety                 | threading.Lock          | asyncpg/SQLAlchemy session   |

Tests using InMemoryEventLog pass because of direct dispatch. Switching to PostgresEventLog silently breaks the same flows. **The two implementations do not have behavioral parity**, which undermines the entire "test with in-memory, deploy with Postgres" strategy.

### 4.5 N-09: time_in_force Default Inconsistency (P1)

- `schemas.py` → `OrderCreate.time_in_force` defaults to `"day"`
- `veda_service.py` → `handle_place_order()` uses `.get("time_in_force", "gtc")`

If `time_in_force` is omitted in different code paths, orders will have different defaults depending on whether they come through REST or through the event handler. For a trading system, this kind of silent inconsistency is dangerous.

### 4.6 N-10: Frontend RunListResponse Pagination Fields (P1)

`haro/src/api/types.ts` defines `RunListResponse` with `page` and `page_size` fields. The backend `RunListResponse` schema also has these fields. However, the backend `list_runs()` handler:

1. Returns all runs (no actual pagination)
2. Sets `total=len(runs)` but uses hardcoded/default values for `page` and `page_size`

The frontend sends `page` and `page_size` query parameters that the backend completely ignores. This creates a false UI experience where pagination controls appear to work but actually do nothing.

---

## 5. Design-Code Alignment Matrix

### 5.1 Architecture Invariants vs Reality

| #   | Invariant               | Doc Claim                                | Code Reality                                                  | Verdict     |
| --- | ----------------------- | ---------------------------------------- | ------------------------------------------------------------- | ----------- |
| 1   | Single EventLog         | All components share one instance        | ✅ Single instance in app.py lifespan                         | **PASS**    |
| 2   | VedaService as entry    | Not OrderManager directly                | ⚠️ POST/DELETE use Veda; GET/list use Mock                    | **PARTIAL** |
| 3   | Session per request     | No long-lived DB sessions                | ✅ FastAPI DI provides per-request sessions                   | **PASS**    |
| 4   | SSE receives all events | EventLog → SSE always connected          | ❌ Subscription exists but callbacks never fire with Postgres | **FAIL**    |
| 5   | Graceful degradation    | Works without DB_URL                     | ✅ Conditional init in app.py                                 | **PASS**    |
| 6   | No module singletons    | Services via DI only                     | ✅ All services via FastAPI Depends()                         | **PASS**    |
| 7   | Multi-Run Support       | Per-run instances for Greta/Marvin/Clock | ✅ RunContext holds per-run instances                         | **PASS**    |
| 8   | Run Isolation           | Events carry run_id; consumers filter    | ✅ Events carry run_id; subscribe_filtered uses filter_fn     | **PASS**    |
| 9   | Plugin Architecture     | AST-based discovery                      | ✅ PluginStrategyLoader and PluginAdapterLoader both work     | **PASS**    |

**Result: 7/9 PASS, 1 PARTIAL, 1 FAIL**

The failed invariant (#4) is the most concerning because it's fundamental to the real-time observability pipeline.

### 5.2 Event Flow Completeness

| Flow                         | Designed Path                                                                               | Code Implementation                         | Gap                            |
| ---------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------ |
| Strategy tick → data request | `clock.Tick` → Runner.on_tick → `strategy.FetchWindow`                                      | ✅ Implemented in StrategyRunner            | None                           |
| Data request → response      | `strategy.FetchWindow` → DomainRouter → `backtest.FetchWindow` → Greta → `data.WindowReady` | ⚠️ Router exists but not wired in runtime   | **DomainRouter inactive**      |
| Data response → strategy     | `data.WindowReady` → Runner.\_on_window_ready → strategy.on_data                            | ✅ Subscription-based                       | None                           |
| Order intent → execution     | `strategy.PlaceRequest` → DomainRouter → `backtest.PlaceOrder` → Greta fill                 | ⚠️ Same DomainRouter gap                    | **DomainRouter inactive**      |
| Event → SSE → Frontend       | EventLog.append → subscriber → SSEBroadcaster.publish → SSE endpoint                        | ❌ PostgresEventLog never calls subscribers | **Subscriber dispatch broken** |
| SSE → UI update              | SSE event → useSSE listener → React Query invalidation                                      | ⚠️ Run events: casing mismatch              | **4 listeners dead**           |

### 5.3 REST API Contract Alignment

| Endpoint              | API.md Contract         | Backend Code                   | Frontend Code              | Alignment      |
| --------------------- | ----------------------- | ------------------------------ | -------------------------- | -------------- |
| GET /healthz          | ✅ Documented           | ✅ Implemented (no prefix)     | ❌ Calls /api/v1/healthz   | **BROKEN**     |
| POST /runs            | ✅ Documented           | ✅ Implemented                 | ✅ createRun()             | OK             |
| GET /runs             | ✅ Documented           | ✅ Implemented (no pagination) | ⚠️ Sends pagination params | **DEGRADED**   |
| GET /runs/{id}        | ✅ Documented           | ✅ Implemented                 | ✅ fetchRun()              | OK             |
| POST /runs/{id}/start | ✅ Documented as target | ❌ **NOT IMPLEMENTED**         | ✅ startRun()              | **BROKEN**     |
| POST /runs/{id}/stop  | ✅ Documented           | ✅ Implemented                 | ✅ stopRun()               | OK             |
| POST /orders          | ✅ Documented           | ✅ Via VedaService             | ❌ No createOrder() fn     | **PARTIAL**    |
| GET /orders           | ✅ Documented           | ⚠️ Via MockOrderService        | ✅ fetchOrders()           | **DEGRADED**   |
| GET /orders/{id}      | ✅ Documented           | ⚠️ Via MockOrderService        | ✅ fetchOrder()            | **DEGRADED**   |
| DELETE /orders/{id}   | ✅ Documented           | ✅ Via VedaService             | ✅ cancelOrder()           | OK             |
| GET /events/stream    | ✅ Documented           | ✅ Implemented                 | ✅ useSSE()                | OK (transport) |

---

## 6. Module-by-Module Deep Review

### 6.1 GLaDOS (Control Plane)

**Design intent**: Sole API boundary; run lifecycle; dependency wiring; clock; domain routing.

**Assessment**: The FastAPI application factory (`create_app`) and lifespan initialization are well-structured. The dependency injection system in `dependencies.py` correctly pulls from `app.state`. Route organization into separate modules (health, runs, orders, sse, candles) follows FastAPI best practices.

**Specific concerns**:

1. **RunManager receives incomplete dependencies** — Initialized with `event_log` only; `bar_repository` and `strategy_loader` are None. Any `start()` call will fail.
2. **DomainRouter is implemented but not wired** — Tests verify it in isolation, but `app.py` lifespan doesn't create or register it.
3. **MockOrderService coupling** — `dependencies.py` types the order service getter as `MockOrderService` rather than an abstract interface.
4. **Health check is a stub** — Returns "ok" without checking DB, event log, or adapter connectivity.

### 6.2 Events

**Design intent**: Immutable envelope; outbox + LISTEN/NOTIFY; consumer offsets; filtered subscriptions.

**Assessment**: The protocol design (Envelope, Subscription) is solid. The namespace/type system is well-organized. The offset tracking infrastructure (OffsetStore, EventConsumer, ConsumerOffset model) is properly designed for at-least-once delivery.

**Specific concerns**:

1. **Behavioral parity gap** (N-01, N-07) — InMemoryEventLog and PostgresEventLog have fundamentally different dispatch semantics.
2. **ALL_EVENT_TYPES is incomplete** — Missing OrderEvents.CREATED, RunEvents.CREATED, RunEvents.COMPLETED. If validation were enforced, these valid events would be rejected.
3. **EventConsumer is never used** — Well-designed but dead code. No consumer in the system uses offset-tracked consumption.
4. **Registry never populated** — Event schema validation fallback silently allows unregistered events to pass without validation.

### 6.3 Veda (Trading)

**Design intent**: Facade over adapter + order manager + repository; event emission; idempotency.

**Assessment**: The VedaService → OrderManager → ExchangeAdapter → OrderRepository layering is correct. The ExchangeAdapter protocol with 14 methods is comprehensive. The plugin loader (PluginAdapterLoader) with AST discovery is elegant.

**Specific concerns**:

1. **Fill history not persisted** (N-03) — `order_state_to_veda_order` drops `fills`. Critical gap for auditing.
2. **AlpacaAdapter blocks event loop** (N-04) — Sync SDK calls in async context.
3. **list_orders() has inconsistent source** — `run_id=None` returns from in-memory manager; `run_id=<value>` returns from repository. After restart, the in-memory state is empty.
4. **PositionTracker always shows zero P&L** — No market data feed updates positions. All `market_value`, `unrealized_pnl`, `unrealized_pnl_percent` are always `Decimal("0")`.
5. **handle_place_order constructs OrderIntent from untyped dict** — Passing raw strings for enum fields (`side`, `order_type`) may fail silently or throw unexpected errors at runtime.

### 6.4 Greta (Backtest)

**Design intent**: Per-run simulator; preloaded bar cache; fill simulation with slippage/commission; equity curve tracking.

**Assessment**: The per-run isolation model is correctly implemented. Bar cache preloading in `initialize()` is efficient. Fill simulation config (slippage models, commission, fill-at point) is well-designed.

**Specific concerns**:

1. **SimulatedFill.side is still str** — TODO from M5 never resolved. Should be `OrderSide` enum.
2. **asyncio.create_task fire-and-forget** — `_on_fetch_window` creates an untracked task. Exceptions could be silently swallowed.
3. **BacktestStats fields are mostly zeros** — Sharpe ratio, Sortino ratio, max drawdown are never computed. The fields exist but `greta_service.py` only computes basic stats (total/annualized return, win rate, profit factor).
4. **No memory bounds on bar cache** — For long backtest periods with many symbols, `_bar_cache` (dict of dict of dicts) could consume significant memory.

### 6.5 Marvin (Strategy)

**Design intent**: Mode-agnostic strategy execution; plugin discovery; event-based data flow.

**Assessment**: BaseStrategy → SMAStrategy hierarchy is clean. StrategyRunner correctly bridges strategy ↔ event system. PluginStrategyLoader with AST metadata extraction is well-implemented.

**Specific concerns**:

1. **StrategyAction stringly typed** (N-05) — `type: str` with convention values `"fetch_window"` and `"place_order"`. No compile-time validation.
2. **No mechanism to inform strategy of fills** — BaseStrategy tracks `_has_position` but there's no callback for fill events. Strategy state can drift from actual position state.
3. **asyncio.create_task fire-and-forget** — Same pattern as Greta.
4. **PlaceRequest doesn't generate client_order_id** — The DomainRouter or downstream handler must create one, but this isn't documented.

### 6.6 WallE (Persistence)

**Design intent**: Centralized writes; repository reads; all SQLAlchemy models in one place.

**Assessment**: The consolidation of all models into `walle/models.py` is correct and prevents metadata registration issues. BarRepository provides proper upsert support. Alembic migrations are properly set up.

**Specific concerns**:

1. **No Fills table** — Fill history is not persisted (related to N-03).
2. **No Runs table** — Run state is entirely in-memory (RunManager.\_runs dict). On restart, all run history is lost.
3. **Dual Bar definitions** — `walle/repositories/bar_repository.py` defines a `Bar` DTO with 7 fields while `veda/models.py` defines a `Bar` with 9 fields (including `trade_count`, `vwap`). Both are valid but poorly documented.

### 6.7 Haro (Frontend)

**Design intent**: React SPA consuming SSE + REST; TanStack Query for server state; Zustand for client state.

**Assessment**: The three-layer API architecture (client → domain → hooks) is well-designed. Query key factory pattern enables proper cache invalidation. SSE connection management with reconnection is implemented.

**Specific concerns**:

1. **4/7 SSE listeners are dead** (casing mismatch on run events)
2. **startRun() calls non-existent endpoint** (404)
3. **Pagination is a fiction** — Backend ignores pagination params
4. **No createOrder function** — Despite OrderCreate type existing and backend endpoint being available
5. **orders.Cancelled event not handled** — Cancel operations won't trigger toast/refresh

---

## 7. Cross-Cutting Invariant Verification

### 7.1 Money/Time Semantics

| Rule                            | Implementation                                                   | Verdict                |
| ------------------------------- | ---------------------------------------------------------------- | ---------------------- |
| All monetary values use Decimal | ✅ OrderIntent, Fill, OrderState, SimulatedFill all use Decimal  | **PASS**               |
| API transmits as strings        | ✅ Schemas use string representation for JSON safety             | **PASS**               |
| DB stores UTC                   | ✅ VedaOrder table uses DateTime (timezone-aware via SQLAlchemy) | **PASS**               |
| Frontend renders user timezone  | ⚠️ Frontend receives ISO strings, displays as-is                 | **NEEDS VERIFICATION** |
| Bar alignment is precise        | ✅ Clock utils calculate next bar boundary correctly             | **PASS**               |

### 7.2 Error Model

| Rule                                     | Implementation                                                    | Verdict           |
| ---------------------------------------- | ----------------------------------------------------------------- | ----------------- |
| {code, message, details, correlation_id} | ✅ ErrorResponse dataclass defined in protocol.py                 | **PASS** (schema) |
| Routes return structured errors          | ⚠️ FastAPI default error responses don't always use ErrorResponse | **PARTIAL**       |
| Exceptions map to HTTP status codes      | ✅ RunNotFoundError → 404, RunNotStartableError → 409, etc.       | **PASS**          |

### 7.3 Identity Chain

| Rule                                 | Implementation                              | Verdict  |
| ------------------------------------ | ------------------------------------------- | -------- |
| Events carry id/corr_id/causation_id | ✅ Envelope default_factory generates UUIDs | **PASS** |
| with_causation creates proper chain  | ✅ New id/ts, carries causation_id          | **PASS** |
| run_id isolation                     | ✅ All events include run_id                | **PASS** |

### 7.4 Idempotency

| Rule                      | Implementation                                                       | Verdict     |
| ------------------------- | -------------------------------------------------------------------- | ----------- |
| client_order_id on orders | ✅ OrderIntent.client_order_id, checked in VedaService               | **PASS**    |
| Duplicate order detection | ✅ OrderManager checks existing, MockAdapter checks client_order_map | **PASS**    |
| Event deduplication by id | ⚠️ Envelope.id generated, but no consumer-side dedup implemented     | **PARTIAL** |

---

## 8. Documentation Quality & Consistency

### 8.1 Document Charter System — Excellent

The document charter system (`Primary role / Authoritative for / Not authoritative for`) at the top of each document is a **genuinely good practice**. It prevents scope creep and makes ownership clear. I haven't seen this done better in most production codebases.

### 8.2 Cross-Document Consistency Issues

| Document A                         | Document B               | Issue                                                                                                                         |
| ---------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| ARCHITECTURE.md §5                 | sse_broadcaster.py       | "SSEBroadcaster filters by run_id" — no filtering implemented                                                                 |
| api.md §3.3 SSE Events             | useSSE.ts                | Table shows `run.Started` etc. but useSSE uses lowercase                                                                      |
| api.md §1 Contract Appendix        | routes/runs.py           | POST /runs/{id}/start documented as "target contract" but marked differently in different tables                              |
| events.md §2 Namespaces            | types.py ALL_EVENT_TYPES | Missing 3 events from validation set                                                                                          |
| veda.md §8 Env Vars                | config.py                | Env var names mismatch (fixed per L-04): `ALPACA_PAPER_KEY` vs `ALPACA_PAPER_API_KEY`                                         |
| deployment.md §4.1 Degraded Matrix | app.py                   | Matrix shows "run/order domain events delivered to SSE: ✅ best-effort" in DB mode, but subscriber dispatch is non-functional |
| TEST_COVERAGE.md §1                | Actual test count        | Says 808 backend, actual is 809 (+1) — minor                                                                                  |

### 8.3 Documentation Strengths

1. **DESIGN_REVIEW_PLAN.md** — The pyramid review structure (Layer 0→5) and "Layer Handoff Packet" concept are methodologically sound
2. **AUDIT_FINDINGS.md** — Thorough historical ledger with root cause analysis and fix tracking
3. **DESIGN_AUDIT.md** — Clean severity classification and verification matrix
4. **DEVELOPMENT.md** — TDD methodology clearly articulated
5. **Architecture sub-docs** (api.md, events.md, clock.md, veda.md) — Each well-scoped with code references

### 8.4 Documentation Gaps

1. **No Greta architecture doc** — Greta relies solely on the M4 milestone design doc. The ARCHITECTURE.md mentions "Promote to Living Architecture" as a principle but this hasn't been done for Greta.
2. **No Marvin architecture doc** — Same issue.
3. **No WallE architecture doc** — Schema decisions, repository patterns, and migration strategy are undocumented outside milestone docs.
4. **SSE event format** (M-06 in DESIGN_AUDIT.md) — The exact SSE wire format is undocumented.
5. **Error handling strategy** — No document describes the full error handling model (what exceptions exist, how they map to HTTP status codes, how errors propagate through the event pipeline).

---

## 9. Risk Assessment & Priority Ordering

### 9.1 P0 — Blocks Long-Running Reliability (Must Fix Before Any Production Use)

| #         | Risk                                                 | Impact                                            | Effort                                                 |
| --------- | ---------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------ |
| N-01/N-07 | EventLog subscriber dispatch broken in Postgres mode | SSE is dead; real-time UI is non-functional       | Medium — requires design decision + implementation     |
| N-02      | \_start_live has zero error handling                 | Ghost zombie runs accumulate; unrecoverable state | Low — add try/except/finally matching \_start_backtest |
| C-01      | SSE event casing mismatch                            | 4/7 SSE listeners dead                            | Trivial — one-line fix on frontend or backend          |
| C-02      | Missing start route                                  | Cannot start runs from UI                         | Low — add route + test                                 |
| C-03      | Health path mismatch                                 | Dashboard health indicator always shows error     | Trivial — add prefix or adjust frontend                |
| C-04      | Split order data source                              | Created orders invisible in list/get              | Medium — unify to VedaService                          |
| —         | DomainRouter not wired                               | Event-driven routing doesn't work at runtime      | Medium — wire in lifespan + integration test           |
| —         | RunManager missing deps                              | No runs can actually start                        | Low — pass deps in lifespan                            |

### 9.2 P1 — Significant Gaps Without Workaround

| #    | Risk                                           | Impact                                              | Effort                                |
| ---- | ---------------------------------------------- | --------------------------------------------------- | ------------------------------------- |
| N-03 | Fill history not persisted                     | Audit trail incomplete; post-restart fill data lost | Medium — add Fills table + migration  |
| N-04 | AlpacaAdapter blocks event loop                | Live trading freezes entire app during API calls    | Medium — wrap in asyncio.to_thread()  |
| N-06 | SSE no run_id filtering                        | All clients see all events                          | Low-Medium — add query param + filter |
| N-09 | time_in_force default inconsistency            | Silent different behavior depending on code path    | Trivial — unify defaults              |
| N-10 | Frontend pagination fields don't match backend | Pagination UI is broken/misleading                  | Low                                   |
| M-01 | ALL_EVENT_TYPES missing 3 events               | Validation would reject valid events                | Trivial                               |
| M-03 | orders.Cancelled not handled in SSE            | Cancel won't trigger UI refresh                     | Trivial                               |

### 9.3 P2 — Cleanup / Improvement

| #    | Risk                          | Impact                    |
| ---- | ----------------------------- | ------------------------- |
| N-05 | StrategyAction stringly typed | Poor developer ergonomics |
| N-08 | BacktestStats mostly zeros    | Misleading UI display     |
| M-04 | SimulatedFill.side is str     | Type safety gap           |
| M-07 | /runs/:runId route unused     | Dead route                |
| L-01 | 3 orphan files                | Code hygiene              |
| L-02 | 3 TODO/FIXME comments         | Tracking debt             |
| L-03 | Dual Bar types                | Documentation gap         |

---

## 10. Recommendations

### 10.1 Immediate (Before M8 Coding Starts)

1. **Design decision: EventLog subscriber dispatch model** — The most important architectural decision. I recommend Option (a) from N-01: add direct subscriber dispatch in PostgresEventLog.append() for in-process consumers, keeping pg_notify for future cross-process use. This maintains behavioral parity with InMemoryEventLog and fixes the SSE pipeline.

2. **Fix RunManager lifespan wiring** — Pass `bar_repository` and `strategy_loader` to RunManager in app.py lifespan. This is a precondition for any run being startable.

3. **Wire DomainRouter** — Without this, the entire event-driven routing design is dead code.

4. **Fix \_start_live error handling** — Copy the try/except/finally pattern from \_start_backtest. This is the simplest reliability fix with the highest impact.

### 10.2 M8 Phase 1 (Contract Alignment)

5. **Fix C-01 through C-04** — The four confirmed critical issues. All are well-understood with clear fixes.

6. **Unify time_in_force defaults** — Pick one default and enforce it at the boundary.

7. **Add integration test for full event pipeline** — Test that: append event → subscriber fires → SSEBroadcaster receives → SSE client gets the event. This single test would catch N-01/N-07.

### 10.3 M8 Phase 2 (Durability & Completeness)

8. **Add Fills table** — Persist fill history for audit trail.
9. **Add Runs table** — Persist run history for restart recovery.
10. **Wrap AlpacaAdapter in asyncio.to_thread()** — Prevent event loop blocking.
11. **Implement server-side pagination** — Or remove pagination UI.

### 10.4 Documentation Additions

12. **Create `docs/architecture/greta.md`** — Promote from milestone doc to living architecture.
13. **Create `docs/architecture/marvin.md`** — Same.
14. **Document SSE event wire format** — Exact bytes on the wire.
15. **Document error handling strategy** — Exception hierarchy, HTTP mapping, event pipeline error propagation.

### 10.5 Questions Requiring Design Decisions

Before coding starts, these design-level decisions should be locked:

| #   | Question                                                                     | Options                                                                                       | My Recommendation                                 |
| --- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| D-1 | How should PostgresEventLog dispatch to in-process subscribers?              | (a) Direct dispatch in append + pg_notify (b) Always require pool (c) Hybrid EventLog wrapper | **(a)** for simplicity and parity                 |
| D-2 | Should runs be persisted to database?                                        | (a) In-memory only (current) (b) Add runs table                                               | **(b)** for restart recovery                      |
| D-3 | Should fills be persisted separately?                                        | (a) Embedded in serialized order (b) Separate fills table                                     | **(b)** for queryability and audit                |
| D-4 | Should DomainRouter be a standalone wired component or inline in RunManager? | (a) Separate wired singleton (b) Integrated into RunManager per-run startup                   | **(a)** for consistency with architecture doc     |
| D-5 | Should SSE support run_id filtering?                                         | (a) Yes, via query param (b) No, client-side filter                                           | **(a)** to reduce UI noise in multi-run scenarios |

---

## 11. Comparison with Existing Reviews

### 11.1 Agreement with Prior Reviews

I **fully agree** with the following findings from the existing review documents:

- All 4 critical findings (C-01 through C-04) in DESIGN_AUDIT.md
- All 7 medium findings (M-01 through M-07) in DESIGN_AUDIT.md
- The "two architecture problem" root cause analysis in AUDIT_FINDINGS.md
- The package A/B/C decision framework in DESIGN_REVIEW_PLAN.md §9
- The chosen options: A2 (lifecycle-first), B2 (dedicated orchestration), C1 (hard unify)

### 11.2 Where My Review Adds Depth

| Area                       | Prior Reviews Said                            | My Fresh Review Found                                                                                                                                                                                                      |
| -------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EventLog/SSE wiring        | "LISTEN/NOTIFY pool missing"                  | The problem is deeper: PostgresEventLog.append() has fundamentally different dispatch semantics than InMemoryEventLog. This isn't just a missing pool — it's a behavioral parity issue that invalidates the test strategy. |
| \_start_live reliability   | Not explicitly called out                     | Zero error handling for background clock failures — directly violates the 24/7 reliability goal                                                                                                                            |
| Fill persistence           | Not mentioned                                 | OrderState.fills lost on persistence round-trip — audit-critical gap                                                                                                                                                       |
| Event loop blocking        | Not mentioned                                 | AlpacaAdapter sync SDK calls block the entire event loop                                                                                                                                                                   |
| SSE run_id filtering       | Mentioned briefly in ARCHITECTURE.md §5 claim | Architecture doc explicitly claims this exists but it doesn't — active documentation lie                                                                                                                                   |
| EventLog behavioral parity | Not mentioned                                 | InMemoryEventLog and PostgresEventLog have different dispatch semantics, undermining the test-with-mock strategy                                                                                                           |

### 11.3 Where Prior Reviews Were Stronger

The existing reviews have better:

- **Milestone-level tracking** — The fix scheduling into M8 phases is well-organized
- **Historical context** — AUDIT_FINDINGS.md preserves the full migration story
- **Process governance** — The DESIGN_REVIEW_PLAN.md pyramid structure is methodologically excellent

### 11.4 Disagreements or Different Emphasis

1. **Prior reviews rate Layer 0-1 as "Satisfied"** — I would rate it "Satisfied with one caveat": the architecture doc contains a factual claim about SSE run_id filtering that is false. This isn't a code bug — it's a documentation accuracy issue that could mislead future developers.

2. **Prior reviews discuss DomainRouter wiring as a P0 with "discussion required"** — I agree on priority but believe this should be a straightforward decision, not requiring extensive discussion. The architecture doc describes the intended behavior clearly; the only question is whether to implement it as a standalone wired singleton (matching the doc) or inline into RunManager.

3. **Package B option selection (B2 — Dedicated orchestration component)** — I lean more toward **B1 (direct app-lifespan wiring)** as the simpler approach for an MVP. A dedicated orchestrator adds abstraction complexity that may not be justified until more consumers exist. The current system has exactly 3 runtime subscriptions (SSE, Greta, StrategyRunner). A centralized orchestrator makes more sense at 10+ subscriptions.

---

## Appendix A: Files Verified During Review

### Backend Source (directly read and analyzed)

- `src/config.py`, `src/glados/app.py`, `src/glados/dependencies.py`, `src/glados/schemas.py`
- `src/glados/sse_broadcaster.py`, `src/glados/routes/*.py` (health, runs, orders, sse)
- `src/glados/services/run_manager.py`
- `src/events/protocol.py`, `src/events/types.py`, `src/events/log.py`, `src/events/offsets.py`
- `src/veda/veda_service.py`, `src/veda/interfaces.py`, `src/veda/models.py`, `src/veda/persistence.py`
- `src/veda/adapters/alpaca_adapter.py`, `src/veda/adapters/mock_adapter.py`
- `src/marvin/strategy_runner.py`, `src/marvin/base_strategy.py`
- `src/greta/greta_service.py`, `src/greta/models.py`
- `src/walle/models.py`

### Frontend Source (directly read and analyzed)

- `haro/src/hooks/useSSE.ts`, `haro/src/hooks/useRuns.ts`
- `haro/src/api/client.ts`, `haro/src/api/runs.ts`, `haro/src/api/orders.ts`, `haro/src/api/health.ts`, `haro/src/api/types.ts`
- `haro/src/App.tsx`, `haro/vite.config.ts`

### Documentation (all fully read)

- `docs/ARCHITECTURE.md`, `docs/DESIGN_AUDIT.md`, `docs/AUDIT_FINDINGS.md`
- `docs/DESIGN_REVIEW_PLAN.md`, `docs/MILESTONE_PLAN.md`, `docs/DEVELOPMENT.md`, `docs/TEST_COVERAGE.md`
- `docs/architecture/api.md`, `docs/architecture/events.md`, `docs/architecture/clock.md`
- `docs/architecture/veda.md`, `docs/architecture/config.md`, `docs/architecture/deployment.md`
- `docs/architecture/roadmap.md`

---

_Generated: 2026-02-16_

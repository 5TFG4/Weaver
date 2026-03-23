# Weaver Test Coverage Report

> **Document Charter**  
> **Primary role**: current test coverage snapshot and gap analysis.  
> **Authoritative for**: latest test counts and coverage trend statements (with snapshot date).  
> **Not authoritative for**: milestone planning details (use `MILESTONE_PLAN.md`).

> Comprehensive analysis of test depth, breadth, and business logic coverage.

**Last Updated**: 2026-03-24 · **Total Tests**: 1136 passed (945 backend unit + 50 integration + 108 frontend + 33 E2E)  
**M8 Status**: ✅ Complete (Fixes & Improvements) · **M9 Status**: ✅ Complete (CI Deployment) · **M10 Status**: ✅ Complete (E2E Tests) · **M11 Status**: ✅ Complete (Runtime Robustness)

---

## 1. Executive Summary

| Metric             | Value                        | Status       |
| ------------------ | ---------------------------- | ------------ |
| Total Tests        | 1136 (945 + 50 + 108 + 33)   | ✅           |
| Test Files         | 80+                          | ✅           |
| Total Assertions   | ~2,000+                      | ✅           |
| Unit Tests         | majority                     | ✅           |
| Integration Tests  | targeted core flows + Alpaca | ✅           |
| E2E Tests          | 33 (Playwright, 0 xfail)     | ✅ M10       |
| Alpaca Integration | 6 (paper API)                | ✅ CI Audit  |
| Frontend Tests     | 108 (Vitest)                 | ✅ 94.8% cov |
| Coverage Gate      | 89.73% (threshold: 80%)      | ✅           |
| Mock Usages        | high (design-intent)         | -            |

**Overall Assessment**: Test breadth is strong. CI audit Waves 1–4 complete: fixed 2 production bugs (submit_order/list_orders SDK contract), added Alpaca integration tests (6), E2E order lifecycle tests (10), frontend coverage reporting, and hardened unit test mocks with autospec. Post-audit CI hardening: Actions upgraded to Node.js 24, npm vulnerabilities patched, workflow permissions locked, coverage artifacts cleaned. M11 (Runtime Robustness) added 47 tests: backtest async race fix, strategy error propagation, concurrent run safety, frontend error hooks, and Alpaca credential skip logic. All 5 CI workflows green.

---

## 2. Coverage by Component

### 2.1 Test Distribution

| Component              | Files | Tests | Classes | % of Total |
| ---------------------- | ----- | ----- | ------- | ---------- |
| **Veda (Trading)**     | 13    | 275   | 75      | 34.1%      |
| **Clock (Timing)**     | 4     | 93    | 22      | 11.5%      |
| **GLaDOS Core**        | 8     | 104   | 25      | 9.2%       |
| **Marvin (Strategy)**  | 7     | 79    | 19      | 7.0%       |
| **Greta (Simulation)** | 5     | 61    | 14      | 5.4%       |
| **Infrastructure**     | 4     | 51    | 18      | 6.3%       |
| **Events**             | 4     | 45    | 8       | 5.6%       |
| **Integration**        | 4     | 44    | 12      | 5.5%       |
| **GLaDOS Services**    | 5     | 66    | 20      | 5.8%       |
| **GLaDOS Routes**      | 5     | 33    | 9       | 4.1%       |
| **WALL-E (Database)**  | 2     | 25    | 6       | 3.0%       |
| **Haro (Frontend)**    | 17    | 108   | 26      | 9.5%       |

### 2.2 Top Test Files by Count

| File                        | Tests | Assertions | Component      |
| --------------------------- | ----- | ---------- | -------------- |
| `test_models.py` (veda)     | 35    | 82         | Veda           |
| `test_backtest.py`          | 33    | 48         | Clock          |
| `test_mock_adapter.py`      | 27    | 63         | Veda           |
| `test_order_manager.py`     | 27    | 38         | Veda           |
| `test_exceptions.py`        | 25    | 27         | Veda           |
| `test_config.py`            | 24    | 65         | Infrastructure |
| `test_persistence.py`       | 24    | 35         | Veda           |
| `test_realtime.py`          | 24    | 31         | Clock          |
| `test_alpaca_connection.py` | 23    | 27         | Veda           |
| `test_adapter_loader.py`    | 22    | 41         | Veda           |

---

## 3. Test Depth Analysis

### 3.1 Test Pyramid

```
                    ┌─────────────┐
                    │    E2E      │  33 tests (3%)
                    │ (Playwright)│  Containerized, Chromium, 0 xfail
                    ├─────────────┤
                    │ Integration │  50 tests (5%)
                    │   Tests     │  DB, Events, Alpaca API
                ┌───┴─────────────┴───┐
                │     Unit Tests      │  902 tests (92%)
                │  Isolated, fast,    │  Avg 0.02s/test
                │  comprehensive      │
                └─────────────────────┘
```

### 3.2 Test Types

| Type             | Count | Description                                    | Quality   |
| ---------------- | ----- | ---------------------------------------------- | --------- |
| **Unit**         | 945   | Isolated function/class tests                  | ★★★★★     |
| **Integration**  | 50    | Multi-component + real DB/API                  | ★★★★☆     |
| **E2E**          | 33    | Full browser→API→DB flow (Playwright, 0 xfail) | ★★★★☆     |
| **Alpaca Integ** | 6     | Real paper trading API                         | ★★★★☆     |
| **Performance**  | 0     | Load/stress testing                            | ❌ Future |

### 3.3 E2E & Integration Coverage by Component

This matrix shows how E2E and integration tests cover each system component, complementing the unit test layer.

| Component                                     |                  E2E Tests                  |          Integration Tests           |       Unit Tests        |  Overall  |
| --------------------------------------------- | :-----------------------------------------: | :----------------------------------: | :---------------------: | :-------: |
| **GLaDOS** (API routes, services, RunManager) |  ✅ 8 tests (backtest/paper flows, health)  |   ✅ 5 tests (backtest lifecycle)    |         ✅ 80+          | Excellent |
| **Haro** (Frontend UI, routing, pages)        |  ✅ 22 tests (nav, forms, tables, modals)   |                  —                   |     ✅ 104 (Vitest)     | Excellent |
| **Veda** (Trading, orders, Alpaca adapter)    |         ✅ 2 tests (order display)          |    ✅ 6 tests (Alpaca paper API)     |         ✅ 80+          | Excellent |
| **Clock** (Backtest, Realtime)                | ✅ 3 tests (backtest completes, paper runs) |      ✅ 2 tests (backtest flow)      |         ✅ 30+          | Excellent |
| **Marvin** (Strategy runner, plugin loader)   |     ✅ 1 test (invalid strategy error)      |     ✅ 1 test (strategy actions)     |         ✅ 40+          |   Good    |
| **Greta** (Fill simulator, order processing)  | ✅ 3 tests (pass — async race fixed M11-1)  |   ✅ 5 tests (backtest order flow)   |         ✅ 35+          | Excellent |
| **WallE** (Database, bar repository, models)  |     ✅ 3 tests (persistence via flows)      |   ✅ 13 tests (bar CRUD, real DB)    |         ✅ 25+          | Excellent |
| **Events** (EventLog, offsets, subscriptions) |         ✅ 1 test (event delivery)          | ✅ 15 tests (Postgres log + offsets) |         ✅ 15+          | Excellent |
| **SSE** (Server-sent events, broadcaster)     |  ✅ 4 tests (connect, deliver, reconnect)   |                  —                   | ⚠️ 5 (broadcaster only) |   Good    |

#### E2E Test Breakdown (33 tests across 6 files)

| Test File                  | Tests | Components Exercised                          |
| -------------------------- | :---: | --------------------------------------------- |
| `test_backtest_flow.py`    |   8   | GLaDOS, Haro, Clock, Greta, WallE             |
| `test_paper_flow.py`       |   5   | GLaDOS, Haro, Clock, Marvin                   |
| `test_navigation.py`       |   6   | Haro (routing, pages, sidebar)                |
| `test_orders.py`           |   2   | Haro, GLaDOS, Veda                            |
| `test_orders_lifecycle.py` |   8   | Greta, Events, Marvin, GLaDOS, Haro (0 xfail) |
| `test_sse.py`              |   4   | SSE, Haro, GLaDOS                             |

#### Integration Test Breakdown (50 tests across 5 files)

| Test File                | Tests | Components Exercised                        |
| ------------------------ | :---: | ------------------------------------------- |
| `test_bar_repository.py` |  15   | WallE (real PostgreSQL)                     |
| `test_event_log.py`      |  10   | Events (PostgresEventLog + concurrency)     |
| `test_offset_store.py`   |  14   | Events (PostgresOffsetStore + concurrency)  |
| `test_backtest_flow.py`  |   5   | GLaDOS, Clock, WallE, Marvin, Greta, Events |
| `test_alpaca_paper.py`   |   6   | Veda (real Alpaca paper API)                |

#### Coverage Gaps (E2E/Integration)

| Gap                   | Description                                           | Impact                                                  | Priority |
| --------------------- | ----------------------------------------------------- | ------------------------------------------------------- | -------- |
| SSE integration tests | No isolated SSE integration tests (only E2E)          | Reconnect edge cases untested in isolation              | Low      |
| Multi-symbol backtest | Only single-symbol tested in integration              | Complex scenarios untested                              | Low      |
| Marvin E2E depth      | Only 1 E2E test touches strategy loading (error path) | Happy-path strategy execution covered via backtest flow | Low      |

---

## 4. Business Logic Coverage

### 4.1 Order Lifecycle ✅ COMPLETE

| Flow                                             | Status | Tests                     |
| ------------------------------------------------ | ------ | ------------------------- |
| OrderIntent → Order creation                     | ✅     | `test_order_manager.py`   |
| Status transitions (PENDING→ACCEPTED→FILLED)     | ✅     | `test_models.py`          |
| Order persistence to database                    | ✅     | `test_persistence.py`     |
| Order cancellation                               | ✅     | `test_order_manager.py`   |
| Idempotent submission                            | ✅     | `test_live_order_flow.py` |
| Event emission (orders.Created, orders.Rejected) | ✅     | `test_live_order_flow.py` |

### 4.2 Backtest Flow ✅ COMPLETE

| Flow                            | Status | Tests                          |
| ------------------------------- | ------ | ------------------------------ |
| Create backtest Run             | ✅     | `test_run_manager.py`          |
| BacktestClock time progression  | ✅     | `test_backtest.py`             |
| Strategy receives ClockTick     | ✅     | `test_strategy_runner.py`      |
| Fill simulation                 | ✅     | `test_fill_simulator.py`       |
| Run completion state transition | ✅     | `test_run_manager_backtest.py` |
| Multi-symbol backtest           | ⚠️     | Basic coverage                 |

### 4.3 Live/Paper Trading ✅ COMPLETE

| Flow                         | Status | Tests                                                 |
| ---------------------------- | ------ | ----------------------------------------------------- |
| RealtimeClock selection      | ✅     | `test_run_mode_integration.py`                        |
| Alpaca connection management | ✅     | `test_alpaca_connection.py`                           |
| Order routing to VedaService | ✅     | `test_order_routing.py`                               |
| Live run stays RUNNING       | ✅     | `test_run_mode_integration.py`                        |
| Actual order submission      | ✅     | `test_alpaca_paper.py` (integration, real Alpaca API) |
| Order cancellation           | ✅     | `test_alpaca_paper.py` (integration)                  |
| Order listing                | ✅     | `test_alpaca_paper.py` (integration)                  |
| WebSocket real-time data     | ❌     | Not implemented                                       |

### 4.4 Strategy System ✅ COMPLETE

| Flow                            | Status | Tests                            |
| ------------------------------- | ------ | -------------------------------- |
| Strategy registration & loading | ✅     | `test_plugin_loader.py`          |
| Plugin-based discovery          | ✅     | `test_plugin_loader.py`          |
| SMA strategy logic              | ✅     | `test_sma_strategy.py`           |
| Strategy tick → action flow     | ✅     | `test_strategy_runner.py`        |
| WindowReady event flow          | ✅     | `test_strategy_runner_events.py` |
| Hot config reload               | ⚠️     | Not tested                       |

### 4.5 Event System ✅ COMPLETE

| Flow                   | Status | Tests                             |
| ---------------------- | ------ | --------------------------------- |
| Event append           | ✅     | `test_event_log.py`               |
| Event subscription     | ✅     | `test_subscription.py`            |
| Filtered subscription  | ✅     | `test_subscription.py`            |
| Offset management      | ✅     | `test_offset_store.py`            |
| PostgreSQL persistence | ✅     | `test_event_log.py` (integration) |
| Consumer replay        | ⚠️     | Basic coverage                    |

### 4.6 API Layer ⚠️ PARTIAL

| Flow                          | Status | Tests                            |
| ----------------------------- | ------ | -------------------------------- |
| REST CRUD endpoints           | ✅     | `test_runs.py`, `test_orders.py` |
| Request validation (Pydantic) | ✅     | `test_schemas.py`                |
| Error responses (4xx/5xx)     | ✅     | Route tests                      |
| SSE real-time push            | ✅     | `test_sse.py`                    |
| Authentication/Authorization  | ❌     | Not implemented                  |
| Rate limiting                 | ❌     | Not implemented                  |

---

## 5. Edge Case Coverage

### 5.1 Covered Edge Cases ✅

| Category              | Edge Case                  | Location                    |
| --------------------- | -------------------------- | --------------------------- |
| **Null/Empty**        | Empty lists, None values   | Most components             |
| **Concurrency**       | Concurrent subscriptions   | EventLog tests              |
| **Idempotency**       | Duplicate order submission | `test_live_order_flow.py`   |
| **Idempotency**       | Double stop on run         | `test_run_manager.py`       |
| **Error Handling**    | Adapter connection failure | `test_alpaca_connection.py` |
| **Timeouts**          | Clock callback timeout     | `test_backtest.py`          |
| **Resource Cleanup**  | Clock stop, DB disconnect  | Various                     |
| **State Transitions** | Invalid state changes      | `test_models.py`            |

### 5.2 Partially Covered ⚠️

| Category      | Edge Case                  | Notes                |
| ------------- | -------------------------- | -------------------- |
| **High Load** | Many concurrent operations | No stress tests      |
| **Network**   | Connection recovery        | Basic reconnect only |
| **Data**      | Large datasets             | Not tested           |

### 5.3 Not Covered ❌

| Category     | Edge Case                | Priority   |
| ------------ | ------------------------ | ---------- |
| **Database** | DB failure recovery      | Medium     |
| **Network**  | Partial message delivery | Low        |
| **Security** | Auth bypass attempts     | High (M10) |

---

## 6. Test Quality Metrics

### 6.1 Assertion Density

| Component      | Tests | Assertions | Avg/Test |
| -------------- | ----- | ---------- | -------- |
| Veda           | 275   | 414        | 1.5      |
| Clock          | 93    | 99         | 1.1      |
| Infrastructure | 51    | 85         | 1.7      |
| Greta          | 56    | 71         | 1.3      |
| Events         | 45    | 58         | 1.3      |
| **Average**    | -     | -          | **1.4**  |

### 6.2 Mock Usage

- **Total Mock Usages**: 499
- **Mock/Test Ratio**: 0.62
- **Pattern**: Heavy use of AsyncMock for adapter tests, MagicMock for service dependencies

### 6.3 Async Coverage

| Type        | Count | Percentage |
| ----------- | ----- | ---------- |
| Async tests | 310   | 38%        |
| Sync tests  | 496   | 62%        |

_High async coverage in: Veda (adapters), Events (subscriptions), Integration tests_

---

## 7. Coverage Gaps & Recommendations

### 7.1 Critical Gaps (Priority: High)

| Gap                   | Impact                        | Recommendation              | Status                |
| --------------------- | ----------------------------- | --------------------------- | --------------------- |
| **E2E Tests**         | Cannot verify full user flows | Add Playwright tests        | ✅ M10 (33 tests)     |
| **Auth Tests**        | Security vulnerability        | Add auth middleware + tests | Backlog               |
| **Real Alpaca Tests** | Unknown production behavior   | Add sandbox integration     | ✅ CI Audit (6 tests) |

### 7.2 Medium Priority Gaps

| Gap                     | Impact                     | Recommendation     | Target |
| ----------------------- | -------------------------- | ------------------ | ------ |
| WebSocket data stream   | Live trading incomplete    | Implement + test   | M7     |
| Multi-symbol concurrent | Limited backtest scenarios | Add parallel tests | M8     |
| Error recovery          | Unknown failure modes      | Add chaos tests    | Future |

### 7.3 Low Priority Gaps

| Gap               | Impact                  | Recommendation |
| ----------------- | ----------------------- | -------------- |
| Performance tests | Unknown limits          | Add after MVP  |
| Load tests        | Scalability unknown     | Add after MVP  |
| Mutation testing  | Test quality validation | Nice to have   |

---

## 8. Test Infrastructure

### 8.1 Fixtures

| Fixture File             | Purpose                                    |
| ------------------------ | ------------------------------------------ |
| `fixtures/clock.py`      | ControllableClock for deterministic timing |
| `fixtures/database.py`   | Test database setup/teardown               |
| `fixtures/event_log.py`  | InMemoryEventLog for fast tests            |
| `fixtures/http.py`       | TestClient setup                           |
| `fixtures/strategies.py` | Mock strategy implementations              |

### 8.2 Factories

| Factory File          | Purpose                        |
| --------------------- | ------------------------------ |
| `factories/events.py` | Event/Envelope creation        |
| `factories/orders.py` | Order/OrderIntent creation     |
| `factories/runs.py`   | Run creation, RunManager setup |

### 8.3 Test Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
timeout = 30
testpaths = ["tests"]
```

---

## 9. Historical Progress

| Milestone            | Tests Added | Total | Date    |
| -------------------- | ----------- | ----- | ------- |
| M1 Foundation        | ~50         | 50    | 2026-01 |
| M2 GLaDOS API        | ~80         | 130   | 2026-01 |
| M3 Veda              | ~150        | 280   | 2026-01 |
| M3.5 Integration     | ~100        | 380   | 2026-01 |
| M4 Greta             | ~200        | 580   | 2026-01 |
| M5 Marvin            | ~74         | 654   | 2026-02 |
| M5 Quality           | ~51         | 705   | 2026-02 |
| M6 Live Trading      | ~101        | 806   | 2026-02 |
| M7 Frontend (M7-0→5) | ~63         | 871   | 2026-02 |
| M7 SSE (M7-6)        | ~23         | 894   | 2026-02 |
| M8 Fixes & Polish    | ~138        | 1032  | 2026-03 |
| M10 E2E Tests        | 23          | 1055  | 2026-03 |
| CI Audit Waves 1–4   | 16          | 1071  | 2026-03 |
| CI Audit (frontend)  | 14          | 1085  | 2026-03 |
| CI Hardening         | 4           | 1089  | 2026-03 |
| M11 Runtime Robust.  | 47          | 1136  | 2026-03 |

---

## 10. Next Steps

### M7 (Frontend) ✅ COMPLETE

- [x] Add API client tests (runs, orders, health)
- [x] Add component tests (Layout, StatCard, StatusBadge, ActivityFeed, OrderStatusBadge, OrderTable)
- [x] Add page tests (Dashboard, RunsPage, OrdersPage)
- [x] Add hook tests (useRuns)
- [x] Add SSE integration tests with real frontend (M7-6) ✅ 23 tests
- [x] Add notification store tests (M7-6) ✅ 6 tests
- [x] Add Toast + ConnectionStatus component tests (M7-6) ✅ 8 tests
- [x] Add useSSE hook tests (M7-6) ✅ 9 tests

### M10 (E2E Tests) ✅ COMPLETE

- [x] E2E infrastructure: test_runner container, docker-compose.e2e.yml
- [x] Navigation tests (6): page loads, routing, sidebar nav, 404
- [x] Backtest flow tests (8): create via UI/API, start→completed, deep-link, dashboard stats
- [x] Paper flow tests (5): create, start→running, active runs, stop→stopped, error state
- [x] Orders tests (2): mock data rendering, detail modal
- [x] Orders lifecycle tests (8): event payloads, pagination, detail modal (3 xfail due to async race B-3)
- [x] SSE tests (4): connection status, real-time run updates, reconnect
- [x] All 33 E2E tests passing in containerized Playwright/Chromium

### CI Audit (Post-M10) ✅ COMPLETE

- [x] Wave 1: Alpaca integration tests (6) + dedicated CI workflow
- [x] Wave 2: E2E order lifecycle tests (10) + SSE tests
- [x] Wave 3: Frontend coverage reporting (vitest → vitest --coverage)
- [x] Wave 4: Production bug fixes (submit_order/list_orders SDK contract), CI path fix, mock hardening (autospec)
- [x] Post-Wave 4: Actions Node.js 24 upgrade, npm vulnerability patches, permissions lockdown, coverage cleanup

### Future

- [ ] Add authentication tests
- [ ] Add error boundary tests
- [ ] Add performance baseline tests
- [ ] Add SSE integration tests (isolated, not just E2E)

---

_This document is auto-generated and should be updated after each milestone completion._

---

## 11. Frontend Testing Patterns (M7)

> Added after M7 completion. Documents frontend-specific testing strategies,
> infrastructure, and patterns for future reference.

### 11.1 Test Stack

| Tool                  | Purpose                      | Version    |
| --------------------- | ---------------------------- | ---------- |
| Vitest                | Test runner & assertions     | 4.0.18     |
| React Testing Library | Component rendering          | 16.3.0     |
| MSW                   | API mocking (service worker) | 2.12.8     |
| jsdom                 | Browser environment          | via Vitest |
| @vitest/coverage-v8   | Coverage reporting           | 4.0.18     |

### 11.2 MSW (Mock Service Worker)

MSW intercepts `fetch()` calls at the network level, providing realistic API mocking
without patching `fetch` manually. All 10 API endpoints have default happy-path handlers
in `tests/mocks/handlers.ts`.

**Default handlers** (always active):

```
GET  /api/v1/runs          → { runs: [...], total: N }
GET  /api/v1/runs/:id      → single run
POST /api/v1/runs          → created run
POST /api/v1/runs/:id/stop → stopped run
GET  /api/v1/orders        → { orders: [...], total: N }
GET  /api/v1/orders/:id    → single order
DELETE /api/v1/orders/:id  → 204 No Content
GET  /healthz              → { status: "ok", ... }
```

**Per-test overrides**: Use `server.use(http.get(...))` to override for
error scenarios. MSW resets after each test via `server.resetHandlers()`.

### 11.3 EventSource Mocking

JSDOM doesn't provide `EventSource`. Two-tier approach:

1. **Global no-op** (`tests/setup.ts`): Prevents crash when components render `useSSE()`.
2. **Rich mock** (`tests/unit/hooks/useSSE.test.tsx`): Full `MockEventSource` class with
   `simulateOpen()`, `simulateError()`, `simulateEvent(type, data)` for controlled SSE testing.

### 11.4 Custom Render

`tests/utils.tsx` exports a `render()` that wraps every component in required providers:

```tsx
function render(ui: ReactElement, options?: RenderOptions) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    ),
    ...options,
  });
}
```

This ensures all tests get TanStack Query + Router context without boilerplate.

### 11.5 Zustand Store Testing

Zustand stores are plain JS objects — no React rendering needed:

```typescript
const { addNotification, removeNotification } = useNotificationStore.getState();
act(() => addNotification({ type: "success", message: "Test" }));
expect(useNotificationStore.getState().notifications).toHaveLength(1);
```

Use `vi.useFakeTimers()` to test auto-dismiss behavior (5s timeout).

### 11.6 Frontend Test File Map

| Test File                              | Count  | What It Tests                                          |
| -------------------------------------- | ------ | ------------------------------------------------------ |
| `App.test.tsx`                         | 4      | Route rendering, 404, navigation                       |
| `api/runs.test.ts`                     | 4      | fetchRuns, fetchRun, createRun, startRun               |
| `api/orders.test.ts`                   | 3      | fetchOrders, fetchOrder, cancelOrder                   |
| `hooks/useRuns.test.tsx`               | 2      | useRuns query, useCreateRun mutation                   |
| `hooks/useSSE.test.tsx`                | 9      | Connection, reconnection, 7 event types                |
| `components/Layout.test.tsx`           | 4      | Header, sidebar, nav links, active state               |
| `components/StatCard.test.tsx`         | 4      | Label, value, icon, trend display                      |
| `components/ActivityFeed.test.tsx`     | 4      | Rendering, time-ago, empty state, linking              |
| `components/OrderTable.test.tsx`       | 6      | Row rendering, click handler, empty state              |
| `components/OrderStatusBadge.test.tsx` | 4      | Status colors, side badges                             |
| `components/Toast.test.tsx`            | 8      | Notifications, dismiss, auto-remove, connection status |
| `pages/Dashboard.test.tsx`             | 7      | Stat cards, activity feed, loading, error              |
| `pages/RunsPage.test.tsx`              | 14     | CRUD operations, create form, stop action              |
| `pages/OrdersPage.test.tsx`            | 7      | Filter, table, detail modal, run_id param              |
| `stores/notificationStore.test.ts`     | 6      | Add, remove, clearAll, auto-dismiss, IDs               |
| **Total**                              | **86** |                                                        |

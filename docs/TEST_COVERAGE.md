# Weaver Test Coverage Report

> **Document Charter**  
> **Primary role**: current test coverage snapshot and gap analysis.  
> **Authoritative for**: latest test counts and coverage trend statements (with snapshot date).  
> **Not authoritative for**: milestone planning details (use `MILESTONE_PLAN.md`).

> Comprehensive analysis of test depth, breadth, and business logic coverage.

**Last Updated**: 2026-02-26 · **Total Tests**: 933 backend + 90 frontend = 1023  
**M8 Status**: ✅ Complete (Fixes & Improvements) · **M9 Status**: ⏳ Planned (E2E Tests)

---

## 1. Executive Summary

| Metric            | Value                    | Status        |
| ----------------- | ------------------------ | ------------- |
| Total Tests       | 1023 (933 + 90)          | ✅            |
| Test Files        | 73+                      | ✅            |
| Total Assertions  | ~1,700+                  | ✅            |
| Unit Tests        | majority                 | ✅            |
| Integration Tests | targeted core flows      | ✅            |
| E2E Tests         | 0 (0%)                   | ❌ Planned M9 |
| Coverage Gate     | 89.61% (threshold: 80%)  | ✅            |
| Mock Usages       | high (design-intent)     | -             |

**Overall Assessment**: Test breadth is strong and M8 test growth target has been exceeded (1023 total). Coverage gate is passed (`pytest --cov=src tests` = 89.61%, required 80%). E2E testing remains planned for M9.

---

## 2. Coverage by Component

### 2.1 Test Distribution

| Component              | Files | Tests | Classes | % of Total |
| ---------------------- | ----- | ----- | ------- | ---------- |
| **Veda (Trading)**     | 13    | 275   | 75      | 34.1%      |
| **Clock (Timing)**     | 4     | 93    | 22      | 11.5%      |
| **GLaDOS Core**        | 8     | 74    | 25      | 9.2%       |
| **Marvin (Strategy)**  | 6     | 74    | 18      | 9.2%       |
| **Greta (Simulation)** | 4     | 56    | 13      | 6.9%       |
| **Infrastructure**     | 4     | 51    | 18      | 6.3%       |
| **Events**             | 4     | 45    | 8       | 5.6%       |
| **Integration**        | 4     | 44    | 12      | 5.5%       |
| **GLaDOS Services**    | 4     | 36    | 13      | 4.5%       |
| **GLaDOS Routes**      | 5     | 33    | 9       | 4.1%       |
| **WALL-E (Database)**  | 2     | 25    | 6       | 3.0%       |
| **Haro (Frontend)**    | 15    | 90    | 21      | 8.8%       |

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
                    │    E2E      │  0 tests (0%)
                    │  (Planned)  │  Target: ~20–30 in M9
                    ├─────────────┤
                    │ Integration │  44 tests (5%)
                    │   Tests     │  DB, Event flows
                ┌───┴─────────────┴───┐
                │     Unit Tests      │  762 tests (95%)
                │  Isolated, fast,    │  Avg 0.02s/test
                │  comprehensive      │
                └─────────────────────┘
```

### 3.2 Test Types

| Type            | Count | Description                   | Quality   |
| --------------- | ----- | ----------------------------- | --------- |
| **Unit**        | 762   | Isolated function/class tests | ★★★★★     |
| **Integration** | 44    | Multi-component collaboration | ★★★★☆     |
| **E2E**         | 0     | Full HTTP→DB flow             | ❌ M9     |
| **Performance** | 0     | Load/stress testing           | ❌ Future |

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

### 4.3 Live/Paper Trading ⚠️ PARTIAL

| Flow                         | Status | Tests                          |
| ---------------------------- | ------ | ------------------------------ |
| RealtimeClock selection      | ✅     | `test_run_mode_integration.py` |
| Alpaca connection management | ✅     | `test_alpaca_connection.py`    |
| Order routing to VedaService | ✅     | `test_order_routing.py`        |
| Live run stays RUNNING       | ✅     | `test_run_mode_integration.py` |
| Actual order submission      | ⚠️     | Mocked only                    |
| WebSocket real-time data     | ❌     | Not implemented                |

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

| Category     | Edge Case                | Priority  |
| ------------ | ------------------------ | --------- |
| **Database** | DB failure recovery      | Medium    |
| **Network**  | Partial message delivery | Low       |
| **Security** | Auth bypass attempts     | High (M9) |

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

| Gap                   | Impact                        | Recommendation              | Target |
| --------------------- | ----------------------------- | --------------------------- | ------ |
| **E2E Tests**         | Cannot verify full user flows | Add Playwright tests        | M9     |
| **Auth Tests**        | Security vulnerability        | Add auth middleware + tests | M9     |
| **Real Alpaca Tests** | Unknown production behavior   | Add sandbox integration     | M7     |

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

### M8 (Polish & E2E)

- [ ] Add Playwright E2E tests (~40 tests)
- [ ] Add authentication tests
- [ ] Add error boundary tests
- [ ] Achieve ≥80% code coverage
- [ ] Add performance baseline tests

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

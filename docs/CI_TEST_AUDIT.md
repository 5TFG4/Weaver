# CI & Test Coverage Audit (2026-03-21)

> **Document Charter**  
> **Primary role**: Test coverage quality gate — identifies what CI actually validates, what tests are real vs shallow, and where critical gaps exist.  
> **Authoritative for**: CI pipeline coverage analysis, test quality assessment, testing gap priorities.  
> **Not authoritative for**: milestone execution (see `MILESTONE_PLAN.md`), test counts (see `TEST_COVERAGE.md`).  
> **Audit date**: 2026-03-21 · **Milestone context**: Post-M10 (E2E Tests complete)

---

## Table of Contents

1. [CI Pipeline Analysis](#1-ci-pipeline-analysis)
2. [Backend Test Quality](#2-backend-test-quality)
3. [Frontend Test Quality](#3-frontend-test-quality)
4. [E2E Test Quality](#4-e2e-test-quality)
5. [Critical Gaps](#5-critical-gaps)
6. [Alpaca Paper Trading Research](#6-alpaca-paper-trading-research)
7. [Recommendations](#7-recommendations)

---

## 1. CI Pipeline Analysis

### 1.1 Current Workflows

| Workflow           | File                     | Trigger Paths                            | What It Does                                           | Duration |
| ------------------ | ------------------------ | ---------------------------------------- | ------------------------------------------------------ | -------- |
| Backend CI         | `backend-ci.yml`         | `src/`, `tests/`, `pyproject.toml`       | ruff lint + mypy + pytest (unit + integration with DB) | ~2m      |
| Frontend CI        | `frontend-ci.yml`        | `haro/`                                  | ESLint + tsc + vitest coverage + vite build            | ~1m      |
| Compose Smoke      | `compose-smoke.yml`      | `docker/`, `src/`, `haro/`               | Build images → start → health check curl               | ~3m      |
| E2E Tests          | `e2e.yml`                | `docker/`, `src/`, `haro/`, `tests/e2e/` | Build E2E stack → Playwright (33 tests)                | ~5m      |
| Alpaca Integration | `alpaca-integration.yml` | `src/veda/`, `tests/integration/veda/`   | Paper API integration tests (6 tests)                  | ~1m      |

### 1.2 Pipeline Gaps

#### 🔴 G-1: Integration Tests Never Run in CI

**Problem**: Backend CI runs `pytest -m "not container"`. Integration tests under `tests/integration/` require `DB_URL` and are marked `skipif(not os.environ.get("DB_URL"))`. CI has no database service, so all 44 integration tests are always skipped.

**Impact**: Database interaction code (event log, offset store, bar repository, backtest flow) is never validated in CI. Regressions in SQL queries, migration compatibility, or repository methods go undetected until manual local testing.

**Fix**: Add a PostgreSQL service to Backend CI, or create a separate `integration-ci.yml` workflow.

#### 🟡 G-2: No Coverage Reporting in Frontend CI

**Problem**: Frontend CI runs `npm run test` without coverage flags. vitest.config.ts has coverage configured (v8 provider) but it's not invoked.

**Impact**: Frontend coverage can silently degrade without anyone noticing.

**Fix**: Add `npm run test -- --coverage` and optionally fail on threshold.

#### 🟢 G-3: Compose Smoke Overlaps with E2E

**Problem**: Compose Smoke only builds images and curls health endpoints. E2E does the same plus runs 23 real tests.

**Impact**: Not a bug, but Compose Smoke adds ~1m to every PR for minimal value above E2E. Consider whether both are needed.

---

## 2. Backend Test Quality

### 2.1 Strong Coverage (Genuine Value)

| Module                    | Tests | Assessment                                                     |
| ------------------------- | ----- | -------------------------------------------------------------- |
| Clock (backtest/realtime) | 115   | ✅✅ Excellent. Edge cases, callbacks, time boundaries.        |
| Veda (trading service)    | 175+  | ✅ Solid. Order lifecycle, position tracking, fill handling.   |
| Marvin (strategy engine)  | 120   | ✅ Solid. Plugin loading, SMA crossovers, signal validation.   |
| Greta (backtest engine)   | 77    | ✅ Good. Fill simulation, slippage, commission.                |
| Events                    | 54    | ✅ Good. Registration, subscription, filtering, serialization. |
| API routes                | 49    | ✅ Good. All 13 endpoints covered.                             |

### 2.2 Areas Using Mock Appropriately

- **MockExchangeAdapter**: Used in Veda unit tests. Correct — unit tests should not call real exchanges.
- **AsyncMock for DB sessions**: Used in route tests. Correct — route tests should be fast and isolated.
- **FakeEventBus**: Used in service tests. Correct — event delivery tested separately in integration.

### 2.3 Areas Where Mocking Masks Real Problems

#### 🔴 B-1: Alpaca Adapter Unit Tests Use Only Mock SDK

Alpaca adapter tests mock all `TradingClient` calls. This is correct for unit tests, but there are **zero integration tests** that verify:

- Real API authentication works
- Order parameter mapping matches Alpaca's actual contract
- Error codes from Alpaca are correctly mapped to our `OrderStatus` enums
- Connection timeouts and retries work

See [Section 6](#6-alpaca-paper-trading-research) for Alpaca paper trading capabilities.

#### 🟡 B-2: Integration Tests Exist But Never Run in CI

44 integration tests are well-written and test real DB interactions:

- `test_backtest_flow.py` (5 tests) — full backtest with real DB
- `test_bar_repository.py` (14 tests) — bar persistence and querying
- `test_event_log.py` (14 tests) — PostgreSQL event append/read/subscribe
- `test_offset_store.py` (16 tests) — consumer offset persistence

These provide real value but are invisible to CI (see G-1).

### 2.4 Missing Backend Tests

| Gap                                     | Severity  | Description                                         |
| --------------------------------------- | --------- | --------------------------------------------------- |
| Concurrent run operations               | 🔴 High   | No tests for multiple simultaneous start/stop calls |
| Database connection failure recovery    | 🟡 Medium | No tests for DB disconnect/reconnect behavior       |
| Complex multi-symbol backtests          | 🟡 Medium | Only single-symbol tested                           |
| Strategy runtime errors during backtest | 🟡 Medium | Unhandled exception propagation not validated       |

---

## 3. Frontend Test Quality

### 3.1 Test Distribution

| Category      | Total  | Tested | Coverage | Assessment          |
| ------------- | ------ | ------ | -------- | ------------------- |
| Pages         | 4      | 3      | 75%      | ✅ Good             |
| Components    | 11     | 8      | 73%      | ✅ Good             |
| **Hooks**     | **10** | **2**  | **20%**  | 🔴 **Critical gap** |
| API functions | 9      | 6      | 67%      | 🟡 Okay             |
| Stores        | 1      | 1      | 100%     | ✅ Complete         |

### 3.2 Hook Coverage Crisis

**8 of 10 hooks have zero tests.** This is the single largest frontend testing gap.

| Untested Hook      | Used By              | Risk                                |
| ------------------ | -------------------- | ----------------------------------- |
| `useCreateRun()`   | CreateRunForm        | 🔴 Core mutation — form submission  |
| `useStartRun()`    | RunsPage             | 🔴 Core mutation — run execution    |
| `useStopRun()`     | RunsPage             | 🔴 Core mutation — run cancellation |
| `useOrders()`      | OrdersPage           | 🟡 Data fetching — order list       |
| `useOrder()`       | OrderDetailModal     | 🟡 Data fetching — single order     |
| `useCancelOrder()` | OrdersPage           | 🟡 Mutation — order cancellation    |
| `useHealth()`      | Dashboard            | 🟢 Low risk — health display        |
| `useRun()`         | RunsPage (deep link) | 🟢 Low risk — single run view       |

### 3.3 Untested Components

| Component              | Risk      | Why It Matters                                            |
| ---------------------- | --------- | --------------------------------------------------------- |
| `CreateRunForm.tsx`    | 🔴 High   | Core user interaction, form validation, mode selection    |
| `OrderDetailModal.tsx` | 🟡 Medium | Uses `useOrder()` hook, modal open/close, field rendering |
| `Header.tsx`           | 🟢 Low    | Simple display, partially tested via Layout               |
| `Sidebar.tsx`          | 🟢 Low    | Partially tested via Layout integration                   |

### 3.4 Untested API Functions

| Function               | Risk                                        |
| ---------------------- | ------------------------------------------- |
| `startRun(runId)`      | 🟡 Called by untested `useStartRun` hook    |
| `cancelOrder(orderId)` | 🟡 Called by untested `useCancelOrder` hook |
| `fetchHealth()`        | 🟢 Simple GET, used in Dashboard            |

---

## 4. E2E Test Quality

### 4.1 What E2E Actually Validates

| Test Group    | Tests | Real Value?    | Assessment                                        |
| ------------- | ----- | -------------- | ------------------------------------------------- |
| Navigation    | 6     | ✅ Yes         | Pages load, routes work, sidebar navigates        |
| Backtest flow | 6     | ✅ Yes         | Create → start → completed lifecycle with real DB |
| Paper flow    | 5     | ✅ Yes         | Create → running → stopped state machine          |
| Orders        | 2     | ⚠️ **Shallow** | Only tests MockOrderService (2 hardcoded orders)  |
| SSE           | 4     | ✅ Yes         | Real EventSource connection, real-time updates    |

### 4.2 E2E Limitations

#### 🔴 E-1: Orders E2E Tests Are Mock-Only

Without Alpaca credentials in the E2E environment, `VedaService` is `None` and routes fall back to `MockOrderService`. The 2 order tests verify that 2 hardcoded mock orders render correctly. They do **not** test:

- Real backtest → fill → order chain
- Order filtering by status/symbol
- Order cancellation flow
- Orders from different runs

This is the single biggest gap in E2E coverage. Fix options:

1. Add paper trading credentials to E2E environment (see Section 6)
2. Create a "test-mode" adapter that generates deterministic orders from backtests

#### 🟡 E-2: No Form Validation E2E Tests

`CreateRunForm` is tested in E2E only as "fill valid data → submit → succeeds". No tests for:

- Empty strategy ID
- Invalid time range (end before start)
- Missing required fields
- Duplicate submission

#### 🟡 E-3: No Pagination/Filter E2E Tests

Both runs and orders pages support pagination and filtering, but E2E only tests basic list rendering.

---

## 5. Critical Gaps — Priority Summary

### P0 (Must Fix)

| ID  | Gap                          | Impact                            | Fix Effort                                       |
| --- | ---------------------------- | --------------------------------- | ------------------------------------------------ |
| G-1 | Integration tests not in CI  | DB regressions undetected         | Low — add `services: postgres` to backend-ci.yml |
| F-1 | 8/10 frontend hooks untested | Core mutations have zero coverage | Medium — ~8 test files                           |

### P1 (Should Fix)

| ID  | Gap                                      | Impact                                       | Fix Effort                                           |
| --- | ---------------------------------------- | -------------------------------------------- | ---------------------------------------------------- |
| E-1 | Orders E2E mock-only                     | Order rendering pipeline untested end-to-end | Medium — requires Alpaca paper creds or test adapter |
| B-1 | Alpaca adapter untested against real API | Contract drift undetected                    | Medium — requires paper creds in CI                  |
| E-2 | No form validation E2E                   | Invalid input not caught                     | Low — ~3-4 tests                                     |

### P2 (Nice to Have)

| ID  | Gap                            | Impact                               | Fix Effort                   |
| --- | ------------------------------ | ------------------------------------ | ---------------------------- |
| G-2 | No frontend coverage reporting | Coverage decay invisible             | Low — add `--coverage` flag  |
| B-2 | Concurrent operations untested | Race conditions possible             | Medium — async test fixtures |
| E-3 | No pagination/filtering E2E    | UI features untested at system level | Low — ~4-6 tests             |

---

## 6. Alpaca Paper Trading Research

### 6.1 Paper Trading Overview

Alpaca paper trading is a real-time simulation that mirrors the live API exactly. Key facts:

- **Default balance**: $100,000
- **API**: Identical to live — same endpoints, same SDK, same parameters
- **Base URL**: `https://paper-api.alpaca.markets`
- **Fills**: Simulated against real-time NBBO (National Best Bid/Offer)
- **Partial fills**: Random 10% of the time
- **Commission-free** (no regulatory fees simulated)
- **No dividends** simulated

### 6.2 Programmatic Cleanup (Available via API)

| Operation              | API                                    | Python SDK                                       | Purpose                 |
| ---------------------- | -------------------------------------- | ------------------------------------------------ | ----------------------- |
| Cancel all open orders | `DELETE /v2/orders`                    | `TradingClient.cancel_orders()`                  | Clean slate before test |
| Close all positions    | `DELETE /v2/positions`                 | `TradingClient.close_all_positions()`            | Liquidate everything    |
| Get account info       | `GET /v2/account`                      | `TradingClient.get_account()`                    | Check balance, status   |
| Get/Update config      | `GET/PATCH /v2/account/configurations` | `TradingClient.get/set_account_configurations()` | DTR, shorting, etc.     |

### 6.3 Account Reset (NOT Available via API)

**Alpaca removed the old `DELETE /v2/account` reset endpoint.** Account reset now requires:

1. Go to dashboard → click paper account number
2. "Account Settings" → "Delete Account"
3. "Open New Paper Account"
4. Generate new API keys for the new account

**This means**: We cannot programmatically reset account balance to $100k. We can only clean up orders and positions.

### 6.4 Practical Test Strategy for Weaver

**For CI/E2E with real Alpaca paper trading:**

```
Cleanup (before each test):
1. DELETE /v2/orders        → cancel all open orders
2. DELETE /v2/positions     → close all positions
3. Wait for positions to close (may take seconds for market orders)
4. GET /v2/account          → verify account is ACTIVE

Test execution:
- Run strategy → verify orders placed via Alpaca API
- Verify fills arrive (may take seconds during market hours)
- Verify position updates

Limitations:
- Tests involving fills only work during market hours (or use crypto for 24/7)
- Account balance decreases over time (cannot reset via API)
- PDT rules apply if >4 day trades in 5 days with <$25k equity
```

**Recommendation**: Use **crypto pairs** (BTC/USD, ETH/USD) for paper trading tests — they trade 24/7, avoiding market hours dependency. Keep order sizes tiny (0.001 BTC ≈ $60-100) to preserve account balance.

### 6.5 Credentials for CI

**Current GitHub Secrets** (already configured):

| Secret Name               | Maps To (env var)         | Purpose                     |
| ------------------------- | ------------------------- | --------------------------- |
| `ALPACA_API_KEY`          | `ALPACA_LIVE_API_KEY`     | Live trading (NOT for CI)   |
| `ALPACA_API_SECRET`       | `ALPACA_LIVE_API_SECRET`  | Live trading (NOT for CI)   |
| `ALPACA_PAPER_API_KEY`    | `ALPACA_PAPER_API_KEY`    | Paper trading — safe for CI |
| `ALPACA_PAPER_API_SECRET` | `ALPACA_PAPER_API_SECRET` | Paper trading — safe for CI |

> ⚠️ **Naming mismatch**: The live secret on GitHub is `ALPACA_API_KEY` (no `LIVE_` prefix),
> but `AlpacaConfig` expects `ALPACA_LIVE_API_KEY`. Mapping required when referencing:
> `ALPACA_LIVE_API_KEY: ${{ secrets.ALPACA_API_KEY }}`

**🔴 Public Repo Security Requirements** — This repo is **public**. Introducing secrets into CI must follow these rules strictly:

1. **Current state**: CI does **not** reference any Alpaca secrets (all Alpaca tests are mocked)
2. **When introducing secrets in the future**:
   - Create a **dedicated** workflow (e.g. `alpaca-integration.yml`) — do not add to existing workflows
   - Add fork protection: `if: github.event.pull_request.head.repo.full_name == github.repository`
   - **Never** upload container logs containing secrets as artifacts (artifact contents are NOT automatically masked by GitHub)
   - `pull_request:` trigger is safe — fork PRs receive empty strings for secrets
   - `pull_request_target:` **must never be used** — it grants fork PRs access to secrets
3. **Advanced option**: Consider GitHub Environments (supports approval workflows, branch restrictions) instead of repo-level secrets
4. **E2E compose config**: Alpaca variables in `docker-compose.e2e.yml` are currently empty string literals.
   When introducing secrets, change to `${ALPACA_PAPER_API_KEY:-}` for environment passthrough with empty default

### 6.6 What Our Adapter Already Supports

The existing `AlpacaAdapter` in `src/veda/adapters/alpaca_adapter.py` already implements:

- `connect()` — validates account status
- `submit_order()` — full order parameter mapping
- `cancel_order()` / `get_order()` / `list_orders()`
- `get_positions()` / `get_position(symbol)`
- `get_bars()` / `get_latest_bar()` / `get_latest_quote()` / `get_latest_trade()`

**Not yet implemented**: `stream_bars()`, `stream_quotes()` (raise `NotImplementedError`)

### 6.7 Missing Adapter Methods for Test Cleanup

The adapter does NOT currently expose bulk cleanup methods. To support test fixtures:

```python
# These exist in Alpaca SDK but not in our adapter:
TradingClient.cancel_orders()         # Cancel ALL open orders
TradingClient.close_all_positions()   # Close ALL positions
```

Adding these to `AlpacaAdapter` (or a separate test utility) would enable clean test setup/teardown.

---

## 7. Resolution Log & Execution Plan

### 7.1 Completed (P0)

**G-1: Integration tests not in CI** ✅

- Added `services: postgres` (PostgreSQL 16 with health check) to `backend-ci.yml`
- Set `DB_URL=postgresql+asyncpg://weaver:weaver@localhost:5432/weaver_test`
- Added `alembic upgrade head` step before pytest
- Added `--ignore=tests/e2e` to avoid playwright collection errors in non-Docker CI
- Synced `scripts/ci/check-local.sh` with same `--ignore=tests/e2e` flag + DB_URL warning
- **Verified**: 48 integration tests pass in dev container with DB_URL

**F-1: Frontend hooks untested** ✅

- Expanded `useRuns.test.tsx`: +5 tests covering `useRun`, `useCreateRun`, `useStartRun`, `useStopRun`
- Created `useOrders.test.tsx`: 6 tests covering `useOrders`, `useOrder`, `useCancelOrder`
- Created `useHealth.test.tsx`: 2 tests covering health query
- **Verified**: 104 frontend tests pass (was 73)

---

### 7.2 Remaining Gap Analysis

After completing P0, the remaining gaps are re-classified below. The key principle: **gaps are organized by the system risk they address**, not by the layer they sit in (backend/frontend/E2E).

#### Risk Category Overview

| Category                     | What It Protects                          | Remaining Gaps | Highest Severity |
| ---------------------------- | ----------------------------------------- | -------------- | ---------------- |
| **A: Exchange Connectivity** | Can we actually trade?                    | B-1, B-1-CI    | 🔴 Critical      |
| **B: E2E Data Integrity**    | Does the full stack produce correct data? | E-1            | 🟡 High          |
| **C: E2E Input Quality**     | Does the UI reject bad input?             | E-2            | 🟡 Medium        |
| **D: CI Observability**      | Can we see problems in CI?                | G-2            | 🟢 Low           |
| **E: Robustness**            | Does the system handle edge cases?        | B-2, E-3, R-1  | 🟢 Low           |

---

### 7.3 Wave 1 — Exchange Connectivity (Critical)

**Why this is the top priority**: The system's primary purpose is to trade via Alpaca. If the adapter code is broken — wrong parameter names, SDK version mismatch, authentication failure, response mapping error — **every live/paper trading feature is silently broken**. Currently there is zero validation that our adapter can communicate with the real Alpaca API.

This is the only gap that is both **high-impact** and **invisible until production**.

#### B-1: Alpaca Adapter Integration Tests

**Problem**: All 21 adapter unit tests inject `MagicMock()` for the Alpaca SDK clients. `connect()` is never called against a real endpoint. Real API response-to-model mapping is never validated. Contract drift between our adapter and the Alpaca SDK goes undetected.

**Scope**: New file `tests/integration/veda/test_alpaca_paper.py`

| Test                                  | What it verifies                                                |
| ------------------------------------- | --------------------------------------------------------------- |
| `test_connect_succeeds`               | `connect()` creates clients, account is ACTIVE                  |
| `test_get_account_returns_real_data`  | Account has equity, buying_power, status fields                 |
| `test_submit_and_get_order_roundtrip` | Submit small crypto order → `get_order()` returns matching data |
| `test_cancel_pending_order`           | Limit order far from market → cancel → status is CANCELED       |
| `test_list_orders_includes_submitted` | Submit order → `list_orders()` includes it                      |
| `test_get_positions_after_fill`       | Market order fills → `get_positions()` shows position           |

**Safety design**:

- Crypto only (BTC/USD) — trades 24/7, no market-hours dependency
- Tiny quantities (0.001 BTC ≈ $60-100) to preserve paper balance
- `cancel_all_orders()` + `close_all_positions()` in fixture teardown
- Tests skip when `ALPACA_PAPER_API_KEY` not set (same pattern as DB integration tests)

**Source changes needed**:

- Add `cancel_all_orders()` and `close_all_positions()` to `AlpacaAdapter` (wraps existing SDK methods)
- New test file with `@pytest.mark.integration` marker

#### B-1-CI: Dedicated Alpaca Integration CI Workflow

**Problem**: Alpaca tests require paper API keys. These secrets cannot be added to existing workflows because:

1. `e2e.yml` uploads container logs as artifacts — artifact contents are NOT auto-masked by GitHub, anyone can download them from a public repo
2. Adding secrets to general-purpose workflows increases the exposure surface

**Scope**: New workflow `.github/workflows/alpaca-integration.yml`

**Design**:

```yaml
name: Alpaca Integration
on:
  push:
    branches: [main]
    paths: [src/veda/**, tests/integration/veda/**]
  pull_request:
    paths: [src/veda/**, tests/integration/veda/**]

jobs:
  alpaca-paper:
    # Fork protection — fork PRs receive empty secrets, tests skip gracefully
    if: github.event.pull_request.head.repo.full_name == github.repository || github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration/veda/ -v --timeout=60
        env:
          ALPACA_PAPER_API_KEY: ${{ secrets.ALPACA_PAPER_API_KEY }}
          ALPACA_PAPER_API_SECRET: ${{ secrets.ALPACA_PAPER_API_SECRET }}
    # NO artifact uploads — this is intentional for secret safety
```

**Security rules** (see also §6.5):

- Secrets injected only in the `run:` step `env`, not job-level
- No `actions/upload-artifact` — ever
- Fork protection via `if:` condition
- Trigger limited to `src/veda/**` changes only
- Uses `pull_request:` (safe), never `pull_request_target:` (unsafe)

**Secret mapping** (see naming mismatch in §6.5):

- `ALPACA_PAPER_API_KEY` secret → `ALPACA_PAPER_API_KEY` env var — names match, no mapping needed
- `ALPACA_PAPER_API_SECRET` secret → `ALPACA_PAPER_API_SECRET` env var — names match

---

### 7.4 Wave 2 — E2E Data Integrity (High) ✅ COMPLETE

These gaps affect test quality — the E2E suite validates the full stack but currently has blind spots in order data flow and input validation.

#### E-1: Orders E2E with Real Database Data ✅

**Problem**: Orders page E2E tests (`test_orders.py`) render 2 hardcoded mock orders from `MockOrderService`. They only verify mock data renders — no real order-from-backtest lifecycle is tested.

**Architecture discovery**: During implementation, tracing the backtest execution path revealed that Greta processes orders in-memory and emits `orders.Placed`/`orders.Filled` events to the EventLog. However, a **race condition** prevents these events from reaching the outbox: the `strategy.FetchWindow → data.WindowReady → strategy.PlaceRequest → backtest.PlaceOrder → place_order()` chain involves 3 `spawn_tracked_task` (fire-and-forget) hops, but `BacktestClock` only yields once (`asyncio.sleep(0)`) between ticks. The cleanup runs immediately after the clock exits, killing in-flight tasks.

**What was delivered**:

| File                                 | Changes                                                   |
| ------------------------------------ | --------------------------------------------------------- |
| `tests/e2e/helpers.py`               | Added `list_orders()` and `get_order()` to `E2EApiClient` |
| `tests/e2e/test_orders_lifecycle.py` | **NEW**: 8 tests across 3 classes                         |

| Test Class                | Tests                                                        | Status                                               |
| ------------------------- | ------------------------------------------------------------ | ---------------------------------------------------- |
| `TestBacktestOrderEvents` | 3 tests (events in outbox, payload fields, strategy signals) | **xfail** — blocked by backtest async race condition |
| `TestOrdersApi`           | 3 tests (paginated response, required fields, get by id)     | **pass**                                             |
| `TestOrdersPage`          | 2 tests (table columns, detail modal)                        | **pass**                                             |

**Backlog item created**: Fix the backtest async race condition so that `spawn_tracked_task` hops complete before the next tick / cleanup. When fixed, the 3 xfail tests will turn green and the markers can be removed.

#### E-2: Form Validation E2E Tests ✅

**Problem**: `CreateRunForm` uses only HTML `required` attributes. No E2E coverage for invalid input.

**What was delivered**: Added `TestFormValidation` class to `tests/e2e/test_backtest_flow.py`:

| Test                                      | What it verifies                                            | Status   |
| ----------------------------------------- | ----------------------------------------------------------- | -------- |
| `test_create_form_rejects_empty_strategy` | Submit with empty strategy ID blocked by browser validation | **pass** |
| `test_create_form_rejects_empty_symbols`  | Submit with empty symbols blocked                           | **pass** |

**Note**: `test_create_form_shows_api_error` was dropped because there is no visible error feedback in the current UI — `useCreateRun()` mutation has no `onError` handler, so API failures silently reset the button.

**E2E suite total**: 33 tests (30 passed, 3 xfailed) — up from 23 tests.

---

### 7.5 Wave 3 — CI Observability (Low)

#### G-2: Frontend Coverage Reporting in CI ✅

**Problem**: Frontend CI runs `npm run test` without `--coverage`. vitest.config.ts has coverage configured (v8 provider) but it is not invoked in CI.

**Fix applied**: Changed `npm run test` → `npm run test:coverage` in `.github/workflows/frontend-ci.yml`. This invokes `vitest run --coverage` which uses the v8 provider already configured in `vitest.config.ts`. Local verification: 104 tests passed, 94.8% statement coverage.

---

### 7.6 Wave 4 — CI Fix & Hardening (Critical)

Wave 1-3 test code is correct but exposed **real production bugs** and **CI infrastructure issues** that must be fixed before merge. These were discovered during the first CI run of PR #15.

#### C-1: Backend CI — `init_tables` Fixture Uses Hardcoded Path

**Problem**: `tests/conftest.py` line 222 hardcodes `PROJECT_ROOT` default to `/weaver` (the Docker container workdir). In GitHub Actions the project root is `/home/runner/work/Weaver/Weaver`. The `init_tables` fixture calls `alembic upgrade head` with `cwd=project_root` which raises `FileNotFoundError: [Errno 2] No such file or directory: '/weaver'`.

**Impact**: 4 integration tests in `tests/unit/veda/test_persistence.py` ERROR in Backend CI. These tests use the `db_session` fixture → `init_tables` → broken path. Backend CI has been red since PR #15 opened (8 consecutive runs).

**CI log evidence**:

```
ERROR tests/unit/veda/test_persistence.py::TestOrderRepositorySave::test_save_order_persists_to_db
  - FileNotFoundError: [Errno 2] No such file or directory: '/weaver'
ERROR tests/unit/veda/test_persistence.py::TestOrderRepositoryQuery::test_get_by_id_returns_order
  - FileNotFoundError: [Errno 2] No such file or directory: '/weaver'
(... 2 more identical errors)
```

**Fix**:

- File: `tests/conftest.py`
- Change: Replace hardcoded `/weaver` default with dynamic path computation using `Path(__file__).resolve().parent.parent` (conftest.py is at `tests/conftest.py`, parent.parent = project root)
- Verification: `alembic.ini` exists in the computed project root

**Risk**: Low — only changes the default value; Docker containers already set `PROJECT_ROOT=/weaver` via env.

#### C-2: Alpaca Adapter `submit_order()` SDK Contract Mismatch

**Problem**: `AlpacaAdapter.submit_order()` (line 236) calls:

```python
response = await asyncio.to_thread(self._trading_client.submit_order, **order_params)
```

But `TradingClient.submit_order()` signature is:

```python
submit_order(self, order_data: OrderRequest) -> Order
```

It accepts a single `OrderRequest` object, not keyword arguments. Passing `**order_params` causes `TypeError: TradingClient.submit_order() got an unexpected keyword argument 'symbol'`.

**Impact**: **Every real order submission fails.** Paper trading and live trading are completely broken. This was invisible to the 21 unit tests because they all mock `TradingClient`. The Alpaca Integration CI caught this immediately — 4 out of 6 tests fail (the 2 connection/account tests pass).

**CI log evidence**:

```
OrderSubmitResult(success=False, exchange_order_id=None,
  status=<OrderStatus.REJECTED: 'rejected'>,
  error_code='ALPACA_ERROR',
  error_message="TradingClient.submit_order() got an unexpected keyword argument 'symbol'")
```

**Fix**:

- File: `src/veda/adapters/alpaca_adapter.py`
- Change: Import `MarketOrderRequest`, `LimitOrderRequest`, `StopOrderRequest`, `StopLimitOrderRequest` from `alpaca.trading.requests`. Construct the appropriate request object based on `intent.order_type`, then pass it as a single argument:
  ```python
  order_data = MarketOrderRequest(**order_params)  # (or LimitOrderRequest etc.)
  response = await asyncio.to_thread(self._trading_client.submit_order, order_data)
  ```
- The Alpaca SDK's Pydantic models accept string values for enum fields (`"buy"` → `OrderSide.BUY`), so the existing `_map_order_type()` / `_map_time_in_force()` string output is compatible.

**Risk**: Medium — changes production order execution code path. Requires both unit test updates (mocks must expect `OrderRequest` objects) and integration test re-verification.

#### C-3: Alpaca Adapter `list_orders()` SDK Contract Mismatch (Latent)

**Problem**: `AlpacaAdapter.list_orders()` (line 329) calls:

```python
response = await asyncio.to_thread(self._trading_client.get_orders, **params)
```

But `TradingClient.get_orders()` signature is:

```python
get_orders(self, filter: Optional[GetOrdersRequest] = None) -> List[Order]
```

Same issue as C-2: expects a `GetOrdersRequest` object, not keyword args.

**Impact**: **Every order listing call fails.** This bug was masked in CI because `submit_order` fails first (the test never reaches `list_orders`). In production, any page load of the Orders page with a real VedaService would crash.

**Fix**:

- File: `src/veda/adapters/alpaca_adapter.py`
- Change: Import `GetOrdersRequest` from `alpaca.trading.requests`. Construct the filter object:
  ```python
  filter_request = GetOrdersRequest(**params)
  response = await asyncio.to_thread(self._trading_client.get_orders, filter=filter_request)
  ```

**Risk**: Low — same pattern as C-2.

#### C-4: Dev Container Alpaca Test Skip Logic → **Moved to Backlog (B-10)**

Deferred — does not affect CI. Only causes 6 spurious failures when running full `pytest` in the dev container with placeholder credentials. See B-10 in §7.7 for full analysis and proposed fix.

#### C-5: Document Sync (Stale Status/Numbers) ✅

**Problem**: Three docs have outdated information after Waves 1-3 and audit findings.

| Document                                            | Issue                                                                                 |
| --------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `docs/architecture/roadmap.md`                      | M9, M10 show `⏳ PLANNED` in §2 and §3 — should be `✅ COMPLETE`                      |
| `docs/TEST_COVERAGE.md`                             | E2E count = 23 (should be 33), frontend tests = 90 (should be 104), M9 = `⏳ Planned` |
| `docs/archive/milestone-details/m10-e2e-release.md` | Status header = `⏳ PLANNED`                                                          |

**Fix**: Pure text updates to match actual measured values.

**Risk**: None — documentation only.

**Status**: ✅ Completed — 5 documentation files updated (MILESTONE_PLAN.md, roadmap.md, TEST_COVERAGE.md, m10-e2e-release.md, CI_TEST_AUDIT.md).

#### C-6: Unit Test Mock Hardening — `create_autospec`

**Problem**: All 21 unit tests in `tests/unit/veda/test_alpaca_adapter.py` use `MagicMock()` for `TradingClient`. `MagicMock` accepts **any** call signature silently — `mock.submit_order(symbol="AAPL")` and `mock.submit_order(some_request)` both succeed. This is why the C-2/C-3 SDK contract bugs were invisible to unit tests.

**Impact**: Unit tests give false confidence. Future SDK contract changes would again be invisible.

**Fix**:

- File: `tests/unit/veda/test_alpaca_adapter.py`
- Change: Replace `MagicMock()` with `create_autospec(TradingClient, instance=True)` for the trading client mock. Autospec constrains mock calls to match the real method signatures. If `submit_order` is called with kwargs instead of a positional `OrderRequest`, autospec raises `TypeError` immediately.
- Also update `test_submit_order_calls_alpaca_api` and related tests to verify the actual parameter types:
  ```python
  call_args = mock_client.submit_order.call_args
  order_request = call_args[0][0]  # first positional arg
  assert isinstance(order_request, MarketOrderRequest)
  ```

**Note on two improvement directions**: `create_autospec` (signature enforcement) and explicit parameter type assertions are **complementary**, not redundant. Autospec catches "wrong calling convention" (kwargs vs positional); type assertions catch "wrong request class" (e.g., `MarketOrderRequest` when it should be `LimitOrderRequest`). Both are applied.

**Risk**: Low — test-only change. May require adjusting some mock setup code.

---

### 7.7 Backlog (Wave 5+)

Items marked **→ M11** have been promoted to milestone M11 (Runtime Robustness & UX Polish) and are now **resolved**. See [m11-runtime-robustness.md](archive/milestone-details/m11-runtime-robustness.md) for detailed design.

#### Resolved (M11) ✅

| ID   | Gap                                                               | Impact                                                                                                                                                                                                                                                      | Layer    | Resolution                                  |
| ---- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------- |
| B-2  | Concurrent run operations (simultaneous start/stop)               | Race conditions possible                                                                                                                                                                                                                                    | Backend  | ✅ M11-3 (per-run asyncio.Lock)             |
| B-3  | Backtest async race (`spawn_tracked_task` × 3 vs `sleep(0)` × 1)  | Order events lost in backtest mode                                                                                                                                                                                                                          | Backend  | ✅ M11-1 (task registry + drain)            |
| F-2  | No API error feedback in CreateRunForm                            | Failed run creation silently resets                                                                                                                                                                                                                         | Frontend | ✅ M11-4 (onError notifications)            |
| R-3  | Strategy runtime errors during backtest                           | Exception propagation unvalidated                                                                                                                                                                                                                           | Backend  | ✅ M11-2 (fail fast → ERROR + cleanup)      |
| B-8  | Unified dev container (Python + Node + Docker CLI + socket mount) | Dev environment fragmented — see §7.9 for full design discussion                                                                                                                                                                                            | Infra    | ✅ M11-0 (devcontainer.json + socket mount) |
| B-9  | Local CI via Docker (`check-local.sh` rewrite)                    | Current script runs on bare host — see §7.9                                                                                                                                                                                                                 | Infra    | ✅ M11-0 (two-script approach)              |
| B-10 | Dev container Alpaca test skip logic                              | Placeholder `ALPACA_PAPER_API_KEY=your_paper_api_key` in `.env` bypasses `skipif` → 6 spurious failures in dev container. Fix: filter placeholder values in skip condition. Does not affect CI. Deferred to be bundled with B-8/B-9 dev environment rebuild | Infra    | ✅ M11-5 (\_has_real_alpaca_creds)          |

#### Remaining Backlog (M12+)

| ID  | Gap                                                         | Impact                               | Layer       | Status          |
| --- | ----------------------------------------------------------- | ------------------------------------ | ----------- | --------------- |
| E-3 | Pagination/filtering E2E (runs + orders pages)              | UI features untested at system level | E2E         | Deferred (M12+) |
| R-1 | Connection resilience (DB disconnect, Alpaca timeout/retry) | Error recovery untested              | Backend     | Deferred (M12+) |
| R-2 | Complex multi-symbol backtests                              | Only single-symbol tested            | Integration | Deferred (M12+) |

---

### 7.8 Execution Summary

| Wave               | Items                                                                                                                | Depends On                 | Risk                                      | Stories                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------- | -------------------------- | ----------------------------------------- | --------------------------------------------------------------- |
| **Wave 1** ✅      | B-1 (adapter tests) + B-1-CI (workflow)                                                                              | Paper API key in local env | Medium — external API                     | 6 tests + 2 adapter methods + 1 workflow                        |
| **Wave 2** ✅      | E-1 (orders E2E) + E-2 (form validation E2E)                                                                         | Docker E2E stack running   | Low — internal only                       | 10 tests + 2 helper methods (3 xfail due to backtest race)      |
| **Wave 3** ✅      | G-2 (coverage reporting)                                                                                             | Nothing                    | Trivial                                   | 1 CI config change                                              |
| **Wave 4** ✅      | C-1 (path fix) + C-2 (submit_order) + C-3 (list_orders) + C-5 (doc sync ✅) + C-6 (autospec)                         | Nothing                    | Medium — production code change (C-2/C-3) | 2 adapter fixes + 1 conftest fix + mock hardening + doc updates |
| **Post-Wave 4** ✅ | CI hardening: Actions Node.js 24 upgrade, npm vulnerability patches, permissions lockdown, coverage artifact cleanup | Nothing                    | Low                                       | 5 workflow upgrades + 2 npm fixes + 5 permissions + .gitignore  |
| **Backlog**        | B-2, B-3, B-8–B-10, F-2, R-3 → **resolved in M11** ✅ ; E-3, R-1, R-2 remain deferred                                | Various                    | Low–Medium                                | See M11 design doc                                              |

**Rationale for Wave 4 now**: Backend CI and Alpaca Integration CI have been red since PR #15 opened. C-2 (submit_order) is a **real production bug** — live/paper order submission is broken. These must be fixed before merge.

**Wave 4 outcome**: All 6 items completed. Backend CI and Alpaca Integration CI turned green. PR #15 all 5 workflows passing.

---

### 7.8a Post-Wave 4 — CI Hardening (2026-03-22) ✅

Additional improvements applied after Wave 4 to resolve GitHub security alerts, deprecation warnings, and repository hygiene issues discovered during PR #15 review.

#### H-1: GitHub Actions Node.js 24 Upgrade ✅

All 5 workflow files upgraded to Node.js 24-compatible action versions:

| Action                    | Old | New    | Breaking Changes                                |
| ------------------------- | --- | ------ | ----------------------------------------------- |
| `actions/checkout`        | v4  | **v6** | Credential persistence to separate file         |
| `actions/setup-python`    | v5  | **v6** | Node 24 runtime                                 |
| `actions/setup-node`      | v4  | **v6** | Auto-caching when lock file detected (npm only) |
| `actions/cache`           | v4  | **v5** | Node 24 runtime                                 |
| `actions/upload-artifact` | v4  | **v5** | Node 24 runtime                                 |

**Rationale**: GitHub will force Node.js 24 starting June 2, 2026. Proactive upgrade eliminates deprecation warnings.

#### H-2: npm Dependency Vulnerability Patches ✅

| Package   | Old              | New        | Vulnerability                                          | Severity |
| --------- | ---------------- | ---------- | ------------------------------------------------------ | -------- |
| `flatted` | 3.3.3            | **3.4.2**  | Prototype Pollution via `parse()` (CVE)                | High     |
| `undici`  | 7.x (vulnerable) | **7.24.5** | HTTP smuggling, WebSocket DoS, CRLF injection (6 CVEs) | High     |

- `flatted`: Fixed via `overrides` in `haro/package.json` (eslint → flat-cache → flatted transitive dep)
- `undici`: Fixed via `npm audit fix` (vitest transitive dep, semver-compatible upgrade)
- Both are devDependencies — do not affect production bundle

#### H-3: Workflow Permissions Lockdown ✅

All 5 workflows now declare explicit `permissions: contents: read` (CodeQL alert #3 fix). This enforces least-privilege for `GITHUB_TOKEN` — prevents supply-chain attacks from modifying the repository even if an action is compromised.

#### H-4: Coverage Artifact Cleanup ✅

54 generated istanbul coverage report files (`haro/coverage/`) were committed to git by accident. Removed from tracking via `git rm --cached` and added `coverage` to `haro/.gitignore`. This also resolves CodeQL alert #6 (DOM XSS in istanbul's `sorter.js`).

---

### 7.9 Dev Environment Architecture — Discussion & Design (Backlog B-8/B-9/B-10)

This section records the analysis and design decisions from the Wave 4 planning discussion. These items are deferred but fully scoped for future implementation.

#### Current State (Problems)

1. **Fragmented dev containers**: `backend_dev` (Python 3.13 + Node 20) and `frontend_dev` (Node 20 only) are separate services. Developers remote into one container and lose IDE support for the other stack.

2. **`check-local.sh` runs on bare host**: The local CI script invokes `ruff`, `pytest`, `npm run test` etc. directly on the host machine. If the developer works inside Docker (the intended workflow), the host may lack Python/Node dependencies, making `check-local.sh` fail or produce inconsistent results vs CI.

3. **No Docker access from dev container**: The dev container cannot run `docker compose` commands, so compose-smoke and e2e tests cannot be validated locally before push.

4. **Alpaca test skip logic**: `docker/example.env` has placeholder `ALPACA_PAPER_API_KEY=your_paper_api_key`. The `skipif(not os.environ.get(...))` condition treats this non-empty placeholder as truthy → 6 Alpaca integration tests run with fake credentials and fail. GitHub Secrets only exist in Actions runner runtime — they never auto-sync to local environments.

#### Existing Asset

`docker/backend/Dockerfile.dev` already installs Node 20 alongside Python 3.13:

```dockerfile
# Install Node.js 20 LTS (for VS Code TypeScript/ESLint extensions support)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs
```

This means `backend_dev` is already a near-complete full-stack dev container.

#### Designed Solution

**B-8: Unified dev container** — Merge `backend_dev` and `frontend_dev` into a single `dev` service:

- Base: `python:3.13-bookworm` + Node 20 (already in Dockerfile.dev)
- Add: Docker CLI (static binary, ~50 MB) — no daemon needed
- Add: Mount `/var/run/docker.sock` from host (Docker Socket Mount / "DooD")
- Remove: Separate `frontend_dev` service
- Run `npm install` in container entrypoint or Dockerfile to ensure `node_modules` is available for IDE
- VS Code Remote: Single window, single container, full-stack code intelligence (Pylance + TypeScript/ESLint)

**Docker Socket Mount explained**: The host Docker daemon listens on `/var/run/docker.sock`. By volume-mounting this socket into the dev container, the container's `docker` CLI commands are forwarded to the host daemon. Containers started this way are **sibling containers** on the host, not nested. This avoids Docker-in-Docker complexity.

```
┌─ Host ──────────────────────────────────────┐
│  dockerd ◄── /var/run/docker.sock           │
│       ▲              ▲ (volume mount)       │
│       │              │                      │
│  ┌─ dev container ───┼─────┐                │
│  │  docker CLI ──────┘     │                │
│  │  python, node, ruff ... │                │
│  └─────────────────────────┘                │
│       │ (sibling containers via socket)     │
│  ┌─ prod stack ─┐  ┌─ e2e stack ──┐        │
│  │  backend     │  │  test_runner  │        │
│  │  frontend    │  │  backend_e2e  │        │
│  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────┘
```

**Security note**: Socket mount grants host-level Docker control (equivalent to root). Acceptable for dev only — never use in production containers.

**Known caveats**:

- File path mismatch: container paths (`/weaver/...`) differ from host paths. Compose files invoked from inside the container need host-relative paths or env var mapping.
- Socket permissions: may need `--group-add` or `chmod` on the socket file.
- Docker CLI version in container should be compatible with host daemon.

**B-9: Local CI rewrite** — Rewrite `scripts/ci/check-local.sh` to run inside the unified dev container:

- Workflows 1-3 (backend-ci, alpaca-integration, frontend-ci): Execute directly in container — all tools available natively.
- Workflows 4-5 (compose-smoke, e2e): Use `docker compose` via socket mount to spin up sibling containers.
- Alternative: Integrate [`act`](https://github.com/nektos/act) to parse `.github/workflows/*.yml` and replay them locally.

**B-10: Alpaca test skip logic** — Fix `skipif` condition to filter placeholder values:

```python
_alpaca_key = os.environ.get("ALPACA_PAPER_API_KEY", "")
_skip_alpaca = not _alpaca_key or _alpaca_key.startswith("your_")
```

Bundle with B-8/B-9 since the dev environment rebuild will change how credentials flow into the container.

---

_This audit should be re-run after each milestone to track progress on identified gaps._

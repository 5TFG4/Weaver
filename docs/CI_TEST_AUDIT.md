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

| Workflow | File | Trigger Paths | What It Does | Duration |
|----------|------|--------------|--------------|----------|
| Backend CI | `backend-ci.yml` | `src/`, `tests/`, `pyproject.toml` | ruff lint + mypy + pytest (unit only) | ~1m |
| Frontend CI | `frontend-ci.yml` | `haro/` | ESLint + tsc + vitest + vite build | ~40s |
| Compose Smoke | `compose-smoke.yml` | `docker/`, `src/`, `haro/` | Build images → start → health check curl | ~1m |
| E2E Tests | `e2e.yml` | `docker/`, `src/`, `haro/`, `tests/e2e/` | Build E2E stack → Playwright (23 tests) | ~3-5m |

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

| Module | Tests | Assessment |
|--------|-------|------------|
| Clock (backtest/realtime) | 115 | ✅✅ Excellent. Edge cases, callbacks, time boundaries. |
| Veda (trading service) | 175+ | ✅ Solid. Order lifecycle, position tracking, fill handling. |
| Marvin (strategy engine) | 120 | ✅ Solid. Plugin loading, SMA crossovers, signal validation. |
| Greta (backtest engine) | 77 | ✅ Good. Fill simulation, slippage, commission. |
| Events | 54 | ✅ Good. Registration, subscription, filtering, serialization. |
| API routes | 49 | ✅ Good. All 13 endpoints covered. |

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

| Gap | Severity | Description |
|-----|----------|-------------|
| Concurrent run operations | 🔴 High | No tests for multiple simultaneous start/stop calls |
| Database connection failure recovery | 🟡 Medium | No tests for DB disconnect/reconnect behavior |
| Complex multi-symbol backtests | 🟡 Medium | Only single-symbol tested |
| Strategy runtime errors during backtest | 🟡 Medium | Unhandled exception propagation not validated |

---

## 3. Frontend Test Quality

### 3.1 Test Distribution

| Category | Total | Tested | Coverage | Assessment |
|----------|-------|--------|----------|------------|
| Pages | 4 | 3 | 75% | ✅ Good |
| Components | 11 | 8 | 73% | ✅ Good |
| **Hooks** | **10** | **2** | **20%** | 🔴 **Critical gap** |
| API functions | 9 | 6 | 67% | 🟡 Okay |
| Stores | 1 | 1 | 100% | ✅ Complete |

### 3.2 Hook Coverage Crisis

**8 of 10 hooks have zero tests.** This is the single largest frontend testing gap.

| Untested Hook | Used By | Risk |
|---------------|---------|------|
| `useCreateRun()` | CreateRunForm | 🔴 Core mutation — form submission |
| `useStartRun()` | RunsPage | 🔴 Core mutation — run execution |
| `useStopRun()` | RunsPage | 🔴 Core mutation — run cancellation |
| `useOrders()` | OrdersPage | 🟡 Data fetching — order list |
| `useOrder()` | OrderDetailModal | 🟡 Data fetching — single order |
| `useCancelOrder()` | OrdersPage | 🟡 Mutation — order cancellation |
| `useHealth()` | Dashboard | 🟢 Low risk — health display |
| `useRun()` | RunsPage (deep link) | 🟢 Low risk — single run view |

### 3.3 Untested Components

| Component | Risk | Why It Matters |
|-----------|------|----------------|
| `CreateRunForm.tsx` | 🔴 High | Core user interaction, form validation, mode selection |
| `OrderDetailModal.tsx` | 🟡 Medium | Uses `useOrder()` hook, modal open/close, field rendering |
| `Header.tsx` | 🟢 Low | Simple display, partially tested via Layout |
| `Sidebar.tsx` | 🟢 Low | Partially tested via Layout integration |

### 3.4 Untested API Functions

| Function | Risk |
|----------|------|
| `startRun(runId)` | 🟡 Called by untested `useStartRun` hook |
| `cancelOrder(orderId)` | 🟡 Called by untested `useCancelOrder` hook |
| `fetchHealth()` | 🟢 Simple GET, used in Dashboard |

---

## 4. E2E Test Quality

### 4.1 What E2E Actually Validates

| Test Group | Tests | Real Value? | Assessment |
|------------|-------|-------------|------------|
| Navigation | 6 | ✅ Yes | Pages load, routes work, sidebar navigates |
| Backtest flow | 6 | ✅ Yes | Create → start → completed lifecycle with real DB |
| Paper flow | 5 | ✅ Yes | Create → running → stopped state machine |
| Orders | 2 | ⚠️ **Shallow** | Only tests MockOrderService (2 hardcoded orders) |
| SSE | 4 | ✅ Yes | Real EventSource connection, real-time updates |

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

| ID | Gap | Impact | Fix Effort |
|----|-----|--------|------------|
| G-1 | Integration tests not in CI | DB regressions undetected | Low — add `services: postgres` to backend-ci.yml |
| F-1 | 8/10 frontend hooks untested | Core mutations have zero coverage | Medium — ~8 test files |

### P1 (Should Fix)

| ID | Gap | Impact | Fix Effort |
|----|-----|--------|------------|
| E-1 | Orders E2E mock-only | Order rendering pipeline untested end-to-end | Medium — requires Alpaca paper creds or test adapter |
| B-1 | Alpaca adapter untested against real API | Contract drift undetected | Medium — requires paper creds in CI |
| E-2 | No form validation E2E | Invalid input not caught | Low — ~3-4 tests |

### P2 (Nice to Have)

| ID | Gap | Impact | Fix Effort |
|----|-----|--------|------------|
| G-2 | No frontend coverage reporting | Coverage decay invisible | Low — add `--coverage` flag |
| B-2 | Concurrent operations untested | Race conditions possible | Medium — async test fixtures |
| E-3 | No pagination/filtering E2E | UI features untested at system level | Low — ~4-6 tests |

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

| Operation | API | Python SDK | Purpose |
|-----------|-----|-----------|---------|
| Cancel all open orders | `DELETE /v2/orders` | `TradingClient.cancel_orders()` | Clean slate before test |
| Close all positions | `DELETE /v2/positions` | `TradingClient.close_all_positions()` | Liquidate everything |
| Get account info | `GET /v2/account` | `TradingClient.get_account()` | Check balance, status |
| Get/Update config | `GET/PATCH /v2/account/configurations` | `TradingClient.get/set_account_configurations()` | DTR, shorting, etc. |

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

| Secret Name | Maps To (env var) | Purpose |
|---|---|---|
| `ALPACA_API_KEY` | `ALPACA_LIVE_API_KEY` | Live trading (NOT for CI) |
| `ALPACA_API_SECRET` | `ALPACA_LIVE_API_SECRET` | Live trading (NOT for CI) |
| `ALPACA_PAPER_API_KEY` | `ALPACA_PAPER_API_KEY` | Paper trading — safe for CI |
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

| Category | What It Protects | Remaining Gaps | Highest Severity |
|----------|-----------------|----------------|------------------|
| **A: Exchange Connectivity** | Can we actually trade? | B-1, B-1-CI | 🔴 Critical |
| **B: E2E Data Integrity** | Does the full stack produce correct data? | E-1 | 🟡 High |
| **C: E2E Input Quality** | Does the UI reject bad input? | E-2 | 🟡 Medium |
| **D: CI Observability** | Can we see problems in CI? | G-2 | 🟢 Low |
| **E: Robustness** | Does the system handle edge cases? | B-2, E-3, R-1 | 🟢 Low |

---

### 7.3 Wave 1 — Exchange Connectivity (Critical)

**Why this is the top priority**: The system's primary purpose is to trade via Alpaca. If the adapter code is broken — wrong parameter names, SDK version mismatch, authentication failure, response mapping error — **every live/paper trading feature is silently broken**. Currently there is zero validation that our adapter can communicate with the real Alpaca API.

This is the only gap that is both **high-impact** and **invisible until production**.

#### B-1: Alpaca Adapter Integration Tests

**Problem**: All 21 adapter unit tests inject `MagicMock()` for the Alpaca SDK clients. `connect()` is never called against a real endpoint. Real API response-to-model mapping is never validated. Contract drift between our adapter and the Alpaca SDK goes undetected.

**Scope**: New file `tests/integration/veda/test_alpaca_paper.py`

| Test | What it verifies |
|------|-----------------|
| `test_connect_succeeds` | `connect()` creates clients, account is ACTIVE |
| `test_get_account_returns_real_data` | Account has equity, buying_power, status fields |
| `test_submit_and_get_order_roundtrip` | Submit small crypto order → `get_order()` returns matching data |
| `test_cancel_pending_order` | Limit order far from market → cancel → status is CANCELED |
| `test_list_orders_includes_submitted` | Submit order → `list_orders()` includes it |
| `test_get_positions_after_fill` | Market order fills → `get_positions()` shows position |

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

| File | Changes |
|------|---------|
| `tests/e2e/helpers.py` | Added `list_orders()` and `get_order()` to `E2EApiClient` |
| `tests/e2e/test_orders_lifecycle.py` | **NEW**: 8 tests across 3 classes |

| Test Class | Tests | Status |
|-----------|-------|--------|
| `TestBacktestOrderEvents` | 3 tests (events in outbox, payload fields, strategy signals) | **xfail** — blocked by backtest async race condition |
| `TestOrdersApi` | 3 tests (paginated response, required fields, get by id) | **pass** |
| `TestOrdersPage` | 2 tests (table columns, detail modal) | **pass** |

**Backlog item created**: Fix the backtest async race condition so that `spawn_tracked_task` hops complete before the next tick / cleanup. When fixed, the 3 xfail tests will turn green and the markers can be removed.

#### E-2: Form Validation E2E Tests ✅

**Problem**: `CreateRunForm` uses only HTML `required` attributes. No E2E coverage for invalid input.

**What was delivered**: Added `TestFormValidation` class to `tests/e2e/test_backtest_flow.py`:

| Test | What it verifies | Status |
|------|-----------------|--------|
| `test_create_form_rejects_empty_strategy` | Submit with empty strategy ID blocked by browser validation | **pass** |
| `test_create_form_rejects_empty_symbols` | Submit with empty symbols blocked | **pass** |

**Note**: `test_create_form_shows_api_error` was dropped because there is no visible error feedback in the current UI — `useCreateRun()` mutation has no `onError` handler, so API failures silently reset the button.

**E2E suite total**: 33 tests (30 passed, 3 xfailed) — up from 23 tests.

---

### 7.5 Wave 3 — CI Observability (Low)

#### G-2: Frontend Coverage Reporting in CI

**Problem**: Frontend CI runs `npm run test` without `--coverage`. vitest.config.ts has coverage configured (v8 provider) but it is not invoked in CI.

**Fix**: Add `--coverage` to frontend-ci.yml vitest step. Optionally add a threshold gate.

---

### 7.6 Backlog (Wave 4)

These are real but low-priority gaps. Not planned for immediate execution.

| ID | Gap | Impact | Layer |
|----|-----|--------|-------|
| B-2 | Concurrent run operations (simultaneous start/stop) | Race conditions possible | Backend |
| B-3 | Backtest async race (`spawn_tracked_task` × 3 vs `sleep(0)` × 1) | Order events lost in backtest mode | Backend |
| E-3 | Pagination/filtering E2E (runs + orders pages) | UI features untested at system level | E2E |
| F-2 | No API error feedback in CreateRunForm | Failed run creation silently resets | Frontend |
| R-1 | Connection resilience (DB disconnect, Alpaca timeout/retry) | Error recovery untested | Backend |
| R-2 | Complex multi-symbol backtests | Only single-symbol tested | Integration |
| R-3 | Strategy runtime errors during backtest | Exception propagation unvalidated | Backend |

---

### 7.7 Execution Summary

| Wave | Items | Depends On | Risk | Stories |
|------|-------|-----------|------|---------|
| **Wave 1** ✅ | B-1 (adapter tests) + B-1-CI (workflow) | Paper API key in local env | Medium — external API | 6 tests + 2 adapter methods + 1 workflow |
| **Wave 2** ✅ | E-1 (orders E2E) + E-2 (form validation E2E) | Docker E2E stack running | Low — internal only | 10 tests + 2 helper methods (3 xfail due to backtest race) |
| **Wave 3** | G-2 (coverage reporting) | Nothing | Trivial | 1 CI config change |
| **Backlog** | B-2, E-3, R-1, R-2, R-3, backtest async race fix | Various | Low | Deferred |

**Rationale for Wave 1 first**: The system's #1 external dependency is Alpaca. If the adapter is broken, live/paper trading is entirely non-functional. This is the only remaining gap where a bug is both high-impact and completely undetectable by any existing test. Waves 2-3 improve coverage quality but test code paths that are already partially validated.

---

_This audit should be re-run after each milestone to track progress on identified gaps._

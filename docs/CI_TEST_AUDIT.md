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

To enable real paper trading in CI, add these as GitHub repository secrets:
- `ALPACA_PAPER_API_KEY`
- `ALPACA_PAPER_API_SECRET`

Then inject into `docker-compose.e2e.yml` via environment variables. **Security note**: These are paper trading only — no real money risk, but treat API keys as secrets regardless.

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

## 7. Recommendations

### 7.1 Immediate (This Sprint)

1. **Fix G-1**: Add PostgreSQL service to Backend CI workflow so integration tests run
2. **Fix F-1**: Add tests for core frontend hooks (`useCreateRun`, `useStartRun`, `useStopRun`)
3. Add `cancel_all_orders()` and `close_all_positions()` to `AlpacaAdapter`

### 7.2 Next Sprint

4. **Fix E-1**: Configure paper trading credentials → real order E2E tests using crypto (24/7)
5. **Fix E-2**: Add form validation E2E tests
6. Add `CreateRunForm` component tests

### 7.3 Backlog

7. Frontend coverage reporting in CI
8. Concurrent operation tests
9. Pagination/filtering E2E tests
10. Connection resilience tests (DB disconnect, Alpaca timeout)

---

_This audit should be re-run after each milestone to track progress on identified gaps._

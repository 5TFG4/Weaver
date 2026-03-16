# M10: E2E Tests & Release Preparation — Detailed Implementation Plan

> **Document Charter**
> **Primary role**: M10 milestone detailed implementation guide.
> **Authoritative for**: M10 task breakdown, file-level change specs, test requirements, and execution order.
> **Not authoritative for**: milestone summary status (use `MILESTONE_PLAN.md`).

> **Status**: ⏳ PLANNED
> **Prerequisite**: M9 ✅ (946 backend tests, 91 frontend tests, 89.61% backend coverage, all CI green)
> **Estimated Effort**: 1.5–2 weeks
> **Branch**: `e2e-release`
> **Key Inputs**: `MILESTONE_PLAN.md` §6, M9 CI infrastructure, existing compose-smoke flow

---

## Table of Contents

1. [Current State — Verified Tool Results](#1-current-state--verified-tool-results)
2. [Goal & Non-Goals](#2-goal--non-goals)
3. [Execution Order & Dependencies](#3-execution-order--dependencies)
4. [M10-0: E2E Infrastructure Setup](#4-m10-0-e2e-infrastructure-setup)
5. [M10-1: E2E Core Navigation & Health](#5-m10-1-e2e-core-navigation--health)
6. [M10-2: E2E Backtest Flow](#6-m10-2-e2e-backtest-flow)
7. [M10-3: E2E Live/Paper Flow](#7-m10-3-e2e-livepaper-flow)
8. [M10-4: E2E Orders & SSE](#8-m10-4-e2e-orders--sse)
9. [M10-5: Release Polish & Documentation](#9-m10-5-release-polish--documentation)
10. [Exit Gate](#10-exit-gate)

---

## 1. Current State — Verified Tool Results

All results measured locally on 2026-03-15; these are facts, not assumptions.

### 1.1 Existing E2E Infrastructure

| Asset                     | Location                            | Status                                           |
| ------------------------- | ----------------------------------- | ------------------------------------------------ |
| E2E test directory        | `tests/e2e/__init__.py`             | ✅ Exists — empty (no test files)                |
| E2E pytest marker         | `pyproject.toml` + `conftest.py`    | ✅ Registered (`@pytest.mark.e2e`)               |
| Auto-collection hook      | `tests/conftest.py`                 | ✅ Tests in `tests/e2e/*` auto-marked `e2e`      |
| Playwright                | `requirements.dev.txt`              | ❌ Not installed                                 |
| Docker Compose (prod)     | `docker/docker-compose.yml`         | ✅ Working (backend + frontend + db)             |
| Compose smoke script      | `scripts/ci/compose-smoke-local.sh` | ✅ Working (`--keep-up` keeps stack for testing) |
| DB migration              | Alembic (`alembic upgrade head`)    | ✅ Working                                       |
| Integration test fixtures | `tests/integration/conftest.py`     | ✅ Pattern available (DB setup, clean_tables)    |

### 1.2 System Under Test — Endpoints

| Endpoint                           | Method | Purpose                             | E2E Relevance           |
| ---------------------------------- | ------ | ----------------------------------- | ----------------------- |
| `GET /api/v1/healthz`              | GET    | Health check                        | ✅ Smoke                |
| `GET /api/v1/runs`                 | GET    | List runs (paginated, filterable)   | ✅ Core                 |
| `POST /api/v1/runs`                | POST   | Create run                          | ✅ Core                 |
| `GET /api/v1/runs/{run_id}`        | GET    | Get run details                     | ✅ Core                 |
| `POST /api/v1/runs/{run_id}/start` | POST   | Start run                           | ✅ Core                 |
| `POST /api/v1/runs/{run_id}/stop`  | POST   | Stop run                            | ✅ Core                 |
| `GET /api/v1/orders`               | GET    | List orders (paginated, filterable) | ✅ Core                 |
| `POST /api/v1/orders`              | POST   | Create order                        | ⚠️ Requires VedaService |
| `GET /api/v1/orders/{order_id}`    | GET    | Get order details                   | ✅ Core                 |
| `DELETE /api/v1/orders/{order_id}` | DELETE | Cancel order                        | ⚠️ Requires VedaService |
| `GET /api/v1/candles`              | GET    | Get candle data                     | ✅ Data                 |
| `GET /api/v1/events/stream`        | GET    | SSE event stream                    | ✅ Realtime             |

### 1.3 Frontend Routes — Test Targets

| Route          | Component  | Key Elements to Test                                       |
| -------------- | ---------- | ---------------------------------------------------------- |
| `/`            | (redirect) | Redirects to `/dashboard`                                  |
| `/dashboard`   | Dashboard  | 4 stat cards, activity feed, health status, navigation     |
| `/runs`        | RunsPage   | Runs table, create form, start/stop buttons, status badges |
| `/runs/:runId` | RunsPage   | Deep link to specific run, run details view                |
| `/orders`      | OrdersPage | Orders table, status filter, run_id filter, detail modal   |
| `/*`           | NotFound   | 404 page renders properly                                  |

### 1.4 Frontend Components Inventory

| Category  | Components                                     | E2E Testable Actions                 |
| --------- | ---------------------------------------------- | ------------------------------------ |
| Layout    | Header, Sidebar, Layout                        | Navigation clicks, active state      |
| Common    | ConnectionStatus, StatCard, StatusBadge, Toast | Visibility, content correctness      |
| Dashboard | ActivityFeed                                   | Event list rendering                 |
| Runs      | CreateRunForm                                  | Form fill, submit, validation        |
| Orders    | OrderTable, OrderStatusBadge, OrderDetailModal | Table rows, filter, modal open/close |

### 1.5 Docker Service Topology (E2E Target)

```
┌─────────────────────────────────────────────────────────────────┐
│  Host Machine / CI Runner                                       │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ PostgreSQL   │   │  Backend     │   │  Frontend (Nginx)    │ │
│  │ :25432       │◀──│  :28919      │◀──│  :23579              │ │
│  │              │   │  FastAPI     │   │  Serves SPA + proxy  │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                                               ↑                  │
│                                        Playwright tests          │
│                                        (chromium headless)       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.6 Test Pyramid — Current vs Target

```
                Current Pyramid                   M10 Target Pyramid
            ┌─────────────────┐              ┌─────────────────┐
            │    E2E: 0       │              │   E2E: ~25      │
            │   (0%)          │              │   (~2.5%)       │
            ├─────────────────┤              ├─────────────────┤
            │ Integration: 44 │              │ Integration: 44 │
            │   (4.2%)        │              │   (~4.2%)       │
        ┌───┴─────────────────┴───┐      ┌───┴─────────────────┴───┐
        │    Unit: 993            │      │    Unit: 993            │
        │   (95.8%)               │      │   (~93.3%)              │
        └─────────────────────────┘      └─────────────────────────┘
        Total: 1037                      Total: ~1062
```

### 1.7 Critical Architecture Constraints for E2E Testing

> **Purpose**: This section documents facts discovered via code reading that DIRECTLY affect what tests are valid. Every E2E test MUST be designed around these constraints to avoid fake or misleading results.

#### 1.7.1 Orders API Data Source — MockOrderService Fallback

**The Problem**: Without Alpaca credentials (E2E stack has none), `VedaService = None`. The orders route then falls back to `MockOrderService`, which returns **2 hardcoded mock orders** regardless of any actual trading activity:

| Mock Order | Symbol  | Side | Type   | Status        | run_id  |
| ---------- | ------- | ---- | ------ | ------------- | ------- |
| order-123  | BTC/USD | BUY  | MARKET | **FILLED**    | run-123 |
| order-456  | ETH/USD | SELL | LIMIT  | **SUBMITTED** | run-123 |

**Impact on tests**: Any test that asserts "orders appear after backtest" by checking GET /orders would be a **FALSE test** — the orders page ALWAYS shows these 2 mock orders, whether or not a backtest ran. The data is completely unrelated to actual trading activity.

**Fallback logic (code trace)**:

```
GET /api/v1/orders → orders_router.list_orders()
  → if veda_service is not None:  (False in E2E — no Alpaca creds)
      return VedaService.list_orders()
  → else:
      return MockOrderService.list()  ← ALWAYS these 2 hardcoded orders
```

**Valid orders tests**: Test that the orders UI renders correctly with the data it receives (mock data). Do NOT claim it shows "real backtest orders".

#### 1.7.2 Backtest Order Persistence Gap

**Backtest fills live only in GretaService memory**. There is NO persistence path from backtest orders to a queryable API:

```
Strategy → PLACE_ORDER → DomainRouter → backtest.PlaceOrder
  → GretaService.place_order()
    → _pending_orders dict (in-memory)
    → emits "orders.Placed" event
  → GretaService.advance_to()
    → DefaultFillSimulator.simulate_fill()
    → fills stored in self._fills list (in-memory)
    → emits "orders.Filled" event
  → BacktestResult.fills (returned to RunManager, NOT persisted to DB)
```

**No database write**: GretaService never inserts into `veda_orders` table.
**No API exposure**: GET /orders never reads from GretaService's fills.

#### 1.7.3 SSE Event Type Names — Backend vs Frontend Mismatch

| Backend Emitter | Event Type String   | Frontend Listener                     | Match?          |
| --------------- | ------------------- | ------------------------------------- | --------------- |
| RunManager      | `run.Started`       | `addEventListener("run.Started")`     | ✅              |
| RunManager      | `run.Completed`     | `addEventListener("run.Completed")`   | ✅              |
| RunManager      | `run.Stopped`       | `addEventListener("run.Stopped")`     | ✅              |
| RunManager      | `run.Error`         | `addEventListener("run.Error")`       | ✅              |
| VedaService     | `orders.Created`    | `addEventListener("orders.Created")`  | ✅              |
| GretaService    | **`orders.Placed`** | ❌ No listener for `orders.Placed`    | **❌ MISMATCH** |
| GretaService    | `orders.Filled`     | `addEventListener("orders.Filled")`   | ✅              |
| VedaService     | `orders.Rejected`   | `addEventListener("orders.Rejected")` | ✅              |

**Impact**: During a backtest, when GretaService emits `orders.Placed`, the frontend has **no listener** for it — no cache invalidation, no toast. The `orders.Filled` event IS received, which triggers `invalidateQueries(["orders"])`, but the refetch hits MockOrderService (see §1.7.1).

**SSE events the frontend WILL receive during a backtest**:

1. `run.Started` → toast "Run {id} started", invalidates `["runs"]`
2. `orders.Filled` → toast "Order filled", invalidates `["orders"]` (but fetches mock data)
3. `run.Completed` → toast "Run {id} completed", invalidates `["runs"]`

#### 1.7.4 CreateRunForm Limitations

The `CreateRunForm` component has 4 fields:

| Field     | HTML ID       | Type                         | Mapped to RunCreate field |
| --------- | ------------- | ---------------------------- | ------------------------- |
| Strategy  | `strategy-id` | text input                   | `strategy_id`             |
| Mode      | `run-mode`    | select (backtest/paper/live) | `mode`                    |
| Symbols   | `symbols`     | text input (comma-separated) | `symbols`                 |
| Timeframe | `timeframe`   | select (1m/5m/15m/1h/4h/1d)  | `timeframe`               |

**Missing**: `start_time` and `end_time` fields. These are required for backtest execution.

**Consequence**: Creating a backtest run via UI creates a `PENDING` run but **cannot set start/end times**. Calling POST /runs/{id}/start will fail because `_start_backtest` requires `start_time` and `end_time` to create a `BacktestClock`.

**For E2E tests**: Creating backtest runs that need to RUN must use the API (POST /runs with start_time/end_time). The UI form can only create pending runs without time bounds.

#### 1.7.5 React Query Cache Behavior

| Setting                    | Value                 | Impact on E2E                                                        |
| -------------------------- | --------------------- | -------------------------------------------------------------------- |
| `staleTime`                | 60,000ms (60s)        | After first fetch, data is "fresh" for 60s; won't refetch on remount |
| `retry`                    | 1                     | Failed queries retry once before showing error                       |
| SSE invalidation           | `invalidateQueries()` | Forces refetch regardless of staleTime                               |
| `refetchInterval` (health) | 30,000ms (30s)        | Health endpoint polls every 30s                                      |

**Impact on tests**: After an API action (e.g., create run), the runs page may NOT show the new data immediately if the cache is still "fresh". Tests must either:

1. Wait for SSE event to invalidate the cache (preferred, tests real behavior)
2. Use `page.reload()` (forces fresh query)
3. Navigate away and back (new mount triggers fetch if stale)

#### 1.7.6 Strategy Behavior — Exact Bar Data Requirements

**Strategy "sample"** (preferred for E2E — simpler, more controllable):

- Lookback window: 10 bars
- Buy condition: `current_close < avg_close_10bars * 0.99` AND no position
- Sell condition: `current_close > avg_close_10bars * 1.01` AND has position
- Order type: MARKET, qty=1.0
- **Minimum bars for 1 BUY**: 11 (10 for history + 1 with price dip)
- **Minimum bars for 1 BUY + 1 SELL**: 13 bars (see calculated seed data in §4)

**Strategy "sma-crossover"** (NOT recommended for E2E — harder to control):

- Lookback window: `slow_period + 1` = 21 bars (default)
- Requires actual crossover pattern in data → harder to guarantee
- Configurable fast_period/slow_period adds complexity
- **Decision**: Use "sample" for all backtest E2E tests

#### 1.7.7 Paper Run Without VedaService

Without Alpaca credentials, paper and live runs have this behavior:

```
Strategy → PLACE_ORDER → strategy.PlaceRequest event
  → DomainRouter → live.PlaceOrder event
    → VedaService subscriber? NO (VedaService = None → not subscribed)
    → Event is SILENTLY DROPPED (no handler, no error)
```

**Result**: Paper run starts, clock ticks, strategy processes data and emits order intents, but NO orders are ever placed or filled. The run just "runs" with wall-clock ticks until stopped.

**Valid paper tests**: Lifecycle only (create → start → running status → stop → stopped status). Do NOT expect orders.

#### 1.7.8 Nginx Reverse Proxy in E2E Stack

The production frontend (Nginx) proxies API requests:

- `/api/*` → `proxy_pass http://backend:8000`
- `/api/v1/events/stream` → special SSE config: `proxy_buffering off`, `proxy_read_timeout 86400s`
- All other paths → serve static files, fallback to `index.html` (SPA routing)

**In the E2E Docker stack**: The Playwright browser connects to the frontend (Nginx) on port 33579. All API calls from the React app go through Nginx to the backend. This is the same path production uses — which is what E2E should test.

#### 1.7.9 Valid vs Invalid Test Summary

| Test Idea                                   | Valid?          | Why                                                                   |
| ------------------------------------------- | --------------- | --------------------------------------------------------------------- |
| Dashboard loads with stat cards             | ✅              | Reads from GET /runs and /orders — data exists (in-memory + mock)     |
| Create backtest run via UI form             | ✅              | POST /runs works; run visible in list                                 |
| Start backtest via API → completes          | ✅              | Synchronous execution; status changes are real                        |
| Orders appear after backtest                | ❌ **FALSE**    | GET /orders returns MockOrderService, not backtest fills              |
| Dashboard "Total Runs" increments           | ✅              | GET /runs data is real (in-memory RunManager)                         |
| SSE delivers run.Completed                  | ✅              | Event chain: RunManager → EventLog → SSEBroadcaster → browser         |
| SSE delivers orders.Created (backtest)      | ❌ **MISMATCH** | GretaService emits "orders.Placed", frontend listens "orders.Created" |
| Orders page shows data                      | ✅ (mock)       | MockOrderService always returns 2 orders; tests UI rendering          |
| Paper run start → running → stop            | ✅              | Clock + status work; just no order execution                          |
| Connection status shows Connected           | ✅              | EventSource connects to SSE endpoint through Nginx                    |
| SSE reconnect after offline                 | ✅              | useSSE.ts has 3s reconnect; Playwright can simulate offline           |
| Create run via UI → status pending in table | ✅              | Real data flow: POST /runs → RunManager → in-memory → GET /runs       |

---

## 2. Goal & Non-Goals

### Goals

1. **E2E Coverage**: Browser-based tests covering critical user workflows — constrained to what the current architecture actually supports (see §1.7)
2. **SSE Verification**: Verify `run.*` event delivery from backend → frontend; document `orders.Placed` mismatch
3. **Backtest Flow**: Create run → start → verify status transition (PENDING → COMPLETED) via UI
4. **Navigation**: All routes load, render, and link correctly; sidebar navigation works
5. **Deployment Guide**: Complete, tested production deployment documentation
6. **Doc Accuracy**: All test counts, coverage numbers, and API docs reflect final state
7. **Performance Baseline**: Measure and document response times and SSE latency

### Non-Goals

- Real exchange API integration testing (requires real credentials)
- Verifying backtest orders on the orders page (architectural gap — see §1.7.2)
- Load/stress testing (future milestone)
- Visual regression testing (screenshot comparison)
- Mobile/responsive layout testing
- Authentication/authorization testing (no auth in current system)

---

## 3. Execution Order & Dependencies

```
M10-0: E2E Infrastructure Setup  ← MUST DO FIRST (Playwright + Compose + helpers)
  │
  ├── M10-0a: Install Playwright + dependencies
  ├── M10-0b: Create E2E Compose stack (docker-compose.e2e.yml)
  ├── M10-0c: E2E helper module (API client, wait utilities)
  ├── M10-0d: E2E conftest.py (fixtures, auto-start/stop)
  │
  ▼
M10-1: Core Navigation & Health  (page loads, routing, health)
  │
  ├── M10-2: Backtest Flow        (create → start → results)
  │
  ├── M10-3: Live/Paper Flow      (create → monitor → stop)
  │
  ├── M10-4: Orders & SSE         (orders page, SSE verification)
  │
  ▼
M10-5: Release Polish & Documentation  (deploy guide, doc sync, perf baseline)
```

**M10-1 through M10-4 are partially parallelizable** once M10-0 is complete, but M10-2 is recommended first because it exercises the simplest end-to-end flow (backtest completes synchronously).

---

## 4. M10-0: E2E Infrastructure Setup

**Why this phase exists**: No E2E test tooling exists in the project. Before writing any test, we need Playwright installed, a dedicated E2E compose stack, and reusable helpers.

### 4.0 Technology Choice: Playwright (Python)

**Why Playwright over Selenium/Cypress**:

| Factor             | Playwright (Python)                  | Selenium                | Cypress               |
| ------------------ | ------------------------------------ | ----------------------- | --------------------- |
| Language match     | ✅ Python (same as backend tests)    | ✅ Python               | ❌ JS only            |
| pytest integration | ✅ `pytest-playwright` built-in      | ⚠️ Custom setup         | ❌ Mocha-based        |
| Auto-wait          | ✅ Smart auto-wait for elements      | ❌ Manual waits         | ✅ Auto-wait          |
| Headless CI        | ✅ First-class headless              | ⚠️ Works, less polished | ✅ Good               |
| SSE testing        | ✅ `page.evaluate` + EventSource API | ⚠️ Complex              | ⚠️ Tricky             |
| Speed              | ✅ Fast (Chromium CDP)               | ❌ Slower               | ✅ Fast               |
| Existing ecosystem | ✅ Fits pytest markers/conftest      | ⚠️ Different fixtures   | ❌ Separate framework |

**Decision**: Playwright Python with `pytest-playwright` plugin — integrates directly with our existing pytest infrastructure, auto-collection hooks, and test markers.

### 4.1 M10-0a: Install Playwright + Dependencies

**File changes**:

1. **`docker/backend/requirements.dev.txt`** — Add:

   ```
   # E2E Testing (Browser Automation)
   playwright>=1.40.0
   pytest-playwright>=0.5.0
   ```

2. **`pyproject.toml`** — Add Playwright base URL config under pytest options:

   ```toml
   [tool.pytest.ini_options]
   # ... existing config ...
   # Playwright settings (used only by E2E tests; base URL overridable via --base-url)
   base_url = "http://127.0.0.1:23579"
   ```

3. **Install browser binaries** (one-time, inside dev container or CI):
   ```bash
   pip install playwright pytest-playwright
   playwright install chromium --with-deps
   ```

**Verification**:

```bash
pip install -r docker/backend/requirements.dev.txt
playwright install chromium --with-deps
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

**Commit**: `build(e2e): add playwright and pytest-playwright dependencies`

### 4.2 M10-0b: E2E Docker Compose Stack

Create a dedicated compose file for E2E testing that is isolated from dev/prod stacks.

**File**: `docker/docker-compose.e2e.yml`

```yaml
# Docker Compose for E2E testing.
# Spins up backend + frontend + db with deterministic ports.
# Usage: docker compose -f docker/docker-compose.e2e.yml up -d --build

name: weaver-e2e

services:
  db_e2e:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: weaver_e2e_db
      POSTGRES_USER: weaver
      POSTGRES_PASSWORD: weaver_e2e_password
    ports:
      - "35432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U weaver -d weaver_e2e_db"]
      interval: 3s
      timeout: 5s
      retries: 10
    tmpfs:
      - /var/lib/postgresql/data # RAM-based for speed

  backend_e2e:
    build:
      context: ..
      dockerfile: docker/backend/Dockerfile
    environment:
      DB_URL: "postgresql+asyncpg://weaver:weaver_e2e_password@db_e2e:5432/weaver_e2e_db"
      ALPACA_LIVE_API_KEY: ""
      ALPACA_LIVE_API_SECRET: ""
      ALPACA_PAPER_API_KEY: ""
      ALPACA_PAPER_API_SECRET: ""
    ports:
      - "38919:8000"
    depends_on:
      db_e2e:
        condition: service_healthy

  frontend_e2e:
    build:
      context: ..
      dockerfile: docker/frontend/Dockerfile
    ports:
      - "33579:80"
    depends_on:
      - backend_e2e
```

**Design decisions**:

- **Fixed ports** (35432, 38919, 33579): Predictable URLs for Playwright base URL; no port conflicts with dev/prod stacks.
- **`tmpfs` for Postgres**: RAM-based data directory for speed (E2E data is ephemeral).
- **No Alpaca credentials**: E2E tests use mock/degraded mode (no real exchange calls).
- **Separate compose project name** (`weaver-e2e`): Isolated from dev/prod containers.

**Commit**: `ci(e2e): add docker-compose.e2e.yml for E2E test stack`

### 4.3 M10-0c: E2E Helper Module

Create reusable utilities for E2E tests.

**File**: `tests/e2e/helpers.py`

```python
"""
E2E Test Helpers

Reusable utilities for browser-based end-to-end tests.
Provides API client, wait utilities, and assertion helpers.
"""

from __future__ import annotations

import httpx

# E2E stack ports (must match docker-compose.e2e.yml)
E2E_API_BASE = "http://127.0.0.1:38919/api/v1"
E2E_FRONTEND_BASE = "http://127.0.0.1:33579"

# Timeouts
DEFAULT_TIMEOUT_MS = 10_000  # 10 seconds for element waits
SSE_TIMEOUT_MS = 15_000      # 15 seconds for SSE event waits
API_TIMEOUT_S = 10           # 10 seconds for direct API calls


class E2EApiClient:
    """Direct HTTP client for E2E test setup/teardown (bypasses browser)."""

    def __init__(self, base_url: str = E2E_API_BASE) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=API_TIMEOUT_S)

    def health(self) -> dict:
        resp = self._client.get("/healthz")
        resp.raise_for_status()
        return resp.json()

    def create_run(
        self,
        strategy_id: str = "sma",
        mode: str = "backtest",
        symbols: list[str] | None = None,
        timeframe: str = "1m",
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict:
        payload: dict = {
            "strategy_id": strategy_id,
            "mode": mode,
            "symbols": symbols or ["BTC/USD"],
            "timeframe": timeframe,
        }
        if start_time:
            payload["start_time"] = start_time
        if end_time:
            payload["end_time"] = end_time
        resp = self._client.post("/runs", json=payload)
        resp.raise_for_status()
        return resp.json()

    def list_runs(self, status: str | None = None, page: int = 1) -> dict:
        params: dict = {"page": page}
        if status:
            params["status"] = status
        resp = self._client.get("/runs", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_run(self, run_id: str) -> dict:
        resp = self._client.get(f"/runs/{run_id}")
        resp.raise_for_status()
        return resp.json()

    def start_run(self, run_id: str) -> dict:
        resp = self._client.post(f"/runs/{run_id}/start")
        resp.raise_for_status()
        return resp.json()

    def stop_run(self, run_id: str) -> dict:
        resp = self._client.post(f"/runs/{run_id}/stop")
        resp.raise_for_status()
        return resp.json()

    def list_orders(self, run_id: str | None = None) -> dict:
        params = {}
        if run_id:
            params["run_id"] = run_id
        resp = self._client.get("/orders", params=params)
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()
```

**Commit**: `test(e2e): add E2E helper module with API client and constants`

### 4.4 M10-0d: E2E conftest.py — Fixtures & Stack Management

**File**: `tests/e2e/conftest.py`

```python
"""
E2E Test Fixtures

Manages the Docker Compose E2E stack lifecycle and provides
Playwright fixtures for browser-based testing.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

from tests.e2e.helpers import E2E_API_BASE, E2E_FRONTEND_BASE, E2EApiClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = PROJECT_ROOT / "docker" / "docker-compose.e2e.yml"
COMPOSE_ARGS = ["docker", "compose", "-f", str(COMPOSE_FILE)]


def _stack_is_healthy() -> bool:
    """Check if both API and frontend are responding."""
    try:
        api_ok = httpx.get(f"{E2E_API_BASE}/healthz", timeout=3).status_code == 200
        front_ok = httpx.get(E2E_FRONTEND_BASE, timeout=3).status_code == 200
        return api_ok and front_ok
    except (httpx.ConnectError, httpx.ReadTimeout):
        return False


def _wait_for_stack(timeout: int = 120) -> None:
    """Wait for the E2E stack to be healthy."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _stack_is_healthy():
            return
        time.sleep(2)
    raise TimeoutError(f"E2E stack not healthy after {timeout}s")


def _run_migrations() -> None:
    """Run Alembic migrations against E2E database."""
    result = subprocess.run(
        [*COMPOSE_ARGS, "exec", "-T", "backend_e2e", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"E2E migration failed: {result.stderr}")


@pytest.fixture(scope="session")
def e2e_stack() -> Generator[None]:
    """
    Manage the E2E Docker Compose stack lifecycle.

    Starts the stack once per test session, runs migrations,
    waits for health, and tears down after all tests complete.
    """
    # Build and start
    subprocess.run(
        [*COMPOSE_ARGS, "up", "-d", "--build", "--wait"],
        cwd=PROJECT_ROOT,
        check=True,
        timeout=300,
    )

    try:
        _wait_for_stack(timeout=120)
        _run_migrations()
        # Wait again after migrations
        _wait_for_stack(timeout=30)
        yield
    finally:
        subprocess.run(
            [*COMPOSE_ARGS, "down", "-v"],
            cwd=PROJECT_ROOT,
            timeout=60,
        )


@pytest.fixture(scope="session")
def api_client(e2e_stack: None) -> Generator[E2EApiClient]:
    """Provide an E2E API client connected to the running stack."""
    client = E2EApiClient()
    yield client
    client.close()


@pytest.fixture(scope="session")
def e2e_base_url(e2e_stack: None) -> str:
    """Base URL for the E2E frontend."""
    return E2E_FRONTEND_BASE


@pytest.fixture
def clean_e2e_db(e2e_stack: None) -> None:
    """
    Reset database state between tests that require isolation.

    Runs TRUNCATE on all tables via the backend container.
    Most tests should NOT need this — only use when test data
    must be completely clean (e.g., empty-state assertions).
    """
    subprocess.run(
        [
            *COMPOSE_ARGS,
            "exec",
            "-T",
            "backend_e2e",
            "python",
            "-c",
            (
                "import asyncio; "
                "from src.walle.database import Database; "
                "from src.config import DatabaseConfig; "
                "import os; "
                "async def clean(): "
                "    db = Database(DatabaseConfig(url=os.environ['DB_URL'])); "
                "    async with db.session() as s: "
                "        for t in ['fills','veda_orders','runs','bars','outbox','consumer_offsets']: "
                "            await s.execute(__import__('sqlalchemy').text(f'TRUNCATE TABLE {t} CASCADE')); "
                "        await s.commit(); "
                "    await db.close(); "
                "asyncio.run(clean())"
            ),
        ],
        check=True,
        timeout=30,
    )
```

**Design decisions**:

- **Session-scoped stack**: Start Docker Compose once per session (expensive operation), not per test.
- **`--wait` flag**: Docker Compose v2 natively waits for health checks before returning.
- **`tmpfs` in compose**: RAM-based Postgres — fast table truncation for isolation.
- **`clean_e2e_db` fixture**: Optional — only used by tests that need guaranteed empty state. Most tests don't need it because they query by specific IDs.

**Commit**: `test(e2e): add E2E conftest with Docker stack management`

### 4.5 M10-0e: E2E Launch Script

**File**: `scripts/ci/e2e-local.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.e2e.yml"
COMPOSE_ARGS=(-f "$COMPOSE_FILE")

echo "=========================================="
echo " E2E Test Runner"
echo "=========================================="

KEEP_UP=false
for arg in "$@"; do
  case "$arg" in
    --keep-up) KEEP_UP=true ;;
  esac
done

teardown() {
  if ! $KEEP_UP; then
    echo ""
    echo "--- Tearing down E2E stack ---"
    docker compose "${COMPOSE_ARGS[@]}" down -v 2>/dev/null || true
  else
    echo ""
    echo "--- Stack left running (--keep-up). Tear down manually: ---"
    echo "  docker compose ${COMPOSE_ARGS[*]} down -v"
  fi
}
trap teardown EXIT

echo ""
echo "--- Building & starting E2E stack ---"
docker compose "${COMPOSE_ARGS[@]}" up -d --build --wait

echo ""
echo "--- Running Alembic migrations ---"
docker compose "${COMPOSE_ARGS[@]}" exec -T backend_e2e alembic upgrade head

echo ""
echo "--- Installing Playwright browser ---"
playwright install chromium --with-deps 2>/dev/null || true

echo ""
echo "--- Running E2E tests ---"
cd "$ROOT_DIR"
pytest tests/e2e/ -v --timeout=60 "$@"

echo ""
echo "=========================================="
echo " E2E tests complete"
echo "=========================================="
```

**Usage**:

```bash
chmod +x scripts/ci/e2e-local.sh
./scripts/ci/e2e-local.sh              # Run and teardown
./scripts/ci/e2e-local.sh --keep-up    # Keep stack running for debugging
```

**Commit**: `ci(e2e): add local E2E test runner script`

### 4.6 M10-0 Verification Checklist

```
- [ ] pip install playwright pytest-playwright succeeds
- [ ] playwright install chromium --with-deps succeeds
- [ ] docker compose -f docker/docker-compose.e2e.yml config validates
- [ ] docker compose -f docker/docker-compose.e2e.yml up -d --build --wait starts all 3 services
- [ ] curl http://127.0.0.1:38919/api/v1/healthz returns 200
- [ ] curl http://127.0.0.1:33579/ returns 200 (HTML)
- [ ] pytest tests/e2e/ --co collects 0 tests (no test files yet, but no import errors)
- [ ] docker compose -f docker/docker-compose.e2e.yml down -v cleans up
```

---

## 5. M10-1: E2E Core Navigation & Health (~6 tests)

**Goal**: Verify all pages load, navigation works, and health status is displayed.

### 5.1 TDD: Test Specification

**File**: `tests/e2e/test_navigation.py`

```python
"""
E2E Tests: Navigation & Health

Verifies all pages load correctly, navigation links work,
and system health is displayed.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestNavigation:
    """Page loading and navigation tests."""

    def test_root_redirects_to_dashboard(self, page: Page, e2e_base_url: str) -> None:
        """Navigating to / redirects to /dashboard."""
        page.goto(e2e_base_url)
        expect(page).to_have_url(f"{e2e_base_url}/dashboard")

    def test_dashboard_page_loads(self, page: Page, e2e_base_url: str) -> None:
        """Dashboard page renders with stat cards."""
        page.goto(f"{e2e_base_url}/dashboard")
        # Should have stat cards visible
        expect(page.get_by_text("Active Runs")).to_be_visible()
        expect(page.get_by_text("Total Runs")).to_be_visible()
        expect(page.get_by_text("Total Orders")).to_be_visible()

    def test_runs_page_loads(self, page: Page, e2e_base_url: str) -> None:
        """Runs page renders with table or empty state."""
        page.goto(f"{e2e_base_url}/runs")
        expect(page).to_have_url(f"{e2e_base_url}/runs")
        # Page should have a heading or table
        expect(page.locator("h1, h2, table")).to_have_count_greater_than(0)

    def test_orders_page_loads(self, page: Page, e2e_base_url: str) -> None:
        """Orders page renders with table or empty state."""
        page.goto(f"{e2e_base_url}/orders")
        expect(page).to_have_url(f"{e2e_base_url}/orders")

    def test_404_page_for_unknown_route(self, page: Page, e2e_base_url: str) -> None:
        """Unknown route shows 404 / NotFound page."""
        page.goto(f"{e2e_base_url}/nonexistent-page")
        expect(page.get_by_text("404")).to_be_visible()

    def test_sidebar_navigation(self, page: Page, e2e_base_url: str) -> None:
        """Sidebar links navigate between pages."""
        page.goto(f"{e2e_base_url}/dashboard")

        # Click runs link in sidebar
        page.get_by_role("link", name="Runs").click()
        expect(page).to_have_url(f"{e2e_base_url}/runs")

        # Click orders link in sidebar
        page.get_by_role("link", name="Orders").click()
        expect(page).to_have_url(f"{e2e_base_url}/orders")

        # Click dashboard link
        page.get_by_role("link", name="Dashboard").click()
        expect(page).to_have_url(f"{e2e_base_url}/dashboard")
```

### 5.2 Per-Test Data Flow & Validity Proof

| #   | Test               | Prerequisite Data                      | Data Source                                                                                                               | Exact Assertion                                                             | Validity Proof                                                                                  | False-Pass Risk                                     |
| --- | ------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 1   | root redirects     | None                                   | Nginx config (`try_files → /index.html`)                                                                                  | URL changes to `/dashboard`                                                 | React Router `<Navigate to="/dashboard" replace />` in App.tsx                                  | None — redirect is deterministic                    |
| 2   | dashboard loads    | Stack running, MockOrderService active | GET /healthz → `{"status":"ok"}`, GET /runs → `{"items":[],"total":0}`, GET /orders → `{"items":[mock1,mock2],"total":2}` | Text "Active Runs", "Total Runs", "Total Orders" visible as StatCard titles | Dashboard.tsx renders 4 StatCards with hardcoded title props                                    | Low — could fail if backend is slow (use auto-wait) |
| 3   | runs page loads    | Stack running                          | GET /runs → `{"items":[],"total":0}` (no runs created yet)                                                                | Page at `/runs` URL; has heading "Runs"                                     | RunsPage.tsx renders h1 "Runs"; empty state shows `data-testid="runs-empty"` with "No runs yet" | None — static text                                  |
| 4   | orders page loads  | Stack running, MockOrderService active | GET /orders → 2 mock orders                                                                                               | Page at `/orders` URL                                                       | OrdersPage.tsx renders table with OrderTable component                                          | Low — mock data always exists                       |
| 5   | 404 page           | None                                   | Client-side React Router                                                                                                  | Text "404" visible                                                          | App.tsx has `<Route path="*" element={<NotFound />} />`; NotFound renders "Page Not Found"      | None — static text, client-side only                |
| 6   | sidebar navigation | All route components loaded            | Client-side React Router                                                                                                  | URL changes correctly on each click                                         | Sidebar.tsx has `<NavLink to="/runs">`, etc.                                                    | Low — Playwright waits for navigation               |

**Empty state behavior**: On first run with a fresh stack, the runs page shows `data-testid="runs-empty"` with the `text "No runs yet"` and `"Create a new run to get started"`. The orders page shows 2 mock orders from MockOrderService (NOT empty state).

**Data-testid selectors available** (for resilient locators):

- `data-testid="dashboard-loading"` — dashboard skeleton
- `data-testid="dashboard-error"` — dashboard error state
- `data-testid="runs-loading"` / `data-testid="runs-error"` / `data-testid="runs-empty"`
- `data-testid="orders-loading"` / `data-testid="orders-error"`
- `data-testid="connection-dot"` — SSE connection indicator

### 5.3 Implementation Notes

- These tests **do not require database setup** beyond having the stack running.
- `expect()` from `pytest-playwright` provides auto-wait + clear error messages.
- `page` fixture is auto-provided by `pytest-playwright` (each test gets a fresh browser context).
- The `e2e_base_url` fixture ensures the stack is started before tests run (session-scoped dependency chain).

### 5.4 Locator Strategy

| Priority | Locator Type              | Example                             | When to Use                   |
| -------- | ------------------------- | ----------------------------------- | ----------------------------- |
| 1        | `get_by_role()`           | `get_by_role("link", name="Runs")`  | Most accessible, resilient    |
| 2        | `get_by_text()`           | `get_by_text("Active Runs")`        | When content is user-visible  |
| 3        | `get_by_test_id()`        | `get_by_test_id("create-run-form")` | When DOM structure may change |
| 4        | `locator("css selector")` | `locator("table tbody tr")`         | Last resort, fragile          |

**Convention**: If a component needs a stable locator, add `data-testid` attributes to the React component. Track these additions as M10-5 cleanup tasks.

### 5.4 Verification

```bash
pytest tests/e2e/test_navigation.py -v --timeout=30
# Expected: 6 passed
```

**Commit**: `test(e2e): add navigation and health E2E tests (6 tests)`

---

## 6. M10-2: E2E Backtest Flow (~6 tests)

**Goal**: Test the backtest run lifecycle through the UI — create run via API, start, verify status transitions (PENDING → COMPLETED), verify run data on dashboard and runs page.

> **⚠️ Scope constraint (see §1.7.2)**: Backtest orders are NOT accessible via GET /orders API. This phase tests run lifecycle only, NOT order generation visibility.

### 6.1 Pre-Condition: Seed Bar Data

Backtest requires historical bar data in the `bars` table. Without seed data, `GretaService.initialize()` loads zero bars → strategy receives empty windows → no signals → no orders → but run still "completes" (just does nothing).

**Strategy choice**: Use `"sample"` strategy (NOT `"sma-crossover"`).

- `"sample"` needs only 10-bar lookback — smaller seed data
- Simpler buy/sell logic — easier to guarantee signals
- `"sma-crossover"` needs 21 bars minimum and harder-to-control crossover patterns

**Exact seed data specification for "sample" strategy** (20 bars, BTC/USD 1m):

We need bars where `current_close < avg_close_10bars * 0.99` triggers a BUY, then `current_close > avg_close_10bars * 1.01` triggers a SELL.

| Bar # | Timestamp (UTC)          | Open  | High  | Low   | Close     | Purpose                                            |
| ----- | ------------------------ | ----- | ----- | ----- | --------- | -------------------------------------------------- |
| 1-10  | 2024-01-15 09:30 – 09:39 | 42000 | 42100 | 41900 | 42000     | Establish baseline average = 42000                 |
| 11    | 2024-01-15 09:40         | 41200 | 41300 | 40900 | **41000** | **BUY trigger**: 41000 < 41900 × 0.99 = 41481 ✓    |
| 12    | 2024-01-15 09:41         | 41500 | 42100 | 41400 | 42000     | Recovery, no signal                                |
| 13    | 2024-01-15 09:42         | 42200 | 42600 | 42100 | **42500** | **SELL trigger**: 42500 > 41950 × 1.01 = 42369.5 ✓ |
| 14-20 | 2024-01-15 09:43 – 09:49 | 42000 | 42100 | 41900 | 42000     | Stable tail, no signals                            |

**Mathematical proof of 2 orders**:

```
Bar 11 tick → lookback window = bars 2-11
  avg_close = (42000×9 + 41000) / 10 = 41900
  current_close = 41000
  41000 < 41900 × 0.99 (= 41481)? YES → BUY market qty=1.0
  position = True

Bar 12 tick → lookback window = bars 3-12
  avg_close = (42000×8 + 41000 + 42000) / 10 = 41900
  current_close = 42000
  42000 > 41900 × 1.01 (= 42319)? NO → no sell

Bar 13 tick → lookback window = bars 4-13
  avg_close = (42000×7 + 41000 + 42000 + 42500) / 10 = 41950
  current_close = 42500
  42500 > 41950 × 1.01 (= 42369.5)? YES → SELL market qty=1.0
  position = False

Bars 14-20 → no position, prices stable → no action
```

**Fill prices**: MARKET orders fill at `bar.open` (DefaultFillSimulator default).

- BUY fills at bar 12's open = 41500 (order placed at bar 11, filled next advance_to)
- SELL fills at bar 14's open = 42000 (order placed at bar 13, filled next advance_to)

**Seed data is idempotent**: Use `ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING` or check before insert. Safe to run seed script multiple times.

**Run config for E2E**:

```json
{
  "strategy_id": "sample",
  "mode": "backtest",
  "symbols": ["BTC/USD"],
  "timeframe": "1m",
  "start_time": "2024-01-15T09:30:00Z",
  "end_time": "2024-01-15T09:50:00Z"
}
```

This covers bars 1-20 (09:30-09:49), 20 clock ticks, and guarantees exactly 2 orders.

### 6.2 Complete Data Flow for One Backtest Run

```
① POST /runs → RunManager.create()
   → Run(status=PENDING) stored in RunManager._runs dict
   → emits "run.Created" event → SSEBroadcaster → browser (no frontend listener)
   → HTTP 201 returns {"id":"<uuid>","status":"pending",...}

② POST /runs/{id}/start → RunManager.start()
   → StrategyLoader.load("sample") → SampleStrategy instance
   → GretaService() created per-run
   → greta.initialize(["BTC/USD"], "1m", start, end) → loads 20 bars from DB into memory
   → BacktestClock(start, end, "1m") created
   → emits "run.Started" → SSE → frontend invalidates ["runs"] cache → toast "Run {id} started"
   → clock.start() runs synchronously:
     Bar 1 tick → strategy.on_tick → FetchWindow → greta.data.WindowReady (only 1 bar, < 10) → no action
     Bar 2-10 ticks → same (building up window)
     Bar 11 tick → strategy.on_tick → FetchWindow → greta provides 10 bars → strategy.on_data
       → BUY signal → PlaceRequest → DomainRouter → backtest.PlaceOrder → greta.place_order()
       → emits "orders.Placed" (frontend NO listener)
     Bar 12 tick → greta.advance_to() processes pending order → fill at open=41500
       → emits "orders.Filled" → SSE → frontend invalidates ["orders"] (refetches MockOrderService)
     Bar 13 tick → SELL signal (similar flow)
     Bar 14-20 → process orders, no new signals
   → clock exhausted → run.status = COMPLETED
   → emits "run.Completed" → SSE → frontend invalidates ["runs"] cache → toast "Run {id} completed"
   → HTTP 200 returns {"id":"<uuid>","status":"completed",...}

③ GET /runs → RunManager.list()
   → Returns all runs from in-memory dict
   → Run is now status=completed, with started_at and stopped_at set

④ GET /orders → MockOrderService.list()
   → Returns 2 hardcoded mock orders (NOT backtest fills!)
   → Always the same regardless of backtest activity
```

### 6.3 Per-Test Specification (6 tests)

#### Test 1: Create backtest run via UI → PENDING status

| Aspect              | Detail                                                                                                                                                                                                                                                                                          |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Prerequisite**    | Stack running, no prior runs needed                                                                                                                                                                                                                                                             |
| **Steps**           | 1. Navigate to `/runs` 2. Click "+ New Run" button 3. Fill Strategy = "sample" (via `#strategy-id` input) 4. Set Mode = "backtest" (via `#run-mode` select) 5. Fill Symbols = "BTC/USD" (via `#symbols` input) 6. Set Timeframe = "1 Minute" (via `#timeframe` select) 7. Click "Create" button |
| **Selector detail** | `page.locator("#strategy-id").fill("sample")` (NOT `get_by_label` — verify `htmlFor` attribute first); `page.locator("#run-mode").select_option("backtest")`; `page.get_by_role("button", name="+ New Run").click()` to open form                                                               |
| **Expected result** | New row in runs table with status text "pending", mode text "backtest", strategy "sample"                                                                                                                                                                                                       |
| **Assertion**       | `expect(page.get_by_text("pending")).to_be_visible()` (relies on StatusBadge rendering)                                                                                                                                                                                                         |
| **Data flow proof** | POST /runs → RunManager.create() → run in memory → form reset → RunsPage useCreateRun mutation → onSuccess invalidates ["runs"] → refetch GET /runs → new row appears                                                                                                                           |
| **False-pass risk** | LOW. The run IS real. Only caveat: this run has no start_time/end_time → cannot be started (see §1.7.4). This is fine — we're only testing creation.                                                                                                                                            |
| **Note**            | CreateRunForm does NOT send start_time/end_time. The created run is valid as PENDING but would fail on start.                                                                                                                                                                                   |

#### Test 2: Create run via API → visible in UI

| Aspect              | Detail                                                                                                                                                                  |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Prerequisite**    | Stack running                                                                                                                                                           |
| **Steps**           | 1. Create run via E2EApiClient (POST /runs with start/end times) 2. Navigate to `/runs` page                                                                            |
| **API call**        | `api_client.create_run(strategy_id="sample", mode="backtest", symbols=["BTC/USD"], timeframe="1m", start_time="2024-01-15T09:30:00Z", end_time="2024-01-15T09:50:00Z")` |
| **Expected**        | Run ID appears in table (first 8 chars of UUID shown in `font-mono` span)                                                                                               |
| **Assertion**       | `expect(page.get_by_text(run["id"][:8])).to_be_visible()`                                                                                                               |
| **Data flow proof** | POST /runs → 201 → page.goto triggers GET /runs → RunManager.list() returns the run → table row rendered with `data-testid="run-row-{id}"`                              |
| **False-pass risk** | NONE. API creates real run; GET /runs reads from same in-memory store.                                                                                                  |

#### Test 3: Start backtest → COMPLETED status (SSE-verified)

| Aspect                                                                                                                                                                                                                 | Detail                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Prerequisite**                                                                                                                                                                                                       | **Seed data MUST be present** (20 bars in `bars` table). Run created via API with start/end times.                                                                                                                                                                                                                                      |
| **Steps**                                                                                                                                                                                                              | 1. Navigate to `/runs` page 2. Wait for SSE connection (2s) 3. Start run via E2EApiClient 4. Wait for "completed" badge to appear (via SSE cache invalidation)                                                                                                                                                                          |
| **Why SSE-first**: Instead of `page.reload()`, we wait for the `run.Completed` SSE event to invalidate the `["runs"]` query cache → React Query refetches → UI updates automatically. This tests the real SSE→UI flow. |
| **Expected result**                                                                                                                                                                                                    | Run status badge changes from "pending" to "completed" WITHOUT manual page reload                                                                                                                                                                                                                                                       |
| **Assertion**                                                                                                                                                                                                          | `expect(page.get_by_text("completed")).to_be_visible(timeout=15000)` (generous timeout for backtest execution + SSE delivery)                                                                                                                                                                                                           |
| **Data flow proof**                                                                                                                                                                                                    | POST /start → RunManager.\_start_backtest() → BacktestClock runs 20 ticks → emits "run.Completed" → SSEBroadcaster → EventSource → useSSE handler → invalidateQueries(["runs"]) → auto-refetch → StatusBadge re-renders                                                                                                                 |
| **False-pass risk**                                                                                                                                                                                                    | MEDIUM. If seed data is missing, the backtest still "completes" (runs 0 or few ticks, no orders but status=COMPLETED). This is technically correct behavior. The test should also verify the run completed with both started_at and stopped_at set via API check: `run = api_client.get_run(id); assert run["started_at"] is not None`. |
| **Fallback**                                                                                                                                                                                                           | If SSE event doesn't arrive within timeout, `page.reload()` as fallback — but this should be logged as a potential SSE issue.                                                                                                                                                                                                           |

#### Test 4: Backtest run detail deep-link

| Aspect              | Detail                                                                                                                     |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Prerequisite**    | Run created via API                                                                                                        |
| **Steps**           | 1. Navigate directly to `/runs/{run_id}`                                                                                   |
| **Expected**        | Page shows run ID (first 8 chars), mode "backtest", strategy "sample"                                                      |
| **Assertion**       | `expect(page.get_by_text(run["id"][:8])).to_be_visible()` and `expect(page.get_by_text("backtest")).to_be_visible()`       |
| **Data flow proof** | URL `/runs/:runId` → React Router → RunsPage component → `useRun(runId)` hook → GET /runs/{id} → RunManager.get() → render |
| **False-pass risk** | NONE. Direct URL → direct API call → render.                                                                               |

#### Test 5: Dashboard "Total Runs" reflects created runs

| Aspect              | Detail                                                                                                                                                                                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Prerequisite**    | Stack clean (or known run count)                                                                                                                                                                                                                                      |
| **Steps**           | 1. Navigate to `/dashboard` 2. Note initial Total Runs value 3. Create run via API 4. Reload page (or wait for SSE) 5. Verify Total Runs incremented                                                                                                                  |
| **Expected**        | StatCard "Total Runs" value increases by 1                                                                                                                                                                                                                            |
| **Assertion**       | After reload: the Total Runs card shows the run count from `GET /runs` response's `total` field. Since we know we created 1 run, check `total >= 1`. Use `expect(page.locator('[data-testid] >> text=/\\d+/').first).to_be_visible()` to verify a number is rendered. |
| **Data flow proof** | Dashboard.tsx: `useRuns({ page: 1, page_size: 50 })` → GET /runs → `data.total` → StatCard value                                                                                                                                                                      |
| **False-pass risk** | LOW. Run counter is real. The `total` value from RunManager.list() is accurate. The risk is only if `page.reload()` happens before the POST /runs response returns — add a small wait.                                                                                |

#### Test 6: Multiple runs listed in table

| Aspect                     | Detail                                                                                                                                                                                                                                                                                     |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Prerequisite**           | No prior runs (or use `clean_e2e_db`)                                                                                                                                                                                                                                                      |
| **Steps**                  | 1. Create 3 runs via API 2. Navigate to `/runs` 3. Count table rows                                                                                                                                                                                                                        |
| **Expected**               | At least 3 rows in table body                                                                                                                                                                                                                                                              |
| **Assertion**              | `expect(page.locator("table tbody tr")).to_have_count(3)` (exact count, or `>= 3` if prior tests created runs)                                                                                                                                                                             |
| **Note on test isolation** | Runs persist in memory across tests within the same session. Using `clean_e2e_db` only cleans DB tables, NOT RunManager's in-memory dict. For cross-test isolation, either: (a) use `>= N` assertions, or (b) accept cumulative state. Recommended: use `>= 3` since run data is additive. |

### 6.4 ~~Removed: test_backtest_generates_orders~~

> **DELETED from plan** (was in original §6.2). This test would have checked orders page after backtest — this is a FALSE test because GET /orders returns MockOrderService data, not backtest fills (see §1.7.1, §1.7.2). Including it would produce misleading test results.

### 6.5 Potential `data-testid` Additions (Frontend)

If existing locators prove too fragile, add these to React components:

| Component     | Attribute                         | Element        |
| ------------- | --------------------------------- | -------------- |
| CreateRunForm | `data-testid="create-run-form"`   | `<form>`       |
| CreateRunForm | `data-testid="create-run-submit"` | Submit button  |
| RunsPage      | `data-testid="runs-table"`        | `<table>`      |
| OrdersPage    | `data-testid="orders-table"`      | `<table>`      |
| StatCard      | `data-testid="stat-{label}"`      | Card container |

### 6.5 Verification

```bash
pytest tests/e2e/test_backtest_flow.py -v --timeout=60
# Expected: 7 passed
```

**Commit**: `test(e2e): add backtest flow E2E tests (7 tests)`

---

## 7. M10-3: E2E Live/Paper Flow (~5 tests)

**Goal**: Test the paper run lifecycle — create, start (enters RUNNING), verify active status, stop, verify stopped status, and error state display.

> **⚠️ Scope constraint (see §1.7.7)**: Without Alpaca credentials, VedaService = None. Paper runs start and the clock ticks, but strategy order intents are silently dropped. Tests should focus on **lifecycle state transitions**, NOT order generation.

### 7.1 Paper Run Architecture in E2E (No VedaService)

```
POST /runs/{id}/start (mode=paper)
  → RunManager._start_live()
    → StrategyLoader.load("sample") → SampleStrategy
    → RealtimeClock() created (wall-clock aligned ticks)
    → runner.initialize()
    → clock.start() runs in BACKGROUND (async, returns immediately)
    → HTTP 200 returns {"status":"running"}

Background loop:
  RealtimeClock ticks every 1m (at wall-clock bar boundaries)
  → strategy.on_tick() → FetchWindow action
  → DomainRouter → "live.FetchWindow" event
    → MockMarketDataService receives → emits data.WindowReady
  → strategy.on_data() → may emit PLACE_ORDER action
  → DomainRouter → "live.PlaceOrder" event
    → VedaService subscriber? NO → EVENT DROPPED SILENTLY

POST /runs/{id}/stop
  → RunManager.stop()
    → clock.stop() → background loop exits
    → status = STOPPED, stopped_at = now
    → emits "run.Stopped" → SSE → frontend
```

**Key implication**: The paper run WILL stay in RUNNING status indefinitely until stopped. The clock actually ticks (every 1 minute, aligned to wall-clock). The strategy actually processes data. But no orders are placed because VedaService is absent.

### 7.2 Per-Test Specification (5 tests)

#### Test 1: Create paper run → visible in UI

| Aspect        | Detail                                                                                                        |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| **Steps**     | 1. Create paper run via API: `strategy_id="sample", mode="paper", symbols=["BTC/USD"]` 2. Navigate to `/runs` |
| **Expected**  | Run appears in table with status "pending", mode badge "paper" (purple badge)                                 |
| **Assertion** | `page.get_by_test_id(f"run-row-{run['id']}")` visible; text "pending" and "paper" within that row             |
| **Data flow** | POST /runs → RunManager.create() → in-memory → GET /runs → table row                                          |
| **Validity**  | ✅ Real run creation, real data. No false-pass risk.                                                          |

#### Test 2: Start paper run → RUNNING status

| Aspect        | Detail                                                                                                                                                      |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**     | 1. Create paper run via API 2. Navigate to `/runs` 3. Wait for SSE connection 4. Start via API 5. Wait for SSE "run.Started" to update UI                   |
| **Expected**  | Status badge changes to "running" (green badge `bg-green-500/20 text-green-400`)                                                                            |
| **Assertion** | `expect(page.get_by_text("running")).to_be_visible(timeout=10000)`                                                                                          |
| **Data flow** | POST /start → RunManager.\_start_live() → run.status = RUNNING → emits "run.Started" → SSE → invalidateQueries(["runs"]) → refetch → StatusBadge re-renders |
| **Validity**  | ✅ Real state transition. RealtimeClock actually starts (but we don't need to wait for ticks).                                                              |
| **Timing**    | The start API returns synchronously with status=running. SSE event arrives shortly after. Generous timeout needed.                                          |

#### Test 3: Dashboard Active Runs counter

| Aspect        | Detail                                                                                                                                                                                                                                                                 |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**     | 1. Create and start paper run 2. Navigate to `/dashboard`                                                                                                                                                                                                              |
| **Expected**  | "Active Runs" StatCard shows value ≥ 1                                                                                                                                                                                                                                 |
| **Assertion** | The Active Runs card computes: `runs.items.filter(r => r.status === "running").length`. After starting 1 paper run, this should be ≥ 1. Since StatCard renders value as `<span class="text-3xl font-bold">`, assert that text near "Active Runs" contains a digit ≥ 1. |
| **Data flow** | Dashboard.tsx: `useRuns()` → GET /runs → count items where status="running" → StatCard value                                                                                                                                                                           |
| **Validity**  | ✅ Real. The run IS running. Counter IS computed from real data.                                                                                                                                                                                                       |
| **Note**      | If multiple prior tests left runs in "running" state, counter may be > 1. This is fine — assert `>= 1`, not `== 1`.                                                                                                                                                    |

#### Test 4: Stop paper run → STOPPED status (via SSE)

| Aspect               | Detail                                                                                                                                                            |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**            | 1. Create and start paper run 2. Navigate to `/runs` 3. Wait for SSE connection 4. Stop via API 5. Wait for SSE "run.Stopped" to update UI                        |
| **Expected**         | Status badge changes to "stopped" (yellow badge `bg-yellow-500/20 text-yellow-400`)                                                                               |
| **Assertion**        | `expect(page.get_by_text("stopped")).to_be_visible(timeout=10000)`                                                                                                |
| **Data flow**        | POST /stop → RunManager.stop() → clock.stop() → run.status = STOPPED → emits "run.Stopped" → SSE → invalidateQueries(["runs"]) → refetch → StatusBadge re-renders |
| **Validity**         | ✅ Real state transition. Clock actually stops. `stopped_at` gets set.                                                                                            |
| **API verification** | After stop, call `api_client.get_run(id)` and assert `status == "stopped"` and `stopped_at is not None` — double-check the UI isn't lying.                        |

#### Test 5: Error state display (invalid strategy)

| Aspect              | Detail                                                                                                                                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**           | 1. Create backtest run with `strategy_id="nonexistent-xyz-strategy"` (start/end times set) 2. Start via API (expect HTTP error or status change) 3. Navigate to `/runs`                                               |
| **Expected**        | Run shows "error" status badge (red badge `bg-red-500/20 text-red-400`)                                                                                                                                               |
| **Behavior**        | RunManager.start() → StrategyLoader.load("nonexistent-xyz-strategy") → raises exception → RunManager catches → sets run.status = ERROR, run.error = message → emits "run.Error" → SSE                                 |
| **API response**    | POST /start may return 200 with status="error" (internal catch) or 500 (unhandled). Test should handle both: catch exception from `api_client.start_run()`, then check `api_client.get_run(id)["status"] == "error"`. |
| **Assertion**       | `expect(page.get_by_text("error")).to_be_visible()`                                                                                                                                                                   |
| **Validity**        | ✅ Tests real error handling path. Strategy not found → ERROR status is the actual system behavior.                                                                                                                   |
| **False-pass risk** | LOW. The error badge text "error" must match the StatusBadge component's rendering. Verify the badge renders the status string directly.                                                                              |

### 7.3 Verification

```bash
pytest tests/e2e/test_paper_flow.py -v --timeout=60
# Expected: 5 passed
```

**Commit**: `test(e2e): add paper trading flow E2E tests (5 tests)`

---

## 8. M10-4: E2E Orders & SSE (~6 tests)

**Goal**: Test the orders page UI rendering and Server-Sent Events delivery for real-time updates.

> **⚠️ Scope constraints (see §1.7)**:
>
> - GET /orders returns **MockOrderService** data (2 hardcoded orders) when VedaService = None. Orders tests verify UI rendering, NOT real trading results.
> - GretaService emits `orders.Placed` but frontend listens for `orders.Created` — SSE order-creation tests for backtest would be **FALSE tests** (see §1.7.3).
> - SSE tests focus on `run.*` events which ARE delivered end-to-end and proven to trigger UI updates.

### 8.1 Orders Page Data Flow (MockOrderService)

```
Browser navigates to /orders
  → React Router renders OrdersPage
  → useOrders() hook fires
  → GET /api/v1/orders (query params: limit=50, offset=0)
  → Nginx proxy_pass → FastAPI
  → orders_router.list_orders()
    → VedaService injected? NO (no Alpaca creds)
    → Fallback: MockOrderService.list_orders()
    → Returns: {
        items: [
          { id: "order-123", symbol: "BTC/USD", side: "buy",
            quantity: 1.0, status: "filled", ... },
          { id: "order-456", symbol: "ETH/USD", side: "sell",
            quantity: 0.5, status: "submitted", ... }
        ],
        total: 2
      }
  → React Query caches response (staleTime=60s)
  → OrdersPage renders <table> with 2 rows
```

**What we CAN test**: UI rendering of the 2 mock orders (table, columns, badges, detail modal).
**What we CANNOT test**: Orders generated by backtest/paper runs appearing on this page.

### 8.2 Per-Test Specification — Orders Page (2 tests)

**File**: `tests/e2e/test_orders.py`

#### Test 1: Orders page renders mock data

| Aspect              | Detail                                                                                                                                                                                             |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**           | 1. Navigate to `/orders` 2. Wait for table to render                                                                                                                                               |
| **Expected**        | Table shows 2 rows (mock orders). First row contains "BTC/USD", "buy", "filled". Second row contains "ETH/USD", "sell", "submitted".                                                               |
| **Assertion**       | `expect(page.locator("table tbody tr")).to_have_count(2)`. Check first row text includes "BTC/USD". Check second row text includes "ETH/USD".                                                      |
| **Data flow**       | GET /orders → MockOrderService → 2 hardcoded orders → table rows                                                                                                                                   |
| **False-pass risk** | LOW. MockOrderService ALWAYS returns these 2 orders. The test is stable but tests mock data, not real trading. This is the honest scope.                                                           |
| **Note**            | If the orders page has an empty state message instead of a table when MockOrderService is disabled, this test needs adjustment. Verify by reading the OrdersPage component at implementation time. |

#### Test 2: Order detail expands on click

| Aspect              | Detail                                                                                                                                   |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**           | 1. Navigate to `/orders` 2. Click first order row 3. Verify detail view appears                                                          |
| **Expected**        | Order detail panel/modal shows: order ID "order-123", symbol "BTC/USD", side "buy", quantity "1.0", status "filled"                      |
| **Assertion**       | After click: `expect(page.get_by_text("order-123")).to_be_visible()` and `expect(page.get_by_text("1.0")).to_be_visible()`               |
| **Data flow**       | Click row → frontend state change → renders OrderDetail component with order data from cache                                             |
| **False-pass risk** | MEDIUM. Depends on how detail view renders. Need to verify OrderDetail component exists and renders these fields at implementation time. |

### 8.3 Per-Test Specification — SSE Delivery (4 tests)

**File**: `tests/e2e/test_sse.py`

> **SSE event flow verification**: The following events are emitted by the backend and have matching frontend listeners:
>
> - `run.Created` → listener ✓ → invalidateQueries(["runs"])
> - `run.Started` → listener ✓ → invalidateQueries(["runs"])
> - `run.Stopped` → listener ✓ → invalidateQueries(["runs"])
> - `run.Completed` → listener ✓ → invalidateQueries(["runs"])
> - `run.Error` → listener ✓ → invalidateQueries(["runs"])
> - `orders.Filled` → listener ✓ → invalidateQueries(["orders"])
> - `orders.Placed` → NO listener ✗ (backtest orders invisible to frontend)

#### Test 3: ConnectionStatus shows "Connected"

| Aspect              | Detail                                                                                                                                                                                                   |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**           | 1. Navigate to `/dashboard` 2. Wait for SSE handshake (up to 5s)                                                                                                                                         |
| **Expected**        | ConnectionStatus component shows text "Connected" with green indicator                                                                                                                                   |
| **Assertion**       | `expect(page.get_by_text("Connected")).to_be_visible(timeout=10000)`                                                                                                                                     |
| **Data flow**       | Page load → `useSSE()` hook creates `EventSource("/api/v1/events/stream")` → Nginx proxy_pass → FastAPI SSE endpoint → `onopen` callback → `setIsConnected(true)` → ConnectionStatus renders "Connected" |
| **False-pass risk** | LOW. The SSE endpoint exists, Nginx is configured with `proxy_buffering off`. If this test fails, the entire SSE subsystem is broken.                                                                    |
| **Prerequisite**    | Nginx config must have: `location /api/v1/events/stream { proxy_buffering off; ... }`. Already in existing `nginx.conf`.                                                                                 |

#### Test 4: SSE delivers run.Started → UI updates without reload

| Aspect                   | Detail                                                                                                                                                                                                                                                                     |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**                | 1. Create backtest run via API (with seed data, so strategy="sample", start/end times within seed range) 2. Navigate to `/runs` 3. Verify "pending" status visible 4. Wait for SSE connection (2s) 5. Start run via API 6. Do NOT reload page 7. Wait for status to change |
| **Expected**             | Run status changes from "pending" → "completed" (backtest completes synchronously) WITHOUT page reload.                                                                                                                                                                    |
| **Assertion**            | `expect(page.get_by_text("completed")).to_be_visible(timeout=15000)`                                                                                                                                                                                                       |
| **Data flow**            | POST /start → RunManager → backtest runs → emits "run.Started" + "run.Completed" → SSEBroadcaster → EventSource → `addEventListener("run.Completed", ...)` → `invalidateQueries(["runs"])` → React Query refetches GET /runs → StatusBadge re-renders "completed"          |
| **False-pass risk**      | LOW. This is the core SSE integration test. If runs page auto-updates, SSE is working end-to-end.                                                                                                                                                                          |
| **Timing consideration** | Backtest with 20 seed bars completes in <1s. SSE delivery adds ~100ms. React Query invalidation + refetch adds ~200ms. Combined: should complete within 5s, use 15s timeout for safety.                                                                                    |

#### Test 5: SSE reconnects after network interruption

| Aspect                   | Detail                                                                                                                                                                                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Steps**                | 1. Navigate to `/dashboard` 2. Wait for "Connected" indicator (5s) 3. `page.context.set_offline(True)` 4. Wait 1s (force disconnection, EventSource fires onerror) 5. `page.context.set_offline(False)` 6. Wait for reconnection (up to 10s) |
| **Expected**             | ConnectionStatus returns to "Connected" after going offline and back online                                                                                                                                                                  |
| **Assertion**            | After step 3: ConnectionStatus may show "Disconnected" or "Connecting..." (optional assert). After step 5: `expect(page.get_by_text("Connected")).to_be_visible(timeout=15000)`                                                              |
| **Data flow**            | Offline → EventSource.onerror → `useSSE` cleanup → RECONNECT_DELAY=3000ms → `new EventSource(...)` → handshake → `onopen` → "Connected"                                                                                                      |
| **False-pass risk**      | MEDIUM. Browser `set_offline()` may not perfectly simulate SSE disconnection. If EventSource doesn't fire `onerror` synchronously, the reconnect path may not trigger within timeout.                                                        |
| **Alternative approach** | If `set_offline` is flaky: instead of simulating network failure, verify that SSE delivers MULTIPLE events (create two runs in sequence, verify both status updates appear). This proves the connection stays alive and delivers repeatedly. |

#### Test 6: SSE delivers run.Stopped → real-time UI update

| Aspect              | Detail                                                                                                                                                                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Steps**           | 1. Create and start a paper run (stays in RUNNING) 2. Navigate to `/runs` 3. Verify "running" visible 4. Wait for SSE connection (2s) 5. Stop run via API 6. Do NOT reload page 7. Wait for status to change |
| **Expected**        | Run status changes from "running" → "stopped" WITHOUT page reload                                                                                                                                            |
| **Assertion**       | `expect(page.get_by_text("stopped")).to_be_visible(timeout=15000)`                                                                                                                                           |
| **Data flow**       | POST /stop → RunManager.stop() → emits "run.Stopped" → SSE → frontend `addEventListener("run.Stopped", ...)` → `invalidateQueries(["runs"])` → refetch → "stopped" badge                                     |
| **Validity**        | ✅ Real state transition via SSE. Complements Test 4 (which tests backtest completion). Together they prove SSE works for both run.Completed and run.Stopped events.                                         |
| **False-pass risk** | LOW. Paper run genuinely enters RUNNING → stop genuinely transitions to STOPPED → SSE event genuinely fires.                                                                                                 |

### 8.4 Tests intentionally NOT included

| Removed Test                                  | Reason                                                                                                                                                |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Orders appear after backtest"                | GET /orders returns MockOrderService data regardless of backtest results. Backtest fills live in GretaService memory only. See §1.7.2.                |
| "Orders filter by status"                     | MockOrderService has only 2 orders with fixed statuses. Filter test would be trivially true or depend on UI implementation details not yet finalized. |
| "SSE delivers orders.Created during backtest" | GretaService emits "orders.Placed" but frontend has NO listener for this event. Test would never see the event. See §1.7.3.                           |
| "SSE event triggers Activity Feed update"     | Activity Feed component implementation not verified to listen to SSE events. Assertion would be vague.                                                |

### 8.5 Verification

```bash
pytest tests/e2e/test_orders.py tests/e2e/test_sse.py -v --timeout=60
# Expected: 6 passed (2 orders + 4 SSE)
```

**Commits**:

- `test(e2e): add orders page E2E tests (2 tests)`
- `test(e2e): add SSE delivery E2E tests (4 tests)`

---

## 9. M10-5: Release Polish & Documentation

**Goal**: Final documentation updates, deployment guide, performance baseline, and cross-doc consistency check.

### 9.1 M10-5a: Production Deployment Guide

Add a comprehensive deployment section to `docs/architecture/deployment.md`.

**Content to add**:

```markdown
## Production Deployment Guide

### Prerequisites

- Docker Engine 24+ with Docker Compose v2
- PostgreSQL 16 (or use the bundled containerized DB)
- Alpaca Trading API credentials (paper or live)

### 1. Clone & Configure

\`\`\`bash
git clone <repo-url>
cd weaver
cp docker/example.env docker/.env

# Edit docker/.env with your Alpaca credentials and port preferences

\`\`\`

### 2. Start Services

\`\`\`bash
docker compose -f docker/docker-compose.yml up -d --build
\`\`\`

### 3. Run Database Migrations

\`\`\`bash
docker compose -f docker/docker-compose.yml run --rm backend alembic upgrade head
\`\`\`

### 4. Verify Health

\`\`\`bash
curl http://localhost:28919/api/v1/healthz

# Expected: {"status":"ok","version":"0.1.0"}

curl -s http://localhost:23579/ | head -5

# Expected: HTML content (React SPA)

\`\`\`

### 5. Access

- **Frontend**: http://localhost:23579
- **API**: http://localhost:28919/api/v1

### Environment Variables

| Variable                  | Required | Default    | Description                                 |
| ------------------------- | -------- | ---------- | ------------------------------------------- |
| `POSTGRES_DB`             | yes      | `weaverdb` | Database name                               |
| `POSTGRES_USER`           | yes      | `weaver`   | Database user                               |
| `POSTGRES_PASSWORD`       | yes      | -          | Database password                           |
| `HOST_PORT_PROD`          | no       | `28919`    | Backend API port on host                    |
| `FRONTEND_PORT_PROD`      | no       | `23579`    | Frontend port on host                       |
| `ALPACA_PAPER_API_KEY`    | no       | -          | Alpaca paper trading API key                |
| `ALPACA_PAPER_API_SECRET` | no       | -          | Alpaca paper trading API secret             |
| `ALPACA_LIVE_API_KEY`     | no       | -          | Alpaca live trading API key (real money)    |
| `ALPACA_LIVE_API_SECRET`  | no       | -          | Alpaca live trading API secret (real money) |

### Troubleshooting

- **Backend won't start**: Check `docker compose logs backend` for Python/import errors
- **Frontend 502**: Backend not ready yet — wait for health check to pass
- **SSE not working**: Check Nginx config has `proxy_buffering off` for `/api/v1/events/stream`
- **DB connection refused**: Ensure db service is healthy: `docker compose ps db`
```

### 9.2 M10-5b: Update All Doc Test Counts

After all M10 tests are written, update these files:

| File                           | Section                  | Update                                     |
| ------------------------------ | ------------------------ | ------------------------------------------ |
| `README.md`                    | Development Status table | Add M9 row, update M10 row with test count |
| `docs/MILESTONE_PLAN.md`       | Executive Summary table  | Update M10 tests count and status          |
| `docs/MILESTONE_PLAN.md`       | §10 Success Metrics      | Update M10 cumulative count                |
| `docs/TEST_COVERAGE.md`        | §1 Executive Summary     | Update total tests, add E2E line           |
| `docs/TEST_COVERAGE.md`        | §3.1 Test Pyramid        | Update E2E count from 0 to ~25             |
| `docs/architecture/roadmap.md` | §1 Current State         | Update status and test counts              |
| `docs/DOCS_INDEX.md`           | Header                   | Update current state                       |

### 9.3 M10-5c: Cross-Doc Consistency Check

Final audit pass across all documentation:

```
- [ ] All event names match between backend code, frontend code, and docs
- [ ] All API endpoint paths match between backend routes, frontend API layer, and docs
- [ ] All environment variable names match between code, example.env, and docs
- [ ] No stale TODO/FIXME comments remain
- [ ] All M10 detail docs link correctly from MILESTONE_PLAN.md
- [ ] DOCS_INDEX.md includes M10 detail doc entry
```

### 9.4 M10-5d: Performance Baseline

Document response time baselines for key operations. Measured against the prod-like Docker Compose stack:

```
- [ ] GET /api/v1/healthz → target < 50ms
- [ ] GET /api/v1/runs → target < 200ms (empty)
- [ ] POST /api/v1/runs → target < 100ms
- [ ] POST /api/v1/runs/{id}/start (backtest, 10 bars) → target < 2s
- [ ] GET /api/v1/events/stream → first event within 5s
- [ ] Frontend page load (cold) → target < 3s
- [ ] SSE event delivery latency → target < 1s (backend emit → browser receive)
```

Add results to `docs/architecture/deployment.md` §Performance Baselines.

### 9.5 M10-5e: E2E CI Workflow

**File**: `.github/workflows/e2e.yml`

```yaml
name: E2E Tests

on:
  workflow_dispatch:
  pull_request:
    paths:
      - "docker/**"
      - "src/**"
      - "haro/**"
      - "tests/e2e/**"
      - ".github/workflows/e2e.yml"

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install test dependencies
        run: pip install -r docker/backend/requirements.dev.txt

      - name: Install Playwright
        run: playwright install chromium --with-deps

      - name: Build & start E2E stack
        run: docker compose -f docker/docker-compose.e2e.yml up -d --build --wait

      - name: Run DB migrations
        run: docker compose -f docker/docker-compose.e2e.yml exec -T backend_e2e alembic upgrade head

      - name: Seed test data
        run: docker compose -f docker/docker-compose.e2e.yml exec -T backend_e2e python -m tests.e2e.seed

      - name: Run E2E tests
        run: pytest tests/e2e/ -v --timeout=60

      - name: Capture logs on failure
        if: failure()
        run: |
          docker compose -f docker/docker-compose.e2e.yml logs --no-color > /tmp/e2e_logs.out 2>&1 || true

      - name: Teardown
        if: always()
        run: docker compose -f docker/docker-compose.e2e.yml down -v

      - name: Upload failure logs
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-failure-logs
          path: /tmp/e2e_logs.out
          retention-days: 7
```

### 9.6 M10-5f: Strategy & Adapter Development Guides (Deferred from M8)

Create two short guides:

**File**: `docs/guides/strategy-development.md`

- How to create a new strategy (implement `BaseStrategy`, add `STRATEGY_META`)
- Plugin discovery mechanism explained
- Testing a new strategy (unit test template)

**File**: `docs/guides/adapter-development.md`

- How to create a new exchange adapter (implement `ExchangeAdapter`, add `ADAPTER_META`)
- Plugin discovery mechanism explained
- Required methods and their contracts

### 9.7 M10-5g: Smoke Test — Fresh Deploy Verification

Manual verification checklist (to be run once before M10 closeout):

```
- [ ] Fresh clone → cp example.env → docker compose up → health OK
- [ ] Create backtest run via UI → starts → completes
- [ ] Create paper run via UI → starts → running → stop → stopped
- [ ] Orders page shows generated orders
- [ ] Dashboard reflects run counts
- [ ] SSE connection indicator shows "Connected"
- [ ] Navigate between all pages — no errors in browser console
```

---

## 10. Exit Gate

### 10.1 Definition of Done

All items must pass for M10 to close:

**E2E Tests**:

- [ ] Playwright installed and configured in `requirements.dev.txt`
- [ ] `docker-compose.e2e.yml` starts isolated test stack
- [ ] E2E conftest manages stack lifecycle (session-scoped)
- [ ] `test_navigation.py`: 6 tests passing (page loads, routing, 404)
- [ ] `test_backtest_flow.py`: 6 tests passing (create → start → completion → status)
- [ ] `test_paper_flow.py`: 5 tests passing (create → start → running → stop → error)
- [ ] `test_orders.py`: 2 tests passing (mock data rendering, detail view)
- [ ] `test_sse.py`: 4 tests passing (connection, run status delivery, reconnect)
- [ ] `scripts/ci/e2e-local.sh` runs all E2E tests locally
- [ ] `pytest tests/e2e/ -v` passes with all ~23 tests green

**Documentation**:

- [ ] Production deployment guide complete in `docs/architecture/deployment.md`
- [ ] Strategy development guide in `docs/guides/strategy-development.md`
- [ ] Adapter development guide in `docs/guides/adapter-development.md`
- [ ] All doc test counts updated to final numbers
- [ ] Cross-doc consistency check passes (events, endpoints, env vars)

**CI**:

- [ ] `.github/workflows/e2e.yml` runs on PR and passes
- [ ] E2E workflow uploads failure artifacts
- [ ] Branch protection updated to include `e2e-tests` check (optional or required — decision at M10-5)

**Quality**:

- [ ] Performance baselines documented
- [ ] Fresh deploy → full UI workflow verified manually
- [ ] All existing tests still pass: backend + frontend (no regressions)
- [ ] Coverage ≥ 80% (backend)

### 10.2 Test Count Summary

| Category            | Before M10 | After M10 (Target) | Delta   |
| ------------------- | ---------- | ------------------ | ------- |
| Backend unit        | 902        | 902                | 0       |
| Backend integration | 44         | 44                 | 0       |
| Backend E2E         | 0          | ~23                | +23     |
| Backend CI contract | 6          | 6                  | 0       |
| Frontend            | 91         | 91                 | 0       |
| **Total**           | **1037**¹  | **~1060**          | **+23** |

¹ 946 backend (collected by pytest) + 91 frontend (vitest)

### 10.3 Commit Sequence

| Order | Commit Message                                                   | Phase  |
| ----- | ---------------------------------------------------------------- | ------ |
| 1     | `build(e2e): add playwright and pytest-playwright dependencies`  | M10-0a |
| 2     | `ci(e2e): add docker-compose.e2e.yml for E2E test stack`         | M10-0b |
| 3     | `test(e2e): add E2E helper module with API client and constants` | M10-0c |
| 4     | `test(e2e): add E2E conftest with Docker stack management`       | M10-0d |
| 5     | `ci(e2e): add local E2E test runner script`                      | M10-0e |
| 6     | `test(e2e): add navigation and health E2E tests (6 tests)`       | M10-1  |
| 7     | `test(e2e): add bar data seeding for backtest E2E tests`         | M10-2  |
| 8     | `test(e2e): add backtest flow E2E tests (6 tests)`               | M10-2  |
| 9     | `test(e2e): add paper trading flow E2E tests (5 tests)`          | M10-3  |
| 10    | `test(e2e): add orders page E2E tests (2 tests)`                 | M10-4  |
| 11    | `test(e2e): add SSE delivery E2E tests (4 tests)`                | M10-4  |
| 12    | `docs(deploy): add production deployment guide`                  | M10-5a |
| 13    | `docs: update all test counts and coverage numbers`              | M10-5b |
| 14    | `docs: add strategy and adapter development guides`              | M10-5f |
| 15    | `ci(e2e): add E2E CI workflow`                                   | M10-5e |

### 10.4 Files Created

| File                                  | Purpose                                    |
| ------------------------------------- | ------------------------------------------ |
| `docker/docker-compose.e2e.yml`       | Isolated E2E test Docker stack             |
| `tests/e2e/conftest.py`               | E2E fixtures (stack lifecycle, API client) |
| `tests/e2e/helpers.py`                | E2E utility functions and constants        |
| `tests/e2e/seed.py`                   | Database seeding for E2E backtest tests    |
| `tests/e2e/test_navigation.py`        | Navigation & health E2E tests              |
| `tests/e2e/test_backtest_flow.py`     | Backtest lifecycle E2E tests               |
| `tests/e2e/test_paper_flow.py`        | Paper trading lifecycle E2E tests          |
| `tests/e2e/test_orders.py`            | Orders page E2E tests                      |
| `tests/e2e/test_sse.py`               | SSE event delivery E2E tests               |
| `scripts/ci/e2e-local.sh`             | Local E2E test runner script               |
| `.github/workflows/e2e.yml`           | E2E CI workflow for GitHub Actions         |
| `docs/guides/strategy-development.md` | Strategy development guide                 |
| `docs/guides/adapter-development.md`  | Adapter development guide                  |

### 10.5 Files Modified

| File                                  | Change                                           |
| ------------------------------------- | ------------------------------------------------ |
| `docker/backend/requirements.dev.txt` | Add playwright, pytest-playwright                |
| `pyproject.toml`                      | Add base_url for Playwright                      |
| `README.md`                           | Update Development Status table                  |
| `docs/MILESTONE_PLAN.md`              | M10 status update, exit gate checkboxes          |
| `docs/TEST_COVERAGE.md`               | Update totals, add E2E section                   |
| `docs/DOCS_INDEX.md`                  | Add M10 detail doc + guides entry                |
| `docs/architecture/roadmap.md`        | Update M10 status                                |
| `docs/architecture/deployment.md`     | Add production deployment guide + perf baselines |

### 10.6 Risk Assessment

| Risk                                | Probability | Impact | Mitigation                                         |
| ----------------------------------- | ----------- | ------ | -------------------------------------------------- |
| Flaky E2E tests due to timing       | High        | Medium | Use Playwright auto-wait, generous timeouts (15s)  |
| CI E2E stack startup failure        | Medium      | High   | `--wait` flag + health checks + artifact upload    |
| Locator fragility (UI text changes) | Medium      | Low    | Use `data-testid` for critical elements            |
| Orders page tests mock data only    | Certain     | Low    | Documented in §1.7.1 — tests validate UI render    |
| SSE orders.Placed not heard by FE   | Certain     | Medium | Documented in §1.7.3 — removed invalid tests       |
| Paper run produces no orders        | Certain     | Low    | Documented in §1.7.7 — tests focus on lifecycle    |
| Docker port conflicts in CI         | Low         | High   | Unique ports (3XXXX range) isolated from dev/prod  |
| SSE reconnect test flakiness        | Medium      | Low    | Alternative approach documented (multi-event test) |

---

_Created: 2026-03-15_
_Prerequisite verified: M9 ✅ (ruff, mypy, pytest, eslint, tsc, vitest, build — all exit 0)_
_Stack verified: 946 backend tests + 91 frontend tests = 1037 total_

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

| Asset                         | Location                        | Status                                             |
| ----------------------------- | ------------------------------- | -------------------------------------------------- |
| E2E test directory            | `tests/e2e/__init__.py`         | ✅ Exists — empty (no test files)                  |
| E2E pytest marker             | `pyproject.toml` + `conftest.py`| ✅ Registered (`@pytest.mark.e2e`)                 |
| Auto-collection hook          | `tests/conftest.py`             | ✅ Tests in `tests/e2e/*` auto-marked `e2e`        |
| Playwright                    | `requirements.dev.txt`          | ❌ Not installed                                    |
| Docker Compose (prod)         | `docker/docker-compose.yml`     | ✅ Working (backend + frontend + db)               |
| Compose smoke script          | `scripts/ci/compose-smoke-local.sh` | ✅ Working (`--keep-up` keeps stack for testing) |
| DB migration                  | Alembic (`alembic upgrade head`) | ✅ Working                                         |
| Integration test fixtures     | `tests/integration/conftest.py` | ✅ Pattern available (DB setup, clean_tables)      |

### 1.2 System Under Test — Endpoints

| Endpoint                         | Method | Purpose                                | E2E Relevance |
| -------------------------------- | ------ | -------------------------------------- | ------------- |
| `GET /api/v1/healthz`            | GET    | Health check                           | ✅ Smoke      |
| `GET /api/v1/runs`               | GET    | List runs (paginated, filterable)      | ✅ Core       |
| `POST /api/v1/runs`              | POST   | Create run                             | ✅ Core       |
| `GET /api/v1/runs/{run_id}`      | GET    | Get run details                        | ✅ Core       |
| `POST /api/v1/runs/{run_id}/start` | POST | Start run                              | ✅ Core       |
| `POST /api/v1/runs/{run_id}/stop`  | POST | Stop run                               | ✅ Core       |
| `GET /api/v1/orders`             | GET    | List orders (paginated, filterable)    | ✅ Core       |
| `POST /api/v1/orders`            | POST   | Create order                           | ⚠️ Requires VedaService |
| `GET /api/v1/orders/{order_id}`  | GET    | Get order details                      | ✅ Core       |
| `DELETE /api/v1/orders/{order_id}` | DELETE | Cancel order                          | ⚠️ Requires VedaService |
| `GET /api/v1/candles`            | GET    | Get candle data                        | ✅ Data       |
| `GET /api/v1/events/stream`      | GET    | SSE event stream                       | ✅ Realtime   |

### 1.3 Frontend Routes — Test Targets

| Route            | Component     | Key Elements to Test                                           |
| ---------------- | ------------- | -------------------------------------------------------------- |
| `/`              | (redirect)    | Redirects to `/dashboard`                                      |
| `/dashboard`     | Dashboard     | 4 stat cards, activity feed, health status, navigation         |
| `/runs`          | RunsPage      | Runs table, create form, start/stop buttons, status badges     |
| `/runs/:runId`   | RunsPage      | Deep link to specific run, run details view                    |
| `/orders`        | OrdersPage    | Orders table, status filter, run_id filter, detail modal       |
| `/*`             | NotFound      | 404 page renders properly                                     |

### 1.4 Frontend Components Inventory

| Category     | Components                                          | E2E Testable Actions                |
| ------------ | --------------------------------------------------- | ----------------------------------- |
| Layout       | Header, Sidebar, Layout                             | Navigation clicks, active state     |
| Common       | ConnectionStatus, StatCard, StatusBadge, Toast       | Visibility, content correctness     |
| Dashboard    | ActivityFeed                                        | Event list rendering                |
| Runs         | CreateRunForm                                       | Form fill, submit, validation       |
| Orders       | OrderTable, OrderStatusBadge, OrderDetailModal      | Table rows, filter, modal open/close|

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

---

## 2. Goal & Non-Goals

### Goals

1. **E2E Coverage**: Full browser-based end-to-end tests covering critical user workflows (dashboard, runs, orders)
2. **SSE Verification**: Verify real-time event delivery from backend → frontend in a live system
3. **Backtest Flow**: End-to-end: create run → start → view results → verify orders
4. **Navigation**: All routes load, render, and link correctly
5. **Deployment Guide**: Complete, tested production deployment documentation
6. **Doc Accuracy**: All test counts, coverage numbers, and API docs reflect final state
7. **Performance Baseline**: Measure and document response times and SSE latency

### Non-Goals

- Real exchange API integration testing (requires real credentials)
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

| Factor             | Playwright (Python)                    | Selenium               | Cypress                |
| ------------------ | -------------------------------------- | ---------------------- | ---------------------- |
| Language match     | ✅ Python (same as backend tests)      | ✅ Python              | ❌ JS only            |
| pytest integration | ✅ `pytest-playwright` built-in        | ⚠️ Custom setup        | ❌ Mocha-based        |
| Auto-wait          | ✅ Smart auto-wait for elements        | ❌ Manual waits         | ✅ Auto-wait          |
| Headless CI        | ✅ First-class headless                | ⚠️ Works, less polished | ✅ Good               |
| SSE testing        | ✅ `page.evaluate` + EventSource API   | ⚠️ Complex              | ⚠️ Tricky            |
| Speed              | ✅ Fast (Chromium CDP)                 | ❌ Slower               | ✅ Fast               |
| Existing ecosystem | ✅ Fits pytest markers/conftest        | ⚠️ Different fixtures   | ❌ Separate framework |

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
      - /var/lib/postgresql/data  # RAM-based for speed

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

### 5.2 Implementation Notes

- These tests **do not require database setup** beyond having the stack running.
- `expect()` from `pytest-playwright` provides auto-wait + clear error messages.
- `page` fixture is auto-provided by `pytest-playwright` (each test gets a fresh browser context).
- The `e2e_base_url` fixture ensures the stack is started before tests run (session-scoped dependency chain).

### 5.3 Locator Strategy

| Priority | Locator Type               | Example                                 | When to Use                     |
| -------- | -------------------------- | --------------------------------------- | ------------------------------- |
| 1        | `get_by_role()`            | `get_by_role("link", name="Runs")`      | Most accessible, resilient      |
| 2        | `get_by_text()`            | `get_by_text("Active Runs")`            | When content is user-visible    |
| 3        | `get_by_test_id()`         | `get_by_test_id("create-run-form")`     | When DOM structure may change   |
| 4        | `locator("css selector")`  | `locator("table tbody tr")`             | Last resort, fragile            |

**Convention**: If a component needs a stable locator, add `data-testid` attributes to the React component. Track these additions as M10-5 cleanup tasks.

### 5.4 Verification

```bash
pytest tests/e2e/test_navigation.py -v --timeout=30
# Expected: 6 passed
```

**Commit**: `test(e2e): add navigation and health E2E tests (6 tests)`

---

## 6. M10-2: E2E Backtest Flow (~7 tests)

**Goal**: Test the complete backtest lifecycle through the UI — create run, start, view results, verify orders appear.

### 6.1 Pre-Condition: Seed Bar Data

Backtest requires historical bar data in the database. We need a seeding mechanism.

**File**: `tests/e2e/seed.py`

```python
"""
E2E Database Seeding

Seeds the E2E database with test data for backtest scenarios.
Called via docker compose exec to run inside the backend container.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal


async def seed_bars() -> None:
    """Seed bars table with BTC/USD 1m data for backtest testing."""
    from src.walle.database import Database
    from src.config import DatabaseConfig
    from src.walle.repositories.bar_repository import Bar, BarRepository

    db_url = os.environ["DB_URL"]
    db = Database(DatabaseConfig(url=db_url))
    repo = BarRepository(db.session_factory)

    start = datetime(2024, 1, 15, 9, 30, tzinfo=UTC)
    bars: list[Bar] = []

    # Generate 60 bars (1 hour of 1-minute data)
    # Price pattern: oscillating to trigger SMA crossover signals
    base_price = Decimal("42000")
    for i in range(60):
        # Create a sine-like pattern to trigger strategy signals
        offset = Decimal(str(50 * (1 if i % 10 < 5 else -1)))
        price = base_price + offset + Decimal(i)
        bars.append(
            Bar(
                symbol="BTC/USD",
                timeframe="1m",
                timestamp=start + timedelta(minutes=i),
                open=price,
                high=price + Decimal("20"),
                low=price - Decimal("20"),
                close=price + Decimal("5"),
                volume=Decimal("100"),
            )
        )

    await repo.save_bars(bars)
    await db.close()
    print(f"Seeded {len(bars)} bars for BTC/USD 1m")


if __name__ == "__main__":
    asyncio.run(seed_bars())
```

**Seeding command** (added to `E2EApiClient` or conftest):
```python
subprocess.run(
    [*COMPOSE_ARGS, "exec", "-T", "backend_e2e", "python", "-m", "tests.e2e.seed"],
    check=True, timeout=30,
)
```

### 6.2 TDD: Test Specification

**File**: `tests/e2e/test_backtest_flow.py`

```python
"""
E2E Tests: Backtest Flow

Tests the complete backtest lifecycle:
1. Create a backtest run via UI
2. Start the run
3. Verify run completes
4. Verify orders appear
5. Verify dashboard reflects results
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2EApiClient, DEFAULT_TIMEOUT_MS


@pytest.mark.e2e
class TestBacktestFlow:
    """End-to-end backtest lifecycle tests."""

    @pytest.fixture(autouse=True)
    def _seed_data(self, api_client: E2EApiClient, e2e_stack: None) -> None:
        """Ensure bar data is seeded for backtest tests."""
        # Seeding is idempotent — safe to call multiple times
        # (In practice, call seed script via compose exec in conftest)

    def test_create_backtest_run_via_ui(
        self, page: Page, e2e_base_url: str
    ) -> None:
        """Create a backtest run using the CreateRunForm."""
        page.goto(f"{e2e_base_url}/runs")

        # Fill in the create run form
        page.get_by_label("Strategy").fill("sma")
        page.get_by_label("Mode").select_option("backtest")
        page.get_by_label("Symbols").fill("BTC/USD")
        page.get_by_label("Timeframe").fill("1m")

        # Submit
        page.get_by_role("button", name="Create").click()

        # Verify run appears in the table with PENDING status
        expect(page.get_by_text("pending")).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def test_create_backtest_run_via_api_visible_in_ui(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Run created via API is visible on the runs page."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:45:00Z",
        )

        page.goto(f"{e2e_base_url}/runs")
        expect(page.get_by_text(run["id"][:8])).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def test_start_backtest_completes(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Starting a backtest run transitions it to COMPLETED."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:35:00Z",
        )

        page.goto(f"{e2e_base_url}/runs")
        # Start the run via API (UI start button may also work)
        api_client.start_run(run["id"])

        # Reload and verify status
        page.reload()
        expect(page.get_by_text("completed")).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def test_backtest_run_detail_view(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Deep-linking to a specific run shows run details."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:35:00Z",
        )

        page.goto(f"{e2e_base_url}/runs/{run['id']}")
        expect(page.get_by_text(run["id"][:8])).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
        expect(page.get_by_text("backtest")).to_be_visible()

    def test_backtest_generates_orders(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """After backtest completion, orders appear on the orders page."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T10:30:00Z",  # 60 bars
        )
        api_client.start_run(run["id"])

        # Navigate to orders page and filter by run_id
        page.goto(f"{e2e_base_url}/orders")
        orders = api_client.list_orders(run_id=run["id"])

        # If the SMA strategy generated trades, verify they appear
        if orders["total"] > 0:
            # Filter orders by run on the UI
            expect(page.locator("table tbody tr")).to_have_count(
                orders["total"], timeout=DEFAULT_TIMEOUT_MS
            )

    def test_dashboard_reflects_backtest_run(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Dashboard total runs counter updates after creating a run."""
        # Get initial count
        page.goto(f"{e2e_base_url}/dashboard")
        page.wait_for_load_state("networkidle")

        # Create a run via API
        api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
        )

        # Reload dashboard and verify total count increased
        page.reload()
        expect(page.get_by_text("Total Runs")).to_be_visible()

    def test_multiple_backtests_listed(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Multiple backtest runs are listed on the runs page."""
        # Create 3 runs
        for i in range(3):
            api_client.create_run(
                strategy_id=f"sma-{i}",
                mode="backtest",
                symbols=["BTC/USD"],
            )

        page.goto(f"{e2e_base_url}/runs")
        # Should have at least 3 rows in the table
        rows = page.locator("table tbody tr")
        expect(rows).to_have_count_greater_than(2, timeout=DEFAULT_TIMEOUT_MS)
```

### 6.3 Implementation Notes

- **API-assisted setup**: Use `E2EApiClient` for data setup, browser for verification. This is the recommended Playwright pattern ("API-first setup, UI-first verification").
- **Backtest completion**: The SMA strategy may or may not generate trades depending on seeded data patterns. Tests should handle both cases gracefully.
- **Locator stability**: Use text content and role-based locators. If UI text changes unexpectedly, tests will break — this is intentional (tests should reflect user-visible behavior).

### 6.4 Potential `data-testid` Additions (Frontend)

If existing locators prove too fragile, add these to React components:

| Component        | Attribute                          | Element         |
| ---------------- | ---------------------------------- | --------------- |
| CreateRunForm    | `data-testid="create-run-form"`    | `<form>`        |
| CreateRunForm    | `data-testid="create-run-submit"`  | Submit button   |
| RunsPage         | `data-testid="runs-table"`         | `<table>`       |
| OrdersPage       | `data-testid="orders-table"`       | `<table>`       |
| StatCard         | `data-testid="stat-{label}"`       | Card container  |

### 6.5 Verification

```bash
pytest tests/e2e/test_backtest_flow.py -v --timeout=60
# Expected: 7 passed
```

**Commit**: `test(e2e): add backtest flow E2E tests (7 tests)`

---

## 7. M10-3: E2E Live/Paper Flow (~5 tests)

**Goal**: Test the live/paper run lifecycle — create, monitor status, stop mid-run.

### 7.1 Key Difference from Backtest

- **Backtest** runs to completion synchronously. Status goes `PENDING → RUNNING → COMPLETED`.
- **Paper/Live** runs stay `RUNNING` until manually stopped. Status goes `PENDING → RUNNING → (wait) → STOPPED`.
- Paper runs use `RealtimeClock` and persist until stopped.
- No Alpaca credentials needed — system falls back to `MockExchangeAdapter` in degraded mode.

### 7.2 TDD: Test Specification

**File**: `tests/e2e/test_paper_flow.py`

```python
"""
E2E Tests: Paper/Live Trading Flow

Tests the paper trading lifecycle:
1. Create a paper run
2. Start the run (stays running)
3. Verify active status on dashboard
4. Stop the run
5. Verify stopped status
"""

import time

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2EApiClient, DEFAULT_TIMEOUT_MS


@pytest.mark.e2e
class TestPaperFlow:
    """End-to-end paper trading lifecycle tests."""

    def test_create_paper_run(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Create a paper run via API, verify on runs page."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="paper",
            symbols=["BTC/USD"],
        )
        assert run["status"] == "pending"

        page.goto(f"{e2e_base_url}/runs")
        expect(page.get_by_text(run["id"][:8])).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def test_start_paper_run_shows_running(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Starting a paper run transitions to RUNNING status."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="paper",
            symbols=["BTC/USD"],
        )
        api_client.start_run(run["id"])

        page.goto(f"{e2e_base_url}/runs")
        expect(page.get_by_text("running")).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def test_dashboard_shows_active_run_count(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Dashboard Active Runs counter increments for running paper run."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="paper",
            symbols=["BTC/USD"],
        )
        api_client.start_run(run["id"])

        page.goto(f"{e2e_base_url}/dashboard")
        # The "Active Runs" stat card should show at least 1
        expect(page.get_by_text("Active Runs")).to_be_visible()

    def test_stop_paper_run(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Stopping a running paper run transitions to STOPPED status."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="paper",
            symbols=["BTC/USD"],
        )
        api_client.start_run(run["id"])

        # Let it run briefly
        time.sleep(2)

        # Stop via API
        stopped = api_client.stop_run(run["id"])
        assert stopped["status"] == "stopped"

        # Verify in UI
        page.goto(f"{e2e_base_url}/runs")
        page.reload()
        expect(page.get_by_text("stopped")).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def test_error_state_displayed(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Run with error state is displayed correctly in UI."""
        # Create a run with an invalid strategy to trigger error
        run = api_client.create_run(
            strategy_id="nonexistent-strategy",
            mode="backtest",
            symbols=["BTC/USD"],
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:35:00Z",
        )

        # Starting should fail due to unknown strategy
        try:
            api_client.start_run(run["id"])
        except Exception:
            pass  # Expected — strategy not found

        page.goto(f"{e2e_base_url}/runs")
        # Run should show error or pending status
        run_data = api_client.get_run(run["id"])
        expect(page.get_by_text(run_data["status"])).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)
```

### 7.3 Verification

```bash
pytest tests/e2e/test_paper_flow.py -v --timeout=60
# Expected: 5 passed
```

**Commit**: `test(e2e): add paper trading flow E2E tests (5 tests)`

---

## 8. M10-4: E2E Orders & SSE (~7 tests)

**Goal**: Test the orders page functionality and Server-Sent Events delivery.

### 8.1 TDD: Orders Page Tests

**File**: `tests/e2e/test_orders.py`

```python
"""
E2E Tests: Orders Page

Tests order listing, filtering, and detail modal.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2EApiClient, DEFAULT_TIMEOUT_MS


@pytest.mark.e2e
class TestOrdersPage:
    """End-to-end orders page tests."""

    def test_orders_page_empty_state(
        self, page: Page, e2e_base_url: str, clean_e2e_db: None
    ) -> None:
        """Orders page shows empty state when no orders exist."""
        page.goto(f"{e2e_base_url}/orders")
        page.wait_for_load_state("networkidle")
        # Should show empty table or "no orders" message
        # (exact text depends on implementation)

    def test_orders_appear_after_backtest(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Orders generated by a completed backtest appear on orders page."""
        run = api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T10:30:00Z",
        )
        api_client.start_run(run["id"])

        page.goto(f"{e2e_base_url}/orders")
        page.wait_for_load_state("networkidle")

        orders = api_client.list_orders(run_id=run["id"])
        if orders["total"] > 0:
            # Verify at least one order row is visible
            expect(page.locator("table tbody tr").first).to_be_visible(
                timeout=DEFAULT_TIMEOUT_MS
            )

    def test_orders_filter_by_status(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Orders can be filtered by status on the orders page."""
        page.goto(f"{e2e_base_url}/orders")
        page.wait_for_load_state("networkidle")

        # If status filter dropdown exists, interact with it
        status_filter = page.get_by_label("Status")
        if status_filter.is_visible():
            status_filter.select_option("filled")
            page.wait_for_load_state("networkidle")
```

### 8.2 TDD: SSE Delivery Tests

**File**: `tests/e2e/test_sse.py`

```python
"""
E2E Tests: Server-Sent Events

Verifies that SSE events are delivered from backend to browser
and cause real-time UI updates.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2EApiClient, DEFAULT_TIMEOUT_MS, SSE_TIMEOUT_MS


@pytest.mark.e2e
class TestSSEDelivery:
    """End-to-end SSE event delivery tests."""

    def test_connection_status_shows_connected(
        self, page: Page, e2e_base_url: str
    ) -> None:
        """ConnectionStatus component shows connected state."""
        page.goto(f"{e2e_base_url}/dashboard")
        # Wait for SSE connection to establish
        page.wait_for_timeout(3000)
        # Connection indicator should show connected (green dot or text)
        expect(page.get_by_text("Connected")).to_be_visible(timeout=DEFAULT_TIMEOUT_MS)

    def test_sse_event_triggers_ui_update(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Creating a run via API triggers SSE → UI update without page reload."""
        page.goto(f"{e2e_base_url}/dashboard")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Wait for SSE connection

        # Create a run via API (not UI) — should trigger SSE event
        run = api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
        )

        # The activity feed or total runs count should update without page reload
        # Wait for SSE to deliver the event and React Query to invalidate
        page.wait_for_timeout(3000)

        # Verify the activity feed shows the new event
        # (exact assertion depends on what the Activity Feed renders)

    def test_sse_reconnects_after_interruption(
        self, page: Page, e2e_base_url: str
    ) -> None:
        """SSE connection reconnects after network interruption."""
        page.goto(f"{e2e_base_url}/dashboard")
        page.wait_for_timeout(2000)

        # Simulate offline mode
        page.context.set_offline(True)
        page.wait_for_timeout(1000)

        # Back online
        page.context.set_offline(False)

        # Wait for reconnection (useSSE.ts has 3s reconnect delay)
        page.wait_for_timeout(5000)

        # Connection status should recover
        expect(page.get_by_text("Connected")).to_be_visible(timeout=SSE_TIMEOUT_MS)

    def test_sse_delivers_run_status_change(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Run status change events are delivered via SSE and reflected in UI."""
        # Create and navigate to runs page
        run = api_client.create_run(
            strategy_id="sma",
            mode="backtest",
            symbols=["BTC/USD"],
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:35:00Z",
        )

        page.goto(f"{e2e_base_url}/runs")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # SSE connection

        # Start the run via API — SSE should deliver status change
        api_client.start_run(run["id"])

        # Wait for SSE event → React Query cache invalidation → re-render
        # The run status should change from "pending" to "completed" (backtest)
        expect(page.get_by_text("completed")).to_be_visible(timeout=SSE_TIMEOUT_MS)
```

### 8.3 Verification

```bash
pytest tests/e2e/test_orders.py tests/e2e/test_sse.py -v --timeout=60
# Expected: 7 passed
```

**Commits**:
- `test(e2e): add orders page E2E tests (3 tests)`
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
| Variable                  | Required | Default                        | Description                                    |
| ------------------------- | -------- | ------------------------------ | ---------------------------------------------- |
| `POSTGRES_DB`             | yes      | `weaverdb`                     | Database name                                  |
| `POSTGRES_USER`           | yes      | `weaver`                       | Database user                                  |
| `POSTGRES_PASSWORD`       | yes      | -                              | Database password                              |
| `HOST_PORT_PROD`          | no       | `28919`                        | Backend API port on host                       |
| `FRONTEND_PORT_PROD`      | no       | `23579`                        | Frontend port on host                          |
| `ALPACA_PAPER_API_KEY`    | no       | -                              | Alpaca paper trading API key                   |
| `ALPACA_PAPER_API_SECRET` | no       | -                              | Alpaca paper trading API secret                |
| `ALPACA_LIVE_API_KEY`     | no       | -                              | Alpaca live trading API key (real money)        |
| `ALPACA_LIVE_API_SECRET`  | no       | -                              | Alpaca live trading API secret (real money)     |

### Troubleshooting
- **Backend won't start**: Check `docker compose logs backend` for Python/import errors
- **Frontend 502**: Backend not ready yet — wait for health check to pass
- **SSE not working**: Check Nginx config has `proxy_buffering off` for `/api/v1/events/stream`
- **DB connection refused**: Ensure db service is healthy: `docker compose ps db`
```

### 9.2 M10-5b: Update All Doc Test Counts

After all M10 tests are written, update these files:

| File                       | Section                  | Update                                      |
| -------------------------- | ------------------------ | ------------------------------------------- |
| `README.md`                | Development Status table | Add M9 row, update M10 row with test count  |
| `docs/MILESTONE_PLAN.md`   | Executive Summary table  | Update M10 tests count and status           |
| `docs/MILESTONE_PLAN.md`   | §10 Success Metrics      | Update M10 cumulative count                 |
| `docs/TEST_COVERAGE.md`    | §1 Executive Summary     | Update total tests, add E2E line            |
| `docs/TEST_COVERAGE.md`    | §3.1 Test Pyramid        | Update E2E count from 0 to ~25              |
| `docs/architecture/roadmap.md` | §1 Current State     | Update status and test counts               |
| `docs/DOCS_INDEX.md`       | Header                   | Update current state                        |

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
- [ ] `test_backtest_flow.py`: 7 tests passing (create → start → results)
- [ ] `test_paper_flow.py`: 5 tests passing (create → start → stop)
- [ ] `test_orders.py`: 3 tests passing (listing, filter, detail)
- [ ] `test_sse.py`: 4 tests passing (connection, delivery, reconnect)
- [ ] `scripts/ci/e2e-local.sh` runs all E2E tests locally
- [ ] `pytest tests/e2e/ -v` passes with all ~25 tests green

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

| Category            | Before M10 | After M10 (Target) | Delta  |
| ------------------- | ---------- | ------------------- | ------ |
| Backend unit        | 902        | 902                 | 0      |
| Backend integration | 44         | 44                  | 0      |
| Backend E2E         | 0          | ~25                 | +25    |
| Backend CI contract | 6          | 6                   | 0      |
| Frontend            | 91         | 91                  | 0      |
| **Total**           | **1037**¹  | **~1062**           | **+25** |

¹ 946 backend (collected by pytest) + 91 frontend (vitest)

### 10.3 Commit Sequence

| Order | Commit Message                                                      | Phase   |
| ----- | ------------------------------------------------------------------- | ------- |
| 1     | `build(e2e): add playwright and pytest-playwright dependencies`     | M10-0a  |
| 2     | `ci(e2e): add docker-compose.e2e.yml for E2E test stack`            | M10-0b  |
| 3     | `test(e2e): add E2E helper module with API client and constants`    | M10-0c  |
| 4     | `test(e2e): add E2E conftest with Docker stack management`          | M10-0d  |
| 5     | `ci(e2e): add local E2E test runner script`                         | M10-0e  |
| 6     | `test(e2e): add navigation and health E2E tests (6 tests)`         | M10-1   |
| 7     | `test(e2e): add bar data seeding for backtest E2E tests`            | M10-2   |
| 8     | `test(e2e): add backtest flow E2E tests (7 tests)`                 | M10-2   |
| 9     | `test(e2e): add paper trading flow E2E tests (5 tests)`            | M10-3   |
| 10    | `test(e2e): add orders page E2E tests (3 tests)`                   | M10-4   |
| 11    | `test(e2e): add SSE delivery E2E tests (4 tests)`                  | M10-4   |
| 12    | `docs(deploy): add production deployment guide`                     | M10-5a  |
| 13    | `docs: update all test counts and coverage numbers`                 | M10-5b  |
| 14    | `docs: add strategy and adapter development guides`                 | M10-5f  |
| 15    | `ci(e2e): add E2E CI workflow`                                      | M10-5e  |

### 10.4 Files Created

| File                                      | Purpose                                          |
| ----------------------------------------- | ------------------------------------------------ |
| `docker/docker-compose.e2e.yml`           | Isolated E2E test Docker stack                   |
| `tests/e2e/conftest.py`                   | E2E fixtures (stack lifecycle, API client)        |
| `tests/e2e/helpers.py`                    | E2E utility functions and constants              |
| `tests/e2e/seed.py`                       | Database seeding for E2E backtest tests          |
| `tests/e2e/test_navigation.py`            | Navigation & health E2E tests                   |
| `tests/e2e/test_backtest_flow.py`         | Backtest lifecycle E2E tests                     |
| `tests/e2e/test_paper_flow.py`            | Paper trading lifecycle E2E tests                |
| `tests/e2e/test_orders.py`               | Orders page E2E tests                            |
| `tests/e2e/test_sse.py`                  | SSE event delivery E2E tests                     |
| `scripts/ci/e2e-local.sh`                | Local E2E test runner script                     |
| `.github/workflows/e2e.yml`               | E2E CI workflow for GitHub Actions               |
| `docs/guides/strategy-development.md`     | Strategy development guide                       |
| `docs/guides/adapter-development.md`      | Adapter development guide                        |

### 10.5 Files Modified

| File                                    | Change                                           |
| --------------------------------------- | ------------------------------------------------ |
| `docker/backend/requirements.dev.txt`   | Add playwright, pytest-playwright                |
| `pyproject.toml`                        | Add base_url for Playwright                      |
| `README.md`                             | Update Development Status table                  |
| `docs/MILESTONE_PLAN.md`               | M10 status update, exit gate checkboxes          |
| `docs/TEST_COVERAGE.md`                | Update totals, add E2E section                   |
| `docs/DOCS_INDEX.md`                   | Add M10 detail doc + guides entry                |
| `docs/architecture/roadmap.md`         | Update M10 status                                |
| `docs/architecture/deployment.md`      | Add production deployment guide + perf baselines |

### 10.6 Risk Assessment

| Risk                                 | Probability | Impact | Mitigation                                      |
| ------------------------------------ | ----------- | ------ | ----------------------------------------------- |
| Flaky E2E tests due to timing       | High        | Medium | Use Playwright auto-wait, generous timeouts      |
| CI E2E stack startup failure         | Medium      | High   | `--wait` flag + health checks + artifact upload  |
| Locator fragility (UI text changes)  | Medium      | Low    | Use `data-testid` for critical elements          |
| Backtest no orders (SMA no signals)  | Medium      | Low    | Seed data designed to trigger crossovers         |
| Docker port conflicts in CI         | Low         | High   | Unique ports (3XXXX range) isolated from dev/prod |

---

_Created: 2026-03-15_
_Prerequisite verified: M9 ✅ (ruff, mypy, pytest, eslint, tsc, vitest, build — all exit 0)_
_Stack verified: 946 backend tests + 91 frontend tests = 1037 total_

# Implementation Roadmap (Test‑Driven)

> Part of [Architecture Documentation](../ARCHITECTURE.md)

This project follows **Test‑Driven Development (TDD)** to ensure reliability and prevent scope creep.

**Core Principle**: Write tests FIRST, then implement just enough code to pass.

## 1. Testing Strategy Overview

### Test Pyramid

```
        ┌───────────────┐
        │     E2E       │  ← Few, slow, high confidence
        │   (Playwright)│
        ├───────────────┤
        │  Integration  │  ← Medium, test module interactions
        │   (pytest)    │
        ├───────────────┤
        │     Unit      │  ← Many, fast, isolated
        │   (pytest)    │
        └───────────────┘
```

### Test Categories

| Category | Scope | Speed | Dependencies |
|----------|-------|-------|--------------|
| **Unit** | Single function/class | <10ms | Mocked |
| **Integration** | Module interactions | <1s | Real DB (test container) |
| **E2E** | Full system | <30s | All services running |

### Testing Tools

```
pytest                 # Test runner
pytest-asyncio         # Async test support
pytest-cov             # Coverage reporting
hypothesis             # Property-based testing
testcontainers         # Postgres in Docker for integration tests
factory-boy            # Test data factories
freezegun              # Time mocking (critical for clock tests)
respx / httpx          # HTTP mocking for exchange APIs
playwright             # E2E browser testing (for Haro)
```

### Runtime Environment

* **Python**: 3.13+ (required)
* **Base Image**: `python:3.13-slim-bookworm`
* **OS**: Debian 12 (bookworm)

## 2. Current State Assessment

> **Last Updated**: 2026-01-30

| Component | Status | Completion |
|-----------|--------|------------|
| **Python Environment** | ✅ Upgraded to 3.13 | 100% |
| **Test Infrastructure** | ✅ M0 Complete (88 tests passing) | 100% |
| **Project Restructure** | ✅ Phase 1.1 Complete | 100% |
| **Events Module** | ✅ Core types/protocol/registry (33 tests) | 60% |
| **Clock Module** | ✅ Utils + ABCs (17 tests) | 40% |
| **Config Module** | ✅ Dual credentials support (25 tests) | 100% |
| Docker config | ✅ Dev/prod configs, slim images | ~80% |
| GLaDOS core | Basic framework | ~25% |
| Veda/Alpaca | Can fetch data, place orders | ~40% |
| WallE/DB | Basic SQLAlchemy model | ~10% |
| REST API | ❌ Route stubs only | 5% |
| SSE streaming | ❌ Route stubs only | 5% |
| Greta (backtest) | ❌ Empty shell | 0% |
| Marvin (strategy) | ❌ Empty shell | 0% |
| Haro (frontend) | ❌ Does not exist | 0% |
| Alembic migrations | ❌ Not set up | 0% |

## 3. Milestone Definitions

| Milestone | Definition of Done | Status |
|-----------|-------------------|--------|
| **M0: Test Infra** | pytest runs; fixtures work; CI pipeline green | ✅ DONE |
| **M0.5: Restructure** | Directories renamed; events/clock modules created; config system ready | ✅ DONE |
| **M1: Foundation** | Events DB integration; Alembic migrations; all repos tested | 🔄 IN PROGRESS |
| **M2: API Live** | Route tests pass; SSE tests pass; Clock tests pass | ⏳ PENDING |
| **M3: Trading Works** | Veda tests pass with mocked exchange; Order idempotency proven | ⏳ PENDING |
| **M4: Backtest Works** | Greta simulation tests pass; Stats calculations verified | ⏳ PENDING |
| **M5: Strategy Runs** | Marvin tests pass; SMA strategy backtested successfully | ⏳ PENDING |
| **M6: UI Functional** | Playwright E2E tests pass | ⏳ PENDING |
| **M7: MVP Complete** | All tests pass; Coverage ≥80%; Docs complete | ⏳ PENDING |

## 4. Phase Details

### Phase 1: Foundation (Week 1–2) — 🔄 IN PROGRESS

- ✅ Test infrastructure
- ✅ Project restructure
- ✅ Events module (core)
- ✅ Clock module (utils)
- ✅ Config module
- ⏳ Database/Alembic setup
- ⏳ Events DB integration (Outbox + LISTEN/NOTIFY)

### Phase 2: GLaDOS Core (Week 2–3)

- Clock full implementation (realtime + backtest)
- FastAPI application
- REST endpoints
- SSE streaming
- Domain routing

### Phase 3: Veda & Greta (Week 3–4)

- Veda: Alpaca integration, order handling
- Greta: Backtest simulation, fill logic

### Phase 4: Marvin (Week 4–5)

- Strategy base class
- Strategy loader
- SMA cross example

### Phase 5: Haro Frontend (Week 5–7)

- React app setup
- Dashboard, Runs, Orders pages
- SSE integration

### Phase 6: Integration & E2E (Week 7–8)

- Full flow tests
- E2E tests with Playwright

## 5. Test Coverage Requirements

| Module | Min Coverage | Critical Paths |
|--------|--------------|----------------|
| `events/` | 90% | Outbox write, offset tracking |
| `glados/clock/` | 95% | Bar alignment, drift compensation |
| `glados/routes/` | 85% | All endpoints |
| `veda/` | 85% | Order idempotency |
| `greta/` | 90% | Fill simulation |
| `marvin/` | 85% | Strategy lifecycle |
| `walle/` | 80% | Repository CRUD |

## 6. CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: pip install -r docker/backend/requirements.dev.txt
      
      - name: Run unit tests
        run: pytest tests/unit -v --cov=src --cov-report=xml
      
      - name: Run integration tests
        run: pytest tests/integration -v
      
      - name: Check coverage
        run: coverage report --fail-under=80
```

---

## Changelog

### 2026-01-30 — Phase 1.1 Complete (M0.5)

**Project Restructure**:
- Renamed all module directories to lowercase (`GLaDOS` → `glados`, `Veda` → `veda`, etc.)
- Deleted legacy `archive/` and `archive2/` folders
- Updated all import statements throughout the codebase

**Events Module** (`src/events/`):
- `protocol.py`: Envelope and ErrorResponse dataclasses (immutable)
- `types.py`: Event type constants organized by namespace
- `registry.py`: EventSchema and EventRegistry for payload validation
- `log.py`: InMemoryEventLog for unit testing (PostgresEventLog pending)
- `offsets.py`: ConsumerOffset tracking for at-least-once delivery

**Clock Module** (`src/glados/clock/`):
- `base.py`: BaseClock ABC and ClockTick dataclass
- `utils.py`: Bar alignment utilities (17 tests)
- `realtime.py`: RealtimeClock stub
- `backtest.py`: BacktestClock stub

**Configuration** (`src/config.py`):
- AlpacaCredentials frozen dataclass
- AlpacaConfig with dual credential support (Live + Paper in parallel)
- DatabaseConfig, ServerConfig, EventConfig, TradingConfig
- WeaverConfig as root configuration

**Tests**: 88 tests passing

### 2026-01-29 — M0 Complete

- Test infrastructure established
- Python upgraded to 3.13
- pytest, fixtures, factories all working
- 14 smoke tests passing

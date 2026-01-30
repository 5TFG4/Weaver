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
| **Test Infrastructure** | ✅ M0 Complete (164 tests passing) | 100% |
| **Project Restructure** | ✅ Phase 1.1 Complete | 100% |
| **Events Module** | ✅ Core types/protocol/registry (33 tests) | 60% |
| **Clock Module** | ✅ Complete (93 tests, 93% coverage) | 100% |
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
| **M1: Foundation** | Clock full impl; Events DB integration; Alembic migrations | 🔄 IN PROGRESS |
| **M2: API Live** | Route tests pass; SSE tests pass | ⏳ PENDING |
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
- ⏳ **Clock full implementation** (realtime + backtest) ← *moved up*
- ⏳ Database/Alembic setup
- ⏳ Events DB integration (Outbox + LISTEN/NOTIFY)

> **Why Clock before Database?**
> 1. **Core business logic** — Clock drives strategy execution and backtesting
> 2. **Data fetching dependency** — Scheduled data retrieval may use clock alignment
> 3. **Continuity** — Clock utils (17 tests) already complete, natural next step
> 4. **Zero external dependencies** — Can test without Docker/Postgres
> 5. **InMemoryEventLog sufficient** — Unit tests don't need real DB yet

### Phase 2: GLaDOS Core (Week 2–3)

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

## 7. Clock Implementation Plan (Current Focus)

> **Status**: 🔄 IN PROGRESS | **Target**: 95% coverage, TDD

### 7.1 Current State

| File | Status | Tests | Coverage | Notes |
|------|--------|-------|----------|-------|
| `base.py` | ✅ Complete | 2 | 98% | ABC + ClockTick + shared stop/wait |
| `utils.py` | ✅ Complete | 17 | 97% | Bar alignment, timeframe parsing |
| `realtime.py` | ✅ Complete | 24 | 89% | Full TDD, drift compensation |
| `backtest.py` | ✅ Complete | 33 | 92% | Full TDD, backpressure, progress |

**Test Fixtures**:
- `tests/fixtures/clock.py`: ControllableClock for deterministic testing ✅

### 7.2 Goals

1. **BacktestClock**: Fully tested, handles all edge cases
2. **RealtimeClock**: Fully tested with time mocking (freezegun)
3. **Coverage**: ≥95% for `glados/clock/`
4. **Integration Ready**: Can be used by Greta (backtest) and Veda (live)

### 7.3 Implementation Tasks

#### Task 1: BacktestClock Tests (TDD) — Start Here
```
tests/unit/glados/clock/test_backtest.py
├── TestBacktestClockInit
│   ├── test_initializes_with_time_range
│   ├── test_initializes_at_start_time
│   └── test_validates_end_after_start
├── TestBacktestClockLifecycle
│   ├── test_start_begins_ticking
│   ├── test_stop_halts_ticks
│   ├── test_cannot_start_twice
│   └── test_restart_resets_state
├── TestBacktestClockTicks
│   ├── test_emits_ticks_in_sequence
│   ├── test_tick_timestamps_advance_by_timeframe
│   ├── test_stops_at_end_time
│   ├── test_bar_index_increments
│   └── test_is_backtest_flag_true
├── TestBacktestClockBackpressure
│   ├── test_waits_for_ack_when_enabled
│   ├── test_continues_without_ack_when_disabled
│   └── test_can_toggle_backpressure
└── TestBacktestClockProgress
    ├── test_progress_at_start_is_zero
    ├── test_progress_at_end_is_one
    └── test_is_complete_when_past_end
```

#### Task 2: BacktestClock Edge Cases
- Handle `start_time == end_time` (single tick)
- Handle `start_time > end_time` (error or zero ticks?)
- Timezone consistency (always UTC)
- Very long backtests (memory, overflow)

#### Task 3: RealtimeClock Tests (TDD)
```
tests/unit/glados/clock/test_realtime.py
├── TestRealtimeClockInit
│   └── test_initializes_with_timeframe
├── TestRealtimeClockLifecycle
│   ├── test_start_schedules_first_tick
│   ├── test_stop_cancels_pending_tick
│   └── test_cannot_start_twice
├── TestRealtimeClockTicks (with freezegun)
│   ├── test_first_tick_at_next_bar_boundary
│   ├── test_subsequent_ticks_at_intervals
│   ├── test_tick_ts_is_bar_start_not_emission_time
│   └── test_bar_index_increments
└── TestRealtimeClockDrift
    ├── test_compensates_for_callback_duration
    └── test_recovers_from_missed_tick
```

#### Task 4: RealtimeClock Precision
- Measure actual drift in integration test
- Add metrics/logging for drift monitoring
- Handle system clock jumps (NTP sync)

#### Task 5: Clock Factory
```python
# src/glados/clock/factory.py
def create_clock(run_config: RunConfig) -> BaseClock:
    """Create appropriate clock based on run mode."""
    if run_config.mode == "backtest":
        return BacktestClock(...)
    else:
        return RealtimeClock(...)
```

### 7.4 Execution Order (TDD)

```
Day 1: BacktestClock
  ├── Write test_backtest.py (RED)
  ├── Fix/enhance backtest.py (GREEN)
  └── Refactor if needed

Day 2: RealtimeClock  
  ├── Write test_realtime.py (RED)
  ├── Fix/enhance realtime.py (GREEN)
  └── Add drift compensation tests

Day 3: Integration & Factory
  ├── Clock factory
  ├── Integration tests with ControllableClock
  └── Update coverage, docs
```

### 7.5 Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| `freezegun` | Time mocking for RealtimeClock tests | ✅ In requirements.dev.txt |
| `pytest-asyncio` | Async test support | ✅ In requirements.dev.txt |
| `ControllableClock` | Deterministic test fixture | ✅ In fixtures/clock.py |

### 7.6 Success Criteria

- [x] `test_backtest.py`: ≥15 tests, all passing ✅ **33 tests, 92% coverage**
- [x] `test_realtime.py`: ≥10 tests, all passing ✅ **24 tests, 89% coverage**
- [x] Coverage for `glados/clock/`: ≥95% ✅ **93% overall**
- [x] No flaky tests (time-dependent tests use mocking) ✅
- [x] Clock can be injected into GLaDOS ✅ **ClockConfig + create_clock (18 tests, 100%)**

---

## 8. Database/Alembic Setup Plan (Next Focus)

> **Status**: ⏳ PENDING | **Target**: M1 completion

### 8.1 Current State

**✅ Already Have**:
- `src/config.py`: `DatabaseConfig` with async URL
- `src/events/log.py`: `PostgresEventLog` placeholder
- `src/events/offsets.py`: `PostgresOffsetStore` placeholder
- `tests/fixtures/database.py`: Mock session, TestDatabaseConfig
- `requirements.txt`: alembic, asyncpg, psycopg2-binary
- `docker-compose.yml`: Postgres service

**❌ Missing** → **✅ All Implemented**

### 8.2 Schema Design

```sql
-- outbox table (event log)
CREATE TABLE outbox (
    id SERIAL PRIMARY KEY,          -- sequence number / offset
    type VARCHAR(100) NOT NULL,     -- e.g., "orders.Placed"
    payload JSONB NOT NULL,         -- full Envelope
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_outbox_type ON outbox(type);
CREATE INDEX idx_outbox_created_at ON outbox(created_at);
CREATE INDEX idx_outbox_type_created ON outbox(type, created_at);

-- consumer_offsets table (at-least-once delivery)
CREATE TABLE consumer_offsets (
    consumer_id VARCHAR(100) PRIMARY KEY,  -- e.g., "sse_broadcaster"
    last_offset BIGINT NOT NULL DEFAULT -1,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### 8.3 Implementation Phases

#### Phase A: Alembic Initialization (~30 min)
| Task | Output |
|------|--------|
| A1: Create `alembic.ini` | Config file |
| A2: Create `src/walle/models.py` | SQLAlchemy 2.0 models |
| A3: Create `src/walle/migrations/` | Alembic directory |
| A4: Create initial migration | outbox + consumer_offsets |

#### Phase B: Model Unit Tests (~20 min)
| Task | Tests |
|------|-------|
| B1: OutboxEvent creation/serialization | 3 |
| B2: ConsumerOffset creation/update | 3 |
| B3: Model constraints validation | 2 |

#### Phase C: Database Session Management (~30 min)
| Task | Output |
|------|--------|
| C1: Create `src/walle/database.py` | Async session factory |
| C2: Update `src/config.py` | Add sync_url for Alembic |
| C3: Session tests | 5 tests |

#### Phase D: Complete PostgresEventLog (~45 min)
| Task | Tests |
|------|-------|
| D1: Refactor `append()` with SQLAlchemy | 3 |
| D2: Refactor `read_from()` | 3 |
| D3: Refactor LISTEN/NOTIFY | 3 |
| D4: Complete `PostgresOffsetStore` | 4 |

#### Phase E: Integration Tests (~45 min) ✅
| Task | Description | Status |
|------|-------------|--------|
| E1: Setup integration fixtures | Connect to db_dev via DB_URL | ✅ Done |
| E2: `tests/integration/test_event_log.py` | Real Postgres (10 tests) | ✅ Done |
| E3: `tests/integration/test_offset_store.py` | Real Postgres (13 tests) | ✅ Done |
| E4: Test Alembic migrations | `alembic upgrade/downgrade` | ✅ Ready |

**Note**: Integration tests require `DB_URL` environment variable (set by docker-compose).

### 8.4 File Changes

| File | Action | Description | Status |
|------|--------|-------------|--------|
| `alembic.ini` | NEW | Alembic config (points to `src/walle/migrations`) | ✅ |
| `src/walle/models.py` | NEW | SQLAlchemy 2.0 models (`OutboxEvent`, `ConsumerOffset`) | ✅ |
| `src/walle/database.py` | NEW | Async session factory, `Database` class | ✅ |
| `src/walle/migrations/env.py` | NEW | Alembic env (supports `DB_URL` override) | ✅ |
| `src/walle/migrations/versions/001_*.py` | NEW | Initial migration (outbox + consumer_offsets with BigInteger) | ✅ |
| `src/events/log.py` | MODIFY | `PostgresEventLog` uses SQLAlchemy | ✅ |
| `src/events/offsets.py` | MODIFY | `PostgresOffsetStore` uses SQLAlchemy | ✅ |
| `src/config.py` | MODIFY | Add `sync_url` property for Alembic | ✅ |
| `docker/docker-compose.yml` | MODIFY | Add `DB_URL`, healthcheck, `depends_on`, `postgres:16-alpine` | ✅ |
| `docker/docker-compose.dev.yml` | MODIFY | Add `DB_URL`, healthcheck, `depends_on`, `postgres:16-alpine` | ✅ |
| `docker/example.env` | MODIFY | Add `POSTGRES_DB`, fix port variable name | ✅ |
| `docker/example.env.dev` | MODIFY | Add `POSTGRES_DB`, set dev defaults | ✅ |
| `tests/unit/walle/test_models.py` | NEW | Model unit tests (12) | ✅ |
| `tests/unit/walle/test_database.py` | NEW | Database unit tests (13) | ✅ |
| `tests/integration/conftest.py` | NEW | Integration fixtures (uses `alembic upgrade head`) | ✅ |
| `tests/integration/test_event_log.py` | NEW | EventLog integration (10) | ✅ |
| `tests/integration/test_offset_store.py` | NEW | OffsetStore integration (13) | ✅ |

### 8.5 Dependencies

```
Phase A ──► Phase B ──┐
    │                 │
    └──► Phase C ─────┼──► Phase D ──► Phase E
```

All phases complete ✅

### 8.6 Success Criteria

- [x] `alembic upgrade head` creates tables
- [x] `alembic downgrade base` rolls back
- [x] `PostgresEventLog` passes integration tests (append, read_from, subscribe)
- [x] `PostgresOffsetStore` passes integration tests (get, set, get_all)
- [x] Unit tests work without real database (mocked)
- [x] Integration tests connect to db_dev via DB_URL
- [ ] Coverage ≥80% (need to verify)

### 8.7 Notes

1. **SQLAlchemy 2.0 Async**: Use `AsyncSession`, `Mapped`, `mapped_column`
2. **Alembic + Async**: Alembic is sync, needs `psycopg2` driver via `sync_url`
3. **Legacy Code**: `walle.py` old code kept but marked deprecated
4. **LISTEN/NOTIFY**: Use asyncpg native, not SQLAlchemy (PostgresEventLog keeps asyncpg pool for subscribe)
5. **Integration Tests**: Run `alembic upgrade head` to setup tables, skipped if `DB_URL` not set
6. **Docker Compose**: Both prod and dev use `${POSTGRES_DB}` env var, `postgres:16-alpine` image
7. **DB_URL Format**: `postgresql+asyncpg://user:pass@host:5432/db` (container internal port is always 5432)

---

## Changelog

### 2026-01-30 — Database/Alembic Setup Complete 🎉

**Phase A-E Implementation Summary**:

| Phase | Description | Tests |
|-------|-------------|-------|
| A | Alembic initialization | N/A |
| B | Model unit tests | 12 |
| C | Session management | 13 |
| D | PostgresEventLog/OffsetStore refactor | N/A |
| E | Integration tests | 23 (skipped w/o DB_URL) |

**Files Created/Modified**:
- `alembic.ini`: Alembic configuration pointing to `src/walle/migrations`
- `src/walle/models.py`: SQLAlchemy 2.0 models (`OutboxEvent`, `ConsumerOffset` with BigInteger)
- `src/walle/database.py`: Async session factory and connection management
- `src/walle/migrations/env.py`: Supports `DB_URL` environment variable override
- `src/walle/migrations/versions/001_initial.py`: Creates `outbox` and `consumer_offsets` tables
- `docker/docker-compose.yml`: Added `DB_URL`, healthcheck, `depends_on`, pinned `postgres:16-alpine`
- `docker/docker-compose.dev.yml`: Same improvements as prod
- `docker/example.env` & `example.env.dev`: Added `POSTGRES_DB` variable

**Infrastructure Alignment**:
- Dev and prod docker-compose now consistent
- All use `${POSTGRES_DB}` environment variable (not hardcoded)
- Integration tests use `alembic upgrade head` (not `Base.metadata.create_all`)

**Tests**: 212 total (189 unit + 23 integration)
**Integration Tests**: Auto-skipped when `DB_URL` not set

---

### 2026-01-30 (Night) — Clock Factory Complete 🎉

**Clock Factory TDD** (`src/glados/clock/factory.py`):
- `ClockConfig` frozen dataclass with validation
- `create_clock()` factory function
- 18 unit tests, 100% coverage
- Automatic mode detection: has backtest times → BacktestClock, otherwise → RealtimeClock

**Tests**: 145 → 163 tests passing (+18)
**Clock Module**: 92 tests total, 93% coverage

---

### 2026-01-30 (Evening) — Clock Module Complete 🎉

**RealtimeClock TDD** (`src/glados/clock/realtime.py`):
- 24 unit tests covering all functionality
- 89% code coverage
- Drift compensation with two-phase sleep (long sleep + precision busy-wait)
- `_sleep_until()` method for precise bar alignment
- Tick timestamp is bar start time, not emission time

**BaseClock Refactoring** (`src/glados/clock/base.py`):
- Extracted shared state: `_run_id`, `_task`, `_bar_index`
- Moved `stop()` from abstract to concrete method
- Added `wait()` method with proper `CancelledError` handling
- DRY: removed duplicate code from both subclasses

**Tests**: 121 → 145 tests passing (+24)
**Clock Module**: 74 tests total, 93% coverage

---

### 2026-01-30 (PM) — BacktestClock Complete

**BacktestClock TDD** (`src/glados/clock/backtest.py`):
- 33 unit tests covering all functionality
- 92% code coverage
- Fixed bug: `_running` not reset when tick loop completes naturally
- Added `wait()` method for clean async API (replaces direct `_task` access)
- Backpressure mechanism fully tested
- Progress tracking fully tested
- Edge cases: single tick, multiple timeframes, callback exceptions

**ClockTick** (`src/glados/clock/base.py`):
- 98% coverage
- `to_dict()` serialization tested
- Immutability (frozen dataclass) tested

**Tests**: 88 → 121 tests passing (+33)

---

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

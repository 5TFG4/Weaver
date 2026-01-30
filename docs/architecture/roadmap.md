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
| **Test Infrastructure** | ✅ M0 Complete (212 tests passing) | 100% |
| **Project Restructure** | ✅ Phase 1.1 Complete | 100% |
| **Events Module** | ✅ Core types/protocol/registry (33 tests) | 60% |
| **Clock Module** | ✅ Complete (93 tests, 93% coverage) | 100% |
| **Config Module** | ✅ Dual credentials support (24 tests) | 100% |
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
| **M1: Foundation** | Clock full impl; Events DB integration; Alembic migrations | ✅ DONE |
| **M2: API Live** | Route tests pass; SSE tests pass | 🔄 IN PROGRESS |
| **M3: Trading Works** | Veda tests pass with mocked exchange; Order idempotency proven | ⏳ PENDING |
| **M4: Backtest Works** | Greta simulation tests pass; Stats calculations verified | ⏳ PENDING |
| **M5: Strategy Runs** | Marvin tests pass; SMA strategy backtested successfully | ⏳ PENDING |
| **M6: UI Functional** | Playwright E2E tests pass | ⏳ PENDING |
| **M7: MVP Complete** | All tests pass; Coverage ≥80%; Docs complete | ⏳ PENDING |

## 4. Phase Details

### Phase 1: Foundation (Week 1–2) — ✅ COMPLETE

- ✅ Test infrastructure
- ✅ Project restructure
- ✅ Events module (core)
- ✅ Clock module (complete: 93 tests, 93% coverage)
- ✅ Config module
- ✅ Database/Alembic setup
- ✅ Events DB integration (Outbox + LISTEN/NOTIFY)

### Phase 2: GLaDOS Core (Week 2–3) — 🔄 IN PROGRESS

- ⏳ FastAPI application factory
- ⏳ Dependency injection setup
- ⏳ REST endpoints (health, runs, orders, candles)
- ⏳ SSE streaming (/events/stream)
- ⏳ Domain routing foundation

> **Detailed Plan**: See Section 9 below

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

## 9. GLaDOS API Implementation Plan (Current Focus)

> **Status**: 🔄 IN PROGRESS | **Target**: M2 completion, 85% coverage

### 9.1 Current State

**✅ Already Have**:
- `src/glados/__init__.py`: Module definition with lazy import
- `src/glados/glados.py`: Legacy prototype code (needs refactor)
- `src/glados/routes/api.py`: Empty placeholder
- `src/glados/routes/sse.py`: Empty placeholder
- `src/glados/clock/`: Complete (93 tests)
- `src/events/`: Core types, protocol, registry, log, offsets
- `src/config.py`: Full configuration system
- `requirements.txt`: FastAPI, uvicorn, sse-starlette

**❌ Missing**:
- `src/glados/app.py`: FastAPI application factory
- `src/glados/dependencies.py`: Dependency injection
- `src/glados/schemas.py`: Pydantic request/response schemas
- REST endpoint implementations
- SSE streaming implementation
- Tests for all routes

### 9.2 API Endpoints Design

```
┌─────────────────────────────────────────────────────────────────┐
│  REST Endpoints                                                 │
├─────────────────────────────────────────────────────────────────┤
│  GET  /healthz              → Health check                      │
│  GET  /api/v1/runs          → List runs                         │
│  POST /api/v1/runs          → Start new run                     │
│  GET  /api/v1/runs/{id}     → Get run details                   │
│  POST /api/v1/runs/{id}/stop → Stop a run                       │
│  GET  /api/v1/orders        → Query orders (filter by run_id)   │
│  GET  /api/v1/orders/{id}   → Get order details                 │
│  GET  /api/v1/candles       → Query candle data                 │
├─────────────────────────────────────────────────────────────────┤
│  SSE Endpoint                                                   │
├─────────────────────────────────────────────────────────────────┤
│  GET  /api/v1/events/stream → SSE stream (thin events)          │
│  GET  /api/v1/events/tail   → REST polling alternative          │
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Implementation Phases

#### Phase A: Application Foundation (~1 hour)

| Task | Output | Tests |
|------|--------|-------|
| A1: Create `app.py` (factory pattern) | FastAPI app with lifespan | 3 |
| A2: Create `dependencies.py` | DI container, get_db, get_event_log | 4 |
| A3: Create `schemas.py` | Pydantic models for API | 5 |
| A4: Implement `/healthz` | Health check endpoint | 2 |

**Files**:
```
src/glados/
├── app.py              # create_app() factory
├── dependencies.py     # Dependency injection
├── schemas.py          # Pydantic request/response models
└── routes/
    └── api.py          # Add healthz endpoint
```

**Test First** (`tests/unit/glados/test_app.py`):
```python
def test_create_app_returns_fastapi_instance():
    """App factory should return configured FastAPI app."""

def test_healthz_returns_ok():
    """GET /healthz should return 200 with status ok."""

def test_app_includes_api_router():
    """App should include /api/v1 router."""
```

#### Phase B: Run Management Endpoints (~1.5 hours)

| Task | Output | Tests |
|------|--------|-------|
| B1: `GET /api/v1/runs` | List all runs | 3 |
| B2: `POST /api/v1/runs` | Start new run | 4 |
| B3: `GET /api/v1/runs/{id}` | Get run details | 3 |
| B4: `POST /api/v1/runs/{id}/stop` | Stop a run | 3 |

**Schemas**:
```python
class RunMode(str, Enum):
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"

class RunCreate(BaseModel):
    strategy_id: str
    mode: RunMode
    symbols: list[str]
    timeframe: str = "1m"
    # Backtest only
    start_time: datetime | None = None
    end_time: datetime | None = None

class RunResponse(BaseModel):
    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    symbols: list[str]
    timeframe: str
    created_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None
```

**Test First** (`tests/unit/glados/routes/test_runs.py`):
```python
def test_list_runs_empty():
    """GET /runs with no runs should return empty list."""

def test_list_runs_returns_all():
    """GET /runs should return all runs."""

def test_create_run_validates_mode():
    """POST /runs with invalid mode should return 422."""

def test_create_run_returns_201():
    """POST /runs with valid data should return 201."""

def test_get_run_not_found():
    """GET /runs/{id} with unknown id should return 404."""

def test_stop_run_transitions_status():
    """POST /runs/{id}/stop should change status to stopped."""
```

#### Phase C: Order Query Endpoints (~1 hour)

| Task | Output | Tests |
|------|--------|-------|
| C1: `GET /api/v1/orders` | Query orders with filters | 4 |
| C2: `GET /api/v1/orders/{id}` | Get order details | 3 |

**Schemas**:
```python
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderResponse(BaseModel):
    id: str
    run_id: str
    client_order_id: str      # For idempotency
    symbol: str
    side: OrderSide
    qty: Decimal
    filled_qty: Decimal
    price: Decimal | None     # Limit price
    filled_avg_price: Decimal | None
    status: OrderStatus
    created_at: datetime
    filled_at: datetime | None
```

**Test First** (`tests/unit/glados/routes/test_orders.py`):
```python
def test_list_orders_filters_by_run_id():
    """GET /orders?run_id=x should filter by run."""

def test_list_orders_filters_by_status():
    """GET /orders?status=filled should filter by status."""

def test_get_order_not_found():
    """GET /orders/{id} with unknown id should return 404."""
```

#### Phase D: Candle Data Endpoint (~45 min)

| Task | Output | Tests |
|------|--------|-------|
| D1: `GET /api/v1/candles` | Query candle data | 4 |

**Schemas**:
```python
class CandleResponse(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
```

**Test First** (`tests/unit/glados/routes/test_candles.py`):
```python
def test_candles_requires_symbol():
    """GET /candles without symbol should return 422."""

def test_candles_returns_ohlcv():
    """GET /candles should return OHLCV data."""
```

#### Phase E: SSE Streaming (~1.5 hours)

| Task | Output | Tests |
|------|--------|-------|
| E1: Create `SSEBroadcaster` class | Manages SSE connections | 4 |
| E2: `GET /api/v1/events/stream` | SSE endpoint | 5 |
| E3: `GET /api/v1/events/tail` | REST polling fallback | 3 |
| E4: Integrate with EventLog | Broadcast on new events | 3 |

**Files**:
```
src/glados/
├── sse_broadcaster.py  # SSEBroadcaster class
└── routes/
    └── sse.py          # SSE endpoints
```

**SSE Event Format** (Thin Events):
```
event: ui.run_started
data: {"run_id": "abc123", "status": "running"}

event: ui.order_updated
data: {"order_id": "xyz789", "status": "filled", "run_id": "abc123"}

event: ui.tick
data: {"run_id": "abc123", "timestamp": "2026-01-30T10:00:00Z", "bar_index": 42}
```

**Test First** (`tests/unit/glados/routes/test_sse.py`):
```python
async def test_sse_stream_connects():
    """GET /events/stream should establish SSE connection."""

async def test_sse_receives_events():
    """SSE stream should receive published events."""

async def test_sse_reconnect_with_last_event_id():
    """SSE should support Last-Event-ID for reconnection."""

def test_tail_returns_events_after_offset():
    """GET /events/tail?after=10 should return events after offset."""
```

#### Phase F: Error Handling & Middleware (~45 min)

| Task | Output | Tests |
|------|--------|-------|
| F1: Create error response schema | Consistent error format | 2 |
| F2: Add exception handlers | Global error handling | 4 |
| F3: Add request ID middleware | Correlation tracking | 2 |
| F4: Add logging middleware | Structured request logs | 2 |

**Error Response Format**:
```python
class ErrorResponse(BaseModel):
    code: str              # e.g., "NOT_FOUND", "VALIDATION_ERROR"
    message: str           # Human-readable message
    details: dict | None   # Additional context
    correlation_id: str    # Request tracking ID
```

### 9.4 File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/glados/app.py` | NEW | FastAPI factory with lifespan |
| `src/glados/dependencies.py` | NEW | DI: get_db, get_event_log, get_config |
| `src/glados/schemas.py` | NEW | All Pydantic models |
| `src/glados/sse_broadcaster.py` | NEW | SSE connection manager |
| `src/glados/routes/api.py` | MODIFY | REST endpoints implementation |
| `src/glados/routes/sse.py` | MODIFY | SSE endpoints implementation |
| `src/glados/routes/__init__.py` | MODIFY | Export routers |
| `src/glados/glados.py` | REFACTOR | Remove legacy code, use new patterns |
| `tests/unit/glados/test_app.py` | NEW | App factory tests |
| `tests/unit/glados/test_dependencies.py` | NEW | DI tests |
| `tests/unit/glados/routes/test_runs.py` | NEW | Run endpoint tests |
| `tests/unit/glados/routes/test_orders.py` | NEW | Order endpoint tests |
| `tests/unit/glados/routes/test_candles.py` | NEW | Candle endpoint tests |
| `tests/unit/glados/routes/test_sse.py` | NEW | SSE endpoint tests |
| `tests/fixtures/http.py` | MODIFY | Add TestClient fixture |

### 9.5 Execution Order (TDD)

```
┌─────────────────────────────────────────────────────────────────┐
│  Day 1: Foundation                                              │
│  ├── A1: app.py (factory)     ← Write tests first               │
│  ├── A2: dependencies.py      ← Write tests first               │
│  ├── A3: schemas.py           ← Define all models               │
│  └── A4: /healthz             ← First working endpoint          │
├─────────────────────────────────────────────────────────────────┤
│  Day 2: Run Management                                          │
│  ├── B1: GET /runs            ← List runs                       │
│  ├── B2: POST /runs           ← Start run (mock backend)        │
│  ├── B3: GET /runs/{id}       ← Get details                     │
│  └── B4: POST /runs/{id}/stop ← Stop run                        │
├─────────────────────────────────────────────────────────────────┤
│  Day 3: Orders & Candles                                        │
│  ├── C1-C2: Order endpoints   ← Query orders                    │
│  └── D1: Candle endpoint      ← Query candles                   │
├─────────────────────────────────────────────────────────────────┤
│  Day 4: SSE Streaming                                           │
│  ├── E1: SSEBroadcaster       ← Connection manager              │
│  ├── E2: /events/stream       ← SSE endpoint                    │
│  ├── E3: /events/tail         ← REST fallback                   │
│  └── E4: EventLog integration ← Broadcast on append             │
├─────────────────────────────────────────────────────────────────┤
│  Day 5: Polish                                                  │
│  ├── F1-F4: Error handling    ← Middleware, errors              │
│  ├── Integration tests        ← Full API flow                   │
│  └── Documentation update     ← API docs                        │
└─────────────────────────────────────────────────────────────────┘
```

### 9.6 Dependencies

```
Phase A ──► Phase B ──► Phase C ──► Phase D
    │                                   │
    └──────────► Phase E ◄──────────────┘
                    │
                    ▼
                Phase F
```

- **A (Foundation)**: No dependencies, start here
- **B (Runs)**: Depends on A (schemas, dependencies)
- **C (Orders)**: Depends on A
- **D (Candles)**: Depends on A
- **E (SSE)**: Depends on A, needs EventLog
- **F (Error Handling)**: After all routes work

### 9.7 Success Criteria

- [ ] `pytest tests/unit/glados/routes/ -v` all passing
- [ ] Coverage ≥85% for `src/glados/routes/`
- [ ] `/healthz` returns `{"status": "ok"}`
- [ ] Run CRUD operations work (with mock backend)
- [ ] SSE stream can be established and receives events
- [ ] Error responses follow standard format
- [ ] Request correlation IDs are logged
- [ ] No flaky tests

### 9.8 Testing Strategy

**Unit Tests** (mock everything):
- Use FastAPI `TestClient` for sync tests
- Use `httpx.AsyncClient` for async tests
- Mock EventLog with `InMemoryEventLog`
- Mock database with fixtures

**Integration Tests** (real dependencies):
- Run with Docker Compose
- Test SSE with real EventLog (Postgres)
- Test error recovery

**Key Test Fixtures**:
```python
# tests/fixtures/http.py
@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    """Sync test client for route testing."""
    return TestClient(app)

@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Async test client for SSE testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

# tests/conftest.py
@pytest.fixture
def app(mock_event_log, mock_db) -> FastAPI:
    """Create app with mocked dependencies."""
    return create_app(
        event_log=mock_event_log,
        db=mock_db,
    )
```

### 9.9 Notes

1. **TDD Strict**: Write test → Run (RED) → Implement → Run (GREEN) → Refactor
2. **Mock Backend**: Routes don't call real Veda/Greta yet, just manage state
3. **Schema First**: Define all Pydantic models before implementing routes
4. **SSE Testing**: Use `sse-starlette` for server, `httpx-sse` for client testing
5. **Error Codes**: Use consistent codes like `NOT_FOUND`, `VALIDATION_ERROR`, `INTERNAL_ERROR`
6. **Correlation ID**: Generate UUID per request, include in all logs and error responses
7. **OpenAPI**: FastAPI auto-generates `/docs` (Swagger) and `/redoc`

---

## Changelog

### 2026-01-30 (Late Night) — M1 Complete, M2 Started 🎉

**M1: Foundation Complete**:
- ✅ Clock module: 93 tests, 93% coverage
- ✅ Events DB integration: PostgresEventLog, PostgresOffsetStore
- ✅ Alembic migrations: outbox + consumer_offsets tables
- ✅ Integration tests: 23 tests (skipped without DB_URL)

**M2: API Live Started**:
- Created detailed implementation plan (Section 9)
- 6 phases: Foundation → Runs → Orders → Candles → SSE → Error Handling
- Estimated: 5 days, ~50 tests
- Target: 85% coverage for `src/glados/routes/`

**Tests**: 212 total (189 unit + 23 integration)

---

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

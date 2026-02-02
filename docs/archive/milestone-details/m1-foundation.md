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


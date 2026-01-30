# Weaver — Architecture Baseline



## 1. Document Goals & Scope

* **Goals**: Fix system **invariants** and boundaries; prevent implementation drift; provide a single shared vocabulary for collaboration, reviews, troubleshooting, and iteration.
* **Out of scope**: Library shootouts, full DDL/API samples, long code listings.



## 2. System Goals & Non‑Goals

* **Goals**:

  * A 24/7 automated trading system on a local server, supporting **live trading and backtesting**, **multi‑strategy concurrency**, **web UI**, and **containerized deployment**.
  * Integrate Alpaca first; keep the door open for more exchanges.
* **Non‑Goals (MVP)**:

  * Microservice split, distributed queues, or complex workflow engines.
  * Exactly‑once stream processing.
  * External multi‑tenant or complex auth systems.



## 3. Architecture Overview

### 3.1 Shape & Boundaries

* **Modulith**: A single backend process (Python) hosting domain packages: `GLaDOS / Events / Veda / Greta / Marvin / WallE`. **Only GLaDOS** exposes northbound APIs.
* **Frontend–Backend split**: Haro (React) runs as an independent container, talking to the backend via APIs.

### 3.2 External Interfaces

* **REST**: synchronous query & control.
* **Realtime**: prefer **SSE (thin events)**; **REST Tail (incremental polling)** is also supported. Contracts are equivalent and interchangeable.

### 3.3 Internal Collaboration Model

* **Synchronous calls**: Critical paths are in‑process function calls (GLaDOS assembles and calls Veda/Greta/Marvin/WallE).
* **Event‑driven**: For broadcast, decoupling, notifications, and replay. Implemented as **EventLog (Postgres Outbox + LISTEN/NOTIFY)**:

  * Business write and event append happen in the **same transaction** (`outbox`).
  * After commit, `NOTIFY` wakes subscribers.
  * Consumers persist progress in `consumer_offsets`. Delivery is **at‑least‑once**.
* **Strategy‑led**: Strategies express intent via events (fetch/order). GLaDOS performs **domain routing** (`strategy.* → live|backtest.*`).

### 3.4 Global Invariants

* **Time**: DB stores **UTC**; frontend renders in the user timezone.
* **Error model**: `{code, message, details, correlation_id}`.
* **Identity chain**: `id / corr_id / causation_id / trace_id`; events are immutable and replayable.



## 4. Modules — Responsibilities & Boundaries

> Defines what each module **does / does not** do. Library choices and low‑level details are out of scope.

### 4.1 GLaDOS (Control Plane & API)

* **Responsibilities**: Sole northbound API; run lifecycle; domain routing (`strategy.* → live|backtest.*`); self‑clock (align to bar timeframes); dependency wiring; publish thin events to the frontend.
* **I/O**: Inbound `strategy.* / run.*` (via REST or internal triggers); outbound `live|backtest.*` requests and `ui.*` thin events.
* **Constraints**: Does **not** write business tables directly (delegates to WallE); single publisher for events.

### 4.2 Veda (Live Data & Trading)

* **Responsibilities**: Handle `live.*` requests; call exchanges and cache for data, submit/query orders; emit `data.* / market.* / orders.*`.
* **Constraints**: Idempotent orders (`client_order_id`); global rate limits coordinated by GLaDOS; prefer cache hits.

### 4.3 Greta (Backtest Data & Simulation)

* **Responsibilities**: Handle `backtest.*` requests; produce historical windows; simulate fills/slippage/fees; emit `orders.*` and backtest stats.
* **Constraints**: Shares the same contracts as Veda; only the execution domain differs.

### 4.4 Marvin (Strategy Execution)

* **Responsibilities**: Maintain `run_id` context; tick by self‑clock; emit `strategy.FetchWindow/PlaceRequest`; consume `data.* / market.* / orders.*`; produce `strategy.DecisionMade`.
* **Constraints**: **Mode‑agnostic** (live/backtest); in‑flight backpressure keyed by `corr_id`.

### 4.5 WallE (Persistence Layer)

* **Responsibilities**: Centralized writes (`data.* / orders.* / strategy.DecisionMade`, etc.) and repository‑style reads for API.
* **Constraints**: Every table has `id, created_at(UTC), updated_at(UTC)`; single write path, auditable.

### 4.6 Haro (Web UI)

* **Responsibilities**: Show accounts/orders/runs/backtests; start/stop runs; consume SSE or REST Tail.
* **Constraints**: Subscribes **thin events only**; fetch details via REST.

### 4.7 Events (Protocol & Runtime)

* **Responsibilities**: Envelope/registry/validation; Outbox append & fan‑out; offsets management; retention/cleanup policy.
* **Implementation**: **EventLog (Postgres Outbox + LISTEN/NOTIFY)** — write business + event to `outbox` in one transaction; after commit, `NOTIFY` wakes consumers; progress stored in `consumer_offsets`; at‑least‑once, consumers deduplicate.
* **Constraints**: Thin events for UI; internal payload size policy in §5; protocol versioning supports parallel `*.v2`.



## 5. Event Model & Flows

### 5.1 Envelope (Stable Contract)

`{ id, kind:'evt'|'cmd', type, version, run_id, corr_id, causation_id, trace_id, ts, producer, headers, payload }`

### 5.2 Namespaces

`strategy.* / live.* / backtest.* / data.* / market.* / orders.* / run.* / ui.*`

### 5.3 Payload & Size Policy

* **Thin events** (to UI): keys + status only; fetch details via REST.
* **Internal events**: ≤ ~100KB inline; 100KB–2MB use `data.WindowChunk/Complete`; >2MB store **reference** only (`data_ref`).

### 5.4 Typical Flows

* **Fetch**: `strategy.FetchWindow → (GLaDOS route) → live|backtest.FetchWindow → data.WindowReady/Chunk/Complete`.
* **Orders**: `orders.PlaceRequest → orders.Ack/Placed/Filled/Rejected`.
* **Run**: `run.Started/StopRequested/Heartbeat`; `clock.Tick`.

### 5.5 Delivery & Idempotency

* Write `outbox` in‑transaction; `NOTIFY` after commit; resume via `consumer_offsets`; deduplicate by `id/corr_id`.



## 6. Data & Persistence

* **Business data (WallE)**: `orders / fills / candles / runs / backtests / strategy_results`, exposed via repositories.
* **EventLog**: `outbox` (fact log) and `consumer_offsets` (progress).
* **Retention & Cleanup**: time/partition based; TTL + audit retention; large payloads may use external storage (store references only).



## 7. External Interfaces

* **REST**: `/healthz`, `/runs` (list/start/stop), `/orders` query, `/candles` query.
* **Realtime**: `/events/stream` (SSE) or `/events/tail` (REST incremental).
* **Auth**: Local/private can run without auth; when exposed, use a **single API Key** (header), optionally with IP allow‑list.
* **Time semantics**: If no timezone specified in inputs, fall back to system default; responses are UTC or include timezone.



## 8. Deployment & Environment

### 8.1 Container Topology

* **Backend**: one multi‑stage Dockerfile (`dev`/`prod` targets).
* **Frontend**: `haro/Dockerfile` multi‑stage (`dev`: Node dev server; `prod`: Nginx static).
* **Compose**: `docker-compose.yml` (production‑like) + `docker-compose.dev.yml` (dev overrides).

### 8.2 Environment Variables & Secrets

* **Templates in repo**: `/.env.example` (prod template), `/.env.dev.example` (dev template).
* **Local files**: `.env / .env.dev` are copied from templates and **not committed** (`.gitignore`).
* **Build‑time args**: non‑secrets only (e.g., `VITE_API_BASE`).
* **Run‑time secrets**: DB/exchange keys injected by the deployment system; **never baked into image layers**.
* **CI build‑time private sources**: use **BuildKit Secrets** (ephemeral mounts, no layer leakage).

### 8.3 Migrations

* Use **Alembic** from day one; run `upgrade head` before release; keep migrations minimal and necessary.



## 9. Operations & Reliability

* **Backpressure**: throttle based on `consumer_offsets` lag thresholds.
* **Rate limiting**: live access coordinated by GLaDOS (DB token bucket/quotas).
* **Observability**: structured logs (include `run_id / corr_id`); optional metrics for lag/in‑flight/error rates.
* **Idempotency & Recovery**: event dedupe (`id/corr_id`); `client_order_id` on orders; consumers resume via offsets; outbox is replayable.



## 10. Versioning & Compatibility

* **Additive changes are backward‑compatible**; breaking changes use new names like `*.v2` and run in parallel for migration.
* **Pluggable implementation**: if LISTEN/NOTIFY is insufficient, swap `events/log.py` for Redis Streams/Kafka; protocol and business code remain unchanged.
* **Decomposition**: modules can be split into separate processes if needed, reusing the same protocol and offsets semantics.



## 11. Repository Structure

```plaintext
weaver/
├── README.md
├── LICENSE
├── .gitignore
├── .dockerignore
├── .editorconfig
├── pyproject.toml                     # tooling config only (no deps here)
├── .env.example                       # templates; .env/.env.dev are untracked
├── .env.dev.example                   # templates; .env/.env.dev are untracked
├── docker/
│   ├── backend/
│   │   ├── Dockerfile                 # multi-stage dev/prod
│   │   ├── requirements.txt           # runtime deps (single source of truth)
│   │   └── requirements.dev.txt       # dev deps (optional)
│   ├── docker-compose.yml             # production-like
│   └── docker-compose.dev.yml         # dev overrides
├── src/
│   ├── glados/
│   │   ├── app.py
│   │   ├── routes/
│   │   │   ├── api.py                 # /healthz, /runs, /orders, /candles
│   │   │   └── sse.py                 # /events/stream (or REST tail)
│   │   ├── domain_router.py           # route strategy.* → live|backtest.*
│   │   ├── clock/
│   │   │   ├── base.py                # BaseClock ABC
│   │   │   ├── realtime.py            # RealtimeClock (wall-clock aligned)
│   │   │   ├── backtest.py            # BacktestClock (fast-forward)
│   │   │   └── utils.py               # bar alignment calculations
│   │   └── main.py                    # start EventPump/Clock/API
│   ├── events/
│   │   ├── protocol.py                # envelope/error model
│   │   ├── types.py                   # event name constants
│   │   ├── registry.py                # type→payload model registry/validation
│   │   ├── log.py                     # Outbox/LISTEN-NOTIFY/fan-out
│   │   ├── offsets.py                 # consumer_offsets management
│   │   └── retention.py               # TTL/cleanup/partitioning
│   ├── veda/
│   │   ├── handlers.py                # subscribe to live.* → produce data.* / market.*
│   │   ├── trading.py                 # orders.PlaceRequest → orders.*
│   │   └── alpaca_client.py
│   ├── greta/
│   │   └── handlers.py                # subscribe to backtest.* → data.* / orders.*
│   ├── marvin/
│   │   ├── handlers.py                # strategy intents/decisions
│   │   ├── timing.py                  # self-clock/backpressure
│   │   ├── base_strategy.py
│   │   └── strategies/
│   │       ├── sma_cross.py           # example strategy (optional placeholder)
│   │       └── README.md
│   ├── walle/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── repos.py
│   │   └── handlers.py                # centralized writes
│   ├── config.py                      # providers/thresholds/concurrency
│   └── __init__.py
├── haro/
│   ├── Dockerfile                     # multi-stage: dev (dev server) / prod (Nginx static)
│   ├── package.json
│   ├── vite.config.ts                 # or webpack config
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts              # wraps REST + SSE (or REST tail)
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Runs.tsx
│       │   ├── Orders.tsx
│       │   └── Backtests.tsx
│       ├── components/
│       │   ├── EventFeed.tsx
│       │   └── Charts/
│       └── styles/
│           └── index.css
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 0001_init.py
├── tests/
│   ├── unit/
│   │   ├── test_events_registry.py
│   │   ├── test_glados_router.py
│   │   ├── veda/
│   │   ├── greta/
│   │   ├── marvin/
│   │   └── walle/
│   ├── integration/
│   │   ├── test_fetch_window_flow.py
│   │   └── test_order_flow.py
│   └── e2e/
│       └── test_ui_basic.py
├── scripts/
│   ├── dev_up.sh                     # optional
│   └── seed_demo_data.py             # optional
├── .github/
│   └── workflows/
│       └── ci.yml                    # Lint/Test/Build
└── docs/
    └── ADRs/                         # Architecture Decision Records (optional)
```



## 12. Clock System (Self‑Clock)

> **Critical Design Note**: Python's `asyncio.sleep()` is not precise. The clock system must handle both realtime trading (strict wall‑clock alignment) and backtesting (fast‑forward simulation).

### 12.1 Clock Abstraction

The clock system uses a **strategy pattern** with a common interface:

```python
class BaseClock(ABC):
    @abstractmethod
    async def start(self, run_id: str, timeframe: str) -> None:
        """Start emitting clock.Tick events."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the clock."""
        pass

    @abstractmethod
    def current_time(self) -> datetime:
        """Return the current clock time (wall or simulated)."""
        pass
```

### 12.2 RealtimeClock (Live Trading)

Used for **live trading** where ticks must align to actual wall‑clock time.

* **Bar Alignment**: Ticks fire at the **start of each bar** (e.g., every minute at `:00` seconds).
* **Drift Compensation**: Calculate sleep duration dynamically to compensate for execution time.
* **Implementation Strategy**:
  1. Calculate `next_tick_time` based on timeframe (e.g., next minute boundary).
  2. Sleep until `next_tick_time - small_buffer` (e.g., 100ms before).
  3. Busy‑wait or precise sleep for the remaining time.
  4. Emit `clock.Tick` with `ts = next_tick_time` (not actual wall time).

```python
class RealtimeClock(BaseClock):
    """
    Emits clock.Tick aligned to wall-clock bar boundaries.
    
    Example for 1-minute bars:
      - 09:30:00.000 → Tick
      - 09:31:00.000 → Tick
      - 09:32:00.000 → Tick
    
    Handles drift by recalculating sleep duration each iteration.
    """
    async def _tick_loop(self):
        while self.running:
            next_tick = self._calculate_next_bar_start()
            await self._sleep_until(next_tick)
            await self._emit_tick(next_tick)
```

* **Precision Target**: ±50ms of intended tick time.
* **Fallback**: If system clock drifts significantly, log warning and continue.

### 12.3 BacktestClock (Simulation)

Used for **backtesting** where simulation should run as fast as possible.

* **Fast‑Forward Mode**: No actual sleeping; ticks are emitted immediately.
* **Simulated Time**: Advances based on historical data range.
* **Backpressure Awareness**: Wait for strategy to finish processing before advancing.

```python
class BacktestClock(BaseClock):
    """
    Emits clock.Tick as fast as possible for backtesting.
    
    Does NOT sleep. Advances simulated time immediately.
    Waits for strategy acknowledgment before next tick (backpressure).
    """
    def __init__(self, start_time: datetime, end_time: datetime, timeframe: str):
        self.simulated_time = start_time
        self.end_time = end_time
        self.timeframe = timeframe

    async def _tick_loop(self):
        while self.simulated_time <= self.end_time and self.running:
            await self._emit_tick(self.simulated_time)
            await self._wait_for_strategy_ack()  # backpressure
            self.simulated_time = self._advance_time()
```

* **Speed**: Limited only by strategy execution time and I/O.
* **Determinism**: Same inputs produce same tick sequence.

### 12.4 Clock Selection (GLaDOS Responsibility)

GLaDOS selects the appropriate clock based on run mode:

```python
def create_clock(run_config: RunConfig) -> BaseClock:
    if run_config.mode == "live":
        return RealtimeClock(timeframe=run_config.timeframe)
    elif run_config.mode == "backtest":
        return BacktestClock(
            start_time=run_config.backtest_start,
            end_time=run_config.backtest_end,
            timeframe=run_config.timeframe
        )
```

### 12.5 clock.Tick Event

```python
@dataclass
class ClockTick:
    run_id: str
    ts: datetime          # Bar start time (not emission time)
    timeframe: str        # "1m", "5m", "1h", "1d"
    bar_index: int        # Sequential bar number within run
    is_backtest: bool     # Hint for logging/metrics (strategy should NOT use this for logic)
```

### 12.6 Timeframe Support

| Timeframe | Code | Bar Alignment |
|-----------|------|---------------|
| 1 minute  | `1m` | `:00` seconds |
| 5 minutes | `5m` | `:00`, `:05`, `:10`, ... |
| 15 minutes| `15m`| `:00`, `:15`, `:30`, `:45` |
| 1 hour    | `1h` | `:00:00` |
| 1 day     | `1d` | `00:00:00 UTC` |

### 12.7 Files

```plaintext
src/glados/
├── clock/
│   ├── __init__.py
│   ├── base.py           # BaseClock ABC
│   ├── realtime.py       # RealtimeClock implementation
│   ├── backtest.py       # BacktestClock implementation
│   └── utils.py          # Bar alignment calculations
```



## 13. Implementation Roadmap (Test‑Driven)

> This project follows **Test‑Driven Development (TDD)** to ensure reliability and prevent scope creep.
> 
> **Core Principle**: Write tests FIRST, then implement just enough code to pass.

### 13.1 Testing Strategy Overview

#### Test Pyramid

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

#### Test Categories

| Category | Scope | Speed | Dependencies |
|----------|-------|-------|--------------|
| **Unit** | Single function/class | <10ms | Mocked |
| **Integration** | Module interactions | <1s | Real DB (test container) |
| **E2E** | Full system | <30s | All services running |

#### Testing Tools

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

#### Runtime Environment

* **Python**: 3.13+ (required)
* **Base Image**: `python:3.13-slim-bookworm`
* **OS**: Debian 12 (bookworm)

### 13.2 Test Infrastructure Setup (Day 1) — ✅ COMPLETE

The testing foundation has been established with the following structure:

```plaintext
tests/
├── __init__.py
├── conftest.py              # Shared fixtures (frozen_time, sample_ids, test_config, etc.)
├── factories/               # Test data factories
│   ├── __init__.py
│   ├── events.py            # EventFactory, create_event()
│   ├── orders.py            # OrderFactory, create_order()
│   └── runs.py              # RunFactory, create_run()
├── fixtures/                # Reusable test fixtures
│   ├── __init__.py
│   ├── clock.py             # ControllableClock, ClockTick
│   ├── database.py          # TestDatabaseConfig, MockDatabaseSession
│   ├── event_log.py         # InMemoryEventLog, TestEnvelope
│   └── http.py              # AlpacaMockBuilder, MockBar/Order/Account
├── unit/
│   ├── test_infrastructure.py  # 14 smoke tests verifying test setup
│   ├── events/
│   ├── glados/
│   │   ├── clock/
│   │   └── routes/
│   ├── veda/
│   ├── greta/
│   ├── marvin/
│   └── walle/
├── integration/
└── e2e/
```

#### Key Fixtures

```python
# conftest.py - Critical shared fixtures

@pytest.fixture
def test_clock():
    """Controllable clock for deterministic tests."""
    return ControllableClock(start_time=datetime(2024, 1, 1, 9, 30))

@pytest.fixture
def in_memory_event_log():
    """In-memory event log for unit tests (no DB)."""
    return InMemoryEventLog()

@pytest.fixture
async def test_db(tmp_path):
    """Isolated Postgres via testcontainers."""
    async with PostgresContainer() as pg:
        engine = create_async_engine(pg.get_connection_url())
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine

@pytest.fixture
def mock_alpaca():
    """Mocked Alpaca API responses."""
    with respx.mock:
        # Pre-configure common responses
        yield AlpacaMockBuilder()
```

### 13.3 TDD Workflow Per Feature

```
┌─────────────────────────────────────────────────────────────┐
│                    TDD Cycle (Red-Green-Refactor)           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. RED: Write a failing test                              │
│      - Test describes the expected behavior                 │
│      - Run test → FAIL (proves test works)                  │
│                                                             │
│   2. GREEN: Write minimal code to pass                      │
│      - Only implement what's needed                         │
│      - Run test → PASS                                      │
│                                                             │
│   3. REFACTOR: Improve code quality                         │
│      - Clean up, optimize, extract patterns                 │
│      - Run test → STILL PASS                                │
│                                                             │
│   4. REPEAT for next test case                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 13.4 Current State Assessment

> **Last Updated**: 2026-01-29

| Component | Status | Completion |
|-----------|--------|------------|
| **Python Environment** | ✅ Upgraded to 3.13 | 100% |
| **Test Infrastructure** | ✅ M0 Complete (14 tests passing) | 100% |
| Docker config | ✅ Dev/prod configs, slim images | ~80% |
| GLaDOS core | Basic framework | ~25% |
| Veda/Alpaca | Can fetch data, place orders | ~40% |
| EventBus | Simple in‑memory | ~15% |
| WallE/DB | Basic SQLAlchemy model | ~10% |
| Events module | ❌ Not implemented | 0% |
| REST API | ❌ Not implemented | 0% |
| SSE streaming | ❌ Not implemented | 0% |
| Greta (backtest) | ❌ Empty shell | 0% |
| Marvin (strategy) | ❌ Empty shell | 0% |
| Haro (frontend) | ❌ Does not exist | 0% |
| Alembic migrations | ❌ Not set up | 0% |

### 13.5 Phase 1: Foundation + Test Infrastructure (Week 1–2)

**Goal**: Establish test infrastructure AND core modules together.

#### 1.0 Test Infrastructure (FIRST) — ✅ COMPLETE
- [x] Set up `pyproject.toml` test config (pytest, coverage, ruff, mypy)
- [x] Create `tests/conftest.py` with core fixtures
- [x] Create `tests/fixtures/database.py` — TestDatabaseConfig, MockDatabaseSession
- [x] Create `tests/fixtures/clock.py` — ControllableClock, ClockTick
- [x] Create `tests/fixtures/event_log.py` — InMemoryEventLog, TestEnvelope
- [x] Create `tests/fixtures/http.py` — AlpacaMockBuilder, MockBar/Order/Account
- [x] Create `tests/factories/` — EventFactory, OrderFactory, RunFactory
- [x] Verify: `pytest tests/ -v` → 14 tests passing
- [x] Upgrade Python to 3.13 (from 3.8)

#### 1.1 Project Restructure
- [ ] Rename directories to match spec (`GLaDOS` → `glados`, etc.)
- [ ] Clean up archive folders
- [ ] Update `requirements.txt` + `requirements.dev.txt`
- [ ] Add `pyproject.toml` for tooling config

#### 1.2 Events Module (TDD)

**Tests First:**
```python
# tests/unit/events/test_protocol.py
def test_envelope_creation():
    """Envelope should have all required fields."""
    
def test_envelope_immutable():
    """Envelope should be frozen after creation."""

def test_envelope_serialization():
    """Envelope should serialize to/from JSON."""

# tests/unit/events/test_registry.py
def test_register_event_type():
    """Should register event type with payload schema."""

def test_validate_payload_success():
    """Should pass validation for correct payload."""

def test_validate_payload_failure():
    """Should raise ValidationError for incorrect payload."""

# tests/integration/events/test_outbox.py
async def test_outbox_write_and_notify():
    """Writing to outbox should trigger NOTIFY."""

async def test_consumer_offset_tracking():
    """Consumer should track processed offset."""

async def test_at_least_once_delivery():
    """Events should be redelivered after consumer crash."""
```

**Implementation:**
- [ ] `events/protocol.py` — Envelope dataclass, ErrorResponse
- [ ] `events/types.py` — Event type constants
- [ ] `events/registry.py` — Type → Payload registry
- [ ] `events/log.py` — Outbox write + LISTEN/NOTIFY
- [ ] `events/offsets.py` — Consumer offset management

#### 1.3 Database Setup (TDD)

**Tests First:**
```python
# tests/unit/walle/test_models.py
def test_run_model_has_required_fields():
    """Run model should have id, created_at, updated_at."""

def test_order_model_relationships():
    """Order should link to Run via run_id."""

# tests/integration/walle/test_repos.py
async def test_create_and_get_run():
    """Should persist and retrieve a run."""

async def test_order_idempotency():
    """Duplicate client_order_id should not create duplicate."""
```

**Implementation:**
- [ ] Initialize Alembic
- [ ] Create initial migration
- [ ] `walle/database.py` — Session management
- [ ] `walle/models.py` — SQLAlchemy models
- [ ] `walle/repos.py` — Repository pattern

### 13.6 Phase 2: GLaDOS Core (Week 2–3)

**Goal**: REST API + SSE + Clock with full test coverage.

#### 2.1 Clock System (TDD) — HIGH PRIORITY

**Tests First:**
```python
# tests/unit/glados/clock/test_utils.py
def test_next_bar_start_1m():
    """09:30:45 → next bar at 09:31:00."""

def test_next_bar_start_5m():
    """09:32:00 → next bar at 09:35:00."""

def test_bar_alignment_edge_cases():
    """Exactly on boundary should return next bar, not current."""

# tests/unit/glados/clock/test_realtime.py
@freeze_time("2024-01-01 09:30:00")
async def test_realtime_clock_emits_on_boundary():
    """RealtimeClock should emit tick at bar boundary."""

async def test_realtime_clock_drift_compensation():
    """Should compensate for execution time drift."""

# tests/unit/glados/clock/test_backtest.py
async def test_backtest_clock_no_sleep():
    """BacktestClock should not actually sleep."""

async def test_backtest_clock_respects_backpressure():
    """Should wait for strategy ack before next tick."""

async def test_backtest_clock_deterministic():
    """Same inputs should produce same tick sequence."""
```

**Implementation:**
- [ ] `glados/clock/base.py` — BaseClock ABC
- [ ] `glados/clock/utils.py` — Bar alignment utilities
- [ ] `glados/clock/realtime.py` — RealtimeClock
- [ ] `glados/clock/backtest.py` — BacktestClock

#### 2.2 FastAPI Application (TDD)

**Tests First:**
```python
# tests/unit/glados/routes/test_api.py
async def test_healthz_returns_ok():
    """GET /healthz should return 200."""

async def test_create_run_validates_config():
    """POST /runs with invalid config should return 422."""

async def test_create_run_returns_run_id():
    """POST /runs should return created run_id."""

async def test_get_orders_filters_by_run_id():
    """GET /orders?run_id=X should only return orders for that run."""

# tests/unit/glados/routes/test_sse.py
async def test_sse_stream_format():
    """SSE should use correct event format."""

async def test_sse_reconnection_with_last_event_id():
    """Should resume from Last-Event-ID header."""
```

**Implementation:**
- [ ] `glados/app.py` — FastAPI instance
- [ ] `glados/main.py` — Startup logic
- [ ] `glados/routes/api.py` — REST endpoints
- [ ] `glados/routes/sse.py` — SSE streaming

#### 2.3 Domain Routing (TDD)

**Tests First:**
```python
# tests/unit/glados/test_domain_router.py
def test_route_strategy_fetch_to_live():
    """strategy.FetchWindow → live.FetchWindow when mode=live."""

def test_route_strategy_fetch_to_backtest():
    """strategy.FetchWindow → backtest.FetchWindow when mode=backtest."""

def test_route_preserves_correlation_id():
    """Routed event should maintain corr_id."""
```

**Implementation:**
- [ ] `glados/domain_router.py`

### 13.7 Phase 3: Veda & Greta (Week 3–4)

#### 3.1 Veda (TDD)

**Tests First:**
```python
# tests/unit/veda/test_trading.py
def test_order_idempotency_same_client_order_id():
    """Same client_order_id should not place duplicate order."""

def test_order_side_conversion():
    """Should convert 'buy'/'sell' to exchange format."""

# tests/integration/veda/test_alpaca.py (with mocked HTTP)
async def test_fetch_crypto_bars():
    """Should parse Alpaca bar response correctly."""

async def test_submit_order_success():
    """Should handle successful order response."""

async def test_submit_order_insufficient_funds():
    """Should handle rejection gracefully."""
```

#### 3.2 Greta (TDD)

**Tests First:**
```python
# tests/unit/greta/test_simulator.py
def test_market_order_fill_with_slippage():
    """Market order should fill with configured slippage."""

def test_limit_order_fill_price_respected():
    """Limit order should not fill above limit price."""

def test_commission_calculation():
    """Commission should be calculated correctly."""

# tests/unit/greta/test_stats.py
def test_sharpe_ratio_calculation():
    """Should calculate Sharpe ratio correctly."""

def test_max_drawdown_calculation():
    """Should calculate max drawdown correctly."""
```

### 13.8 Phase 4: Marvin (Week 4–5)

**Tests First:**
```python
# tests/unit/marvin/test_base_strategy.py
def test_strategy_receives_tick():
    """Strategy on_tick should be called on clock.Tick."""

def test_strategy_emits_fetch_intent():
    """Strategy should emit strategy.FetchWindow."""

# tests/integration/marvin/test_sma_cross.py
async def test_sma_cross_generates_buy_signal():
    """SMA cross up should generate buy signal."""

async def test_sma_cross_generates_sell_signal():
    """SMA cross down should generate sell signal."""

# Property-based test
@given(prices=st.lists(st.floats(min_value=1, max_value=1000), min_size=50))
def test_sma_cross_never_crashes(prices):
    """SMA strategy should handle any valid price sequence."""
```

### 13.9 Phase 5: Haro Frontend (Week 5–7)

**Tests First (Playwright):**
```typescript
// tests/e2e/runs.spec.ts
test('can create a new run', async ({ page }) => {
  await page.goto('/runs');
  await page.click('button:has-text("New Run")');
  await page.fill('[name="strategy"]', 'sma_cross');
  await page.click('button:has-text("Start")');
  await expect(page.locator('.run-status')).toHaveText('Running');
});

test('can stop a running run', async ({ page }) => {
  // ...
});

test('displays real-time order updates', async ({ page }) => {
  // ...
});
```

### 13.10 Phase 6: Integration & E2E (Week 7–8)

**Full Flow Integration Tests:**
```python
# tests/integration/test_full_live_flow.py
async def test_live_order_flow_end_to_end():
    """
    1. Create run (mode=live)
    2. Clock ticks
    3. Strategy emits FetchWindow
    4. GLaDOS routes to live.FetchWindow
    5. Veda fetches data, emits data.WindowReady
    6. Strategy emits PlaceRequest
    7. Veda places order, emits orders.Placed
    8. WallE persists order
    9. SSE emits ui.OrderUpdated
    """

# tests/integration/test_full_backtest_flow.py
async def test_backtest_completes_with_stats():
    """
    1. Create run (mode=backtest, start/end dates)
    2. BacktestClock runs fast-forward
    3. Greta provides historical data
    4. Greta simulates fills
    5. Stats calculated at end
    """
```

### 13.11 Test Coverage Requirements

| Module | Min Coverage | Critical Paths |
|--------|--------------|----------------|
| `events/` | 90% | Outbox write, offset tracking |
| `glados/clock/` | 95% | Bar alignment, drift compensation |
| `glados/routes/` | 85% | All endpoints |
| `veda/` | 85% | Order idempotency |
| `greta/` | 90% | Fill simulation |
| `marvin/` | 85% | Strategy lifecycle |
| `walle/` | 80% | Repository CRUD |

### 13.12 CI Pipeline

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

### 13.13 Milestone Definitions (Updated for TDD)

| Milestone | Definition of Done | Status |
|-----------|-------------------|--------|
| **M0: Test Infra** | pytest runs; fixtures work; CI pipeline green | ✅ DONE |
| **M1: Foundation** | Events tests pass; DB tests pass; all repos tested |
| **M2: API Live** | Route tests pass; SSE tests pass; Clock tests pass (including edge cases) |
| **M3: Trading Works** | Veda tests pass with mocked exchange; Order idempotency proven |
| **M4: Backtest Works** | Greta simulation tests pass; Stats calculations verified |
| **M5: Strategy Runs** | Marvin tests pass; SMA strategy backtested successfully |
| **M6: UI Functional** | Playwright E2E tests pass |
| **M7: MVP Complete** | All tests pass; Coverage ≥80%; Docs complete |



## 14. Terms & Quick Reference

* **Modulith**: a single‑process architecture with multiple domain packages.
* **EventLog**: DB‑backed event log (Outbox + Offsets); `LISTEN/NOTIFY` is used only for wake‑ups.
* **Thin events**: keys/status only for realtime UI; details fetched via REST.
* **Domain routing**: translate `strategy.*` into `live.*` or `backtest.*` based on the execution domain.
* **RealtimeClock**: Wall‑clock aligned clock for live trading; ticks at bar boundaries.
* **BacktestClock**: Fast‑forward clock for simulation; no sleeping, advances immediately.
* **Bar Alignment**: Ticks fire at the start of each bar (e.g., minute boundary for 1m bars).

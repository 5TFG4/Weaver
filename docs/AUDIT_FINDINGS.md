# Architecture Audit Findings

> **Audit Date**: 2026-02-03 (Post-M4)  
> **Status**: ✅ M4 Complete — 631 tests passing  
> **Purpose**: Document design-vs-implementation inconsistencies for systematic resolution

---

## Executive Summary

A comprehensive audit revealed **29 issues** across all modules. The root cause is the existence of **two parallel architectures** (legacy vs. modern) that were never fully migrated. The system works for testing but has significant gaps for production use.

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | 11 | Broken integrations, dead code paths, production blockers |
| 🟡 Medium | 14 | Incomplete features, missing validation, test issues |
| 🟢 Low | 4 | Cleanup items, documentation gaps |

---

## Table of Contents

1. [Critical Issues](#1-critical-issues)
2. [Medium Issues](#2-medium-issues)
3. [Low Priority Issues](#3-low-priority-issues)
4. [Root Cause Analysis](#4-root-cause-analysis)
5. [Recommended Fix Order](#5-recommended-fix-order)
6. [Progress Tracking](#6-progress-tracking)

---

## 1. Critical Issues

### 1.1 Routes Use Module Singletons Instead of app.state

**Module**: GLaDOS  
**Files**: `src/glados/routes/runs.py`, `orders.py`, `candles.py`  
**Severity**: 🔴 Critical

**Problem**: All route files create their own service instances via lazy-initialized module globals instead of using services wired in the app lifespan.

```python
# Current pattern in routes/runs.py
_run_manager: RunManager | None = None

def get_run_manager() -> RunManager:
    global _run_manager
    if _run_manager is None:
        _run_manager = RunManager()  # Creates NEW instance!
    return _run_manager
```

**Impact**:
- Services in routes are disconnected from Database, EventLog, and VedaService initialized in lifespan
- RunManager operates in-memory only, not persisted to database
- No events flow through the system because routes don't use the EventLog

**Expected Behavior**: Routes should use dependency injection to get services from `request.app.state`.

**Fix Strategy**:
1. Add dependency functions in `dependencies.py` that pull from `app.state`
2. Update all routes to use `Depends(get_run_manager)` from dependencies
3. Remove module-level singleton pattern from route files

---

### 1.2 Orphan Files in GLaDOS (Legacy Architecture)

**Module**: GLaDOS  
**Files**: 
- `src/glados/glados.py` (old class-based implementation)
- `src/glados/data_manager.py`
- `src/glados/api_handler.py`
- `src/glados/event_bus.py`
- `src/glados/tasks.py`
- `src/glados/error_handler.py`
- `src/glados/routes/api.py` (empty placeholder)

**Severity**: 🔴 Critical

**Problem**: These files implement an old class-based GLaDOS architecture that is completely separate from the FastAPI app in `app.py`. They are never used by the current system.

**Impact**:
- Confusion about which implementation is authoritative
- Maintenance burden for dead code
- New developers may accidentally use the wrong system

**Fix Strategy**:
1. Verify no production code imports these files
2. Move to `src/glados/_deprecated/` or delete entirely
3. Document the migration in commit message

---

### 1.3 VedaService Created But Never Used

**Module**: Veda  
**Files**: `src/veda/veda_service.py`, `src/glados/app.py`

**Severity**: 🔴 Critical

**Problem**: `VedaService` is instantiated during app startup and stored in `app.state.veda_service`, but no routes or handlers actually use it. The order routes use `MockOrderService` instead.

```python
# In app.py lifespan - VedaService is created
veda_service = create_veda_service(...)
app.state.veda_service = veda_service

# In routes/orders.py - MockOrderService is used instead
from src.glados.services.order_service import MockOrderService
```

**Impact**:
- The entire VedaService integration (OrderManager, OrderRepository, EventLog, PositionTracker) is bypassed
- Orders are not persisted to database
- No order events flow through EventLog → SSE

**Fix Strategy**:
1. Create `get_veda_service()` dependency in `dependencies.py`
2. Update order routes to use VedaService for order operations
3. Remove MockOrderService or keep only for testing

---

### 1.4 AlpacaAdapter Clients Never Initialized

**Module**: Veda  
**File**: `src/veda/adapters/alpaca_adapter.py`

**Severity**: 🔴 Critical

**Problem**: The `AlpacaAdapter` class has `_trading_client` and `_data_client` attributes that are always `None`. There is no initialization code.

```python
class AlpacaAdapter(ExchangeAdapter):
    def __init__(self, credentials: AlpacaCredentials) -> None:
        self._credentials = credentials
        # Initialize clients (lazy - set directly in tests)
        self._trading_client: Any = None  # Always None!
        self._data_client: Any = None     # Always None!
```

**Impact**:
- Any real API call will fail with `AttributeError: 'NoneType' object has no attribute ...`
- Production trading is impossible
- Only MockAdapter works

**Contrast**: The legacy `alpaca_api_handler.py` does initialize clients:
```python
self.data_client = CryptoHistoricalDataClient(api_key=api_key)
self.trading_client = TradingClient(api_key=api_key, secret_key=api_secret, paper=True)
```

**Fix Strategy**:
1. Add actual client initialization in `AlpacaAdapter.__init__()` or a `connect()` method
2. Use the credentials to create Alpaca SDK clients
3. Add connection verification on startup

---

### 1.5 Duplicate Veda Implementations

**Module**: Veda  
**Files**: `src/veda/veda.py` vs `src/veda/veda_service.py`

**Severity**: 🔴 Critical

**Problem**: Two completely different classes exist for the same purpose with incompatible interfaces.

| Aspect | `Veda` class | `VedaService` class |
|--------|--------------|---------------------|
| File | `veda.py` | `veda_service.py` |
| Uses | `AlpacaAPIHandler` | `ExchangeAdapter` pattern |
| Order tracking | None | `OrderState` with persistence |
| Event emission | None | Emits to EventLog |
| Idempotency | None | Via OrderManager |

**Impact**:
- Unclear which is authoritative
- `Veda` class is used by legacy `GLaDOS` class
- `VedaService` is created but never used (see 1.3)

**Fix Strategy**:
1. Decide on one implementation (recommend `VedaService`)
2. Migrate any needed functionality from `Veda` to `VedaService`
3. Delete or deprecate the unused one

---

### 1.6 Missing Event Type Definition

**Module**: Events  
**Files**: `src/events/types.py`, `src/veda/veda_service.py`

**Severity**: 🔴 Critical

**Problem**: `"orders.Created"` is used in `veda_service.py` but is NOT defined in `types.py`.

```python
# veda_service.py line 98
event_type = (
    "orders.Rejected" if state.status == OrderStatus.REJECTED else "orders.Created"
)
```

The `OrderEvents` class in `types.py` defines:
- `SUBMITTED`, `ACCEPTED`, `FILLED`, `PARTIALLY_FILLED`, `CANCELLED`, `REJECTED`, `EXPIRED`

**Missing**: `CREATED`

**Impact**:
- Type validation would fail if registry validation is enabled
- Inconsistency between emitted events and defined types

**Fix Strategy**:
```python
# Add to src/events/types.py
class OrderEvents:
    CREATED: Final[str] = "orders.Created"  # Add this
    SUBMITTED: Final[str] = "orders.Submitted"
    # ... rest
```

---

### 1.7 LISTEN/NOTIFY Never Activated

**Module**: Events  
**Files**: `src/events/log.py`, `src/glados/app.py`

**Severity**: 🔴 Critical

**Problem**: PostgreSQL LISTEN/NOTIFY is implemented but never activated because no `asyncpg` pool is provided to `PostgresEventLog`.

```python
# app.py line 56 - pool is not provided
event_log = PostgresEventLog(session_factory=database.session_factory)
# Note: pool=None (not provided)

# log.py line 285-287 - listener task never created
if self._listener_task is None and self._pool is not None:
    self._listener_task = asyncio.create_task(self._listen_loop())
```

**Impact**:
- `pg_notify()` is called on every event append (working)
- But no listeners receive the notifications (broken)
- Real-time event delivery is completely non-functional

**Fix Strategy**:
1. Create asyncpg pool during app startup
2. Pass pool to `PostgresEventLog` constructor
3. Ensure `_listen_loop()` is started

```python
# In app.py lifespan
import asyncpg
pool = await asyncpg.create_pool(settings.database.url)
event_log = PostgresEventLog(session_factory=..., pool=pool)
```

---

### 1.8 Clock Not Integrated with Run/Strategy System

**Module**: Clock  
**Files**: `src/glados/clock/`, `src/glados/services/run_manager.py`

**Severity**: 🔴 Critical

**Problem**: The Clock module is completely isolated from the rest of the system. No code creates clocks for runs or connects tick callbacks to strategies.

| Component | Clock Usage | Status |
|-----------|-------------|--------|
| `RunManager` | No imports | ❌ Missing |
| `run_manager.start()` | No clock creation | ❌ Missing |
| Marvin | Only docstring mention | ❌ Placeholder |

**Impact**:
- Starting a run does not start a clock
- No tick events are generated
- Strategies cannot execute on schedule

**Fix Strategy**:
1. Add clock creation in `RunManager.start()`:
```python
async def start(self, run_id: str) -> Run:
    run = self._runs.get(run_id)
    config = ClockConfig(
        timeframe=run.timeframe,
        backtest_start=run.start_time if run.mode == "backtest" else None,
        backtest_end=run.end_time if run.mode == "backtest" else None,
    )
    self._clocks[run_id] = create_clock(config)
    self._clocks[run_id].on_tick(self._handle_tick)
    await self._clocks[run_id].start(run_id)
```

---

### 1.9 Legacy Database System in walle.py

**Module**: WallE  
**File**: `src/walle/walle.py`

**Severity**: 🔴 Critical

**Problem**: `walle.py` implements a completely separate synchronous database connection that bypasses the modern async architecture.

| Aspect | Modern (`database.py`) | Legacy (`walle.py`) |
|--------|------------------------|---------------------|
| Style | Async (SQLAlchemy 2.0) | Sync (SQLAlchemy 1.x) |
| Engine | `create_async_engine` | `create_engine` |
| Session | `AsyncSession` | `Session` |
| Driver | `asyncpg` | `psycopg2` |
| Config | `Database` class | Raw env vars |

**Impact**:
- Two database connections to same database
- Potential connection pool exhaustion
- Inconsistent transaction handling
- `TradeRecord` model is not tracked by Alembic

**Fix Strategy**:
1. If `walle.py` functionality is needed, migrate to async
2. If not needed, delete the file
3. Move any models to main `models.py`

---

### 1.10 trade_records Table Not Migrated

**Module**: WallE  
**Files**: `src/walle/walle.py`, `src/walle/migrations/`

**Severity**: 🔴 Critical

**Problem**: The `TradeRecord` model in `walle.py` defines a `trade_records` table that has no Alembic migration. It uses `Base.metadata.create_all()` directly.

**Impact**:
- Schema drift between environments
- Table may or may not exist depending on how app was started
- Migration conflicts if table is manually created

**Fix Strategy**:
1. Either create proper migration for `trade_records`
2. Or delete `TradeRecord` model if not needed

---

### 1.11 OrderRepository Session Leak

**Module**: Veda  
**File**: `src/veda/orders/repository.py`

**Severity**: 🔴 Critical

**Problem**: Repository methods don't use context managers for session handling.

```python
# Current (problematic)
async def save(self, order_state: OrderState) -> None:
    session = self._session_factory()  # Not using context manager
    veda_order = VedaOrder.from_order_state(order_state)
    await session.merge(veda_order)
    await session.commit()  # No error handling, no session close
```

**Impact**:
- Sessions may not be properly closed on errors
- Connection pool exhaustion over time
- Potential data corruption on partial failures

**Fix Strategy**:
```python
async def save(self, order_state: OrderState) -> None:
    async with self._session_factory() as session:
        veda_order = VedaOrder.from_order_state(order_state)
        await session.merge(veda_order)
        await session.commit()
```

---

## 2. Medium Issues

### 2.1 EventConsumer Class Never Used

**Module**: Events  
**File**: `src/events/offsets.py`

**Problem**: The `EventConsumer` class provides automatic offset tracking but is never instantiated anywhere.

**Impact**: Consumers must manually manage offsets; SSE broadcaster has no crash recovery.

**Fix**: Either use `EventConsumer` in SSE subscription or remove the class.

---

### 2.2 75%+ of Event Types Never Used

**Module**: Events  
**File**: `src/events/types.py`

**Problem**: Many event types are defined but never emitted in production code:
- `strategy.FetchWindow`, `strategy.PlaceRequest`, `strategy.DecisionMade`
- `live.FetchWindow`, `backtest.FetchWindow`, `backtest.PlaceOrder`
- `market.Quote`, `market.Trade`, `market.Bar`
- `system.Started`, `system.Stopping`, `system.Error`
- All `ui.*` events

**Impact**: Over-designed, dead code, confusing for developers.

**Fix**: Mark as "planned for M4+" or remove if not needed.

---

### 2.3 Event Registry Never Pre-populated

**Module**: Events  
**File**: `src/events/registry.py`

**Problem**: The global registry is never populated with event schemas. Validation has a fallback that allows unregistered events to pass.

```python
schema = self._schemas.get(event_type)
if schema is None:
    return  # Allow unregistered events - no validation!
```

**Impact**: No payload validation actually occurs.

**Fix**: Either pre-register schemas at startup or remove the registry if not needed.

---

### 2.4 Unused Config Classes

**Module**: Config  
**File**: `src/config.py`

**Problem**: `ServerConfig`, `EventConfig`, `TradingConfig` are defined but never referenced.

**Impact**: Dead code, confusion about which config is used.

**Fix**: Use them or remove them.

---

### 2.5 alpaca_api_handler.py Bypasses Config System

**Module**: Veda  
**File**: `src/veda/alpaca_api_handler.py`

**Problem**: Uses environment variables directly instead of the config system.

```python
api_key = os.getenv('ALPACA_API_KEY')
api_secret = os.getenv('ALPACA_SECRET_KEY')
```

**Impact**: Config inconsistency, harder to test, no dual-credential support.

**Fix**: Migrate to use `AlpacaCredentials` from config.

---

### 2.6 AlpacaCredentials May Expose Secrets

**Module**: Config  
**File**: `src/config.py`

**Problem**: `AlpacaCredentials` dataclass doesn't have `repr=False`, so default repr would expose secrets if logged.

**Fix**:
```python
@dataclass(frozen=True, repr=False)
class AlpacaCredentials:
    ...
    def __repr__(self) -> str:
        return f"AlpacaCredentials(api_key='***', base_url={self.base_url!r})"
```

---

### 2.7 Unused Exception Classes

**Module**: GLaDOS  
**File**: `src/glados/exceptions.py`

**Problem**: `RunNotStartableError` and `RunNotStoppableError` are defined but never raised.

**Impact**: Design says these should be used for state validation, but they're not.

**Fix**: Use them in `RunManager.start()` and `stop()` methods.

---

### 2.8 Routes Don't Emit Events (SSE is Dead)

**Module**: GLaDOS  
**Files**: `src/glados/routes/*.py`

**Problem**: Even though SSEBroadcaster is connected to EventLog, no routes emit events. When a run is created or stopped, no events are published.

**Impact**: SSE clients never receive real-time updates.

**Fix**: Add EventLog calls in routes/services:
```python
await event_log.append("runs.Created", {"run_id": run.id, "status": "pending"})
```

---

### 2.9 4h Timeframe Not Tested

**Module**: Clock  
**File**: `tests/unit/glados/clock/`

**Problem**: 4-hour bar alignment has no specific tests. May not align correctly with market open times.

**Fix**: Add tests for 4h timeframe alignment.

---

### 2.10 Documentation Says "Busy-Wait" But Implementation Uses Sleep

**Module**: Clock  
**File**: `src/glados/clock/realtime.py`

**Problem**: Documentation mentions busy-wait for precision, but implementation only uses `asyncio.sleep()`.

**Impact**: May have 10-20ms drift on tick timing.

**Fix**: Either implement busy-wait or update documentation.

---

### 2.11 Inconsistent Database Cleanup in Tests

**Module**: Tests  
**Files**: `tests/conftest.py`, `tests/integration/conftest.py`

**Problem**: Main conftest only cleans `veda_orders` table, but integration conftest cleans all tables.

**Impact**: Tests may have dirty state when run in different orders.

**Fix**: Use consistent cleanup across all test fixtures.

---

### 2.12 Tests That Only Check Method Existence

**Module**: Tests  
**Files**: Various test files

**Problem**: Multiple tests only verify methods exist without testing behavior:
```python
def test_has_submit_order_method(self, mock_adapter) -> None:
    manager = OrderManager(adapter=mock_adapter)
    assert hasattr(manager, "submit_order")
    assert callable(manager.submit_order)
```

**Impact**: False sense of coverage; tests pass even if method is broken.

**Fix**: Add behavioral assertions to these tests.

---

### 2.13 Async Tests Use Sleep for Synchronization

**Module**: Tests  
**Files**: `tests/unit/glados/test_sse_broadcaster.py`

**Problem**: Tests use `asyncio.sleep(0.01)` for synchronization, which is a race condition.

```python
task = asyncio.create_task(collect())
await asyncio.sleep(0.01)  # Race condition!
await broadcaster.publish("test.event", {"data": "hello"})
```

**Impact**: Tests may be flaky under load.

**Fix**: Use `asyncio.Event` or similar synchronization primitives.

---

### 2.14 Factories Create Dicts Instead of Model Instances

**Module**: Tests  
**Files**: `tests/factories/*.py`

**Problem**: Factories return `dict` instead of actual model instances. Status values are strings, not enums.

**Impact**: Tests may pass with invalid data that would fail in production.

**Fix**: Have factories create actual Pydantic models or dataclasses.

---

## 3. Low Priority Issues

### 3.1 Empty Stub Files in WallE

**Files**: `src/walle/data_storage.py`, `src/walle/data_retrieval.py`

**Problem**: These files exist but are empty or contain only docstrings.

**Fix**: Implement or delete.

---

### 3.2 Empty E2E Tests Directory

**File**: `tests/e2e/__init__.py`

**Problem**: E2E test directory is registered but contains no tests.

**Fix**: Add tests or remove marker.

---

### 3.3 DRIFT_WARNING_THRESHOLD Never Used

**File**: `src/glados/clock/realtime.py`

**Problem**: Constant is defined but never referenced.

**Fix**: Use it or remove it.

---

### 3.4 Documentation Missing Timeframes

**File**: `docs/architecture/clock.md`

**Problem**: Timeframe table was missing 30m and 4h, which are supported in code.

**Status**: ✅ Fixed 2026-02-03 - Added 30m and 4h to documentation.

---

## 4. Root Cause Analysis

### The Two-Architecture Problem

The codebase evolved through multiple iterations without completing migrations:

```
Legacy Architecture (Abandoned)          Modern Architecture (Incomplete)
────────────────────────────────        ────────────────────────────────
src/glados/glados.py                    src/glados/app.py (FastAPI)
  ├── GLaDOS class                        ├── lifespan
  ├── data_manager.py                     ├── routes/*.py
  ├── api_handler.py                      ├── services/*.py
  ├── event_bus.py                        └── sse_broadcaster.py
  └── tasks.py                          

src/veda/veda.py                        src/veda/veda_service.py
  └── Veda class                          └── VedaService class

src/walle/walle.py (sync)               src/walle/database.py (async)
  └── Synchronous psycopg2                └── Async asyncpg

src/veda/alpaca_api_handler.py          src/veda/adapters/alpaca_adapter.py
  └── Direct env vars                     └── Uses config system
```

### Broken Connection Points

1. **Routes → Services**: Routes create own instances instead of using app.state
2. **VedaService → Routes**: Created but never called
3. **EventLog → SSE**: Connected but no events produced
4. **Clock → Runs**: Completely disconnected
5. **Database → Repositories**: Repository doesn't use context managers

---

## 5. Milestone-Based Fix Schedule (Revised 2026-02-03)

> Issues scheduled per [MILESTONE_PLAN.md](MILESTONE_PLAN.md) and [roadmap.md](architecture/roadmap.md).

### M5: Marvin Core (Strategy System)

| Issue | Task | MVP |
|-------|------|-----|
| 1.7 | EventLog subscription | M5-1 |
| 2.1 | EventConsumer (subscribe pattern) | M5-1 |
| - | data.WindowReady flow | M5-2 |
| - | SMA Strategy implementation | M5-3 |
| - | PluginStrategyLoader | M5-4 |
| 2.2 | Unused event types (strategy.*) | M5-3 |
| M4 #4 | SimulatedFill.side enum | M5-5 |
| M4 #5 | ClockTick duplicate | M5-5 |

### M6: Live Trading (Paper/Live Flow)

| Issue | Task | MVP |
|-------|------|-----|
| - | PluginAdapterLoader | M6-1 |
| 1.4 | AlpacaAdapter clients init | M6-2 |
| 1.3 | VedaService routing | M6-3 |
| - | Live order flow | M6-4 |
| - | Run mode integration | M6-5 |

### M7: Haro Frontend

| Issue | Task | MVP |
|-------|------|-----|
| - | React scaffold | M7-1 |
| - | Dashboard page | M7-2 |
| - | Runs page | M7-3 |
| - | Orders page | M7-4 |
| - | SSE integration | M7-5 |

### M8: Polish & E2E

| Issue | Task | MVP |
|-------|------|-----|
| 2.3 | Registry not pre-populated | M8-4 |
| 2.4 | Unused config classes | M8-4 |
| 2.6 | Credentials repr security | M8-4 |
| 2.9-2.14 | Test improvements | M8-4 |
| 3.x | Low priority items | M8-4 |
| - | Sharpe ratio, max drawdown | M8-4 |
| - | E2E tests (Playwright) | M8-1~3 |
| - | Documentation | M8-5 |

---

## 6. Progress Tracking

### Status Legend
- ⬜ Not Started
- 🟨 In Progress  
- ✅ Completed
- ❌ Blocked

### Batch 0: Legacy Cleanup (2026-02-02) ✅
| Task | Status | Date | Notes |
|------|--------|------|-------|
| Delete orphan GLaDOS files | ✅ | 2026-02-02 | Removed 7 files |
| Delete orphan Veda files | ✅ | 2026-02-02 | Removed: veda.py, alpaca_api_handler.py |
| Delete orphan WallE files | ✅ | 2026-02-02 | Removed: walle.py, data_storage.py, data_retrieval.py |
| Update weaver.py entry point | ✅ | 2026-02-02 | Now uses FastAPI create_app() |
| Update __init__.py exports | ✅ | 2026-02-02 | GLaDOS exports create_app, Veda exports VedaService |

### M3.5: Integration Fixes ✅
| Task | Status | Date | Notes |
|------|--------|------|-------|
| Add `orders.Created` to types.py | ✅ | 2026-02-02 | Trivial |
| Fix OrderRepository session handling | ✅ | 2026-02-02 | All 6 methods use `async with` |
| Use/remove unused exceptions | ✅ | 2026-02-02 | RunNotStartableError now used |
| Create proper dependencies.py | ✅ | 2026-02-02 | 7 getters + 9 tests |
| Update routes to use Depends() | ✅ | 2026-02-02 | All 4 route files migrated |
| Wire VedaService to routes | ⏳ | | Deferred to M5 (needs real orders) |
| Add event emission in services | ✅ | 2026-02-02 | RunManager emits run.* events + 5 tests |
| Code review fixes | ✅ | 2026-02-02 | PR feedback addressed |
| **Total new tests** | | | **+15 tests** |

### M4: Greta Backtest Engine ✅ COMPLETED (2026-02-03)

**Branch**: `greta_update` → PR #9 merged  
**Changes**: 37 files, +6649/-81 lines

| Task | Status | Date | Notes |
|------|--------|------|-------|
| **MVP-1**: WallE BarRepository | ✅ | 2026-02-03 | 16 tests, bars table + migration |
| **MVP-2**: Greta Models & FillSimulator | ✅ | 2026-02-03 | 29 tests, TDD red→green |
| **MVP-3**: GretaService (uses BarRepo) | ✅ | 2026-02-03 | 20 tests, per-run instance |
| **MVP-4**: Marvin Skeleton | ✅ | 2026-02-03 | 32 tests, BaseStrategy + StrategyRunner |
| **MVP-5**: GLaDOS DomainRouter | ✅ | 2026-02-03 | 12 tests, strategy.* → backtest.* |
| **MVP-6**: Run Orchestration | ✅ | 2026-02-03 | 10 tests, RunContext + async tick |
| **MVP-7**: Integration Test | ✅ | 2026-02-03 | 5 tests, end-to-end flow |
| Code review (20 comments) | ✅ | 2026-02-03 | All addressed |
| Provide asyncpg pool to EventLog | ⬜ | | Deferred (nice-to-have) |
| **Actual new tests** | | | **+125 tests (631 total)** |

#### M4 New Files Created

| File | Purpose | Tests |
|------|---------|-------|
| `src/greta/models.py` | FillSimulationConfig, SimulatedFill, SimulatedPosition, BacktestStats, BacktestResult | 20 |
| `src/greta/fill_simulator.py` | DefaultFillSimulator with slippage/commission/limit/stop | 29 |
| `src/greta/greta_service.py` | Per-run backtest execution engine | 20 |
| `src/marvin/base_strategy.py` | BaseStrategy ABC, StrategyAction frozen dataclass | 9 |
| `src/marvin/strategy_runner.py` | Executes strategy on_tick/on_data, emits strategy.* events | 12 |
| `src/marvin/sample_strategy.py` | Mean-reversion demo strategy (buy low, sell high) | 11 |
| `src/glados/services/domain_router.py` | Routes strategy.* → backtest.*/live.* based on RunMode | 12 |
| `src/walle/repositories/__init__.py` | Package exports | - |
| `src/walle/repositories/bar_repository.py` | BarRepository + Bar frozen DTO, upsert support | 16 |
| `src/walle/migrations/*_add_bars_table.py` | bars table: symbol, timeframe, timestamp, OHLCV | - |
| `tests/integration/test_backtest_flow.py` | End-to-end backtest: RunManager → Clock → Strategy → Greta | 5 |
| `tests/integration/test_bar_repository.py` | BarRepository PostgreSQL integration tests | 16 |
| `docs/archive/milestone-details/m4-greta.md` | M4 design document with architecture diagrams | - |

#### M4 Modified Files

| File | Change |
|------|--------|
| `src/glados/services/run_manager.py` | Added RunContext dataclass, _start_backtest() method, try/finally cleanup, RunStatus.ERROR on failure |
| `src/glados/clock/base.py` | Made _emit_tick() async, added callback_timeout (default 30s), asyncio.wait_for() protection |
| `src/glados/clock/backtest.py` | await _emit_tick() |
| `src/glados/clock/realtime.py` | await _emit_tick() |
| `src/events/types.py` | Added RunEvents.COMPLETED constant |
| `src/greta/__init__.py` | Export GretaService, FillSimulationConfig, BacktestResult |
| `src/marvin/__init__.py` | Export BaseStrategy, StrategyAction, StrategyRunner |
| `src/marvin/strategy_loader.py` | Updated type hints for BaseStrategy |
| `src/walle/models.py` | Added BarRecord model with UNIQUE_CONSTRAINT class constant |
| `tests/integration/conftest.py` | Import updates for new modules |
| `tests/unit/walle/test_models.py` | Assert 4 tables (outbox, consumer_offsets, bars, veda_orders) |
| `docs/ARCHITECTURE.md` | Updated test count to 631, M4 status |
| `docs/architecture/roadmap.md` | M4 entry gate checked, M5 exit gate added |
| `docs/architecture/clock.md` | Added callback_timeout documentation |
| `docs/architecture/events.md` | Event namespace updates for strategy.*/backtest.* |

#### M4 Code Review Fixes (2026-02-03)

20 GitHub Copilot code review comments addressed:

| Category | Issue | Fix | Files |
|----------|-------|-----|-------|
| **Readability** | Position sizing logic hard to follow | Added `_is_adding_to_position()`, `_is_position_reversal()` static methods with docstrings | greta_service.py |
| **Bug** | Resource leak on backtest failure | Wrapped clock.start() in try/finally to cleanup RunContext | run_manager.py |
| **Cleanup** | ~15 unused imports | Removed unused `Decimal`, `patch`, `timedelta`, `pytest` imports | tests/*.py |
| **Cleanup** | Redundant Envelope ID generation | Removed `id=str(uuid4())` - Envelope has default_factory | strategy_runner.py, domain_router.py |
| **Cleanup** | Unused dataclass import | Removed `from dataclasses import dataclass` | fill_simulator.py |
| **Cleanup** | Unused field import | Removed `from dataclasses import field` | base_strategy.py |
| **Cleanup** | Unused OrderSide import | Removed unused import | test_models.py (greta) |
| **Quality** | Magic string for constraint name | Defined `BarRecord.UNIQUE_CONSTRAINT = "uq_bar"` | models.py, bar_repository.py |
| **Quality** | Anonymous tick objects in tests | Added `make_tick()` factory using real `ClockTick` dataclass | test_sample_strategy.py, test_strategy_runner.py |
| **Quality** | Weak PnL assertion | Changed `pnl > 0` to `150 < pnl <= 300` for meaningful validation | test_greta_service.py |
| **Docs** | Decimal serialization unclear | Added docstring note about str serialization for precision | strategy_runner.py |
| **Docs** | Position reversal edge case | Added docstring note about new_qty == 0 handling | greta_service.py |

#### M4 Design Notes & TODOs

1. **EventLog Pattern**: `InMemoryEventLog` for unit tests, `PostgresEventLog` for integration.
   - Rationale: Unit tests shouldn't need DB
   - Alternative: Use PostgresEventLog with test DB everywhere (more realistic)
   - Decision: Keep as-is for now, evaluate in M5

2. **Greta/Marvin Test Coupling**: `test_backtest_flow.py` contains `SimpleTestStrategy` and `MockStrategyLoader`
   - These are integration test fixtures, not production code
   - Consider moving to `tests/fixtures/strategy.py` in M5 for reuse
   - GretaService itself has no Marvin imports (clean separation)

3. **StrategyRunner Location**: Lives in `src/marvin/` as designed
   - Uses injection (`event_log`, `strategy`) - no hardcoded dependencies
   - Integration test wires it with GretaService via RunManager

4. **SimulatedFill.side Type**: Currently `str` ("buy"/"sell"), should be `OrderSide` enum
   - Impact: Comparison uses `fill.side == OrderSide.BUY.value` instead of direct enum
   - Fix: Change `SimulatedFill.side: str` → `side: OrderSide` in M5
   - Files affected: `src/greta/models.py`, `src/greta/fill_simulator.py`, `src/greta/greta_service.py`

5. **Duplicate ClockTick Definition**: `tests/fixtures/clock.py` duplicates `src/glados/clock/base.py`
   - `ControllableClock` uses its own local `ClockTick` dataclass
   - Should import from `src/glados/clock/base` to avoid drift
   - Fix: Remove duplicate, update `ControllableClock` to use production `ClockTick`
   - Files affected: `tests/fixtures/clock.py`, `tests/unit/test_infrastructure.py`

6. **VedaOrder Model Location**: ✅ FIXED - Moved from `veda/persistence.py` to `walle/models.py`
   - **Problem**: SQLAlchemy models inherit from shared `Base`, but VedaOrder was in veda/
   - **Impact**: `Base.metadata.tables` count varied (3 vs 4) depending on import order
   - **Fix**: All SQLAlchemy models MUST be in `walle/models.py` for consistent metadata
   - **Pattern**: Domain modules (veda/) import models from `walle/models.py`, not define them
   - Conversion functions (`veda_order_to_order_state`, `order_state_to_veda_order`) stay in veda/
   - Files changed: `src/walle/models.py`, `src/veda/persistence.py`, `tests/unit/veda/test_persistence.py`

---

## M5: Marvin Core (Strategy System) 🟨 IN PROGRESS

**Design Document**: [m5-marvin.md](archive/milestone-details/m5-marvin.md)  
**Start Date**: 2026-02-03

### M5-1: EventLog Subscription ✅ COMPLETED (12 tests)
| Task | Status | Notes |
|------|--------|-------|
| Add `Subscription` dataclass to protocol.py | ✅ | With `matches()` method for filtering |
| Add `subscribe_filtered()` to EventLog ABC | ✅ | Returns subscription ID |
| Add `unsubscribe_by_id()` to EventLog ABC | ✅ | Safe no-op for unknown ID |
| Implement in InMemoryEventLog | ✅ | Full filtering support |
| Implement in PostgresEventLog | ✅ | Uses LISTEN/NOTIFY |
| Test: subscribe returns unique ID | ✅ | test_subscription.py |
| Test: subscriber receives matching events | ✅ | Type filtering works |
| Test: subscriber ignores non-matching events | ✅ | |
| Test: custom filter_fn works | ✅ | e.g., filter by run_id |
| Test: unsubscribe stops delivery | ✅ | |
| Test: multiple subscribers same event | ✅ | Both receive |
| Test: subscriber error doesn't break others | ✅ | Logs error, continues |
| Test: wildcard subscription ["*"] | ✅ | Receives all events |
| Test: multiple event types | ✅ | ["type.A", "type.B"] |
| Test: unsubscribe unknown ID is safe | ✅ | No error raised |
| Test: each subscription unique ID | ✅ | |
| Test: filter_fn with payload check | ✅ | |
| **Total tests added** | | **+12 tests (643 total)** |

#### M5-1 Files Changed
| File | Change |
|------|--------|
| `src/events/protocol.py` | Added `Subscription` dataclass with `matches()` |
| `src/events/log.py` | Added `subscribe_filtered()`, `unsubscribe_by_id()` to ABC, InMemoryEventLog, PostgresEventLog |
| `tests/unit/events/test_subscription.py` | **Created**: 12 tests for subscription functionality |

### M5-2: data.WindowReady Flow ✅ COMPLETED (15 tests)
| Task | Status | Notes |
|------|--------|-------|
| StrategyRunner subscribes to data.WindowReady | ✅ | In initialize() |
| StrategyRunner filters by run_id | ✅ | Only own run's events |
| StrategyRunner calls strategy.on_data() | ✅ | On WindowReady |
| StrategyRunner cleanup unsubscribes | ✅ | Async cleanup |
| GretaService subscribes to backtest.FetchWindow | ✅ | In initialize() |
| GretaService emits data.WindowReady | ✅ | With bars from cache |
| GretaService filters by run_id | ✅ | Only own run's events |
| GretaService preserves correlation_id | ✅ | For request tracking |
| Test: Runner subscribes on init | ✅ | test_strategy_runner_events.py |
| Test: WindowReady calls on_data | ✅ | |
| Test: Filters by run_id | ✅ | |
| Test: on_data emits PlaceRequest | ✅ | |
| Test: cleanup unsubscribes | ✅ | |
| Test: multiple events delivered | ✅ | |
| Test: on_tick emits FetchWindow | ✅ | |
| Test: subscription ID stored | ✅ | |
| Test: Greta subscribes on init | ✅ | test_greta_events.py |
| Test: FetchWindow → WindowReady | ✅ | |
| Test: Greta filters by run_id | ✅ | |
| Test: uses bar cache | ✅ | |
| Test: WindowReady includes bars | ✅ | |
| Test: Greta subscription ID stored | ✅ | |
| Test: correlation ID preserved | ✅ | |
| **Total tests added** | | **+15 tests (658 total)** |

#### M5-2 Files Changed
| File | Change |
|------|--------|
| `src/marvin/strategy_runner.py` | Added `_subscription_id`, `subscribe_filtered()` in init, `cleanup()`, `_on_window_ready()` |
| `src/greta/greta_service.py` | Added `_subscription_id`, `subscribe_filtered()` in init, `_on_fetch_window()`, `_handle_fetch_window()` |
| `tests/unit/marvin/test_strategy_runner_events.py` | **Created**: 8 tests for runner event handling |
| `tests/unit/greta/test_greta_events.py` | **Created**: 7 tests for Greta event handling |

### M5-3: SMA Strategy (~12 tests)
| Task | Status | Notes |
|------|--------|-------|
| Create src/marvin/strategies/ package | ⬜ | |
| Implement SMAStrategy with crossover logic | ⬜ | |
| Configurable fast_period, slow_period | ⬜ | |
| Test: SMA calculation | ⬜ | |
| Test: crossover signal generation | ⬜ | |
| Integration: SMA backtest with trades | ⬜ | |

### M5-4: Plugin Strategy Loader (~15 tests)
| Task | Status | Notes |
|------|--------|-------|
| Create StrategyMeta dataclass | ⬜ | Plugin metadata |
| Create @strategy decorator (optional) | ⬜ | |
| Implement PluginStrategyLoader | ⬜ | Auto-discovery |
| Dependency resolution (topological sort) | ⬜ | |
| Move sample_strategy.py to strategies/ | ⬜ | Add STRATEGY_META |
| Remove hardcoded imports from __init__.py | ⬜ | Delete safety |
| Test: discover strategies | ⬜ | |
| Test: load by ID | ⬜ | |
| Test: dependency resolution | ⬜ | |
| Test: deleted strategy = system works | ⬜ | |
| Test: missing dependency error | ⬜ | |

### M5-5: Code Quality - Marvin (~8 tests)
| Task | Status | Notes |
|------|--------|-------|
| SimulatedFill.side: str → OrderSide | ⬜ | M4 note #4 |
| Extract SimpleTestStrategy to fixtures | ⬜ | M4 note #2 |
| Extract MockStrategyLoader to fixtures | ⬜ | M4 note #2 |
| Fix ClockTick duplicate definition | ⬜ | M4 note #5 |
| Clock Union type | ⬜ | run_manager.py TODO |

---

## M6: Live Trading (Paper/Live Flow)

### M6-1: Plugin Adapter Loader (~10 tests)
| Task | Status | Notes |
|------|--------|-------|
| Create AdapterMeta dataclass | ⬜ | Plugin metadata |
| Implement PluginAdapterLoader | ⬜ | Auto-discovery |
| Add ADAPTER_META to alpaca_adapter.py | ⬜ | |
| Add ADAPTER_META to mock_adapter.py | ⬜ | |
| Remove hardcoded imports from adapters/__init__.py | ⬜ | Delete safety |
| Test: discover adapters | ⬜ | |
| Test: load by ID | ⬜ | |
| Test: deleted adapter = system works | ⬜ | |
| Test: feature support query | ⬜ | |

### M6-2: AlpacaAdapter Init (~12 tests)
| Task | Status | Notes |
|------|--------|-------|
| Add connect() method to AlpacaAdapter | ⬜ | Issue 1.4 |
| Initialize TradingClient | ⬜ | |
| Initialize CryptoHistoricalDataClient | ⬜ | |
| Add connection verification | ⬜ | |
| Error handling: invalid credentials | ⬜ | |
| Error handling: network timeout | ⬜ | |
| Test: connection success | ⬜ | |
| Test: Paper vs Live mode | ⬜ | |

### M6-3: VedaService Routing (~10 tests)
| Task | Status | Notes |
|------|--------|-------|
| Add get_veda_service to dependencies.py | ⬜ | Issue 1.3 |
| Update order routes to use VedaService | ⬜ | |
| Remove/deprecate MockOrderService | ⬜ | |
| Test: route injection | ⬜ | |
| Test: order creation via VedaService | ⬜ | |

### M6-4: Live Order Flow (~15 tests)
| Task | Status | Notes |
|------|--------|-------|
| VedaService subscribes to live.PlaceOrder | ⬜ | |
| DomainRouter routes to live.* for live mode | ⬜ | |
| Order status sync (submitted → filled) | ⬜ | |
| Test: paper order submit | ⬜ | |
| Test: paper order fill | ⬜ | |
| Test: order cancel | ⬜ | |
| Test: partial fill | ⬜ | |

### M6-5: Run Mode Integration (~8 tests)
| Task | Status | Notes |
|------|--------|-------|
| RunManager supports live runs (RealtimeClock) | ⬜ | |
| Live Run uses real market time | ⬜ | |
| Backtest/Live switch correctly | ⬜ | |
| Test: create live run | ⬜ | |
| Test: live run uses RealtimeClock | ⬜ | |
| Test: stop live run | ⬜ | |

---

## M7: Haro Frontend

| Task | Status | Notes |
|------|--------|-------|
| React scaffold + Vite + TypeScript | ⬜ | M7-1 |
| Docker build configuration | ⬜ | M7-1 |
| Dashboard page | ⬜ | M7-2 |
| Runs page (list + detail) | ⬜ | M7-3 |
| Orders page | ⬜ | M7-4 |
| SSE client integration | ⬜ | M7-5 |

---

## M8: Polish & E2E

| Task | Status | Notes |
|------|--------|-------|
| Playwright E2E setup | ⬜ | M8-1 |
| E2E: backtest flow | ⬜ | M8-2 |
| E2E: live flow | ⬜ | M8-3 |
| Clean all TODO/FIXME | ⬜ | M8-4 |
| Sharpe ratio calculation | ⬜ | M8-4 |
| Max drawdown calculation | ⬜ | M8-4 |
| Credentials repr security | ⬜ | M8-4 |
| Remove unused config/event types | ⬜ | M8-4 |
| Documentation update | ⬜ | M8-5 |
| Strategy development guide | ⬜ | M8-5 |
| Adapter development guide | ⬜ | M8-5 |

---

*Last Updated: 2026-02-03 (Milestone plan reorganized: M5-M8)*

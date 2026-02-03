# Architecture Audit Findings

> **Audit Date**: 2026-02-02 (Post-M3)  
> **Status**: ✅ M3.5 Complete — 506 tests passing  
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

## 5. Milestone-Based Fix Schedule

> Issues are now scheduled into milestones per [roadmap.md](architecture/roadmap.md).
> See Section 4 of roadmap for M3.5 full design.

### M3.5: Integration Fixes (Before M4)

| Issue | Task | Complexity |
|-------|------|------------|
| 1.1 | Routes use module singletons → Use Depends() | Medium |
| 1.3 | VedaService unused → Wire to routes | Medium |
| 1.6 | `orders.Created` undefined → Add to types.py | Trivial |
| 1.11 | OrderRepository session leak → Use context managers | Trivial |
| 2.7 | Unused exceptions → Use or remove | Trivial |
| 2.8 | Routes don't emit events → Add EventLog calls | Medium |

### M4: With Greta (Backtest)

| Issue | Task | Notes |
|-------|------|-------|
| 1.7 | LISTEN/NOTIFY not activated | Real-time for live runs |
| 1.8 | Clock not integrated | Greta needs clock |
| 2.1 | EventConsumer unused | Useful for replay |

### M5: With Marvin (Strategy)

| Issue | Task | Notes |
|-------|------|-------|
| 1.4 | AlpacaAdapter clients null | Live trading needs this |
| 2.2 | 75% event types unused | Strategy events |

### M7: Polish

| Issue | Task |
|-------|------|
| 2.3 | Registry not pre-populated |
| 2.4 | Unused config classes |
| 2.6 | Credentials repr security |
| 2.9-2.14 | Test improvements |
| 3.x | Low priority items |

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
| Task | Status | Date | Notes |
|------|--------|------|-------|
| **MVP-1**: WallE BarRepository | ✅ | 2026-02-03 | 16 tests, bars table + migration |
| **MVP-2**: Greta Models & FillSimulator | ✅ | 2026-02-03 | 29 tests, TDD red→green |
| **MVP-3**: GretaService (uses BarRepo) | ✅ | 2026-02-03 | 20 tests, per-run instance |
| **MVP-4**: Marvin Skeleton | ✅ | 2026-02-03 | 32 tests, BaseStrategy + StrategyRunner |
| **MVP-5**: GLaDOS DomainRouter | ✅ | 2026-02-03 | 12 tests, strategy.* → backtest.* |
| **MVP-6**: Run Orchestration | ✅ | 2026-02-03 | 10 tests, RunContext + async tick |
| **MVP-7**: Integration Test | ✅ | 2026-02-03 | 5 tests, end-to-end flow |
| Provide asyncpg pool to EventLog | ⬜ | | Deferred (nice-to-have) |
| **Actual new tests** | | | **+79 tests (631 total)** |

#### M4 New Files Created

| File | Purpose |
|------|---------|
| `src/greta/models.py` | FillSimulationConfig, SimulatedFill, SimulatedPosition, BacktestStats |
| `src/greta/fill_simulator.py` | DefaultFillSimulator with slippage/commission |
| `src/greta/greta_service.py` | Per-run backtest execution engine |
| `src/marvin/base_strategy.py` | BaseStrategy ABC, StrategyAction dataclass |
| `src/marvin/strategy_runner.py` | Executes strategy, emits events |
| `src/marvin/sample_strategy.py` | Mean-reversion test strategy |
| `src/glados/services/domain_router.py` | Routes strategy.* → backtest.*/live.* |
| `src/walle/repositories/bar_repository.py` | BarRepository + Bar DTO |
| `src/walle/migrations/versions/*_add_bars_table.py` | bars table migration |

#### M4 Modified Files

| File | Change |
|------|--------|
| `src/glados/services/run_manager.py` | Added RunContext, _start_backtest() |
| `src/glados/clock/base.py` | Made _emit_tick() async |
| `src/glados/clock/backtest.py` | await _emit_tick() |
| `src/glados/clock/realtime.py` | await _emit_tick() |
| `src/events/types.py` | Added RunEvents.COMPLETED |

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

### M5: Marvin Full Implementation
| Task | Status | Date | Notes |
|------|--------|------|-------|
| Complete Marvin strategy loading | ⬜ | | |
| Initialize AlpacaAdapter clients | ⬜ | | Live trading needs this |
| Wire VedaService to order routes | ⬜ | | Deferred from M3.5 |
| Implement SMA strategy | ⬜ | | |
| Live order flow (paper mode) | ⬜ | | |

### M7: Polish
| Task | Status | Date | Notes |
|------|--------|------|-------|
| Fix test cleanup consistency | ⬜ | | |
| Add behavioral assertions | ⬜ | | |
| Remove unused config/event types | ⬜ | | |
| Security: credentials repr | ⬜ | | |

---

*Last Updated: 2026-02-03*

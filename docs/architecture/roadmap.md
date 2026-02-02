# Implementation Roadmap

> Part of [Architecture Documentation](../ARCHITECTURE.md)
> 
> For development methodology, see [DEVELOPMENT.md](../DEVELOPMENT.md)  
> For audit findings, see [AUDIT_FINDINGS.md](../AUDIT_FINDINGS.md)

---

## 1. Current State

| Component | Status | Tests |
|-----------|--------|-------|
| **Python Environment** | ✅ 3.13 | - |
| **Test Infrastructure** | ✅ Complete | 493 passing |
| **Events Module** | ⚠️ Core done, integration gaps | 33 tests |
| **Clock Module** | ✅ Complete (not integrated) | 93 tests (93% cov) |
| **Config Module** | ✅ Dual credentials | 24 tests |
| **GLaDOS API (M2)** | ⚠️ Routes work, DI incomplete | 85 tests |
| **Veda Trading (M3)** | ⚠️ Tests pass, not wired to API | 196 tests |
| **WallE/DB** | ⚠️ Basic models | ~30% |
| **Greta (backtest)** | ❌ Empty shell | 0% |
| **Marvin (strategy)** | ❌ Empty shell | 0% |
| **Haro (frontend)** | ❌ Not started | 0% |

## 2. Milestones (Revised)

| Milestone | Definition of Done | Status |
|-----------|-------------------|--------|
| **M0–M3** | Foundation, API, Trading | ✅ DONE |
| **M3.5** | Integration fixes (audit remediation) | ⏳ NEXT |
| **M4** | Greta simulation; Stats verified | ⏳ PENDING |
| **M5** | Marvin tests; SMA backtested | ⏳ PENDING |
| **M6** | Playwright E2E tests pass | ⏳ PENDING |
| **M7** | All tests; Coverage ≥80%; Docs | ⏳ PENDING |

### M3.5: Integration Fixes (NEW)

> **Purpose**: Fix design-vs-implementation gaps discovered in audit before proceeding to M4.
> Without these fixes, M4 (Greta) cannot properly integrate with the system.

**Definition of Done**:
- Routes use app.state services (not module singletons)
- VedaService connected to order routes
- EventLog → SSE pipeline working end-to-end
- All 493+ tests still passing

## 3. Audit Issue Classification

Issues from [AUDIT_FINDINGS.md](../AUDIT_FINDINGS.md) are classified by when to fix:

### Fix in M3.5 (Required for M4)

These block Greta/Marvin integration:

| Issue | Why M3.5 | Complexity |
|-------|----------|------------|
| 1.1 Routes use module singletons | Greta needs proper DI | Medium |
| 1.3 VedaService unused | Greta needs order flow | Medium |
| 1.6 `orders.Created` undefined | Event flow broken | Trivial |
| 1.11 OrderRepository session leak | DB corruption risk | Trivial |
| 2.7 Unused exceptions | Clean up before adding more | Trivial |
| 2.8 Routes don't emit events | SSE dead without this | Medium |

### Fix in M4 (With Greta)

These are naturally addressed when implementing Greta:

| Issue | Why M4 | Notes |
|-------|--------|-------|
| 1.8 Clock not integrated | Greta needs clock for backtest | Part of Greta design |
| 1.7 LISTEN/NOTIFY not activated | Real-time needed for live runs | Can test with Greta |
| 2.1 EventConsumer unused | Useful for Greta event replay | Design into Greta |

### Fix in M5 (With Marvin)

These relate to strategy execution:

| Issue | Why M5 | Notes |
|-------|--------|-------|
| 1.4 AlpacaAdapter clients null | Only needed for live trading | Marvin will test live mode |
| 2.2 75% event types unused | Many are strategy events | Will use in Marvin |

### Fix in M7 (Polish)

Low priority cleanup:

| Issue | Notes |
|-------|-------|
| 2.3 Registry not pre-populated | Nice to have |
| 2.4 Unused config classes | Clean up |
| 2.6 Credentials repr security | Security hardening |
| 2.9-2.14 Test improvements | Quality polish |
| 3.x Low priority items | Docs, dead code |

## 4. M3.5 Design (Integration Fixes)

### Part A: Full Design

#### A.1 Dependency Injection Fix

**Current State**: Routes create module-level singletons:
```python
# routes/runs.py (CURRENT - WRONG)
_run_manager: RunManager | None = None
def get_run_manager() -> RunManager:
    global _run_manager
    if _run_manager is None:
        _run_manager = RunManager()
    return _run_manager
```

**Target State**: Routes get services from app.state:
```python
# dependencies.py (TARGET)
def get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager

def get_veda_service(request: Request) -> VedaService:
    return request.app.state.veda_service

def get_event_log(request: Request) -> EventLog:
    return request.app.state.event_log
```

**Files to Change**:
- `src/glados/dependencies.py` - Add all dependency functions
- `src/glados/routes/runs.py` - Use Depends()
- `src/glados/routes/orders.py` - Use Depends()
- `src/glados/routes/candles.py` - Use Depends()
- `src/glados/routes/sse.py` - Use Depends()
- `src/glados/app.py` - Ensure services in app.state

#### A.2 Event Flow Fix

**Current State**: No events emitted when runs/orders change.

**Target State**: Services emit events to EventLog:
```python
# run_manager.py
async def create(self, request: RunCreate) -> Run:
    run = Run(...)
    self._runs[run.id] = run
    await self._event_log.append("runs.Created", {"run_id": run.id, ...})
    return run

async def stop(self, run_id: str) -> Run:
    run = self._runs[run_id]
    run.status = RunStatus.STOPPED
    await self._event_log.append("runs.Stopped", {"run_id": run_id})
    return run
```

**Events to Add**:
- `runs.Created`, `runs.Started`, `runs.Stopped`
- `orders.Created` (add to types.py)

#### A.3 VedaService Wiring

**Current State**: `routes/orders.py` uses MockOrderService.

**Target State**: Use VedaService for order operations:
```python
# routes/orders.py
@router.get("/orders")
async def list_orders(
    veda: Annotated[VedaService, Depends(get_veda_service)],
):
    return await veda.list_orders()
```

### Part B: MVP Execution Plan

#### MVP-1: Trivial Fixes (30 min)
- Add `orders.Created` to `src/events/types.py`
- Fix OrderRepository to use context managers
- Remove/use unused exceptions

#### MVP-2: Dependencies Module (1 hour)
- Rewrite `src/glados/dependencies.py` with all getters
- Update app.py lifespan to populate app.state

#### MVP-3: Routes Migration (2 hours)
- Update each route file to use Depends()
- Remove module-level singletons
- Add EventLog injection

#### MVP-4: Event Emission (2 hours)
- Add EventLog to RunManager constructor
- Emit events on state changes
- Verify SSE receives events

#### MVP-5: VedaService Integration (1 hour)
- Wire VedaService to order routes
- Test order flow end-to-end

**Total Estimate**: ~6-8 hours

## 5. Phase Timeline (Revised)

| Phase | Weeks | Focus | Status |
|-------|-------|-------|--------|
| 1 | 1–2 | Foundation (events, clock, config, DB) | ✅ |
| 2 | 2–3 | GLaDOS Core (REST, SSE, DI) | ✅ |
| 3 | 3–4 | Veda Trading | ✅ |
| **3.5** | **4** | **Integration Fixes (M3.5)** | **⏳ NEXT** |
| 4 | 4–5 | Greta (backtest) + Clock integration | ⏳ |
| 5 | 5–6 | Marvin (strategies) + Live trading | ⏳ |
| 6 | 6–7 | Haro (frontend) | ⏳ |
| 7 | 7–8 | Integration & E2E | ⏳ |

## 6. Test Coverage Targets

| Module | Target | Critical Paths |
|--------|--------|----------------|
| `events/` | 90% | Outbox, offset tracking |
| `glados/clock/` | 95% | Bar alignment, drift |
| `glados/routes/` | 85% | All endpoints |
| `veda/` | 85% | Order idempotency |
| `greta/` | 90% | Fill simulation |
| `marvin/` | 85% | Strategy lifecycle |

## 7. Architecture Invariants

These MUST remain true across all milestones:

1. **Single EventLog instance** - All components share one EventLog
2. **VedaService as entry point** - External callers use VedaService, not OrderManager
3. **Database session per request** - No long-lived sessions
4. **SSE receives all events** - EventLog → SSEBroadcaster pipeline always connected
5. **Graceful degradation** - App functions in in-memory mode when DB_URL absent
6. **No module singletons** - Services come from app.state via DI (NEW)

## 8. M4 Entry Gate Checklist

Before starting M4, **all M3.5 items must pass**:

- [ ] Routes use `Depends()` from dependencies.py
- [ ] `POST /runs` emits `runs.Created` event
- [ ] EventLog entry → SSE broadcast visible in `/events/stream`
- [ ] VedaService is called for order operations
- [ ] OrderRepository uses proper session handling
- [ ] All 493+ tests still passing

---

## Appendix: Detailed Milestone Specs

Completed milestone specifications are archived for reference:

- [M1: Foundation](../archive/milestone-details/m1-foundation.md) - Clock, DB, Alembic
- [M2: GLaDOS API](../archive/milestone-details/m2-glados-api.md) - REST, SSE, Services
- [M3: Veda Trading](../archive/milestone-details/m3-veda.md) - Adapters, Orders, Idempotency

---

*Last updated: 2026-02-02 (Post-Audit)*

# Implementation Roadmap

> Part of [Architecture Documentation](../ARCHITECTURE.md)

---

## Document Rules

**This file contains ONLY**:
- Current state summary (Section 1)
- Milestone definitions and status (Section 2)
- Phase timeline (Section 3)
- Architecture invariants (Section 4)
- Entry gate checklists (Section 5)

**Detailed designs go in**: `docs/archive/milestone-details/mX-name.md`

**Issue tracking goes in**: `docs/AUDIT_FINDINGS.md`

**Maximum length**: ~150 lines. If longer, extract details to archive.

---

## 1. Current State

| Component | Status | Tests |
|-----------|--------|-------|
| Test Infrastructure | ✅ Complete | 631 |
| Events Module | ✅ Core complete | 33 |
| Clock Module | ✅ Complete | 93 |
| Config Module | ✅ Complete | 24 |
| GLaDOS API | ✅ DI complete | 201 |
| Veda Trading | ✅ Complete | 197 |
| Greta (backtest) | ✅ Complete | 49 |
| Marvin (strategy) | ✅ Skeleton | 32 |
| WallE (bars) | ✅ Complete | 16 |
| Haro (frontend) | ❌ Not started | 0 |

## 2. Milestones

| Milestone | Definition of Done | Status |
|-----------|-------------------|--------|
| M0–M3 | Foundation, API, Trading | ✅ DONE |
| M3.5 | [Integration fixes](../archive/milestone-details/m3.5-integration.md) | ✅ DONE |
| M4 | [Greta backtest engine](../archive/milestone-details/m4-greta.md) (multi-run ready) | ✅ DONE |
| **M5** | Marvin full + SMA backtested (parallel runs) | ⏳ NEXT |
| M6 | E2E tests pass | ⏳ |
| M7 | Coverage ≥80%, docs complete | ⏳ |

## 3. Phase Timeline

| Phase | Focus | Status |
|-------|-------|--------|
| 1–3 | Foundation → Veda | ✅ |
| 3.5 | Integration fixes | ✅ |
| 4 | Greta + Clock integration | ✅ DONE |
| 5 | Marvin full + Live trading | ⏳ NEXT |
| 6 | Haro frontend | ⏳ |
| 7 | E2E + Polish | ⏳ |

## 4. Architecture Invariants

1. **Single EventLog** - All components share one instance (events tagged with run_id)
2. **VedaService as entry** - Not OrderManager directly
3. **Session per request** - No long-lived DB sessions
4. **SSE receives all events** - EventLog → SSE always connected
5. **Graceful degradation** - Works without DB_URL
6. **No module singletons** - Services via DI only
7. **Multi-Run Support** - Per-run instances (Greta, Marvin, Clock) vs singletons (EventLog, BarRepository)
8. **Run Isolation** - Events carry run_id; consumers filter by run_id

## 5. Entry Gate Checklists

### Before M4 ✅ COMPLETED

- [x] Routes use `Depends()` from dependencies.py
- [x] `POST /runs` emits `runs.Created` event
- [x] SSE receives events from EventLog
- [ ] VedaService wired to order routes (deferred to M5)
- [x] All tests passing (506)

### Before M5 ✅ COMPLETED (was "Before M5")

- [x] WallE BarRepository created (bars table + repository)
- [x] GretaService created and tested (uses BarRepository)
- [x] Fill simulator handles market/limit orders
- [x] Marvin skeleton: StrategyRunner + TestStrategy
- [x] DomainRouter routes strategy.* → backtest.*
- [x] BacktestClock integrated with RunManager
- [x] Backtest run completes via API
- [x] All events emitted correctly (run.*, strategy.*)
- [x] ~79 new tests passing (631 total)

### Before M6 (M5 Exit Gate)

- [ ] Marvin executes SMA strategy with indicators
- [ ] Strategy loading from file/config
- [ ] Live order flow works (paper mode)
- [ ] AlpacaAdapter initialized
- [ ] VedaService wired to order routes
- [ ] data.WindowReady flow implemented (fetch historical)

### Design Review Notes (M5)

> **EventLog**: Current impl has `InMemoryEventLog` for unit tests and `PostgresEventLog` for integration. 
> This is intentional - unit tests don't need DB. However, consider if this adds complexity.

> **Greta/Marvin Coupling**: Integration tests have `MockStrategyLoader` and `SimpleTestStrategy` in 
> `test_backtest_flow.py`. These may belong in `tests/factories/` or `tests/fixtures/` for reuse.
> The current location works but review during M5 to ensure proper separation.

---

## Appendix: Milestone Details

| Milestone | Design Doc |
|-----------|-----------|
| M1 | [Foundation](../archive/milestone-details/m1-foundation.md) |
| M2 | [GLaDOS API](../archive/milestone-details/m2-glados-api.md) |
| M3 | [Veda Trading](../archive/milestone-details/m3-veda.md) |
| M3.5 | [Integration](../archive/milestone-details/m3.5-integration.md) |
| M4 | [Greta Backtest](../archive/milestone-details/m4-greta.md) |

---

*Last updated: 2026-02-03 (M4 design complete)*

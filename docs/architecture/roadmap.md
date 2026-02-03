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

**Detailed milestone plan**: [MILESTONE_PLAN.md](../MILESTONE_PLAN.md)

**Detailed designs go in**: `docs/archive/milestone-details/mX-name.md`

**Issue tracking goes in**: `docs/AUDIT_FINDINGS.md`

---

## 1. Current State

| Component | Status | Tests |
|-----------|--------|-------|
| Test Infrastructure | ✅ Complete | 692 |
| Events Module | ✅ Subscription added | 57 |
| Clock Module | ✅ Complete | 93 |
| Config Module | ✅ Complete | 24 |
| GLaDOS API | ✅ DI complete | 201 |
| Veda Trading | ✅ Complete | 197 |
| Greta (backtest) | ✅ Events wired | 56 |
| Marvin (strategy) | ✅ Plugin complete | 74 |
| WallE (bars) | ✅ Complete | 16 |
| Haro (frontend) | ❌ Not started | 0 |

## 2. Milestones (Revised 2026-02-03)

| Milestone | Definition of Done | Status |
|-----------|-------------------|--------|
| M0–M3 | Foundation, API, Trading | ✅ DONE |
| M3.5 | [Integration fixes](../archive/milestone-details/m3.5-integration.md) | ✅ DONE |
| M4 | [Greta backtest](../archive/milestone-details/m4-greta.md) | ✅ DONE |
| **M5** | Marvin Core (Strategy + Plugin) | 🟨 IN PROGRESS (M5-1 ✅, M5-2 ✅, M5-3 ✅, M5-4 ✅) |
| **M6** | Live Trading (Paper/Live Flow) | ⏳ |
| **M7** | Haro Frontend (React UI) | ⏳ |
| **M8** | Polish & E2E (Quality + Tests) | ⏳ |

## 3. Phase Timeline

| Phase | Focus | Est. Tests | Status |
|-------|-------|------------|--------|
| 1–4 | Foundation → Greta | 631 | ✅ DONE |
| **5** | Marvin Core + Plugin Strategy | ~74 | ✅ 74/74 (705 total) |
| **6** | Live Trading + Plugin Adapter | ~60 | ⏳ |
| **7** | Haro Frontend + SSE | ~50 | ⏳ |
| **8** | E2E + Polish | ~40 | ⏳ |

## 4. Architecture Invariants

1. **Single EventLog** - All components share one instance (events tagged with run_id)
2. **VedaService as entry** - Not OrderManager directly
3. **Session per request** - No long-lived DB sessions
4. **SSE receives all events** - EventLog → SSE always connected
5. **Graceful degradation** - Works without DB_URL
6. **No module singletons** - Services via DI only
7. **Multi-Run Support** - Per-run instances (Greta, Marvin, Clock) vs singletons (EventLog, BarRepository)
8. **Run Isolation** - Events carry run_id; consumers filter by run_id
9. **Plugin Architecture** - Strategies/Adapters are sideloadable, no hardcoded imports

## 5. Entry Gate Checklists

### Before M5 ✅ COMPLETED

- [x] WallE BarRepository created (bars table + repository)
- [x] GretaService created and tested (uses BarRepository)
- [x] Fill simulator handles market/limit orders
- [x] Marvin skeleton: StrategyRunner + TestStrategy
- [x] DomainRouter routes strategy.* → backtest.*
- [x] BacktestClock integrated with RunManager
- [x] Backtest run completes via API
- [x] All events emitted correctly (run.*, strategy.*)
- [x] 631 tests passing

### Before M6 (M5 Exit Gate)

- [x] EventLog subscription mechanism added ✅ 2026-02-03
- [x] data.WindowReady flow implemented ✅ 2026-02-03
- [x] SMA strategy with indicators implemented ✅ 2026-02-03
- [x] **PluginStrategyLoader with auto-discovery** ✅ 2026-02-03
- [ ] Code quality fixes (ClockTick, SimulatedFill.side, test fixtures)
- [ ] ~80 new tests (target: 711+)

### Before M7 (M6 Exit Gate)

- [ ] **PluginAdapterLoader with auto-discovery**
- [ ] AlpacaAdapter initialized with real clients
- [ ] VedaService wired to order routes
- [ ] Live order flow works (paper mode)
- [ ] RealtimeClock integrated for live runs
- [ ] ~60 new tests (target: 771+)

### Before M8 (M7 Exit Gate)

- [ ] React app running in Docker
- [ ] Dashboard, Runs, Orders pages functional
- [ ] SSE real-time updates working
- [ ] ~50 new tests (target: 821+)

### M8 Exit Gate (MVP Complete)

- [ ] E2E tests pass (Playwright)
- [ ] Coverage ≥80%
- [ ] All TODO/FIXME cleaned
- [ ] Documentation complete
- [ ] ~40 new tests (target: 861+)

---

## 6. MVP Tables

### M5: Marvin Core ✅ COMPLETE

| MVP | Focus | Tests |
|-----|-------|-------|
| M5-1 | EventLog Subscription | 12 ✅ |
| M5-2 | data.WindowReady Flow | 15 ✅ |
| M5-3 | SMA Strategy | 17 ✅ |
| M5-4 | Plugin Strategy Loader | 17 ✅ |
| M5-5 | Code Quality (Marvin) | 13 ✅ |

### M6: Live Trading

| MVP | Focus | Est. Tests |
|-----|-------|------------|
| M6-1 | Plugin Adapter Loader | ~10 |
| M6-2 | AlpacaAdapter Init | ~12 |
| M6-3 | VedaService Routing | ~10 |
| M6-4 | Live Order Flow | ~15 |
| M6-5 | Run Mode Integration | ~8 |

### M7: Haro Frontend

| MVP | Focus | Est. Tests |
|-----|-------|------------|
| M7-1 | React App Scaffold | ~10 |
| M7-2 | Dashboard Page | ~10 |
| M7-3 | Runs Page | ~12 |
| M7-4 | Orders Page | ~10 |
| M7-5 | SSE Integration | ~8 |

### M8: Polish & E2E

| MVP | Focus | Est. Tests |
|-----|-------|------------|
| M8-1 | E2E Test Setup | ~5 |
| M8-2 | E2E Backtest Flow | ~8 |
| M8-3 | E2E Live Flow | ~8 |
| M8-4 | Code Quality | ~10 |
| M8-5 | Documentation | - |

---

## Appendix: Design Documents

| Milestone | Design Doc |
|-----------|-----------|
| M1 | [Foundation](../archive/milestone-details/m1-foundation.md) |
| M2 | [GLaDOS API](../archive/milestone-details/m2-glados-api.md) |
| M3 | [Veda Trading](../archive/milestone-details/m3-veda.md) |
| M3.5 | [Integration](../archive/milestone-details/m3.5-integration.md) |
| M4 | [Greta Backtest](../archive/milestone-details/m4-greta.md) |
| M5 | [Marvin Full](../archive/milestone-details/m5-marvin.md) |

---

*Last updated: 2026-02-03 (Milestone plan reorganized)*

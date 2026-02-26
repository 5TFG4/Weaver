# Implementation Roadmap

> Part of [Architecture Documentation](../ARCHITECTURE.md)
>
> **Document Charter**  
> **Primary role**: high-level phase roadmap and architecture entry-gate framing.  
> **Authoritative for**: roadmap phases and gate checklist framing only.  
> **Not authoritative for**: current detailed task execution (use `../MILESTONE_PLAN.md`) or latest test counts/coverage (use `../TEST_COVERAGE.md`).

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

**Active issue tracking goes in**: `docs/DESIGN_AUDIT.md`  
**Historical issue trail remains in**: `docs/AUDIT_FINDINGS.md`

---

## 1. Current State

> Snapshot note: values in this section are historical roadmap checkpoints. For latest measured totals and coverage, use `docs/TEST_COVERAGE.md`.

| Component           | Status                | Tests |
| ------------------- | --------------------- | ----- |
| Test Infrastructure | ✅ Complete           | 904   |
| Events Module       | ✅ Subscription added | 57    |
| Clock Module        | ✅ Complete           | 93    |
| Config Module       | ✅ Complete           | 24    |
| GLaDOS API          | ✅ Order routing      | 214   |
| Veda Trading        | ✅ Complete           | 197   |
| Greta (backtest)    | ✅ Events wired       | 56    |
| Marvin (strategy)   | ✅ Plugin complete    | 74    |
| WallE (bars)        | ✅ Complete           | 16    |
| Haro (frontend)     | ✅ Complete           | 88    |

**Total (historical snapshot)**: 904 backend + 88 frontend = 992 tests

**Active Milestone**: M9 (E2E Tests & Release Preparation)

**Last State Update**: 2026-02-25

## 2. Milestones (Revised 2026-02-19)

| Milestone | Definition of Done                                                                | Status              |
| --------- | --------------------------------------------------------------------------------- | ------------------- |
| M0–M3     | Foundation, API, Trading                                                          | ✅ DONE             |
| M3.5      | [Integration fixes](../archive/milestone-details/m3.5-integration.md)             | ✅ DONE             |
| M4        | [Greta backtest](../archive/milestone-details/m4-greta.md)                        | ✅ DONE             |
| **M5**    | [Marvin Core](../archive/milestone-details/m5-marvin.md) (Strategy + Plugin)      | ✅ DONE (74 tests)  |
| **M6**    | [Live Trading](../archive/milestone-details/m6-live-trading.md) (Paper/Live Flow) | ✅ DONE (101 tests) |
| **M7**    | [Haro Frontend](../archive/milestone-details/m7-haro-frontend.md) (React UI)      | ✅ DONE (86 tests)  |
| **M8**    | Critical Fixes & Improvements (P0 fixes + Runtime wiring + Quality)               | ✅ COMPLETE         |
| **M9**    | E2E Tests & Release Preparation (Playwright + Final polish)                       | ⏳ PLANNED          |

## 3. Phase Timeline

| Phase | Focus                         | Est. Tests | Status               |
| ----- | ----------------------------- | ---------- | -------------------- |
| 1–4   | Foundation → Greta            | 631        | ✅ DONE              |
| **5** | Marvin Core + Plugin Strategy | ~74        | ✅ 74/74 (705 total) |
| **6** | Live Trading + Plugin Adapter | ~65        | ✅ 101 (808 total)   |
| **7** | Haro Frontend + SSE           | ~86        | ✅ 86 (894 total)    |
| **8** | Critical Fixes + Improvements | ~96        | ✅ COMPLETE          |
| **9** | E2E Tests + Release Prep      | ~20–30     | ⏳ PLANNED           |

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
- [x] DomainRouter routes strategy._ → backtest._
- [x] BacktestClock integrated with RunManager
- [x] Backtest run completes via API
- [x] All events emitted correctly (run._, strategy._)
- [x] 631 tests passing

### Before M6 (M5 Exit Gate) ✅ COMPLETE

- [x] EventLog subscription mechanism added ✅ 2026-02-03
- [x] data.WindowReady flow implemented ✅ 2026-02-03
- [x] SMA strategy with indicators implemented ✅ 2026-02-03
- [x] PluginStrategyLoader with auto-discovery ✅ 2026-02-03
- [x] Code quality fixes (ClockTick, test fixtures) ✅ 2026-02-04
- [x] 74 new tests (705 total) ✅ 2026-02-04

### Before M7 (M6 Exit Gate)

- [x] **PluginAdapterLoader with auto-discovery** (M6-1) ✅ 40 tests
- [x] **AlpacaAdapter connect() implemented** (M6-2) ✅ 23 tests
- [x] **VedaService wired to order routes** (M6-3) ✅ 13 tests
- [x] **Live order flow with events & persistence** (M6-4) ✅ 15 tests
- [x] **RealtimeClock for live runs** (M6-5) ✅ 10 tests
- [x] ~100 new tests (target: 805+) → actual: 806 ✅

### Before M8 (M7 Exit Gate) ✅ COMPLETE

- [x] React app running in Docker ✅
- [x] Dashboard, Runs, Orders pages functional ✅
- [x] SSE real-time updates working ✅ 2026-02-06
- [x] 86 new tests (target: 821+) → actual: 894 ✅

### M8 Exit Gate (Fixes & Improvements)

- [x] All P0 critical issues resolved (C-01–C-04, N-01/N-02/N-07)
- [x] Design decisions D-1–D-5 implemented
- [x] DomainRouter wired into runtime lifecycle
- [x] RunManager dependencies fully injected
- [x] Code coverage ≥80% (see `docs/TEST_COVERAGE.md` for latest measured value)
- [x] All TODO/FIXME cleaned
- [x] Documentation complete
- [x] ~96 new tests (target: 934+) → achieved; latest totals tracked in `docs/TEST_COVERAGE.md`

### M9 Exit Gate (E2E & Release Ready)

- [ ] E2E tests pass (Playwright)
- [ ] Full user workflow validated end-to-end
- [ ] Deployment guide complete
- [ ] ~20–30 new tests (target: 954+)

---

## 6. MVP Tables

### M5: Marvin Core ✅ COMPLETE

| MVP  | Focus                  | Tests |
| ---- | ---------------------- | ----- |
| M5-1 | EventLog Subscription  | 12 ✅ |
| M5-2 | data.WindowReady Flow  | 15 ✅ |
| M5-3 | SMA Strategy           | 17 ✅ |
| M5-4 | Plugin Strategy Loader | 17 ✅ |
| M5-5 | Code Quality (Marvin)  | 13 ✅ |

### M6: Live Trading ✅ COMPLETE

| MVP  | Focus                    | Est. Tests | Status |
| ---- | ------------------------ | ---------- | ------ |
| M6-1 | PluginAdapterLoader      | ~15        | ✅ 40  |
| M6-2 | AlpacaAdapter Connection | ~14        | ✅ 23  |
| M6-3 | VedaService Routing      | ~12        | ✅ 13  |
| M6-4 | Live Order Flow          | ~15        | ✅ 15  |
| M6-5 | Run Mode Integration     | ~9         | ✅ 10  |

### M7: Haro Frontend

| MVP  | Focus                 | Est. Tests | Status |
| ---- | --------------------- | ---------- | ------ |
| M7-0 | Dev Environment Setup | 0          | ✅     |
| M7-1 | React App Scaffold    | ~10        | ✅ 8   |
| M7-2 | API Client Layer      | ~10        | ✅ 9   |
| M7-3 | Dashboard Page        | ~8         | ✅ 15  |
| M7-4 | Runs Page             | ~12        | ✅ 14  |
| M7-5 | Orders Page           | ~8         | ✅ 17  |
| M7-6 | SSE Integration       | ~8         | 23 ✅  |

### M8: Polish & E2E

| MVP  | Focus             | Est. Tests |
| ---- | ----------------- | ---------- |
| M8-1 | E2E Test Setup    | ~5         |
| M8-2 | E2E Backtest Flow | ~8         |
| M8-3 | E2E Live Flow     | ~8         |
| M8-4 | Code Quality      | ~10        |
| M8-5 | Documentation     | -          |

---

## Appendix: Design Documents

| Milestone | Design Doc                                                        |
| --------- | ----------------------------------------------------------------- |
| M1        | [Foundation](../archive/milestone-details/m1-foundation.md)       |
| M2        | [GLaDOS API](../archive/milestone-details/m2-glados-api.md)       |
| M3        | [Veda Trading](../archive/milestone-details/m3-veda.md)           |
| M3.5      | [Integration](../archive/milestone-details/m3.5-integration.md)   |
| M4        | [Greta Backtest](../archive/milestone-details/m4-greta.md)        |
| M5        | [Marvin Full](../archive/milestone-details/m5-marvin.md)          |
| M6        | [Live Trading](../archive/milestone-details/m6-live-trading.md)   |
| M7        | [Haro Frontend](../archive/milestone-details/m7-haro-frontend.md) |

---

_Last updated: 2026-02-26 (roadmap snapshot sync; latest live metrics delegated to TEST_COVERAGE.md)_

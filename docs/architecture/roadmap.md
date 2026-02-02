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
| Test Infrastructure | ✅ Complete | 493 |
| Events Module | ⚠️ Core done, gaps | 33 |
| Clock Module | ✅ Complete | 93 |
| Config Module | ✅ Complete | 24 |
| GLaDOS API | ⚠️ DI incomplete | 85 |
| Veda Trading | ⚠️ Not wired | 196 |
| Greta (backtest) | ❌ Empty | 0 |
| Marvin (strategy) | ❌ Empty | 0 |
| Haro (frontend) | ❌ Not started | 0 |

## 2. Milestones

| Milestone | Definition of Done | Status |
|-----------|-------------------|--------|
| M0–M3 | Foundation, API, Trading | ✅ DONE |
| **M3.5** | [Integration fixes](../archive/milestone-details/m3.5-integration.md) | ⏳ NEXT |
| M4 | Greta simulation works | ⏳ |
| M5 | Marvin + SMA backtested | ⏳ |
| M6 | E2E tests pass | ⏳ |
| M7 | Coverage ≥80%, docs complete | ⏳ |

## 3. Phase Timeline

| Phase | Focus | Status |
|-------|-------|--------|
| 1–3 | Foundation → Veda | ✅ |
| 3.5 | Integration fixes | ⏳ NEXT |
| 4 | Greta + Clock integration | ⏳ |
| 5 | Marvin + Live trading | ⏳ |
| 6 | Haro frontend | ⏳ |
| 7 | E2E + Polish | ⏳ |

## 4. Architecture Invariants

1. **Single EventLog** - All components share one instance
2. **VedaService as entry** - Not OrderManager directly
3. **Session per request** - No long-lived DB sessions
4. **SSE receives all events** - EventLog → SSE always connected
5. **Graceful degradation** - Works without DB_URL
6. **No module singletons** - Services via DI only

## 5. Entry Gate Checklists

### Before M4

- [ ] Routes use `Depends()` from dependencies.py
- [ ] `POST /runs` emits `runs.Created` event
- [ ] SSE receives events from EventLog
- [ ] VedaService wired to order routes
- [ ] All tests passing

### Before M5

- [ ] Greta can simulate fills
- [ ] Clock integrated with runs
- [ ] Backtest stats calculated

### Before M6

- [ ] Marvin executes SMA strategy
- [ ] Live order flow works (paper mode)
- [ ] AlpacaAdapter initialized

---

## Appendix: Milestone Details

| Milestone | Design Doc |
|-----------|-----------|
| M1 | [Foundation](../archive/milestone-details/m1-foundation.md) |
| M2 | [GLaDOS API](../archive/milestone-details/m2-glados-api.md) |
| M3 | [Veda Trading](../archive/milestone-details/m3-veda.md) |
| M3.5 | [Integration](../archive/milestone-details/m3.5-integration.md) |

---

*Last updated: 2026-02-02*

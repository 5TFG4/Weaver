# Implementation Roadmap

> Part of [Architecture Documentation](../ARCHITECTURE.md)
> 
> For development methodology, see [DEVELOPMENT.md](../DEVELOPMENT.md)

---

## 1. Current State

| Component | Status | Tests |
|-----------|--------|-------|
| **Python Environment** | ✅ 3.13 | - |
| **Test Infrastructure** | ✅ Complete | 493 passing |
| **Events Module** | ✅ Core types/protocol/registry | 33 tests |
| **Clock Module** | ✅ Complete | 93 tests (93% cov) |
| **Config Module** | ✅ Dual credentials | 24 tests |
| **GLaDOS API (M2)** | ✅ Complete | 85 tests |
| **Veda Trading (M3)** | ✅ Complete | 196 tests |
| **WallE/DB** | ⚠️ Basic models | ~30% |
| **Greta (backtest)** | ❌ Empty shell | 0% |
| **Marvin (strategy)** | ❌ Empty shell | 0% |
| **Haro (frontend)** | ❌ Not started | 0% |

## 2. Milestones

| Milestone | Definition of Done | Status |
|-----------|-------------------|--------|
| **M0** | Test infra works; CI green | ✅ DONE |
| **M0.5** | Restructure; events/clock created | ✅ DONE |
| **M1** | Clock impl; Events DB; Alembic | ✅ DONE |
| **M2** | Route tests pass; SSE tests pass | ✅ DONE |
| **M3** | Veda tests pass; Order idempotency | ✅ DONE |
| **M4** | Greta simulation; Stats verified | ⏳ NEXT |
| **M5** | Marvin tests; SMA backtested | ⏳ PENDING |
| **M6** | Playwright E2E tests pass | ⏳ PENDING |
| **M7** | All tests; Coverage ≥80%; Docs | ⏳ PENDING |

## 3. Phase Timeline

| Phase | Weeks | Focus | Status |
|-------|-------|-------|--------|
| 1 | 1–2 | Foundation (events, clock, config, DB) | ✅ |
| 2 | 2–3 | GLaDOS Core (REST, SSE, DI) | ✅ |
| 3 | 3–4 | Veda (adapters, orders) + Greta (backtest) | ✅ Veda only |
| 4 | 4–5 | Marvin (strategies) | ⏳ |
| 5 | 5–7 | Haro (frontend) | ⏳ |
| 6 | 7–8 | Integration & E2E | ⏳ |

## 4. Test Coverage Targets

| Module | Target | Critical Paths |
|--------|--------|----------------|
| `events/` | 90% | Outbox, offset tracking |
| `glados/clock/` | 95% | Bar alignment, drift |
| `glados/routes/` | 85% | All endpoints |
| `veda/` | 85% | Order idempotency |
| `greta/` | 90% | Fill simulation |
| `marvin/` | 85% | Strategy lifecycle |

## 5. Architecture Invariants

These MUST remain true across all milestones:

1. **Single EventLog instance** - All components share one EventLog
2. **VedaService as entry point** - External callers use VedaService, not OrderManager
3. **Database session per request** - No long-lived sessions
4. **SSE receives all events** - EventLog → SSEBroadcaster pipeline always connected
5. **Graceful degradation** - App functions in in-memory mode when DB_URL absent

## 6. Deferred Work (M4+)

| Feature | Current Status | Target |
|---------|---------------|--------|
| Streaming quotes | ❌ Deferred | M4+ |
| Real-time bar updates | ❌ Deferred | M4+ |
| Order sync on startup | ❌ Deferred | M4+ |
| RunManager persistence | ⚠️ In-memory only | M4 |
| GLaDOS OrderService real data | ⚠️ Mock data | M4 |
| CandleStore persistence | ❌ Ephemeral | M4 |
| Multiple exchanges | ❌ Alpaca only | M5+ |

## 7. M4 Entry Gate Checklist

Before starting M4, verify:

- [ ] `POST /runs` → creates Run record in database
- [ ] Order placed via REST → persisted in `veda_orders`
- [ ] EventLog entry → SSE broadcast visible
- [ ] Clock tick → triggers strategy (after Marvin)
- [ ] Graceful shutdown cleans up resources

---

## Appendix: Detailed Milestone Specs

Completed milestone specifications are archived for reference:

- [M1: Foundation](../archive/milestone-details/m1-foundation.md) - Clock, DB, Alembic
- [M2: GLaDOS API](../archive/milestone-details/m2-glados-api.md) - REST, SSE, Services
- [M3: Veda Trading](../archive/milestone-details/m3-veda.md) - Adapters, Orders, Idempotency

---

*Last updated: Post-M3 Audit*

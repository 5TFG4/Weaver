# Weaver — Architecture

> An automated trading system (live + backtesting) with a React UI.

**Last Updated**: 2026-02-04 · **Tests**: 768 passing · **M6-2**: ✅ Complete

---

## ⚠️ Key Planning Documents

> **Start a new session?** These contain critical project planning info:

| What You Need | Where to Find It |
|---------------|------------------|
| **Issue backlog & milestone schedule** | [AUDIT_FINDINGS.md §5](AUDIT_FINDINGS.md#5-milestone-based-fix-schedule) |
| **Implementation progress** | [AUDIT_FINDINGS.md §6](AUDIT_FINDINGS.md#6-progress-tracking) |
| **Entry gate checklists** | [roadmap.md §5](architecture/roadmap.md#5-entry-gate-checklists) |
| **Next milestone design** | [M6 Live Trading](archive/milestone-details/m6-live-trading.md) |
| **Documentation rules** | [DEVELOPMENT.md §8](DEVELOPMENT.md#8-documentation-structure) |

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Development](DEVELOPMENT.md) | Methodology, TDD, coding standards, **doc structure rules (§8)** |
| [Audit Findings](AUDIT_FINDINGS.md) | Issues to fix, **milestone schedule (§5)**, **progress (§6)** |
| [Roadmap](architecture/roadmap.md) | Milestones, phases, **entry checklists (§5)** |
| [Events](architecture/events.md) | Event model, envelope, namespaces, delivery |
| [API](architecture/api.md) | REST, SSE, auth, thin events pattern |
| [Clock](architecture/clock.md) | RealtimeClock, BacktestClock, bar alignment |
| [Config](architecture/config.md) | Dual credentials, security, testing |
| [Deployment](architecture/deployment.md) | Docker, env vars, operations |

### Archived Milestone Details

| Milestone | Design Doc | Status |
|-----------|-----------|--------|
| M1 Foundation | [m1-foundation.md](archive/milestone-details/m1-foundation.md) | ✅ Done |
| M2 GLaDOS API | [m2-glados-api.md](archive/milestone-details/m2-glados-api.md) | ✅ Done |
| M3 Veda Trading | [m3-veda.md](archive/milestone-details/m3-veda.md) | ✅ Done |
| M3.5 Integration | [m3.5-integration.md](archive/milestone-details/m3.5-integration.md) | ✅ Done |
| M4 Greta | [m4-greta.md](archive/milestone-details/m4-greta.md) | ✅ Done |
| **M5 Marvin** | [m5-marvin.md](archive/milestone-details/m5-marvin.md) | ✅ Done (74 tests) |
| **M6 Live Trading** | [m6-live-trading.md](archive/milestone-details/m6-live-trading.md) | ⏳ Next |

---

## 1. System Goals
* A 24/7 automated trading system on a local server
* **Live trading and backtesting** with the same strategy code
* **Multi‑strategy concurrency** (parallel runs isolated by `run_id`)
* **Web UI** for monitoring and control
* **Containerized deployment** (Docker Compose)
* Integrate Alpaca first; keep the door open for more exchanges

### Non‑Goals (MVP)

* Microservice split, distributed queues
* Exactly‑once stream processing
* External multi‑tenant or complex auth

---

## 2. Architecture Overview

### Shape & Boundaries

* **Modulith**: A single backend process (Python) hosting domain packages
* **Only GLaDOS** exposes northbound APIs
* **Frontend–Backend split**: Haro (React) runs as independent container
* **Multi-run support**: Multiple strategies can run concurrently (backtests + live)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Haro (React UI)                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST + SSE
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GLaDOS (Control Plane)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐│
│  │ Routes  │  │  Clock  │  │ Router  │  │    Event Pump       ││
│  │ api/sse │  │ rt/bt   │  │ domain  │  │ outbox → consumers  ││
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────────┘│
└───────────────────────────────┬─────────────────────────────────┘
                                │ Events (in-process)
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│     Veda      │       │    Greta      │       │    Marvin     │
│  Live Trading │       │   Backtest    │       │   Strategy    │
│  (singleton)  │       │  (per-run)    │       │  (per-run)    │
└───────────────┘       └───────────────┘       └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                        ┌───────────────┐
                        │    WallE      │
                        │  Persistence  │
                        │  (singleton)  │
                        └───────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │   PostgreSQL  │
                        └───────────────┘
```

### Internal Collaboration

* **Synchronous calls**: Critical paths are in‑process function calls
* **Event‑driven**: For broadcast, decoupling, notifications, and replay
* **Strategy‑led**: Strategies express intent via events; GLaDOS routes to live/backtest

---

## 3. Modules — Responsibilities

| Module | Responsibilities | Does NOT |
|--------|-----------------|----------|
| **GLaDOS** | Sole API; run lifecycle; domain routing; clock; dependency wiring | Write business tables directly |
| **Veda** | Handle `live.*` requests; call exchanges; submit orders | Handle backtest logic |
| **Greta** | Handle `backtest.*` requests; simulate fills/slippage/fees | Make real API calls |
| **Marvin** | Maintain run context; tick by clock; emit strategy intents | Know if live or backtest |
| **WallE** | Centralized writes; repository reads | Expose APIs |
| **Haro** | Show UI; consume SSE; fetch details via REST | Process events directly |
| **Events** | Envelope/registry; Outbox + LISTEN/NOTIFY; offsets | Store business data |

---

## 4. Global Invariants

| Rule | Implementation |
|------|----------------|
| **Time** | DB stores UTC; frontend renders user timezone |
| **Error model** | `{code, message, details, correlation_id}` |
| **Identity chain** | `id / corr_id / causation_id / trace_id` |
| **Events** | Immutable, replayable, at-least-once delivery |
| **Idempotency** | `client_order_id` on orders; dedupe by `id/corr_id` |

---

## 5. Instance Model (Per-Run vs Singleton)

When multiple runs execute concurrently (multiple backtests, or backtest + live), services follow one of two patterns:

| Pattern | Services | Rationale |
|---------|----------|-----------|
| **Per-Run** | GretaService, StrategyRunner, Clock | Each run has isolated positions, orders, equity curve, strategy state |
| **Singleton** | EventLog, BarRepository, DomainRouter, SSEBroadcaster | Shared infrastructure; events tagged with `run_id` for isolation |

```
RunManager
├── run_contexts: Dict[str, RunContext]
│
├── RunContext (run-001, backtest)
│   ├── GretaService instance
│   ├── StrategyRunner instance
│   └── BacktestClock instance
│
├── RunContext (run-002, backtest)
│   ├── GretaService instance
│   ├── StrategyRunner instance
│   └── BacktestClock instance
│
└── Shared Singletons
    ├── EventLog (events tagged with run_id)
    ├── BarRepository (immutable data)
    ├── DomainRouter (stateless routing)
    └── SSEBroadcaster (filters by run_id for clients)
```

**Key Isolation Mechanism**: Events carry `run_id` metadata. Consumers filter events by their `run_id` to prevent cross-run interference.

---

## 6. Key Design Decisions

### Dual Alpaca Credentials
Live and Paper run **simultaneously** as separate trading runs, not time-based switching.
→ See [Config](architecture/config.md#2-alpaca-credentials)

### SSE over WebSocket
Unidirectional push is sufficient; SSE has built-in reconnection.
→ See [API](architecture/api.md#why-sse-over-websocket)

### Thin Events Pattern
SSE sends minimal notifications; frontend fetches details via REST.
→ See [API](architecture/api.md#thin-events-pattern)

### Consumer Offsets
At-least-once delivery with crash recovery via offset tracking.
→ See [Events](architecture/events.md#6-consumer-offsets-at-least-once-delivery)

### Bar-Aligned Clock
Ticks fire at bar boundaries (e.g., `:00` seconds for 1m bars).
→ See [Clock](architecture/clock.md)

---

## 7. Terms & Quick Reference

* **Modulith**: single‑process with multiple domain packages
* **EventLog**: DB Outbox + LISTEN/NOTIFY; offsets for recovery
* **Thin events**: keys/status only; details via REST
* **Domain routing**: `strategy.*` → `live.*` or `backtest.*`
* **RealtimeClock**: wall‑clock aligned for live trading
* **BacktestClock**: fast‑forward simulation, no sleeping
* **Bar Alignment**: ticks at bar start (e.g., minute boundary)
* **Dual Credentials**: Live + Paper configured separately for parallel runs

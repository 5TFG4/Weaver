# Event Model & Flows

> Part of [Architecture Documentation](../ARCHITECTURE.md)

## 1. Envelope (Stable Contract)

`{ id, kind:'evt'|'cmd', type, version, run_id, corr_id, causation_id, trace_id, ts, producer, headers, payload }`

### Identity Chain Explained

```
┌─────────────────────────────────────────────────────────────────────┐
│  Event Identity Fields                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  id            Unique identifier for THIS event (UUID)              │
│                → Used for deduplication                             │
│                                                                     │
│  corr_id       Correlation ID — groups related events               │
│                → All events from one user request share this        │
│                → Example: FetchWindow request + all resulting       │
│                  data events share the same corr_id                 │
│                                                                     │
│  causation_id  ID of the event that CAUSED this event               │
│                → Builds a causal chain for debugging                │
│                → Example: orders.Placed has causation_id pointing   │
│                  to orders.PlaceRequest                             │
│                                                                     │
│  trace_id      Distributed tracing ID (optional)                    │
│                → For integration with observability tools           │
│                                                                     │
│  run_id        Which trading run this event belongs to              │
│                → Critical for isolating parallel runs               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Namespaces

| Namespace | Source | Handler | Events |
|-----------|--------|---------|--------|
| `strategy.*` | Marvin | DomainRouter → live/backtest | FetchWindow, PlaceRequest, DecisionMade |
| `live.*` | DomainRouter | Veda | FetchWindow, PlaceOrder |
| `backtest.*` | DomainRouter | Greta | FetchWindow, PlaceOrder |
| `data.*` | Veda/Greta | Marvin | WindowReady, WindowChunk, WindowComplete |
| `market.*` | Exchange | - | Quote, Trade, Bar |
| `orders.*` | Veda/Greta | - | Created, PlaceRequest, Ack, Placed, Filled, Rejected |
| `run.*` | RunManager | SSE | Created, Started, StopRequested, Stopped, Completed, Error |
| `clock.*` | Clock | StrategyRunner | Tick |
| `ui.*` | Frontend | - | (future) |

## 3. Payload & Size Policy

* **Thin events** (to UI): keys + status only; fetch details via REST.
* **Internal events**: ≤ ~100KB inline; 100KB–2MB use `data.WindowChunk/Complete`; >2MB store **reference** only (`data_ref`).

## 4. Typical Flows

* **Fetch**: `strategy.FetchWindow → (GLaDOS route) → live|backtest.FetchWindow → data.WindowReady/Chunk/Complete`.
* **Orders**: `orders.PlaceRequest → orders.Ack/Placed/Filled/Rejected`.
* **Run**: `run.Started/StopRequested/Heartbeat`; `clock.Tick`.

## 5. Delivery & Idempotency

* Write `outbox` in‑transaction; `NOTIFY` after commit; resume via `consumer_offsets`; deduplicate by `id/corr_id`.

## 6. Multi-Run Event Isolation

When multiple runs execute concurrently (parallel backtests, backtest + live):

```
┌─────────────────────────────────────────────────────────────────────┐
│  Event Isolation via run_id                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  EventLog (singleton)                                               │
│    │                                                                │
│    │  event: { run_id: "run-001", type: "orders.Filled", ... }     │
│    │  event: { run_id: "run-002", type: "orders.Filled", ... }     │
│    │                                                                │
│    ├──► GretaService (run-001) filters: run_id == "run-001"        │
│    │                                                                │
│    └──► GretaService (run-002) filters: run_id == "run-002"        │
│                                                                     │
│  Result: Each run only sees its own events                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Pattern**: Events are shared in one EventLog, but consumers filter by `run_id` to maintain isolation.

## 7. Consumer Offsets (At-Least-Once Delivery)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Outbox Table                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ seq │ id     │ type              │ payload    │ created_at  │   │
│  ├─────┼────────┼───────────────────┼────────────┼─────────────┤   │
│  │ 1   │ evt-1  │ orders.Placed     │ {...}      │ 09:30:01    │   │
│  │ 2   │ evt-2  │ orders.Filled     │ {...}      │ 09:30:02    │   │
│  │ 3   │ evt-3  │ clock.Tick        │ {...}      │ 09:31:00    │   │
│  │ 4   │ evt-4  │ strategy.Decision │ {...}      │ 09:31:01    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Consumer Offsets Table                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ consumer_name     │ last_processed_seq │ updated_at         │   │
│  ├───────────────────┼────────────────────┼────────────────────┤   │
│  │ "sse_broadcaster" │ 3                  │ 09:31:00           │   │
│  │ "walle_persister" │ 4                  │ 09:31:01           │   │
│  │ "strategy_runner" │ 2                  │ 09:30:02           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  If "strategy_runner" crashes and restarts:                        │
│  → Reads last_processed_seq = 2                                    │
│  → Resumes from seq > 2 (events 3, 4, ...)                         │
│  → May reprocess event 3 if crash happened mid-processing          │
│  → Consumer must be IDEMPOTENT (handle duplicates gracefully)      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 7. Implementation

**Files**: `src/events/`

| File | Purpose |
|------|---------|
| `protocol.py` | Envelope dataclass, ErrorResponse |
| `types.py` | Event type constants by namespace |
| `registry.py` | Type → Payload validation |
| `log.py` | Outbox write + LISTEN/NOTIFY |
| `offsets.py` | Consumer offset management |

## 8. Data & Persistence

* **Business data (WallE)**: `orders / fills / candles / runs / backtests / strategy_results`, exposed via repositories.
* **EventLog**: `outbox` (fact log) and `consumer_offsets` (progress).
* **Retention & Cleanup**: time/partition based; TTL + audit retention; large payloads may use external storage (store references only).

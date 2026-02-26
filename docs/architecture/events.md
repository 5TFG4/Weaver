# Event Model & Flows

> Part of [Architecture Documentation](../ARCHITECTURE.md)
>
> **Document Charter**  
> **Primary role**: event envelope, event taxonomy, and delivery semantics.  
> **Authoritative for**: event identity chain, namespacing, offsets, and subscription model.  
> **Not authoritative for**: HTTP route planning and milestone tracking.

## 1. Envelope (Stable Contract)

`{ id, kind:'evt'|'cmd', type, version, run_id, corr_id, causation_id, trace_id, ts, producer, headers, payload }`

### 1.1 SSE Wire Format (API Boundary)

Public SSE endpoint: `GET /api/v1/events/stream`

Wire rules:

- each message uses standard SSE framing (`event:` + `data:` + blank line),
- `event` is exactly `Envelope.type` (case-sensitive),
- `data` is JSON object encoded from envelope payload and metadata,
- optional query filter `run_id=<id>` limits stream to a single run.

Example message:

```text
event: run.Started
data: {"id":"evt-123","type":"run.Started","run_id":"run-abc","ts":"2026-02-26T10:00:00Z","payload":{"run_id":"run-abc","status":"running"}}

```

Example order event:

```text
event: orders.Filled
data: {"id":"evt-456","type":"orders.Filled","run_id":"run-abc","payload":{"order_id":"ord-1","filled_qty":"1.0","filled_avg_price":"50000"}}

```

### Contract Appendix (Locked Baseline — Segment 5)

- Event type naming is case-sensitive and currently uses `namespace.PascalCase` (for example `run.Started`, `orders.Filled`).
- SSE `event` is a direct passthrough of `Envelope.type` from backend to clients.
- `ui.*` events are reserved and not currently the public stream contract.
- `run_id` is required for run-scoped lifecycle and routing semantics.
- Contract drift policy: when docs and runtime differ, document both states explicitly and track runtime convergence in the action queue.

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

| Namespace    | Source       | Handler                      | Events                                                       |
| ------------ | ------------ | ---------------------------- | ------------------------------------------------------------ |
| `strategy.*` | Marvin       | DomainRouter → live/backtest | FetchWindow, PlaceRequest, DecisionMade                      |
| `live.*`     | DomainRouter | Veda                         | FetchWindow, PlaceOrder                                      |
| `backtest.*` | DomainRouter | Greta                        | FetchWindow, PlaceOrder                                      |
| `data.*`     | Veda/Greta   | Marvin                       | WindowReady, WindowChunk, WindowComplete                     |
| `market.*`   | Exchange     | -                            | Quote, Trade, Bar                                            |
| `orders.*`   | Veda/Greta   | -                            | **Created**, PlaceRequest, Ack, Placed, Filled, **Rejected** |
| `run.*`      | RunManager   | SSE                          | Created, Started, StopRequested, Stopped, Completed, Error   |
| `clock.*`    | Clock        | StrategyRunner               | Tick                                                         |
| `ui.*`       | Frontend     | -                            | (future)                                                     |

### 2.1 Order Events (M6)

| Event              | Emitter     | Trigger                    | Payload                                                                     |
| ------------------ | ----------- | -------------------------- | --------------------------------------------------------------------------- |
| `orders.Created`   | VedaService | Order accepted by exchange | `{order_id, client_order_id, exchange_order_id, symbol, side, qty, status}` |
| `orders.Rejected`  | VedaService | Order rejected by exchange | `{order_id, client_order_id, symbol, error_code, error_message}`            |
| `orders.Filled`    | VedaService | Order fully filled         | `{order_id, exchange_order_id, filled_qty, filled_avg_price}`               |
| `orders.Cancelled` | VedaService | Order cancelled            | `{order_id, exchange_order_id}`                                             |

## 3. Payload & Size Policy

- **Thin events** (to UI): keys + status only; fetch details via REST.
- **Internal events**: ≤ ~100KB inline; 100KB–2MB use `data.WindowChunk/Complete`; >2MB store **reference** only (`data_ref`).

## 4. Typical Flows

- **Fetch**: `strategy.FetchWindow → (GLaDOS route) → live|backtest.FetchWindow → data.WindowReady/Chunk/Complete`.
- **Orders**: `orders.PlaceRequest → orders.Ack/Placed/Filled/Rejected`.
- **Run**: `run.Started/StopRequested/Heartbeat`; `clock.Tick`.

## 5. Delivery & Idempotency

- Write `outbox` in‑transaction; `NOTIFY` after commit; resume via `consumer_offsets`; deduplicate by `id/corr_id`.

### 5.1 API-Boundary Delivery Semantics

- Delivery guarantee remains at-least-once at event log/consumer boundary.
- API boundary currently guarantees reconnect behavior from SSE clients, but does not guarantee resume-from-last-event replay contract for browser consumers.
- In DB-backed mode, append/offset durability is provided by `outbox` and `consumer_offsets`.
- In no-DB mode, there is no durable event log or offset store; stream delivery is best-effort and non-durable.

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

## 8. Subscription API

EventLog supports filtered subscriptions for real-time event delivery:

```python
from src.events.log import InMemoryEventLog
from src.events.protocol import Envelope

log = InMemoryEventLog()

# Subscribe to specific event types
def on_order_event(envelope: Envelope):
    print(f"Order event: {envelope.type}")

sub_id = log.subscribe_filtered(
    event_types=["orders.Placed", "orders.Filled"],
    callback=on_order_event
)

# Subscribe with custom filter (e.g., by run_id)
sub_id = log.subscribe_filtered(
    event_types=["orders.Placed"],
    callback=on_order_event,
    filter_fn=lambda e: e.run_id == "my-run-id"
)

# Subscribe to ALL events (wildcard)
sub_id = log.subscribe_filtered(
    event_types=["*"],
    callback=on_all_events
)

# Unsubscribe by ID (safe for unknown IDs)
log.unsubscribe_by_id(sub_id)
```

**Key Features:**

- `subscribe_filtered()` returns a unique subscription ID
- Filter by event types (list) + optional custom `filter_fn`
- Wildcard `["*"]` subscribes to all events
- Error in one subscriber doesn't break others (logged, continues)
- `unsubscribe_by_id()` is safe for unknown IDs (no-op)

## 9. Implementation

**Files**: `src/events/`

| File          | Purpose                                                   |
| ------------- | --------------------------------------------------------- |
| `protocol.py` | Envelope dataclass, Subscription dataclass, ErrorResponse |
| `types.py`    | Event type constants by namespace                         |
| `registry.py` | Type → Payload validation                                 |
| `log.py`      | Outbox write + LISTEN/NOTIFY + Subscription management    |
| `offsets.py`  | Consumer offset management                                |

## 10. Data & Persistence

- **Business data (WallE)**: `orders / fills / candles / runs / backtests / strategy_results`, exposed via repositories.
- **EventLog**: `outbox` (fact log) and `consumer_offsets` (progress).
- **Retention & Cleanup**: time/partition based; TTL + audit retention; large payloads may use external storage (store references only).

# External Interfaces (API)

> Part of [Architecture Documentation](../ARCHITECTURE.md)

## 1. REST API

* **Endpoints**: `/healthz`, `/runs` (list/start/stop), `/orders` query, `/candles` query.
* **Purpose**: Synchronous queries and control operations.
* **Implementation**: `src/glados/routes/api.py`

## 2. Realtime Updates (SSE)

* **Endpoint**: `/events/stream` (SSE) or `/events/tail` (REST incremental polling).
* **Purpose**: Push thin events to the frontend in real-time.
* **Implementation**: `src/glados/routes/sse.py`

### Why SSE over WebSocket?

| Consideration | SSE | WebSocket |
|---------------|-----|-----------|
| Direction | Server → Client (unidirectional) | Bidirectional |
| Complexity | Simple, HTTP-based | Requires upgrade, state management |
| Reconnection | Built-in with `Last-Event-ID` | Manual implementation |
| Our use case | Push updates only | Overkill for our needs |

### Thin Events Pattern

SSE sends **minimal notification events**; the frontend fetches full details via REST:

```
┌─────────────────────────────────────────────────────────────────┐
│  Backend                                                        │
│  ┌─────────────────┐                                           │
│  │ Order Filled    │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────────────────────────────┐               │
│  │ SSE Event (thin):                           │               │
│  │ { "type": "ui.order_updated",               │               │
│  │   "order_id": "abc123",                     │               │
│  │   "status": "filled" }                      │  ────────────▶│
│  └─────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Haro)                                                │
│  ┌─────────────────────────────────────────────┐               │
│  │ 1. Receive SSE: "order abc123 filled"       │               │
│  │ 2. GET /orders/abc123 for full details      │  ◀────────────│
│  │ 3. Update UI with complete order data       │               │
│  └─────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits**:
- SSE payloads stay small (< 1KB)
- Frontend always has fresh data from REST
- No need to version SSE payload schemas aggressively

## 3. Auth

* **Local/private**: can run without auth.
* **When exposed**: use a **single API Key** (header), optionally with IP allow‑list.

## 4. Time Semantics

* If no timezone specified in inputs, fall back to system default.
* Responses are UTC or include timezone explicitly.

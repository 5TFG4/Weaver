# External Interfaces (API)

> Part of [Architecture Documentation](../ARCHITECTURE.md)

## 1. REST API

### Implemented Endpoints (M6)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/healthz` | Health check |
| GET | `/api/v1/runs` | List all runs |
| POST | `/api/v1/runs` | Create a new run |
| GET | `/api/v1/runs/{id}` | Get run details |
| POST | `/api/v1/runs/{id}/stop` | Stop a running run |
| GET | `/api/v1/orders` | List orders (optional `run_id` filter) |
| **POST** | `/api/v1/orders` | **Create order via VedaService** |
| GET | `/api/v1/orders/{id}` | Get order details |
| **DELETE** | `/api/v1/orders/{id}` | **Cancel order via VedaService** |
| GET | `/api/v1/candles` | Get OHLCV candles (`symbol`, `timeframe` required) |

### Order Creation (M6-3)

```json
// POST /api/v1/orders
{
  "run_id": "run-123",
  "client_order_id": "order-abc",
  "symbol": "BTC/USD",
  "side": "buy",           // "buy" | "sell"
  "order_type": "market",  // "market" | "limit" | "stop" | "stop_limit"
  "qty": "1.5",
  "limit_price": "50000.00",  // required for limit orders
  "stop_price": null,         // required for stop orders
  "time_in_force": "day",     // "day" | "gtc" | "ioc" | "fok"
  "extended_hours": false
}
```

**Response**: `201 Created` with `OrderResponse`

**Errors**:
- `422 Unprocessable Entity`: Invalid input
- `503 Service Unavailable`: VedaService not configured (no trading credentials)

### API Documentation

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### Implementation

- `src/glados/app.py` - Application factory
- `src/glados/routes/` - Route handlers

## 2. Realtime Updates (SSE)

### Implemented Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/events/stream` | SSE event stream |

### Implementation

- `src/glados/sse_broadcaster.py` - Connection manager
- `src/glados/routes/sse.py` - SSE endpoint

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

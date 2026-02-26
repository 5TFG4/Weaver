# External Interfaces (API)

> Part of [Architecture Documentation](../ARCHITECTURE.md)
>
> **Document Charter**  
> **Primary role**: API/SSE contract and frontend API integration model.  
> **Authoritative for**: endpoint contract and event transport semantics at API boundary.  
> **Not authoritative for**: milestone status and audit backlog.

## 1. REST API

### Contract Appendix (Locked Baseline — Segment 5)

This appendix is the current contract baseline used for review and remediation.

| Surface              | Baseline Contract                                   | Current Runtime State                                    |
| -------------------- | --------------------------------------------------- | -------------------------------------------------------- |
| Health               | `GET /api/v1/healthz`                               | Implemented and tested at `/api/v1/healthz`              |
| Runs start           | `POST /api/v1/runs/{id}/start`                      | Implemented                                              |
| Runs stop            | `POST /api/v1/runs/{id}/stop`                       | Implemented                                              |
| Runs list/create/get | `GET/POST /api/v1/runs`, `GET /api/v1/runs/{id}`    | Implemented                                              |
| Orders list/get      | `GET /api/v1/orders`, `GET /api/v1/orders/{id}`     | Implemented (`VedaService` first, fallback to mock path) |
| Orders create/cancel | `POST /api/v1/orders`, `DELETE /api/v1/orders/{id}` | Implemented via `VedaService`                            |
| SSE stream           | `GET /api/v1/events/stream`                         | Implemented                                              |

**Drift decision (doc vs code):** this appendix records both the locked contract target and current runtime truth when they differ. Code remediation must move runtime to the locked contract, not silently rewrite the contract.

### Implemented Endpoints (M8 Verified)

| Method     | Endpoint                  | Description                                        |
| ---------- | ------------------------- | -------------------------------------------------- |
| GET        | `/api/v1/healthz`         | Health check                                       |
| GET        | `/api/v1/runs`            | List all runs                                      |
| POST       | `/api/v1/runs`            | Create a new run                                   |
| GET        | `/api/v1/runs/{id}`       | Get run details                                    |
| POST       | `/api/v1/runs/{id}/start` | Start a pending run                                |
| POST       | `/api/v1/runs/{id}/stop`  | Stop a running run                                 |
| GET        | `/api/v1/orders`          | List orders (optional `run_id` filter)             |
| **POST**   | `/api/v1/orders`          | **Create order via VedaService**                   |
| GET        | `/api/v1/orders/{id}`     | Get order details                                  |
| **DELETE** | `/api/v1/orders/{id}`     | **Cancel order via VedaService**                   |
| GET        | `/api/v1/candles`         | Get OHLCV candles (`symbol`, `timeframe` required) |

### Order Creation (M6-3)

```json
// POST /api/v1/orders
{
  "run_id": "run-123",
  "client_order_id": "order-abc",
  "symbol": "BTC/USD",
  "side": "buy", // "buy" | "sell"
  "order_type": "market", // "market" | "limit" | "stop" | "stop_limit"
  "qty": "1.5",
  "limit_price": "50000.00", // required for limit orders
  "stop_price": null, // required for stop orders
  "time_in_force": "day", // "day" | "gtc" | "ioc" | "fok"
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

| Method | Endpoint                | Description      |
| ------ | ----------------------- | ---------------- |
| GET    | `/api/v1/events/stream` | SSE event stream |

### SSE Contract Appendix (Locked Baseline — Segment 5)

- SSE `event` field is the exact backend event type (`Envelope.type`) and is case-sensitive.
- Current emitted run/order domain names are PascalCase suffix style (for example `run.Started`, `orders.Created`, `orders.Filled`, `orders.Rejected`).
- Current public stream forwards domain events directly (not `ui.*` projection events).
- Browser-level reconnection is expected; resume from `Last-Event-ID` is not currently guaranteed by an offset replay contract at API boundary.

### Implementation

- `src/glados/sse_broadcaster.py` - Connection manager
- `src/glados/routes/sse.py` - SSE endpoint

### Why SSE over WebSocket?

| Consideration | SSE                              | WebSocket                          |
| ------------- | -------------------------------- | ---------------------------------- |
| Direction     | Server → Client (unidirectional) | Bidirectional                      |
| Complexity    | Simple, HTTP-based               | Requires upgrade, state management |
| Reconnection  | Built-in with `Last-Event-ID`    | Manual implementation              |
| Our use case  | Push updates only                | Overkill for our needs             |

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

## 3. Frontend API Client (Haro)

> Added M7. Documents how the React frontend consumes the backend API.

### 3.1 Three-Layer Architecture

```
Layer 1: client.ts        → Thin fetch wrapper (get/post/del + error handling)
Layer 2: runs.ts etc.     → Domain API functions (no React dependency)
Layer 3: useRuns.ts etc.  → React Query hooks (cache, loading, mutations)
```

**Layer 1 — `haro/src/api/client.ts`**: Generic `get<T>`, `post<T>`, `del<T>` methods.
Handles JSON parsing, `204 No Content` (returns `undefined as T`), error extraction
into `ApiClientError` with status/message/details. All requests include
`Content-Type: application/json`.

**Layer 2 — Domain modules** (`runs.ts`, `orders.ts`, `health.ts`): Pure TypeScript
functions that call Layer 1. Handle query parameter construction (e.g., `?run_id=X&status=Y`
in `fetchOrders`). No React imports — can be tested without rendering.

**Layer 3 — React Query hooks** (`useRuns.ts`, `useOrders.ts`, `useHealth.ts`):
Bind Layer 2 functions to TanStack Query. Provide `{ data, isLoading, error }`
states, automatic cache invalidation on mutations, and polling intervals.

### 3.2 Query Key Convention

All hooks use a hierarchical factory pattern for cache key management:

```typescript
// Example: runKeys
const runKeys = {
  all: ["runs"] as const,
  lists: () => [...runKeys.all, "list"] as const,
  list: (params?) => [...runKeys.lists(), params] as const,
  details: () => [...runKeys.all, "detail"] as const,
  detail: (id: string) => [...runKeys.details(), id] as const,
};
```

- **SSE invalidation** targets the broadest key (`runKeys.all` → `["runs"]`)
  to invalidate all list and detail queries at once.
- **Mutations** invalidate more specifically (e.g., `runKeys.lists()` on create).

### 3.3 SSE Consumption Pattern

The frontend connects to SSE once at the app root (`useSSE()` in `App.tsx`):

```
EventSource("/api/v1/events/stream")
  │
  ├── onopen → isConnected = true
  ├── onerror → isConnected = false, reconnect after 3s
  │
  └── addEventListener("run.started", ...) → {
        queryClient.invalidateQueries({ queryKey: ["runs"] })
        addNotification({ type: "success", message: "Run started" })
      }
```

**Event mapping** (7 event types):

| SSE Event         | Query Invalidated | Notification Type |
| ----------------- | ----------------- | ----------------- |
| `run.Started`     | `["runs"]`        | success           |
| `run.Stopped`     | `["runs"]`        | info              |
| `run.Completed`   | `["runs"]`        | success           |
| `run.Error`       | `["runs"]`        | error             |
| `orders.Created`  | `["orders"]`      | info              |
| `orders.Filled`   | `["orders"]`      | success           |
| `orders.Rejected` | `["orders"]`      | error             |

### 3.4 Vite Proxy

In development, Vite proxies `/api` requests to the backend:

```typescript
// vite.config.ts
server: {
  proxy: { "/api": { target: "http://backend_dev:8000" } }
}
```

In production, Nginx serves the built files and proxies `/api` to the backend container.

### 3.5 TypeScript Types

`haro/src/api/types.ts` mirrors the backend Pydantic schemas exactly:

- `Run`, `RunCreate`, `RunListResponse` (paginated with `total`)
- `Order`, `OrderCreate`, `OrderListResponse`
- `HealthResponse`
- Enums: `RunMode`, `RunStatus`, `OrderSide`, `OrderType`, `OrderStatus`

These types are manually maintained. When backend schemas change, the corresponding
frontend types must be updated.

## 4. Auth

- **Local/private**: can run without auth.
- **When exposed**: use a **single API Key** (header), optionally with IP allow‑list.

## 5. Time Semantics

- If no timezone specified in inputs, fall back to system default.
- Responses are UTC or include timezone explicitly.

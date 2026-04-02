# Weaver Frontend Functional Specification

> **Document type**: Frontend Specification
> **Covers**: All pages, components, interaction logic, state management, real-time communication
> **Tech stack**: React 18 + TypeScript + TanStack React Query + Zustand + Tailwind CSS + Vite
> **Related documents**: [System Overview](SYSTEM_SPEC.md) · [Backend Specification](SPEC_BACKEND.md) · [Data Flow Specification](SPEC_FLOWS.md)

---

## Table of Contents

1. [Technical Architecture](#1-technical-architecture)
2. [Routing Structure](#2-routing-structure)
3. [API Client Layer](#3-api-client-layer)
4. [Data Query Layer (Hooks)](#4-data-query-layer-hooks)
5. [Page Specifications](#5-page-specifications)
6. [Component Specifications](#6-component-specifications)
7. [Real-time Communication (SSE)](#7-real-time-communication-sse)
8. [Notification System](#8-notification-system)
9. [Visual Design](#9-visual-design)

---

## 1. Technical Architecture

### 1.1 Overall Layering

```
┌─────────────────────────────────────────┐
│              Pages (Pages)                │  Dashboard / RunsPage / OrdersPage
├─────────────────────────────────────────┤
│           Components (Components)          │  Layout / Forms / Tables / Modals
├─────────────────────────────────────────┤
│          Custom Hooks (Hooks)              │  useRuns / useOrders / useSSE / useHealth
├─────────────────────────────────────────┤
│          State Management (Stores)         │  Zustand (notifications)
├─────────────────────────────────────────┤
│           API Client (API Layer)           │  client.ts / runs.ts / orders.ts / health.ts
├─────────────────────────────────────────┤
│           TanStack React Query            │  Cache / Auto-refetch / Optimistic Updates
└─────────────────────────────────────────┘
```

### 1.2 Key Configuration

| Item                       | Value                                               |
| -------------------------- | --------------------------------------------------- |
| React Query staleTime      | 60 seconds                                          |
| React Query retry          | 1 time                                              |
| Health check poll interval | 30 seconds                                          |
| SSE reconnect delay        | 3 seconds                                           |
| Toast auto-dismiss         | 5 seconds                                           |
| SSE endpoint               | `/api/v1/events/stream`                             |
| API base path              | `/api/v1` (relative path, forwarded via Vite proxy) |

---

## 2. Routing Structure

| Path                 | Page                   | Description                                  |
| -------------------- | ---------------------- | -------------------------------------------- |
| `/`                  | —                      | Redirects to `/dashboard`                    |
| `/dashboard`         | Dashboard              | System overview, stat cards, recent activity |
| `/runs`              | RunsPage               | Run management, create/start/stop runs       |
| `/runs/:runId`       | RunsPage (detail mode) | Detail view for a single run                 |
| `/orders`            | OrdersPage             | Order list, status filtering, detail modal   |
| `/orders?run_id=xxx` | OrdersPage (filtered)  | Order view filtered by Run                   |
| `/*`                 | NotFound               | 404 page                                     |

---

## 3. API Client Layer

### 3.1 HTTP Client (`api/client.ts`)

Wraps the `fetch` API to provide type-safe HTTP methods:

| Method                  | Purpose                            |
| ----------------------- | ---------------------------------- |
| `get<T>(path, params?)` | GET request, supports query params |
| `post<T>(path, body?)`  | POST request, JSON body            |
| `del<T>(path)`          | DELETE request                     |

**Error handling**:

- Non-2xx response → throws `ApiClientError` (carrying `statusCode` and `details`)
- 204 No Content → returns `undefined`
- Parses JSON error message (extracted from the `detail` field)

### 3.2 Runs API (`api/runs.ts`)

| Function             | HTTP                       | Params                  | Returns           |
| -------------------- | -------------------------- | ----------------------- | ----------------- |
| `fetchRuns(params?)` | `GET /runs`                | page, page_size, status | `RunListResponse` |
| `fetchRun(runId)`    | `GET /runs/{runId}`        | —                       | `Run`             |
| `createRun(data)`    | `POST /runs`               | RunCreate body          | `Run`             |
| `startRun(runId)`    | `POST /runs/{runId}/start` | —                       | `Run`             |
| `stopRun(runId)`     | `POST /runs/{runId}/stop`  | —                       | `Run`             |

### 3.3 Strategies API (`api/strategies.ts`)

| Function            | HTTP              | Params | Returns                |
| ------------------- | ----------------- | ------ | ---------------------- |
| `fetchStrategies()` | `GET /strategies` | —      | `StrategyListResponse` |

Returns metadata for all available strategies (id, name, description, config_schema). `config_schema` is used by the frontend to dynamically render the strategy configuration form.

### 3.4 Orders API (`api/orders.ts`)

| Function               | HTTP                       | Params                          | Returns             |
| ---------------------- | -------------------------- | ------------------------------- | ------------------- |
| `fetchOrders(params?)` | `GET /orders`              | page, page_size, run_id, status | `OrderListResponse` |
| `fetchOrder(orderId)`  | `GET /orders/{orderId}`    | —                               | `Order`             |
| `cancelOrder(orderId)` | `DELETE /orders/{orderId}` | —                               | `void`              |

### 3.5 Health API (`api/health.ts`)

| Function        | HTTP           | Returns          |
| --------------- | -------------- | ---------------- |
| `fetchHealth()` | `GET /healthz` | `HealthResponse` |

### 3.6 Type Definitions (`api/types.ts`)

#### Enum Types

```typescript
RunMode = "live" | "paper" | "backtest";
RunStatus = "pending" | "running" | "stopped" | "completed" | "error";
OrderSide = "buy" | "sell";
OrderType = "market" | "limit" | "stop" | "stop_limit";
OrderStatus =
  "pending" |
  "submitted" |
  "accepted" |
  "partial" |
  "filled" |
  "cancelled" |
  "rejected" |
  "expired";
```

#### Run Types

```typescript
interface Run {
  id: string;
  strategy_id: string;
  mode: RunMode;
  status: RunStatus;
  config: Record<string, unknown>; // All strategy configuration parameters
  created_at: string; // ISO 8601
  started_at?: string;
  stopped_at?: string;
}

interface RunCreate {
  strategy_id: string; // Selected from GET /strategies dropdown
  mode: RunMode;
  config: Record<string, unknown>; // All strategy config (including symbols, timeframe, backtest date range, exchange, etc.)
}
```

#### Order Types

```typescript
interface Order {
  id: string;
  run_id: string;
  client_order_id: string;
  exchange_order_id?: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  qty: string; // Decimal string
  price?: string;
  stop_price?: string;
  time_in_force: string;
  filled_qty: string;
  filled_avg_price?: string;
  status: OrderStatus;
  created_at: string;
  submitted_at?: string;
  filled_at?: string;
  reject_reason?: string;
}
```

---

## 4. Data Query Layer (Hooks)

### 4.1 Runs Hooks (`hooks/useRuns.ts`)

**Cache key structure**:

```typescript
runKeys = {
  all: ["runs"],
  lists: () => ["runs", "list"],
  list: (params) => ["runs", "list", params],
  details: () => ["runs", "detail"],
  detail: (id) => ["runs", "detail", id],
};
```

| Hook               | Type     | Purpose                                                |
| ------------------ | -------- | ------------------------------------------------------ |
| `useRuns(params?)` | Query    | Fetch paginated run list                               |
| `useRun(runId)`    | Query    | Fetch a single run's details                           |
| `useCreateRun()`   | Mutation | Create a new run. Refreshes list cache on success      |
| `useStartRun()`    | Mutation | Start a run. Updates cache + refreshes list on success |
| `useStopRun()`     | Mutation | Stop a run. Updates cache + refreshes list on success  |

**Error handling**: On mutation failure, an error toast is shown via Zustand.

### 4.2 Orders Hooks (`hooks/useOrders.ts`)

**Cache key structure**:

```typescript
orderKeys = {
  all: ["orders"],
  lists: () => ["orders", "list"],
  list: (params) => ["orders", "list", params],
  details: () => ["orders", "detail"],
  detail: (id) => ["orders", "detail", id],
};
```

| Hook                 | Type     | Purpose                                              |
| -------------------- | -------- | ---------------------------------------------------- |
| `useOrders(params?)` | Query    | Fetch order list (supports run_id, status filtering) |
| `useOrder(orderId)`  | Query    | Fetch a single order                                 |
| `useCancelOrder()`   | Mutation | Cancel an order. Refreshes cache on success          |

### 4.3 Strategies Hook (`hooks/useStrategies.ts`)

| Hook              | Type  | Purpose                                                                                                                       |
| ----------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------- |
| `useStrategies()` | Query | Fetch available strategy list (with config_schema), used for dropdown selection and dynamic form rendering when creating runs |

### 4.4 Health Hook (`hooks/useHealth.ts`)

| Hook          | Purpose                                                                    |
| ------------- | -------------------------------------------------------------------------- |
| `useHealth()` | Polls `/healthz` every 30 seconds, used for Dashboard API status indicator |

---

## 5. Page Specifications

### 5.1 Dashboard

**Path**: `/dashboard`

**Function**: An at-a-glance view of system health.

**Data sources**:

- `useRuns({ page: 1, page_size: 50 })` — Fetch all runs
- `useOrders({ page: 1, page_size: 50 })` — Fetch all orders
- `useHealth()` — Fetch API status

**Page content**:

#### Stat Cards Area (4-column grid)

| Card         | Data source  | Calculation                                        |
| ------------ | ------------ | -------------------------------------------------- |
| Active Runs  | runs.items   | `items.filter(r => r.status === "running").length` |
| Total Runs   | runs.total   | Used directly                                      |
| Total Orders | orders.total | Used directly                                      |
| API Status   | health       | Success → green "Online"; failure → red "Offline"  |

#### Recent Activity Area

- Title: `Recent Activity`
- Displays the most recent 5 run records (`runs.items.slice(0, 5)`)
- Each shows: status dot, strategy name, mode badge, status badge, relative time
- Link to `/runs` at the bottom

**State handling**:

- Loading: Display shimmer placeholders (`data-testid="dashboard-loading"`)
- Error: Red error message

---

### 5.2 RunsPage (Run Management Page)

**Path**: `/runs` or `/runs/:runId`

**Function**: Create, view, start, and stop trading runs. This is the most critical operations page.

**Data sources**:

- `useRuns()` — Run list
- `useRun(runId)` — If URL contains runId, load a single record
- `useCreateRun()` — Mutation for creating a run
- `useStopRun()` — Mutation for stopping a run

**Page interactions**:

#### Create Run Flow

1. User clicks the `+ New Run` button
2. Inline form `CreateRunForm` expands
3. Fill in form fields:
   - **Strategy**: Dropdown select, fetches strategy list from `GET /strategies`, required
   - **Mode**: Dropdown select backtest/paper/live, default backtest
   - **Config** (Strategy configuration): Dynamically renders a configuration form based on the selected strategy's `config_schema`. Each strategy requires different parameters (e.g., symbols, timeframe, exchange selection, backtest date range, etc. are all filled in here)
4. Click `Create` to submit
5. Success: Close form, list refreshes automatically
6. Failure: Show error toast

#### Stop Run

- When run status is `running` or `pending`, the actions column shows a `Stop` button
- Clicking calls `useStopRun()`
- Uses optimistic update: immediately marks as stopped in the UI (`stoppedIds` set)

#### Run List Table

| Column   | Data source       | Format                                                         |
| -------- | ----------------- | -------------------------------------------------------------- |
| Run ID   | `run.id`          | Monospace font, truncated display                              |
| Strategy | `run.strategy_id` | Text                                                           |
| Mode     | `run.mode`        | Colored badge (backtest=cyan, paper=purple, live=red)          |
| Status   | `run.status`      | Colored badge (running=green, completed=blue, error=red, etc.) |
| Config   | `run.config`      | Key parameter summary (e.g., symbols, timeframe)               |
| Created  | `run.created_at`  | Local time format                                              |
| Actions  | —                 | Stop button (conditionally shown)                              |

#### Detail Mode

When the URL contains `:runId`, additionally queries a single run and displays it in the same table format.
⚠️ There is no standalone detail page (no order list, equity curve, etc.).

---

### 5.3 OrdersPage (Orders Page)

**Path**: `/orders` or `/orders?run_id=xxx`

**Function**: View and filter all trading orders.

**Data sources**:

- `useOrders({ run_id?, status? })` — Order list

**Page interactions**:

#### Status Filter

Dropdown menu, options:

- All
- Pending / Submitted / Accepted / Partial / Filled / Cancelled / Rejected / Expired

Automatically re-queries upon selection.

#### Run ID Filter

Automatically extracted from URL query parameter `?run_id=xxx`, pre-filters orders to the specified run.

#### Order Table (OrderTable)

| Column   | Data source                        | Format                      |
| -------- | ---------------------------------- | --------------------------- |
| Order ID | `order.id`                         | Monospace font              |
| Symbol   | `order.symbol`                     | Text                        |
| Side     | `order.side`                       | Badge (buy=green, sell=red) |
| Type     | `order.order_type`                 | Text                        |
| Qty      | `order.qty`                        | Number                      |
| Price    | `order.price` / `order.stop_price` | Number or "—"               |
| Status   | `order.status`                     | Colored badge               |
| Time     | `order.created_at`                 | Local time                  |

**Click row → Opens OrderDetailModal**

#### Order Detail Modal (OrderDetailModal)

Clicking an order row opens a modal displaying all fields of the order:

**Two-column grid layout**, containing 15+ fields:

| Group    | Fields                                                       |
| -------- | ------------------------------------------------------------ |
| Identity | Order ID, Client Order ID, Exchange Order ID, Run ID         |
| Trade    | Symbol, Side, Type, Qty, Price, Stop Price, Time in Force    |
| Status   | Status, Filled Qty, Filled Avg Price                         |
| Time     | Created At, Submitted At, Filled At                          |
| Other    | Reject Reason (red background box, shown only when rejected) |

---

### 5.4 NotFound (404 Page)

**Path**: `/*` (all unmatched paths)

**Content**: 404 title + icon + return to dashboard button.

---

## 6. Component Specifications

### 6.1 Layout Components

#### Layout

Outermost container, includes Header + Sidebar + main content area.

```
┌──────── Header ─────────────────────────────────┐
│ [W] Weaver                    ● Connected       │
├────┬────────────────────────────────────────────┤
│    │                                            │
│ S  │                                            │
│ i  │          Main content area                   │
│ d  │          (children)                         │
│ e  │                                            │
│ b  │                                            │
│ a  │                                            │
│ r  │                                            │
│    │                                            │
└────┴────────────────────────────────────────────┘
```

**Props**: `isConnected: boolean` (SSE connection status, passed to Header)

#### Header

Top bar:

- Left: Blue "W" square logo + "Weaver" text (click to navigate home)
- Right: ConnectionStatus component

#### Sidebar

Left navigation bar, width 64px:

- Dashboard icon + text
- Runs icon + text
- Orders icon + text
- Current page highlighted (blue background)
- Non-current page hover effect (dark gray background)

### 6.2 Common Components

#### StatCard

Statistic number card.

| Prop     | Type      | Description                                   |
| -------- | --------- | --------------------------------------------- |
| `title`  | string    | Title (gray small text)                       |
| `value`  | string    | Value (large bold)                            |
| `icon`   | ReactNode | Top-right icon                                |
| `trend`  | string    | Bottom trend text                             |
| `status` | enum      | default/success/warning/error (affects color) |

#### StatusBadge

Status label/pill.

| Variant     | Color  |
| ----------- | ------ |
| `running`   | Green  |
| `completed` | Blue   |
| `stopped`   | Yellow |
| `pending`   | Gray   |
| `error`     | Red    |
| `live`      | Red    |
| `paper`     | Purple |
| `backtest`  | Cyan   |

#### ConnectionStatus

SSE connection status indicator.

- Connected: Green dot + "Connected"
- Disconnected: Red dot + "Disconnected"

#### Toast

Notification message component (fixed at bottom-right corner).

| Type    | Icon | Color  |
| ------- | ---- | ------ |
| success | ✓    | Green  |
| error   | ✕    | Red    |
| warning | ⚠    | Yellow |
| info    | ℹ    | Blue   |

### 6.3 Runs Components

#### CreateRunForm

Inline create run form.

| Field    | Type              | Default    | Validation                                                            |
| -------- | ----------------- | ---------- | --------------------------------------------------------------------- |
| Strategy | select (dropdown) | —          | Required, options from `GET /strategies`                              |
| Mode     | select            | `backtest` | —                                                                     |
| Config   | dynamic form      | —          | Dynamically rendered based on the selected strategy's `config_schema` |

**Dynamic Config form**:

- After selecting a strategy, renders corresponding input controls based on that strategy's `config_schema`
- Supported control types: text input, number input, dropdown select, datetime picker, list input
- Fields with default values are auto-populated
- Required fields are marked with `*`

**Submit handling**:

- Collects all config fields → assembles into a `config` dict
- Calls `onSubmit(RunCreate)`

### 6.4 Orders Components

#### OrderTable

Order table, displaying summary information.

| Prop           | Type            | Description        |
| -------------- | --------------- | ------------------ |
| `orders`       | Order[]         | Data source        |
| `onOrderClick` | (order) => void | Row click callback |

Side column special formatting: buy shows green pill, sell shows red pill.

#### OrderDetailModal

Order detail modal.

| Prop      | Type          | Description                         |
| --------- | ------------- | ----------------------------------- |
| `order`   | Order \| null | Order to display (hidden when null) |
| `onClose` | () => void    | Close callback                      |

**Display rules**:

- `exchange_order_id` is empty → show "—"
- `reject_reason` is non-empty → show red background box
- Amount fields display with full precision

### 6.5 Dashboard Components

#### ActivityFeed

Recent activity feed.

| Prop        | Type    | Description      |
| ----------- | ------- | ---------------- |
| `runs`      | Run[]   | Recent runs list |
| `isLoading` | boolean | Loading state    |

**Time formatting**:

- < 60 seconds: "just now"
- < 60 minutes: "Xm ago"
- < 24 hours: "Xh ago"
- > = 24 hours: "Xd ago"

---

## 7. Real-time Communication (SSE)

### 7.1 useSSE Hook

Called at the application top level (`App.tsx`), maintains a single global SSE connection.

**Connection management**:

- Automatically connects to `/api/v1/events/stream` on startup
- Automatically reconnects after 3 seconds on disconnect
- Closes connection on component unmount

**Event handling mapping**:

| SSE Event Type     | Frontend Action                      |
| ------------------ | ------------------------------------ |
| `run.Started`      | Refresh runs cache + success toast   |
| `run.Stopped`      | Refresh runs cache + info toast      |
| `run.Completed`    | Refresh runs cache + success toast   |
| `run.Error`        | Refresh runs cache + error toast     |
| `orders.Created`   | Refresh orders cache + info toast    |
| `orders.Filled`    | Refresh orders cache + success toast |
| `orders.Rejected`  | Refresh orders cache + error toast   |
| `orders.Cancelled` | Refresh orders cache + info toast    |

**"Refresh cache"** = Calls `queryClient.invalidateQueries()` to invalidate the corresponding React Query cache, triggering an automatic re-fetch.

**Return value**: `{ isConnected: boolean }`

### 7.2 SSE and React Query Collaboration

```
SSE event arrives
  → useSSE receives event
    → invalidateQueries(["runs"]) or invalidateQueries(["orders"])
      → React Query marks cache as stale
        → Automatically re-requests GET /runs or GET /orders
          → UI updates automatically
```

This pattern means the frontend does not need to manually parse data from events—it only needs to know which category of data changed and let React Query re-fetch.

---

## 8. Notification System

### 8.1 Zustand Store

```typescript
// State
notifications: Notification[]

// Actions
addNotification({ type, message })  // Add notification (auto-assigns ID, auto-removes after 5 seconds)
removeNotification(id)              // Manually remove
clearAll()                          // Clear all
```

### 8.2 Notification Sources

| Source           | Trigger                     | Type               |
| ---------------- | --------------------------- | ------------------ |
| SSE events       | Various run/order events    | success/error/info |
| Mutation failure | Create/start/stop run error | error              |

---

## 9. Visual Design

### 9.1 Theme

Dark theme, based on Tailwind CSS Slate color palette:

| Element            | Color                 |
| ------------------ | --------------------- |
| Page background    | `slate-900` (#0f172a) |
| Sidebar background | `slate-800` (#1e293b) |
| Header background  | `slate-800`           |
| Card background    | `slate-800`           |
| Body text          | `slate-200` (#e2e8f0) |
| Secondary text     | `slate-400` (#94a3b8) |
| Primary color      | `blue-600` (#2563eb)  |
| Success color      | `green-500`           |
| Warning color      | `yellow-500`          |
| Danger color       | `red-500`             |

### 9.2 Typography

| Element    | Font class                     |
| ---------- | ------------------------------ |
| Body       | System font stack (sans-serif) |
| Code/ID    | Monospace font (monospace)     |
| Page title | 2xl / 3xl bold                 |
| Card title | sm / base                      |
| Card value | 3xl bold                       |

### 9.3 Responsiveness

- Stat cards: 4-column grid (adapts to screen width)
- Tables: Full width, horizontal scroll on overflow
- Sidebar: Fixed 64px width
- Main content area: flex-1, auto-fill

# M7: Haro Frontend - Design Document

> **Status**: Planning  
> **Estimated Duration**: 1.5-2 weeks  
> **Prerequisites**: M6 ✅ (Live Trading complete, 808 tests)  
> **Target Tests**: ~50 new tests (frontend + integration)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Development Environment Setup](#3-development-environment-setup)
4. [Technology Stack](#4-technology-stack)
5. [MVP Breakdown](#5-mvp-breakdown)
6. [Detailed Implementation Plan](#6-detailed-implementation-plan)
7. [API Integration](#7-api-integration)
8. [SSE Integration](#8-sse-integration)
9. [Testing Strategy](#9-testing-strategy)
10. [File Structure](#10-file-structure)
11. [Risk Mitigation](#11-risk-mitigation)

---

## 1. Overview

### 1.1 Goals

Haro is the React-based web UI for the Weaver trading system. It provides:

- **Dashboard**: System health, active runs, recent activity
- **Runs Management**: Create, monitor, and stop trading runs
- **Orders View**: Real-time order status and history
- **Live Updates**: SSE-powered real-time notifications

### 1.2 Non-Goals (Deferred to M9+)

- Strategy code editor
- Advanced charting (TradingView integration)
- User authentication
- Multi-user support
- Mobile-responsive design

### 1.3 Exit Gate (Definition of Done)

- [ ] React app builds and runs in Docker container
- [ ] Dashboard displays system status and active runs
- [ ] Can create, view, and stop runs via UI
- [ ] Orders page shows order list with status
- [ ] SSE delivers real-time updates to UI
- [ ] ~50 tests passing (unit + E2E)
- [ ] TypeScript strict mode, no any types

---

## 2. Architecture

### 2.1 System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Browser                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Haro React App                                                          ││
│  │   - Dashboard Page                                                      ││
│  │   - Runs Page (List + Detail + Create)                                  ││
│  │   - Orders Page (List + Detail)                                         ││
│  │   - SSE Client (real-time updates)                                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
        │                                            │
        │ HTTP REST (CRUD)                           │ SSE (Server-Sent Events)
        │ localhost:8000                             │ localhost:8000
        ▼                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GLaDOS (FastAPI Backend)                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ REST API                           │ SSE Endpoint                       ││
│  │ GET/POST /api/v1/runs              │ GET /api/v1/events/stream          ││
│  │ GET/POST /api/v1/orders            │                                    ││
│  │ GET /api/v1/candles                │                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Frontend Architecture

```
haro/
├── src/
│   ├── main.tsx                 # Entry point
│   ├── App.tsx                  # Root component + router
│   ├── api/                     # API client layer
│   │   ├── client.ts            # Axios/fetch wrapper
│   │   ├── runs.ts              # Run API functions
│   │   ├── orders.ts            # Order API functions
│   │   └── types.ts             # API response types (from OpenAPI)
│   ├── hooks/                   # Custom React hooks
│   │   ├── useRuns.ts           # Run data + mutations
│   │   ├── useOrders.ts         # Order data + mutations
│   │   ├── useSSE.ts            # SSE connection management
│   │   └── useToast.ts          # Notifications
│   ├── pages/                   # Page components (routes)
│   │   ├── Dashboard.tsx
│   │   ├── RunsPage.tsx
│   │   ├── RunDetailPage.tsx
│   │   ├── OrdersPage.tsx
│   │   └── NotFound.tsx
│   ├── components/              # Reusable UI components
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── runs/
│   │   │   ├── RunCard.tsx
│   │   │   ├── RunList.tsx
│   │   │   ├── RunForm.tsx
│   │   │   └── RunStatusBadge.tsx
│   │   ├── orders/
│   │   │   ├── OrderRow.tsx
│   │   │   ├── OrderTable.tsx
│   │   │   └── OrderStatusBadge.tsx
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorAlert.tsx
│   │       └── EmptyState.tsx
│   ├── stores/                  # State management (Zustand)
│   │   ├── runStore.ts
│   │   └── notificationStore.ts
│   └── utils/                   # Utilities
│       ├── formatters.ts        # Date, number formatting
│       └── constants.ts
├── public/
│   └── favicon.ico
├── tests/                       # Test files
│   ├── unit/
│   │   ├── api/
│   │   ├── hooks/
│   │   └── components/
│   └── e2e/
│       └── runs.spec.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── vitest.config.ts
```

### 2.3 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  User Action                                                                │
│  (Click "Create Run")                                                       │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  React Component (RunForm)                                                  │
│  - Form validation (client-side)                                            │
│  - Call mutation hook                                                       │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  useRuns Hook (React Query mutation)                                        │
│  - POST /api/v1/runs                                                        │
│  - Optimistic update (optional)                                             │
│  - Invalidate queries on success                                            │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Backend Response                                                           │
│  - 201 Created + RunResponse                                                │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  │                                     │
                  ▼                                     ▼
┌─────────────────────────────────────┐  ┌────────────────────────────────────┐
│  React Query Cache                  │  │  SSE Event (async)                 │
│  - Update run list                  │  │  { type: "run.created",            │
│  - Trigger re-render                │  │    run_id: "xxx" }                 │
└─────────────────────────────────────┘  └──────────────────┬─────────────────┘
                                                            │
                                                            ▼
                                         ┌────────────────────────────────────┐
                                         │  SSE Hook                          │
                                         │  - Receive event                   │
                                         │  - Invalidate React Query cache    │
                                         │  - Show toast notification         │
                                         └────────────────────────────────────┘
```

---

## 3. Development Environment Setup

### 3.1 Architecture (Option 3: Hybrid)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  VS Code (Dev Container → backend_dev)                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  /weaver/                                                               ││
│  │  ├── src/         ← Edit Python backend code                            ││
│  │  └── haro/        ← Edit React frontend code                            ││
│  │                                                                         ││
│  │  Tools installed:                                                       ││
│  │  - Python 3.13 (backend runtime + tests)                                ││
│  │  - Node.js 20 LTS (for VS Code TypeScript/ESLint extensions)            ││
│  │                                                                         ││
│  │  VS Code Extensions:                                                    ││
│  │  - Python, Pylance                                                      ││
│  │  - ESLint, Prettier                                                     ││
│  │  - TypeScript (built-in)                                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
         │                              │                          │
         │                              │                          │
         ▼                              ▼                          ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│ backend_dev     │          │ frontend_dev    │          │ db_dev          │
│ Python 3.13     │          │ Node.js 20      │          │ PostgreSQL 16   │
│                 │          │                 │          │                 │
│ uvicorn :8000   │◀─────────│ vite :3000      │          │ :5432           │
│                 │  proxy   │                 │          │                 │
│ /weaver ────────┼──────────┼─ shared volume ─┼──────────│                 │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

### 3.2 File Changes Required

#### 3.2.1 `docker/backend/Dockerfile.dev` (Add Node.js)

```dockerfile
FROM python:3.13-bookworm
WORKDIR /weaver

# Install Node.js 20 LTS (for VS Code TypeScript/ESLint support)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Install Python dev dependencies
COPY requirements.txt requirements.dev.txt /weaver/
RUN pip install --no-cache-dir -r requirements.dev.txt

COPY . /weaver/
CMD ["tail", "-f", "/dev/null"]
```

#### 3.2.2 `docker/frontend/Dockerfile.dev` (Proper Node.js)

```dockerfile
FROM node:20-bookworm
WORKDIR /weaver/haro

# Install dependencies (will be mounted via volume)
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
```

#### 3.2.3 `docker/docker-compose.dev.yml` (Update frontend_dev)

```yaml
services:
  backend_dev:
    # ... existing config ...
    ports:
      - "${HOST_PORT}:8000"
      - "${DEBUG_PORT}:5678"

  frontend_dev:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "${FRONTEND_PORT}:5173" # Vite default port
    volumes:
      - ../:/weaver # Share entire project
      - frontend_node_modules:/weaver/haro/node_modules # Persist node_modules
    environment:
      - VITE_API_BASE_URL=http://backend_dev:8000
    depends_on:
      - backend_dev
    working_dir: /weaver/haro

  db_dev:
    # ... existing config ...

volumes:
  weaver_dev_postgres_data:
  frontend_node_modules: # Named volume for node_modules
```

#### 3.2.4 `.devcontainer/devcontainer.json` (Add frontend extensions)

```jsonc
{
  "name": "Weaver",
  "dockerComposeFile": "../docker/docker-compose.dev.yml",
  "service": "backend_dev",
  "workspaceFolder": "/weaver",
  "initializeCommand": "bash docker/init-env.sh",
  "customizations": {
    "vscode": {
      "extensions": [
        // Python
        "ms-python.python",
        "ms-python.vscode-pylance",
        // Frontend
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode",
        "bradlc.vscode-tailwindcss",
      ],
      "settings": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "[python]": {
          "editor.defaultFormatter": "ms-python.black-formatter",
        },
      },
    },
  },
}
```

### 3.3 Port Mapping Summary

| Service        | Container Port | Host Port | URL                   |
| -------------- | -------------- | --------- | --------------------- |
| Backend API    | 8000           | 8000      | http://localhost:8000 |
| Frontend Dev   | 5173           | 3000      | http://localhost:3000 |
| PostgreSQL     | 5432           | 5432      | -                     |
| Debug (Python) | 5678           | 5678      | -                     |

---

## 4. Technology Stack

### 4.1 Core

| Technology   | Version | Purpose                 |
| ------------ | ------- | ----------------------- |
| React        | 18.x    | UI framework            |
| TypeScript   | 5.x     | Type safety             |
| Vite         | 5.x     | Build tool + dev server |
| React Router | 6.x     | Client-side routing     |

### 4.2 State & Data

| Technology                   | Purpose                                |
| ---------------------------- | -------------------------------------- |
| TanStack Query (React Query) | Server state, caching, mutations       |
| Zustand                      | Client state (notifications, UI state) |

### 4.3 UI Components

| Technology   | Purpose                         |
| ------------ | ------------------------------- |
| Tailwind CSS | Utility-first styling           |
| shadcn/ui    | Accessible component primitives |
| Lucide React | Icons                           |

### 4.4 Testing

| Technology                | Purpose                    |
| ------------------------- | -------------------------- |
| Vitest                    | Unit testing (Vite-native) |
| React Testing Library     | Component testing          |
| MSW (Mock Service Worker) | API mocking                |
| Playwright                | E2E testing (M8)           |

### 4.5 Why These Choices?

| Choice                  | Rationale                                        |
| ----------------------- | ------------------------------------------------ |
| Vite over CRA           | Faster dev server, native ESM, better DX         |
| React Query over Redux  | Server state ≠ client state; RQ handles caching  |
| Zustand over Redux      | Minimal boilerplate for simple client state      |
| Tailwind over CSS-in-JS | Fast iteration, consistent design system         |
| shadcn/ui over MUI      | Copy-paste ownership, smaller bundle, accessible |

---

## 5. MVP Breakdown

### 5.1 Summary

| MVP      | Focus                 | Est. Tests | Dependencies | Duration |
| -------- | --------------------- | ---------- | ------------ | -------- |
| **M7-0** | Dev Environment Setup | 0          | -            | 0.5 day  |
| **M7-1** | React App Scaffold    | ~8         | M7-0         | 1 day    |
| **M7-2** | API Client Layer      | ~10        | M7-1         | 1 day    |
| **M7-3** | Dashboard Page        | ~8         | M7-2         | 1 day    |
| **M7-4** | Runs Page             | ~12        | M7-3         | 2 days   |
| **M7-5** | Orders Page           | ~8         | M7-4         | 1 day    |
| **M7-6** | SSE Integration       | ~8         | M7-5         | 1 day    |

### 5.2 Dependency Graph

```
M7-0: Dev Environment
    │
    ▼
M7-1: React Scaffold
    │
    ▼
M7-2: API Client ─────────────┐
    │                         │
    ▼                         │
M7-3: Dashboard               │
    │                         │
    ▼                         │
M7-4: Runs Page               │
    │                         │
    ▼                         │
M7-5: Orders Page             │
    │                         │
    ▼                         │
M7-6: SSE Integration ◀───────┘
```

---

## 6. Detailed Implementation Plan

### 6.1 M7-0: Development Environment Setup (0.5 day) ✅ COMPLETE

**Goal**: Configure Docker environment for frontend development

#### Tasks

| #   | Task                                                | Status | Files                             |
| --- | --------------------------------------------------- | ------ | --------------------------------- |
| 0.1 | Update backend Dockerfile.dev to include Node.js 20 | ✅     | `docker/backend/Dockerfile.dev`   |
| 0.2 | Create proper frontend Dockerfile.dev with Node.js  | ✅     | `docker/frontend/Dockerfile.dev`  |
| 0.3 | Update docker-compose.dev.yml for frontend service  | ✅     | `docker/docker-compose.dev.yml`   |
| 0.4 | Add frontend VS Code extensions to devcontainer     | ✅     | `.devcontainer/devcontainer.json` |
| 0.5 | Update example.env.dev with frontend port           | ✅     | `docker/example.env.dev`          |
| 0.6 | Document dev environment in DEVELOPMENT.md          | ✅     | `docs/DEVELOPMENT.md`             |
| 0.7 | Create nginx.conf for production frontend           | ✅     | `docker/frontend/nginx.conf`      |
| 0.8 | Update production Dockerfile for multi-stage build  | ✅     | `docker/frontend/Dockerfile`      |

#### Verification

```bash
# After rebuild
docker compose -f docker/docker-compose.dev.yml ps
# Should show: backend_dev, frontend_dev, db_dev all running

# In backend_dev container
node --version  # Should show v20.x
npm --version   # Should show 10.x
```

---

### 6.2 M7-1: React App Scaffold (~8 tests, 1 day) ✅ COMPLETE

**Goal**: Create Haro React project with basic structure

#### Tasks

| #   | Task                                         | Test                | Files                         |
| --- | -------------------------------------------- | ------------------- | ----------------------------- |
| 1.1 | Initialize Vite + React + TypeScript project | ✅ Build passes     | `haro/`                       |
| 1.2 | Configure TypeScript strict mode             | ✅ No TS errors     | `haro/tsconfig.json`          |
| 1.3 | Install and configure Tailwind CSS           | ✅ Styles apply     | `haro/vite.config.ts`         |
| 1.4 | Install React Router, setup basic routes     | ✅ Routes work      | `haro/src/App.tsx`            |
| 1.5 | Create Layout component (Header, Sidebar)    | ✅                  | `haro/src/components/layout/` |
| 1.6 | Create placeholder pages                     | ✅ Navigation works | `haro/src/pages/`             |
| 1.7 | Configure Vitest for testing                 | ✅ Tests run        | `haro/vitest.config.ts`       |
| 1.8 | Add basic component tests                    | ✅ 8 tests pass     | `haro/tests/unit/`            |

#### TDD Specifications

```typescript
// tests/unit/components/Layout.test.tsx
describe("Layout", () => {
  it("renders header with app name");
  it("renders sidebar with navigation links");
  it("renders children in main content area");
  it("highlights active navigation link");
});

// tests/unit/App.test.tsx
describe("App", () => {
  it("renders without crashing");
  it("routes to dashboard by default");
  it("routes to runs page on /runs");
  it("routes to orders page on /orders");
});
```

#### Commands

```bash
# In haro/ directory
npm create vite@latest . -- --template react-ts
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install react-router-dom @tanstack/react-query zustand
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

---

### 6.3 M7-2: API Client Layer (~10 tests, 1 day)

**Goal**: Type-safe API client with error handling

#### Tasks

| #   | Task                                       | Test        | Files                         |
| --- | ------------------------------------------ | ----------- | ----------------------------- |
| 2.1 | Define API response types from OpenAPI     | TS compiles | `haro/src/api/types.ts`       |
| 2.2 | Create base API client with error handling | -           | `haro/src/api/client.ts`      |
| 2.3 | Implement runs API functions               | 4 tests     | `haro/src/api/runs.ts`        |
| 2.4 | Implement orders API functions             | 3 tests     | `haro/src/api/orders.ts`      |
| 2.5 | Configure React Query provider             | -           | `haro/src/main.tsx`           |
| 2.6 | Create useRuns hook with queries/mutations | 2 tests     | `haro/src/hooks/useRuns.ts`   |
| 2.7 | Create useOrders hook                      | 1 test      | `haro/src/hooks/useOrders.ts` |
| 2.8 | Setup MSW for API mocking in tests         | Mocks work  | `haro/tests/mocks/`           |

#### TDD Specifications

```typescript
// tests/unit/api/runs.test.ts
describe("Runs API", () => {
  it("fetchRuns returns paginated list");
  it("fetchRun returns single run by id");
  it("createRun posts correct payload");
  it("stopRun posts to correct endpoint");
});

// tests/unit/api/orders.test.ts
describe("Orders API", () => {
  it("fetchOrders returns paginated list");
  it("fetchOrders filters by run_id");
  it("fetchOrder returns single order by id");
});

// tests/unit/hooks/useRuns.test.tsx
describe("useRuns", () => {
  it("returns loading state initially");
  it("returns data after fetch completes");
});
```

#### API Types (from Backend Schemas)

```typescript
// haro/src/api/types.ts
export type RunMode = "live" | "paper" | "backtest";
export type RunStatus =
  | "pending"
  | "running"
  | "stopped"
  | "completed"
  | "error";
export type OrderSide = "buy" | "sell";
export type OrderType = "market" | "limit" | "stop" | "stop_limit";
export type OrderStatus =
  | "pending"
  | "submitted"
  | "accepted"
  | "partial"
  | "filled"
  | "cancelled"
  | "rejected"
  | "expired";

export interface Run {
  id: string;
  strategy_id: string;
  mode: RunMode;
  status: RunStatus;
  symbols: string[];
  timeframe: string;
  config?: Record<string, unknown>;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface Order {
  id: string;
  run_id: string;
  client_order_id: string;
  exchange_order_id?: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  qty: string;
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

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

---

### 6.4 M7-3: Dashboard Page (~8 tests, 1 day)

**Goal**: Overview page with system status

#### Tasks

| #   | Task                            | Test    | Files                                            |
| --- | ------------------------------- | ------- | ------------------------------------------------ |
| 3.1 | Create StatCard component       | 2 tests | `haro/src/components/common/StatCard.tsx`        |
| 3.2 | Create ActivityFeed component   | 2 tests | `haro/src/components/dashboard/ActivityFeed.tsx` |
| 3.3 | Implement Dashboard page layout | -       | `haro/src/pages/Dashboard.tsx`                   |
| 3.4 | Display active run count        | 1 test  | -                                                |
| 3.5 | Display recent runs list        | 1 test  | -                                                |
| 3.6 | Display API health status       | 1 test  | -                                                |
| 3.7 | Add loading and error states    | 1 test  | -                                                |

#### TDD Specifications

```typescript
// tests/unit/components/StatCard.test.tsx
describe("StatCard", () => {
  it("displays title and value");
  it("displays trend indicator when provided");
});

// tests/unit/pages/Dashboard.test.tsx
describe("Dashboard", () => {
  it("shows loading skeleton initially");
  it("displays active run count");
  it("displays recent runs list");
  it("displays API health status");
  it("shows error alert on fetch failure");
  it('navigates to runs page on "View All" click');
});
```

#### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Dashboard                                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Active Runs │  │ Total Runs  │  │ Total Orders│  │ API Status  │        │
│  │     2       │  │     15      │  │     127     │  │  ● Healthy  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
│  ┌──────────────────────────────────┐  ┌───────────────────────────────┐   │
│  │ Recent Runs                      │  │ Recent Activity               │   │
│  │ ┌──────────────────────────────┐ │  │ • Run abc123 started          │   │
│  │ │ run-001  RUNNING  BTC/USD    │ │  │ • Order xyz filled            │   │
│  │ │ run-002  RUNNING  ETH/USD    │ │  │ • Run def456 completed        │   │
│  │ │ run-003  STOPPED  BTC/USD    │ │  │ • Order qrs rejected          │   │
│  │ └──────────────────────────────┘ │  │                               │   │
│  │ [View All Runs →]                │  │                               │   │
│  └──────────────────────────────────┘  └───────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.5 M7-4: Runs Page (~12 tests, 2 days)

**Goal**: Full CRUD for trading runs

#### Tasks

| #   | Task                                     | Test    | Files                                         |
| --- | ---------------------------------------- | ------- | --------------------------------------------- |
| 4.1 | Create RunStatusBadge component          | 2 tests | `haro/src/components/runs/RunStatusBadge.tsx` |
| 4.2 | Create RunCard component                 | 2 tests | `haro/src/components/runs/RunCard.tsx`        |
| 4.3 | Create RunList component                 | 2 tests | `haro/src/components/runs/RunList.tsx`        |
| 4.4 | Implement RunsPage with list             | 2 tests | `haro/src/pages/RunsPage.tsx`                 |
| 4.5 | Create RunForm component (create dialog) | 2 tests | `haro/src/components/runs/RunForm.tsx`        |
| 4.6 | Implement run creation flow              | 1 test  | -                                             |
| 4.7 | Implement RunDetailPage                  | 1 test  | `haro/src/pages/RunDetailPage.tsx`            |
| 4.8 | Add stop run action                      | -       | -                                             |

#### TDD Specifications

```typescript
// tests/unit/components/RunStatusBadge.test.tsx
describe("RunStatusBadge", () => {
  it("renders correct color for each status");
  it("renders status text");
});

// tests/unit/components/RunCard.test.tsx
describe("RunCard", () => {
  it("displays run strategy and symbols");
  it("displays run status badge");
});

// tests/unit/pages/RunsPage.test.tsx
describe("RunsPage", () => {
  it("displays run list");
  it("opens create dialog on button click");
  it("filters runs by status");
  it("navigates to detail on card click");
});

// tests/unit/components/RunForm.test.tsx
describe("RunForm", () => {
  it("validates required fields");
  it("shows backtest date pickers when mode is backtest");
  it("submits form with correct payload");
  it("displays loading state during submission");
});

// tests/unit/pages/RunDetailPage.test.tsx
describe("RunDetailPage", () => {
  it("displays run details");
  it("shows stop button for running runs");
  it("displays associated orders");
});
```

#### Run Form Fields

| Field       | Type         | Required      | Notes                            |
| ----------- | ------------ | ------------- | -------------------------------- |
| strategy_id | select       | ✓             | Dropdown of available strategies |
| mode        | select       | ✓             | live / paper / backtest          |
| symbols     | multi-select | ✓             | e.g., BTC/USD, ETH/USD           |
| timeframe   | select       | ✓             | 1m, 5m, 15m, 30m, 1h, 4h, 1d     |
| start_time  | datetime     | backtest only | -                                |
| end_time    | datetime     | backtest only | -                                |

---

### 6.6 M7-5: Orders Page (~8 tests, 1 day)

**Goal**: Order list with filtering

#### Tasks

| #   | Task                              | Test    | Files                                             |
| --- | --------------------------------- | ------- | ------------------------------------------------- |
| 5.1 | Create OrderStatusBadge component | 1 test  | `haro/src/components/orders/OrderStatusBadge.tsx` |
| 5.2 | Create OrderTable component       | 2 tests | `haro/src/components/orders/OrderTable.tsx`       |
| 5.3 | Implement OrdersPage              | 2 tests | `haro/src/pages/OrdersPage.tsx`                   |
| 5.4 | Add run_id filter                 | 1 test  | -                                                 |
| 5.5 | Add status filter                 | 1 test  | -                                                 |
| 5.6 | Add order detail modal            | 1 test  | -                                                 |

#### TDD Specifications

```typescript
// tests/unit/components/OrderTable.test.tsx
describe("OrderTable", () => {
  it("renders order rows");
  it("sorts by created_at descending");
});

// tests/unit/pages/OrdersPage.test.tsx
describe("OrdersPage", () => {
  it("displays order table");
  it("filters by run_id from URL param");
  it("filters by status dropdown");
  it("shows empty state when no orders");
  it("opens detail modal on row click");
});
```

#### Order Table Columns

| Column  | Width | Notes                      |
| ------- | ----- | -------------------------- |
| ID      | 100px | Truncated, click to expand |
| Symbol  | 80px  | e.g., BTC/USD              |
| Side    | 60px  | Buy (green) / Sell (red)   |
| Type    | 80px  | Market, Limit, etc.        |
| Qty     | 80px  | Right-aligned              |
| Price   | 80px  | Limit price                |
| Status  | 100px | Badge component            |
| Created | 120px | Relative time              |

---

### 6.7 M7-6: SSE Integration (~8 tests, 1 day)

**Goal**: Real-time updates via Server-Sent Events

#### Tasks

| #   | Task                                        | Test    | Files                                  |
| --- | ------------------------------------------- | ------- | -------------------------------------- |
| 6.1 | Create useSSE hook                          | 3 tests | `haro/src/hooks/useSSE.ts`             |
| 6.2 | Implement auto-reconnection                 | 1 test  | -                                      |
| 6.3 | Create notification store (Zustand)         | 1 test  | `haro/src/stores/notificationStore.ts` |
| 6.4 | Create Toast component                      | 1 test  | `haro/src/components/common/Toast.tsx` |
| 6.5 | Wire SSE events to React Query invalidation | 1 test  | -                                      |
| 6.6 | Add connection status indicator             | 1 test  | -                                      |

#### TDD Specifications

```typescript
// tests/unit/hooks/useSSE.test.tsx
describe("useSSE", () => {
  it("connects to SSE endpoint on mount");
  it("reconnects after connection lost");
  it("calls onEvent callback for each event");
});

// tests/unit/stores/notificationStore.test.ts
describe("notificationStore", () => {
  it("adds notification");
  it("removes notification after timeout");
});
```

#### SSE Event Handling

```typescript
// haro/src/hooks/useSSE.ts
type SSEEventHandler = {
  "run.started": (data: { run_id: string }) => void;
  "run.stopped": (data: { run_id: string }) => void;
  "run.completed": (data: { run_id: string }) => void;
  "run.error": (data: { run_id: string; error: string }) => void;
  "orders.Created": (data: { order_id: string; run_id: string }) => void;
  "orders.Filled": (data: { order_id: string }) => void;
  "orders.Rejected": (data: { order_id: string; reason: string }) => void;
};

// On event received:
// 1. Show toast notification
// 2. Invalidate relevant React Query cache
// 3. Update UI optimistically if needed
```

---

## 7. API Integration

### 7.1 Vite Proxy Configuration

```typescript
// haro/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://backend_dev:8000",
        changeOrigin: true,
      },
    },
  },
});
```

### 7.2 API Client

```typescript
// haro/src/api/client.ts
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(response.status, error.detail || response.statusText);
  }

  return response.json();
}
```

---

## 8. SSE Integration

### 8.1 SSE Client Hook

```typescript
// haro/src/hooks/useSSE.ts
import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNotificationStore } from "../stores/notificationStore";

const SSE_ENDPOINT = "/api/v1/events/stream";
const RECONNECT_DELAY = 3000;

export function useSSE() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number>();

  const connect = useCallback(() => {
    const eventSource = new EventSource(SSE_ENDPOINT);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log("SSE connected");
    };

    eventSource.onerror = () => {
      eventSource.close();
      // Reconnect after delay
      reconnectTimeoutRef.current = window.setTimeout(connect, RECONNECT_DELAY);
    };

    // Handle specific event types
    eventSource.addEventListener("run.started", (e) => {
      const data = JSON.parse(e.data);
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      addNotification({
        type: "success",
        message: `Run ${data.run_id} started`,
      });
    });

    eventSource.addEventListener("run.stopped", (e) => {
      const data = JSON.parse(e.data);
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      addNotification({ type: "info", message: `Run ${data.run_id} stopped` });
    });

    eventSource.addEventListener("orders.Filled", (e) => {
      const data = JSON.parse(e.data);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      addNotification({ type: "success", message: `Order filled` });
    });

    // ... more event handlers
  }, [queryClient, addNotification]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connect]);
}
```

---

## 9. Testing Strategy

### 9.1 Test Pyramid

```
                    ┌───────────────┐
                    │   E2E (M8)    │  ~10 tests
                    │  Playwright   │
                    └───────────────┘
               ┌─────────────────────────┐
               │   Integration Tests     │  ~15 tests
               │   MSW + React Query     │
               └─────────────────────────┘
          ┌───────────────────────────────────┐
          │         Unit Tests               │  ~35 tests
          │   Components, Hooks, Utils       │
          └───────────────────────────────────┘
```

### 9.2 Testing Tools

| Tool                        | Purpose                         |
| --------------------------- | ------------------------------- |
| Vitest                      | Test runner (Vite-native, fast) |
| React Testing Library       | Component testing               |
| MSW                         | API mocking                     |
| @testing-library/user-event | User interaction simulation     |

### 9.3 Test File Conventions

```
haro/tests/
├── unit/
│   ├── components/
│   │   ├── Layout.test.tsx
│   │   ├── RunCard.test.tsx
│   │   └── ...
│   ├── hooks/
│   │   ├── useRuns.test.tsx
│   │   └── useSSE.test.tsx
│   ├── api/
│   │   ├── runs.test.ts
│   │   └── orders.test.ts
│   └── stores/
│       └── notificationStore.test.ts
├── integration/
│   ├── Dashboard.test.tsx
│   ├── RunsPage.test.tsx
│   └── OrdersPage.test.tsx
├── mocks/
│   ├── handlers.ts       # MSW handlers
│   ├── server.ts         # MSW setup
│   └── data.ts           # Mock data fixtures
└── setup.ts              # Test setup file
```

### 9.4 MSW Mock Setup

```typescript
// haro/tests/mocks/handlers.ts
import { http, HttpResponse } from "msw";
import { mockRuns, mockOrders } from "./data";

export const handlers = [
  http.get("/api/v1/runs", () => {
    return HttpResponse.json({
      items: mockRuns,
      total: mockRuns.length,
      page: 1,
      page_size: 20,
    });
  }),

  http.post("/api/v1/runs", async ({ request }) => {
    const body = await request.json();
    const newRun = {
      id: `run-${Date.now()}`,
      status: "pending",
      created_at: new Date().toISOString(),
      ...body,
    };
    return HttpResponse.json(newRun, { status: 201 });
  }),

  // ... more handlers
];
```

---

## 10. File Structure

### 10.1 Complete Haro Directory

```
haro/
├── public/
│   └── favicon.ico
├── src/
│   ├── main.tsx                      # Entry point
│   ├── App.tsx                       # Root component + QueryProvider
│   ├── index.css                     # Tailwind imports
│   │
│   ├── api/                          # API layer
│   │   ├── client.ts                 # Base fetch wrapper
│   │   ├── types.ts                  # TypeScript types
│   │   ├── runs.ts                   # Run API functions
│   │   └── orders.ts                 # Order API functions
│   │
│   ├── hooks/                        # React hooks
│   │   ├── useRuns.ts                # Run queries + mutations
│   │   ├── useOrders.ts              # Order queries
│   │   └── useSSE.ts                 # SSE connection
│   │
│   ├── stores/                       # Zustand stores
│   │   └── notificationStore.ts
│   │
│   ├── pages/                        # Route pages
│   │   ├── Dashboard.tsx
│   │   ├── RunsPage.tsx
│   │   ├── RunDetailPage.tsx
│   │   ├── OrdersPage.tsx
│   │   └── NotFound.tsx
│   │
│   ├── components/                   # UI components
│   │   ├── layout/
│   │   │   ├── Layout.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── common/
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorAlert.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   ├── StatCard.tsx
│   │   │   └── Toast.tsx
│   │   ├── runs/
│   │   │   ├── RunCard.tsx
│   │   │   ├── RunList.tsx
│   │   │   ├── RunForm.tsx
│   │   │   └── RunStatusBadge.tsx
│   │   ├── orders/
│   │   │   ├── OrderTable.tsx
│   │   │   ├── OrderRow.tsx
│   │   │   └── OrderStatusBadge.tsx
│   │   └── dashboard/
│   │       └── ActivityFeed.tsx
│   │
│   └── utils/
│       ├── formatters.ts             # Date, number formatting
│       └── constants.ts              # App constants
│
├── tests/
│   ├── setup.ts                      # Vitest setup
│   ├── mocks/
│   │   ├── handlers.ts
│   │   ├── server.ts
│   │   └── data.ts
│   ├── unit/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── stores/
│   └── integration/
│
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── vitest.config.ts
├── tailwind.config.js
├── postcss.config.js
├── .eslintrc.cjs
└── .prettierrc
```

### 10.2 Package.json Scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "lint": "eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint src --ext ts,tsx --fix",
    "format": "prettier --write \"src/**/*.{ts,tsx}\"",
    "type-check": "tsc --noEmit"
  }
}
```

---

## 11. Risk Mitigation

### 11.1 Technical Risks

| Risk                         | Probability | Impact | Mitigation                                 |
| ---------------------------- | ----------- | ------ | ------------------------------------------ |
| CORS issues                  | Medium      | Low    | Vite proxy handles in dev; nginx in prod   |
| SSE reconnection failures    | Low         | Medium | Exponential backoff + connection status UI |
| Large bundle size            | Low         | Low    | Dynamic imports, tree shaking              |
| TypeScript strictness issues | Medium      | Low    | Incremental adoption                       |

### 11.2 Schedule Risks

| Risk                         | Probability | Impact | Mitigation                             |
| ---------------------------- | ----------- | ------ | -------------------------------------- |
| shadcn/ui learning curve     | Medium      | Low    | Use plain Tailwind initially if needed |
| Dev environment setup issues | Medium      | Medium | Document thoroughly, test on rebuild   |
| Scope creep (more features)  | High        | Medium | Stick to MVP, defer to M9              |

### 11.3 Fallback Options

1. **If shadcn/ui is too complex**: Use plain Tailwind + basic HTML elements
2. **If React Query is overkill**: Use simple useState + useEffect
3. **If Zustand not needed**: React Context for notifications
4. **If SSE problematic**: Polling as fallback (every 5s)

---

## 12. Success Criteria

### 12.1 Quantitative

| Metric                 | Target          |
| ---------------------- | --------------- |
| Tests passing          | ~50             |
| TypeScript coverage    | 100% (no `any`) |
| Build time             | < 30s           |
| Bundle size (gzipped)  | < 200KB         |
| Lighthouse performance | > 80            |

### 12.2 Qualitative

- [ ] Developer can create and monitor a backtest run via UI
- [ ] Real-time updates appear within 1 second of backend event
- [ ] Error states are clearly communicated
- [ ] Navigation is intuitive

---

## 13. Execution Checklist

### Phase 1: Environment (Day 1, Morning)

- [ ] M7-0: Docker environment setup
- [ ] Verify containers start correctly
- [ ] Verify VS Code extensions work

### Phase 2: Scaffold (Day 1-2)

- [ ] M7-1.1-1.4: Vite + React + Router + Tailwind
- [ ] M7-1.5-1.6: Layout + placeholder pages
- [ ] M7-1.7-1.8: Vitest + initial tests

### Phase 3: API Layer (Day 3)

- [ ] M7-2.1-2.2: Types + client
- [ ] M7-2.3-2.5: API functions + React Query
- [ ] M7-2.6-2.8: Hooks + MSW

### Phase 4: Pages (Day 4-7)

- [ ] M7-3: Dashboard
- [ ] M7-4: Runs (list, create, detail)
- [ ] M7-5: Orders

### Phase 5: SSE (Day 8)

- [ ] M7-6: SSE integration + notifications

### Phase 6: Polish (Day 9-10)

- [ ] Fix bugs, improve UX
- [ ] Documentation
- [ ] Final testing

---

_Document Created: 2026-02-04_  
_Last Updated: 2026-02-04_  
_Author: Weaver Team_

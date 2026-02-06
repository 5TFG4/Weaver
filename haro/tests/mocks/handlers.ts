/**
 * MSW Handlers
 *
 * Mock Service Worker handlers for API mocking in tests.
 */

import { http, HttpResponse } from "msw";
import type {
  Run,
  Order,
  RunListResponse,
  OrderListResponse,
  HealthResponse,
} from "../../src/api/types";

// =============================================================================
// Mock Data
// =============================================================================

export const mockRuns: Run[] = [
  {
    id: "run-1",
    strategy_id: "sma-crossover",
    mode: "backtest",
    status: "completed",
    symbols: ["BTC/USD"],
    timeframe: "1h",
    created_at: "2026-02-01T10:00:00Z",
    started_at: "2026-02-01T10:00:01Z",
    stopped_at: "2026-02-01T10:05:00Z",
  },
  {
    id: "run-2",
    strategy_id: "sma-crossover",
    mode: "paper",
    status: "running",
    symbols: ["ETH/USD"],
    timeframe: "15m",
    created_at: "2026-02-04T08:00:00Z",
    started_at: "2026-02-04T08:00:01Z",
  },
];

export const mockOrders: Order[] = [
  {
    id: "order-1",
    run_id: "run-1",
    client_order_id: "client-1",
    exchange_order_id: "exch-1",
    symbol: "BTC/USD",
    side: "buy",
    order_type: "market",
    qty: "0.1",
    time_in_force: "day",
    filled_qty: "0.1",
    filled_avg_price: "45000.00",
    status: "filled",
    created_at: "2026-02-01T10:01:00Z",
    submitted_at: "2026-02-01T10:01:01Z",
    filled_at: "2026-02-01T10:01:02Z",
  },
  {
    id: "order-2",
    run_id: "run-2",
    client_order_id: "client-2",
    symbol: "ETH/USD",
    side: "buy",
    order_type: "limit",
    qty: "1.0",
    price: "2500.00",
    time_in_force: "gtc",
    filled_qty: "0",
    status: "pending",
    created_at: "2026-02-04T08:05:00Z",
  },
];

// =============================================================================
// Handlers
// =============================================================================

export const handlers = [
  // GET /api/v1/healthz - Health check
  http.get("/api/v1/healthz", () => {
    const response: HealthResponse = {
      status: "ok",
      version: "0.1.0",
    };
    return HttpResponse.json(response);
  }),

  // GET /api/v1/runs - List runs
  http.get("/api/v1/runs", () => {
    const response: RunListResponse = {
      items: mockRuns,
      total: mockRuns.length,
      page: 1,
      page_size: 20,
    };
    return HttpResponse.json(response);
  }),

  // GET /api/v1/runs/:id - Get run by ID
  http.get("/api/v1/runs/:id", ({ params }) => {
    const run = mockRuns.find((r) => r.id === params.id);
    if (!run) {
      return HttpResponse.json({ detail: "Run not found" }, { status: 404 });
    }
    return HttpResponse.json(run);
  }),

  // POST /api/v1/runs - Create run
  http.post("/api/v1/runs", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newRun: Run = {
      id: `run-${Date.now()}`,
      strategy_id: body.strategy_id as string,
      mode: body.mode as Run["mode"],
      status: "pending",
      symbols: body.symbols as string[],
      timeframe: (body.timeframe as string) || "1m",
      created_at: new Date().toISOString(),
    };
    return HttpResponse.json(newRun, { status: 201 });
  }),

  // POST /api/v1/runs/:id/start - Start run
  http.post("/api/v1/runs/:id/start", ({ params }) => {
    const run = mockRuns.find((r) => r.id === params.id);
    if (!run) {
      return HttpResponse.json({ detail: "Run not found" }, { status: 404 });
    }
    return HttpResponse.json({
      ...run,
      status: "running",
      started_at: new Date().toISOString(),
    });
  }),

  // POST /api/v1/runs/:id/stop - Stop run
  http.post("/api/v1/runs/:id/stop", ({ params }) => {
    const run = mockRuns.find((r) => r.id === params.id);
    if (!run) {
      return HttpResponse.json({ detail: "Run not found" }, { status: 404 });
    }
    return HttpResponse.json({
      ...run,
      status: "stopped",
      stopped_at: new Date().toISOString(),
    });
  }),

  // GET /api/v1/orders - List orders
  http.get("/api/v1/orders", ({ request }) => {
    const url = new URL(request.url);
    const runId = url.searchParams.get("run_id");

    let orders = mockOrders;
    if (runId) {
      orders = orders.filter((o) => o.run_id === runId);
    }

    const response: OrderListResponse = {
      items: orders,
      total: orders.length,
      page: 1,
      page_size: 50,
    };
    return HttpResponse.json(response);
  }),

  // GET /api/v1/orders/:id - Get order by ID
  http.get("/api/v1/orders/:id", ({ params }) => {
    const order = mockOrders.find((o) => o.id === params.id);
    if (!order) {
      return HttpResponse.json({ detail: "Order not found" }, { status: 404 });
    }
    return HttpResponse.json(order);
  }),

  // DELETE /api/v1/orders/:id - Cancel order
  http.delete("/api/v1/orders/:id", ({ params }) => {
    const order = mockOrders.find((o) => o.id === params.id);
    if (!order) {
      return HttpResponse.json({ detail: "Order not found" }, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),
];

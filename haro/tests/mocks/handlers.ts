/**
 * MSW Handlers
 *
 * Mock Service Worker handlers for API mocking in tests.
 */

import { http, HttpResponse } from "msw";
import type {
  Run,
  Order,
  BacktestResult,
  RunListResponse,
  OrderListResponse,
  HealthResponse,
  StrategyMeta,
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
    config: { symbols: ["BTC/USD"], timeframe: "1h" },
    error: null,
    created_at: "2026-02-01T10:00:00Z",
    started_at: "2026-02-01T10:00:01Z",
    stopped_at: "2026-02-01T10:05:00Z",
  },
  {
    id: "run-2",
    strategy_id: "sma-crossover",
    mode: "paper",
    status: "running",
    config: { symbols: ["ETH/USD"], timeframe: "15m" },
    error: null,
    created_at: "2026-02-04T08:00:00Z",
    started_at: "2026-02-04T08:00:01Z",
  },
];

export const mockBacktestResult: BacktestResult = {
  run_id: "run-1",
  start_time: "2026-02-01T10:00:00Z",
  end_time: "2026-02-01T10:05:00Z",
  timeframe: "1h",
  symbols: ["BTC/USD"],
  final_equity: "10500.00",
  simulation_duration_ms: 1234,
  total_bars_processed: 100,
  stats: {
    total_return: 5000.0,
    total_return_pct: 5.0,
    annualized_return: 8.5,
    sharpe_ratio: 1.23,
    sortino_ratio: 1.5,
    max_drawdown: -2000.0,
    max_drawdown_pct: -2.0,
    total_trades: 5,
    winning_trades: 3,
    losing_trades: 2,
    win_rate: 60.0,
    avg_win: 2500.0,
    avg_loss: -1000.0,
    profit_factor: 3.75,
    total_bars: 100,
    bars_in_position: 40,
    total_commission: 5.0,
    total_slippage: 1.0,
  },
  equity_curve: [
    { timestamp: "2026-02-01T10:00:00Z", equity: 10000 },
    { timestamp: "2026-02-01T10:01:00Z", equity: 10100 },
    { timestamp: "2026-02-01T10:02:00Z", equity: 10050 },
    { timestamp: "2026-02-01T10:03:00Z", equity: 10200 },
    { timestamp: "2026-02-01T10:04:00Z", equity: 10350 },
    { timestamp: "2026-02-01T10:05:00Z", equity: 10500 },
  ],
  fills: [
    {
      timestamp: "2026-02-01T10:00:30Z",
      symbol: "BTC/USD",
      side: "buy",
      qty: "0.1",
      fill_price: "100.50",
      commission: "0.10",
      slippage: "0.01",
    },
    {
      timestamp: "2026-02-01T10:03:00Z",
      symbol: "BTC/USD",
      side: "sell",
      qty: "0.1",
      fill_price: "102.00",
      commission: "0.10",
      slippage: "0.02",
    },
  ],
};

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

export const mockStrategies: StrategyMeta[] = [
  {
    id: "sample",
    name: "Sample Mean-Reversion Strategy",
    version: "1.0.0",
    description: "Simple mean-reversion strategy for testing",
    author: "weaver",
    config_schema: {
      type: "object",
      properties: {
        symbols: {
          type: "array",
          items: {
            type: "string",
            enum: ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"],
          },
        },
        timeframe: { type: "string", default: "1m" },
      },
      required: ["symbols"],
    },
  },
  {
    id: "sma-crossover",
    name: "SMA Crossover Strategy",
    version: "1.0.0",
    description: "Simple Moving Average crossover strategy",
    author: "weaver",
    config_schema: {
      type: "object",
      properties: {
        symbols: {
          type: "array",
          items: {
            type: "string",
            enum: ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"],
          },
        },
        timeframe: { type: "string", default: "1m" },
        fast_period: { type: "integer", default: 5 },
        slow_period: { type: "integer", default: 20 },
      },
      required: ["symbols"],
    },
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

  // GET /api/v1/strategies - List strategies
  http.get("/api/v1/strategies", () => {
    return HttpResponse.json(mockStrategies);
  }),

  // GET /api/v1/runs - List runs
  http.get("/api/v1/runs", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const filtered = status
      ? mockRuns.filter((r) => r.status === status)
      : mockRuns;
    const response: RunListResponse = {
      items: filtered,
      total: filtered.length,
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

  // GET /api/v1/runs/:id/results - Get backtest results
  http.get("/api/v1/runs/:id/results", ({ params }) => {
    if (params.id === mockBacktestResult.run_id) {
      return HttpResponse.json(mockBacktestResult);
    }
    return HttpResponse.json({ detail: "Results not found" }, { status: 404 });
  }),

  // POST /api/v1/runs - Create run
  http.post("/api/v1/runs", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newRun: Run = {
      id: `run-${Date.now()}`,
      strategy_id: body.strategy_id as string,
      mode: body.mode as Run["mode"],
      status: "pending",
      config: (body.config as Record<string, unknown>) ?? {},
      error: null,
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
    const status = url.searchParams.get("status");

    let orders = mockOrders;
    if (runId) {
      orders = orders.filter((o) => o.run_id === runId);
    }
    if (status) {
      orders = orders.filter((o) => o.status === status);
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

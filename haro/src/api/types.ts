/**
 * API Types
 *
 * TypeScript types matching backend Pydantic schemas.
 * Keep in sync with src/glados/schemas.py
 */

// =============================================================================
// Enums
// =============================================================================

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

// =============================================================================
// Run Types
// =============================================================================

export interface Run {
  id: string;
  strategy_id: string;
  mode: RunMode;
  status: RunStatus;
  config: Record<string, unknown>;
  error: string | null;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface RunCreate {
  strategy_id: string;
  mode: RunMode;
  config: Record<string, unknown>;
}

export interface RunListResponse {
  items: Run[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// Backtest Result Types
// =============================================================================

export interface BacktestResult {
  run_id: string;
  start_time: string;
  end_time: string;
  timeframe: string;
  symbols: string[];
  final_equity: string;
  simulation_duration_ms: number;
  total_bars_processed: number;
  stats: Record<string, unknown>;
  equity_curve: Array<{ timestamp: string; equity: number }>;
  fills: Array<Record<string, unknown>>;
}

// =============================================================================
// Order Types
// =============================================================================

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

export interface OrderCreate {
  run_id: string;
  client_order_id: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  qty: string;
  limit_price?: string;
  stop_price?: string;
  time_in_force?: string;
  extended_hours?: boolean;
}

export interface OrderListResponse {
  items: Order[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// Health Types
// =============================================================================

export interface HealthResponse {
  status: string;
  version: string;
}

// =============================================================================
// API Error
// =============================================================================

export interface ApiError {
  detail: string;
  status_code?: number;
}

// =============================================================================
// Strategy Types
// =============================================================================

export interface StrategyMeta {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  config_schema: Record<string, unknown> | null;
}

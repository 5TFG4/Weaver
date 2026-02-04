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
  symbols: string[];
  timeframe: string;
  config?: Record<string, unknown>;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface RunCreate {
  strategy_id: string;
  mode: RunMode;
  symbols: string[];
  timeframe?: string;
  start_time?: string; // ISO 8601 for backtest
  end_time?: string; // ISO 8601 for backtest
  config?: Record<string, unknown>;
}

export interface RunListResponse {
  items: Run[];
  total: number;
  page: number;
  page_size: number;
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

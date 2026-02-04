"""
GLaDOS API Schemas

Pydantic models for API request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class RunMode(str, Enum):
    """Trading run mode."""

    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"


class RunStatus(str, Enum):
    """Run lifecycle status."""

    PENDING = "pending"  # Created, not started
    RUNNING = "running"  # Actively trading
    STOPPED = "stopped"  # Manually stopped
    COMPLETED = "completed"  # Finished (backtest end or strategy exit)
    ERROR = "error"  # Failed with error


# =============================================================================
# Health
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


# =============================================================================
# Run Schemas
# =============================================================================


class RunCreate(BaseModel):
    """Request body for creating a run."""

    strategy_id: str = Field(..., min_length=1)
    mode: RunMode
    symbols: list[str] = Field(..., min_length=1)
    timeframe: str = Field(default="1m")
    # Backtest-specific (required when mode=backtest)
    start_time: datetime | None = None
    end_time: datetime | None = None
    # Optional strategy config
    config: dict[str, Any] | None = None


class RunResponse(BaseModel):
    """Full run details response."""

    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    symbols: list[str]
    timeframe: str
    config: dict[str, Any] | None = None
    # Timestamps
    created_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    items: list[RunResponse]
    total: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# Order Schemas
# =============================================================================


class OrderSide(str, Enum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderCreate(BaseModel):
    """Request body for creating an order."""

    run_id: str = Field(..., min_length=1)
    client_order_id: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    side: OrderSide
    order_type: OrderType
    qty: str = Field(..., description="Quantity as decimal string")
    limit_price: str | None = Field(default=None, description="Limit price for LIMIT orders")
    stop_price: str | None = Field(default=None, description="Stop price for STOP orders")
    time_in_force: str = Field(default="day")
    extended_hours: bool = Field(default=False)


class OrderResponse(BaseModel):
    """Full order details response."""

    id: str
    run_id: str
    client_order_id: str
    exchange_order_id: str | None = None
    # Order details
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: str  # Decimal as string for JSON
    price: str | None = None
    stop_price: str | None = None
    time_in_force: str = "day"
    # Fill info
    filled_qty: str = "0"
    filled_avg_price: str | None = None
    # Status & timestamps
    status: OrderStatus
    created_at: datetime
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    # Error info
    reject_reason: str | None = None


class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    items: list[OrderResponse]
    total: int
    page: int = 1
    page_size: int = 50


# =============================================================================
# Candle Schemas
# =============================================================================


class CandleResponse(BaseModel):
    """Single OHLCV candle."""

    symbol: str
    timeframe: str
    timestamp: datetime
    open: str  # Decimal as string for JSON
    high: str
    low: str
    close: str
    volume: str
    trade_count: int | None = None


class CandleListResponse(BaseModel):
    """List of candles."""

    symbol: str
    timeframe: str
    items: list[CandleResponse]


"""
GLaDOS API Schemas

Pydantic models for API request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

# =============================================================================
# Enums
# =============================================================================


class RunMode(StrEnum):
    """Trading run mode."""

    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"


class RunStatus(StrEnum):
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

    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(..., min_length=1)
    mode: RunMode
    config: dict[str, Any] = Field(
        ..., description="Strategy configuration containing symbols, timeframe, etc."
    )

    @model_validator(mode="after")
    def validate_backtest_dates(self) -> RunCreate:
        """Require valid timezone-aware backtest_start/backtest_end when mode is backtest."""
        if self.mode != RunMode.BACKTEST:
            return self

        start_raw = self.config.get("backtest_start")
        end_raw = self.config.get("backtest_end")

        if start_raw is None:
            raise ValueError("config.backtest_start is required for backtest mode")
        if end_raw is None:
            raise ValueError("config.backtest_end is required for backtest mode")

        try:
            start = datetime.fromisoformat(start_raw)
        except (ValueError, TypeError):
            raise ValueError("config.backtest_start must be a valid ISO 8601 datetime")

        try:
            end = datetime.fromisoformat(end_raw)
        except (ValueError, TypeError):
            raise ValueError("config.backtest_end must be a valid ISO 8601 datetime")

        if start.tzinfo is None:
            raise ValueError("config.backtest_start must include timezone (e.g. 'Z' or '+00:00')")
        if end.tzinfo is None:
            raise ValueError("config.backtest_end must include timezone (e.g. 'Z' or '+00:00')")

        if end <= start:
            raise ValueError("config.backtest_end must be after backtest_start")

        return self


class RunResponse(BaseModel):
    """Full run details response."""

    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    config: dict[str, Any]
    error: str | None = None
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
# Backtest Result Schemas
# =============================================================================


class BacktestResultResponse(BaseModel):
    """Response body for GET /runs/{run_id}/results."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    start_time: datetime
    end_time: datetime
    timeframe: str
    symbols: list[str]
    final_equity: str
    simulation_duration_ms: int
    total_bars_processed: int
    stats: dict[str, Any]
    equity_curve: list[dict[str, Any]]
    fills: list[dict[str, Any]]


# =============================================================================
# Order Schemas
# =============================================================================


class OrderSide(StrEnum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Order type."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(StrEnum):
    """Order status."""

    PENDING = "pending"
    SUBMITTING = "submitting"
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

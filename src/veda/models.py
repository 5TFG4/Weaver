"""
Veda Data Models

Domain models for live trading operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING


# =============================================================================
# Enums
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


class TimeInForce(str, Enum):
    """Order time-in-force options."""

    DAY = "day"  # Valid until end of regular trading hours
    GTC = "gtc"  # Good til cancelled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    # Initial states
    PENDING = "pending"  # Created locally, not yet submitted
    SUBMITTING = "submitting"  # Being sent to exchange

    # Exchange acknowledged states
    SUBMITTED = "submitted"  # Sent, awaiting exchange ack
    ACCEPTED = "accepted"  # Exchange accepted, in order book
    PARTIALLY_FILLED = "partial"  # Some quantity filled

    # Terminal states
    FILLED = "filled"  # Fully filled
    CANCELLED = "cancelled"  # Cancelled (by user or system)
    REJECTED = "rejected"  # Rejected by exchange
    EXPIRED = "expired"  # Time-in-force expired


class PositionSide(str, Enum):
    """Position side."""

    LONG = "long"
    SHORT = "short"


# =============================================================================
# Order Models
# =============================================================================


@dataclass(frozen=True)
class OrderIntent:
    """
    Strategy's order intent - what the strategy WANTS to do.

    This is the INPUT to Veda, coming from strategy.PlaceRequest events.
    Immutable to ensure intent cannot be modified after creation.
    """

    run_id: str
    client_order_id: str  # Idempotency key (strategy-generated)
    symbol: str
    side: OrderSide  # BUY | SELL
    order_type: OrderType  # MARKET | LIMIT | STOP | STOP_LIMIT
    qty: Decimal
    limit_price: Decimal | None  # Required for LIMIT, STOP_LIMIT
    stop_price: Decimal | None  # Required for STOP, STOP_LIMIT
    time_in_force: TimeInForce  # DAY | GTC | IOC | FOK
    extended_hours: bool = False


@dataclass
class OrderState:
    """
    Full order state tracked by Veda.

    Combines the original intent with exchange response and fill status.
    Mutable to allow state transitions during order lifecycle.
    """

    # Identity
    id: str  # Veda's internal order ID
    client_order_id: str  # From intent (idempotency key)
    exchange_order_id: str | None  # Exchange's order ID (after submit)
    run_id: str

    # Order details (from intent)
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    time_in_force: TimeInForce

    # Status
    status: OrderStatus

    # Fill info
    filled_qty: Decimal
    filled_avg_price: Decimal | None

    # Timestamps
    created_at: datetime
    submitted_at: datetime | None
    filled_at: datetime | None  # When fully filled
    cancelled_at: datetime | None

    # Error handling
    reject_reason: str | None
    error_code: str | None

    # List field with default must come last
    fills: list[Fill] = field(default_factory=list)


@dataclass(frozen=True)
class Fill:
    """Individual fill record."""

    id: str
    order_id: str
    qty: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime


# =============================================================================
# Account Models
# =============================================================================


@dataclass(frozen=True)
class AccountInfo:
    """Account information from exchange."""

    account_id: str
    buying_power: Decimal
    cash: Decimal
    portfolio_value: Decimal
    currency: str
    status: str  # ACTIVE, INACTIVE, etc.


@dataclass(frozen=True)
class Position:
    """Current position for a symbol."""

    symbol: str
    qty: Decimal
    side: PositionSide
    avg_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal


# =============================================================================
# Market Data Models
# =============================================================================


@dataclass(frozen=True)
class Bar:
    """OHLCV bar (candle) data."""

    symbol: str
    timestamp: datetime  # Bar open time (UTC)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: int | None = None
    vwap: Decimal | None = None  # Volume-weighted average price


@dataclass(frozen=True)
class Quote:
    """Real-time quote data."""

    symbol: str
    timestamp: datetime
    bid_price: Decimal
    bid_size: Decimal
    ask_price: Decimal
    ask_size: Decimal


@dataclass(frozen=True)
class Trade:
    """Real-time trade data."""

    symbol: str
    timestamp: datetime
    price: Decimal
    size: Decimal
    exchange: str

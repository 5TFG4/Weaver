"""
Veda Interfaces

Abstract interfaces for exchange communication and result types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from src.veda.models import (
        AccountInfo,
        Bar,
        OrderIntent,
        OrderSide,
        OrderStatus,
        OrderType,
        Position,
        Quote,
        Trade,
    )

from src.veda.models import OrderSide, OrderStatus, OrderType


# =============================================================================
# Result Types
# =============================================================================


@dataclass(frozen=True)
class OrderSubmitResult:
    """Result of order submission to exchange."""

    success: bool
    exchange_order_id: str | None
    status: OrderStatus
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class ExchangeOrder:
    """Order as represented by the exchange."""

    exchange_order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Exchange Adapter Interface
# =============================================================================


class ExchangeAdapter(ABC):
    """
    Abstract interface for exchange communication.

    Implementations:
    - AlpacaAdapter: Real Alpaca API
    - MockExchangeAdapter: For testing
    """

    # =========================================================================
    # Order Management
    # =========================================================================

    @abstractmethod
    async def submit_order(self, intent: OrderIntent) -> OrderSubmitResult:
        """
        Submit order to exchange.

        Args:
            intent: Order intent from strategy

        Returns:
            OrderSubmitResult with exchange_order_id or error

        Raises:
            ExchangeConnectionError: If exchange unreachable
            RateLimitError: If rate limit exceeded
        """

    @abstractmethod
    async def cancel_order(self, exchange_order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            exchange_order_id: Exchange's order ID

        Returns:
            True if cancel request accepted, False if order not found
        """

    @abstractmethod
    async def get_order(self, exchange_order_id: str) -> ExchangeOrder | None:
        """
        Get current order status from exchange.

        Args:
            exchange_order_id: Exchange's order ID

        Returns:
            ExchangeOrder if found, None otherwise
        """

    @abstractmethod
    async def list_orders(
        self,
        status: OrderStatus | None = None,
        symbols: list[str] | None = None,
        limit: int = 100,
    ) -> list[ExchangeOrder]:
        """List orders from exchange."""

    # =========================================================================
    # Account & Positions
    # =========================================================================

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get account information."""

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all current positions."""

    @abstractmethod
    async def get_position(self, symbol: str) -> Position | None:
        """Get position for a specific symbol."""

    # =========================================================================
    # Market Data
    # =========================================================================

    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        """
        Get historical OHLCV bars.

        Args:
            symbol: Trading symbol (e.g., "BTC/USD")
            timeframe: Bar timeframe (e.g., "1m", "5m", "1h", "1d")
            start: Start datetime (UTC)
            end: End datetime (UTC), defaults to now
            limit: Max bars to return

        Returns:
            List of Bar objects, oldest first
        """

    @abstractmethod
    async def get_latest_bar(self, symbol: str) -> Bar | None:
        """Get the most recent bar for a symbol."""

    @abstractmethod
    async def get_latest_quote(self, symbol: str) -> Quote | None:
        """Get the most recent quote for a symbol."""

    @abstractmethod
    async def get_latest_trade(self, symbol: str) -> Trade | None:
        """Get the most recent trade for a symbol."""

    # =========================================================================
    # Streaming (Future)
    # =========================================================================

    @abstractmethod
    async def stream_bars(
        self,
        symbols: list[str],
    ) -> AsyncIterator[Bar]:
        """Stream real-time bars (future implementation)."""

    @abstractmethod
    async def stream_quotes(
        self,
        symbols: list[str],
    ) -> AsyncIterator[Quote]:
        """Stream real-time quotes (future implementation)."""

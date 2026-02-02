"""
Veda Exceptions

Exception hierarchy for Veda module errors.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.veda.models import OrderStatus


class VedaError(Exception):
    """Base exception for Veda module."""

    pass


class ExchangeConnectionError(VedaError):
    """Failed to connect to exchange."""

    pass


class RateLimitError(VedaError):
    """Exchange rate limit exceeded."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        self.retry_after = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Retry after {retry_after_seconds}s")


class OrderNotFoundError(VedaError):
    """Order not found."""

    def __init__(self, client_order_id: str) -> None:
        self.client_order_id = client_order_id
        super().__init__(f"Order not found: {client_order_id}")


class OrderNotCancellableError(VedaError):
    """Order cannot be cancelled (already in terminal state)."""

    def __init__(self, client_order_id: str, status: OrderStatus) -> None:
        self.client_order_id = client_order_id
        self.status = status
        super().__init__(
            f"Order {client_order_id} cannot be cancelled (status: {status.value})"
        )


class InsufficientFundsError(VedaError):
    """Insufficient funds for order."""

    def __init__(self, required: Decimal, available: Decimal) -> None:
        self.required = required
        self.available = available
        super().__init__(f"Insufficient funds: need {required}, have {available}")


class InvalidOrderError(VedaError):
    """Order validation failed."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Invalid order: {reason}")


class SymbolNotFoundError(VedaError):
    """Trading symbol not found."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Symbol not found: {symbol}")

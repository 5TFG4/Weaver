"""
Veda Exceptions Tests

TDD tests for Veda exception classes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.veda.exceptions import (
    ExchangeConnectionError,
    InsufficientFundsError,
    InvalidOrderError,
    OrderNotCancellableError,
    OrderNotFoundError,
    RateLimitError,
    SymbolNotFoundError,
    VedaError,
)
from src.veda.models import OrderStatus


class TestVedaError:
    """Tests for base VedaError."""

    def test_is_exception(self) -> None:
        """VedaError should be an Exception."""
        exc = VedaError("test error")
        assert isinstance(exc, Exception)

    def test_stores_message(self) -> None:
        """VedaError should store message."""
        exc = VedaError("test error message")
        assert str(exc) == "test error message"


class TestExchangeConnectionError:
    """Tests for ExchangeConnectionError."""

    def test_is_veda_error(self) -> None:
        """ExchangeConnectionError should be VedaError."""
        exc = ExchangeConnectionError("Connection failed")
        assert isinstance(exc, VedaError)

    def test_stores_message(self) -> None:
        """ExchangeConnectionError should store message."""
        exc = ExchangeConnectionError("Failed to connect to Alpaca")
        assert "Failed to connect to Alpaca" in str(exc)


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_is_veda_error(self) -> None:
        """RateLimitError should be VedaError."""
        exc = RateLimitError(retry_after_seconds=60)
        assert isinstance(exc, VedaError)

    def test_stores_retry_after(self) -> None:
        """RateLimitError should store retry_after."""
        exc = RateLimitError(retry_after_seconds=60)
        assert exc.retry_after == 60

    def test_retry_after_can_be_none(self) -> None:
        """RateLimitError should allow None retry_after."""
        exc = RateLimitError(retry_after_seconds=None)
        assert exc.retry_after is None

    def test_message_includes_retry(self) -> None:
        """RateLimitError message should include retry time."""
        exc = RateLimitError(retry_after_seconds=30)
        assert "30" in str(exc)


class TestOrderNotFoundError:
    """Tests for OrderNotFoundError."""

    def test_is_veda_error(self) -> None:
        """OrderNotFoundError should be VedaError."""
        exc = OrderNotFoundError("client-123")
        assert isinstance(exc, VedaError)

    def test_stores_client_order_id(self) -> None:
        """OrderNotFoundError should store client_order_id."""
        exc = OrderNotFoundError("client-123")
        assert exc.client_order_id == "client-123"

    def test_message_includes_id(self) -> None:
        """OrderNotFoundError message should include order ID."""
        exc = OrderNotFoundError("client-123")
        assert "client-123" in str(exc)


class TestOrderNotCancellableError:
    """Tests for OrderNotCancellableError."""

    def test_is_veda_error(self) -> None:
        """OrderNotCancellableError should be VedaError."""
        exc = OrderNotCancellableError("client-123", OrderStatus.FILLED)
        assert isinstance(exc, VedaError)

    def test_stores_client_order_id(self) -> None:
        """OrderNotCancellableError should store client_order_id."""
        exc = OrderNotCancellableError("client-123", OrderStatus.FILLED)
        assert exc.client_order_id == "client-123"

    def test_stores_status(self) -> None:
        """OrderNotCancellableError should store current status."""
        exc = OrderNotCancellableError("client-123", OrderStatus.FILLED)
        assert exc.status == OrderStatus.FILLED

    def test_message_includes_details(self) -> None:
        """OrderNotCancellableError message should include ID and status."""
        exc = OrderNotCancellableError("client-123", OrderStatus.CANCELLED)
        assert "client-123" in str(exc)
        assert "cancelled" in str(exc).lower()


class TestInsufficientFundsError:
    """Tests for InsufficientFundsError."""

    def test_is_veda_error(self) -> None:
        """InsufficientFundsError should be VedaError."""
        exc = InsufficientFundsError(
            required=Decimal("10000"),
            available=Decimal("5000"),
        )
        assert isinstance(exc, VedaError)

    def test_stores_required_amount(self) -> None:
        """InsufficientFundsError should store required amount."""
        exc = InsufficientFundsError(
            required=Decimal("10000"),
            available=Decimal("5000"),
        )
        assert exc.required == Decimal("10000")

    def test_stores_available_amount(self) -> None:
        """InsufficientFundsError should store available amount."""
        exc = InsufficientFundsError(
            required=Decimal("10000"),
            available=Decimal("5000"),
        )
        assert exc.available == Decimal("5000")

    def test_message_includes_amounts(self) -> None:
        """InsufficientFundsError message should include amounts."""
        exc = InsufficientFundsError(
            required=Decimal("10000"),
            available=Decimal("5000"),
        )
        assert "10000" in str(exc)
        assert "5000" in str(exc)


class TestInvalidOrderError:
    """Tests for InvalidOrderError."""

    def test_is_veda_error(self) -> None:
        """InvalidOrderError should be VedaError."""
        exc = InvalidOrderError("Missing limit price")
        assert isinstance(exc, VedaError)

    def test_stores_reason(self) -> None:
        """InvalidOrderError should store reason."""
        exc = InvalidOrderError("Missing limit price for limit order")
        assert exc.reason == "Missing limit price for limit order"

    def test_message_includes_reason(self) -> None:
        """InvalidOrderError message should include reason."""
        exc = InvalidOrderError("Quantity must be positive")
        assert "Quantity must be positive" in str(exc)


class TestSymbolNotFoundError:
    """Tests for SymbolNotFoundError."""

    def test_is_veda_error(self) -> None:
        """SymbolNotFoundError should be VedaError."""
        exc = SymbolNotFoundError("INVALID/USD")
        assert isinstance(exc, VedaError)

    def test_stores_symbol(self) -> None:
        """SymbolNotFoundError should store symbol."""
        exc = SymbolNotFoundError("INVALID/USD")
        assert exc.symbol == "INVALID/USD"

    def test_message_includes_symbol(self) -> None:
        """SymbolNotFoundError message should include symbol."""
        exc = SymbolNotFoundError("NOTREAL/USD")
        assert "NOTREAL/USD" in str(exc)

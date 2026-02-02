"""
Veda Interfaces Tests

TDD tests for Veda interface definitions.
"""

from __future__ import annotations

from abc import ABC
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.veda.interfaces import (
    ExchangeAdapter,
    ExchangeOrder,
    OrderSubmitResult,
)
from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)


class TestOrderSubmitResult:
    """Tests for OrderSubmitResult dataclass."""

    def test_success_result(self) -> None:
        """OrderSubmitResult for successful submission."""
        result = OrderSubmitResult(
            success=True,
            exchange_order_id="exch-123",
            status=OrderStatus.SUBMITTED,
            error_code=None,
            error_message=None,
        )
        assert result.success is True
        assert result.exchange_order_id == "exch-123"
        assert result.status == OrderStatus.SUBMITTED

    def test_failure_result(self) -> None:
        """OrderSubmitResult for failed submission."""
        result = OrderSubmitResult(
            success=False,
            exchange_order_id=None,
            status=OrderStatus.REJECTED,
            error_code="INSUFFICIENT_FUNDS",
            error_message="Not enough buying power",
        )
        assert result.success is False
        assert result.exchange_order_id is None
        assert result.error_code == "INSUFFICIENT_FUNDS"
        assert result.error_message == "Not enough buying power"

    def test_is_immutable(self) -> None:
        """OrderSubmitResult should be frozen."""
        from dataclasses import FrozenInstanceError

        result = OrderSubmitResult(
            success=True,
            exchange_order_id="exch-123",
            status=OrderStatus.SUBMITTED,
        )
        with pytest.raises(FrozenInstanceError):
            result.success = False  # type: ignore


class TestExchangeOrder:
    """Tests for ExchangeOrder dataclass."""

    def test_has_all_fields(self) -> None:
        """ExchangeOrder should have all required fields."""
        now = datetime.now(UTC)
        order = ExchangeOrder(
            exchange_order_id="exch-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            filled_qty=Decimal("1.0"),
            filled_avg_price=Decimal("42000.00"),
            status=OrderStatus.FILLED,
            created_at=now,
            updated_at=now,
        )
        assert order.exchange_order_id == "exch-123"
        assert order.client_order_id == "client-123"
        assert order.symbol == "BTC/USD"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.qty == Decimal("1.0")
        assert order.filled_qty == Decimal("1.0")
        assert order.filled_avg_price == Decimal("42000.00")
        assert order.status == OrderStatus.FILLED

    def test_filled_avg_price_can_be_none(self) -> None:
        """ExchangeOrder filled_avg_price can be None for unfilled orders."""
        now = datetime.now(UTC)
        order = ExchangeOrder(
            exchange_order_id="exch-456",
            client_order_id="client-456",
            symbol="ETH/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("2.0"),
            filled_qty=Decimal("0"),
            filled_avg_price=None,
            status=OrderStatus.ACCEPTED,
            created_at=now,
            updated_at=now,
        )
        assert order.filled_avg_price is None
        assert order.status == OrderStatus.ACCEPTED


class TestExchangeAdapterInterface:
    """Tests for ExchangeAdapter ABC."""

    def test_is_abstract_class(self) -> None:
        """ExchangeAdapter should be an ABC."""
        assert issubclass(ExchangeAdapter, ABC)

    def test_cannot_instantiate_directly(self) -> None:
        """ExchangeAdapter should not be directly instantiable."""
        with pytest.raises(TypeError):
            ExchangeAdapter()  # type: ignore

    def test_has_submit_order_method(self) -> None:
        """ExchangeAdapter should define submit_order."""
        assert hasattr(ExchangeAdapter, "submit_order")

    def test_has_cancel_order_method(self) -> None:
        """ExchangeAdapter should define cancel_order."""
        assert hasattr(ExchangeAdapter, "cancel_order")

    def test_has_get_order_method(self) -> None:
        """ExchangeAdapter should define get_order."""
        assert hasattr(ExchangeAdapter, "get_order")

    def test_has_list_orders_method(self) -> None:
        """ExchangeAdapter should define list_orders."""
        assert hasattr(ExchangeAdapter, "list_orders")

    def test_has_get_account_method(self) -> None:
        """ExchangeAdapter should define get_account."""
        assert hasattr(ExchangeAdapter, "get_account")

    def test_has_get_positions_method(self) -> None:
        """ExchangeAdapter should define get_positions."""
        assert hasattr(ExchangeAdapter, "get_positions")

    def test_has_get_position_method(self) -> None:
        """ExchangeAdapter should define get_position."""
        assert hasattr(ExchangeAdapter, "get_position")

    def test_has_get_bars_method(self) -> None:
        """ExchangeAdapter should define get_bars."""
        assert hasattr(ExchangeAdapter, "get_bars")

    def test_has_get_latest_bar_method(self) -> None:
        """ExchangeAdapter should define get_latest_bar."""
        assert hasattr(ExchangeAdapter, "get_latest_bar")

    def test_has_get_latest_quote_method(self) -> None:
        """ExchangeAdapter should define get_latest_quote."""
        assert hasattr(ExchangeAdapter, "get_latest_quote")

    def test_has_get_latest_trade_method(self) -> None:
        """ExchangeAdapter should define get_latest_trade."""
        assert hasattr(ExchangeAdapter, "get_latest_trade")


class ConcreteAdapter(ExchangeAdapter):
    """Concrete implementation for testing interface compliance."""

    async def submit_order(self, intent):
        return OrderSubmitResult(True, "test", OrderStatus.SUBMITTED)

    async def cancel_order(self, exchange_order_id):
        return True

    async def get_order(self, exchange_order_id):
        return None

    async def list_orders(self, status=None, symbols=None, limit=100):
        return []

    async def get_account(self):
        from src.veda.models import AccountInfo

        return AccountInfo("acc", Decimal("0"), Decimal("0"), Decimal("0"), "USD", "ACTIVE")

    async def get_positions(self):
        return []

    async def get_position(self, symbol):
        return None

    async def get_bars(self, symbol, timeframe, start, end=None, limit=None):
        return []

    async def get_latest_bar(self, symbol):
        return None

    async def get_latest_quote(self, symbol):
        return None

    async def get_latest_trade(self, symbol):
        return None

    async def stream_bars(self, symbols):
        yield  # Empty generator
        return

    async def stream_quotes(self, symbols):
        yield  # Empty generator
        return


class TestExchangeAdapterImplementation:
    """Tests that verify a concrete adapter can implement the interface."""

    def test_concrete_implementation_instantiates(self) -> None:
        """A concrete implementation should be instantiable."""
        adapter = ConcreteAdapter()
        assert adapter is not None

    @pytest.mark.asyncio
    async def test_concrete_submit_order_works(self) -> None:
        """A concrete implementation should have working submit_order."""
        adapter = ConcreteAdapter()
        intent = OrderIntent(
            run_id="run-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        result = await adapter.submit_order(intent)
        assert isinstance(result, OrderSubmitResult)

    @pytest.mark.asyncio
    async def test_concrete_get_account_works(self) -> None:
        """A concrete implementation should have working get_account."""
        from src.veda.models import AccountInfo

        adapter = ConcreteAdapter()
        account = await adapter.get_account()
        assert isinstance(account, AccountInfo)

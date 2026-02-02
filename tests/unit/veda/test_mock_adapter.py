"""
Mock Exchange Adapter Tests

TDD tests for MockExchangeAdapter - testing infrastructure for Veda.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.veda.adapters.mock_adapter import MockExchangeAdapter
from src.veda.interfaces import ExchangeAdapter, ExchangeOrder, OrderSubmitResult
from src.veda.models import (
    AccountInfo,
    Bar,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Quote,
    TimeInForce,
    Trade,
)


@pytest.fixture
def mock_adapter() -> MockExchangeAdapter:
    """Create fresh MockExchangeAdapter for testing."""
    return MockExchangeAdapter()


# =============================================================================
# Interface Compliance Tests
# =============================================================================


class TestMockAdapterInterface:
    """Tests that MockExchangeAdapter implements ExchangeAdapter."""

    def test_is_exchange_adapter(self, mock_adapter: MockExchangeAdapter) -> None:
        """MockExchangeAdapter should implement ExchangeAdapter."""
        assert isinstance(mock_adapter, ExchangeAdapter)


# =============================================================================
# Order Submission Tests
# =============================================================================


class TestMockAdapterSubmitOrder:
    """Tests for MockExchangeAdapter.submit_order()."""

    @pytest.mark.asyncio
    async def test_submit_market_order_returns_success(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Submit market order should return success result."""
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
        result = await mock_adapter.submit_order(intent)
        assert result.success is True
        assert result.exchange_order_id is not None
        assert len(result.exchange_order_id) > 0

    @pytest.mark.asyncio
    async def test_submit_order_generates_exchange_id(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Submit order should generate unique exchange order ID."""
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
        result = await mock_adapter.submit_order(intent)
        assert result.exchange_order_id is not None
        # Should be UUID format
        assert len(result.exchange_order_id) == 36

    @pytest.mark.asyncio
    async def test_submit_order_idempotent_by_client_order_id(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Same client_order_id should return same exchange_order_id."""
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
        result1 = await mock_adapter.submit_order(intent)
        result2 = await mock_adapter.submit_order(intent)
        # Same client_order_id should return same exchange_order_id
        assert result1.exchange_order_id == result2.exchange_order_id

    @pytest.mark.asyncio
    async def test_submit_different_orders_get_different_ids(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Different client_order_ids should get different exchange_order_ids."""
        intent1 = OrderIntent(
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
        intent2 = OrderIntent(
            run_id="run-123",
            client_order_id="client-456",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("2.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        result1 = await mock_adapter.submit_order(intent1)
        result2 = await mock_adapter.submit_order(intent2)
        assert result1.exchange_order_id != result2.exchange_order_id

    @pytest.mark.asyncio
    async def test_market_order_fills_immediately(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Market orders should fill immediately in mock."""
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
        result = await mock_adapter.submit_order(intent)
        # Check order status is filled
        assert result.exchange_order_id is not None
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_limit_order_stays_pending(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Limit orders should not auto-fill, stay accepted."""
        intent = OrderIntent(
            run_id="run-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("1.0"),
            limit_price=Decimal("30000.00"),  # Below typical mock price
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        result = await mock_adapter.submit_order(intent)
        assert result.exchange_order_id is not None
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.status == OrderStatus.ACCEPTED
        assert order.filled_qty == Decimal("0")

    @pytest.mark.asyncio
    async def test_submit_order_returns_correct_status(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Submit result should indicate correct status."""
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
        result = await mock_adapter.submit_order(intent)
        # Market order should be filled immediately
        assert result.status == OrderStatus.FILLED


# =============================================================================
# Order Query Tests
# =============================================================================


class TestMockAdapterGetOrder:
    """Tests for MockExchangeAdapter.get_order()."""

    @pytest.mark.asyncio
    async def test_get_order_returns_submitted_order(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_order should return previously submitted order."""
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
        result = await mock_adapter.submit_order(intent)
        assert result.exchange_order_id is not None
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.exchange_order_id == result.exchange_order_id
        assert order.client_order_id == "client-123"
        assert order.symbol == "BTC/USD"
        assert order.side == OrderSide.BUY

    @pytest.mark.asyncio
    async def test_get_order_returns_none_for_unknown(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_order should return None for unknown order ID."""
        order = await mock_adapter.get_order("non-existent-id")
        assert order is None

    @pytest.mark.asyncio
    async def test_get_order_has_timestamps(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Order should have created_at and updated_at timestamps."""
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
        result = await mock_adapter.submit_order(intent)
        assert result.exchange_order_id is not None
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.created_at is not None
        assert order.updated_at is not None


class TestMockAdapterListOrders:
    """Tests for MockExchangeAdapter.list_orders()."""

    @pytest.mark.asyncio
    async def test_list_orders_returns_all(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """list_orders should return all submitted orders."""
        for i in range(3):
            intent = OrderIntent(
                run_id="run-123",
                client_order_id=f"client-{i}",
                symbol="BTC/USD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=Decimal("1.0"),
                limit_price=None,
                stop_price=None,
                time_in_force=TimeInForce.GTC,
            )
            await mock_adapter.submit_order(intent)
        orders = await mock_adapter.list_orders()
        assert len(orders) == 3

    @pytest.mark.asyncio
    async def test_list_orders_empty_initially(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """list_orders should return empty list initially."""
        orders = await mock_adapter.list_orders()
        assert orders == []


# =============================================================================
# Cancel Order Tests
# =============================================================================


class TestMockAdapterCancelOrder:
    """Tests for MockExchangeAdapter.cancel_order()."""

    @pytest.mark.asyncio
    async def test_cancel_pending_order(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """cancel_order should work for accepted orders."""
        intent = OrderIntent(
            run_id="run-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=Decimal("1.0"),
            limit_price=Decimal("30000.00"),
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        result = await mock_adapter.submit_order(intent)
        assert result.exchange_order_id is not None
        cancelled = await mock_adapter.cancel_order(result.exchange_order_id)
        assert cancelled is True
        # Verify status changed
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_unknown_order_returns_false(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """cancel_order should return False for unknown order."""
        cancelled = await mock_adapter.cancel_order("non-existent-id")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_cancel_filled_order_returns_false(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """cancel_order should return False for filled orders."""
        intent = OrderIntent(
            run_id="run-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,  # Will fill immediately
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        result = await mock_adapter.submit_order(intent)
        assert result.exchange_order_id is not None
        # Order is already filled
        cancelled = await mock_adapter.cancel_order(result.exchange_order_id)
        assert cancelled is False


# =============================================================================
# Account Tests
# =============================================================================


class TestMockAdapterAccount:
    """Tests for MockExchangeAdapter account methods."""

    @pytest.mark.asyncio
    async def test_get_account_returns_mock_data(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_account should return mock account info."""
        account = await mock_adapter.get_account()
        assert isinstance(account, AccountInfo)
        assert account.buying_power > 0
        assert account.status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_get_positions_returns_list(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_positions should return positions list."""
        positions = await mock_adapter.get_positions()
        assert isinstance(positions, list)

    @pytest.mark.asyncio
    async def test_get_position_returns_none_for_no_position(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_position should return None when no position."""
        position = await mock_adapter.get_position("NONEXISTENT/USD")
        assert position is None


# =============================================================================
# Market Data Tests
# =============================================================================


class TestMockAdapterMarketData:
    """Tests for MockExchangeAdapter market data methods."""

    @pytest.mark.asyncio
    async def test_get_bars_returns_mock_data(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_bars should return mock OHLCV data."""
        bars = await mock_adapter.get_bars(
            symbol="BTC/USD",
            timeframe="1m",
            start=datetime.now(UTC) - timedelta(hours=1),
        )
        assert len(bars) > 0
        assert all(isinstance(b, Bar) for b in bars)

    @pytest.mark.asyncio
    async def test_get_bars_respects_limit(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_bars should respect limit parameter."""
        bars = await mock_adapter.get_bars(
            symbol="BTC/USD",
            timeframe="1m",
            start=datetime.now(UTC) - timedelta(hours=1),
            limit=5,
        )
        assert len(bars) <= 5

    @pytest.mark.asyncio
    async def test_get_bars_has_correct_symbol(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """Bars should have correct symbol."""
        bars = await mock_adapter.get_bars(
            symbol="ETH/USD",
            timeframe="1m",
            start=datetime.now(UTC) - timedelta(hours=1),
        )
        assert all(b.symbol == "ETH/USD" for b in bars)

    @pytest.mark.asyncio
    async def test_get_latest_bar_returns_bar(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_latest_bar should return a Bar."""
        bar = await mock_adapter.get_latest_bar("BTC/USD")
        assert bar is not None
        assert isinstance(bar, Bar)
        assert bar.symbol == "BTC/USD"

    @pytest.mark.asyncio
    async def test_get_latest_quote_returns_quote(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_latest_quote should return a Quote."""
        quote = await mock_adapter.get_latest_quote("BTC/USD")
        assert quote is not None
        assert isinstance(quote, Quote)
        assert quote.symbol == "BTC/USD"
        assert quote.bid_price > 0
        assert quote.ask_price > 0

    @pytest.mark.asyncio
    async def test_get_latest_trade_returns_trade(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_latest_trade should return a Trade."""
        trade = await mock_adapter.get_latest_trade("BTC/USD")
        assert trade is not None
        assert isinstance(trade, Trade)
        assert trade.symbol == "BTC/USD"
        assert trade.price > 0


# =============================================================================
# Mock Configuration Tests
# =============================================================================


class TestMockAdapterConfiguration:
    """Tests for MockExchangeAdapter configuration."""

    @pytest.mark.asyncio
    async def test_set_mock_price(self, mock_adapter: MockExchangeAdapter) -> None:
        """Should be able to set mock price for a symbol."""
        mock_adapter.set_mock_price("BTC/USD", Decimal("50000.00"))
        bar = await mock_adapter.get_latest_bar("BTC/USD")
        assert bar is not None
        # Close price should be around the mock price
        assert bar.close == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_simulate_rejection(self, mock_adapter: MockExchangeAdapter) -> None:
        """Should be able to configure rejections."""
        mock_adapter.set_reject_next_order(True, reason="Insufficient funds")
        intent = OrderIntent(
            run_id="run-123",
            client_order_id="client-reject",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        result = await mock_adapter.submit_order(intent)
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        assert result.error_message == "Insufficient funds"

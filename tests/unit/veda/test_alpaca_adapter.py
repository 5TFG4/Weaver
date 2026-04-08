"""
Unit tests for AlpacaAdapter

MVP-6: AlpacaAdapter (Paper Trading)
- Implements ExchangeAdapter for Alpaca
- Paper trading support
- Proper error handling
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch
from uuid import uuid4

import pytest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest

from src.veda.adapters.alpaca_adapter import AlpacaAdapter
from src.veda.interfaces import TradeActivity
from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)

# ============================================================================
# Test: AlpacaAdapter Interface
# ============================================================================


class TestAlpacaAdapterInterface:
    """Test that AlpacaAdapter implements ExchangeAdapter."""

    def test_alpaca_adapter_exists(self) -> None:
        """AlpacaAdapter class exists."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        assert AlpacaAdapter is not None

    def test_alpaca_adapter_is_exchange_adapter(self) -> None:
        """AlpacaAdapter implements ExchangeAdapter."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.interfaces import ExchangeAdapter

        assert issubclass(AlpacaAdapter, ExchangeAdapter)

    def test_alpaca_adapter_accepts_credentials(self) -> None:
        """AlpacaAdapter accepts API credentials."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        # Should not raise with valid credentials
        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        assert adapter is not None

    def test_alpaca_adapter_has_paper_mode(self) -> None:
        """AlpacaAdapter supports paper trading mode."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        assert adapter.paper is True


# ============================================================================
# Test: Order Submission
# ============================================================================


class TestAlpacaAdapterSubmitOrder:
    """Test order submission through Alpaca."""

    @pytest.fixture
    def sample_intent(self) -> OrderIntent:
        """Create sample order intent."""
        return OrderIntent(
            run_id="test-run-001",
            client_order_id=str(uuid4()),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("10"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.DAY,
        )

    @pytest.fixture
    def mock_alpaca_client(self) -> MagicMock:
        """Create mock Alpaca trading client."""
        mock = create_autospec(TradingClient, instance=True)
        # Mock order response
        mock_order = MagicMock()
        mock_order.id = "alpaca-order-123"
        mock_order.client_order_id = "client-123"
        mock_order.status = "accepted"
        mock_order.filled_qty = "0"
        mock_order.filled_avg_price = None
        mock_order.created_at = datetime.now(UTC)
        mock_order.updated_at = datetime.now(UTC)
        mock_order.symbol = "AAPL"
        mock_order.side = "buy"
        mock_order.type = "market"
        mock_order.qty = "10"
        mock.submit_order.return_value = mock_order
        return mock

    async def test_submit_order_calls_alpaca_api(
        self, sample_intent: OrderIntent, mock_alpaca_client: MagicMock
    ) -> None:
        """submit_order calls Alpaca API."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        await adapter.submit_order(sample_intent)

        mock_alpaca_client.submit_order.assert_called_once()
        # Verify OrderRequest object was passed (not kwargs)
        order_request = mock_alpaca_client.submit_order.call_args[0][0]
        assert isinstance(order_request, MarketOrderRequest)
        assert order_request.symbol == "AAPL"
        assert order_request.qty == 10.0

    async def test_submit_order_returns_result(
        self, sample_intent: OrderIntent, mock_alpaca_client: MagicMock
    ) -> None:
        """submit_order returns OrderSubmitResult."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.interfaces import OrderSubmitResult

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        result = await adapter.submit_order(sample_intent)

        assert isinstance(result, OrderSubmitResult)
        assert result.exchange_order_id == "alpaca-order-123"

    async def test_submit_order_maps_symbol_correctly(
        self, sample_intent: OrderIntent, mock_alpaca_client: MagicMock
    ) -> None:
        """submit_order uses correct symbol format."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        await adapter.submit_order(sample_intent)

        # Verify symbol mapping in OrderRequest
        call_args = mock_alpaca_client.submit_order.call_args
        order_request = call_args[0][0]
        assert isinstance(order_request, MarketOrderRequest)
        assert order_request.symbol == sample_intent.symbol


# ============================================================================
# Test: Order Management
# ============================================================================


class TestAlpacaAdapterOrderManagement:
    """Test order management operations."""

    @pytest.fixture
    def mock_alpaca_client(self) -> MagicMock:
        """Create mock Alpaca trading client."""
        mock = create_autospec(TradingClient, instance=True)

        # Mock get_order response
        mock_order = MagicMock()
        mock_order.id = "alpaca-order-123"
        mock_order.client_order_id = "client-123"
        mock_order.status = "filled"
        mock_order.filled_qty = "10"
        mock_order.filled_avg_price = "150.25"
        mock_order.created_at = datetime.now(UTC)
        mock_order.updated_at = datetime.now(UTC)
        mock_order.symbol = "AAPL"
        mock_order.side = "buy"
        mock_order.type = "market"
        mock_order.qty = "10"
        mock.get_order_by_id.return_value = mock_order
        mock.cancel_order_by_id.return_value = None
        mock.get_orders.return_value = [mock_order]

        return mock

    async def test_get_order_returns_exchange_order(self, mock_alpaca_client: MagicMock) -> None:
        """get_order returns ExchangeOrder."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.interfaces import ExchangeOrder

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        result = await adapter.get_order("alpaca-order-123")

        assert result is not None
        assert isinstance(result, ExchangeOrder)
        assert result.exchange_order_id == "alpaca-order-123"

    async def test_cancel_order_calls_alpaca(self, mock_alpaca_client: MagicMock) -> None:
        """cancel_order calls Alpaca cancel API."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        result = await adapter.cancel_order("alpaca-order-123")

        assert result is True
        mock_alpaca_client.cancel_order_by_id.assert_called_once_with("alpaca-order-123")

    async def test_list_orders_returns_list(self, mock_alpaca_client: MagicMock) -> None:
        """list_orders returns list of ExchangeOrder."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.interfaces import ExchangeOrder

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        result = await adapter.list_orders()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ExchangeOrder)
        # Verify GetOrdersRequest was used (not kwargs)
        filter_arg = mock_alpaca_client.get_orders.call_args[1]["filter"]
        assert isinstance(filter_arg, GetOrdersRequest)


# ============================================================================
# Test: Account & Positions
# ============================================================================


class TestAlpacaAdapterAccount:
    """Test account and position operations."""

    @pytest.fixture
    def mock_alpaca_client(self) -> MagicMock:
        """Create mock Alpaca trading client."""
        mock = create_autospec(TradingClient, instance=True)

        # Mock account
        mock_account = MagicMock()
        mock_account.id = "account-123"
        mock_account.buying_power = "100000.00"
        mock_account.cash = "50000.00"
        mock_account.portfolio_value = "150000.00"
        mock_account.currency = "USD"
        mock_account.status = "ACTIVE"
        mock.get_account.return_value = mock_account

        # Mock positions
        mock_position = MagicMock()
        mock_position.symbol = "AAPL"
        mock_position.qty = "100"
        mock_position.side = "long"
        mock_position.avg_entry_price = "150.00"
        mock_position.market_value = "15500.00"
        mock_position.unrealized_pl = "500.00"
        mock_position.unrealized_plpc = "0.0333"
        mock.get_all_positions.return_value = [mock_position]
        mock.get_open_position.return_value = mock_position

        return mock

    async def test_get_account_returns_account_info(self, mock_alpaca_client: MagicMock) -> None:
        """get_account returns AccountInfo."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.models import AccountInfo

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        result = await adapter.get_account()

        assert isinstance(result, AccountInfo)
        assert result.buying_power == Decimal("100000.00")

    async def test_get_positions_returns_list(self, mock_alpaca_client: MagicMock) -> None:
        """get_positions returns list of Position."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.models import Position

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client
        adapter._connected = True  # Simulate connected state

        result = await adapter.get_positions()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Position)
        assert result[0].symbol == "AAPL"

    async def test_get_position_returns_position(self, mock_alpaca_client: MagicMock) -> None:
        """get_position returns Position for symbol."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.models import Position

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._trading_client = mock_alpaca_client

        result = await adapter.get_position("AAPL")

        assert result is not None
        assert isinstance(result, Position)


# ============================================================================
# Test: Market Data
# ============================================================================


class TestAlpacaAdapterMarketData:
    """Test market data operations."""

    @pytest.fixture
    def mock_data_client(self) -> MagicMock:
        """Create mock Alpaca data client."""
        mock = MagicMock()

        # Mock bars
        mock_bar = MagicMock()
        mock_bar.symbol = "AAPL"
        mock_bar.timestamp = datetime.now(UTC)
        mock_bar.open = 150.0
        mock_bar.high = 152.0
        mock_bar.low = 149.0
        mock_bar.close = 151.0
        mock_bar.volume = 1000000
        mock_bar.trade_count = 5000
        mock_bar.vwap = 150.5
        mock.get_stock_bars = MagicMock(return_value={"AAPL": [mock_bar]})
        mock.get_stock_latest_bar = MagicMock(return_value={"AAPL": mock_bar})

        # Mock quote
        mock_quote = MagicMock()
        mock_quote.symbol = "AAPL"
        mock_quote.timestamp = datetime.now(UTC)
        mock_quote.bid_price = 150.95
        mock_quote.bid_size = 100
        mock_quote.ask_price = 151.05
        mock_quote.ask_size = 200
        mock.get_stock_latest_quote = MagicMock(return_value={"AAPL": mock_quote})

        # Mock trade
        mock_trade = MagicMock()
        mock_trade.symbol = "AAPL"
        mock_trade.timestamp = datetime.now(UTC)
        mock_trade.price = 151.00
        mock_trade.size = 100
        mock_trade.exchange = "NASDAQ"
        mock.get_stock_latest_trade = MagicMock(return_value={"AAPL": mock_trade})

        return mock

    async def test_get_bars_returns_list(self, mock_data_client: MagicMock) -> None:
        """get_bars returns list of Bar."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.models import Bar

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._stock_data_client = mock_data_client

        start = datetime.now(UTC) - timedelta(days=1)
        result = await adapter.get_bars("AAPL", "1h", start)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert isinstance(result[0], Bar)

    async def test_get_latest_bar_returns_bar(self, mock_data_client: MagicMock) -> None:
        """get_latest_bar returns Bar."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.models import Bar

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._stock_data_client = mock_data_client

        result = await adapter.get_latest_bar("AAPL")

        assert result is not None
        assert isinstance(result, Bar)

    async def test_get_latest_quote_returns_quote(self, mock_data_client: MagicMock) -> None:
        """get_latest_quote returns Quote."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.models import Quote

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._stock_data_client = mock_data_client

        result = await adapter.get_latest_quote("AAPL")

        assert result is not None
        assert isinstance(result, Quote)

    async def test_get_latest_trade_returns_trade(self, mock_data_client: MagicMock) -> None:
        """get_latest_trade returns Trade."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter
        from src.veda.models import Trade

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        adapter._stock_data_client = mock_data_client

        result = await adapter.get_latest_trade("AAPL")

        assert result is not None
        assert isinstance(result, Trade)


# ============================================================================
# Test: Error Handling
# ============================================================================


class TestAlpacaAdapterErrorHandling:
    """Test error handling for Alpaca operations."""

    def test_adapter_raises_on_missing_credentials(self) -> None:
        """Adapter raises if credentials missing."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        with pytest.raises((ValueError, TypeError)):
            AlpacaAdapter(api_key="", api_secret="", paper=True)

    async def test_submit_order_handles_rejection(self) -> None:
        """submit_order handles order rejection gracefully."""
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )

        # Mock rejection
        mock_client = create_autospec(TradingClient, instance=True)
        mock_client.submit_order.side_effect = Exception("Insufficient buying power")
        adapter._trading_client = mock_client
        adapter._connected = True  # Simulate connected state

        intent = OrderIntent(
            run_id="test-run",
            client_order_id=str(uuid4()),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1000000"),  # Large qty
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.DAY,
        )

        result = await adapter.submit_order(intent)

        assert result.success is False
        assert result.status == OrderStatus.REJECTED


# ============================================================================
# Test: Async Thread Wrapping (N-04)
# ============================================================================


class TestAlpacaAdapterAsyncWrapping:
    """Sync Alpaca SDK calls must run in asyncio.to_thread to avoid blocking."""

    @pytest.fixture
    def adapter(self) -> AlpacaAdapter:
        from src.veda.adapters.alpaca_adapter import AlpacaAdapter

        a = AlpacaAdapter(api_key="k", api_secret="s", paper=True)
        a._connected = True
        return a

    async def test_submit_order_runs_in_thread_pool(self, adapter) -> None:
        """submit_order delegates the sync SDK call to asyncio.to_thread."""

        mock_response = MagicMock()
        mock_response.id = "order-1"
        mock_response.status = "accepted"
        mock_client = create_autospec(TradingClient, instance=True)
        mock_client.submit_order.return_value = mock_response
        adapter._trading_client = mock_client

        intent = OrderIntent(
            run_id="run-1",
            client_order_id="cid-1",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.DAY,
        )

        with patch(
            "src.veda.adapters.alpaca_adapter.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = mock_response
            await adapter.submit_order(intent)
            mock_to_thread.assert_called_once()
            # First positional arg must be the SDK method
            assert mock_to_thread.call_args[0][0] is mock_client.submit_order
            # Second positional arg must be an OrderRequest object
            order_request = mock_to_thread.call_args[0][1]
            assert isinstance(order_request, MarketOrderRequest)

    async def test_get_account_runs_in_thread_pool(self, adapter) -> None:
        """get_account delegates the sync SDK call to asyncio.to_thread."""
        mock_response = MagicMock()
        mock_response.id = "acct-1"
        mock_response.buying_power = "100000"
        mock_response.cash = "50000"
        mock_response.portfolio_value = "150000"
        mock_response.currency = "USD"
        mock_response.status = "ACTIVE"
        mock_client = create_autospec(TradingClient, instance=True)
        mock_client.get_account.return_value = mock_response
        adapter._trading_client = mock_client

        with patch(
            "src.veda.adapters.alpaca_adapter.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_to_thread:
            mock_to_thread.return_value = mock_response
            await adapter.get_account()
            mock_to_thread.assert_called_once()
            assert mock_to_thread.call_args[0][0] is mock_client.get_account


# ============================================================================
# Test: Trade Activities (M14)
# ============================================================================


class TestAlpacaAdapterTradeActivities:
    """Account activity polling should map Alpaca fills into domain objects."""

    async def test_list_trade_activities_maps_partial_fill_payload(self) -> None:
        """A partial fill payload should map to TradeActivity correctly."""
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = [
            {
                "id": "20220304135420898::2b9e8979-48b4-4b70-9ba0-008210b76ebf",
                "account_id": "3dcb795c-3ccc-402a-abb9-07e26a1b1326",
                "activity_type": "FILL",
                "transaction_time": "2022-03-04T18:54:20.903569Z",
                "type": "partial_fill",
                "price": "2907.15",
                "qty": "1.792161878",
                "side": "buy",
                "symbol": "AMZN",
                "leaves_qty": "1",
                "order_id": "cddf433b-1a41-497d-ae31-50b1fee56fff",
                "cum_qty": "1.792161878",
                "order_status": "partially_filled",
            }
        ]

        http_client = AsyncMock()
        http_client.get = AsyncMock(return_value=response)
        async_client_cm = AsyncMock()
        async_client_cm.__aenter__.return_value = http_client

        adapter = AlpacaAdapter(api_key="test-key", api_secret="test-secret", paper=True)
        adapter._connected = True

        after = datetime(2022, 3, 4, 18, 54, 20, tzinfo=UTC)
        with patch(
            "src.veda.adapters.alpaca_adapter.httpx.AsyncClient", return_value=async_client_cm
        ):
            activities = await adapter.list_trade_activities(after=after)

        assert len(activities) == 1
        activity = activities[0]
        assert isinstance(activity, TradeActivity)
        assert activity.activity_id == "20220304135420898::2b9e8979-48b4-4b70-9ba0-008210b76ebf"
        assert activity.order_id == "cddf433b-1a41-497d-ae31-50b1fee56fff"
        assert activity.symbol == "AMZN"
        assert activity.activity_type == "partial_fill"
        assert activity.order_status == OrderStatus.PARTIALLY_FILLED
        assert activity.qty == Decimal("1.792161878")
        assert activity.leaves_qty == Decimal("1")
        assert activity.cum_qty == Decimal("1.792161878")

    async def test_list_trade_activities_uses_page_token_for_pagination(self) -> None:
        """The adapter should keep paging until Alpaca returns an empty page."""
        first_response = MagicMock()
        first_response.raise_for_status = MagicMock()
        first_response.json.return_value = [
            {
                "id": "20220304123922310::b53b6d71-a644-4be1-9f88-39d1c8d29831",
                "account_id": "3dcb795c-3ccc-402a-abb9-07e26a1b1326",
                "activity_type": "FILL",
                "transaction_time": "2022-03-04T17:39:22.310917Z",
                "type": "partial_fill",
                "price": "837.45",
                "qty": "1.998065556",
                "side": "sell",
                "symbol": "TSLA",
                "leaves_qty": "4",
                "order_id": "5f4a07dc-6503-4cbf-902a-8c6608401d97",
                "cum_qty": "1.998065556",
                "order_status": "partially_filled",
            }
        ]
        second_response = MagicMock()
        second_response.raise_for_status = MagicMock()
        second_response.json.return_value = [
            {
                "id": "20220304123922305::bc84b8a8-8758-42aa-be3b-618d097c2867",
                "account_id": "3dcb795c-3ccc-402a-abb9-07e26a1b1326",
                "activity_type": "FILL",
                "transaction_time": "2022-03-04T17:39:22.305629Z",
                "type": "fill",
                "price": "837.45",
                "qty": "4",
                "side": "sell",
                "symbol": "TSLA",
                "leaves_qty": "0",
                "order_id": "5f4a07dc-6503-4cbf-902a-8c6608401d97",
                "cum_qty": "5.998065556",
                "order_status": "filled",
            }
        ]
        final_response = MagicMock()
        final_response.raise_for_status = MagicMock()
        final_response.json.return_value = []

        http_client = AsyncMock()
        http_client.get = AsyncMock(side_effect=[first_response, second_response, final_response])
        async_client_cm = AsyncMock()
        async_client_cm.__aenter__.return_value = http_client

        adapter = AlpacaAdapter(api_key="test-key", api_secret="test-secret", paper=True)
        adapter._connected = True

        after = datetime(2022, 3, 4, 17, 39, 22, tzinfo=UTC)
        with patch(
            "src.veda.adapters.alpaca_adapter.httpx.AsyncClient", return_value=async_client_cm
        ):
            activities = await adapter.list_trade_activities(after=after, page_size=1)

        assert [activity.activity_type for activity in activities] == ["partial_fill", "fill"]
        assert activities[-1].order_status == OrderStatus.FILLED
        assert http_client.get.await_count == 3
        second_call_params = http_client.get.await_args_list[1].kwargs["params"]
        assert (
            second_call_params["page_token"]
            == "20220304123922310::b53b6d71-a644-4be1-9f88-39d1c8d29831"
        )

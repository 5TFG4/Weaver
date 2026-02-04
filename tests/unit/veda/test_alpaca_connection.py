"""
Tests for AlpacaAdapter Connection

TDD tests for M6-2: connect(), disconnect(), is_connected, _require_connection().
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.veda.adapters.alpaca_adapter import AlpacaAdapter
from src.veda.models import OrderIntent, OrderSide, OrderType, TimeInForce


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def adapter() -> AlpacaAdapter:
    """Create AlpacaAdapter with test credentials."""
    return AlpacaAdapter(
        api_key="test-api-key",
        api_secret="test-api-secret",
        paper=True,
    )


@pytest.fixture
def mock_trading_client() -> MagicMock:
    """Create mock TradingClient."""
    client = MagicMock()
    # Mock account with ACTIVE status
    account = MagicMock()
    account.status = "ACTIVE"
    client.get_account = MagicMock(return_value=account)
    return client


@pytest.fixture
def mock_stock_data_client() -> MagicMock:
    """Create mock StockHistoricalDataClient."""
    return MagicMock()


@pytest.fixture
def mock_crypto_data_client() -> MagicMock:
    """Create mock CryptoHistoricalDataClient."""
    return MagicMock()


# =============================================================================
# Connection State Tests
# =============================================================================


class TestConnectionState:
    """Tests for connection state management."""

    def test_is_connected_false_initially(self, adapter: AlpacaAdapter) -> None:
        """Adapter should not be connected after initialization."""
        assert adapter.is_connected is False

    def test_has_connect_method(self, adapter: AlpacaAdapter) -> None:
        """Adapter should have connect() method."""
        assert hasattr(adapter, "connect")
        assert callable(adapter.connect)

    def test_has_disconnect_method(self, adapter: AlpacaAdapter) -> None:
        """Adapter should have disconnect() method."""
        assert hasattr(adapter, "disconnect")
        assert callable(adapter.disconnect)

    def test_has_is_connected_property(self, adapter: AlpacaAdapter) -> None:
        """Adapter should have is_connected property."""
        assert hasattr(adapter, "is_connected")


# =============================================================================
# Connect Tests
# =============================================================================


class TestConnect:
    """Tests for connect() method."""

    def test_connect_creates_trading_client(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should create TradingClient."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()

            mock_trading.assert_called_once()
            assert adapter._trading_client is not None

    def test_connect_creates_stock_data_client(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should create StockHistoricalDataClient."""
        with (
            patch(
                "src.veda.adapters.alpaca_adapter.TradingClient"
            ) as mock_trading,
            patch(
                "src.veda.adapters.alpaca_adapter.StockHistoricalDataClient"
            ) as mock_stock,
        ):
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()

            mock_stock.assert_called_once()
            assert adapter._stock_data_client is not None

    def test_connect_creates_crypto_data_client(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should create CryptoHistoricalDataClient."""
        with (
            patch(
                "src.veda.adapters.alpaca_adapter.TradingClient"
            ) as mock_trading,
            patch(
                "src.veda.adapters.alpaca_adapter.CryptoHistoricalDataClient"
            ) as mock_crypto,
        ):
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()

            mock_crypto.assert_called_once()
            assert adapter._crypto_data_client is not None

    def test_connect_verifies_account_active(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should verify account status is ACTIVE."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()

            mock_client.get_account.assert_called_once()

    def test_connect_raises_on_inactive_account(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should raise ConnectionError if account not ACTIVE."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACCOUNT_BLOCKED"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            with pytest.raises(ConnectionError) as exc:
                adapter.connect()

            assert "ACCOUNT_BLOCKED" in str(exc.value)

    def test_connect_sets_is_connected_true(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should set is_connected to True."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()

            assert adapter.is_connected is True

    def test_connect_idempotent(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should be idempotent (no error if already connected)."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()
            adapter.connect()  # Should not raise

            # Should only create client once
            assert mock_trading.call_count == 1

    def test_connect_passes_paper_mode(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """connect() should pass paper=True to TradingClient."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()

            call_kwargs = mock_trading.call_args[1]
            assert call_kwargs.get("paper") is True

    def test_connect_live_mode_passes_paper_false(self) -> None:
        """connect() should pass paper=False for live adapter."""
        adapter = AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=False,
        )
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()

            call_kwargs = mock_trading.call_args[1]
            assert call_kwargs.get("paper") is False


# =============================================================================
# Disconnect Tests
# =============================================================================


class TestDisconnect:
    """Tests for disconnect() method."""

    def test_disconnect_clears_trading_client(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """disconnect() should clear _trading_client."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()
            assert adapter._trading_client is not None

            adapter.disconnect()
            assert adapter._trading_client is None

    def test_disconnect_clears_data_clients(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """disconnect() should clear data clients."""
        with (
            patch(
                "src.veda.adapters.alpaca_adapter.TradingClient"
            ) as mock_trading,
            patch(
                "src.veda.adapters.alpaca_adapter.StockHistoricalDataClient"
            ),
            patch(
                "src.veda.adapters.alpaca_adapter.CryptoHistoricalDataClient"
            ),
        ):
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()
            adapter.disconnect()

            assert adapter._stock_data_client is None
            assert adapter._crypto_data_client is None

    def test_disconnect_sets_is_connected_false(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """disconnect() should set is_connected to False."""
        with patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        ) as mock_trading:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = "ACTIVE"
            mock_client.get_account.return_value = mock_account
            mock_trading.return_value = mock_client

            adapter.connect()
            assert adapter.is_connected is True

            adapter.disconnect()
            assert adapter.is_connected is False

    def test_disconnect_idempotent(self, adapter: AlpacaAdapter) -> None:
        """disconnect() should be safe to call when not connected."""
        adapter.disconnect()  # Should not raise
        assert adapter.is_connected is False


# =============================================================================
# Require Connection Guard Tests
# =============================================================================


class TestRequireConnection:
    """Tests for _require_connection() guard."""

    @pytest.mark.asyncio
    async def test_submit_order_requires_connection(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """submit_order should raise if not connected."""
        intent = OrderIntent(
            run_id="test-run",
            client_order_id="test-order-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1.0"),
            order_type=OrderType.MARKET,
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )

        with pytest.raises(ConnectionError) as exc:
            await adapter.submit_order(intent)

        assert "not connected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_get_order_requires_connection(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """get_order should raise if not connected."""
        with pytest.raises(ConnectionError) as exc:
            await adapter.get_order("some-order-id")

        assert "not connected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_cancel_order_requires_connection(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """cancel_order should raise if not connected."""
        with pytest.raises(ConnectionError) as exc:
            await adapter.cancel_order("some-order-id")

        assert "not connected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_list_orders_requires_connection(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """list_orders should raise if not connected."""
        with pytest.raises(ConnectionError) as exc:
            await adapter.list_orders()

        assert "not connected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_get_account_requires_connection(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """get_account should raise if not connected."""
        with pytest.raises(ConnectionError) as exc:
            await adapter.get_account()

        assert "not connected" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_get_positions_requires_connection(
        self,
        adapter: AlpacaAdapter,
    ) -> None:
        """get_positions should raise if not connected."""
        with pytest.raises(ConnectionError) as exc:
            await adapter.get_positions()

        assert "not connected" in str(exc.value).lower()

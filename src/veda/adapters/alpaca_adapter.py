"""
Alpaca Exchange Adapter

Implementation of ExchangeAdapter for Alpaca Markets.
Supports both paper and live trading.
"""

from __future__ import annotations

ADAPTER_META = {
    "id": "alpaca",
    "name": "Alpaca Markets",
    "version": "1.0.0",
    "description": "Alpaca Markets exchange adapter for paper and live trading",
    "author": "Weaver Team",
    "class": "AlpacaAdapter",
    "features": ["paper_trading", "live_trading", "crypto", "stocks"],
}

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, AsyncIterator

# Alpaca SDK imports (lazy imported in connect())
try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import (
        CryptoHistoricalDataClient,
        StockHistoricalDataClient,
    )
except ImportError:
    # SDK not installed - will fail at connect() time
    TradingClient = None  # type: ignore
    CryptoHistoricalDataClient = None  # type: ignore
    StockHistoricalDataClient = None  # type: ignore

from src.veda.interfaces import ExchangeAdapter, ExchangeOrder, OrderSubmitResult
from src.veda.models import (
    AccountInfo,
    Bar,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    Quote,
    TimeInForce,
    Trade,
)


class AlpacaAdapter(ExchangeAdapter):
    """
    Alpaca Markets exchange adapter.

    Implements ExchangeAdapter for Alpaca's trading and data APIs.
    Supports paper trading mode for testing.
    """

    # Paper trading base URLs
    PAPER_TRADING_URL = "https://paper-api.alpaca.markets"
    PAPER_DATA_URL = "https://data.alpaca.markets"

    # Live trading base URLs
    LIVE_TRADING_URL = "https://api.alpaca.markets"
    LIVE_DATA_URL = "https://data.alpaca.markets"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        paper: bool = True,
    ) -> None:
        """
        Initialize Alpaca adapter.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            paper: Whether to use paper trading (default True)

        Raises:
            ValueError: If credentials are empty
        """
        if not api_key or not api_secret:
            raise ValueError("API key and secret are required")

        self._api_key = api_key
        self._api_secret = api_secret
        self._paper = paper

        # Initialize clients (lazy - created on connect())
        self._trading_client: Any = None
        self._stock_data_client: Any = None
        self._crypto_data_client: Any = None
        self._connected: bool = False

    @property
    def paper(self) -> bool:
        """Whether adapter is in paper trading mode."""
        return self._paper

    @property
    def is_connected(self) -> bool:
        """Whether adapter is connected to Alpaca."""
        return self._connected

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def connect(self) -> None:
        """
        Connect to Alpaca APIs.

        Initializes trading client and data clients, then verifies
        connection by checking account status.

        Raises:
            ConnectionError: If account status is not ACTIVE
            ImportError: If alpaca-py SDK is not installed
        """
        if self._connected:
            return  # Already connected (idempotent)

        if TradingClient is None:
            raise ImportError(
                "alpaca-py SDK is not installed. "
                "Install with: pip install alpaca-py"
            )

        # Verify all SDK classes are available (they're imported together,
        # but explicit check is safer than assert which can be disabled with -O)
        if StockHistoricalDataClient is None or CryptoHistoricalDataClient is None:
            raise ImportError(
                "alpaca-py SDK is incomplete. "
                "Reinstall with: pip install --force-reinstall alpaca-py"
            )

        # Create trading client
        self._trading_client = TradingClient(
            api_key=self._api_key,
            secret_key=self._api_secret,
            paper=self._paper,
        )

        # Create data clients (SDK availability already verified above)
        self._stock_data_client = StockHistoricalDataClient(
            api_key=self._api_key,
            secret_key=self._api_secret,
        )
        self._crypto_data_client = CryptoHistoricalDataClient(
            api_key=self._api_key,
            secret_key=self._api_secret,
        )

        # Verify connection by checking account status
        account = self._trading_client.get_account()
        if account.status != "ACTIVE":
            # Clean up on failure
            self._trading_client = None
            self._stock_data_client = None
            self._crypto_data_client = None
            raise ConnectionError(
                f"Account status is {account.status}, expected ACTIVE"
            )

        self._connected = True

    async def disconnect(self) -> None:
        """
        Disconnect from Alpaca APIs.

        Clears all clients and resets connection state.
        Safe to call even if not connected (idempotent).
        """
        self._trading_client = None
        self._stock_data_client = None
        self._crypto_data_client = None
        self._connected = False

    def _require_connection(self) -> None:
        """
        Guard that raises if not connected.

        Raises:
            ConnectionError: If adapter is not connected
        """
        if not self._connected:
            raise ConnectionError(
                "Adapter is not connected. Call connect() first."
            )

    # =========================================================================
    # Order Management
    # =========================================================================

    async def submit_order(self, intent: OrderIntent) -> OrderSubmitResult:
        """
        Submit order to Alpaca.

        Args:
            intent: The order intent

        Returns:
            OrderSubmitResult with exchange response

        Raises:
            ConnectionError: If adapter is not connected
        """
        self._require_connection()
        try:
            # Map order parameters
            side = "buy" if intent.side == OrderSide.BUY else "sell"
            order_type = self._map_order_type(intent.order_type)
            time_in_force = self._map_time_in_force(intent.time_in_force)

            # Build order request
            order_params: dict[str, Any] = {
                "symbol": intent.symbol,
                "qty": str(intent.qty),
                "side": side,
                "type": order_type,
                "time_in_force": time_in_force,
                "client_order_id": intent.client_order_id,
            }

            if intent.limit_price is not None:
                order_params["limit_price"] = str(intent.limit_price)
            if intent.stop_price is not None:
                order_params["stop_price"] = str(intent.stop_price)
            if intent.extended_hours:
                order_params["extended_hours"] = True

            # Submit to Alpaca
            response = await self._trading_client.submit_order(**order_params)

            return OrderSubmitResult(
                success=True,
                exchange_order_id=response.id,
                status=self._map_alpaca_status(response.status),
            )

        except Exception as e:
            return OrderSubmitResult(
                success=False,
                exchange_order_id=None,
                status=OrderStatus.REJECTED,
                error_code="ALPACA_ERROR",
                error_message=str(e),
            )

    async def cancel_order(self, exchange_order_id: str) -> bool:
        """
        Cancel an order on Alpaca.

        Args:
            exchange_order_id: The Alpaca order ID

        Returns:
            True if cancel succeeded

        Raises:
            ConnectionError: If adapter is not connected
        """
        self._require_connection()
        try:
            await self._trading_client.cancel_order_by_id(exchange_order_id)
            return True
        except Exception:
            return False

    async def get_order(self, exchange_order_id: str) -> ExchangeOrder | None:
        """
        Get order by Alpaca order ID.

        Args:
            exchange_order_id: The Alpaca order ID

        Returns:
            ExchangeOrder if found

        Raises:
            ConnectionError: If adapter is not connected
        """
        self._require_connection()
        try:
            response = await self._trading_client.get_order_by_id(exchange_order_id)
            return self._map_alpaca_order(response)
        except Exception:
            return None

    async def list_orders(
        self,
        status: OrderStatus | None = None,
        symbols: list[str] | None = None,
        limit: int = 100,
    ) -> list[ExchangeOrder]:
        """
        List orders from Alpaca.

        Args:
            status: Filter by status
            symbols: Filter by symbols
            limit: Maximum results

        Returns:
            List of ExchangeOrder

        Raises:
            ConnectionError: If adapter is not connected
        """
        self._require_connection()
        try:
            params: dict[str, Any] = {"limit": limit}
            if status is not None:
                params["status"] = self._map_status_to_alpaca(status)
            if symbols is not None:
                params["symbols"] = symbols

            response = await self._trading_client.get_orders(**params)
            return [self._map_alpaca_order(o) for o in response]
        except Exception:
            return []

    # =========================================================================
    # Account & Positions
    # =========================================================================

    async def get_account(self) -> AccountInfo:
        """
        Get Alpaca account info.

        Raises:
            ConnectionError: If adapter is not connected
        """
        self._require_connection()
        response = await self._trading_client.get_account()
        return AccountInfo(
            account_id=response.id,
            buying_power=Decimal(response.buying_power),
            cash=Decimal(response.cash),
            portfolio_value=Decimal(response.portfolio_value),
            currency=response.currency,
            status=response.status,
        )

    async def get_positions(self) -> list[Position]:
        """
        Get all positions from Alpaca.

        Raises:
            ConnectionError: If adapter is not connected
        """
        self._require_connection()
        response = await self._trading_client.get_all_positions()
        return [self._map_alpaca_position(p) for p in response]

    async def get_position(self, symbol: str) -> Position | None:
        """Get position for a symbol."""
        try:
            response = await self._trading_client.get_open_position(symbol)
            return self._map_alpaca_position(response)
        except Exception:
            return None

    # =========================================================================
    # Market Data
    # =========================================================================

    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        """Get historical bars from Alpaca."""
        params = {
            "symbol_or_symbols": symbol,
            "timeframe": self._map_timeframe(timeframe),
            "start": start,
        }
        if end is not None:
            params["end"] = end
        if limit is not None:
            params["limit"] = limit

        response = await self._stock_data_client.get_stock_bars(**params)
        bars_data = response.get(symbol, [])
        return [self._map_alpaca_bar(symbol, b) for b in bars_data]

    async def get_latest_bar(self, symbol: str) -> Bar | None:
        """Get latest bar for a symbol."""
        try:
            response = await self._stock_data_client.get_stock_latest_bar(symbol)
            bar_data = response.get(symbol)
            if bar_data:
                return self._map_alpaca_bar(symbol, bar_data)
            return None
        except Exception:
            return None

    async def get_latest_quote(self, symbol: str) -> Quote | None:
        """Get latest quote for a symbol."""
        try:
            response = await self._stock_data_client.get_stock_latest_quote(symbol)
            quote_data = response.get(symbol)
            if quote_data:
                return Quote(
                    symbol=symbol,
                    timestamp=quote_data.timestamp,
                    bid_price=Decimal(str(quote_data.bid_price)),
                    bid_size=Decimal(str(quote_data.bid_size)),
                    ask_price=Decimal(str(quote_data.ask_price)),
                    ask_size=Decimal(str(quote_data.ask_size)),
                )
            return None
        except Exception:
            return None

    async def get_latest_trade(self, symbol: str) -> Trade | None:
        """Get latest trade for a symbol."""
        try:
            response = await self._stock_data_client.get_stock_latest_trade(symbol)
            trade_data = response.get(symbol)
            if trade_data:
                return Trade(
                    symbol=symbol,
                    timestamp=trade_data.timestamp,
                    price=Decimal(str(trade_data.price)),
                    size=Decimal(str(trade_data.size)),
                    exchange=trade_data.exchange,
                )
            return None
        except Exception:
            return None

    async def stream_bars(self, symbols: list[str]) -> AsyncIterator[Bar]:
        """Stream bars (not yet implemented)."""
        raise NotImplementedError("stream_bars is not yet implemented")

    async def stream_quotes(self, symbols: list[str]) -> AsyncIterator[Quote]:
        """Stream quotes (not yet implemented)."""
        raise NotImplementedError("stream_quotes is not yet implemented")

    # =========================================================================
    # Mapping Helpers
    # =========================================================================

    @staticmethod
    def _map_order_type(order_type: OrderType) -> str:
        """Map OrderType to Alpaca type string."""
        mapping = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit",
        }
        return mapping[order_type]

    @staticmethod
    def _map_time_in_force(tif: TimeInForce) -> str:
        """Map TimeInForce to Alpaca TIF string."""
        mapping = {
            TimeInForce.DAY: "day",
            TimeInForce.GTC: "gtc",
            TimeInForce.IOC: "ioc",
            TimeInForce.FOK: "fok",
        }
        return mapping[tif]

    @staticmethod
    def _map_alpaca_status(status: str) -> OrderStatus:
        """Map Alpaca status string to OrderStatus."""
        mapping = {
            "new": OrderStatus.SUBMITTED,
            "accepted": OrderStatus.ACCEPTED,
            "pending_new": OrderStatus.SUBMITTING,
            "accepted_for_bidding": OrderStatus.ACCEPTED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "done_for_day": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "expired": OrderStatus.EXPIRED,
            "replaced": OrderStatus.CANCELLED,
            "pending_cancel": OrderStatus.ACCEPTED,
            "pending_replace": OrderStatus.ACCEPTED,
            "stopped": OrderStatus.ACCEPTED,
            "rejected": OrderStatus.REJECTED,
            "suspended": OrderStatus.REJECTED,
            "calculated": OrderStatus.ACCEPTED,
        }
        return mapping.get(status, OrderStatus.PENDING)

    @staticmethod
    def _map_status_to_alpaca(status: OrderStatus) -> str:
        """Map OrderStatus to Alpaca query status."""
        mapping = {
            OrderStatus.PENDING: "pending_new",
            OrderStatus.SUBMITTED: "new",
            OrderStatus.ACCEPTED: "open",
            OrderStatus.FILLED: "closed",
            OrderStatus.CANCELLED: "closed",
            OrderStatus.REJECTED: "closed",
        }
        return mapping.get(status, "all")

    def _map_alpaca_order(self, response) -> ExchangeOrder:
        """Map Alpaca order response to ExchangeOrder."""
        filled_price = None
        if response.filled_avg_price is not None:
            filled_price = Decimal(str(response.filled_avg_price))

        return ExchangeOrder(
            exchange_order_id=response.id,
            client_order_id=response.client_order_id,
            symbol=response.symbol,
            side=OrderSide.BUY if response.side == "buy" else OrderSide.SELL,
            order_type=self._map_alpaca_order_type(response.type),
            qty=Decimal(str(response.qty)),
            filled_qty=Decimal(str(response.filled_qty)),
            filled_avg_price=filled_price,
            status=self._map_alpaca_status(response.status),
            created_at=response.created_at,
            updated_at=response.updated_at,
        )

    @staticmethod
    def _map_alpaca_order_type(type_str: str) -> OrderType:
        """Map Alpaca order type string to OrderType."""
        mapping = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT,
        }
        return mapping.get(type_str, OrderType.MARKET)

    @staticmethod
    def _map_alpaca_position(response) -> Position:
        """Map Alpaca position response to Position."""
        return Position(
            symbol=response.symbol,
            qty=Decimal(str(response.qty)),
            side=PositionSide.LONG if response.side == "long" else PositionSide.SHORT,
            avg_entry_price=Decimal(str(response.avg_entry_price)),
            market_value=Decimal(str(response.market_value)),
            unrealized_pnl=Decimal(str(response.unrealized_pl)),
            unrealized_pnl_percent=Decimal(str(response.unrealized_plpc)),
        )

    @staticmethod
    def _map_alpaca_bar(symbol: str, bar) -> Bar:
        """Map Alpaca bar response to Bar."""
        return Bar(
            symbol=symbol,
            timestamp=bar.timestamp,
            open=Decimal(str(bar.open)),
            high=Decimal(str(bar.high)),
            low=Decimal(str(bar.low)),
            close=Decimal(str(bar.close)),
            volume=Decimal(str(bar.volume)),
            trade_count=bar.trade_count,
            vwap=Decimal(str(bar.vwap)) if bar.vwap else None,
        )

    @staticmethod
    def _map_timeframe(timeframe: str) -> str:
        """Map timeframe string to Alpaca format."""
        # Alpaca accepts formats like "1Min", "1Hour", "1Day"
        unit = timeframe[-1]
        value = timeframe[:-1] if len(timeframe) > 1 else "1"

        if unit == "m":
            return f"{value}Min"
        elif unit == "h":
            return f"{value}Hour"
        elif unit == "d":
            return f"{value}Day"
        elif unit == "w":
            return f"{value}Week"
        else:
            return timeframe  # Pass through

"""
Mock Exchange Adapter

A mock implementation of ExchangeAdapter for testing.
Simulates exchange behavior without making real API calls.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import AsyncIterator
from uuid import uuid4

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


class MockExchangeAdapter(ExchangeAdapter):
    """
    Mock exchange adapter for testing.

    Features:
    - Simulates order submission with idempotency
    - Market orders fill immediately
    - Limit orders stay in ACCEPTED state
    - Configurable mock prices and rejections
    - Mock account and position data
    - Mock market data generation
    """

    def __init__(self) -> None:
        """Initialize mock adapter with default state."""
        # Order storage: exchange_order_id -> ExchangeOrder
        self._orders: dict[str, ExchangeOrder] = {}
        # Idempotency mapping: client_order_id -> exchange_order_id
        self._client_order_map: dict[str, str] = {}
        # Mock prices: symbol -> price
        self._mock_prices: dict[str, Decimal] = {
            "BTC/USD": Decimal("42000.00"),
            "ETH/USD": Decimal("2500.00"),
        }
        # Mock account
        self._mock_account = AccountInfo(
            account_id="mock-account-001",
            buying_power=Decimal("100000.00"),
            cash=Decimal("50000.00"),
            portfolio_value=Decimal("150000.00"),
            currency="USD",
            status="ACTIVE",
        )
        # Mock positions
        self._mock_positions: dict[str, Position] = {}
        # Rejection configuration
        self._reject_next_order = False
        self._reject_reason: str | None = None

    # =========================================================================
    # Configuration Methods (for testing)
    # =========================================================================

    def set_mock_price(self, symbol: str, price: Decimal) -> None:
        """Set mock price for a symbol."""
        self._mock_prices[symbol] = price

    def set_reject_next_order(
        self, reject: bool, reason: str | None = None
    ) -> None:
        """Configure next order to be rejected."""
        self._reject_next_order = reject
        self._reject_reason = reason

    def reset(self) -> None:
        """Reset all state."""
        self._orders.clear()
        self._client_order_map.clear()
        self._reject_next_order = False
        self._reject_reason = None

    # =========================================================================
    # Order Management
    # =========================================================================

    async def submit_order(self, intent: OrderIntent) -> OrderSubmitResult:
        """
        Submit order (mock implementation).

        - Idempotent: same client_order_id returns same exchange_order_id
        - Market orders fill immediately
        - Limit orders stay in ACCEPTED state
        """
        # Check idempotency
        if intent.client_order_id in self._client_order_map:
            exchange_order_id = self._client_order_map[intent.client_order_id]
            order = self._orders[exchange_order_id]
            return OrderSubmitResult(
                success=True,
                exchange_order_id=exchange_order_id,
                status=order.status,
            )

        # Check for configured rejection
        if self._reject_next_order:
            self._reject_next_order = False
            reason = self._reject_reason or "Order rejected"
            self._reject_reason = None
            return OrderSubmitResult(
                success=False,
                exchange_order_id=None,
                status=OrderStatus.REJECTED,
                error_code="REJECTED",
                error_message=reason,
            )

        # Generate exchange order ID
        exchange_order_id = str(uuid4())
        now = datetime.now(UTC)

        # Determine fill status based on order type
        if intent.order_type == OrderType.MARKET:
            # Market orders fill immediately
            status = OrderStatus.FILLED
            filled_qty = intent.qty
            filled_avg_price = self._get_mock_price(intent.symbol)
        else:
            # Limit/Stop orders stay accepted
            status = OrderStatus.ACCEPTED
            filled_qty = Decimal("0")
            filled_avg_price = None

        # Create exchange order
        order = ExchangeOrder(
            exchange_order_id=exchange_order_id,
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            order_type=intent.order_type,
            qty=intent.qty,
            filled_qty=filled_qty,
            filled_avg_price=filled_avg_price,
            status=status,
            created_at=now,
            updated_at=now,
        )

        # Store order
        self._orders[exchange_order_id] = order
        self._client_order_map[intent.client_order_id] = exchange_order_id

        return OrderSubmitResult(
            success=True,
            exchange_order_id=exchange_order_id,
            status=status,
        )

    async def cancel_order(self, exchange_order_id: str) -> bool:
        """
        Cancel an order.

        Returns False if order not found or already in terminal state.
        """
        order = self._orders.get(exchange_order_id)
        if order is None:
            return False

        # Can't cancel orders in terminal states
        terminal_states = {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        }
        if order.status in terminal_states:
            return False

        # Update order status
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(UTC)
        return True

    async def get_order(self, exchange_order_id: str) -> ExchangeOrder | None:
        """Get order by exchange order ID."""
        return self._orders.get(exchange_order_id)

    async def list_orders(
        self,
        status: OrderStatus | None = None,
        symbols: list[str] | None = None,
        limit: int = 100,
    ) -> list[ExchangeOrder]:
        """List orders with optional filters."""
        orders = list(self._orders.values())

        if status is not None:
            orders = [o for o in orders if o.status == status]

        if symbols is not None:
            orders = [o for o in orders if o.symbol in symbols]

        return orders[:limit]

    # =========================================================================
    # Account & Positions
    # =========================================================================

    async def get_account(self) -> AccountInfo:
        """Get mock account information."""
        return self._mock_account

    async def get_positions(self) -> list[Position]:
        """Get all mock positions."""
        return list(self._mock_positions.values())

    async def get_position(self, symbol: str) -> Position | None:
        """Get mock position for a symbol."""
        return self._mock_positions.get(symbol)

    # =========================================================================
    # Market Data
    # =========================================================================

    def _get_mock_price(self, symbol: str) -> Decimal:
        """Get mock price for a symbol."""
        return self._mock_prices.get(symbol, Decimal("100.00"))

    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        """Generate mock OHLCV bars."""
        if end is None:
            end = datetime.now(UTC)

        # Parse timeframe to get interval
        interval_minutes = self._parse_timeframe(timeframe)

        # Generate bars
        bars: list[Bar] = []
        current = start
        base_price = self._get_mock_price(symbol)

        while current < end:
            if limit is not None and len(bars) >= limit:
                break

            # Generate OHLCV with some variation
            variation = Decimal(str(len(bars) % 10 - 5)) / Decimal("100")
            price = base_price * (1 + variation)

            bar = Bar(
                symbol=symbol,
                timestamp=current,
                open=price * Decimal("0.999"),
                high=price * Decimal("1.002"),
                low=price * Decimal("0.998"),
                close=price,
                volume=Decimal("100.0"),
                trade_count=50,
                vwap=price,
            )
            bars.append(bar)
            current += timedelta(minutes=interval_minutes)

        return bars

    async def get_latest_bar(self, symbol: str) -> Bar | None:
        """Get latest mock bar."""
        price = self._get_mock_price(symbol)
        now = datetime.now(UTC)
        return Bar(
            symbol=symbol,
            timestamp=now,
            open=price * Decimal("0.999"),
            high=price * Decimal("1.002"),
            low=price * Decimal("0.998"),
            close=price,
            volume=Decimal("100.0"),
            trade_count=50,
            vwap=price,
        )

    async def get_latest_quote(self, symbol: str) -> Quote | None:
        """Get latest mock quote."""
        price = self._get_mock_price(symbol)
        spread = price * Decimal("0.0001")  # 0.01% spread
        return Quote(
            symbol=symbol,
            timestamp=datetime.now(UTC),
            bid_price=price - spread,
            bid_size=Decimal("1.0"),
            ask_price=price + spread,
            ask_size=Decimal("1.0"),
        )

    async def get_latest_trade(self, symbol: str) -> Trade | None:
        """Get latest mock trade."""
        price = self._get_mock_price(symbol)
        return Trade(
            symbol=symbol,
            timestamp=datetime.now(UTC),
            price=price,
            size=Decimal("0.1"),
            exchange="MOCK",
        )

    # =========================================================================
    # Streaming (Stub implementations)
    # =========================================================================

    async def stream_bars(self, symbols: list[str]) -> AsyncIterator[Bar]:
        """Stream bars (not implemented in mock)."""
        # Yield nothing - streaming not needed for unit tests
        return
        yield  # Make this a generator

    async def stream_quotes(self, symbols: list[str]) -> AsyncIterator[Quote]:
        """Stream quotes (not implemented in mock)."""
        # Yield nothing - streaming not needed for unit tests
        return
        yield  # Make this a generator

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _parse_timeframe(timeframe: str) -> int:
        """Parse timeframe string to minutes."""
        unit = timeframe[-1]
        value = int(timeframe[:-1]) if len(timeframe) > 1 else 1

        if unit == "m":
            return value
        elif unit == "h":
            return value * 60
        elif unit == "d":
            return value * 60 * 24
        else:
            return 1  # Default to 1 minute

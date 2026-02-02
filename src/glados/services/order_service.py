"""
Order Service

Provides order query capabilities.
MVP-4: Mock implementation with fake data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from src.glados.schemas import OrderSide, OrderStatus, OrderType


@dataclass
class Order:
    """Internal Order entity."""

    id: str
    run_id: str
    client_order_id: str
    exchange_order_id: str | None
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Decimal | None
    stop_price: Decimal | None
    time_in_force: str
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    status: OrderStatus
    created_at: datetime
    submitted_at: datetime | None
    filled_at: datetime | None
    reject_reason: str | None


class MockOrderService:
    """
    Mock order service for MVP-4.
    
    Returns fake order data for testing and development.
    
    Future (M3+):
    - Real data from Veda/WallE
    - Complex filtering (status, date range)
    - Pagination
    """

    def __init__(self) -> None:
        # Pre-populate with some mock orders
        self._orders: dict[str, Order] = {}
        self._init_mock_data()

    def _init_mock_data(self) -> None:
        """Initialize mock order data."""
        now = datetime.now(UTC)
        
        # Order 1: Filled buy order
        self._orders["order-123"] = Order(
            id="order-123",
            run_id="run-123",
            client_order_id="client-123",
            exchange_order_id="exch-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("0.5"),
            price=None,
            stop_price=None,
            time_in_force="day",
            filled_qty=Decimal("0.5"),
            filled_avg_price=Decimal("42150.00"),
            status=OrderStatus.FILLED,
            created_at=now,
            submitted_at=now,
            filled_at=now,
            reject_reason=None,
        )
        
        # Order 2: Pending limit order
        self._orders["order-456"] = Order(
            id="order-456",
            run_id="run-123",
            client_order_id="client-456",
            exchange_order_id="exch-456",
            symbol="ETH/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            qty=Decimal("2.0"),
            price=Decimal("2500.00"),
            stop_price=None,
            time_in_force="gtc",
            filled_qty=Decimal("0"),
            filled_avg_price=None,
            status=OrderStatus.SUBMITTED,
            created_at=now,
            submitted_at=now,
            filled_at=None,
            reject_reason=None,
        )

    async def get(self, order_id: str) -> Order | None:
        """
        Get order by ID.
        
        Args:
            order_id: The order ID to fetch
            
        Returns:
            Order if found, None otherwise
        """
        return self._orders.get(order_id)

    async def list(
        self,
        run_id: str | None = None,
    ) -> tuple[list[Order], int]:
        """
        List orders with optional filter.
        
        MVP-4: Only run_id filter supported.
        
        Args:
            run_id: Filter by run ID
            
        Returns:
            Tuple of (orders list, total count)
        """
        orders = list(self._orders.values())
        
        if run_id is not None:
            orders = [o for o in orders if o.run_id == run_id]
        
        return orders, len(orders)

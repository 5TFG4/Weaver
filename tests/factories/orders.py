"""
Order Factories

Provides factory functions and classes for creating test orders.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4


@dataclass
class OrderFactory:
    """
    Factory for creating test order objects.
    
    Usage:
        # Create with defaults
        order = OrderFactory.create("AAPL", "buy", 100)
        
        # Create with custom fields
        order = OrderFactory.create(
            "AAPL",
            "sell",
            50,
            order_type="limit",
            limit_price=Decimal("150.00"),
        )
        
        # Use builder pattern
        order = (OrderFactory()
            .with_symbol("BTCUSD")
            .with_side("buy")
            .with_qty(Decimal("0.5"))
            .build())
    """
    
    _id: str | None = None
    _client_order_id: str | None = None
    _run_id: str | None = None
    _symbol: str = "AAPL"
    _side: str = "buy"
    _order_type: str = "market"
    _qty: Decimal = Decimal("100")
    _limit_price: Decimal | None = None
    _status: str = "pending"
    _filled_qty: Decimal = Decimal("0")
    _filled_avg_price: Decimal | None = None
    _created_at: datetime | None = None
    _updated_at: datetime | None = None
    
    def with_id(self, id: str) -> "OrderFactory":
        """Set order ID."""
        self._id = id
        return self
    
    def with_client_order_id(self, client_order_id: str) -> "OrderFactory":
        """Set client order ID."""
        self._client_order_id = client_order_id
        return self
    
    def with_run_id(self, run_id: str) -> "OrderFactory":
        """Set run ID."""
        self._run_id = run_id
        return self
    
    def with_symbol(self, symbol: str) -> "OrderFactory":
        """Set symbol."""
        self._symbol = symbol
        return self
    
    def with_side(self, side: str) -> "OrderFactory":
        """Set side (buy or sell)."""
        self._side = side
        return self
    
    def with_order_type(self, order_type: str) -> "OrderFactory":
        """Set order type (market or limit)."""
        self._order_type = order_type
        return self
    
    def with_qty(self, qty: Decimal | float | int) -> "OrderFactory":
        """Set quantity."""
        self._qty = Decimal(str(qty))
        return self
    
    def with_limit_price(self, price: Decimal | float | None) -> "OrderFactory":
        """Set limit price."""
        self._limit_price = Decimal(str(price)) if price else None
        return self
    
    def with_status(self, status: str) -> "OrderFactory":
        """Set status."""
        self._status = status
        return self
    
    def with_fill(
        self,
        filled_qty: Decimal | float,
        avg_price: Decimal | float,
    ) -> "OrderFactory":
        """Set fill information."""
        self._filled_qty = Decimal(str(filled_qty))
        self._filled_avg_price = Decimal(str(avg_price))
        self._status = "filled" if self._filled_qty >= self._qty else "partial"
        return self
    
    def build(self) -> dict[str, Any]:
        """Build the order as a dictionary."""
        now = datetime.now(timezone.utc)
        return {
            "id": self._id or str(uuid4()),
            "client_order_id": self._client_order_id or str(uuid4()),
            "run_id": self._run_id,
            "symbol": self._symbol,
            "side": self._side,
            "order_type": self._order_type,
            "qty": self._qty,
            "limit_price": self._limit_price,
            "status": self._status,
            "filled_qty": self._filled_qty,
            "filled_avg_price": self._filled_avg_price,
            "created_at": self._created_at or now,
            "updated_at": self._updated_at or now,
        }
    
    @classmethod
    def create(
        cls,
        symbol: str,
        side: str,
        qty: float | int | Decimal,
        *,
        order_type: str = "market",
        limit_price: float | Decimal | None = None,
        status: str = "pending",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Convenience method to create an order with minimal boilerplate.
        
        Args:
            symbol: Trading symbol (e.g., "AAPL", "BTCUSD")
            side: Order side ("buy" or "sell")
            qty: Order quantity
            order_type: Order type (default: "market")
            limit_price: Limit price for limit orders
            status: Order status (default: "pending")
            run_id: Optional run ID
            
        Returns:
            Order as dictionary
        """
        factory = (
            cls()
            .with_symbol(symbol)
            .with_side(side)
            .with_qty(qty)
            .with_order_type(order_type)
            .with_status(status)
        )
        
        if limit_price is not None:
            factory.with_limit_price(limit_price)
        
        if run_id is not None:
            factory.with_run_id(run_id)
        
        return factory.build()


def create_order(
    symbol: str = "AAPL",
    side: str = "buy",
    qty: float | int | Decimal = 100,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Simple function to create a test order.
    
    Args:
        symbol: Trading symbol
        side: Order side
        qty: Quantity
        **kwargs: Additional fields
        
    Returns:
        Order as dictionary
    """
    return OrderFactory.create(symbol, side, qty, **kwargs)


# =============================================================================
# Pre-built Order Templates
# =============================================================================

def create_market_buy(
    symbol: str,
    qty: float | int | Decimal,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a market buy order."""
    return create_order(
        symbol=symbol,
        side="buy",
        qty=qty,
        order_type="market",
        run_id=run_id,
    )


def create_market_sell(
    symbol: str,
    qty: float | int | Decimal,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a market sell order."""
    return create_order(
        symbol=symbol,
        side="sell",
        qty=qty,
        order_type="market",
        run_id=run_id,
    )


def create_limit_buy(
    symbol: str,
    qty: float | int | Decimal,
    price: float | Decimal,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a limit buy order."""
    return create_order(
        symbol=symbol,
        side="buy",
        qty=qty,
        order_type="limit",
        limit_price=price,
        run_id=run_id,
    )


def create_limit_sell(
    symbol: str,
    qty: float | int | Decimal,
    price: float | Decimal,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a limit sell order."""
    return create_order(
        symbol=symbol,
        side="sell",
        qty=qty,
        order_type="limit",
        limit_price=price,
        run_id=run_id,
    )


def create_filled_order(
    symbol: str,
    side: str,
    qty: float | int | Decimal,
    fill_price: float | Decimal,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a filled order."""
    factory = (
        OrderFactory()
        .with_symbol(symbol)
        .with_side(side)
        .with_qty(qty)
        .with_fill(qty, fill_price)
    )
    if run_id:
        factory = factory.with_run_id(run_id)
    return factory.build()

"""
Orders Routes

REST endpoints for order queries.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.glados.schemas import OrderListResponse, OrderResponse, OrderStatus
from src.glados.services.order_service import MockOrderService, Order

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

# Shared service instance for MVP-4
_order_service: MockOrderService | None = None


def get_order_service() -> MockOrderService:
    """Get or create OrderService instance."""
    global _order_service
    if _order_service is None:
        _order_service = MockOrderService()
    return _order_service


def reset_order_service() -> None:
    """Reset OrderService (for testing)."""
    global _order_service
    _order_service = None


def _order_to_response(order: Order) -> OrderResponse:
    """Convert internal Order to OrderResponse."""
    return OrderResponse(
        id=order.id,
        run_id=order.run_id,
        client_order_id=order.client_order_id,
        exchange_order_id=order.exchange_order_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        qty=str(order.qty),
        price=str(order.price) if order.price else None,
        stop_price=str(order.stop_price) if order.stop_price else None,
        time_in_force=order.time_in_force,
        filled_qty=str(order.filled_qty),
        filled_avg_price=str(order.filled_avg_price) if order.filled_avg_price else None,
        status=order.status,
        created_at=order.created_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        reject_reason=order.reject_reason,
    )


@router.get("", response_model=OrderListResponse)
async def list_orders(
    run_id: str | None = Query(default=None),
    order_service: MockOrderService = Depends(get_order_service),
) -> OrderListResponse:
    """
    List orders with optional filters.
    
    MVP-4: Only run_id filter supported.
    """
    orders, total = await order_service.list(run_id=run_id)
    return OrderListResponse(
        items=[_order_to_response(o) for o in orders],
        total=total,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    order_service: MockOrderService = Depends(get_order_service),
) -> OrderResponse:
    """Get order by ID."""
    order = await order_service.get(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order not found: {order_id}",
        )
    return _order_to_response(order)

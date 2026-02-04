"""
Orders Routes

REST endpoints for order management.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.glados.dependencies import get_order_service, get_veda_service
from src.glados.schemas import OrderCreate, OrderListResponse, OrderResponse
from src.glados.services.order_service import MockOrderService, Order
from src.veda import VedaService
from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderState,
    OrderType,
    TimeInForce,
)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


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


def _state_to_response(state: OrderState) -> OrderResponse:
    """Convert Veda OrderState to OrderResponse."""
    return OrderResponse(
        id=state.intent.client_order_id,
        run_id=state.intent.run_id,
        client_order_id=state.intent.client_order_id,
        exchange_order_id=state.exchange_order_id,
        symbol=state.intent.symbol,
        side=state.intent.side.value,
        order_type=state.intent.order_type.value,
        qty=str(state.intent.qty),
        price=str(state.intent.limit_price) if state.intent.limit_price else None,
        stop_price=str(state.intent.stop_price) if state.intent.stop_price else None,
        time_in_force=state.intent.time_in_force.value,
        filled_qty=str(state.filled_qty),
        filled_avg_price=str(state.filled_avg_price) if state.filled_avg_price else None,
        status=state.status.value,
        created_at=state.created_at,
        submitted_at=state.submitted_at,
        filled_at=state.filled_at,
        reject_reason=state.reject_reason,
    )


def _require_veda_service(
    veda_service: VedaService | None = Depends(get_veda_service),
) -> VedaService:
    """Require VedaService to be configured."""
    if veda_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trading service not configured",
        )
    return veda_service


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    veda_service: VedaService = Depends(_require_veda_service),
) -> OrderResponse:
    """
    Create a new order.
    
    Requires VedaService to be configured (live/paper trading enabled).
    """
    # Map request to OrderIntent
    intent = OrderIntent(
        run_id=body.run_id,
        client_order_id=body.client_order_id,
        symbol=body.symbol,
        side=OrderSide(body.side),
        order_type=OrderType(body.order_type),
        qty=Decimal(body.qty),
        limit_price=Decimal(body.limit_price) if body.limit_price else None,
        stop_price=Decimal(body.stop_price) if body.stop_price else None,
        time_in_force=TimeInForce(body.time_in_force),
        extended_hours=body.extended_hours,
    )
    
    # Place order via VedaService
    state = await veda_service.place_order(intent)
    
    return _state_to_response(state)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: str,
    veda_service: VedaService = Depends(_require_veda_service),
) -> None:
    """
    Cancel an order by client_order_id.
    
    Requires VedaService to be configured.
    """
    success = await veda_service.cancel_order(order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order not found: {order_id}",
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

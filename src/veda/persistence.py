"""
Veda Persistence Layer

Repository for order persistence. Uses VedaOrder model from walle/models.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.veda.models import (
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from src.walle.models import VedaOrder


# =============================================================================
# Conversion Functions
# =============================================================================


def order_state_to_veda_order(state: OrderState) -> VedaOrder:
    """Create VedaOrder from domain OrderState."""
    return VedaOrder(
        id=state.id,
        client_order_id=state.client_order_id,
        exchange_order_id=state.exchange_order_id,
        run_id=state.run_id,
        symbol=state.symbol,
        side=state.side.value,
        order_type=state.order_type.value,
        qty=state.qty,
        limit_price=state.limit_price,
        stop_price=state.stop_price,
        time_in_force=state.time_in_force.value,
        status=state.status.value,
        filled_qty=state.filled_qty,
        filled_avg_price=state.filled_avg_price,
        created_at=state.created_at,
        submitted_at=state.submitted_at,
        filled_at=state.filled_at,
        cancelled_at=state.cancelled_at,
        reject_reason=state.reject_reason,
        error_code=state.error_code,
    )


def veda_order_to_order_state(order: VedaOrder) -> OrderState:
    """Convert VedaOrder to domain OrderState."""
    return OrderState(
        id=order.id,
        client_order_id=order.client_order_id,
        exchange_order_id=order.exchange_order_id,
        run_id=order.run_id,
        symbol=order.symbol,
        side=OrderSide(order.side),
        order_type=OrderType(order.order_type),
        qty=order.qty,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
        time_in_force=TimeInForce(order.time_in_force),
        status=OrderStatus(order.status),
        filled_qty=order.filled_qty,
        filled_avg_price=order.filled_avg_price,
        created_at=order.created_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        cancelled_at=order.cancelled_at,
        reject_reason=order.reject_reason,
        error_code=order.error_code,
    )


# =============================================================================
# Repository
# =============================================================================


class OrderRepository:
    """
    Repository for order persistence operations.

    Provides clean interface for CRUD operations on orders.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
    ) -> None:
        """
        Initialize repository.

        Args:
            session_factory: Factory to get async session
        """
        self._session_factory = session_factory

    async def save(self, order_state: OrderState) -> None:
        """
        Save or update an order (upsert).

        Uses SQLAlchemy's merge() to perform an upsert:
        - If order with same ID exists, updates all fields
        - If order doesn't exist, inserts a new row

        Args:
            order_state: The OrderState to persist
        """
        async with self._session_factory() as session:
            veda_order = order_state_to_veda_order(order_state)
            await session.merge(veda_order)
            await session.commit()

    async def get_by_id(self, order_id: str) -> OrderState | None:
        """
        Get order by Veda ID.

        Args:
            order_id: The Veda order ID

        Returns:
            OrderState if found, None otherwise
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(VedaOrder).where(VedaOrder.id == order_id)
            )
            row = result.scalar_one_or_none()
            return veda_order_to_order_state(row) if row else None

    async def get_by_client_order_id(
        self, client_order_id: str
    ) -> OrderState | None:
        """
        Get order by client order ID.

        Args:
            client_order_id: The client order ID (idempotency key)

        Returns:
            OrderState if found, None otherwise
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(VedaOrder).where(VedaOrder.client_order_id == client_order_id)
            )
            row = result.scalar_one_or_none()
            return veda_order_to_order_state(row) if row else None

    async def list_by_run_id(
        self, run_id: str, status: OrderStatus | None = None
    ) -> list[OrderState]:
        """
        List orders for a specific run.

        Args:
            run_id: The run ID
            status: Optional filter by status

        Returns:
            List of OrderState instances
        """
        async with self._session_factory() as session:
            query = select(VedaOrder).where(VedaOrder.run_id == run_id)
            if status is not None:
                query = query.where(VedaOrder.status == status.value)
            
            result = await session.execute(query)
            rows = result.scalars().all()
            return [veda_order_to_order_state(row) for row in rows]

    async def list_by_status(
        self, status: OrderStatus, limit: int = 100
    ) -> list[OrderState]:
        """
        List orders by status.

        Args:
            status: The status to filter by
            limit: Maximum number of results

        Returns:
            List of OrderState instances
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(VedaOrder)
                .where(VedaOrder.status == status.value)
                .limit(limit)
            )
            rows = result.scalars().all()
            return [veda_order_to_order_state(row) for row in rows]


# Re-export VedaOrder for backward compatibility
# Canonical location is src/walle/models.py
__all__ = [
    "VedaOrder",
    "OrderRepository",
    "order_state_to_veda_order",
    "veda_order_to_order_state",
]

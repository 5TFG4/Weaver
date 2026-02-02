"""
Veda Persistence Layer

SQLAlchemy models and repository for order persistence.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable

from sqlalchemy import DateTime, Index, Numeric, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.veda.models import (
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from src.walle.models import Base


# =============================================================================
# SQLAlchemy Model
# =============================================================================


class VedaOrder(Base):
    """
    SQLAlchemy model for persisting order state.

    Maps to veda_orders table for durable order tracking.
    """

    __tablename__ = "veda_orders"

    # Identity
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_order_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    exchange_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    run_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Order details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # buy | sell
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    time_in_force: Mapped[str] = mapped_column(String(10), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Fill info
    filled_qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    filled_avg_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error handling
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Composite indexes
    __table_args__ = (
        Index("idx_veda_orders_run_status", "run_id", "status"),
        Index("idx_veda_orders_symbol_status", "symbol", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<VedaOrder(id={self.id!r}, symbol={self.symbol!r}, "
            f"status={self.status!r})>"
        )

    # =========================================================================
    # Conversion Methods
    # =========================================================================

    def to_order_state(self) -> OrderState:
        """Convert to domain OrderState."""
        return OrderState(
            id=self.id,
            client_order_id=self.client_order_id,
            exchange_order_id=self.exchange_order_id,
            run_id=self.run_id,
            symbol=self.symbol,
            side=OrderSide(self.side),
            order_type=OrderType(self.order_type),
            qty=self.qty,
            limit_price=self.limit_price,
            stop_price=self.stop_price,
            time_in_force=TimeInForce(self.time_in_force),
            status=OrderStatus(self.status),
            filled_qty=self.filled_qty,
            filled_avg_price=self.filled_avg_price,
            created_at=self.created_at,
            submitted_at=self.submitted_at,
            filled_at=self.filled_at,
            cancelled_at=self.cancelled_at,
            reject_reason=self.reject_reason,
            error_code=self.error_code,
        )

    @classmethod
    def from_order_state(cls, state: OrderState) -> VedaOrder:
        """Create VedaOrder from domain OrderState."""
        return cls(
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
            veda_order = VedaOrder.from_order_state(order_state)
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
            return row.to_order_state() if row else None

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
            return row.to_order_state() if row else None

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
            return [row.to_order_state() for row in rows]

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
            return [row.to_order_state() for row in rows]

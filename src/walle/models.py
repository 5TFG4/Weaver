"""
WallE Database Models

SQLAlchemy 2.0 async models for Weaver persistence layer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {
        dict[str, Any]: JSONB,
    }


class OutboxEvent(Base):
    """
    Outbox table for event sourcing.

    Events are appended here within business transactions.
    LISTEN/NOTIFY wakes consumers after commit.
    """

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("idx_outbox_type_created", "type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<OutboxEvent(id={self.id}, type={self.type!r})>"


class ConsumerOffset(Base):
    """
    Consumer offset tracking for at-least-once delivery.

    Each consumer tracks its last processed outbox.id here.
    On restart, consumers resume from their last offset.
    """

    __tablename__ = "consumer_offsets"

    consumer_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_offset: Mapped[int] = mapped_column(BigInteger, nullable=False, default=-1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<ConsumerOffset(consumer_id={self.consumer_id!r}, last_offset={self.last_offset})>"


class BarRecord(Base):
    """
    Historical OHLCV bar data for backtesting.

    Stores candle data fetched from exchanges. Used by Greta
    during backtests to provide historical market data.
    
    Data is immutable once written - safe to share across runs.
    """

    __tablename__ = "bars"
    
    # Constraint names (referenced by repository for upsert)
    UNIQUE_CONSTRAINT = "uq_bar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name=UNIQUE_CONSTRAINT),
        Index("ix_bars_lookup", "symbol", "timeframe", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<BarRecord({self.symbol} {self.timeframe} {self.timestamp})>"


class VedaOrder(Base):
    """
    SQLAlchemy model for persisting order state.

    Maps to veda_orders table for durable order tracking.
    
    Note: Defined in walle/models.py (persistence layer) but used by Veda.
    This ensures all SQLAlchemy models are registered in Base.metadata
    consistently, regardless of import order.
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
        return f"<VedaOrder(id={self.id!r}, symbol={self.symbol!r}, status={self.status!r})>"


# =============================================================================
# Model Registration Note
# =============================================================================
# All SQLAlchemy models MUST be defined in this file to ensure they are
# registered in Base.metadata when walle.models is imported.
#
# DO NOT define models in other modules (e.g., veda/persistence.py).
# This causes inconsistent metadata state depending on import order.

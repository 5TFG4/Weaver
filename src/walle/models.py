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


# =============================================================================
# Future Models (M2+)
# =============================================================================
# The following domain models will be added in future migrations:
#
# - Run: Trading run records (run_id, strategy, mode, status, timestamps)
# - Order: Order records (order_id, run_id, symbol, side, qty, status)
# - Fill: Fill/execution records (fill_id, order_id, price, qty, timestamp)
#
# Concrete SQLAlchemy models will be defined here once schemas are finalized.

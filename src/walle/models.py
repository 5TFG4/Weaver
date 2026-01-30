"""
WallE Database Models

SQLAlchemy 2.0 async models for Weaver persistence layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
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


# =============================================================================
# Future tables (stubs for M2+)
# =============================================================================

# class Run(Base):
#     """Trading run record."""
#     __tablename__ = "runs"
#     ...

# class Order(Base):
#     """Order record."""
#     __tablename__ = "orders"
#     ...

# class Fill(Base):
#     """Fill/execution record."""
#     __tablename__ = "fills"
#     ...

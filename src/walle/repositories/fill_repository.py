"""
Fill Repository

Provides persistence for fill history (audit trail).
D-3: Each fill is an immutable record of order execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.walle.models import FillRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class FillRepository:
    """
    Repository for fill persistence.

    Fills are append-only — never updated or deleted.
    Provides save and query operations for audit trail.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialize repository.

        Args:
            session_factory: SQLAlchemy async session factory
        """
        self._session_factory = session_factory

    async def save(self, record: FillRecord) -> None:
        """
        Save a fill record.

        Args:
            record: FillRecord to persist
        """
        async with self._session_factory() as session:
            session.add(record)
            await session.commit()

    async def list_by_order(self, order_id: str) -> list[FillRecord]:
        """
        List fills for a specific order.

        Args:
            order_id: The order identifier

        Returns:
            List of FillRecord ordered by filled_at ascending
        """
        async with self._session_factory() as session:
            stmt = (
                select(FillRecord)
                .where(FillRecord.order_id == order_id)
                .order_by(FillRecord.filled_at.asc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

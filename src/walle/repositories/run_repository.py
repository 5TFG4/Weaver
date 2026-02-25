"""
Run Repository

Provides CRUD operations for persisted run state.
D-2: Used by RunManager for restart recovery.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.walle.models import RunRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class RunRepository:
    """
    Repository for run persistence.

    Saves and retrieves run records for restart recovery.
    Follows the same pattern as BarRepository.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialize repository.

        Args:
            session_factory: SQLAlchemy async session factory
        """
        self._session_factory = session_factory

    async def save(self, record: RunRecord) -> None:
        """
        Save or update a run record.

        Uses merge() for upsert semantics — inserts if new,
        updates if existing.

        Args:
            record: RunRecord to persist
        """
        async with self._session_factory() as session:
            await session.merge(record)
            await session.commit()

    async def get(self, run_id: str) -> RunRecord | None:
        """
        Get a run record by ID.

        Args:
            run_id: The run identifier

        Returns:
            RunRecord if found, None otherwise
        """
        async with self._session_factory() as session:
            stmt = select(RunRecord).where(RunRecord.id == run_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list(
        self,
        status: str | None = None,
    ) -> list[RunRecord]:
        """
        List run records, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of RunRecord ordered by created_at descending
        """
        async with self._session_factory() as session:
            stmt = select(RunRecord).order_by(RunRecord.created_at.desc())
            if status is not None:
                stmt = stmt.where(RunRecord.status == status)
            result = await session.execute(stmt)
            return list(result.scalars().all())

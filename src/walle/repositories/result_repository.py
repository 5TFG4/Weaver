"""
Result Repository

Provides CRUD operations for backtest result records.
M13-2: Stores and retrieves BacktestResultRecord by run_id.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.walle.models import BacktestResultRecord


class ResultRepository:
    """Repository for backtest result persistence."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, record: BacktestResultRecord) -> None:
        """Save or update a backtest result record (upsert via merge)."""
        async with self._session_factory() as session:
            await session.merge(record)
            await session.commit()

    async def get_by_run_id(self, run_id: str) -> BacktestResultRecord | None:
        """Get a backtest result by run ID."""
        async with self._session_factory() as session:
            stmt = select(BacktestResultRecord).where(
                BacktestResultRecord.run_id == run_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

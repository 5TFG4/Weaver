"""
Bar Repository

Provides historical OHLCV bar data for backtesting.
This is a SINGLETON - safe to share across runs because bar data is immutable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.walle.models import BarRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True)
class Bar:
    """
    Immutable bar data transfer object.
    
    Used throughout the system to represent OHLCV data.
    Frozen dataclass ensures immutability.
    """

    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class BarRepository:
    """
    Repository for historical bar data.
    
    This is a SINGLETON shared across all runs because:
    - Historical data is immutable (cannot be modified)
    - Caching is efficient when shared
    - No isolation concerns (reads only)
    
    Responsibilities:
    - Store bars from exchange API
    - Retrieve bars for backtest time ranges
    - Handle upsert for duplicate timestamps
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """
        Initialize repository.
        
        Args:
            session_factory: SQLAlchemy async session factory
        """
        self._session_factory = session_factory

    async def save_bars(self, bars: Sequence[Bar]) -> int:
        """
        Save bars to database with upsert semantics.
        
        Bars with duplicate (symbol, timeframe, timestamp) are skipped.
        
        Args:
            bars: Sequence of Bar objects to save
            
        Returns:
            Number of bars actually inserted (excludes duplicates)
        """
        if not bars:
            return 0

        async with self._session_factory() as session:
            # Prepare values for bulk upsert
            values = [
                {
                    "symbol": bar.symbol,
                    "timeframe": bar.timeframe,
                    "timestamp": bar.timestamp,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in bars
            ]

            # PostgreSQL upsert: ON CONFLICT DO NOTHING
            stmt = pg_insert(BarRecord).values(values)
            stmt = stmt.on_conflict_do_nothing(constraint=BarRecord.UNIQUE_CONSTRAINT)

            result = await session.execute(stmt)
            await session.commit()

            return result.rowcount  # type: ignore[return-value]

    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """
        Get bars for a symbol/timeframe in a time range.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USD")
            timeframe: Bar timeframe (e.g., "1m", "5m", "1h")
            start: Start timestamp (inclusive)
            end: End timestamp (inclusive)
            
        Returns:
            List of Bar objects sorted by timestamp ascending
        """
        async with self._session_factory() as session:
            stmt = (
                select(BarRecord)
                .where(
                    BarRecord.symbol == symbol,
                    BarRecord.timeframe == timeframe,
                    BarRecord.timestamp >= start,
                    BarRecord.timestamp <= end,
                )
                .order_by(BarRecord.timestamp)
            )

            result = await session.execute(stmt)
            records = result.scalars().all()

            return [
                Bar(
                    symbol=rec.symbol,
                    timeframe=rec.timeframe,
                    timestamp=rec.timestamp,
                    open=rec.open,
                    high=rec.high,
                    low=rec.low,
                    close=rec.close,
                    volume=rec.volume,
                )
                for rec in records
            ]

    async def get_bar_count(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> int:
        """
        Count bars in a time range without fetching data.
        
        Useful for checking cache coverage before fetching from exchange.
        
        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            start: Start timestamp (inclusive)
            end: End timestamp (inclusive)
            
        Returns:
            Number of bars in range
        """
        async with self._session_factory() as session:
            stmt = (
                select(func.count())
                .select_from(BarRecord)
                .where(
                    BarRecord.symbol == symbol,
                    BarRecord.timeframe == timeframe,
                    BarRecord.timestamp >= start,
                    BarRecord.timestamp <= end,
                )
            )

            result = await session.execute(stmt)
            return result.scalar() or 0

    async def get_latest_bar(
        self,
        symbol: str,
        timeframe: str,
    ) -> Bar | None:
        """
        Get the most recent bar for a symbol/timeframe.
        
        Useful for determining where to start fetching new data.
        
        Args:
            symbol: Trading symbol
            timeframe: Bar timeframe
            
        Returns:
            Most recent Bar or None if no data exists
        """
        async with self._session_factory() as session:
            stmt = (
                select(BarRecord)
                .where(
                    BarRecord.symbol == symbol,
                    BarRecord.timeframe == timeframe,
                )
                .order_by(BarRecord.timestamp.desc())
                .limit(1)
            )

            result = await session.execute(stmt)
            rec = result.scalar_one_or_none()

            if rec is None:
                return None

            return Bar(
                symbol=rec.symbol,
                timeframe=rec.timeframe,
                timestamp=rec.timestamp,
                open=rec.open,
                high=rec.high,
                low=rec.low,
                close=rec.close,
                volume=rec.volume,
            )

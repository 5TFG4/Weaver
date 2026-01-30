"""
Database Session Management

Provides async session factory and connection utilities.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from src.config import DatabaseConfig


class Database:
    """
    Database connection manager.

    Handles engine creation, session management, and cleanup.
    """

    def __init__(self, config: "DatabaseConfig") -> None:
        """
        Initialize database with configuration.

        Args:
            config: Database configuration
        """
        self._config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine (creates if not exists)."""
        if self._engine is None:
            self._engine = create_async_engine(
                self._config.url,
                pool_size=self._config.pool_size,
                max_overflow=self._config.pool_overflow,
                echo=self._config.echo,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session as async context manager.

        Usage:
            async with db.session() as session:
                # use session
                await session.commit()
        """
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close the database engine."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global database instance (initialized by application startup)
_db: Database | None = None


def get_database() -> Database:
    """Get the global database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


def init_database(config: "DatabaseConfig") -> Database:
    """
    Initialize the global database instance.

    Args:
        config: Database configuration

    Returns:
        The initialized Database instance
    """
    global _db
    _db = Database(config)
    return _db


async def close_database() -> None:
    """Close the global database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None

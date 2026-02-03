"""
Integration Test Fixtures

Connects to the PostgreSQL database from docker-compose (db_dev).
Database URL is provided via DB_URL environment variable.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import DatabaseConfig
from src.walle.database import Database

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def _get_database_url() -> str | None:
    """Get database URL from environment."""
    return os.environ.get("DB_URL")


def _check_database_configured() -> bool:
    """Check if database is configured via environment."""
    return _get_database_url() is not None


@pytest.fixture(scope="module")
def database_url() -> str:
    """Get the database URL from environment."""
    url = _get_database_url()
    if not url:
        pytest.skip("DB_URL environment variable not set")
    return url


@pytest.fixture(scope="module")
def db_config(database_url: str) -> DatabaseConfig:
    """Create DatabaseConfig from environment."""
    return DatabaseConfig(url=database_url, pool_size=2, pool_overflow=5, echo=False)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def async_engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create an async engine for the test database."""
    engine = create_async_engine(database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def init_tables(database_url: str) -> None:
    """
    Initialize database tables using Alembic migrations.

    This ensures migrations are tested alongside the application code.
    """
    # Run alembic upgrade head
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Alembic migration failed: {result.stderr}")


@pytest_asyncio.fixture
async def database(
    db_config: DatabaseConfig, init_tables: None
) -> AsyncGenerator[Database, None]:
    """
    Create a Database instance connected to db_dev.

    Each test gets a fresh Database instance but shares the same tables.
    """
    db = Database(db_config)
    yield db
    await db.close()


@pytest_asyncio.fixture
async def clean_tables(database: Database) -> AsyncGenerator[None, None]:
    """
    Clean all tables before and after test.

    Use this fixture when tests need completely empty tables.
    """
    async with database.session() as sess:
        # Clean before test
        await sess.execute(text("TRUNCATE TABLE outbox RESTART IDENTITY CASCADE"))
        await sess.execute(text("TRUNCATE TABLE consumer_offsets CASCADE"))
        await sess.execute(text("TRUNCATE TABLE veda_orders CASCADE"))
        await sess.execute(text("TRUNCATE TABLE bars RESTART IDENTITY CASCADE"))
        await sess.commit()

    yield

    async with database.session() as sess:
        # Clean after test
        await sess.execute(text("TRUNCATE TABLE outbox RESTART IDENTITY CASCADE"))
        await sess.execute(text("TRUNCATE TABLE consumer_offsets CASCADE"))
        await sess.execute(text("TRUNCATE TABLE veda_orders CASCADE"))
        await sess.execute(text("TRUNCATE TABLE bars RESTART IDENTITY CASCADE"))
        await sess.commit()


@pytest_asyncio.fixture
async def db_session(
    async_engine: "AsyncEngine", init_tables: None
) -> AsyncGenerator["AsyncSession", None]:
    """
    Provide an AsyncSession for integration tests.
    
    Each test gets a fresh session with automatic rollback.
    This fixture can be used in any test file that needs database access.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()
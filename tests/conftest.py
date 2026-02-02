"""
Weaver Test Configuration

This module contains shared pytest fixtures and configuration used across all tests.
Fixtures are organized by scope and purpose.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generator
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the entire test session.
    
    This is needed for session-scoped async fixtures.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Time Fixtures
# =============================================================================

@pytest.fixture
def frozen_time() -> datetime:
    """
    A fixed point in time for deterministic tests.
    
    Default: 2024-01-15 09:30:00 UTC (market open)
    """
    return datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def market_open_time() -> datetime:
    """US market open time (9:30 AM ET = 14:30 UTC in winter)."""
    return datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def market_close_time() -> datetime:
    """US market close time (4:00 PM ET = 21:00 UTC in winter)."""
    return datetime(2024, 1, 15, 21, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# ID Generation Fixtures
# =============================================================================

@pytest.fixture
def sample_run_id() -> str:
    """A deterministic run ID for tests."""
    return "run-00000000-0000-0000-0000-000000000001"


@pytest.fixture
def sample_order_id() -> str:
    """A deterministic order ID for tests."""
    return "order-00000000-0000-0000-0000-000000000001"


@pytest.fixture
def sample_corr_id() -> str:
    """A deterministic correlation ID for tests."""
    return "corr-00000000-0000-0000-0000-000000000001"


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def test_config() -> dict[str, Any]:
    """
    Test configuration that mirrors production config structure.
    
    Use this for testing config parsing and validation.
    """
    return {
        "database": {
            "url": "postgresql+asyncpg://test:test@localhost:5432/weaver_test",
            "pool_size": 5,
            "echo": False,
        },
        "alpaca": {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "paper": True,
        },
        "clock": {
            "default_timeframe": "1m",
            "precision_ms": 50,
        },
    }


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_logger() -> MagicMock:
    """A mock logger for testing log calls."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


# =============================================================================
# Async Utility Fixtures
# =============================================================================

@pytest.fixture
def async_timeout() -> float:
    """Default timeout for async operations in tests (seconds)."""
    return 5.0


# =============================================================================
# Markers Registration
# =============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (may use containers)")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")


# =============================================================================
# Test Collection Hooks
# =============================================================================

def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """
    Automatically add markers based on test path.
    
    - tests/unit/* -> @pytest.mark.unit
    - tests/integration/* -> @pytest.mark.integration
    - tests/e2e/* -> @pytest.mark.e2e
    """
    for item in items:
        test_path = str(item.fspath)
        
        if "/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/e2e/" in test_path:
            item.add_marker(pytest.mark.e2e)


# =============================================================================
# Database Fixtures (Integration Tests)
# =============================================================================

import os
import subprocess
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


def _get_database_url() -> str | None:
    """Get database URL from environment."""
    return os.environ.get("DB_URL")


@pytest.fixture(scope="function")
def database_url() -> str:
    """Get the database URL from environment."""
    url = _get_database_url()
    if not url:
        pytest.skip("DB_URL environment variable not set")
    return url


@pytest_asyncio.fixture(scope="function")
async def async_engine(database_url: str) -> AsyncGenerator[Any, None]:
    """Create an async engine for the test database."""
    engine = create_async_engine(database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
def init_tables(database_url: str) -> None:
    """
    Initialize database tables using Alembic migrations.

    This ensures migrations are tested alongside the application code.
    """
    project_root = os.environ.get("PROJECT_ROOT", "/weaver")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Alembic migration failed: {result.stderr}")


@pytest_asyncio.fixture
async def db_session(
    async_engine: Any, init_tables: None
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an AsyncSession for integration tests.
    
    Each test gets a fresh session with clean tables.
    Used by tests marked @pytest.mark.integration.
    """
    from sqlalchemy import text
    
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        # Clean tables before test
        await session.execute(
            text("TRUNCATE TABLE veda_orders, outbox, consumer_offsets")
        )
        await session.commit()
        
        yield session
        
        # Rollback any uncommitted changes and clean up
        await session.rollback()

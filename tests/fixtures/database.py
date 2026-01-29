"""
Database Test Fixtures

Provides fixtures for database testing:
- Test database creation/teardown using testcontainers
- Session management
- Transaction rollback for test isolation
"""
from __future__ import annotations
import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class TestDatabaseConfig:
    """Configuration for test database."""
    
    host: str = "localhost"
    port: int = 5432
    user: str = "test"
    password: str = "test"
    database: str = "weaver_test"
    
    @property
    def url(self) -> str:
        """Get async database URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
    
    @property
    def sync_url(self) -> str:
        """Get sync database URL (for Alembic)."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class MockDatabaseSession:
    """
    A mock database session for unit tests.
    
    Use this when you don't need a real database but want to verify
    that database calls are made correctly.
    """
    
    def __init__(self) -> None:
        self._committed = False
        self._rolled_back = False
        self._added: list[Any] = []
        self._queries: list[str] = []
    
    @property
    def committed(self) -> bool:
        """Check if commit was called."""
        return self._committed
    
    @property
    def rolled_back(self) -> bool:
        """Check if rollback was called."""
        return self._rolled_back
    
    @property
    def added_objects(self) -> list[Any]:
        """Get all objects added to the session."""
        return self._added.copy()
    
    def add(self, obj: Any) -> None:
        """Mock add operation."""
        self._added.append(obj)
    
    async def commit(self) -> None:
        """Mock commit operation."""
        self._committed = True
    
    async def rollback(self) -> None:
        """Mock rollback operation."""
        self._rolled_back = True
    
    async def execute(self, query: Any) -> "MockResult":
        """Mock execute operation."""
        self._queries.append(str(query))
        return MockResult()
    
    async def __aenter__(self) -> "MockDatabaseSession":
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        pass


class MockResult:
    """Mock result from database query."""
    
    def __init__(self, rows: list[Any] | None = None) -> None:
        self._rows = rows or []
    
    def scalars(self) -> "MockResult":
        return self
    
    def all(self) -> list[Any]:
        return self._rows
    
    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None
    
    def one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def test_db_config() -> TestDatabaseConfig:
    """Provide test database configuration."""
    return TestDatabaseConfig()


@pytest.fixture
def mock_db_session() -> MockDatabaseSession:
    """Provide a mock database session for unit tests."""
    return MockDatabaseSession()


# =============================================================================
# Integration Test Support (using testcontainers)
# =============================================================================

# Note: The actual testcontainers integration will be set up when we
# implement the real database layer. For now, we provide the mock versions.

async def create_test_tables(engine: Any) -> None:
    """
    Create all tables in the test database.
    
    This will be implemented when we have the actual models.
    """
    # TODO: Import Base from walle.models and create tables
    pass


async def drop_test_tables(engine: Any) -> None:
    """
    Drop all tables in the test database.
    
    This will be implemented when we have the actual models.
    """
    # TODO: Import Base from walle.models and drop tables
    pass

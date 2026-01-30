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

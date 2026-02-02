"""
GLaDOS Unit Test Fixtures

Provides shared fixtures for GLaDOS API testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from fastapi import FastAPI

    from src.config import WeaverConfig


@pytest.fixture
def test_settings() -> WeaverConfig:
    """Get test configuration."""
    from src.config import get_test_config

    return get_test_config()


@pytest.fixture
def app(test_settings: WeaverConfig) -> FastAPI:
    """Create test application with fresh state."""
    from src.glados.app import create_app
    from src.glados.routes.candles import reset_market_data_service
    from src.glados.routes.orders import reset_order_service
    from src.glados.routes.runs import reset_run_manager
    from src.glados.routes.sse import reset_broadcaster

    # Reset shared state before each test
    reset_run_manager()
    reset_broadcaster()
    reset_order_service()
    reset_market_data_service()

    return create_app(settings=test_settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Synchronous test client for HTTP requests."""
    return TestClient(app)

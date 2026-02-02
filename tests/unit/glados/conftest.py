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

    # Each call to create_app() creates fresh services in app.state
    # No need to reset module-level singletons anymore
    return create_app(settings=test_settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Synchronous test client for HTTP requests.
    
    Uses context manager to trigger app lifespan events,
    which initializes services in app.state.
    """
    with TestClient(app) as client:
        yield client

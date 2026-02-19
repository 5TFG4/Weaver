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
    Replaces RunManager with a fully-wired version for route testing.
    """
    from tests.factories.runs import create_run_manager_with_deps

    with TestClient(app) as client:
        # Replace RunManager with one that has all deps mocked,
        # so routes like POST /runs/{id}/start actually work.
        app.state.run_manager = create_run_manager_with_deps(
            event_log=getattr(app.state, "event_log", None),
        )
        # Ensure VedaService is None by default in unit tests.
        # Tests that need VedaService inject it explicitly via app.state.
        app.state.veda_service = None
        yield client

"""
GLaDOS Unit Test Fixtures

Provides shared fixtures for GLaDOS API testing.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
def client(app: FastAPI) -> Generator[TestClient]:
    """Synchronous test client for HTTP requests.

    Uses context manager to trigger app lifespan events,
    which initializes services in app.state.
    Replaces RunManager with a fully-wired version for route testing.
    """
    from tests.factories.runs import create_run_manager_with_deps

    with TestClient(app) as client:
        security = app.state.settings.security
        client.headers[security.api_key_header] = security.api_token

        # Replace RunManager with one that has all deps mocked,
        # so routes like POST /runs/{id}/start actually work.
        # Always use mock event_log to prevent unit tests from writing
        # run.Created events to the real outbox table in db_dev.
        app.state.run_manager = create_run_manager_with_deps()
        # Ensure VedaService is None by default in unit tests.
        # Tests that need VedaService inject it explicitly via app.state.
        app.state.veda_service = None

        # M13: Seed result_repository for results endpoint tests
        from unittest.mock import AsyncMock

        mock_result_repo = AsyncMock()
        mock_result_repo.save = AsyncMock()
        mock_result_repo.get_by_run_id = AsyncMock(return_value=None)
        app.state.result_repository = mock_result_repo

        mock_fill_repo = AsyncMock()
        mock_fill_repo.list_by_run_id = AsyncMock(return_value=[])
        app.state.fill_repository = mock_fill_repo

        yield client

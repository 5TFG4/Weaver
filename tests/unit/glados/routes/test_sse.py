"""
Tests for SSE Endpoint

MVP-3: SSE Real-time Push
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestSSEStreamEndpoint:
    """Tests for GET /api/v1/events/stream."""

    def test_endpoint_exists(self, client: TestClient) -> None:
        """SSE endpoint should be registered."""
        from src.glados.app import create_app

        app = create_app()
        routes = [getattr(r, "path", None) for r in app.routes]

        assert "/api/v1/events/stream" in routes

    def test_broadcaster_in_app_state(self, app: FastAPI) -> None:
        """Broadcaster should be available in app.state after lifespan."""
        from src.glados.sse_broadcaster import SSEBroadcaster

        # Use TestClient to trigger lifespan
        with TestClient(app):
            assert hasattr(app.state, "broadcaster")
            assert isinstance(app.state.broadcaster, SSEBroadcaster)

    def test_each_app_gets_fresh_broadcaster(self) -> None:
        """Each create_app() should create a fresh broadcaster."""
        from src.config import get_test_config
        from src.glados.app import create_app

        app1 = create_app(settings=get_test_config())
        app2 = create_app(settings=get_test_config())

        with TestClient(app1), TestClient(app2):
            # Each app has its own broadcaster instance
            assert app1.state.broadcaster is not app2.state.broadcaster

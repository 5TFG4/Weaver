"""
Tests for SSE Endpoint

MVP-3: SSE Real-time Push
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    pass


class TestSSEStreamEndpoint:
    """Tests for GET /api/v1/events/stream."""

    def test_endpoint_exists(self, client: TestClient) -> None:
        """SSE endpoint should be registered."""
        from src.glados.app import create_app

        app = create_app()
        routes = [r.path for r in app.routes]

        assert "/api/v1/events/stream" in routes

    def test_broadcaster_is_accessible(self) -> None:
        """get_broadcaster() should return SSEBroadcaster instance."""
        from src.glados.routes.sse import get_broadcaster
        from src.glados.sse_broadcaster import SSEBroadcaster

        broadcaster = get_broadcaster()

        assert isinstance(broadcaster, SSEBroadcaster)

    def test_broadcaster_singleton(self) -> None:
        """get_broadcaster() should return same instance."""
        from src.glados.routes.sse import get_broadcaster, reset_broadcaster

        reset_broadcaster()
        b1 = get_broadcaster()
        b2 = get_broadcaster()

        assert b1 is b2

    def test_reset_broadcaster(self) -> None:
        """reset_broadcaster() should create new instance."""
        from src.glados.routes.sse import get_broadcaster, reset_broadcaster

        b1 = get_broadcaster()
        reset_broadcaster()
        b2 = get_broadcaster()

        assert b1 is not b2

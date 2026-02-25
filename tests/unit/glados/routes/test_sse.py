"""
Tests for SSE Endpoint

MVP-3: SSE Real-time Push
TDD: Write tests first, then implement.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.glados.routes.sse import _should_include_event
from src.glados.sse_broadcaster import ServerSentEvent


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


class TestSSERunIdFiltering:
    """N-06/D-5: SSE run_id query param filtering."""

    def test_filter_includes_matching_run_id(self) -> None:
        """Event with matching run_id should be included."""
        event = ServerSentEvent(
            id="1",
            event="run.Started",
            data=json.dumps({"run_id": "run-123", "status": "running"}),
        )
        assert _should_include_event(event, run_id="run-123") is True

    def test_filter_excludes_non_matching_run_id(self) -> None:
        """Event with different run_id should be excluded."""
        event = ServerSentEvent(
            id="2",
            event="run.Started",
            data=json.dumps({"run_id": "run-456", "status": "running"}),
        )
        assert _should_include_event(event, run_id="run-123") is False

    def test_no_filter_includes_all_events(self) -> None:
        """Without run_id filter, all events pass through."""
        event = ServerSentEvent(
            id="3",
            event="run.Started",
            data=json.dumps({"run_id": "run-999", "status": "running"}),
        )
        assert _should_include_event(event, run_id=None) is True

    def test_filter_includes_event_without_run_id_field(self) -> None:
        """Events without run_id in data should pass through (e.g., system events)."""
        event = ServerSentEvent(
            id="4",
            event="system.heartbeat",
            data=json.dumps({"ts": "2024-01-01"}),
        )
        assert _should_include_event(event, run_id="run-123") is True

    def test_filter_handles_malformed_json(self) -> None:
        """Malformed JSON data should pass through (don't drop events due to parse errors)."""
        event = ServerSentEvent(
            id="5",
            event="unknown",
            data="not-json",
        )
        assert _should_include_event(event, run_id="run-123") is True

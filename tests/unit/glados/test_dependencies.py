"""
Unit tests for GLaDOS dependency injection.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.glados.dependencies import (
    get_broadcaster,
    get_event_log,
    get_market_data_service,
    get_order_service,
    get_run_manager,
    get_settings,
    get_veda_service,
)


class MockRequest:
    """Mock FastAPI Request with app.state access."""

    def __init__(self, app: MagicMock) -> None:
        self.app = app


class TestGetSettings:
    """Tests for get_settings dependency."""

    def test_returns_settings_from_app_state(self) -> None:
        """get_settings returns app.state.settings."""
        app = MagicMock()
        app.state.settings = MagicMock(name="settings")
        request = MockRequest(app)

        result = get_settings(request)

        assert result is app.state.settings


class TestGetRunManager:
    """Tests for get_run_manager dependency."""

    def test_returns_run_manager_from_app_state(self) -> None:
        """get_run_manager returns app.state.run_manager."""
        app = MagicMock()
        app.state.run_manager = MagicMock(name="run_manager")
        request = MockRequest(app)

        result = get_run_manager(request)

        assert result is app.state.run_manager


class TestGetOrderService:
    """Tests for get_order_service dependency."""

    def test_returns_order_service_from_app_state(self) -> None:
        """get_order_service returns app.state.order_service."""
        app = MagicMock()
        app.state.order_service = MagicMock(name="order_service")
        request = MockRequest(app)

        result = get_order_service(request)

        assert result is app.state.order_service


class TestGetMarketDataService:
    """Tests for get_market_data_service dependency."""

    def test_returns_market_data_service_from_app_state(self) -> None:
        """get_market_data_service returns app.state.market_data_service."""
        app = MagicMock()
        app.state.market_data_service = MagicMock(name="market_data_service")
        request = MockRequest(app)

        result = get_market_data_service(request)

        assert result is app.state.market_data_service


class TestGetBroadcaster:
    """Tests for get_broadcaster dependency."""

    def test_returns_broadcaster_from_app_state(self) -> None:
        """get_broadcaster returns app.state.broadcaster."""
        app = MagicMock()
        app.state.broadcaster = MagicMock(name="broadcaster")
        request = MockRequest(app)

        result = get_broadcaster(request)

        assert result is app.state.broadcaster


class TestGetEventLog:
    """Tests for get_event_log dependency."""

    def test_returns_event_log_from_app_state(self) -> None:
        """get_event_log returns app.state.event_log when set."""
        app = MagicMock()
        app.state.event_log = MagicMock(name="event_log")
        request = MockRequest(app)

        result = get_event_log(request)

        assert result is app.state.event_log

    def test_returns_none_when_not_configured(self) -> None:
        """get_event_log returns None when event_log not in state."""
        app = MagicMock(spec=["state"])
        app.state = MagicMock(spec=[])  # No event_log attribute
        request = MockRequest(app)

        result = get_event_log(request)

        assert result is None


class TestGetVedaService:
    """Tests for get_veda_service dependency."""

    def test_returns_veda_service_from_app_state(self) -> None:
        """get_veda_service returns app.state.veda_service when set."""
        app = MagicMock()
        app.state.veda_service = MagicMock(name="veda_service")
        request = MockRequest(app)

        result = get_veda_service(request)

        assert result is app.state.veda_service

    def test_returns_none_when_not_configured(self) -> None:
        """get_veda_service returns None when veda_service not in state."""
        app = MagicMock(spec=["state"])
        app.state = MagicMock(spec=[])  # No veda_service attribute
        request = MockRequest(app)

        result = get_veda_service(request)

        assert result is None

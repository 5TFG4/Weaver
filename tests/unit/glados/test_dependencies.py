"""
Unit tests for GLaDOS dependency injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from fastapi import Request

from src.glados.dependencies import (
    get_broadcaster,
    get_domain_router,
    get_event_log,
    get_market_data_service,
    get_order_service,
    get_run_manager,
    get_settings,
    get_veda_service,
)


def create_mock_request(app: MagicMock) -> "Request":
    """Create a mock request with app.state access."""
    request = MagicMock()
    request.app = app
    return cast("Request", request)


class TestGetSettings:
    """Tests for get_settings dependency."""

    def test_returns_settings_from_app_state(self) -> None:
        """get_settings returns app.state.settings."""
        app = MagicMock()
        app.state.settings = MagicMock(name="settings")
        request = create_mock_request(app)

        result = get_settings(request)

        assert result is app.state.settings


class TestGetRunManager:
    """Tests for get_run_manager dependency."""

    def test_returns_run_manager_from_app_state(self) -> None:
        """get_run_manager returns app.state.run_manager."""
        app = MagicMock()
        app.state.run_manager = MagicMock(name="run_manager")
        request = create_mock_request(app)

        result = get_run_manager(request)

        assert result is app.state.run_manager


class TestGetOrderService:
    """Tests for get_order_service dependency."""

    def test_returns_order_service_from_app_state(self) -> None:
        """get_order_service returns app.state.order_service."""
        app = MagicMock()
        app.state.order_service = MagicMock(name="order_service")
        request = create_mock_request(app)

        result = get_order_service(request)

        assert result is app.state.order_service


class TestGetMarketDataService:
    """Tests for get_market_data_service dependency."""

    def test_returns_market_data_service_from_app_state(self) -> None:
        """get_market_data_service returns app.state.market_data_service."""
        app = MagicMock()
        app.state.market_data_service = MagicMock(name="market_data_service")
        request = create_mock_request(app)

        result = get_market_data_service(request)

        assert result is app.state.market_data_service


class TestGetBroadcaster:
    """Tests for get_broadcaster dependency."""

    def test_returns_broadcaster_from_app_state(self) -> None:
        """get_broadcaster returns app.state.broadcaster."""
        app = MagicMock()
        app.state.broadcaster = MagicMock(name="broadcaster")
        request = create_mock_request(app)

        result = get_broadcaster(request)

        assert result is app.state.broadcaster


class TestGetEventLog:
    """Tests for get_event_log dependency."""

    def test_returns_event_log_from_app_state(self) -> None:
        """get_event_log returns app.state.event_log when set."""
        app = MagicMock()
        app.state.event_log = MagicMock(name="event_log")
        request = create_mock_request(app)

        result = get_event_log(request)

        assert result is app.state.event_log

    def test_returns_none_when_not_configured(self) -> None:
        """get_event_log returns None when event_log not in state."""
        app = MagicMock(spec=["state"])
        app.state = MagicMock(spec=[])  # No event_log attribute
        request = create_mock_request(app)

        result = get_event_log(request)

        assert result is None


class TestGetVedaService:
    """Tests for get_veda_service dependency."""

    def test_returns_veda_service_from_app_state(self) -> None:
        """get_veda_service returns app.state.veda_service when set."""
        app = MagicMock()
        app.state.veda_service = MagicMock(name="veda_service")
        request = create_mock_request(app)

        result = get_veda_service(request)

        assert result is app.state.veda_service

    def test_returns_none_when_not_configured(self) -> None:
        """get_veda_service returns None when veda_service not in state."""
        app = MagicMock(spec=["state"])
        app.state = MagicMock(spec=[])  # No veda_service attribute
        request = create_mock_request(app)

        result = get_veda_service(request)

        assert result is None


class TestGetDomainRouter:
    """Tests for get_domain_router dependency."""

    def test_returns_domain_router_from_app_state(self) -> None:
        """get_domain_router returns app.state.domain_router when set."""
        app = MagicMock()
        app.state.domain_router = MagicMock(name="domain_router")
        request = create_mock_request(app)

        result = get_domain_router(request)

        assert result is app.state.domain_router

    def test_returns_none_when_not_configured(self) -> None:
        """get_domain_router returns None when domain_router not in state."""
        app = MagicMock(spec=["state"])
        app.state = MagicMock(spec=[])
        request = create_mock_request(app)

        result = get_domain_router(request)

        assert result is None

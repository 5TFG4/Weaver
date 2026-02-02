"""
Tests for GLaDOS Application Factory

MVP-1: Bootable Skeleton
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI

if TYPE_CHECKING:
    from src.config import WeaverConfig


class TestCreateApp:
    """Tests for create_app() factory function."""

    def test_returns_fastapi_instance(self, test_settings: WeaverConfig) -> None:
        """create_app() should return a FastAPI instance."""
        from src.glados.app import create_app

        app = create_app(settings=test_settings)

        assert isinstance(app, FastAPI)

    def test_app_has_configured_title(self, test_settings: WeaverConfig) -> None:
        """App should have title 'Weaver API'."""
        from src.glados.app import create_app

        app = create_app(settings=test_settings)

        assert app.title == "Weaver API"

    def test_app_has_configured_version(self, test_settings: WeaverConfig) -> None:
        """App should have version '0.1.0'."""
        from src.glados.app import create_app

        app = create_app(settings=test_settings)

        assert app.version == "0.1.0"

    def test_accepts_custom_settings(self, test_settings: WeaverConfig) -> None:
        """create_app() should store settings in app.state."""
        from src.glados.app import create_app

        app = create_app(settings=test_settings)

        assert app.state.settings == test_settings

    def test_default_settings_when_none_provided(self) -> None:
        """create_app() should use default settings when none provided."""
        from src.glados.app import create_app

        app = create_app()

        assert app.state.settings is not None

    def test_healthz_route_registered(self, test_settings: WeaverConfig) -> None:
        """App should have /healthz route registered."""
        from src.glados.app import create_app

        app = create_app(settings=test_settings)
        routes = [route.path for route in app.routes]

        assert "/healthz" in routes

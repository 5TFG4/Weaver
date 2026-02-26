"""
Tests for GLaDOS Application Factory

MVP-1: Bootable Skeleton
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        """App should have /api/v1/healthz route registered."""
        from src.glados.app import create_app

        app = create_app(settings=test_settings)
        routes = [getattr(route, "path", None) for route in app.routes]

        assert "/api/v1/healthz" in routes


class TestAppLifespanWiring:
    """Tests for runtime wiring completed during app lifespan startup."""

    def test_lifespan_wires_domain_router(self, test_settings: WeaverConfig) -> None:
        """DomainRouter should be created and stored in app.state during startup."""
        import os

        from fastapi.testclient import TestClient

        from src.glados.app import create_app
        from src.glados.services.domain_router import DomainRouter

        app = create_app(settings=test_settings)

        old_db_url = os.environ.pop("DB_URL", None)
        try:
            with TestClient(app):
                assert hasattr(app.state, "domain_router")
                assert isinstance(app.state.domain_router, DomainRouter)
        finally:
            if old_db_url is not None:
                os.environ["DB_URL"] = old_db_url

    def test_lifespan_injects_strategy_loader_into_run_manager(
        self,
        test_settings: WeaverConfig,
    ) -> None:
        """RunManager should have strategy_loader configured after startup."""
        import os

        from fastapi.testclient import TestClient

        from src.glados.app import create_app

        app = create_app(settings=test_settings)

        old_db_url = os.environ.pop("DB_URL", None)
        try:
            with TestClient(app):
                run_manager = app.state.run_manager
                assert run_manager._strategy_loader is not None
        finally:
            if old_db_url is not None:
                os.environ["DB_URL"] = old_db_url

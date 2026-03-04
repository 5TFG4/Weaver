"""Authentication middleware tests for /api/v1 routes and SSE stream."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.config import SecurityConfig, WeaverConfig, get_test_config
from src.glados.app import create_app


def _make_auth_enabled_settings() -> WeaverConfig:
    base = get_test_config()
    return base.model_copy(
        update={
            "security": SecurityConfig(
                auth_required=True,
                api_token="secret-token",
                api_key_header="X-API-Key",
            )
        }
    )


class TestAuthMiddleware:
    """SECURITY: API and SSE endpoints require credentials when enabled."""

    def test_api_rejects_unauthenticated_requests(self) -> None:
        app = create_app(settings=_make_auth_enabled_settings())
        with TestClient(app) as client:
            response = client.get("/api/v1/healthz")
            assert response.status_code == 401

    def test_api_accepts_x_api_key(self) -> None:
        app = create_app(settings=_make_auth_enabled_settings())
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/healthz",
                headers={"X-API-Key": "secret-token"},
            )
            assert response.status_code == 200

    def test_api_accepts_bearer_token(self) -> None:
        app = create_app(settings=_make_auth_enabled_settings())
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/healthz",
                headers={"Authorization": "Bearer secret-token"},
            )
            assert response.status_code == 200

    def test_sse_stream_rejects_unauthenticated_requests(self) -> None:
        app = create_app(settings=_make_auth_enabled_settings())
        with TestClient(app) as client:
            response = client.get("/api/v1/events/stream")
            assert response.status_code == 401


def test_test_config_auth_enabled_by_default() -> None:
    """Guardrail: test config must keep auth enabled to mirror production path."""
    settings = get_test_config()
    assert settings.security.auth_required is True
    assert settings.security.api_token

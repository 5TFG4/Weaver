"""
Test MVP-6: Production Polish

Tests for application lifecycle, middleware, and production-ready features.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.glados.app import create_app


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    """Fresh test client with a new app instance."""
    app = create_app()
    with TestClient(app) as client:
        yield client


# =============================================================================
# Test: OpenAPI / API Docs
# =============================================================================


class TestOpenAPIDocs:
    """Tests for OpenAPI documentation availability."""

    def test_openapi_json_available(self, client: TestClient) -> None:
        """GET /openapi.json should return 200."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_has_info(self, client: TestClient) -> None:
        """OpenAPI spec should contain info section."""
        response = client.get("/openapi.json")
        data = response.json()
        assert "info" in data
        assert data["info"]["title"] == "Weaver API"

    def test_openapi_has_paths(self, client: TestClient) -> None:
        """OpenAPI spec should list all API paths."""
        response = client.get("/openapi.json")
        data = response.json()
        assert "paths" in data
        # Key endpoints should be documented
        assert "/api/v1/healthz" in data["paths"]
        assert "/api/v1/runs" in data["paths"]

    def test_docs_ui_available(self, client: TestClient) -> None:
        """GET /docs should return 200 (Swagger UI)."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client: TestClient) -> None:
        """GET /redoc should return 200 (ReDoc)."""
        response = client.get("/redoc")
        assert response.status_code == 200


# =============================================================================
# Test: CORS Middleware
# =============================================================================


class TestCORSMiddleware:
    """Tests for CORS configuration."""

    def test_options_preflight_returns_cors_headers(self, client: TestClient) -> None:
        """OPTIONS request should return CORS headers."""
        response = client.options(
            "/api/v1/runs",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should allow preflight
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_localhost_origin(self, client: TestClient) -> None:
        """CORS should allow localhost origins for development."""
        response = client.get(
            "/api/v1/healthz",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling and structured responses."""

    def test_404_returns_json_error(self, client: TestClient) -> None:
        """404 errors should return JSON with error details."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_validation_error_returns_422(self, client: TestClient) -> None:
        """Validation errors should return 422 with details."""
        response = client.post(
            "/api/v1/runs",
            json={"invalid": "data"},  # Missing required fields
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_validation_error_includes_field_info(self, client: TestClient) -> None:
        """Validation error details should include field names."""
        response = client.post(
            "/api/v1/runs",
            json={"strategy_id": "test"},  # Missing mode and symbols
        )
        assert response.status_code == 422
        data = response.json()
        # FastAPI includes field location in validation errors
        assert any("mode" in str(err) for err in data["detail"])


# =============================================================================
# Test: Startup/Shutdown Lifecycle
# =============================================================================


class TestLifecycleEvents:
    """Tests for application lifecycle handling."""

    def test_app_has_lifespan_context(self) -> None:
        """App should have lifespan context manager defined."""
        app = create_app()
        # FastAPI 0.109+ uses lifespan parameter
        assert app.router.lifespan_context is not None

    def test_app_starts_successfully(self, client: TestClient) -> None:
        """App should start without errors."""
        # TestClient handles startup automatically
        response = client.get("/api/v1/healthz")
        assert response.status_code == 200

    def test_app_shutdown_completes(self) -> None:
        """App shutdown should complete without errors."""
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/api/v1/healthz")
            assert response.status_code == 200
        # If we get here, shutdown completed successfully

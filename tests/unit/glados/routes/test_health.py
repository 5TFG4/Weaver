"""
Tests for Health Endpoint

MVP-1: Bootable Skeleton
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /healthz endpoint."""

    def test_returns_200_ok(self, client: TestClient) -> None:
        """GET /healthz should return HTTP 200."""
        response = client.get("/healthz")

        assert response.status_code == 200

    def test_returns_status_ok(self, client: TestClient) -> None:
        """Response should contain status: ok."""
        response = client.get("/healthz")
        data = response.json()

        assert data["status"] == "ok"

    def test_returns_version(self, client: TestClient) -> None:
        """Response should contain version string."""
        response = client.get("/healthz")
        data = response.json()

        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_response_matches_schema(self, client: TestClient) -> None:
        """Response should match HealthResponse schema."""
        response = client.get("/healthz")
        data = response.json()

        # Should have exactly these fields
        assert set(data.keys()) == {"status", "version"}
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)

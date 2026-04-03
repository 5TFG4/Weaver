"""Tests for Strategies Endpoint — GET /api/v1/strategies."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestListStrategiesEndpoint:
    """Tests for GET /api/v1/strategies."""

    def test_returns_200(self, client: TestClient) -> None:
        """GET /strategies should return HTTP 200."""
        response = client.get("/api/v1/strategies")
        assert response.status_code == 200

    def test_returns_all_strategies(self, client: TestClient) -> None:
        """GET /strategies should return all discovered strategies."""
        response = client.get("/api/v1/strategies")
        data = response.json()
        assert len(data) >= 2  # sample + sma-crossover at minimum

    def test_strategy_response_includes_config_schema(self, client: TestClient) -> None:
        """SMA strategy should include config_schema with properties."""
        response = client.get("/api/v1/strategies")
        data = response.json()
        sma = next(s for s in data if s["id"] == "sma-crossover")
        assert sma["config_schema"]["type"] == "object"
        assert "symbols" in sma["config_schema"]["properties"]

    def test_strategy_response_fields(self, client: TestClient) -> None:
        """Each strategy item should have the expected fields."""
        response = client.get("/api/v1/strategies")
        data = response.json()
        item = data[0]
        assert set(item.keys()) >= {"id", "name", "version", "description", "config_schema"}

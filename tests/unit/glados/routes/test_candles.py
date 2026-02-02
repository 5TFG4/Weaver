"""
Tests for Candles Endpoint

MVP-5: Candle Queries
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestCandlesEndpoint:
    """Tests for GET /api/v1/candles."""

    def test_returns_200(self, client: TestClient) -> None:
        """GET /candles should return HTTP 200."""
        response = client.get("/api/v1/candles?symbol=BTC/USD&timeframe=1m")

        assert response.status_code == 200

    def test_requires_symbol_param(self, client: TestClient) -> None:
        """GET /candles without symbol should return 422."""
        response = client.get("/api/v1/candles?timeframe=1m")

        assert response.status_code == 422

    def test_requires_timeframe_param(self, client: TestClient) -> None:
        """GET /candles without timeframe should return 422."""
        response = client.get("/api/v1/candles?symbol=BTC/USD")

        assert response.status_code == 422

    def test_returns_items_with_ohlcv(self, client: TestClient) -> None:
        """Response should contain OHLCV data."""
        response = client.get("/api/v1/candles?symbol=BTC/USD&timeframe=1m")
        data = response.json()

        assert "items" in data
        assert len(data["items"]) > 0
        candle = data["items"][0]
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        assert "volume" in candle

    def test_returns_symbol_and_timeframe(self, client: TestClient) -> None:
        """Response should echo symbol and timeframe."""
        response = client.get("/api/v1/candles?symbol=BTC/USD&timeframe=1m")
        data = response.json()

        assert data["symbol"] == "BTC/USD"
        assert data["timeframe"] == "1m"

    def test_accepts_limit_param(self, client: TestClient) -> None:
        """GET /candles should accept limit parameter."""
        response = client.get("/api/v1/candles?symbol=BTC/USD&timeframe=1m&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5

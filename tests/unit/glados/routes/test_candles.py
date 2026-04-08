"""
Tests for Candles Endpoint

MVP-5: Candle Queries
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.veda.models import Bar


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


def _make_bar(timestamp: datetime) -> Bar:
    """Create a deterministic Veda bar."""
    return Bar(
        symbol="AAPL",
        timestamp=timestamp,
        open=Decimal("100.00"),
        high=Decimal("101.00"),
        low=Decimal("99.50"),
        close=Decimal("100.50"),
        volume=Decimal("1234.00"),
        trade_count=25,
        vwap=Decimal("100.20"),
    )


class TestCandlesVedaPath:
    """M14: /candles should use real bars when VedaService is available."""

    def test_uses_veda_service_when_available(self, client: TestClient) -> None:
        """Explicit ranges should route to VedaService.get_bars()."""
        mock_veda = AsyncMock()
        start = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)
        end = datetime(2024, 1, 15, 14, 34, tzinfo=UTC)
        mock_veda.get_bars.return_value = [_make_bar(start)]
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        response = client.get(
            "/api/v1/candles?symbol=AAPL&timeframe=1m"
            "&start=2024-01-15T14:30:00Z&end=2024-01-15T14:34:00Z&limit=5"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["symbol"] == "AAPL"
        assert data["items"][0]["close"] == "100.50"
        mock_veda.get_bars.assert_awaited_once_with(
            symbol="AAPL",
            timeframe="1m",
            start=start,
            end=end,
            limit=5,
        )

    def test_derives_deterministic_window_when_start_omitted(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No-start requests should derive a stable real-data window."""
        from src.glados.routes import candles as candles_route

        fixed_now = datetime(2024, 1, 15, 14, 34, 27, tzinfo=UTC)
        monkeypatch.setattr(candles_route, "_utc_now", lambda: fixed_now)

        mock_veda = AsyncMock()
        mock_veda.get_bars.return_value = []
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        response = client.get("/api/v1/candles?symbol=AAPL&timeframe=1m&limit=5")

        assert response.status_code == 200
        mock_veda.get_bars.assert_awaited_once_with(
            symbol="AAPL",
            timeframe="1m",
            start=datetime(2024, 1, 15, 14, 30, tzinfo=UTC),
            end=datetime(2024, 1, 15, 14, 34, tzinfo=UTC),
            limit=5,
        )

    def test_falls_back_to_mock_when_veda_is_absent(self, client: TestClient) -> None:
        """Existing mock path remains available without VedaService."""
        response = client.get("/api/v1/candles?symbol=BTC/USD&timeframe=1m&limit=3")

        assert response.status_code == 200
        assert len(response.json()["items"]) <= 3

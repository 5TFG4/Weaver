"""
Tests for Market Data Service

MVP-5: Candle Queries
TDD: Write tests first, then implement.
"""

from __future__ import annotations

import pytest


class TestMarketDataServiceGetCandles:
    """Tests for MarketDataService.get_candles()."""

    async def test_returns_candle_list(self) -> None:
        """get_candles() should return list of candles."""
        from src.glados.services.market_data_service import MockMarketDataService

        service = MockMarketDataService()

        candles = await service.get_candles("BTC/USD", "1m")

        assert isinstance(candles, list)
        assert len(candles) > 0

    async def test_candle_has_ohlcv_fields(self) -> None:
        """Each candle should have OHLCV fields."""
        from src.glados.services.market_data_service import MockMarketDataService

        service = MockMarketDataService()

        candles = await service.get_candles("BTC/USD", "1m")
        candle = candles[0]

        assert hasattr(candle, "open")
        assert hasattr(candle, "high")
        assert hasattr(candle, "low")
        assert hasattr(candle, "close")
        assert hasattr(candle, "volume")

    async def test_candle_has_timestamp(self) -> None:
        """Each candle should have timestamp."""
        from src.glados.services.market_data_service import MockMarketDataService

        service = MockMarketDataService()

        candles = await service.get_candles("BTC/USD", "1m")
        candle = candles[0]

        assert hasattr(candle, "timestamp")
        assert candle.timestamp is not None

    async def test_respects_limit(self) -> None:
        """get_candles() should respect limit parameter."""
        from src.glados.services.market_data_service import MockMarketDataService

        service = MockMarketDataService()

        candles = await service.get_candles("BTC/USD", "1m", limit=5)

        assert len(candles) <= 5

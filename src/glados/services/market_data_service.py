"""
Market Data Service

Provides market data queries (candles, symbols).
MVP-5: Mock implementation with fake data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import random


@dataclass
class Candle:
    """Internal Candle entity."""

    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: int | None = None


class MockMarketDataService:
    """
    Mock market data service for MVP-5.
    
    Returns fake OHLCV data for testing and development.
    
    Future (M3+):
    - Real data from Veda (live) or WallE (historical)
    - Date range filters
    - /symbols endpoint
    """

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> list[Candle]:
        """
        Get OHLCV candles.
        
        MVP-5: Returns mock data.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USD")
            timeframe: Candle timeframe (e.g., "1m", "5m", "1h")
            limit: Maximum number of candles to return
            
        Returns:
            List of Candle objects
        """
        # Generate mock candles
        candles: list[Candle] = []
        base_price = Decimal("42000.00")  # Base BTC price
        now = datetime.now(UTC)
        
        # Determine interval based on timeframe
        interval_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1),
        }
        interval = interval_map.get(timeframe, timedelta(minutes=1))
        
        for i in range(limit):
            timestamp = now - (interval * (limit - i - 1))
            
            # Generate realistic OHLCV data
            open_price = base_price + Decimal(str(random.uniform(-500, 500)))
            close_price = open_price + Decimal(str(random.uniform(-200, 200)))
            high_price = max(open_price, close_price) + Decimal(str(random.uniform(0, 100)))
            low_price = min(open_price, close_price) - Decimal(str(random.uniform(0, 100)))
            volume = Decimal(str(random.uniform(10, 1000)))
            
            candles.append(Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                open=open_price.quantize(Decimal("0.01")),
                high=high_price.quantize(Decimal("0.01")),
                low=low_price.quantize(Decimal("0.01")),
                close=close_price.quantize(Decimal("0.01")),
                volume=volume.quantize(Decimal("0.01")),
                trade_count=random.randint(100, 5000),
            ))
            
            # Update base price for next candle
            base_price = close_price
        
        return candles

"""
Candles Routes

REST endpoints for market data queries.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.glados.dependencies import get_market_data_service
from src.glados.schemas import CandleListResponse, CandleResponse
from src.glados.services.market_data_service import Candle, MockMarketDataService

router = APIRouter(prefix="/api/v1/candles", tags=["candles"])


def _candle_to_response(candle: Candle) -> CandleResponse:
    """Convert internal Candle to CandleResponse."""
    return CandleResponse(
        symbol=candle.symbol,
        timeframe=candle.timeframe,
        timestamp=candle.timestamp,
        open=str(candle.open),
        high=str(candle.high),
        low=str(candle.low),
        close=str(candle.close),
        volume=str(candle.volume),
        trade_count=candle.trade_count,
    )


@router.get("", response_model=CandleListResponse)
async def get_candles(
    symbol: str = Query(..., description="Trading symbol (e.g., BTC/USD)"),
    timeframe: str = Query(..., description="Candle timeframe (e.g., 1m, 5m, 1h)"),
    limit: int = Query(default=100, ge=1, le=1000),
    market_data_service: MockMarketDataService = Depends(get_market_data_service),
) -> CandleListResponse:
    """
    Get OHLCV candles.
    
    MVP-5: Returns mock data.
    """
    candles = await market_data_service.get_candles(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )
    return CandleListResponse(
        symbol=symbol,
        timeframe=timeframe,
        items=[_candle_to_response(c) for c in candles],
    )

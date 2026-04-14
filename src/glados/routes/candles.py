"""
Candles Routes

REST endpoints for market data queries.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.glados.dependencies import get_market_data_service, get_veda_service
from src.glados.schemas import CandleListResponse, CandleResponse
from src.glados.services.market_data_service import Candle, MockMarketDataService
from src.veda import VedaService
from src.veda.models import Bar

router = APIRouter(prefix="/api/v1/candles", tags=["candles"])


def _utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def _timeframe_to_delta(timeframe: str) -> timedelta:
    """Map a supported timeframe string to a timedelta."""
    interval_map = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
    }
    delta = interval_map.get(timeframe)
    if delta is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported timeframe for inferred candle window: {timeframe}",
        )
    return delta


def _align_default_end(anchor: datetime, timeframe: str) -> datetime:
    """Align implicit end timestamps to the start of the timeframe bucket."""
    anchor = anchor.astimezone(UTC)
    if timeframe.endswith("m"):
        minutes = int(timeframe[:-1])
        aligned_minute = anchor.minute - (anchor.minute % minutes)
        return anchor.replace(minute=aligned_minute, second=0, microsecond=0)
    if timeframe.endswith("h"):
        hours = int(timeframe[:-1])
        aligned_hour = anchor.hour - (anchor.hour % hours)
        return anchor.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
    if timeframe.endswith("d"):
        return anchor.replace(hour=0, minute=0, second=0, microsecond=0)
    return anchor


def _resolve_bar_window(
    *,
    timeframe: str,
    limit: int,
    start: datetime | None,
    end: datetime | None,
) -> tuple[datetime, datetime | None]:
    """Resolve a deterministic window for real-data candle queries."""
    if start is not None:
        return start, end

    delta = _timeframe_to_delta(timeframe)
    effective_end = end or _align_default_end(_utc_now(), timeframe)
    effective_start = effective_end - (delta * (limit - 1))
    return effective_start, effective_end


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


def _bar_to_response(bar: Bar, timeframe: str) -> CandleResponse:
    """Convert Veda bar data to CandleResponse."""
    return CandleResponse(
        symbol=bar.symbol,
        timeframe=timeframe,
        timestamp=bar.timestamp,
        open=str(bar.open),
        high=str(bar.high),
        low=str(bar.low),
        close=str(bar.close),
        volume=str(bar.volume),
        trade_count=bar.trade_count,
    )


@router.get("", response_model=CandleListResponse)
async def get_candles(
    symbol: str = Query(..., description="Trading symbol (e.g., BTC/USD)"),
    timeframe: str = Query(..., description="Candle timeframe (e.g., 1m, 5m, 1h)"),
    start: datetime | None = Query(default=None, description="Inclusive start time (UTC)"),
    end: datetime | None = Query(default=None, description="Inclusive end time (UTC)"),
    limit: int = Query(default=100, ge=1, le=1000),
    veda_service: VedaService | None = Depends(get_veda_service),
    market_data_service: MockMarketDataService = Depends(get_market_data_service),
) -> CandleListResponse:
    """
    Get OHLCV candles.

    Uses VedaService when available and falls back to mock data otherwise.
    """
    if veda_service is not None:
        resolved_start, resolved_end = _resolve_bar_window(
            timeframe=timeframe,
            limit=limit,
            start=start,
            end=end,
        )
        bars = await veda_service.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=resolved_start,
            end=resolved_end,
            limit=limit,
        )
        return CandleListResponse(
            symbol=symbol,
            timeframe=timeframe,
            items=[_bar_to_response(bar, timeframe) for bar in bars],
        )

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

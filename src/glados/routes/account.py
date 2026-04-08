"""
Account Routes

REST endpoints for account and position monitoring.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.glados.dependencies import get_veda_service
from src.glados.schemas import (
    AccountResponse,
    PositionListResponse,
    PositionResponse,
)
from src.glados.schemas import PositionSide as SchemaPositionSide
from src.veda import VedaService
from src.veda.models import AccountInfo, Position

router = APIRouter(prefix="/api/v1/account", tags=["account"])


def _require_veda_service(
    veda_service: VedaService | None = Depends(get_veda_service),
) -> VedaService:
    """Require VedaService to be configured."""
    if veda_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trading service not configured",
        )
    return veda_service


def _account_to_response(account: AccountInfo) -> AccountResponse:
    """Convert AccountInfo to API schema."""
    return AccountResponse(
        account_id=account.account_id,
        buying_power=str(account.buying_power),
        cash=str(account.cash),
        portfolio_value=str(account.portfolio_value),
        currency=account.currency,
        status=account.status,
    )


def _position_to_response(position: Position) -> PositionResponse:
    """Convert Position to API schema."""
    return PositionResponse(
        symbol=position.symbol,
        qty=str(position.qty),
        side=SchemaPositionSide(position.side.value),
        avg_entry_price=str(position.avg_entry_price),
        market_value=str(position.market_value),
        unrealized_pnl=str(position.unrealized_pnl),
        unrealized_pnl_percent=str(position.unrealized_pnl_percent),
    )


@router.get("", response_model=AccountResponse)
async def get_account(
    veda_service: VedaService = Depends(_require_veda_service),
) -> AccountResponse:
    """Get the current broker account snapshot."""
    account = await veda_service.get_account()
    return _account_to_response(account)


@router.get("/positions", response_model=PositionListResponse)
async def get_account_positions(
    veda_service: VedaService = Depends(_require_veda_service),
) -> PositionListResponse:
    """Get the current open positions from the exchange."""
    positions = await veda_service.get_exchange_positions()
    return PositionListResponse(
        items=[_position_to_response(position) for position in positions],
        total=len(positions),
    )

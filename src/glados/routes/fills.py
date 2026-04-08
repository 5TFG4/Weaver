"""
Fill Routes

REST endpoints for persisted fill history.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from src.glados.dependencies import get_fill_repository
from src.glados.schemas import FillListResponse, FillResponse
from src.glados.schemas import OrderSide as SchemaOrderSide
from src.walle.models import FillRecord
from src.walle.repositories.fill_repository import FillRepository

router = APIRouter(prefix="/api/v1/runs", tags=["fills"])


def _require_fill_repository(
    fill_repository: FillRepository | None = Depends(get_fill_repository),
) -> FillRepository:
    """Require fill history storage to be configured."""
    if fill_repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fill history not configured",
        )
    return fill_repository


def _decimal_to_fixed_string(value: Decimal | None) -> str | None:
    """Serialize persisted numeric values with stable scale."""
    if value is None:
        return None
    return f"{value:.8f}"


def _fill_to_response(fill: FillRecord) -> FillResponse:
    """Convert FillRecord to API schema."""
    return FillResponse(
        id=fill.id,
        order_id=fill.order_id,
        price=_decimal_to_fixed_string(fill.price) or "0.00000000",
        quantity=_decimal_to_fixed_string(fill.quantity) or "0.00000000",
        side=SchemaOrderSide(fill.side),
        filled_at=fill.filled_at,
        exchange_fill_id=fill.exchange_fill_id,
        commission=_decimal_to_fixed_string(fill.commission),
        symbol=fill.symbol,
    )


@router.get("/{run_id}/fills", response_model=FillListResponse)
async def get_run_fills(
    run_id: str,
    fill_repository: FillRepository = Depends(_require_fill_repository),
) -> FillListResponse:
    """Get persisted fills for a run."""
    fills = await fill_repository.list_by_run_id(run_id)
    return FillListResponse(
        items=[_fill_to_response(fill) for fill in fills],
        total=len(fills),
    )

"""Strategies Routes — strategy discovery endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from src.glados.dependencies import get_strategy_loader
from src.marvin.strategy_loader import PluginStrategyLoader

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


@router.get("")
async def list_strategies(
    loader: PluginStrategyLoader = Depends(get_strategy_loader),
) -> list[dict[str, Any]]:
    strategies = loader.list_available()
    return [
        {
            "id": s.id,
            "name": s.name,
            "version": s.version,
            "description": s.description,
            "author": s.author,
            "config_schema": s.config_schema,
        }
        for s in strategies
    ]

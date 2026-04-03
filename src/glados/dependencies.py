"""
GLaDOS Dependency Injection

Provides FastAPI dependency functions for accessing shared resources.
All services are retrieved from app.state, which is initialized in the lifespan.
"""

from __future__ import annotations

from fastapi import Request

from src.config import WeaverConfig
from src.events.log import EventLog
from src.glados.services.domain_router import DomainRouter
from src.glados.services.market_data_service import MockMarketDataService
from src.glados.services.order_service import MockOrderService
from src.glados.services.run_manager import RunManager
from src.glados.sse_broadcaster import SSEBroadcaster
from src.marvin.strategy_loader import PluginStrategyLoader
from src.veda import VedaService


def get_settings(request: Request) -> WeaverConfig:
    """Get application settings from app state."""
    return request.app.state.settings  # type: ignore[no-any-return]


def get_run_manager(request: Request) -> RunManager:
    """Get RunManager from app state."""
    return request.app.state.run_manager  # type: ignore[no-any-return]


def get_order_service(request: Request) -> MockOrderService:
    """Get OrderService from app state."""
    return request.app.state.order_service  # type: ignore[no-any-return]


def get_market_data_service(request: Request) -> MockMarketDataService:
    """Get MarketDataService from app state."""
    return request.app.state.market_data_service  # type: ignore[no-any-return]


def get_broadcaster(request: Request) -> SSEBroadcaster:
    """Get SSEBroadcaster from app state."""
    return request.app.state.broadcaster  # type: ignore[no-any-return]


def get_event_log(request: Request) -> EventLog | None:
    """Get EventLog from app state (may be None if no DB configured)."""
    return getattr(request.app.state, "event_log", None)


def get_veda_service(request: Request) -> VedaService | None:
    """Get VedaService from app state (may be None if no credentials configured)."""
    return getattr(request.app.state, "veda_service", None)


def get_domain_router(request: Request) -> DomainRouter | None:
    """Get DomainRouter from app state (may be None before lifespan startup)."""
    return getattr(request.app.state, "domain_router", None)


def get_strategy_loader(request: Request) -> PluginStrategyLoader:
    """Get PluginStrategyLoader from app state."""
    return request.app.state.strategy_loader  # type: ignore[no-any-return]

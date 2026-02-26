"""
GLaDOS Application Factory

Creates and configures the FastAPI application.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import WeaverConfig, get_config
from src.glados.routes.candles import router as candles_router
from src.glados.routes.health import router as health_router
from src.glados.routes.orders import router as orders_router
from src.glados.routes.runs import router as runs_router
from src.glados.routes.sse import router as sse_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events:
    - Startup: Initialize Database, EventLog, VedaService, SSE subscription
    - Shutdown: Close database connections, cleanup resources
    """
    settings: WeaverConfig = app.state.settings

    # =========================================================================
    # Startup - Always-initialized services (no DB required)
    # =========================================================================
    
    # OrderService (mock, always available)
    from src.glados.services.order_service import MockOrderService
    app.state.order_service = MockOrderService()
    logger.info("OrderService initialized")
    
    # MarketDataService (mock, always available)
    from src.glados.services.market_data_service import MockMarketDataService
    app.state.market_data_service = MockMarketDataService()
    logger.info("MarketDataService initialized")
    
    # SSEBroadcaster (always available)
    from src.glados.sse_broadcaster import SSEBroadcaster
    app.state.broadcaster = SSEBroadcaster()
    logger.info("SSEBroadcaster initialized")
    
    # Initialize placeholders (may be set to real implementations below)
    event_log = None
    database = None

    # =========================================================================
    # Startup - DB-dependent services
    # =========================================================================

    # 1. Initialize Database (if DB_URL is configured)
    db_url = os.environ.get("DB_URL")
    if db_url:
        from src.config import DatabaseConfig
        from src.walle.database import Database

        db_config = DatabaseConfig(url=db_url)
        database = Database(db_config)
        app.state.database = database
        logger.info("Database initialized")

        # 2. Initialize EventLog with database session
        from src.events.log import PostgresEventLog

        event_log = PostgresEventLog(session_factory=database.session_factory)
        app.state.event_log = event_log
        logger.info("EventLog initialized")

        # 3. Subscribe SSEBroadcaster to EventLog for real-time events
        broadcaster = app.state.broadcaster

        async def on_event(envelope):
            """Forward events from EventLog to SSE clients."""
            await broadcaster.publish(envelope.type, envelope.payload)

        unsubscribe = await event_log.subscribe(on_event)
        app.state.event_log_unsubscribe = unsubscribe
        logger.info("SSEBroadcaster subscribed to EventLog")

        # 4. Initialize VedaService (if Alpaca credentials configured)
        if settings.alpaca.has_paper_credentials or settings.alpaca.has_live_credentials:
            from src.veda.adapters.factory import create_adapter_for_mode
            from src.veda.veda_service import create_veda_service

            # Use paper credentials by default for safety
            mode = "paper" if settings.alpaca.has_paper_credentials else "live"
            credentials = settings.alpaca.get_credentials(mode)
            adapter = create_adapter_for_mode(credentials)

            try:
                veda_service = create_veda_service(
                    adapter=adapter,
                    event_log=event_log,
                    session_factory=database.session_factory,
                    config=settings,
                )
                app.state.veda_service = veda_service
                logger.info(f"VedaService initialized (mode={mode})")
            except Exception as exc:
                logger.exception(
                    "Failed to initialize VedaService (mode=%s, has_paper_credentials=%s, has_live_credentials=%s)",
                    mode,
                    settings.alpaca.has_paper_credentials,
                    settings.alpaca.has_live_credentials,
                )
                raise RuntimeError(f"Failed to initialize VedaService for mode={mode}") from exc
    else:
        logger.warning("DB_URL not set - running without database (in-memory mode)")
        app.state.database = None
        app.state.veda_service = None

        # B.3: Create InMemoryEventLog for no-DB mode (degraded but functional)
        from src.events.log import InMemoryEventLog

        event_log = InMemoryEventLog()
        app.state.event_log = event_log
        logger.info("InMemoryEventLog initialized (no-DB mode)")

        # Subscribe SSEBroadcaster to InMemoryEventLog
        broadcaster = app.state.broadcaster

        async def on_event(envelope):
            """Forward events from EventLog to SSE clients."""
            await broadcaster.publish(envelope.type, envelope.payload)

        unsubscribe = await event_log.subscribe(on_event)
        app.state.event_log_unsubscribe = unsubscribe
        logger.info("SSEBroadcaster subscribed to InMemoryEventLog")

    # =========================================================================
    # Startup - Services that may use EventLog
    # =========================================================================
    
    # RunManager runtime dependencies
    from src.glados.services.run_manager import RunManager
    from src.marvin.strategy_loader import PluginStrategyLoader

    strategy_loader = PluginStrategyLoader()
    bar_repository = None
    run_repository = None

    if database is not None:
        from src.walle.repositories.bar_repository import BarRepository
        from src.walle.repositories.run_repository import RunRepository

        bar_repository = BarRepository(database.session_factory)
        run_repository = RunRepository(database.session_factory)

    run_manager = RunManager(
        event_log=event_log,
        bar_repository=bar_repository,
        strategy_loader=strategy_loader,
        run_repository=run_repository,
    )
    app.state.run_manager = run_manager
    app.state.strategy_loader = strategy_loader
    app.state.bar_repository = bar_repository
    app.state.run_repository = run_repository

    recovered_count = await run_manager.recover()
    if recovered_count > 0:
        logger.info("Recovered %d runs from persistence", recovered_count)

    logger.info("RunManager initialized with runtime dependencies")

    # D-4: Wire DomainRouter as standalone singleton
    from src.glados.services.domain_router import DomainRouter

    domain_router = DomainRouter(event_log=event_log, run_manager=run_manager)
    app.state.domain_router = domain_router

    domain_router_subscription_id = await event_log.subscribe_filtered(
        event_types=["strategy.FetchWindow", "strategy.PlaceRequest"],
        callback=domain_router.route,
    )
    app.state.domain_router_subscription_id = domain_router_subscription_id
    logger.info("DomainRouter wired to strategy.* events")

    yield

    # =========================================================================
    # Shutdown
    # =========================================================================

    # Unsubscribe from EventLog
    if hasattr(app.state, "event_log_unsubscribe") and app.state.event_log_unsubscribe:
        app.state.event_log_unsubscribe()
        logger.info("SSEBroadcaster unsubscribed from EventLog")

    if (
        hasattr(app.state, "domain_router_subscription_id")
        and app.state.domain_router_subscription_id
        and hasattr(app.state, "event_log")
        and app.state.event_log is not None
    ):
        await app.state.event_log.unsubscribe_by_id(app.state.domain_router_subscription_id)
        logger.info("DomainRouter unsubscribed from EventLog")

    # Close database connection
    if hasattr(app.state, "database") and app.state.database:
        await app.state.database.close()
        logger.info("Database closed")


def create_app(settings: WeaverConfig | None = None) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        settings: Optional WeaverConfig. If None, uses default config.
    
    Returns:
        Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_config()

    app = FastAPI(
        title="Weaver API",
        version="0.1.0",
        description="Weaver Trading System API",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React dev server
            "http://localhost:5173",  # Vite dev server
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store settings in app state for dependency injection
    app.state.settings = settings

    # Register routes
    app.include_router(health_router)
    app.include_router(runs_router)
    app.include_router(sse_router)
    app.include_router(orders_router)
    app.include_router(candles_router)

    return app


# Default app instance for uvicorn
app = create_app()

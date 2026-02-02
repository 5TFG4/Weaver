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
    
    # RunManager (in-memory, always available)
    from src.glados.services.run_manager import RunManager
    app.state.run_manager = RunManager()
    logger.info("RunManager initialized")
    
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

            veda_service = create_veda_service(
                adapter=adapter,
                event_log=event_log,
                session_factory=database.session_factory,
                config=settings,
            )
            app.state.veda_service = veda_service
            logger.info(f"VedaService initialized (mode={mode})")
    else:
        logger.warning("DB_URL not set - running without database (in-memory mode)")
        app.state.database = None
        app.state.event_log = None
        app.state.veda_service = None

    yield

    # =========================================================================
    # Shutdown
    # =========================================================================

    # Unsubscribe from EventLog
    if hasattr(app.state, "event_log_unsubscribe") and app.state.event_log_unsubscribe:
        app.state.event_log_unsubscribe()
        logger.info("SSEBroadcaster unsubscribed from EventLog")

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

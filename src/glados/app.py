"""
GLaDOS Application Factory

Creates and configures the FastAPI application.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import WeaverConfig, get_config
from src.glados.routes.candles import reset_market_data_service
from src.glados.routes.candles import router as candles_router
from src.glados.routes.health import router as health_router
from src.glados.routes.orders import reset_order_service
from src.glados.routes.orders import router as orders_router
from src.glados.routes.runs import reset_run_manager
from src.glados.routes.runs import router as runs_router
from src.glados.routes.sse import reset_broadcaster
from src.glados.routes.sse import router as sse_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    # Startup: Initialize resources
    # (Database connections, background tasks, etc. will be added here)
    yield
    # Shutdown: Clean up resources
    # (Close connections, stop tasks, etc. will be added here)


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

    # Reset shared state for testing
    reset_run_manager()
    reset_broadcaster()
    reset_order_service()
    reset_market_data_service()

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


# Default app instance for uvicorn
app = create_app()

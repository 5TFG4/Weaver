"""
GLaDOS Application Factory

Creates and configures the FastAPI application.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.config import WeaverConfig, get_config
from src.glados.routes.health import router as health_router
from src.glados.routes.runs import reset_run_manager
from src.glados.routes.runs import router as runs_router
from src.glados.routes.sse import reset_broadcaster
from src.glados.routes.sse import router as sse_router


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

    app = FastAPI(
        title="Weaver API",
        version="0.1.0",
        description="Weaver Trading System API",
    )

    # Store settings in app state for dependency injection
    app.state.settings = settings

    # Register routes
    app.include_router(health_router)
    app.include_router(runs_router)
    app.include_router(sse_router)

    return app


# Default app instance for uvicorn
app = create_app()

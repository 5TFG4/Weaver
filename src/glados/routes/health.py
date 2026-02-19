"""
Health Check Routes

Provides /healthz endpoint for service health monitoring.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.glados.schemas import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with status and version
    """
    return HealthResponse(status="ok", version="0.1.0")

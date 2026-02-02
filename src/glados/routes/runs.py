"""
Runs Routes

REST endpoints for run management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.glados.exceptions import RunNotFoundError
from src.glados.schemas import RunCreate, RunListResponse, RunResponse, RunStatus
from src.glados.services.run_manager import Run, RunManager

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])

# Shared RunManager instance for MVP-2 (will be injected via DI in production)
_run_manager: RunManager | None = None


def get_run_manager() -> RunManager:
    """Get or create RunManager instance."""
    global _run_manager
    if _run_manager is None:
        _run_manager = RunManager()
    return _run_manager


def reset_run_manager() -> None:
    """Reset RunManager (for testing)."""
    global _run_manager
    _run_manager = None


def _run_to_response(run: Run) -> RunResponse:
    """Convert internal Run to RunResponse."""
    return RunResponse(
        id=run.id,
        strategy_id=run.strategy_id,
        mode=run.mode,
        status=run.status,
        symbols=run.symbols,
        timeframe=run.timeframe,
        config=run.config,
        created_at=run.created_at,
        started_at=run.started_at,
        stopped_at=run.stopped_at,
    )


@router.get("", response_model=RunListResponse)
async def list_runs(
    run_manager: RunManager = Depends(get_run_manager),
) -> RunListResponse:
    """
    List all runs.
    
    MVP-2: No pagination, returns all runs.
    """
    runs, total = await run_manager.list()
    return RunListResponse(
        items=[_run_to_response(r) for r in runs],
        total=total,
    )


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: RunCreate,
    run_manager: RunManager = Depends(get_run_manager),
) -> RunResponse:
    """Create a new trading run."""
    run = await run_manager.create(request)
    return _run_to_response(run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> RunResponse:
    """Get run by ID."""
    run = await run_manager.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )
    return _run_to_response(run)


@router.post("/{run_id}/stop", response_model=RunResponse)
async def stop_run(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> RunResponse:
    """Stop a running run."""
    try:
        run = await run_manager.stop(run_id)
        return _run_to_response(run)
    except RunNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )

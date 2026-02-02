"""
Run Manager Service

Manages trading run lifecycle: create, get, list, stop.
MVP-2: In-memory storage (persistence deferred to M3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.glados.exceptions import RunNotFoundError
from src.glados.schemas import RunCreate, RunMode, RunStatus


@dataclass
class Run:
    """Internal Run entity."""

    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    symbols: list[str]
    timeframe: str
    config: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None


class RunManager:
    """
    Manages trading run lifecycle.
    
    MVP-2 Implementation:
    - In-memory storage (data lost on restart)
    - No pagination (returns all)
    - No filters (returns all)
    
    Future (M3+):
    - PostgreSQL persistence
    - Pagination and filtering
    - Integration with Marvin (strategy loader)
    """

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    async def create(self, request: RunCreate) -> Run:
        """
        Create a new run in PENDING status.
        
        Args:
            request: Run creation parameters
            
        Returns:
            Created Run with generated ID
        """
        run = Run(
            id=str(uuid4()),
            strategy_id=request.strategy_id,
            mode=request.mode,
            status=RunStatus.PENDING,
            symbols=request.symbols,
            timeframe=request.timeframe,
            config=request.config,
            created_at=datetime.now(UTC),
        )
        self._runs[run.id] = run
        return run

    async def get(self, run_id: str) -> Run | None:
        """
        Get run by ID.
        
        Args:
            run_id: The run ID to fetch
            
        Returns:
            Run if found, None otherwise
        """
        return self._runs.get(run_id)

    async def list(self) -> tuple[list[Run], int]:
        """
        List all runs.
        
        MVP-2: No pagination, returns all runs.
        
        Returns:
            Tuple of (runs list, total count)
        """
        runs = list(self._runs.values())
        return runs, len(runs)

    async def start(self, run_id: str) -> Run:
        """
        Start a pending run.
        
        Args:
            run_id: The run ID to start
            
        Returns:
            Updated Run with RUNNING status
            
        Raises:
            RunNotFoundError: If run doesn't exist
        """
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        # Only start if pending
        if run.status == RunStatus.PENDING:
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(UTC)

        return run

    async def stop(self, run_id: str) -> Run:
        """
        Stop a run.
        
        Args:
            run_id: The run ID to stop
            
        Returns:
            Updated Run with STOPPED status
            
        Raises:
            RunNotFoundError: If run doesn't exist
        """
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        # Idempotent: if already stopped, just return
        if run.status != RunStatus.STOPPED:
            run.status = RunStatus.STOPPED
            run.stopped_at = datetime.now(UTC)

        return run

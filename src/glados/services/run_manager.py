"""
Run Manager Service

Manages trading run lifecycle: create, get, list, stop.
MVP-2: In-memory storage (persistence deferred to M3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.events.protocol import Envelope
from src.events.types import RunEvents
from src.glados.exceptions import RunNotFoundError, RunNotStartableError, RunNotStoppableError
from src.glados.schemas import RunCreate, RunMode, RunStatus

if TYPE_CHECKING:
    from src.events.log import EventLog


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

    def __init__(self, event_log: EventLog | None = None) -> None:
        self._runs: dict[str, Run] = {}
        self._event_log = event_log

    async def _emit_event(self, event_type: str, run: Run) -> None:
        """Emit an event if event_log is configured."""
        if self._event_log is None:
            return
        
        envelope = Envelope(
            type=event_type,
            producer="glados.run_manager",
            payload={
                "run_id": run.id,
                "strategy_id": run.strategy_id,
                "mode": run.mode.value,
                "status": run.status.value,
            },
            run_id=run.id,
        )
        await self._event_log.append(envelope)

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
        await self._emit_event(RunEvents.CREATED, run)
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
        if run.status != RunStatus.PENDING:
            raise RunNotStartableError(run_id, run.status.value)
        
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        await self._emit_event(RunEvents.STARTED, run)
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
            await self._emit_event(RunEvents.STOPPED, run)
        
        return run

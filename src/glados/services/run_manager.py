"""
Run Manager Service

Manages trading run lifecycle: create, get, list, stop.

Multi-Run Architecture (M4+):
- Each run gets a unique run_id
- Per-run instances: GretaService, StrategyRunner, Clock
- Singletons (shared): EventLog, BarRepository, DomainRouter
- RunManager maintains RunContext dict keyed by run_id
- Events tagged with run_id for isolation

Current Implementation (MVP-2):
- In-memory storage (persistence deferred to M3)
- No per-run service instantiation yet (added in M4)
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
    
    Multi-Run Architecture (M4+):
    - Creates per-run instances (GretaService, StrategyRunner, Clock)
    - Maintains _run_contexts: Dict[str, RunContext]
    - Disposes per-run instances when run completes
    - Singletons (EventLog, BarRepository) injected at construction
    
    Current Implementation (MVP-2):
    - In-memory storage (data lost on restart)
    - No pagination (returns all)
    - No filters (returns all)
    
    Future (M4):
    - RunContext creation in start()
    - Per-run GretaService/StrategyRunner instantiation
    - Resource cleanup on stop/complete
    """

    def __init__(self, event_log: EventLog | None = None) -> None:
        self._runs: dict[str, Run] = {}
        self._event_log = event_log
        # M4+: self._run_contexts: dict[str, RunContext] = {}

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
        
        M4+ Multi-Run Implementation:
        1. Create per-run instances based on run.mode:
           - BACKTEST: GretaService, StrategyRunner, BacktestClock
           - LIVE/PAPER: StrategyRunner, RealtimeClock (uses VedaService singleton)
        2. Store in self._run_contexts[run_id]
        3. Start the clock to begin execution
        
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
        
        # M4+: Create per-run context here
        # if run.mode == RunMode.BACKTEST:
        #     context = RunContext(
        #         greta=GretaService(run_id, self._bar_repo, self._event_log),
        #         runner=StrategyRunner(run_id, ...),
        #         clock=BacktestClock(run.start_time, run.end_time, run.timeframe),
        #     )
        #     self._run_contexts[run_id] = context
        #     await context.clock.start(run_id)
        
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        await self._emit_event(RunEvents.STARTED, run)
        return run

    async def stop(self, run_id: str) -> Run:
        """
        Stop a run.
        
        M4+ Multi-Run Implementation:
        1. Stop the clock (halts tick generation)
        2. Dispose per-run instances
        3. Remove from self._run_contexts[run_id]
        
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

        # M4+: Cleanup per-run context
        # if run_id in self._run_contexts:
        #     await self._run_contexts[run_id].clock.stop()
        #     del self._run_contexts[run_id]

        # Idempotent: if already stopped, just return
        if run.status != RunStatus.STOPPED:
            run.status = RunStatus.STOPPED
            run.stopped_at = datetime.now(UTC)
            await self._emit_event(RunEvents.STOPPED, run)
        
        return run

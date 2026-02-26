"""
Run Manager Service

Manages trading run lifecycle: create, get, list, stop.

Multi-Run Architecture (M4+):
- Each run gets a unique run_id
- Per-run instances: GretaService, StrategyRunner, Clock
- Singletons (shared): EventLog, BarRepository, DomainRouter
- RunManager maintains RunContext dict keyed by run_id
- Events tagged with run_id for isolation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.events.protocol import Envelope
from src.events.types import RunEvents
from src.glados.clock.backtest import BacktestClock
from src.glados.clock.base import BaseClock, ClockTick
from src.glados.clock.realtime import RealtimeClock
from src.glados.exceptions import RunNotFoundError, RunNotStartableError, RunNotStoppableError
from src.glados.schemas import RunCreate, RunMode, RunStatus
from src.greta.greta_service import GretaService
from src.marvin.strategy_runner import StrategyRunner

if TYPE_CHECKING:
    from src.events.log import EventLog
    from src.marvin.strategy_loader import StrategyLoader
    from src.walle.repositories.bar_repository import BarRepository
    from src.walle.repositories.run_repository import RunRepository


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
    # Backtest time range (optional for live/paper)
    start_time: datetime | None = None
    end_time: datetime | None = None
    # Lifecycle timestamps
    started_at: datetime | None = None
    stopped_at: datetime | None = None


@dataclass
class RunContext:
    """
    Per-run execution context.
    
    Holds all components that are instantiated per-run.
    For backtest: greta, runner, clock all set.
    For live/paper: greta is None (uses singleton VedaService).
    """
    
    greta: GretaService | None
    runner: StrategyRunner
    clock: BaseClock  # BacktestClock or RealtimeClock


class RunManager:
    """
    Manages trading run lifecycle.
    
    Multi-Run Architecture (M4):
    - Creates per-run instances (GretaService, StrategyRunner, Clock)
    - Maintains _run_contexts: Dict[str, RunContext]
    - Disposes per-run instances when run completes
    - Singletons (EventLog, BarRepository) injected at construction
    """

    def __init__(
        self,
        event_log: "EventLog | None" = None,
        bar_repository: "BarRepository | None" = None,
        strategy_loader: "StrategyLoader | None" = None,
        run_repository: "RunRepository | None" = None,
    ) -> None:
        """
        Initialize RunManager.
        
        Args:
            event_log: Event log for emitting run events
            bar_repository: Bar repository for GretaService (backtest)
            strategy_loader: Loader for strategy instances
            run_repository: Optional RunRepository for persistence/recovery (D-2)
        """
        self._runs: dict[str, Run] = {}
        self._event_log = event_log
        self._bar_repository = bar_repository
        self._strategy_loader = strategy_loader
        self._run_repository = run_repository
        self._run_contexts: dict[str, RunContext] = {}

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

    async def _persist_run(self, run: Run) -> None:
        """Persist run state to repository if configured."""
        if self._run_repository is None:
            return

        from src.walle.models import RunRecord

        record = RunRecord(
            id=run.id,
            strategy_id=run.strategy_id,
            mode=run.mode.value,
            status=run.status.value,
            symbols=run.symbols,
            timeframe=run.timeframe,
            config=run.config,
            created_at=run.created_at,
            started_at=run.started_at,
            stopped_at=run.stopped_at,
        )
        await self._run_repository.save(record)

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
            start_time=request.start_time,
            end_time=request.end_time,
        )
        self._runs[run.id] = run
        await self._emit_event(RunEvents.CREATED, run)
        await self._persist_run(run)
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
        
        For BACKTEST mode:
        1. Create GretaService, StrategyRunner, BacktestClock
        2. Initialize all components
        3. Run clock to completion (synchronous)
        4. Return completed run
        
        For LIVE/PAPER mode: (not yet implemented)
        1. Create StrategyRunner, RealtimeClock
        2. Start async execution
        
        Args:
            run_id: The run ID to start
            
        Returns:
            Updated Run (COMPLETED for backtest, RUNNING for live)
            
        Raises:
            RunNotFoundError: If run doesn't exist
            RunNotStartableError: If run is not in PENDING status
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
        await self._persist_run(run)

        try:
            if run.mode == RunMode.BACKTEST:
                await self._start_backtest(run)
            else:
                # LIVE/PAPER use RealtimeClock
                await self._start_live(run)
        except Exception:
            await self._persist_run(run)
            raise

        if run.status != RunStatus.RUNNING:
            await self._persist_run(run)

        return run

    async def _start_live(self, run: Run) -> None:
        """
        Start a live or paper trading run.
        
        Creates RealtimeClock and StrategyRunner, starts async execution.
        Unlike backtest, this returns immediately while clock runs in background.
        
        N-02: Added try/except/finally matching _start_backtest pattern.
        On failure: status → ERROR, stopped_at set, RunContext cleaned up.
        
        Args:
            run: The run to execute
        """
        if self._strategy_loader is None:
            raise RuntimeError("StrategyLoader required for live/paper run")
        
        # 1. Load strategy
        strategy = self._strategy_loader.load(run.strategy_id)
        
        # 2. Create per-run instances (no GretaService for live - uses VedaService)
        runner = StrategyRunner(
            strategy=strategy,
            event_log=self._event_log,
        )
        clock = RealtimeClock(timeframe=run.timeframe)
        
        # Store context
        ctx = RunContext(greta=None, runner=runner, clock=clock)
        self._run_contexts[run.id] = ctx
        
        try:
            # 3. Initialize runner
            await runner.initialize(run_id=run.id, symbols=run.symbols)
            
            # 4. Wire tick handler
            async def on_tick(tick: ClockTick) -> None:
                # Strategy processes tick (may emit order intents)
                await runner.on_tick(tick)
            
            clock.on_tick(on_tick)
            
            # 5. Start clock (runs in background, doesn't block)
            await clock.start(run.id)
        except Exception:
            run.status = RunStatus.ERROR
            raise
        finally:
            # Cleanup RunContext if start failed (status == ERROR)
            if run.status == RunStatus.ERROR:
                run.stopped_at = datetime.now(UTC)
                if run.id in self._run_contexts:
                    del self._run_contexts[run.id]

    async def _start_backtest(self, run: Run) -> None:
        """
        Execute backtest run to completion.
        
        Creates per-run components, runs clock, and completes.
        
        Args:
            run: The run to execute
        """
        if self._event_log is None or self._bar_repository is None:
            raise RuntimeError("EventLog and BarRepository required for backtest")
        if self._strategy_loader is None:
            raise RuntimeError("StrategyLoader required for backtest")
        if run.start_time is None or run.end_time is None:
            raise RuntimeError("start_time and end_time required for backtest")

        # 1. Load strategy
        strategy = self._strategy_loader.load(run.strategy_id)

        # 2. Create per-run instances
        greta = GretaService(
            run_id=run.id,
            bar_repository=self._bar_repository,
            event_log=self._event_log,
        )
        runner = StrategyRunner(
            strategy=strategy,
            event_log=self._event_log,
        )
        clock = BacktestClock(
            start_time=run.start_time,
            end_time=run.end_time,
            timeframe=run.timeframe,
        )

        # Store context
        ctx = RunContext(greta=greta, runner=runner, clock=clock)
        self._run_contexts[run.id] = ctx

        # 3-5: Initialize, wire, and run — all inside try/finally for cleanup
        try:
            # 3. Initialize components
            await greta.initialize(
                symbols=run.symbols,
                timeframe=run.timeframe,
                start=run.start_time,
                end=run.end_time,
            )
            await runner.initialize(run_id=run.id, symbols=run.symbols)

            # 4. Wire tick handler
            async def on_tick(tick: ClockTick) -> None:
                # a. Greta advances (processes orders, updates prices)
                await greta.advance_to(tick.ts)
                # b. Strategy processes tick (may emit events)
                await runner.on_tick(tick)

            clock.on_tick(on_tick)

            # 5. Run to completion (backtest is synchronous)
            await clock.start(run.id)
            run.status = RunStatus.COMPLETED
        except Exception:
            run.status = RunStatus.ERROR
            raise
        finally:
            # Cleanup RunContext even if init or backtest fails
            run.stopped_at = datetime.now(UTC)
            if run.id in self._run_contexts:
                del self._run_contexts[run.id]

        # 6. Emit completion event
        await self._emit_event(RunEvents.COMPLETED, run)

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

        # Cleanup per-run context
        if run_id in self._run_contexts:
            ctx = self._run_contexts[run_id]
            await ctx.clock.stop()
            del self._run_contexts[run_id]

        # Idempotent: if already stopped, just return
        if run.status != RunStatus.STOPPED:
            run.status = RunStatus.STOPPED
            run.stopped_at = datetime.now(UTC)
            await self._emit_event(RunEvents.STOPPED, run)
            await self._persist_run(run)
        
        return run

    async def recover(self) -> int:
        """
        Recover runs from database on startup (D-2).

        Loads pending and running runs from the repository.
        Running runs from a previous process are marked as ERROR
        (unclean shutdown — cannot resume execution context).
        Pending runs are loaded as-is (can be restarted).

        Returns:
            Number of runs recovered
        """
        if self._run_repository is None:
            return 0

        recovered = 0

        # Load runs that need recovery (running or pending)
        for status in ("running", "pending"):
            records = await self._run_repository.list(status=status)
            for record in records:
                # Skip if already in memory
                if record.id in self._runs:
                    continue

                run = Run(
                    id=record.id,
                    strategy_id=record.strategy_id,
                    mode=RunMode(record.mode),
                    status=RunStatus(record.status),
                    symbols=record.symbols or [],
                    timeframe=record.timeframe or "1h",
                    config=record.config,
                    created_at=record.created_at,
                    started_at=record.started_at,
                    stopped_at=record.stopped_at,
                )

                # Mark previously-running runs as ERROR (unclean shutdown)
                if run.status == RunStatus.RUNNING:
                    run.status = RunStatus.ERROR
                    run.stopped_at = datetime.now(UTC)
                    await self._persist_run(run)

                self._runs[run.id] = run
                recovered += 1

        return recovered

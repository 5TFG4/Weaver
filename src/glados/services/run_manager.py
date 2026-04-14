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

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.events.log import EventLog
from src.events.protocol import Envelope
from src.events.types import RunEvents
from src.glados.clock.backtest import BacktestClock
from src.glados.clock.base import BaseClock, ClockTick
from src.glados.clock.realtime import RealtimeClock
from src.glados.exceptions import RunNotFoundError, RunNotStartableError
from src.glados.schemas import RunCreate, RunMode, RunStatus
from src.greta.greta_service import GretaService
from src.greta.models import BacktestResult
from src.marvin.strategy_loader import StrategyLoader
from src.marvin.strategy_runner import StrategyRunner
from src.walle.repositories.bar_repository import BarRepository
from src.walle.repositories.result_repository import ResultRepository
from src.walle.repositories.run_repository import RunRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.veda import VedaService


@dataclass
class Run:
    """Internal Run entity."""

    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    config: dict[str, Any]
    created_at: datetime
    # Lifecycle timestamps
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    # Error details (M13-4)
    error: str | None = None


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
    pending_tasks: set[asyncio.Task[Any]] = field(default_factory=set)
    background_tasks: set[asyncio.Task[Any]] = field(default_factory=set)


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
        event_log: EventLog | None = None,
        bar_repository: BarRepository | None = None,
        strategy_loader: StrategyLoader | None = None,
        run_repository: RunRepository | None = None,
        result_repository: ResultRepository | None = None,
        veda_service: VedaService | None = None,
    ) -> None:
        """
        Initialize RunManager.

        Args:
            event_log: Event log for emitting run events
            bar_repository: Bar repository for GretaService (backtest)
            strategy_loader: Loader for strategy instances
            run_repository: Optional RunRepository for persistence/recovery (D-2)
            result_repository: Optional ResultRepository for backtest results (M13)
        """
        self._runs: dict[str, Run] = {}
        self._event_log = event_log
        self._bar_repository = bar_repository
        self._strategy_loader = strategy_loader
        self._run_repository = run_repository
        self._result_repository = result_repository
        self._run_contexts: dict[str, RunContext] = {}
        self._run_locks: dict[str, asyncio.Lock] = {}
        self._veda_service = veda_service

    def _get_run_lock(self, run_id: str) -> asyncio.Lock:
        """Get or create a per-run asyncio.Lock."""
        if run_id not in self._run_locks:
            self._run_locks[run_id] = asyncio.Lock()
        return self._run_locks[run_id]

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
            config=run.config,
            created_at=run.created_at,
            started_at=run.started_at,
            stopped_at=run.stopped_at,
            error=run.error,
        )
        await self._run_repository.save(record)

    async def _persist_result(self, result: BacktestResult) -> None:
        """Persist a backtest result to the result repository."""
        if self._result_repository is None:
            return

        from src.walle.models import BacktestResultRecord

        record = BacktestResultRecord(
            run_id=result.run_id,
            start_time=result.start_time,
            end_time=result.end_time,
            timeframe=result.timeframe,
            symbols=result.symbols,
            final_equity=str(result.final_equity),
            simulation_duration_ms=result.simulation_duration_ms,
            total_bars_processed=result.total_bars_processed,
            stats={
                "total_return": float(result.stats.total_return),
                "total_return_pct": float(result.stats.total_return_pct),
                "annualized_return": float(result.stats.annualized_return),
                "sharpe_ratio": float(result.stats.sharpe_ratio)
                if result.stats.sharpe_ratio is not None
                else None,
                "sortino_ratio": float(result.stats.sortino_ratio)
                if result.stats.sortino_ratio is not None
                else None,
                "max_drawdown": float(result.stats.max_drawdown),
                "max_drawdown_pct": float(result.stats.max_drawdown_pct),
                "total_trades": result.stats.total_trades,
                "winning_trades": result.stats.winning_trades,
                "losing_trades": result.stats.losing_trades,
                "win_rate": float(result.stats.win_rate),
                "avg_win": float(result.stats.avg_win),
                "avg_loss": float(result.stats.avg_loss),
                "profit_factor": float(result.stats.profit_factor)
                if result.stats.profit_factor is not None
                else None,
                "total_bars": result.stats.total_bars,
                "bars_in_position": result.stats.bars_in_position,
                "total_commission": float(result.stats.total_commission),
                "total_slippage": float(result.stats.total_slippage),
            },
            equity_curve=[
                {"timestamp": point[0].isoformat(), "equity": float(point[1])}
                for point in result.equity_curve
            ],
            fills=[
                {
                    "order_id": f.order_id,
                    "client_order_id": f.client_order_id,
                    "symbol": f.symbol,
                    "side": f.side.value,
                    "qty": str(f.qty),
                    "fill_price": str(f.fill_price),
                    "commission": str(f.commission),
                    "slippage": str(f.slippage),
                    "timestamp": f.timestamp.isoformat(),
                    "bar_index": f.bar_index,
                }
                for f in result.fills
            ],
        )
        await self._result_repository.save(record)

    async def _cleanup_run_context(self, run_id: str) -> None:
        """Cleanup per-run runtime resources if context exists.

        Cleanup contract (ordered for correctness):
        1. Stop clock (no more ticks generated)
        2. Drain pending tasks (spawned work completes before unsubscribe)
        3. Cleanup StrategyRunner subscriptions
        4. Cleanup GretaService subscriptions/state
        5. Remove context from manager
        """
        ctx = self._run_contexts.pop(run_id, None)
        if ctx is None:
            self._run_locks.pop(run_id, None)
            return

        # 1. Stop clock — no more ticks
        await ctx.clock.stop()

        # 2. Cancel long-lived background tasks before draining spawned work.
        if ctx.background_tasks:
            snapshot = list(ctx.background_tasks)
            for task in snapshot:
                task.cancel()
            await asyncio.gather(*snapshot, return_exceptions=True)
            ctx.background_tasks -= set(snapshot)

        # 3. Drain pending tasks — tasks may spawn children (e.g.
        #    fetch_window → on_data_ready → handle_place_order).
        #    Snapshot + explicit removal avoids set-mutation races.
        while ctx.pending_tasks:
            snapshot = list(ctx.pending_tasks)
            await asyncio.gather(*snapshot, return_exceptions=True)
            ctx.pending_tasks -= set(snapshot)

        # 4-5. Unsubscribe (safe now — all tasks complete)
        await ctx.runner.cleanup()
        if ctx.greta is not None:
            await ctx.greta.cleanup()

        self._run_locks.pop(run_id, None)

    async def create(self, request: RunCreate) -> Run:
        """
        Create a new run in PENDING status.

        Validates config against strategy's config_schema if available.

        Args:
            request: Run creation parameters

        Returns:
            Created Run with generated ID

        Raises:
            ValueError: If config fails JSON Schema validation
        """
        if self._strategy_loader is not None:
            meta = self._strategy_loader.get_meta(request.strategy_id)
            if meta and meta.config_schema:
                import jsonschema

                try:
                    jsonschema.validate(instance=request.config, schema=meta.config_schema)
                except jsonschema.ValidationError as e:
                    raise ValueError(str(e.message)) from e

        run = Run(
            id=str(uuid4()),
            strategy_id=request.strategy_id,
            mode=request.mode,
            status=RunStatus.PENDING,
            config=request.config,
            created_at=datetime.now(UTC),
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

    async def list(self, status: RunStatus | None = None) -> tuple[list[Run], int]:
        """
        List all runs.

        MVP-2: No pagination, returns all runs.

        Args:
            status: Optional status filter

        Returns:
            Tuple of (runs list, total count)
        """
        runs = list(self._runs.values())
        if status is not None:
            runs = [run for run in runs if run.status == status]
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
        async with self._get_run_lock(run_id):
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

        # Execute OUTSIDE the lock so stop() can acquire it during execution
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
        if self._event_log is None:
            raise RuntimeError("EventLog required for live/paper run")

        try:
            # 1. Load strategy
            strategy = self._strategy_loader.load(run.strategy_id)

            # 2. Create per-run instances (no GretaService for live - uses VedaService)
            runner = StrategyRunner(
                strategy=strategy,
                event_log=self._event_log,
            )
            clock = RealtimeClock(timeframe=run.config.get("timeframe", "1m"))

            # Store context
            ctx = RunContext(greta=None, runner=runner, clock=clock)
            self._run_contexts[run.id] = ctx

            # 3. Initialize runner
            await runner.initialize(
                run_id=run.id,
                config=run.config,
                task_set=ctx.pending_tasks,
            )

            # 4. Wire tick handler
            async def on_tick(tick: ClockTick) -> None:
                # Strategy processes tick (may emit order intents)
                await runner.on_tick(tick)

            clock.on_tick(on_tick)

            # 5. Start clock (runs in background, doesn't block)
            await clock.start(run.id)

            if self._veda_service is not None:
                task = asyncio.create_task(self._run_fill_reconciler(run))
                ctx.background_tasks.add(task)
        except Exception:
            run.status = RunStatus.ERROR
            raise
        finally:
            # Cleanup RunContext if start failed (status == ERROR)
            if run.status == RunStatus.ERROR:
                run.stopped_at = datetime.now(UTC)
                await self._cleanup_run_context(run.id)

    async def _run_fill_reconciler(self, run: Run) -> None:
        """Poll broker trade activities and reconcile fills for a live/paper run."""
        if self._veda_service is None:
            return

        interval_raw = run.config.get("fill_reconcile_interval_seconds", 2.0)
        try:
            interval_seconds = max(float(interval_raw), 0.5)
        except (TypeError, ValueError):
            interval_seconds = 2.0

        cursor = run.started_at or datetime.now(UTC)

        while True:
            try:
                cursor = await self._veda_service.reconcile_run_fills_once(
                    run_id=run.id,
                    after=cursor,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Fill reconciliation failed for run %s", run.id)

            await asyncio.sleep(interval_seconds)

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

        backtest_start = run.config.get("backtest_start")
        backtest_end = run.config.get("backtest_end")
        if backtest_start is None or backtest_end is None:
            raise RuntimeError("config must contain backtest_start and backtest_end for backtest")
        start_time = datetime.fromisoformat(backtest_start)
        end_time = datetime.fromisoformat(backtest_end)

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
            start_time=start_time,
            end_time=end_time,
            timeframe=run.config.get("timeframe", "1m"),
        )

        # Store context
        ctx = RunContext(greta=greta, runner=runner, clock=clock)
        self._run_contexts[run.id] = ctx

        # 3-5: Initialize, wire, and run — all inside try/finally for cleanup
        try:
            # 3. Initialize components
            await greta.initialize(
                symbols=run.config.get("symbols", []),
                timeframe=run.config.get("timeframe", "1m"),
                start=start_time,
                end=end_time,
                task_set=ctx.pending_tasks,
            )
            await runner.initialize(
                run_id=run.id,
                config=run.config,
                task_set=ctx.pending_tasks,
            )

            # 4. Wire tick handler
            async def on_tick(tick: ClockTick) -> None:
                # a. Greta advances (processes orders, updates prices)
                await greta.advance_to(tick.ts)
                # b. Strategy processes tick (may emit events)
                await runner.on_tick(tick)

            clock.on_tick(on_tick)

            # 5. Run to completion (backtest is synchronous)
            await clock.start(run.id)
            await clock.wait()

            # 6. Drain spawned tasks and collect errors.
            #    Tasks may spawn children (fetch_window → on_data_ready
            #    → handle_place_order).  Done-callbacks remove finished
            #    tasks from the set; loop exits when nothing remains.
            drain_errors: list[BaseException] = []
            while ctx.pending_tasks:
                snapshot = list(ctx.pending_tasks)
                results = await asyncio.gather(*snapshot, return_exceptions=True)
                ctx.pending_tasks -= set(snapshot)
                drain_errors.extend(r for r in results if isinstance(r, BaseException))

            clock_error = clock.error
            if clock_error is not None or drain_errors:
                run.status = RunStatus.ERROR
                error_msg = str(clock_error) if clock_error else str(drain_errors[0])
                run.error = error_msg
                logger.error("Backtest %s failed: %s", run.id, error_msg)
            else:
                run.status = RunStatus.COMPLETED
                # M13-1: Capture and persist result before cleanup
                try:
                    bt_result = greta.get_result()
                    await self._persist_result(bt_result)
                except Exception as persist_err:
                    run.status = RunStatus.ERROR
                    run.error = f"Result persistence failed: {persist_err}"
                    logger.error(
                        "Backtest %s result persistence failed: %s",
                        run.id,
                        persist_err,
                    )
        except Exception as exc:
            # Don't override STOPPED status if stop() was called concurrently
            if run.status != RunStatus.STOPPED:
                run.status = RunStatus.ERROR
                run.error = str(exc)
            raise
        finally:
            # Cleanup RunContext even if init or backtest fails
            if run.stopped_at is None:
                run.stopped_at = datetime.now(UTC)
            await self._cleanup_run_context(run.id)

        # Emit terminal event (skip if stop() already emitted)
        if run.status == RunStatus.ERROR:
            await self._emit_event(RunEvents.ERROR, run)
        elif run.status == RunStatus.COMPLETED:
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
        async with self._get_run_lock(run_id):
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(run_id)

            # Cleanup per-run context
            await self._cleanup_run_context(run_id)

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
                    config=record.config or {},
                    created_at=record.created_at,
                    started_at=record.started_at,
                    stopped_at=record.stopped_at,
                )

                # Mark previously-running runs as ERROR (unclean shutdown)
                if run.status == RunStatus.RUNNING:
                    run.status = RunStatus.ERROR
                    run.stopped_at = datetime.now(UTC)
                    await self._persist_run(run)
                    await self._emit_event(RunEvents.ERROR, run)

                self._runs[run.id] = run
                recovered += 1

        return recovered

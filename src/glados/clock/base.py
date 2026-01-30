"""
Base Clock Abstraction

Defines the interface for clock implementations used in GLaDOS.
Both RealtimeClock and BacktestClock implement this interface.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClockTick:
    """
    Represents a single clock tick event.

    Attributes:
        run_id: Associated run identifier
        ts: Bar start time (not emission time)
        timeframe: Timeframe code (e.g., '1m', '5m', '1h')
        bar_index: Sequential bar number within run
        is_backtest: Hint for logging/metrics (strategy should NOT use for logic)
    """

    run_id: str
    ts: datetime
    timeframe: str
    bar_index: int
    is_backtest: bool = False

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "run_id": self.run_id,
            "ts": self.ts.isoformat(),
            "timeframe": self.timeframe,
            "bar_index": self.bar_index,
            "is_backtest": self.is_backtest,
        }


# Type alias for tick callback
TickCallback = Callable[[ClockTick], None]


class BaseClock(ABC):
    """
    Abstract base class for clock implementations.

    The clock is responsible for:
    - Emitting clock.Tick events at appropriate intervals
    - Providing current time (wall or simulated)
    - Managing start/stop lifecycle
    """

    def __init__(self, timeframe: str = "1m") -> None:
        """
        Initialize the clock.

        Args:
            timeframe: Bar timeframe (e.g., '1m', '5m', '1h', '1d')
        """
        self.timeframe = timeframe
        self._callbacks: list[TickCallback] = []
        self._running = False
        self._tick_count = 0
        # Shared state for all clock implementations
        self._run_id: str = ""
        self._task: asyncio.Task[None] | None = None
        self._bar_index: int = 0

    @abstractmethod
    async def start(self, run_id: str) -> None:
        """
        Start emitting clock.Tick events.

        Args:
            run_id: The run identifier to include in ticks
        """
        pass

    async def stop(self) -> None:
        """
        Stop the clock.

        Cancels the running task and waits for cleanup.
        Subclasses can override to add cleanup logic, but should call super().
        """
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def wait(self) -> None:
        """
        Wait for the clock to stop.

        This is the preferred way to wait for the clock,
        rather than accessing the internal _task directly.
        Handles both natural completion and cancellation.
        """
        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @abstractmethod
    def current_time(self) -> datetime:
        """
        Return the current clock time.

        For RealtimeClock: actual wall clock time
        For BacktestClock: simulated time
        """
        pass

    def on_tick(self, callback: TickCallback) -> Callable[[], None]:
        """
        Register a callback for tick events.

        Args:
            callback: Function to call on each tick

        Returns:
            Unsubscribe function
        """
        self._callbacks.append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unsubscribe

    def _emit_tick(self, tick: ClockTick) -> None:
        """Emit a tick to all registered callbacks."""
        self._tick_count += 1
        for callback in self._callbacks:
            try:
                callback(tick)
            except Exception:
                logger.exception("Tick callback failed in clock")

    @property
    def is_running(self) -> bool:
        """Check if the clock is running."""
        return self._running

    @property
    def tick_count(self) -> int:
        """Get the total number of ticks emitted."""
        return self._tick_count

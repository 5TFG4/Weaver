"""
Backtest Clock

Fast-forward clock for backtesting simulation.
No actual sleeping - advances as fast as strategy can process.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from .base import BaseClock, ClockTick
from .utils import parse_timeframe

logger = logging.getLogger(__name__)


class BacktestClock(BaseClock):
    """
    Clock implementation for backtesting.

    Emits clock.Tick events as fast as possible (no sleeping).
    Advances simulated time immediately after each tick.
    Supports backpressure via acknowledgment mechanism.

    Features:
    - No actual sleeping (fast-forward mode)
    - Deterministic tick sequence
    - Backpressure support (wait for strategy acknowledgment)
    """

    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "1m",
    ) -> None:
        """
        Initialize the backtest clock.

        Args:
            start_time: Simulation start time
            end_time: Simulation end time
            timeframe: Bar timeframe (e.g., '1m', '5m', '1h')
        """
        super().__init__(timeframe)
        self._start_time = start_time
        self._end_time = end_time
        self._simulated_time = start_time

        # Backpressure support
        self._ack_event: asyncio.Event = asyncio.Event()
        self._ack_event.set()  # Start ready
        self._use_backpressure = False

    async def start(self, run_id: str) -> None:
        """Start the backtest simulation."""
        if self._running:
            return

        self._run_id = run_id
        self._running = True
        self._simulated_time = self._start_time
        self._bar_index = 0
        self._task = asyncio.create_task(self._tick_loop())

    async def stop(self) -> None:
        """Stop the backtest."""
        self._ack_event.set()  # Release any waiting
        await super().stop()

    def current_time(self) -> datetime:
        """Return the current simulated time."""
        return self._simulated_time

    def enable_backpressure(self) -> None:
        """Enable backpressure mode (wait for ack before next tick)."""
        self._use_backpressure = True

    def disable_backpressure(self) -> None:
        """Disable backpressure mode."""
        self._use_backpressure = False
        self._ack_event.set()

    def acknowledge(self) -> None:
        """Acknowledge processing of the current tick (releases backpressure)."""
        self._ack_event.set()

    async def _tick_loop(self) -> None:
        """Main loop that emits ticks as fast as possible."""
        tf = parse_timeframe(self.timeframe)
        delta = timedelta(seconds=tf.seconds)

        try:
            while self._running and self._simulated_time <= self._end_time:
                try:
                    # Wait for acknowledgment if backpressure is enabled
                    if self._use_backpressure:
                        self._ack_event.clear()

                    # Emit tick
                    self._bar_index += 1
                    tick = ClockTick(
                        run_id=self._run_id,
                        ts=self._simulated_time,
                        timeframe=self.timeframe,
                        bar_index=self._bar_index,
                        is_backtest=True,
                    )
                    self._emit_tick(tick)

                    # Wait for acknowledgment if backpressure is enabled
                    if self._use_backpressure:
                        await self._ack_event.wait()

                    # Advance simulated time
                    self._simulated_time += delta

                    # Yield to allow other tasks to run
                    await asyncio.sleep(0)

                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Error in backtest clock tick loop, skipping tick")
                    self._simulated_time += delta
        finally:
            # Mark as not running when loop exits (natural completion or cancellation)
            self._running = False

    @property
    def simulated_time(self) -> datetime:
        """Get the current simulated time."""
        return self._simulated_time

    @property
    def progress(self) -> float:
        """
        Get the simulation progress as a percentage.

        Returns:
            Progress from 0.0 to 1.0
        """
        total = (self._end_time - self._start_time).total_seconds()
        if total <= 0:
            return 1.0
        elapsed = (self._simulated_time - self._start_time).total_seconds()
        return min(1.0, max(0.0, elapsed / total))

    @property
    def is_complete(self) -> bool:
        """Check if the backtest has completed."""
        return self._simulated_time > self._end_time

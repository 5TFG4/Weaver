"""
Realtime Clock

Wall-clock aligned clock for live trading.
Ticks fire at bar boundaries with drift compensation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .base import BaseClock, ClockTick
from .utils import calculate_next_bar_start, seconds_until_next_bar


class RealtimeClock(BaseClock):
    """
    Clock implementation for live trading.

    Emits clock.Tick events aligned to wall-clock bar boundaries.
    Handles drift compensation to maintain precision.

    Example for 1-minute bars:
        - 09:30:00.000 → Tick
        - 09:31:00.000 → Tick
        - 09:32:00.000 → Tick

    Precision target: ±50ms of intended tick time.
    """

    # Buffer time before bar boundary to switch from sleep to busy-wait
    PRECISION_BUFFER_MS = 100

    def __init__(self, timeframe: str = "1m") -> None:
        """
        Initialize the realtime clock.

        Args:
            timeframe: Bar timeframe (e.g., '1m', '5m', '1h')
        """
        super().__init__(timeframe)

    async def start(self, run_id: str) -> None:
        """Start emitting ticks at bar boundaries."""
        if self._running:
            return

        self._run_id = run_id
        self._running = True
        self._bar_index = 0
        self._task = asyncio.create_task(self._tick_loop())

    def current_time(self) -> datetime:
        """Return the current wall clock time (UTC)."""
        return datetime.now(timezone.utc)

    async def _tick_loop(self) -> None:
        """Main loop that emits ticks at bar boundaries."""
        try:
            while self._running:
                try:
                    # Calculate next bar boundary
                    now = self.current_time()
                    next_bar = calculate_next_bar_start(now, self.timeframe)

                    # Sleep until close to the boundary
                    await self._sleep_until(next_bar)

                    if not self._running:
                        break

                    # Emit tick with the bar start time (not actual emission time)
                    self._bar_index += 1
                    tick = ClockTick(
                        run_id=self._run_id,
                        ts=next_bar,
                        timeframe=self.timeframe,
                        bar_index=self._bar_index,
                        is_backtest=False,
                    )
                    self._emit_tick(tick)

                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Log error but continue
                    await asyncio.sleep(1)
        finally:
            self._running = False

    async def _sleep_until(self, target: datetime) -> None:
        """
        Sleep until the target time with drift compensation.

        Uses a two-phase approach:
        1. Long sleep until close to target
        2. Short sleeps for precision
        """
        while self._running:
            now = self.current_time()
            remaining = (target - now).total_seconds()

            if remaining <= 0:
                # Already past target
                return

            if remaining > 1.0:
                # Long sleep (leave 100ms buffer)
                sleep_time = remaining - 0.1
                await asyncio.sleep(sleep_time)
            elif remaining > 0.01:
                # Short sleep for precision
                await asyncio.sleep(0.01)
            else:
                # Close enough
                return

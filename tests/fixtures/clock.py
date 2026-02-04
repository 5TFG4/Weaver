"""
Controllable Clock Fixtures

Provides test clocks that can be precisely controlled for deterministic testing.
This is critical for testing the clock system without real time delays.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

# Import ClockTick from production code - do NOT redefine it here
from src.glados.clock.base import ClockTick


@dataclass
class ControllableClock:
    """
    A clock that can be manually advanced for testing.
    
    Unlike RealtimeClock (waits for wall clock) or BacktestClock (runs fast),
    this clock only advances when explicitly told to, making tests deterministic.
    
    Usage:
        clock = ControllableClock(start_time=datetime(2024, 1, 1, 9, 30))
        
        # Advance by one bar
        clock.advance()
        
        # Advance to specific time
        clock.advance_to(datetime(2024, 1, 1, 10, 0))
        
        # Get all emitted ticks
        assert len(clock.ticks) == 30
    """
    
    start_time: datetime
    timeframe: str = "1m"
    run_id: str = "test-run-id"
    
    # Internal state
    _current_time: datetime = field(init=False)
    _bar_index: int = field(default=0, init=False)
    _ticks: list[ClockTick] = field(default_factory=list, init=False)
    _tick_callbacks: list[Callable[[ClockTick], None]] = field(
        default_factory=list, init=False
    )
    _running: bool = field(default=False, init=False)
    
    def __post_init__(self) -> None:
        """Initialize current time to start time."""
        self._current_time = self.start_time
    
    @property
    def current_time(self) -> datetime:
        """Get the current clock time."""
        return self._current_time
    
    @property
    def ticks(self) -> list[ClockTick]:
        """Get all emitted ticks."""
        return self._ticks.copy()
    
    @property
    def tick_count(self) -> int:
        """Get the number of ticks emitted."""
        return len(self._ticks)
    
    def start(self) -> None:
        """Mark clock as running (does not emit ticks automatically)."""
        self._running = True
    
    def stop(self) -> None:
        """Mark clock as stopped."""
        self._running = False

    def make_tick(self, ts: datetime | None = None) -> ClockTick:
        """
        Create a ClockTick without advancing the clock.
        
        Useful for creating test ticks without modifying clock state.
        Uses the production ClockTick class from src.glados.clock.base.
        
        Args:
            ts: Timestamp for the tick (default: current_time)
            
        Returns:
            A new ClockTick instance
        """
        return ClockTick(
            run_id=self.run_id,
            ts=ts or self._current_time,
            timeframe=self.timeframe,
            bar_index=self._bar_index,
            is_backtest=True,
        )

    def on_tick(self, callback: Callable[[ClockTick], None]) -> None:
        """Register a callback to be called on each tick."""
        self._tick_callbacks.append(callback)
    
    def advance(self, bars: int = 1) -> list[ClockTick]:
        """
        Advance the clock by the specified number of bars.
        
        Args:
            bars: Number of bars to advance (default: 1)
            
        Returns:
            List of ticks emitted during the advance
        """
        emitted: list[ClockTick] = []
        delta = self._timeframe_to_delta()
        
        for _ in range(bars):
            self._current_time += delta
            tick = self._emit_tick()
            emitted.append(tick)
        
        return emitted
    
    def advance_to(self, target_time: datetime) -> list[ClockTick]:
        """
        Advance the clock to the specified time, emitting ticks along the way.
        
        Args:
            target_time: The time to advance to
            
        Returns:
            List of ticks emitted during the advance
        """
        if target_time <= self._current_time:
            raise ValueError(
                f"Target time {target_time} must be after current time {self._current_time}"
            )
        
        emitted: list[ClockTick] = []
        delta = self._timeframe_to_delta()
        
        while self._current_time + delta <= target_time:
            self._current_time += delta
            tick = self._emit_tick()
            emitted.append(tick)
        
        return emitted
    
    def set_time(self, new_time: datetime) -> None:
        """
        Set the clock to a specific time without emitting ticks.
        
        Use this for setting up test scenarios.
        """
        self._current_time = new_time
    
    def reset(self) -> None:
        """Reset the clock to its initial state."""
        self._current_time = self.start_time
        self._bar_index = 0
        self._ticks.clear()
    
    def _emit_tick(self) -> ClockTick:
        """Create and emit a tick at the current time."""
        tick = ClockTick(
            run_id=self.run_id,
            ts=self._current_time,
            timeframe=self.timeframe,
            bar_index=self._bar_index,
            is_backtest=True,  # Test clock is always "backtest-like"
        )
        
        self._bar_index += 1
        self._ticks.append(tick)
        
        # Notify callbacks
        for callback in self._tick_callbacks:
            callback(tick)
        
        return tick
    
    def _timeframe_to_delta(self) -> timedelta:
        """Convert timeframe string to timedelta."""
        mapping = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1),
        }
        
        delta = mapping.get(self.timeframe)
        if delta is None:
            raise ValueError(f"Unknown timeframe: {self.timeframe}")
        
        return delta


def create_test_clock(
    start_time: datetime | None = None,
    timeframe: str = "1m",
    run_id: str = "test-run-id",
) -> ControllableClock:
    """
    Factory function to create a ControllableClock with sensible defaults.
    
    Args:
        start_time: Start time (default: 2024-01-15 09:30:00 UTC)
        timeframe: Bar timeframe (default: "1m")
        run_id: Run ID for ticks (default: "test-run-id")
        
    Returns:
        A new ControllableClock instance
    """
    if start_time is None:
        start_time = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
    
    return ControllableClock(
        start_time=start_time,
        timeframe=timeframe,
        run_id=run_id,
    )

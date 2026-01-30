"""
Clock Factory

Factory function for creating the appropriate clock based on configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from .backtest import BacktestClock
from .base import BaseClock
from .realtime import RealtimeClock
from .utils import parse_timeframe


@dataclass(frozen=True)
class ClockConfig:
    """
    Configuration for clock creation.

    Attributes:
        timeframe: Bar timeframe (e.g., '1m', '5m', '1h', '1d')
        backtest_start: Simulation start time (None for realtime)
        backtest_end: Simulation end time (None for realtime)

    If backtest_start and backtest_end are provided, creates a BacktestClock.
    Otherwise, creates a RealtimeClock.
    """

    timeframe: str = "1m"
    backtest_start: datetime | None = None
    backtest_end: datetime | None = None

    def __post_init__(self) -> None:
        """Validate configuration."""
        # Validate timeframe early (fail fast)
        parse_timeframe(self.timeframe)

        # Must provide both start and end, or neither
        has_start = self.backtest_start is not None
        has_end = self.backtest_end is not None

        if has_start != has_end:
            raise ValueError(
                "Must provide both backtest_start and backtest_end, or neither"
            )

        # End must be >= start
        if has_start and has_end:
            # Safe to cast since we verified both are not None
            start = cast(datetime, self.backtest_start)
            end = cast(datetime, self.backtest_end)
            if end < start:
                raise ValueError("backtest_end must be >= backtest_start")

    @property
    def is_backtest(self) -> bool:
        """Return True if this is a backtest configuration."""
        return self.backtest_start is not None


def create_clock(config: ClockConfig) -> BaseClock:
    """
    Create the appropriate clock based on configuration.

    Args:
        config: Clock configuration

    Returns:
        RealtimeClock for live/paper trading, BacktestClock for backtesting
    """
    if config.is_backtest:
        # Safe to cast: is_backtest guarantees both times are set
        return BacktestClock(
            start_time=cast(datetime, config.backtest_start),
            end_time=cast(datetime, config.backtest_end),
            timeframe=config.timeframe,
        )
    return RealtimeClock(timeframe=config.timeframe)

"""
GLaDOS Clock Module

Provides clock implementations for both live trading (wall-clock aligned)
and backtesting (fast-forward simulation).
"""

from .backtest import BacktestClock
from .base import BaseClock, ClockTick
from .factory import ClockConfig, create_clock
from .realtime import RealtimeClock
from .utils import calculate_next_bar_start, parse_timeframe

__all__ = [
    # Factory
    "ClockConfig",
    "create_clock",
    # Clock classes
    "BaseClock",
    "BacktestClock",
    "RealtimeClock",
    "ClockTick",
    # Utilities
    "calculate_next_bar_start",
    "parse_timeframe",
]

"""
GLaDOS Clock Module

Provides clock implementations for both live trading (wall-clock aligned)
and backtesting (fast-forward simulation).
"""

from .base import BaseClock, ClockTick
from .utils import calculate_next_bar_start, parse_timeframe

__all__ = [
    "BaseClock",
    "ClockTick",
    "calculate_next_bar_start",
    "parse_timeframe",
]

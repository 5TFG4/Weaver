"""Marvin - Strategy Execution

Manages strategy lifecycle and execution:
- Maintains run_id context
- Receives clock ticks
- Emits strategy intents (FetchWindow, PlaceRequest)
- Consumes market data and order events
- Produces strategy decisions

Mode-agnostic: works identically for live and backtest runs.
"""

from .base_strategy import BaseStrategy, StrategyAction
from .sample_strategy import SampleStrategy
from .strategy_loader import StrategyLoader
from .strategy_runner import StrategyRunner


class Marvin:
    """Strategy execution manager (placeholder)."""

    def __init__(self) -> None:
        """Initialize Marvin."""
        pass


__all__ = [
    "BaseStrategy",
    "Marvin",
    "SampleStrategy",
    "StrategyAction",
    "StrategyLoader",
    "StrategyRunner",
]

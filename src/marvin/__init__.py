"""Marvin - Strategy Execution

Manages strategy lifecycle and execution:
- Maintains run_id context
- Receives clock ticks
- Emits strategy intents (FetchWindow, PlaceRequest)
- Consumes market data and order events
- Produces strategy decisions

Mode-agnostic: works identically for live and backtest runs.
"""

from .strategy_loader import StrategyLoader


class Marvin:
    """Strategy execution manager (placeholder)."""

    def __init__(self) -> None:
        """Initialize Marvin."""
        pass


__all__ = ["Marvin", "StrategyLoader"]

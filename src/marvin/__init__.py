"""Marvin - Strategy Execution

Manages strategy lifecycle and execution:
- Maintains run_id context
- Receives clock ticks
- Emits strategy intents (FetchWindow, PlaceRequest)
- Consumes market data and order events
- Produces strategy decisions

Mode-agnostic: works identically for live and backtest runs.

Plugin Architecture:
- Strategies are auto-discovered from strategies/ directory
- No hardcoded imports - use PluginStrategyLoader.load(strategy_id)
- Delete safety - removing strategy files doesn't break system
"""

from .base_strategy import BaseStrategy, StrategyAction
from .exceptions import (
    CircularDependencyError,
    DependencyError,
    MarvinError,
    StrategyNotFoundError,
)
from .strategy_loader import PluginStrategyLoader, SimpleStrategyLoader, StrategyLoader
from .strategy_meta import StrategyMeta
from .strategy_runner import StrategyRunner

# For backwards compatibility, import SampleStrategy from new location
# This can be removed once all usages migrate to PluginStrategyLoader
from .strategies.sample_strategy import SampleStrategy


class Marvin:
    """Strategy execution manager (placeholder)."""

    def __init__(self) -> None:
        """Initialize Marvin."""
        pass


__all__ = [
    # Core
    "BaseStrategy",
    "Marvin",
    "StrategyAction",
    "StrategyRunner",
    # Loaders
    "PluginStrategyLoader",
    "SimpleStrategyLoader",
    "StrategyLoader",
    "StrategyMeta",
    # Exceptions
    "CircularDependencyError",
    "DependencyError",
    "MarvinError",
    "StrategyNotFoundError",
    # Backwards compatibility
    "SampleStrategy",
]

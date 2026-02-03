"""
Marvin Exceptions

Custom exceptions for strategy loading and execution.
"""


class MarvinError(Exception):
    """Base exception for Marvin module."""

    pass


class StrategyNotFoundError(MarvinError):
    """Raised when a strategy is not found."""

    def __init__(self, strategy_id: str) -> None:
        self.strategy_id = strategy_id
        super().__init__(f"Strategy not found: {strategy_id}")


class DependencyError(MarvinError):
    """Raised when a strategy dependency cannot be resolved."""

    def __init__(self, strategy_id: str, missing_dependency: str) -> None:
        self.strategy_id = strategy_id
        self.missing_dependency = missing_dependency
        super().__init__(
            f"Strategy '{strategy_id}' requires '{missing_dependency}' which was not found"
        )


class CircularDependencyError(MarvinError):
    """Raised when circular dependencies are detected."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        cycle_str = " → ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")

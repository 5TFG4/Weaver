from abc import ABC, abstractmethod

from src.marvin.base_strategy import BaseStrategy


class StrategyLoader(ABC):
    """Abstract strategy loader interface."""

    @abstractmethod
    def load(self, strategy_id: str) -> BaseStrategy:
        """Load a strategy by ID."""
        pass


class SimpleStrategyLoader(StrategyLoader):
    """Simple strategy loader from registry."""

    def __init__(self) -> None:
        self._strategies: dict[str, type[BaseStrategy]] = {}

    def register(self, strategy_id: str, strategy_class: type[BaseStrategy]) -> None:
        """Register a strategy class."""
        self._strategies[strategy_id] = strategy_class

    def load(self, strategy_id: str) -> BaseStrategy:
        """Load a strategy by ID."""
        if strategy_id not in self._strategies:
            raise ValueError(f"Strategy not found: {strategy_id}")
        return self._strategies[strategy_id]()

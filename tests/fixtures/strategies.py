"""
Test Strategy Fixtures

Reusable test strategy implementations for unit and integration tests.

Classes:
- DummyStrategy: No-op strategy with configurable return actions
- RecordingStrategy: Records all inputs without producing actions
- PredictableStrategy: Returns pre-configured sequence of actions
- SimpleTestStrategy: Simple strategy that buys once (for integration tests)
- MockStrategyLoader: Mock loader that returns configured strategy
"""

from decimal import Decimal

from src.glados.clock.base import ClockTick
from src.marvin.base_strategy import BaseStrategy, StrategyAction
from src.marvin.strategy_loader import StrategyLoader


class DummyStrategy(BaseStrategy):
    """
    No-op strategy with configurable return actions.
    
    Use for unit tests where you need to control what the strategy returns.
    
    Usage:
        strategy = DummyStrategy()
        strategy.tick_actions = [StrategyAction(...)]
        strategy.data_actions = [StrategyAction(...)]
        
        # Run strategy
        actions = await strategy.on_tick(tick)
        
        # Assert what was received
        assert strategy.received_ticks == [tick]
    """

    def __init__(self) -> None:
        super().__init__()
        # Configure these before running tests
        self.tick_actions: list[StrategyAction] = []
        self.data_actions: list[StrategyAction] = []
        # Records all inputs for assertions
        self.received_ticks: list[ClockTick] = []
        self.received_data: list[dict] = []

    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]:
        """Record tick and return configured actions."""
        self.received_ticks.append(tick)
        return self.tick_actions

    async def on_data(self, data: dict) -> list[StrategyAction]:
        """Record data and return configured actions."""
        self.received_data.append(data)
        return self.data_actions


class RecordingStrategy(BaseStrategy):
    """
    Strategy that records all inputs without producing actions.
    
    Use for integration tests where you need to verify what data
    the strategy received.
    """

    def __init__(self) -> None:
        super().__init__()
        self.tick_history: list[ClockTick] = []
        self.data_history: list[dict] = []

    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]:
        """Record tick, return no actions."""
        self.tick_history.append(tick)
        return []

    async def on_data(self, data: dict) -> list[StrategyAction]:
        """Record data, return no actions."""
        self.data_history.append(data)
        return []


class PredictableStrategy(BaseStrategy):
    """
    Strategy that returns pre-configured sequence of actions.
    
    Use when you need to test specific action sequences.
    
    Usage:
        strategy = PredictableStrategy(
            tick_actions=[[action1], [action2], []],  # First tick: action1, second: action2, third: none
            data_actions=[[buy], [sell]],
        )
    """

    def __init__(
        self,
        tick_actions: list[list[StrategyAction]] | None = None,
        data_actions: list[list[StrategyAction]] | None = None,
    ) -> None:
        super().__init__()
        self._tick_actions = tick_actions or []
        self._data_actions = data_actions or []
        self._tick_index = 0
        self._data_index = 0

    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]:
        """Return next action in sequence."""
        if self._tick_index < len(self._tick_actions):
            actions = self._tick_actions[self._tick_index]
            self._tick_index += 1
            return actions
        return []

    async def on_data(self, data: dict) -> list[StrategyAction]:
        """Return next action in sequence."""
        if self._data_index < len(self._data_actions):
            actions = self._data_actions[self._data_index]
            self._data_index += 1
            return actions
        return []


class SimpleTestStrategy(BaseStrategy):
    """
    Simple strategy that buys once when data is available.
    
    Use for end-to-end integration tests that need a working strategy.
    Migrated from tests/integration/test_backtest_flow.py.
    """

    def __init__(self) -> None:
        super().__init__()
        self._bought = False

    async def on_tick(self, tick: ClockTick) -> list[StrategyAction]:
        """Request data on each tick."""
        return [
            StrategyAction(
                type="fetch_window",
                symbol=self._symbols[0] if self._symbols else "BTC/USD",
                lookback=5,
            )
        ]

    async def on_data(self, data: dict) -> list[StrategyAction]:
        """Buy once when we have data."""
        bars = data.get("bars", [])
        if len(bars) >= 2 and not self._bought:
            self._bought = True
            symbol = bars[0].symbol if hasattr(bars[0], "symbol") else "BTC/USD"
            return [
                StrategyAction(
                    type="place_order",
                    symbol=symbol,
                    side="buy",
                    qty=Decimal("0.1"),
                    order_type="market",
                )
            ]
        return []


class MockStrategyLoader(StrategyLoader):
    """
    Mock strategy loader for testing.
    
    Returns a pre-configured strategy instead of loading from file.
    Migrated from tests/integration/test_backtest_flow.py.
    
    Usage:
        loader = MockStrategyLoader(strategy=my_dummy_strategy)
        strategy = loader.load("any-id")  # Returns my_dummy_strategy
    """

    def __init__(self, strategy: BaseStrategy | None = None) -> None:
        self._strategy = strategy

    def load(self, strategy_id: str) -> BaseStrategy:
        """Return configured strategy, or SimpleTestStrategy by default."""
        if self._strategy is not None:
            return self._strategy
        return SimpleTestStrategy()

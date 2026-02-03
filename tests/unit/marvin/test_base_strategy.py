"""
Tests for BaseStrategy

Unit tests for the strategy base class and action types.
"""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from src.marvin.base_strategy import BaseStrategy, StrategyAction


class TestStrategyAction:
    """Tests for StrategyAction dataclass."""

    def test_fetch_window_action(self) -> None:
        """Can create fetch_window action."""
        action = StrategyAction(
            type="fetch_window",
            symbol="BTC/USD",
            lookback=10,
        )

        assert action.type == "fetch_window"
        assert action.symbol == "BTC/USD"
        assert action.lookback == 10

    def test_place_order_action(self) -> None:
        """Can create place_order action."""
        action = StrategyAction(
            type="place_order",
            symbol="BTC/USD",
            side="buy",
            qty=Decimal("1.5"),
        )

        assert action.type == "place_order"
        assert action.symbol == "BTC/USD"
        assert action.side == "buy"
        assert action.qty == Decimal("1.5")

    def test_action_is_frozen(self) -> None:
        """StrategyAction is immutable."""
        action = StrategyAction(type="fetch_window", symbol="BTC/USD")

        with pytest.raises(FrozenInstanceError):
            action.type = "other"  # type: ignore


class TestBaseStrategy:
    """Tests for BaseStrategy abstract class."""

    def test_is_abstract(self) -> None:
        """BaseStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseStrategy()  # type: ignore

    def test_subclass_must_implement_on_tick(self) -> None:
        """Subclass without on_tick raises TypeError."""

        class IncompleteStrategy(BaseStrategy):
            async def on_data(self, data: dict) -> list[StrategyAction]:
                return []

        with pytest.raises(TypeError):
            IncompleteStrategy()  # type: ignore

    def test_subclass_must_implement_on_data(self) -> None:
        """Subclass without on_data raises TypeError."""

        class IncompleteStrategy(BaseStrategy):
            async def on_tick(self, tick) -> list[StrategyAction]:
                return []

        with pytest.raises(TypeError):
            IncompleteStrategy()  # type: ignore

    def test_concrete_subclass_can_instantiate(self) -> None:
        """Complete subclass can be instantiated."""

        class ConcreteStrategy(BaseStrategy):
            async def on_tick(self, tick) -> list[StrategyAction]:
                return []

            async def on_data(self, data: dict) -> list[StrategyAction]:
                return []

        strategy = ConcreteStrategy()
        assert strategy is not None

    def test_initialize_is_optional(self) -> None:
        """initialize() has default implementation."""

        class ConcreteStrategy(BaseStrategy):
            async def on_tick(self, tick) -> list[StrategyAction]:
                return []

            async def on_data(self, data: dict) -> list[StrategyAction]:
                return []

        strategy = ConcreteStrategy()
        # Should not raise
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            strategy.initialize(["BTC/USD"])
        )

    def test_has_position_defaults_false(self) -> None:
        """has_position property defaults to False."""

        class ConcreteStrategy(BaseStrategy):
            async def on_tick(self, tick) -> list[StrategyAction]:
                return []

            async def on_data(self, data: dict) -> list[StrategyAction]:
                return []

        strategy = ConcreteStrategy()
        assert strategy.has_position is False

    def test_has_position_can_be_set(self) -> None:
        """has_position can be updated by subclass."""

        class ConcreteStrategy(BaseStrategy):
            async def on_tick(self, tick) -> list[StrategyAction]:
                return []

            async def on_data(self, data: dict) -> list[StrategyAction]:
                return []

        strategy = ConcreteStrategy()
        strategy._has_position = True
        assert strategy.has_position is True

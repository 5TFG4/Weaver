"""
Base Strategy

Abstract base class for trading strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ActionType(str, Enum):
    """Type of strategy action."""

    FETCH_WINDOW = "fetch_window"
    PLACE_ORDER = "place_order"


class StrategyOrderSide(str, Enum):
    """Order side for strategy actions."""

    BUY = "buy"
    SELL = "sell"


class StrategyOrderType(str, Enum):
    """Order type for strategy actions."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass(frozen=True)
class StrategyAction:
    """
    Action returned by a strategy.
    
    Represents either a data request or an order placement.
    
    Attributes:
        type: Action type - FETCH_WINDOW or PLACE_ORDER
        symbol: Trading symbol
        lookback: Number of bars to fetch (for fetch_window)
        side: Order side - BUY or SELL (for place_order)
        qty: Order quantity (for place_order)
        order_type: Order type - MARKET, LIMIT, STOP (for place_order)
        limit_price: Limit price (for limit orders)
        stop_price: Stop price (for stop orders)
    """

    type: ActionType
    symbol: str | None = None
    lookback: int | None = None
    side: StrategyOrderSide | None = None
    qty: Decimal | None = None
    order_type: StrategyOrderType = StrategyOrderType.MARKET
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    Strategies implement logic for generating trading signals
    based on market data. They are mode-agnostic and work
    identically for live trading and backtesting.
    
    Lifecycle:
        1. initialize() - called once when strategy starts
        2. on_tick() - called on each clock tick
        3. on_data() - called when requested data arrives
    """

    def __init__(self) -> None:
        """Initialize strategy state."""
        self._has_position = False
        self._symbols: list[str] = []

    @property
    def has_position(self) -> bool:
        """Whether strategy currently has a position."""
        return self._has_position

    async def initialize(self, symbols: list[str]) -> None:
        """
        Initialize strategy with symbols.
        
        Override for custom initialization logic.
        
        Args:
            symbols: List of symbols the strategy will trade
        """
        self._symbols = symbols

    @abstractmethod
    async def on_tick(self, tick) -> list[StrategyAction]:
        """
        Handle clock tick event.
        
        Called on each time step. Strategy should return
        actions like requesting data or placing orders.
        
        Args:
            tick: Clock tick with timestamp
            
        Returns:
            List of StrategyAction to execute
        """
        ...

    @abstractmethod
    async def on_data(self, data: dict) -> list[StrategyAction]:
        """
        Handle data ready event.
        
        Called when requested market data is available.
        
        Args:
            data: Dictionary with requested data (e.g., {"bars": [...]})
            
        Returns:
            List of StrategyAction to execute
        """
        ...

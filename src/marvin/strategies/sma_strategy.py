"""
SMA Crossover Strategy

Simple Moving Average crossover strategy implementation.
Buys when fast SMA crosses above slow SMA, sells when it crosses below.
"""

from dataclasses import dataclass
from decimal import Decimal

from src.marvin.base_strategy import (
    ActionType,
    BaseStrategy,
    StrategyAction,
    StrategyOrderSide,
)


# Plugin metadata for auto-discovery
STRATEGY_META = {
    "id": "sma-crossover",
    "name": "SMA Crossover Strategy",
    "version": "1.0.0",
    "description": "Simple Moving Average crossover strategy",
    "author": "weaver",
    "dependencies": [],
    "class": "SMAStrategy",
}


@dataclass(frozen=True)
class SMAConfig:
    """
    Configuration for SMA crossover strategy.
    
    Attributes:
        fast_period: Period for fast SMA (shorter)
        slow_period: Period for slow SMA (longer)
        qty: Quantity to trade on each signal
    """

    fast_period: int = 5
    slow_period: int = 20
    qty: Decimal = Decimal("1.0")

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.fast_period >= self.slow_period:
            raise ValueError(
                f"fast_period must be less than slow_period "
                f"({self.fast_period} >= {self.slow_period})"
            )


class SMAStrategy(BaseStrategy):
    """
    Simple Moving Average crossover strategy.
    
    Logic:
        - Calculates fast and slow SMAs from bar close prices
        - Buy when fast SMA crosses above slow SMA (bullish crossover)
        - Sell when fast SMA crosses below slow SMA (bearish crossover)
    
    Crossover detection requires tracking previous SMA relationship.
    """

    def __init__(self, config: SMAConfig | None = None) -> None:
        """
        Initialize SMA strategy.
        
        Args:
            config: Strategy configuration (uses defaults if None)
        """
        super().__init__()
        self._config = config or SMAConfig()
        self._prev_fast_above_slow: bool | None = None

    async def on_tick(self, tick) -> list[StrategyAction]:
        """
        Handle clock tick - request data window.
        
        Requests bars for slow_period + 1 to ensure enough data
        for calculating both SMAs.
        
        Args:
            tick: Clock tick with timestamp
            
        Returns:
            List with single FetchWindow action
        """
        symbol = self._symbols[0] if self._symbols else "BTC/USD"
        lookback = self._config.slow_period + 1

        return [
            StrategyAction(
                type=ActionType.FETCH_WINDOW,
                symbol=symbol,
                lookback=lookback,
            )
        ]

    async def on_data(self, data: dict) -> list[StrategyAction]:
        """
        Handle data ready - check for SMA crossover.
        
        Args:
            data: Dictionary with "bars" key containing list of bar dicts
            
        Returns:
            List of StrategyAction (0 or 1 items)
        """
        bars = data.get("bars", [])
        symbol = data.get("symbol", self._symbols[0] if self._symbols else "BTC/USD")

        # Need at least slow_period bars to calculate both SMAs
        if len(bars) < self._config.slow_period:
            return []

        # Extract close prices as Decimals
        closes = self._extract_closes(bars)

        # Calculate SMAs
        fast_sma = self._calculate_sma(closes, self._config.fast_period)
        slow_sma = self._calculate_sma(closes, self._config.slow_period)

        # Determine current relationship
        fast_above_slow = fast_sma > slow_sma

        # Check for crossover
        action = self._check_crossover(fast_above_slow, symbol)

        # Update previous state
        self._prev_fast_above_slow = fast_above_slow

        return action

    def _extract_closes(self, bars: list[dict]) -> list[Decimal]:
        """
        Extract close prices from bar dicts.
        
        Args:
            bars: List of bar dictionaries with 'close' key
            
        Returns:
            List of Decimal close prices
        """
        closes = []
        for bar in bars:
            close = bar.get("close")
            if close is not None:
                if isinstance(close, Decimal):
                    closes.append(close)
                else:
                    closes.append(Decimal(str(close)))
        return closes

    def _calculate_sma(self, values: list[Decimal], period: int) -> Decimal:
        """
        Calculate Simple Moving Average.
        
        Uses the last 'period' values. If fewer values available,
        uses all available values.
        
        Args:
            values: List of Decimal values
            period: Number of periods for SMA
            
        Returns:
            SMA as Decimal
        """
        if not values:
            return Decimal("0")

        # Use last 'period' values, or all if fewer available
        window = values[-period:] if len(values) >= period else values
        return sum(window, Decimal("0")) / Decimal(len(window))

    def _check_crossover(
        self, fast_above_slow: bool, symbol: str
    ) -> list[StrategyAction]:
        """
        Check for SMA crossover and generate signal.
        
        Args:
            fast_above_slow: Whether fast SMA is currently above slow SMA
            symbol: Trading symbol
            
        Returns:
            List with trade action if crossover detected, empty otherwise
        """
        # No previous state = first data, can't detect crossover
        if self._prev_fast_above_slow is None:
            return []

        # Bullish crossover: fast crosses above slow
        if fast_above_slow and not self._prev_fast_above_slow:
            if not self._has_position:
                self._has_position = True
                return [
                    StrategyAction(
                        type=ActionType.PLACE_ORDER,
                        symbol=symbol,
                        side=StrategyOrderSide.BUY,
                        qty=self._config.qty,
                    )
                ]

        # Bearish crossover: fast crosses below slow
        if not fast_above_slow and self._prev_fast_above_slow:
            if self._has_position:
                self._has_position = False
                return [
                    StrategyAction(
                        type=ActionType.PLACE_ORDER,
                        symbol=symbol,
                        side=StrategyOrderSide.SELL,
                        qty=self._config.qty,
                    )
                ]

        return []

"""
Sample Strategy

Simple sample strategy for verifying backtest flow.
Logic: Buy when price drops 1% below average, sell when up 1%.
"""

from decimal import Decimal

from src.marvin.base_strategy import BaseStrategy, StrategyAction


# Plugin metadata for auto-discovery
STRATEGY_META = {
    "id": "sample",
    "name": "Sample Mean-Reversion Strategy",
    "version": "1.0.0",
    "description": "Simple mean-reversion strategy for testing",
    "author": "weaver",
    "dependencies": [],
    "class": "SampleStrategy",
}


class SampleStrategy(BaseStrategy):
    """
    Simple strategy for testing backtest flow.
    
    Logic:
        - Request 10-bar window on each tick
        - Buy when current price < 99% of average (and no position)
        - Sell when current price > 101% of average (and has position)
    
    This is intentionally simple for testing purposes.
    """

    def __init__(self, lookback: int = 10) -> None:
        """
        Initialize TestStrategy.
        
        Args:
            lookback: Number of bars to request for analysis
        """
        super().__init__()
        self._lookback = lookback

    async def on_tick(self, tick) -> list[StrategyAction]:
        """
        Handle clock tick - request data window.
        
        Args:
            tick: Clock tick with timestamp
            
        Returns:
            List with single FetchWindow action
        """
        # Always request data window
        return [
            StrategyAction(
                type="fetch_window",
                symbol=self._symbols[0] if self._symbols else "BTC/USD",
                lookback=self._lookback,
            )
        ]

    async def on_data(self, data: dict) -> list[StrategyAction]:
        """
        Handle data ready - decide whether to trade.
        
        Simple mean-reversion logic:
        - Buy if current < 99% of average
        - Sell if current > 101% of average
        
        Args:
            data: Dictionary with "bars" key containing list of bars
            
        Returns:
            List of StrategyAction (0 or 1 items)
        """
        bars = data.get("bars", [])

        if len(bars) < 2:
            return []

        # Calculate average close price
        total: Decimal = sum((bar.close for bar in bars), Decimal("0"))
        avg: Decimal = total / Decimal(len(bars))

        current = bars[-1].close
        symbol = bars[-1].symbol if hasattr(bars[-1], "symbol") else "BTC/USD"

        # Mean-reversion logic with 1% threshold
        lower_threshold = avg * Decimal("0.99")
        upper_threshold = avg * Decimal("1.01")

        if current < lower_threshold and not self._has_position:
            # Buy signal - price dropped below average
            self._has_position = True
            return [
                StrategyAction(
                    type="place_order",
                    symbol=symbol,
                    side="buy",
                    qty=Decimal("1"),
                    order_type="market",
                )
            ]
        elif current > upper_threshold and self._has_position:
            # Sell signal - price rose above average
            self._has_position = False
            return [
                StrategyAction(
                    type="place_order",
                    symbol=symbol,
                    side="sell",
                    qty=Decimal("1"),
                    order_type="market",
                )
            ]

        return []

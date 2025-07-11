"""
Mean Reversion Trading Strategy
Trades based on mean reversion principles - assumes prices return to average.
"""

from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyConfig, StrategySignal


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion trading strategy.
    
    Strategy Logic:
    - Similar to momentum but with different thresholds and logic
    - Designed for stocks that tend to revert to mean
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.reversion_threshold = self.parameters.get("reversion_threshold", 2.5)
        self.max_position_multiplier = self.parameters.get("max_position_multiplier", 1.5)
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Analyze market data for mean reversion opportunities"""
        
        # Extract market data
        symbol = market_data.get("symbol")
        data = market_data.get("data", {})
        current_price = data.get("price", 0.0)
        change_percent = data.get("change_percent", 0.0)
        
        # Check if we should trade this symbol
        if not symbol or not self.should_trade_symbol(symbol):
            return None
        
        # Update price tracking
        self.update_last_price(symbol, current_price)
        
        # Mean reversion logic - opposite of momentum
        if change_percent > self.reversion_threshold:
            # Price up too much - expect reversion, so sell
            position_size = int(self.position_size * self.max_position_multiplier)
            return StrategySignal(
                action="sell",
                symbol=symbol,
                quantity=position_size,
                reason=f"Mean reversion signal - price up {change_percent:.2f}%",
                strategy=self.name,
                confidence=min(1.0, abs(change_percent) / 10.0)
            )
        
        elif change_percent < -self.reversion_threshold:
            # Price down too much - expect reversion, so buy
            position_size = int(self.position_size * self.max_position_multiplier)
            return StrategySignal(
                action="buy",
                symbol=symbol,
                quantity=position_size,
                reason=f"Mean reversion signal - price down {change_percent:.2f}%",
                strategy=self.name,
                confidence=min(1.0, abs(change_percent) / 10.0)
            )
        
        return None
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information including mean reversion specific parameters"""
        info = super().get_strategy_info()
        info["strategy_type"] = "mean_reversion"
        info["reversion_threshold"] = self.reversion_threshold
        info["max_position_multiplier"] = self.max_position_multiplier
        return info

"""
Momentum Trading Strategy
Trades based on price momentum - buys dips and sells on rallies.
"""

from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyConfig, StrategySignal


class MomentumStrategy(BaseStrategy):
    """
    Momentum-based trading strategy.
    
    Strategy Logic:
    - Sell when price increases by momentum_threshold (default: 2%)
    - Buy when price decreases by momentum_threshold (default: -2%)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.momentum_threshold = self.parameters.get("momentum_threshold", 2.0)
        self.min_price_change = self.parameters.get("min_price_change", 0.5)
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Analyze market data for momentum trading opportunities"""
        
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
        
        # Check for minimum price change to avoid noise
        if abs(change_percent) < self.min_price_change:
            return None
        
        # Momentum logic
        if change_percent > self.momentum_threshold:
            # Price up significantly - take profit (sell)
            return StrategySignal(
                action="sell",
                symbol=symbol,
                quantity=self.position_size,
                reason=f"Price increased {change_percent:.2f}% - taking profit",
                strategy=self.name,
                confidence=min(1.0, abs(change_percent) / 5.0)  # Higher confidence for larger moves
            )
        
        elif change_percent < -self.momentum_threshold:
            # Price down significantly - buy the dip
            return StrategySignal(
                action="buy",
                symbol=symbol,
                quantity=self.position_size,
                reason=f"Price dropped {change_percent:.2f}% - buying dip",
                strategy=self.name,
                confidence=min(1.0, abs(change_percent) / 5.0)
            )
        
        return None
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information including momentum-specific parameters"""
        info = super().get_strategy_info()
        info["strategy_type"] = "momentum"
        info["momentum_threshold"] = self.momentum_threshold
        info["min_price_change"] = self.min_price_change
        return info

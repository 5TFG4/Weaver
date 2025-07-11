"""
Tech Stock Trading Strategy
Specialized strategy for technology stocks with sector-specific logic.
"""

from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy, StrategyConfig, StrategySignal


class TechStockStrategy(BaseStrategy):
    """
    Technology stock focused trading strategy.
    
    Strategy Logic:
    - Optimized for tech stocks (AAPL, GOOGL, NVDA, etc.)
    - Uses different thresholds and position sizing
    - Considers tech sector volatility
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters for tech stocks
        self.tech_momentum_threshold = self.parameters.get("tech_momentum_threshold", 2.0)
        self.volatility_adjustment = self.parameters.get("volatility_adjustment", 1.2)
        self.large_position_multiplier = self.parameters.get("large_position_multiplier", 2.0)
        
        # Tech-specific symbols mapping
        self.tech_symbols = {
            "AAPL": {"volatility": 1.0, "momentum_factor": 1.0},
            "GOOGL": {"volatility": 1.2, "momentum_factor": 1.1}, 
            "NVDA": {"volatility": 1.5, "momentum_factor": 1.3},
            "MSFT": {"volatility": 0.9, "momentum_factor": 0.9},
            "TSLA": {"volatility": 2.0, "momentum_factor": 1.5}
        }
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Analyze market data for tech stock opportunities"""
        
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
        
        # Get tech-specific parameters
        symbol_config = self.tech_symbols.get(symbol, {"volatility": 1.0, "momentum_factor": 1.0})
        adjusted_threshold = self.tech_momentum_threshold * symbol_config["momentum_factor"]
        
        # Tech stock momentum logic with volatility adjustment
        if change_percent > adjusted_threshold:
            # Tech stock momentum up - take profit
            position_size = int(self.position_size * self.large_position_multiplier)
            return StrategySignal(
                action="sell",
                symbol=symbol,
                quantity=position_size,
                reason=f"Price increased {change_percent:.2f}% - taking profit",
                strategy=self.name,
                confidence=min(1.0, abs(change_percent) / (5.0 * symbol_config["volatility"]))
            )
        
        elif change_percent < -adjusted_threshold:
            # Tech stock dip - buy opportunity
            position_size = int(self.position_size * self.large_position_multiplier)
            return StrategySignal(
                action="buy",
                symbol=symbol,
                quantity=position_size,
                reason=f"Price dropped {change_percent:.2f}% - buying dip",
                strategy=self.name,
                confidence=min(1.0, abs(change_percent) / (5.0 * symbol_config["volatility"]))
            )
        
        return None
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information including tech-specific parameters"""
        info = super().get_strategy_info()
        info["strategy_type"] = "tech_stock"
        info["tech_momentum_threshold"] = self.tech_momentum_threshold
        info["volatility_adjustment"] = self.volatility_adjustment
        info["supported_tech_symbols"] = list(self.tech_symbols.keys())
        return info

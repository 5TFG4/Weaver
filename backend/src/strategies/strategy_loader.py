"""
Strategy Factory and Loader
Handles dynamic loading and creation of trading strategies.
"""

from typing import Dict, Any, List, Type
from .base_strategy import BaseStrategy, StrategyConfig
from .momentum_strategy import MomentumStrategy
# from .mean_reversion_strategy import MeanReversionStrategy  # Disabled for now
# from .tech_stock_strategy import TechStockStrategy  # Disabled for now


class StrategyFactory:
    """Factory for creating trading strategy instances"""
    
    # Registry of available strategies - simplified to only momentum strategy
    STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
        "momentum_strategy": MomentumStrategy,
        # "mean_reversion_strategy": MeanReversionStrategy,  # Disabled for now
        # "tech_stock_strategy": TechStockStrategy  # Disabled for now
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: str, config: StrategyConfig) -> BaseStrategy:
        """Create a strategy instance from configuration"""
        if strategy_type not in cls.STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        strategy_class = cls.STRATEGY_REGISTRY[strategy_type]
        return strategy_class(config)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategy types"""
        return list(cls.STRATEGY_REGISTRY.keys())
    
    @classmethod
    def register_strategy(cls, strategy_type: str, strategy_class: Type[BaseStrategy]) -> None:
        """Register a new strategy type"""
        cls.STRATEGY_REGISTRY[strategy_type] = strategy_class


class StrategyLoader:
    """Loads strategies from configuration data"""
    
    @staticmethod
    def load_strategies_from_config(strategy_configs: List[Dict[str, Any]]) -> Dict[str, BaseStrategy]:
        """Load multiple strategies from configuration"""
        strategies: Dict[str, BaseStrategy] = {}
        
        for config_data in strategy_configs:
            # Create strategy configuration
            config = StrategyConfig(
                name=config_data["name"],
                position_size=config_data.get("position_size", 100),
                symbols=config_data.get("symbols", []),
                enabled=config_data.get("enabled", True),
                parameters=config_data.get("parameters", {})
            )
            
            # Determine strategy type (can be specified or inferred from name)
            strategy_type = config_data.get("strategy_type", config.name)
            
            # Create strategy instance
            try:
                strategy = StrategyFactory.create_strategy(strategy_type, config)
                strategies[config.name] = strategy
            except ValueError as e:
                # Log error but continue with other strategies
                print(f"Warning: Failed to load strategy {config.name}: {e}")
        
        return strategies
    
    @staticmethod
    def get_default_strategy_configs() -> List[Dict[str, Any]]:
        """Get default strategy configuration for testing - simplified to one strategy"""
        return [
            {
                "name": "simple_momentum",
                "strategy_type": "momentum_strategy",
                "position_size": 50,
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "parameters": {
                    "momentum_threshold": 2.0,
                    "min_price_change": 0.5
                }
            }
        ]

"""
Configuration for Alpaca connector using environment variables
"""

import os
from decimal import Decimal
from typing import List
from connectors.alpaca_connector import AlpacaConnectorConfig

def get_alpaca_config() -> AlpacaConnectorConfig:
    """
    Get Alpaca connector configuration from environment variables
    
    Returns:
        AlpacaConnectorConfig: Configuration for Alpaca connector
    """
    # Determine if we're in paper trading mode
    env = os.getenv("ENV", "production")
    is_paper_trading = env == "development"
    
    # Get API credentials based on trading mode
    if is_paper_trading:
        # For paper trading, use paper API keys
        api_key = os.getenv("ALPACA_PAPER_API_KEY", "")
        secret_key = os.getenv("ALPACA_PAPER_API_SECRET", "")
    else:
        # For live trading, use live API keys
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_API_SECRET", "")
    
    return AlpacaConnectorConfig(
        name="alpaca_trading",
        enabled=True,
        paper_trading=is_paper_trading,
        
        # API credentials from environment
        api_key=api_key,
        secret_key=secret_key,
        
        # Trading parameters - simplified to fewer symbols
        supported_symbols=[
            "AAPL", "GOOGL", "MSFT"  # Keep it simple with just 3 symbols
        ],
        commission_rate=Decimal("0.0"),  # Alpaca has no commission
        max_order_size=Decimal("10000") if is_paper_trading else Decimal("1000"),
        min_order_size=Decimal("1"),
        
        # Connection parameters
        timeout=30.0 if is_paper_trading else 60.0,
        retry_attempts=3 if is_paper_trading else 5,
        retry_delay=1.0 if is_paper_trading else 2.0,
        
        # Additional parameters
        parameters={
            "enable_market_data": True,
            "enable_streaming": True,
            "max_positions": 20 if is_paper_trading else 5,
            "risk_management": {
                "max_daily_loss": 5000 if is_paper_trading else 1000,
                "max_position_size": 0.1 if is_paper_trading else 0.05,
                "stop_loss_percentage": 0.02 if is_paper_trading else 0.01
            }
        }
    )

def get_alpaca_data_config() -> AlpacaConnectorConfig:
    """
    Get Alpaca data connector configuration for real-time market data
    Uses live API keys even in development mode to get real market data
    
    Returns:
        AlpacaConnectorConfig: Configuration for Alpaca data connector
    """
    # Always use live API keys for market data
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_API_SECRET", "")
    
    return AlpacaConnectorConfig(
        name="alpaca_data",
        enabled=True,
        paper_trading=False,  # Use live API for data
        
        # Live API credentials for market data
        api_key=api_key,
        secret_key=secret_key,
        
        # Same symbols as trading connector
        supported_symbols=[
            "AAPL", "GOOGL", "MSFT"
        ],
        commission_rate=Decimal("0.0"),
        max_order_size=Decimal("0"),  # No trading allowed
        min_order_size=Decimal("0"),
        
        # Connection parameters
        timeout=60.0,
        retry_attempts=5,
        retry_delay=2.0,
        
        # Data-only parameters
        parameters={
            "enable_market_data": True,
            "enable_streaming": True,
            "enable_trading": False,  # Disable trading for data connector
            "data_only": True
        }
    )

def get_config_for_environment() -> AlpacaConnectorConfig:
    """
    Get configuration for current environment
    
    Returns:
        AlpacaConnectorConfig: Configuration for the environment
    """
    return get_alpaca_config()

def get_all_configs() -> List[AlpacaConnectorConfig]:
    """
    Get all Alpaca connector configurations
    
    Returns:
        List[AlpacaConnectorConfig]: List of all configurations
    """
    configs = [get_alpaca_config()]
    
    # Add data connector if we have live API keys
    live_api_key = os.getenv("ALPACA_API_KEY", "")
    live_secret_key = os.getenv("ALPACA_API_SECRET", "")
    
    if live_api_key and live_secret_key:
        configs.append(get_alpaca_data_config())
    
    return configs

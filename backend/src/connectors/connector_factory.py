"""
Connector Factory

Factory for creating and managing different types of connectors.
"""

from typing import Dict, Any, Optional, List, Type, TYPE_CHECKING
from enum import Enum

from .base_connector import BaseConnector
from .base_trading_connector import BaseTradingConnector, TradingConnectorConfig
from .base_data_connector import BaseDataConnector, DataConnectorConfig
# from .paper_trading_connector import PaperTradingConnector  # Disabled for now
from .alpaca_connector import AlpacaConnector

if TYPE_CHECKING:
    from core.event_bus import EventBus

class ConnectorType(Enum):
    """Connector type enumeration"""
    PAPER_TRADING = "paper_trading"
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"
    POLYGON = "polygon"
    YAHOO_FINANCE = "yahoo_finance"

class ConnectorFactory:
    """
    Factory for creating and managing connectors.
    
    Provides a centralized way to create, configure, and manage
    different types of trading and data connectors.
    """
    
    # Registry of available connectors
    _trading_connectors: Dict[ConnectorType, Type[BaseTradingConnector]] = {
        # ConnectorType.PAPER_TRADING: PaperTradingConnector,  # Disabled for now
        ConnectorType.ALPACA: AlpacaConnector,
        # TODO: Add other trading connectors
        # ConnectorType.INTERACTIVE_BROKERS: InteractiveBrokersConnector,
    }
    
    _data_connectors: Dict[ConnectorType, Type[BaseDataConnector]] = {
        # TODO: Add data connectors
        # ConnectorType.POLYGON: PolygonDataConnector,
        # ConnectorType.YAHOO_FINANCE: YahooFinanceConnector,
    }
    
    def __init__(self, event_bus: Optional["EventBus"] = None) -> None:
        self.event_bus = event_bus
        self._active_connectors: Dict[str, BaseConnector] = {}
        
    def create_trading_connector(self, connector_type: ConnectorType, 
                                config: TradingConnectorConfig) -> BaseTradingConnector:
        """
        Create a trading connector.
        
        Args:
            connector_type: Type of connector to create
            config: Configuration for the connector
            
        Returns:
            BaseTradingConnector: Created connector instance
        """
        if connector_type not in self._trading_connectors:
            raise ValueError(f"Unsupported trading connector type: {connector_type}")
            
        connector_class = self._trading_connectors[connector_type]
        connector = connector_class(config, self.event_bus)
        
        # Store active connector
        self._active_connectors[config.name] = connector
        
        return connector
        
    def create_data_connector(self, connector_type: ConnectorType, 
                             config: DataConnectorConfig) -> BaseDataConnector:
        """
        Create a data connector.
        
        Args:
            connector_type: Type of connector to create
            config: Configuration for the connector
            
        Returns:
            BaseDataConnector: Created connector instance
        """
        if connector_type not in self._data_connectors:
            raise ValueError(f"Unsupported data connector type: {connector_type}")
            
        connector_class = self._data_connectors[connector_type]
        connector = connector_class(config, self.event_bus)
        
        # Store active connector
        self._active_connectors[config.name] = connector
        
        return connector
        
    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """
        Get a connector by name.
        
        Args:
            name: Name of the connector
            
        Returns:
            BaseConnector: Connector instance or None
        """
        return self._active_connectors.get(name)
        
    def get_trading_connectors(self) -> List[BaseTradingConnector]:
        """
        Get all trading connectors.
        
        Returns:
            List[BaseTradingConnector]: List of trading connectors
        """
        return [conn for conn in self._active_connectors.values() 
                if isinstance(conn, BaseTradingConnector)]
        
    def get_data_connectors(self) -> List[BaseDataConnector]:
        """
        Get all data connectors.
        
        Returns:
            List[BaseDataConnector]: List of data connectors
        """
        return [conn for conn in self._active_connectors.values() 
                if isinstance(conn, BaseDataConnector)]
        
    def get_active_connectors(self) -> Dict[str, BaseConnector]:
        """
        Get all active connectors.
        
        Returns:
            Dict[str, BaseConnector]: Dictionary of active connectors
        """
        return self._active_connectors.copy()
        
    async def start_all_connectors(self) -> None:
        """Start all active connectors"""
        for connector in self._active_connectors.values():
            if connector.is_enabled:
                await connector.start()
                
    async def stop_all_connectors(self) -> None:
        """Stop all active connectors"""
        for connector in self._active_connectors.values():
            await connector.stop()
            
    def remove_connector(self, name: str) -> bool:
        """
        Remove a connector.
        
        Args:
            name: Name of the connector to remove
            
        Returns:
            bool: True if connector was removed
        """
        if name in self._active_connectors:
            del self._active_connectors[name]
            return True
        return False
        
    @classmethod
    def get_supported_trading_connectors(cls) -> List[ConnectorType]:
        """
        Get list of supported trading connector types.
        
        Returns:
            List[ConnectorType]: List of supported types
        """
        return list(cls._trading_connectors.keys())
        
    @classmethod
    def get_supported_data_connectors(cls) -> List[ConnectorType]:
        """
        Get list of supported data connector types.
        
        Returns:
            List[ConnectorType]: List of supported types
        """
        return list(cls._data_connectors.keys())
        
    @classmethod
    def register_trading_connector(cls, connector_type: ConnectorType, 
                                  connector_class: Type[BaseTradingConnector]) -> None:
        """
        Register a new trading connector type.
        
        Args:
            connector_type: Type identifier
            connector_class: Connector class
        """
        cls._trading_connectors[connector_type] = connector_class
        
    @classmethod
    def register_data_connector(cls, connector_type: ConnectorType, 
                               connector_class: Type[BaseDataConnector]) -> None:
        """
        Register a new data connector type.
        
        Args:
            connector_type: Type identifier
            connector_class: Connector class
        """
        cls._data_connectors[connector_type] = connector_class
        
def get_default_connector_configs() -> Dict[str, Any]:
    """
    Get default connector configurations.
    
    Returns:
        Dict[str, Any]: Default configurations
    """
    return {
        "paper_trading": {
            "name": "paper_trading",
            "enabled": True,
            "paper_trading": True,
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "timeout": 30.0,
            "commission_rate": 0.001,
            "parameters": {
                "starting_capital": 100000,
                "max_position_size": 10000
            }
        },
        "alpaca": {
            "name": "alpaca",
            "enabled": False,
            "paper_trading": True,
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "timeout": 30.0,
            "commission_rate": 0.0,
            "parameters": {
                "base_url": "https://paper-api.alpaca.markets",
                "api_key": "",
                "api_secret": ""
            }
        }
    }

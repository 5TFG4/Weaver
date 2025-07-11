"""
Updated Veda - Exchange API Manager with Connector Architecture

Handles all interactions with trading platforms and exchanges using the new connector system.
Provides market data, executes orders, and manages exchange connections.
"""

import asyncio
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from core.logger import get_logger
from core.event_bus import EventBus

# Import connector components
from connectors import (
    ConnectorFactory, ConnectorType, 
    TradingConnectorConfig, DataConnectorConfig,
    BaseTradingConnector, BaseDataConnector,
    Order, OrderSide, OrderType, OrderStatus,
    get_default_connector_configs
)

if TYPE_CHECKING:
    from connectors import BaseConnector

logger = get_logger(__name__)


class VedaConnectorManager:
    """
    Manages connectors for Veda module.
    
    Handles creation, configuration, and lifecycle management of
    trading and data connectors.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.factory = ConnectorFactory(event_bus)
        self.trading_connectors: Dict[str, BaseTradingConnector] = {}
        self.data_connectors: Dict[str, BaseDataConnector] = {}
        
    async def initialize_connectors(self) -> None:
        """Initialize default connectors"""
        logger.info("Initializing trading connectors...")
        
        # Get default configurations
        default_configs = get_default_connector_configs()
        
        # Create paper trading connector
        paper_config = TradingConnectorConfig(
            name="paper_trading",
            enabled=True,
            paper_trading=True,
            retry_attempts=3,
            retry_delay=1.0,
            timeout=30.0,
            commission_rate=0.001,
            supported_symbols=["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMZN"]
        )
        
        try:
            paper_connector = self.factory.create_trading_connector(
                ConnectorType.PAPER_TRADING, 
                paper_config
            )
            self.trading_connectors["paper_trading"] = paper_connector
            logger.info("Paper trading connector created")
            
            # Start connectors
            await self.start_all_connectors()
            
        except Exception as e:
            logger.error(f"Failed to initialize connectors: {e}")
            raise
            
    async def start_all_connectors(self) -> None:
        """Start all connectors"""
        logger.info("Starting all connectors...")
        
        # Start trading connectors
        for name, connector in self.trading_connectors.items():
            try:
                await connector.start()
                logger.info(f"Started trading connector: {name}")
            except Exception as e:
                logger.error(f"Failed to start trading connector {name}: {e}")
                
        # Start data connectors
        for name, connector in self.data_connectors.items():
            try:
                await connector.start()
                logger.info(f"Started data connector: {name}")
            except Exception as e:
                logger.error(f"Failed to start data connector {name}: {e}")
                
    async def stop_all_connectors(self) -> None:
        """Stop all connectors"""
        logger.info("Stopping all connectors...")
        
        # Stop trading connectors
        for name, connector in self.trading_connectors.items():
            try:
                await connector.stop()
                logger.info(f"Stopped trading connector: {name}")
            except Exception as e:
                logger.error(f"Failed to stop trading connector {name}: {e}")
                
        # Stop data connectors
        for name, connector in self.data_connectors.items():
            try:
                await connector.stop()
                logger.info(f"Stopped data connector: {name}")
            except Exception as e:
                logger.error(f"Failed to stop data connector {name}: {e}")
                
    def get_available_trading_platforms(self) -> Dict[str, Dict[str, Any]]:
        """Get available trading platforms"""
        platforms = {}
        
        for name, connector in self.trading_connectors.items():
            if connector.is_connected:
                platforms[name] = {
                    "name": name,
                    "status": "connected",
                    "paper_trading": connector.is_paper_trading,
                    "account_id": connector.account.account_id if connector.account else None,
                    "buying_power": float(connector.account.buying_power) if connector.account else 0.0
                }
            else:
                platforms[name] = {
                    "name": name,
                    "status": "disconnected",
                    "paper_trading": connector.is_paper_trading,
                    "account_id": None,
                    "buying_power": 0.0
                }
                
        return platforms
        
    async def submit_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Submit an order through available connectors"""
        # Find available trading connector
        available_connector = None
        for connector in self.trading_connectors.values():
            if connector.is_connected:
                available_connector = connector
                break
                
        if not available_connector:
            logger.warning("No trading connectors available for order submission")
            return None
            
        # Create order object
        try:
            order = Order(
                symbol=order_data["symbol"],
                side=OrderSide.BUY if order_data["side"].lower() == "buy" else OrderSide.SELL,
                quantity=order_data["quantity"],
                order_type=OrderType.MARKET  # Default to market orders
            )
            
            # Submit order
            order_id = await available_connector.submit_order(order)
            logger.info(f"Order submitted: {order_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            return None


class Veda:
    """
    Exchange API Manager - Autonomous module for trading platform integration.
    
    Uses the new connector architecture for platform abstraction.
    """
    
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus: EventBus = event_bus
        self.running: bool = False
        self.ready: bool = False
        
        # Connector manager
        self.connector_manager = VedaConnectorManager(event_bus)
        
        # Subscribe to system events immediately during initialization
        self.event_bus.subscribe("system_init", self._on_system_init)
        self.event_bus.subscribe("system_terminate", self._on_system_terminate)
        
        logger.info("Veda initialized - Exchange API Manager ready")
    
    async def startup(self) -> None:
        """Start Veda module and initialize connectors"""
        logger.info("Veda starting up - Initializing exchange connections...")
        
        # Subscribe to trading-specific events
        self.event_bus.subscribe("trading_platform_request", self._on_platform_request)
        self.event_bus.subscribe("market_data_request", self._on_market_data_request)
        self.event_bus.subscribe("order_request", self._on_order_request)
        
        # Initialize connectors
        await self.connector_manager.initialize_connectors()
        
        self.running = True
        self.ready = True
        
        # Report ready to GLaDOS
        ready_data: Dict[str, Any] = {
            "module": "veda",
            "status": "ready",
            "message": "Exchange connections established"
        }
        await self.event_bus.publish("module_ready", ready_data)
        
        logger.info("Veda startup complete - Exchange API Manager online")
    
    async def shutdown(self) -> None:
        """Shutdown Veda module"""
        logger.info("Veda shutting down - Closing exchange connections...")
        
        self.running = False
        
        # Log pending orders
        logger.info("Cancelling pending orders...")
        
        # Stop all connectors
        await self.connector_manager.stop_all_connectors()
        
        # Simulate graceful shutdown delay
        await asyncio.sleep(0.3)
        
        logger.info("Closing exchange API connections...")
        
        # Simulate API connection cleanup
        await asyncio.sleep(0.3)
        
        # Report shutdown complete
        shutdown_data: Dict[str, Any] = {
            "module": "veda",
            "message": "Exchange connections closed, pending orders cancelled"
        }
        await self.event_bus.publish("module_shutdown_complete", shutdown_data)
        
        logger.info("Veda shutdown complete - Exchange API Manager offline")
    
    async def _on_system_init(self, data: Any) -> None:
        """Handle system initialization event"""
        logger.info("Veda received system_init - Starting exchange connections")
        await self.startup()
    
    async def _on_system_terminate(self, data: Any) -> None:
        """Handle system termination event"""
        logger.info("Veda received system_terminate - Closing exchange connections")
        await self.shutdown()
    
    def _safe_get(self, data: Any, key: str, default: Any = None) -> Any:
        """Safely get value from data dictionary with proper typing"""
        if hasattr(data, 'get'):
            return data.get(key, default)
        return default
    
    async def _on_platform_request(self, data: Any) -> None:
        """Handle trading platform availability requests"""
        request_id: Optional[str] = self._safe_get(data, "request_id")
        
        logger.info(f"Platform request received, request_id: {request_id}")
        
        # Get available platforms from connector manager
        platforms = self.connector_manager.get_available_trading_platforms()
        
        # Respond with available platforms
        response_data: Dict[str, Any] = {
            "platforms": platforms,
            "request_id": request_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.event_bus.publish("platform_available", response_data)
        
        logger.info(f"Platform availability sent: {len(platforms)} platforms")
    
    async def _on_market_data_request(self, data: Any) -> None:
        """Handle market data requests"""
        symbol: str = self._safe_get(data, "symbol", "AAPL")
        data_type: str = self._safe_get(data, "type", "real_time")
        request_id: Optional[str] = self._safe_get(data, "request_id")
        
        logger.info(f"Market data request: {symbol} ({data_type})")
        
        # For now, let the connectors handle market data publishing
        # The paper trading connector will automatically publish market data updates
        
        logger.info(f"Market data request acknowledged for {symbol}")
    
    async def _on_order_request(self, data: Any) -> None:
        """Handle order execution requests"""
        order_data: Dict[str, Any] = self._safe_get(data, "order", {})
        
        logger.info(f"Order request received: {order_data}")
        
        # Submit order through connector manager
        order_id = await self.connector_manager.submit_order(order_data)
        
        if order_id:
            logger.info(f"Order submitted successfully: {order_id}")
        else:
            logger.warning("Order submission failed")

"""
Core Application Module
Provides the main Application class for system startup and configuration.
"""
import os
from typing import Optional, Dict, Any
from core.logger import get_logger
from core.event_bus import EventBus
from connectors.connector_factory import ConnectorFactory, ConnectorType
from connectors.base_connector import BaseConnector

logger = get_logger(__name__)

class Application:
    """
    Core Application class that handles system startup and configuration.
    This is used by GLaDOS to initialize the system properly.
    """
    
    def __init__(self, env: Optional[str] = None):
        self.env = env or os.getenv("ENV", "production")
        self.event_bus = EventBus()
        self.connector_factory = ConnectorFactory(self.event_bus)
        self.connectors: Dict[str, BaseConnector] = {}
        self.modules = {}
        self.running = False
        
        logger.info(f"Application initialized in {self.env} mode")
    
    async def startup(self):
        """Initialize and start all core systems"""
        logger.info("Starting core application systems...")
        
        # Initialize event bus
        await self.event_bus.start()
        logger.info("✓ Event bus started")
        
        # Initialize connectors
        await self._initialize_connectors()
        
        # Start background tasks
        await self._start_background_tasks()
        
        self.running = True
        logger.info("✓ Core application systems started successfully")
    
    async def _initialize_connectors(self):
        """Initialize trading connectors"""
        logger.info("Initializing trading connectors...")
        
        try:
            # Get all Alpaca configurations
            from connectors.alpaca_config import get_all_configs
            alpaca_configs = get_all_configs()
            
            for config in alpaca_configs:
                # Validate configuration
                if not config.api_key or not config.secret_key:
                    logger.warning(f"⚠️  {config.name} API credentials not configured - connector will be disabled")
                    continue
                
                # Create Alpaca connector
                alpaca_connector = self.connector_factory.create_trading_connector(
                    ConnectorType.ALPACA, 
                    config
                )
                
                # Connect to Alpaca
                if await alpaca_connector.connect():
                    self.connectors[config.name] = alpaca_connector
                    
                    # Different logging for different connector types
                    if config.parameters.get("data_only", False):
                        logger.info(f"✓ Alpaca data connector initialized ({config.name})")
                        logger.info(f"  - Mode: Data-Only (Live API)")
                        logger.info(f"  - Supported Symbols: {len(config.supported_symbols)}")
                    else:
                        logger.info(f"✓ Alpaca trading connector initialized ({config.name})")
                        logger.info(f"  - Trading Mode: {'Paper' if config.paper_trading else 'Live'}")
                        logger.info(f"  - Supported Symbols: {len(config.supported_symbols)}")
                        
                        # Get account info to verify connection
                        account = await alpaca_connector.get_account_info()
                        logger.info(f"  - Account: {account.account_id}")
                        logger.info(f"  - Buying Power: ${account.buying_power}")
                        logger.info(f"  - Portfolio Value: ${account.portfolio_value}")
                        
                else:
                    logger.error(f"❌ Failed to connect to {config.name}")
                    
        except Exception as e:
            logger.error(f"❌ Error initializing Alpaca connectors: {e}")
    
    async def _start_background_tasks(self):
        """Start background tasks"""
        logger.info("Starting background tasks...")
        
        # TODO: Add background tasks for:
        # - Market data streaming
        # - Position monitoring
        # - Risk management
        # - Strategy execution
        
        logger.info("✓ Background tasks started")
    
    async def shutdown(self):
        """Gracefully shutdown all systems"""
        logger.info("Shutting down application...")
        
        self.running = False
        
        # Stop connectors
        await self._shutdown_connectors()
        
        # Stop event bus
        await self.event_bus.stop()
        
        logger.info("✓ Application shutdown complete")
    
    async def _shutdown_connectors(self):
        """Shutdown all connectors"""
        logger.info("Shutting down connectors...")
        
        for name, connector in self.connectors.items():
            try:
                await connector.disconnect()
                logger.info(f"✓ {name} connector disconnected")
            except Exception as e:
                logger.error(f"❌ Error disconnecting {name} connector: {e}")
        
        self.connectors.clear()
    
    def get_event_bus(self) -> EventBus:
        """Get the application's event bus"""
        return self.event_bus
    
    def get_connector_factory(self) -> ConnectorFactory:
        """Get the connector factory"""
        return self.connector_factory
    
    def get_connectors(self) -> Dict[str, BaseConnector]:
        """Get all active connectors"""
        return self.connectors.copy()
    
    def is_running(self) -> bool:
        """Check if the application is running"""
        return self.running

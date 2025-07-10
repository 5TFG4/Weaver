import asyncio
import signal
import sys
from typing import Optional
from core.logger import get_logger
from core.application import Application

logger = get_logger("glados")

class GLaDOS:
    """
    Main Application Class - GLaDOS
    
    GLaDOS is the main application that coordinates the entire trading system.
    It manages the application lifecycle, module coordination, and system orchestration.
    """
    
    def __init__(self, env: Optional[str] = None):
        self.app = Application(env)
        self.running = False
        
        # Module references (will be initialized during startup)
        self.veda = None      # Exchange API handler
        self.walle = None     # Database operations
        self.marvin = None    # Strategy executor
        self.greta = None     # Backtesting engine
        self.haro = None      # UI Backend
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        logger.info("GLaDOS initialized - Main Application ready")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def startup(self):
        """Start the entire trading system"""
        logger.info("GLaDOS starting up - Initializing trading system...")
        
        # Start core application systems
        await self.app.startup()
        
        # Initialize modules
        await self._initialize_modules()
        
        # Start module coordination
        await self._start_coordination()
        
        self.running = True
        logger.info("GLaDOS startup complete - Trading system online")
    
    async def _initialize_modules(self):
        """Initialize all trading modules"""
        logger.info("Initializing trading modules...")
        
        # TODO: Initialize Veda (Exchange API)
        # self.veda = Veda(self.app.get_event_bus())
        
        # TODO: Initialize WallE (Database)
        # self.walle = WallE(self.app.get_event_bus())
        
        # TODO: Initialize Marvin (Strategy Executor)
        # self.marvin = Marvin(self.app.get_event_bus())
        
        # TODO: Initialize Greta (Backtesting)
        # self.greta = Greta(self.app.get_event_bus())
        
        # TODO: Initialize Haro (UI Backend)
        # self.haro = Haro(self.app.get_event_bus())
        
        logger.info("All modules initialized")
    
    async def _start_coordination(self):
        """Start module coordination and event subscriptions"""
        logger.info("Starting module coordination...")
        
        event_bus = self.app.get_event_bus()
        
        # Subscribe to key system events
        event_bus.subscribe("system_heartbeat", self._on_system_heartbeat)
        event_bus.subscribe("market_data", self._on_market_data)
        event_bus.subscribe("trade_signal", self._on_trade_signal)
        event_bus.subscribe("order_filled", self._on_order_filled)
        
        # Start periodic tasks
        asyncio.create_task(self._system_heartbeat())
        
        logger.info("Module coordination started")
    
    async def _system_heartbeat(self):
        """System heartbeat - monitor system health"""
        while self.running:
            await self.app.get_event_bus().publish("system_heartbeat", {
                "timestamp": asyncio.get_event_loop().time(),
                "status": "healthy"
            })
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    async def _on_system_heartbeat(self, data):
        """Handle system heartbeat events"""
        logger.debug("System heartbeat received")
    
    async def _on_market_data(self, data):
        """Handle market data events"""
        logger.debug("Market data received")
        # TODO: Process market data and trigger strategy analysis
    
    async def _on_trade_signal(self, data):
        """Handle trade signal events"""
        logger.info("Trade signal received")
        # TODO: Process trade signals and execute orders
    
    async def _on_order_filled(self, data):
        """Handle order filled events"""
        logger.info("Order filled")
        # TODO: Update portfolio and log trade
    
    async def run(self):
        """Main application loop"""
        try:
            await self.startup()
            
            # Keep the application running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Fatal error in GLaDOS: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the trading system"""
        logger.info("GLaDOS shutting down...")
        
        self.running = False
        
        # Shutdown modules
        # TODO: Shutdown all modules gracefully
        
        # Shutdown core application
        await self.app.shutdown()
        
        logger.info("GLaDOS shutdown complete")
        
        # Exit the program
        sys.exit(0)
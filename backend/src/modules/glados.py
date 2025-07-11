import asyncio
import signal
import sys
from typing import Optional, Any, Dict
from types import FrameType
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
        
        # Module references and health tracking
        self.module_health: Dict[str, Dict[str, Any]] = {}
        self.modules_ready: Dict[str, bool] = {
            "veda": False,
            "walle": False, 
            "marvin": False,
            "greta": False,
            "haro": False
        }
        
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
        def signal_handler(signum: int, frame: Optional[FrameType]) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def startup(self):
        """Start the entire trading system"""
        logger.info("GLaDOS starting up - Initializing trading system...")
        
        # Start core application systems
        await self.app.startup()
        
        # Setup event monitoring FIRST - before creating modules
        await self._setup_event_subscriptions()
        
        # Initialize modules (they will subscribe to system_init during creation)
        await self._initialize_modules()
        
        # Now trigger system initialization
        await self._trigger_system_init()
        
        # Start ongoing monitoring
        await self._start_system_monitoring()
        
        self.running = True
        logger.info("GLaDOS startup complete - Trading system online")
    
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions - must happen before modules are created"""
        logger.info("Setting up GLaDOS event monitoring...")
        
        event_bus = self.app.get_event_bus()
        
        # Subscribe to system-level events that GLaDOS needs to coordinate
        event_bus.subscribe("module_ready", self._on_module_ready)
        event_bus.subscribe("module_health", self._on_module_health)
        event_bus.subscribe("system_heartbeat", self._on_system_heartbeat)
        event_bus.subscribe("system_error", self._on_system_error)
        event_bus.subscribe("module_shutdown_request", self._on_shutdown_request)
        event_bus.subscribe("module_shutdown_complete", self._on_module_shutdown_complete)
        
        logger.info("GLaDOS event monitoring ready")
    
    async def _initialize_modules(self):
        """Initialize all trading modules - they will subscribe to system_init during creation"""
        logger.info("Initializing trading modules...")
        
        event_bus = self.app.get_event_bus()
        
        # Initialize modules - each will subscribe to system_init during creation
        try:
            from modules.veda import Veda
            from modules.marvin import Marvin
            
            self.veda = Veda(event_bus, self.app)  # Pass Application to Veda
            self.marvin = Marvin(event_bus)
            
            logger.info("Core modules initialized (Veda, Marvin)")
            
            # TODO: Initialize remaining modules when implemented
            # self.walle = WallE(event_bus)  
            # self.greta = Greta(event_bus)
            # self.haro = Haro(event_bus)
            
        except ImportError as e:
            logger.warning(f"Some modules not available: {e}")
    
    async def _trigger_system_init(self):
        """Trigger system initialization - modules are ready to receive this"""
        logger.info("Triggering system initialization...")
        
        event_bus = self.app.get_event_bus()
        
        # Send system initialization event - modules decide what to do
        await event_bus.publish("system_init", {
            "timestamp": asyncio.get_event_loop().time(),
            "message": "System initialization complete - modules may begin autonomous operations"
        })
        
        logger.info("System initialization triggered - modules will self-manage")
    
    async def _start_system_monitoring(self):
        """Start ongoing system monitoring tasks"""
        logger.info("Starting system monitoring tasks...")
        
        # Start system health monitoring
        asyncio.create_task(self._system_heartbeat())
        
        logger.info("System monitoring active")
    
    async def _system_heartbeat(self) -> None:
        """System heartbeat - monitor system health"""
        while self.running:
            await self.app.get_event_bus().publish("system_heartbeat", {
                "timestamp": asyncio.get_event_loop().time(),
                "status": "healthy"
            })
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    async def _on_system_heartbeat(self, data: Any) -> None:
        """Handle system heartbeat events - just log for health monitoring"""
        logger.debug("System heartbeat received - all systems operational")
    
    async def _on_module_ready(self, data: Any) -> None:
        """Handle module ready events - track module startup status"""
        module_name = data.get("module", "unknown")
        status = data.get("status", "unknown")
        message = data.get("message", "")
        
        logger.info(f"Module ready: {module_name} - {status} - {message}")
        
        if module_name in self.modules_ready:
            self.modules_ready[module_name] = (status == "ready")
            
        # Check if all modules are ready
        await self._check_system_ready()
    
    async def _on_module_health(self, data: Any) -> None:
        """Handle module health status reports"""
        module_name = data.get("module", "unknown")
        status = data.get("status", "unknown")
        
        self.module_health[module_name] = data
        logger.debug(f"Health update: {module_name} - {status}")
        
        # Check for critical health issues
        if status == "error":
            logger.warning(f"Module {module_name} reporting errors - monitoring for intervention")
    
    async def _check_system_ready(self) -> None:
        """Check if all modules are ready and publish system_ready event"""
        all_ready = all(self.modules_ready.values())
        
        if all_ready and not self.running:
            logger.info("All modules ready - System operational!")
            
            # Publish system ready event
            await self.app.get_event_bus().publish("system_ready", {
                "timestamp": asyncio.get_event_loop().time(),
                "modules_ready": self.modules_ready.copy(),
                "message": "All modules operational - trading system ready"
            })
            
            self.running = True
            logger.info("🚀 GLaDOS: Trading operations now active!")
    
    async def _on_system_error(self, data: Any) -> None:
        """Handle system error events - GLaDOS intervention may be needed"""
        logger.error(f"System error reported: {data}")
        # TODO: Decide if GLaDOS needs to intervene or let modules handle it
    
    async def _on_shutdown_request(self, data: Any) -> None:
        """Handle shutdown requests from modules"""
        logger.info(f"Shutdown requested by module: {data}")
        await self.shutdown()
    
    async def _on_module_shutdown_complete(self, data: Any) -> None:
        """Handle module shutdown completion notifications"""
        module_name = data.get("module", "unknown")
        message = data.get("message", "")
        
        logger.info(f"Module shutdown complete: {module_name} - {message}")
        
        if module_name in self.modules_ready:
            self.modules_ready[module_name] = False
    
    async def run(self) -> None:
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
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the trading system with ordered sequence"""
        logger.info("GLaDOS initiating system shutdown...")
        
        self.running = False
        
        # Send terminate message to all modules
        event_bus = self.app.get_event_bus()
        await event_bus.publish("system_terminate", {
            "timestamp": asyncio.get_event_loop().time(),
            "message": "System shutdown initiated - all modules should terminate gracefully",
            "timeout": 30  # Give modules 30 seconds to shutdown
        })
        
        # Ordered shutdown sequence
        shutdown_order = ["marvin", "haro", "veda", "walle", "greta"]
        
        logger.info("Beginning ordered shutdown sequence...")
        for module_name in shutdown_order:
            if self.modules_ready.get(module_name, False):
                logger.info(f"Waiting for {module_name} to shutdown...")
                # Give each module time to shutdown gracefully
                await asyncio.sleep(1)
        
        # Give modules time to complete shutdown
        logger.info("Waiting for all modules to complete shutdown...")
        await asyncio.sleep(3)
        
        # Check which modules completed shutdown
        completed = [name for name, ready in self.modules_ready.items() if not ready]
        still_running = [name for name, ready in self.modules_ready.items() if ready]
        
        if completed:
            logger.info(f"Modules shutdown complete: {completed}")
        if still_running:
            logger.warning(f"Modules still running (timeout): {still_running}")
        
        # Shutdown core application
        await self.app.shutdown()
        
        logger.info("GLaDOS shutdown complete - System offline")
        
        # Exit the program
        sys.exit(0)

"""
Event-Driven Module Communication Architecture

GLaDOS Role:
- System initialization and shutdown coordination
- Basic health monitoring 
- Emergency intervention when needed
- Minimal event subscriptions (system-level only)

Module Autonomy:
- Modules communicate directly via events
- Each module manages its own lifecycle
- Business logic is decentralized

Example Event Flow:
1. GLaDOS publishes "system_init" → all modules start
2. Marvin publishes "strategy_load_request" → strategies initialize
3. Strategy publishes "trading_platform_request" → Veda responds
4. Veda publishes "platform_available" → strategies receive
5. Strategy publishes "market_data_request" → WallE/Veda respond
6. Continuous autonomous communication...
7. GLaDOS publishes "system_terminate" → all modules shutdown

Key Events:
- system_init: GLaDOS signals system startup
- system_terminate: GLaDOS signals shutdown
- system_heartbeat: Health monitoring
- system_error: Error reporting to GLaDOS
- module_shutdown_request: Request GLaDOS to shutdown system

Module-to-Module Events (examples):
- strategy_load_request, trading_platform_request, market_data_request
- platform_available, data_available, trade_signal, order_filled
- backtest_request, ui_update, portfolio_update, etc.
"""
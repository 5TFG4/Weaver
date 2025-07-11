"""
Core Application Module
Provides the main Application class for system startup and configuration.
"""
import os
from typing import Optional
from core.logger import get_logger
from core.event_bus import EventBus

logger = get_logger(__name__)

class Application:
    """
    Core Application class that handles system startup and configuration.
    This is used by GLaDOS to initialize the system properly.
    """
    
    def __init__(self, env: Optional[str] = None):
        self.env = env or os.getenv("ENV", "production")
        self.event_bus = EventBus()
        self.modules = {}
        self.running = False
        
        logger.info(f"Application initialized in {self.env} mode")
    
    async def startup(self):
        """Initialize and start all core systems"""
        logger.info("Starting core application systems...")
        
        # Initialize event bus
        await self.event_bus.start()
        logger.info("Event bus started")
        
        # TODO: Initialize database connections
        # TODO: Initialize API connections
        # TODO: Start background tasks
        
        self.running = True
        logger.info("Core application systems started successfully")
    
    async def shutdown(self):
        """Gracefully shutdown all systems"""
        logger.info("Shutting down application...")
        
        self.running = False
        
        # Stop event bus
        await self.event_bus.stop()
        
        # TODO: Close database connections
        # TODO: Close API connections
        # TODO: Stop background tasks
        
        logger.info("Application shutdown complete")
    
    def get_event_bus(self) -> EventBus:
        """Get the application's event bus"""
        return self.event_bus
    
    def is_running(self) -> bool:
        """Check if the application is running"""
        return self.running

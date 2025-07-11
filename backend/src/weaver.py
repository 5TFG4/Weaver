#!/usr/bin/env python3
"""
Weaver Trading Bot - Main Entry Point
Event-driven autonomous trading system with modular architecture.
"""

import asyncio
import signal
import sys
import argparse
import os

from core.logger import get_logger
from modules.glados import GLaDOS

logger = get_logger(__name__, log_file='main.log')


class WeaverApp:
    """Main application wrapper for Weaver trading system"""
    
    def __init__(self, env: str = "production"):
        self.env = env
        self.glados: GLaDOS = GLaDOS()
        self.shutdown_event = asyncio.Event()
        
    async def start(self) -> None:
        """Start the Weaver trading system"""
        logger.info("🤖 Starting Weaver Trading Bot - Event-Driven Architecture")
        logger.info(f"Environment: {self.env}")
        logger.info("=" * 60)
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        try:
            # Start GLaDOS and run the main event loop
            await self.glados.run()
            
        except Exception as e:
            logger.error(f"💥 Fatal error during startup: {e}")
            await self.shutdown()
            raise
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig: int, frame: object) -> None:
            logger.info(f"\n🛑 Signal {sig} received - initiating graceful shutdown")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the trading system"""
        logger.info("🛑 Shutting down Weaver trading system...")
        
        try:
            # Shutdown GLaDOS (which will coordinate module shutdown)
            await self.glados.shutdown()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        finally:
            logger.info("👋 Weaver shutdown complete")
            self.shutdown_event.set()


async def main():
    """Main entry point for the Weaver trading system"""
    parser = argparse.ArgumentParser(description="Weaver Trading Bot")
    parser.add_argument(
        "--env", 
        type=str, 
        choices=["development", "production"],
        default=os.getenv("ENV", "production"),
        help="Environment mode"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Weaver trading system in %s mode", args.env)
    
    # Create and start the application
    app = WeaverApp(env=args.env)
    
    try:
        await app.start()
        
        # Wait for shutdown signal
        await app.shutdown_event.wait()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Keyboard interrupt received")
        await app.shutdown()
    except Exception as e:
        logger.error(f"💥 Application error: {e}")
        await app.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

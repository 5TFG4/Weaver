import asyncio
import os
from core.logger import get_logger
from modules.glados import GLaDOS

logger = get_logger(__name__, log_file='main.log')

async def main():
    """Main entry point for the Weaver trading system"""
    # Read environment variable if needed
    env = os.getenv("ENV", "production")
    logger.info("Starting Weaver trading system in %s mode", env)

    # Initialize GLaDOS as the main application
    glados = GLaDOS(env)
    
    # Run the main application
    await glados.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

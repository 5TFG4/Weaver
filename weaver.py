import asyncio
import logging
import os
from src.GLaDOS.glados import GLaDOS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Read environment variable if needed
    env = os.getenv("ENV", "production")
    logger.info("Starting GLaDOS system in %s mode", env)

    # Initialize the core controller
    glados = GLaDOS()
    
    # Run the main loop (this could also start the FastAPI server and initialize Celery tasks)
    await glados.run()

if __name__ == "__main__":
    asyncio.run(main())

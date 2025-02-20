import asyncio
import os
from src.lib.logger import get_logger
from src.modules.GLaDOS.glados import GLaDOS

# Removed logging.basicConfig & logging.getLogger(__name__)
logger = get_logger(__name__, log_file='main.log')

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

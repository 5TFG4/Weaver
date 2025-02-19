import asyncio
import logging
from .tasks import fetch_data_task  # Celery task import

logger = logging.getLogger("glados")

class GLaDOS:
    def __init__(self):
        self.running = True

    async def run(self):
        logger.info("Dispatching Celery task for BTC/USD...")
        try:
            fetch_data_task.delay("BTC/USD", 1)
        except Exception as e:
            logger.error(f"Failed to dispatch Celery task: {e}")
            self.running = False  # Stop the loop if task dispatch fails
        while self.running:
            await asyncio.sleep(1)

    def stop(self):
        self.running = False

if __name__ == "__main__":
    glados = GLaDOS()
    try:
        asyncio.run(glados.run())
    except KeyboardInterrupt:
        glados.stop()
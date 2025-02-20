import asyncio
from src.lib.logger import get_logger
from .tasks import fetch_data_task  # Celery task import

logger = get_logger("glados")

class GLaDOS:
    def __init__(self):
        self.running = True

    async def run(self):
        logger.info("Dispatching Celery task for BTC/USD...")
        try:
            result = fetch_data_task.delay("BTC/USD")  # Removed sleepTime argument
            logger.info(f"Task dispatched with id: {result.id}")
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
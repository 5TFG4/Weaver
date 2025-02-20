import time
from src.lib.logger import get_logger
from src.config.celery_config import celery_app

logger = get_logger("celery.glados")

@celery_app.task()  # Use namespaced task name
def fetch_data_task(symbol, sleepTime):
    logger.info(f"[Celery] Dummy fetch_data event for symbol: {symbol}")
    time.sleep(sleepTime)
    return f"Fetched data for {symbol}"

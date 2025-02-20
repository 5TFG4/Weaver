import time
import logging
from src.config.celery_config import celery_app

logger = logging.getLogger("celery.veda")

@celery_app.task()  # Use namespaced task name
def fetch_data_task(symbol, sleepTime):
    logger.info(f"[Celery] Dummy fetch_data event for symbol: {symbol}")
    time.sleep(sleepTime)
    return f"Fetched data for {symbol}"

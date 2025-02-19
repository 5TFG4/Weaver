from celery import Celery
import time
import logging

logger = logging.getLogger("celery.glados")

# Update Celery configuration to use Redis as broker and backend.
celery_app = Celery('glados', broker='redis://localhost:6379/0', backend='redis://localhost:6379/1')

@celery_app.task
def fetch_data_task(symbol, sleepTime):
    logger.info(f"[Celery] Dummy fetch_data event for symbol: {symbol}")
    time.sleep(sleepTime)
    return f"Fetched data for {symbol}"

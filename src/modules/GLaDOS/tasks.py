import time
import asyncio
from src.lib.constants import ALPACA
from src.modules.Veda.veda import Veda
from src.lib.logger import get_logger
from src.config.celery_config import celery_app

logger = get_logger("celery.glados")

@celery_app.task()
def fetch_data_task(symbol):
    logger.info(f"[Celery] Fetching data for symbol: {symbol}")
    veda = Veda()
    data = asyncio.run(veda.get_data(ALPACA, symbols=symbol))
    return data

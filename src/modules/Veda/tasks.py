import asyncio
import logging
from src.modules.Veda.veda import Veda
from src.lib.constants import ALPACA
from src.config.celery_config import celery_app

logger = logging.getLogger("celery.veda")

@celery_app.task()
def fetch_data_task(symbol):
    logger.info(f"[Celery] Fetching data for symbol: {symbol}")
    veda = Veda()
    data = asyncio.run(veda.get_data(ALPACA, symbol=symbol))
    return data

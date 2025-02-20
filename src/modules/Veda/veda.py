import os

from src.lib.constants import ALPACA

from .alpaca_api_handler import AlpacaApiHandler
# Other API imports...

class Veda:
    def __init__(self):
        # Read ENV
        alpaca_api_key = os.getenv('ALPACA_PAPER_API_KEY')
        alpaca_api_secret = os.getenv('ALPACA_PAPER_API_SECRET')

        self.handlers = {
            ALPACA: AlpacaApiHandler(api_key=alpaca_api_key, api_secret=alpaca_api_secret),
            # Init other API handler...
        }

    async def get_data(self, source, *args, **kwargs):
        handler = self.handlers.get(source)
        if handler:
            return await handler.get_data(*args, **kwargs)
        else:
            raise ValueError(f"API handler for {source} not found")

    async def place_order(self, source, *args, **kwargs):
        handler = self.handlers.get(source)
        if handler:
            return await handler.place_order(*args, **kwargs)
        else:
            raise ValueError(f"API handler for {source} not found")
        
    async def get_account_details(self, source, *args, **kwargs):
        handler = self.handlers.get(source)
        if handler:
            return await handler.get_account_details(*args, **kwargs)
        else:
            raise ValueError(f"API handler for {source} not found")
        
    async def get_assets(self, source, *args, **kwargs):
        handler = self.handlers.get(source)
        if handler:
            return await handler.get_assets(*args, **kwargs)
        else:
            raise ValueError(f"API handler for {source} not found")
        
    async def submit_market_order(self, source, *args, **kwargs):
        handler = self.handlers.get(source)
        if handler:
            return await handler.submit_market_order(*args, **kwargs)
        else:
            raise ValueError(f"API handler for {source} not found")

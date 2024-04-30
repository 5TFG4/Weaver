class ApiHandler:
    def __init__(self, veda):
        self.veda = veda

    async def get_stock_data(self, source, symbols, start_date):
        # Use Veda to get stock data
        return await self.veda.get_data(source, symbols, start_date)

    async def place_order(self, source, order_details):
        # Use Veda to place order
        return await self.veda.place_order(source, order_details)
    
    async def get_account_details(self, source):
        # Use Veda to get account details
        return await self.veda.get_account_details(source)
    
    async def get_assets(self, source):
        # Use Veda to get assets info
        return await self.veda.get_assets(source)
    
    async def submit_market_order(self, source, symbol, qty, side):
        # Use Veda to submit market order
        return await self.veda.submit_market_order(source, symbol, qty, side)

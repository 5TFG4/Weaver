class BaseApiHandler:
    def __init__(self):
        pass

    async def get_data(self, *args, **kwargs):
        raise NotImplementedError("This method should be implemented by subclasses.")

    async def place_order(self, *args, **kwargs):
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    async def get_account_details(self, *args, **kwargs):
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    async def get_assets(self, *args, **kwargs):
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    async def submit_market_order(self, *args, **kwargs):
        raise NotImplementedError("This method should be implemented by subclasses.")

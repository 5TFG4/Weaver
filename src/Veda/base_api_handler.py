class BaseApiHandler:
    def __init__(self):
        pass

    async def get_data(self, *args, **kwargs):
        raise NotImplementedError

    async def place_order(self, *args, **kwargs):
        raise NotImplementedError

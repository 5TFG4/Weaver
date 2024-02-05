class ApiHandler:
    def __init__(self, veda):
        self.veda = veda

    async def get_stock_data(self, source, symbols, start_date):
        # 调用Veda模块获取股票数据
        return await self.veda.get_data(source, symbols, start_date)

    async def place_order(self, source, order_details):
        # 调用Veda模块下单
        return await self.veda.place_order(source, order_details)
    
    async def get_account_details(self, source):
        # 调用Veda模块获取账户详情
        return await self.veda.get_account_details(source)
    
    async def get_assets(self, source):
        # 调用Veda模块获取资产信息
        return await self.veda.get_assets(source)

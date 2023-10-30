import asyncio

class GLaDOS:
    async def handle_event(self, event):
        # 处理事件逻辑
        print('test1')
        pass

    async def handle_event2(self, event):
        # 处理事件逻辑
        print('test2')
        pass

    async def get_event(self, time):
        return await asyncio.sleep(time)  # 返回一个延时事件

    async def start(self):
        while True:
            event = await self.get_event(1)
            event2 = await self.get_event(2)
            await self.handle_event(event) 
            await self.handle_event2(event2) 
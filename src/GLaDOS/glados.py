import asyncio

class GLaDOS:
    async def handle_event(self, event):
        # 处理事件逻辑
        print('test')
        pass

    async def get_event(self):
        return await asyncio.sleep(1)  # 返回一个延时事件

    async def start(self):
        while True:
            event = await self.get_event()
            await self.handle_event(event) 
import asyncio
from random import random

class GLaDOS:
    def __init__(self):
        self.stop_event = asyncio.Event()

    async def handle_event(self, event):
        # 处理事件逻辑
        print('test1')
        pass

    async def handle_event2(self, event):
        # 处理事件逻辑
        print('test2')
        if random() < 0.2:
          self.stop_event.set()
        pass

    async def get_event(self, time):
        return await asyncio.sleep(time)  # 返回一个延时事件
    
    async def print_test1_loop(self):
        while not self.stop_event.is_set():
            event1 = await self.get_event(1)
            await self.handle_event(event1)
    
    async def print_test2_loop(self):
        while not self.stop_event.is_set():
            event2 = await self.get_event(2)
            await self.handle_event2(event2)

    async def start(self):
        await asyncio.gather(
            self.print_test1_loop(),
            self.print_test2_loop()  
        )
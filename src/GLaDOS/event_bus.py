import asyncio

class EventBus:
    def __init__(self):
        self.event_handlers = {}

    def register_event(self, event_name, handler):
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)

    def emit_event(self, event_name, *args, **kwargs):
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            # 使用 loop.create_task 以保证 "fire and forget"
            loop = asyncio.get_event_loop()
            loop.create_task(handler(*args, **kwargs))

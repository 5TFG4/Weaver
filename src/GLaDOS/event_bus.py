import asyncio

class EventBus:
    def __init__(self):
        self.event_handlers = {}

    def register_event(self, event_name, handler):
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)

    async def emit_event(self, event_name, *args, **kwargs):
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            asyncio.create_task(handler(*args, **kwargs))

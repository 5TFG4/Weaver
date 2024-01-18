import asyncio
import time

class EventBus:
    def __init__(self, min_interval=6):
        self.event_handlers = {}
        self.last_execution_time = {}
        self.pending_events = {}

        self.min_interval = min_interval

    def register_event(self, event_name, handler):
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
            self.last_execution_time[event_name] = 0
        self.event_handlers[event_name].append(handler)

    def emit_event(self, event_name, *args, **kwargs):
        current_time = time.time()
        if current_time - self.last_execution_time[event_name] >= self.min_interval:
            self.trigger_event(event_name, *args, **kwargs)
            self.last_execution_time[event_name] = current_time
        else:
            if event_name not in self.pending_events:
                self.pending_events[event_name] = (args, kwargs)
                asyncio.create_task(self.trigger_event_after_delay(event_name))
            else:
                self.pending_events[event_name] = (args, kwargs)

    async def trigger_event_after_delay(self, event_name):
        await asyncio.sleep(self.min_interval - (time.time() - self.last_execution_time[event_name]))
        if event_name in self.pending_events:
            args, kwargs = self.pending_events.pop(event_name)
            self.trigger_event(event_name, *args, **kwargs)
            self.last_execution_time[event_name] = time.time()

    def trigger_event(self, event_name, *args, **kwargs):
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            loop = asyncio.get_event_loop()
            loop.create_task(handler(*args, **kwargs))
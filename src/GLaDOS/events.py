from asyncio import Queue

event_queue = Queue()

class BaseEvent:
  def __init__(self, data):
    self.data = data

class TickEvent(BaseEvent):
  def __init__(self):
    super().__init__('Tick', {})

async def get_event():
  return await event_queue.get()

def add_event(event):
  event_queue.put(event)
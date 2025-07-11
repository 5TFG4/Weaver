"""
Event Bus Module
Provides internal message passing system for module communication.
"""

import asyncio
from typing import Dict, List, Callable, Any, Union, Awaitable
from core.logger import get_logger

logger = get_logger(__name__)

# Type alias for event callbacks
EventCallback = Callable[[Any], Union[None, Awaitable[None]]]

class EventBus:
    """
    Internal event bus for module communication.
    Replaces Celery for internal message passing.
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[EventCallback]] = {}
        self.running = False
        
    async def start(self) -> None:
        """Start the event bus"""
        self.running = True
        logger.info("Event bus started")
        
    async def stop(self) -> None:
        """Stop the event bus"""
        self.running = False
        logger.info("Event bus stopped")
        
    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type}")
        
    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from event: {event_type}")
                
    async def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribers"""
        if not self.running:
            logger.warning(f"Event bus not running, discarding event: {event_type}")
            return
            
        if event_type in self.subscribers:
            logger.debug(f"Publishing event: {event_type} to {len(self.subscribers[event_type])} subscribers")
            
            # Call all subscribers
            for callback in self.subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event callback for {event_type}: {e}")
        else:
            logger.debug(f"No subscribers for event: {event_type}")
            
    def list_events(self) -> List[str]:
        """List all registered event types"""
        return list(self.subscribers.keys())
        
    def get_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for an event type"""
        return len(self.subscribers.get(event_type, []))

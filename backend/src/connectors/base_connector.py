"""
Base Connector Classes

Provides abstract base classes for all trading platform and data source connectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from core.event_bus import EventBus

class ConnectorStatus(Enum):
    """Status of connector connection"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class ConnectorConfig:
    """Base configuration for all connectors"""
    name: str
    enabled: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    parameters: Dict[str, Any] = field(default_factory=lambda: {})

class BaseConnector(ABC):
    """
    Abstract base class for all connectors.
    
    Provides common functionality for connection management, 
    error handling, and event communication.
    """
    
    def __init__(self, config: ConnectorConfig, event_bus: Optional["EventBus"] = None) -> None:
        self.config = config
        self.event_bus = event_bus
        self.status = ConnectorStatus.DISCONNECTED
        self._connection_task: Optional[asyncio.Task[None]] = None
        self._retry_count = 0
        
    @property
    def name(self) -> str:
        """Get connector name"""
        return self.config.name
        
    @property
    def is_connected(self) -> bool:
        """Check if connector is connected"""
        return self.status == ConnectorStatus.CONNECTED
        
    @property
    def is_enabled(self) -> bool:
        """Check if connector is enabled"""
        return self.config.enabled
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the external service.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the external service"""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if connection is healthy.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        pass
        
    async def start(self) -> None:
        """Start the connector"""
        if not self.is_enabled:
            return
            
        await self._connect_with_retry()
        
    async def stop(self) -> None:
        """Stop the connector"""
        if self._connection_task and not self._connection_task.done():
            self._connection_task.cancel()
            
        await self.disconnect()
        self.status = ConnectorStatus.DISCONNECTED
        
    async def _connect_with_retry(self) -> None:
        """Connect with retry logic"""
        self._retry_count = 0
        
        while self._retry_count < self.config.retry_attempts:
            try:
                self.status = ConnectorStatus.CONNECTING
                await self._publish_status_update()
                
                success = await self.connect()
                
                if success:
                    self.status = ConnectorStatus.CONNECTED
                    self._retry_count = 0
                    await self._publish_status_update()
                    return
                else:
                    raise Exception(f"Connection failed for {self.name}")
                    
            except Exception as e:
                self._retry_count += 1
                self.status = ConnectorStatus.ERROR
                await self._publish_status_update()
                
                if self._retry_count < self.config.retry_attempts:
                    await asyncio.sleep(self.config.retry_delay * self._retry_count)
                else:
                    raise Exception(f"Failed to connect {self.name} after {self.config.retry_attempts} attempts: {e}")
                    
    async def _publish_status_update(self) -> None:
        """Publish status update to event bus"""
        if self.event_bus:
            await self.event_bus.publish("connector_status_update", {
                "connector_name": self.name,
                "status": self.status.value,
                "retry_count": self._retry_count,
                "is_connected": self.is_connected
            })
            
    async def _publish_error(self, error: Exception) -> None:
        """Publish error to event bus"""
        if self.event_bus:
            await self.event_bus.publish("connector_error", {
                "connector_name": self.name,
                "error": str(error),
                "status": self.status.value
            })

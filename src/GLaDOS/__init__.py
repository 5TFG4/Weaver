# #from .glados_core import GLaDOSCore
# from ..models import Trade
# #from .trading_engine import TradingEngine
# from .event_handlers import EventHandler
import enum

ALPINE_RELEASE_FILE = "/etc/alpine-release"

class CoreState(enum.Enum):
    """Represent the current state of Weaver."""

    not_running = "NOT_RUNNING"
    starting = "STARTING"
    running = "RUNNING"
    stopping = "STOPPING"
    final_write = "FINAL_WRITE"
    stopped = "STOPPED"

    def __str__(self) -> str:
        """Return the event."""
        return self.value

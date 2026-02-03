"""
Domain Router

Routes strategy events to appropriate domain handlers.
Strategy events are mode-agnostic; the router determines
whether to route to backtest or live handlers.
"""

from typing import TYPE_CHECKING

from src.events.protocol import Envelope
from src.glados.schemas import RunMode

if TYPE_CHECKING:
    from src.events.log import EventLog
    from src.glados.services.run_manager import RunManager


# Mapping from strategy event types to routed event types
# The domain prefix (backtest. or live.) is prepended by the router
EVENT_TYPE_MAPPING = {
    "strategy.FetchWindow": "FetchWindow",
    "strategy.PlaceRequest": "PlaceOrder",
}


class DomainRouter:
    """
    Routes strategy events to appropriate domain.
    
    For backtest runs:
        strategy.FetchWindow → backtest.FetchWindow
        strategy.PlaceRequest → backtest.PlaceOrder
        
    For live/paper runs:
        strategy.FetchWindow → live.FetchWindow
        strategy.PlaceRequest → live.PlaceOrder
    
    The router preserves event chain (causation_id, corr_id).
    """

    def __init__(
        self,
        event_log: "EventLog",
        run_manager: "RunManager",
    ) -> None:
        """
        Initialize DomainRouter.
        
        Args:
            event_log: Event log for emitting routed events
            run_manager: Run manager for looking up run mode
        """
        self._event_log = event_log
        self._run_manager = run_manager

    async def route(self, event: Envelope) -> None:
        """
        Route a strategy event to the correct domain.
        
        Only processes events with type starting with "strategy.".
        Other events are ignored.
        
        Args:
            event: The event to potentially route
        """
        # Only process strategy events
        if not event.type.startswith("strategy."):
            return

        # Need run_id to look up mode
        if event.run_id is None:
            return

        # Look up run to determine mode
        run = await self._run_manager.get(event.run_id)
        if run is None:
            return

        # Determine target domain based on run mode
        if run.mode == RunMode.BACKTEST:
            target_domain = "backtest"
        else:
            # PAPER and LIVE both use live handlers
            target_domain = "live"

        # Get the base event type (without domain prefix)
        base_type = EVENT_TYPE_MAPPING.get(event.type)
        if base_type is None:
            # Unknown strategy event type, ignore
            return

        # Create new event type with domain prefix
        new_type = f"{target_domain}.{base_type}"

        # Create routed event preserving chain
        routed = Envelope(
            type=new_type,
            payload=event.payload,
            run_id=event.run_id,
            corr_id=event.corr_id,
            causation_id=event.id,
            producer="glados.router",
        )

        await self._event_log.append(routed)

"""
VedaService - Live Trading Service

Main entry point for Veda module. Orchestrates:
- OrderManager for order lifecycle
- OrderRepository for persistence
- PositionTracker for position tracking
- EventLog for event emission
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from src.events.protocol import Envelope
from src.veda.interfaces import ExchangeAdapter
from src.veda.models import OrderIntent, OrderState, OrderStatus, Position
from src.veda.order_manager import OrderManager
from src.veda.persistence import OrderRepository
from src.veda.position_tracker import PositionTracker

if TYPE_CHECKING:
    from src.config import WeaverConfig
    from src.events.log import EventLog


class VedaService:
    """
    Main Veda service - entry point for live trading.

    Orchestrates:
    - OrderManager for order lifecycle
    - OrderRepository for persistence
    - PositionTracker for P&L tracking
    - EventLog for event emission

    Usage:
        adapter = create_alpaca_adapter(config.alpaca.get_credentials("paper"))
        repository = OrderRepository(session_factory)
        service = VedaService(adapter, event_log, repository, config)

        # Place order (persists + emits event)
        state = await service.place_order(intent)
    """

    def __init__(
        self,
        adapter: ExchangeAdapter,
        event_log: "EventLog",
        repository: OrderRepository,
        config: "WeaverConfig",
    ) -> None:
        """
        Initialize VedaService.

        Args:
            adapter: Exchange adapter (AlpacaAdapter or MockExchangeAdapter)
            event_log: EventLog for emitting order events
            repository: OrderRepository for persistence
            config: Application configuration
        """
        self._adapter = adapter
        self._event_log = event_log
        self._repository = repository
        self._config = config

        # Internal components
        self._order_manager = OrderManager(adapter)
        self._position_tracker = PositionTracker()

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def connect(self) -> None:
        """
        Connect to the exchange.

        Delegates to the adapter's connect() method.
        """
        await self._adapter.connect()

    async def disconnect(self) -> None:
        """
        Disconnect from the exchange.

        Delegates to the adapter's disconnect() method.
        """
        await self._adapter.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if connected to the exchange."""
        return self._adapter.is_connected

    # =========================================================================
    # Order Operations
    # =========================================================================

    async def place_order(self, intent: OrderIntent) -> OrderState:
        """
        Place an order with full persistence and event emission.

        This is the main entry point for order placement:
        1. Submit via OrderManager (includes idempotency check)
        2. Persist to database via OrderRepository (only for new orders)
        3. Emit orders.Created or orders.Rejected event (only for new orders)

        Args:
            intent: The order intent

        Returns:
            OrderState tracking the order
        """
        # Check if order already exists (idempotency)
        existing = self._order_manager.get_order(intent.client_order_id)
        if existing is not None:
            return existing

        # 1. Submit order to exchange
        state = await self._order_manager.submit_order(intent)

        # 2. Persist to database
        await self._repository.save(state)

        # 3. Emit event
        if state.status == OrderStatus.REJECTED:
            event_type = "orders.Rejected"
        else:
            event_type = "orders.Created"
        await self._emit_order_event(event_type, state)

        return state

    async def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            client_order_id: The client order ID

        Returns:
            True if cancelled successfully
        """
        # Get current state
        state = self._order_manager.get_order(client_order_id)
        if state is None:
            return False

        # Cancel via OrderManager
        success = await self._order_manager.cancel_order(client_order_id)

        if success:
            # Update persisted state
            updated_state = self._order_manager.get_order(client_order_id)
            if updated_state:
                await self._repository.save(updated_state)
                await self._emit_order_event("orders.Cancelled", updated_state)

        return success

    async def get_order(self, client_order_id: str) -> OrderState | None:
        """
        Get order by client order ID.

        Checks local state first, falls back to repository.

        Args:
            client_order_id: The client order ID

        Returns:
            OrderState if found
        """
        # Check local state first (faster)
        state = self._order_manager.get_order(client_order_id)
        if state is not None:
            return state

        # Fall back to repository
        return await self._repository.get_by_client_order_id(client_order_id)

    async def list_orders(self, run_id: str | None = None) -> list[OrderState]:
        """
        List orders, optionally filtered by run_id.

        Args:
            run_id: Optional run ID filter

        Returns:
            List of OrderState
        """
        if run_id:
            return await self._repository.list_by_run_id(run_id)
        return self._order_manager.list_orders()

    # =========================================================================
    # Position Operations
    # =========================================================================

    def get_positions(self) -> list[Position]:
        """Get all tracked positions."""
        return self._position_tracker.get_all_positions()

    def get_position(self, symbol: str) -> Position | None:
        """Get position for a symbol."""
        return self._position_tracker.get_position(symbol)

    # =========================================================================
    # Account Operations
    # =========================================================================

    async def get_account(self) -> Any:
        """Get account information from exchange."""
        return await self._adapter.get_account()

    # =========================================================================
    # Event Handling (for GLaDOS routing)
    # =========================================================================

    async def handle_place_order(self, envelope: Envelope) -> None:
        """
        Handle live.PlaceOrder event.

        Extracts OrderIntent from payload and delegates to place_order.
        """
        payload = envelope.payload
        intent = OrderIntent(
            run_id=payload["run_id"],
            client_order_id=payload["client_order_id"],
            symbol=payload["symbol"],
            side=payload["side"],
            order_type=payload["order_type"],
            qty=payload["qty"],
            limit_price=payload.get("limit_price"),
            stop_price=payload.get("stop_price"),
            time_in_force=payload.get("time_in_force", "gtc"),
        )
        await self.place_order(intent)

    async def handle_cancel_order(self, envelope: Envelope) -> None:
        """Handle live.CancelOrder event."""
        client_order_id = envelope.payload["client_order_id"]
        await self.cancel_order(client_order_id)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _emit_order_event(self, event_type: str, state: OrderState) -> None:
        """Emit an order event to the event log."""
        envelope = Envelope(
            type=event_type,
            producer="veda",
            run_id=state.run_id,
            payload={
                "order_id": state.id,
                "client_order_id": state.client_order_id,
                "exchange_order_id": state.exchange_order_id,
                "symbol": state.symbol,
                "side": state.side.value,
                "order_type": state.order_type.value,
                "qty": str(state.qty),
                "status": state.status.value,
                "filled_qty": str(state.filled_qty),
                "filled_avg_price": str(state.filled_avg_price) if state.filled_avg_price else None,
                "reject_reason": state.reject_reason,
            },
        )
        await self._event_log.append(envelope)


# =============================================================================
# Factory Functions
# =============================================================================


def create_veda_service(
    adapter: ExchangeAdapter,
    event_log: "EventLog",
    session_factory: Callable[[], Any],
    config: "WeaverConfig",
) -> VedaService:
    """
    Factory function to create VedaService with all dependencies.

    Args:
        adapter: Exchange adapter
        event_log: EventLog instance
        session_factory: Database session factory
        config: Application configuration

    Returns:
        Configured VedaService instance
    """
    repository = OrderRepository(session_factory)
    return VedaService(
        adapter=adapter,
        event_log=event_log,
        repository=repository,
        config=config,
    )

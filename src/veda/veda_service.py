"""
VedaService - Live Trading Service

Main entry point for Veda module. Orchestrates:
- OrderManager for order lifecycle
- OrderRepository for persistence
- PositionTracker for position tracking
- EventLog for event emission
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import WeaverConfig
from src.events.log import EventLog
from src.events.protocol import Envelope
from src.events.types import OrderEvents
from src.veda.interfaces import ExchangeAdapter
from src.veda.models import (
    AccountInfo,
    Fill,
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    Position,
    TimeInForce,
)
from src.veda.order_manager import OrderManager
from src.veda.persistence import OrderRepository
from src.veda.position_tracker import PositionTracker
from src.walle.models import FillRecord
from src.walle.repositories.fill_repository import FillRepository


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
        event_log: EventLog,
        repository: OrderRepository,
        config: WeaverConfig,
        fill_repository: FillRepository | None = None,
    ) -> None:
        """
        Initialize VedaService.

        Args:
            adapter: Exchange adapter (AlpacaAdapter or MockExchangeAdapter)
            event_log: EventLog for emitting order events
            repository: OrderRepository for persistence
            config: Application configuration
            fill_repository: Optional FillRepository for fill audit trail (N-03)
        """
        self._adapter = adapter
        self._event_log = event_log
        self._repository = repository
        self._config = config
        self._fill_repository = fill_repository

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
        # This is an O(1) in-memory lookup, not a DB call.
        # OrderManager also has its own idempotency check, but checking here
        # allows us to skip persistence and event emission for duplicates.
        existing = self._order_manager.get_order(intent.client_order_id)
        if existing is not None:
            return existing

        # 1. Submit order to exchange
        state = await self._order_manager.submit_order(intent)

        # 2. Persist to database
        await self._repository.save(state)

        # 3. Emit event
        event_type = "orders.Rejected" if state.status == OrderStatus.REJECTED else "orders.Created"
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
            return await self._hydrate_fills(state)

        # Fall back to repository
        state = await self._repository.get_by_client_order_id(client_order_id)
        if state is None:
            return None
        return await self._hydrate_fills(state)

    async def sync_order(self, client_order_id: str) -> OrderState | None:
        """
        Sync order status from exchange.

        Fetches current status from the exchange adapter, updates
        local state and persists changes.

        Args:
            client_order_id: The client order ID

        Returns:
            Updated OrderState if found, None otherwise
        """
        state = await self.get_order(client_order_id)
        if state is None or state.exchange_order_id is None:
            return state

        exchange_order = await self._adapter.get_order(state.exchange_order_id)
        if exchange_order is None:
            return state

        updated = replace(
            state,
            status=exchange_order.status,
            filled_qty=exchange_order.filled_qty,
            filled_avg_price=exchange_order.filled_avg_price,
            filled_at=exchange_order.updated_at
            if exchange_order.status == OrderStatus.FILLED
            else state.filled_at,
        )

        # Update in-memory state
        self._order_manager.update_order(client_order_id, updated)

        # Persist
        await self._repository.save(updated)

        return updated

    async def list_orders(
        self,
        run_id: str | None = None,
        status: OrderStatus | None = None,
    ) -> list[OrderState]:
        """
        List orders, optionally filtered by run_id.

        Args:
            run_id: Optional run ID filter
            status: Optional status filter

        Returns:
            List of OrderState with persisted fills hydrated when fill_repository
            is configured.
        """
        if run_id:
            states = await self._repository.list_by_run_id(run_id, status=status)
        else:
            states = self._order_manager.list_orders()
            if status is not None:
                states = [state for state in states if state.status == status]

        hydrated: list[OrderState] = []
        for state in states:
            hydrated.append(await self._hydrate_fills(state))
        return hydrated

    # =========================================================================
    # Fill Operations (N-03)
    # =========================================================================

    async def record_fill(self, fill: FillRecord) -> None:
        """
        Persist a fill record for audit trail.

        No-op when fill_repository is not configured.

        Args:
            fill: FillRecord to persist
        """
        if self._fill_repository is not None:
            await self._fill_repository.save(fill)

    async def get_fills(self, order_id: str) -> list[FillRecord]:
        """
        Get fills for an order.

        Returns empty list when fill_repository is not configured.

        Args:
            order_id: The order identifier

        Returns:
            List of FillRecord
        """
        if self._fill_repository is not None:
            return await self._fill_repository.list_by_order(order_id)
        return []

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

    async def get_account(self) -> AccountInfo:
        """Get account information from exchange."""
        return await self._adapter.get_account()

    async def reconcile_run_fills_once(self, run_id: str, after: datetime) -> datetime:
        """Persist new broker fills for a run and emit corresponding order events."""
        if self._fill_repository is None:
            return after

        orders = await self._repository.list_by_run_id(run_id)
        orders_by_exchange_id = {
            state.exchange_order_id: state
            for state in orders
            if state.exchange_order_id is not None
        }
        if not orders_by_exchange_id:
            return after

        overlap_after = after - timedelta(seconds=2)
        activities = await self._adapter.list_trade_activities(after=overlap_after)
        next_after = after
        existing_fill_ids_by_order: dict[str, set[str]] = {}

        for activity in activities:
            next_after = max(next_after, activity.transaction_time)
            state = orders_by_exchange_id.get(activity.order_id)
            if state is None:
                continue

            existing_ids = existing_fill_ids_by_order.get(state.id)
            if existing_ids is None:
                persisted_fills = await self._fill_repository.list_by_order(state.id)
                existing_ids = {record.exchange_fill_id or record.id for record in persisted_fills}
                existing_fill_ids_by_order[state.id] = existing_ids

            if activity.activity_id in existing_ids:
                continue

            fill_record = FillRecord(
                id=activity.activity_id,
                order_id=state.id,
                price=activity.price,
                quantity=activity.qty,
                side=activity.side.value,
                filled_at=activity.transaction_time,
                exchange_fill_id=activity.activity_id,
                commission=None,
                symbol=activity.symbol,
            )
            await self._fill_repository.save(fill_record)
            existing_ids.add(activity.activity_id)

            synced_state = await self.sync_order(state.client_order_id)
            event_state = synced_state or state
            event_type = (
                OrderEvents.PARTIALLY_FILLED
                if activity.activity_type == "partial_fill"
                else OrderEvents.FILLED
            )
            await self._emit_order_event(event_type, event_state)

        return next_after

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
            side=OrderSide(payload["side"]),
            order_type=OrderType(payload["order_type"]),
            qty=Decimal(str(payload["qty"])),
            limit_price=Decimal(str(payload["limit_price"]))
            if payload.get("limit_price")
            else None,
            stop_price=Decimal(str(payload["stop_price"])) if payload.get("stop_price") else None,
            time_in_force=TimeInForce(payload.get("time_in_force", "day")),
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

    async def _hydrate_fills(self, state: OrderState) -> OrderState:
        """
        Attach persisted fill history to an OrderState.

        N-03: Ensures repository round-trip includes order fills.

        Canonical lookup key is Veda internal order ID (state.id), not
        client_order_id.

        Note: Historical fills may have NULL commission/symbol until M14 data
        is backfilled via reconciliation.
        """
        if self._fill_repository is None:
            return state

        fill_records = await self._fill_repository.list_by_order(state.id)
        fills = [
            Fill(
                id=record.id,
                order_id=record.order_id,
                qty=record.quantity,
                price=record.price,
                commission=record.commission if record.commission is not None else Decimal("0"),
                timestamp=record.filled_at,
                symbol=record.symbol,
            )
            for record in fill_records
        ]
        return replace(state, fills=fills)


# =============================================================================
# Factory Functions
# =============================================================================


def create_veda_service(
    adapter: ExchangeAdapter,
    event_log: EventLog,
    session_factory: async_sessionmaker[AsyncSession],
    config: WeaverConfig,
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
    fill_repository = FillRepository(session_factory)
    return VedaService(
        adapter=adapter,
        event_log=event_log,
        repository=repository,
        config=config,
        fill_repository=fill_repository,
    )

"""
OrderManager - Local Order State Management

Wraps an ExchangeAdapter to:
1. Track OrderState instances locally
2. Provide idempotent order submission (via client_order_id)
3. Maintain consistent view of orders
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.veda.interfaces import ExchangeAdapter
from src.veda.models import (
    OrderIntent,
    OrderState,
    OrderStatus,
)


class OrderManager:
    """
    Manages order state and wraps exchange adapter calls.

    Provides:
    - Local tracking of OrderState instances
    - Idempotent submit_order (tracks by client_order_id)
    - Synchronous order queries (from local state)
    - Async operations for exchange interactions
    """

    def __init__(self, adapter: ExchangeAdapter) -> None:
        """
        Initialize OrderManager with an exchange adapter.

        Args:
            adapter: The exchange adapter for order execution
        """
        self._adapter = adapter
        # Local order state: client_order_id -> OrderState
        self._orders: dict[str, OrderState] = {}

    # =========================================================================
    # Order Submission
    # =========================================================================

    async def submit_order(self, intent: OrderIntent) -> OrderState:
        """
        Submit an order to the exchange.

        Idempotent: If the same client_order_id is submitted again,
        returns the existing OrderState without resubmitting.

        Args:
            intent: The order intent to submit

        Returns:
            OrderState tracking the order
        """
        # Check for existing order (idempotency)
        if intent.client_order_id in self._orders:
            return self._orders[intent.client_order_id]

        # Submit to exchange
        result = await self._adapter.submit_order(intent)
        now = datetime.now(UTC)

        # Create local order state with all required fields
        order_state = OrderState(
            id=str(uuid4()),  # Veda internal ID
            client_order_id=intent.client_order_id,
            exchange_order_id=result.exchange_order_id,
            run_id=intent.run_id,
            symbol=intent.symbol,
            side=intent.side,
            order_type=intent.order_type,
            qty=intent.qty,
            limit_price=intent.limit_price,
            stop_price=intent.stop_price,
            time_in_force=intent.time_in_force,
            status=result.status,
            filled_qty=Decimal("0"),
            filled_avg_price=None,
            created_at=now,
            submitted_at=now,  # Submitted now
            filled_at=None,
            cancelled_at=None,
            reject_reason=result.error_message if not result.success else None,
            error_code=result.error_code if not result.success else None,
        )

        # If the exchange reports the order as FILLED, hydrate fill details.
        # NOTE:
        #   Many exchanges return only basic information from submit_order
        #   (e.g. status + exchange_order_id) and require a follow-up query
        #   to retrieve full execution details such as filled quantity and
        #   average fill price. This extra get_order call is therefore
        #   intentional, even though it adds an additional API call and
        #   some latency.
        #
        #   If the ExchangeAdapter.submit_order implementation is enhanced
        #   in the future to always return filled quantities and prices
        #   when an order is immediately FILLED, this block can be updated
        #   to avoid the redundant query (e.g. by checking for existing
        #   fill information on result before calling get_order).
        if result.status == OrderStatus.FILLED and result.exchange_order_id:
            # Query exchange for fill details
            exchange_order = await self._adapter.get_order(result.exchange_order_id)
            if exchange_order is not None:
                order_state.filled_qty = exchange_order.filled_qty
                order_state.filled_avg_price = exchange_order.filled_avg_price
                order_state.filled_at = now

        # Track locally
        self._orders[intent.client_order_id] = order_state

        return order_state

    # =========================================================================
    # Order Cancellation
    # =========================================================================

    async def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            client_order_id: The client order ID to cancel

        Returns:
            True if cancellation succeeded, False otherwise
        """
        # Check if we're tracking this order
        order_state = self._orders.get(client_order_id)
        if order_state is None:
            return False

        # Can't cancel orders without exchange_order_id
        if order_state.exchange_order_id is None:
            return False

        # Try to cancel on exchange
        success = await self._adapter.cancel_order(order_state.exchange_order_id)

        if success:
            # Update local state
            order_state.status = OrderStatus.CANCELLED
            order_state.cancelled_at = datetime.now(UTC)

        return success

    # =========================================================================
    # Order Queries (Local)
    # =========================================================================

    def get_order(self, client_order_id: str) -> OrderState | None:
        """
        Get local order state by client_order_id.

        Args:
            client_order_id: The client order ID

        Returns:
            OrderState if found, None otherwise
        """
        return self._orders.get(client_order_id)

    def list_orders(self) -> list[OrderState]:
        """
        List all locally tracked orders.

        Returns:
            List of all tracked OrderState instances
        """
        return list(self._orders.values())

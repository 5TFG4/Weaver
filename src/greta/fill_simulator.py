"""
Fill Simulator

Simulates order fills with slippage and commission for backtesting.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from src.greta.models import FillSimulationConfig, SimulatedFill
from src.veda.models import OrderIntent, OrderSide, OrderType

if TYPE_CHECKING:
    from src.walle.repositories.bar_repository import Bar


class DefaultFillSimulator:
    """
    Default fill simulator with slippage and fees.
    
    Fill Models:
    - MARKET orders: Fill at bar open/close + slippage
    - LIMIT BUY: Fill if low <= limit_price
    - LIMIT SELL: Fill if high >= limit_price
    - STOP BUY: Trigger when high >= stop_price
    - STOP SELL: Trigger when low <= stop_price
    """

    def simulate_fill(
        self,
        intent: OrderIntent,
        current_bar: Bar,
        config: FillSimulationConfig,
    ) -> SimulatedFill | None:
        """
        Simulate a fill given current bar.
        
        Args:
            intent: Order intent from strategy
            current_bar: Current OHLCV bar
            config: Fill simulation configuration
            
        Returns:
            SimulatedFill if order can be filled, None otherwise
        """
        # Determine base fill price based on order type
        base_price = self._get_base_price(intent, current_bar, config)
        
        if base_price is None:
            return None  # Order cannot fill

        # Apply slippage (always unfavorable to trader)
        slippage_amount = self._calculate_slippage(base_price, intent.side, config)
        
        if intent.side == OrderSide.BUY:
            fill_price = base_price + slippage_amount
        else:
            fill_price = base_price - slippage_amount

        # Calculate commission
        commission = self._calculate_commission(intent.qty, fill_price, config)

        return SimulatedFill(
            order_id=intent.client_order_id,
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side.value,
            qty=intent.qty,
            fill_price=fill_price,
            commission=commission,
            slippage=abs(slippage_amount * intent.qty),
            timestamp=current_bar.timestamp,
            bar_index=0,  # Set by caller
        )

    def _get_base_price(
        self,
        intent: OrderIntent,
        bar: Bar,
        config: FillSimulationConfig,
    ) -> Decimal | None:
        """
        Get base fill price based on order type.
        
        Returns None if order cannot fill.
        """
        if intent.order_type == OrderType.MARKET:
            return self._get_market_price(bar, config)

        elif intent.order_type == OrderType.LIMIT:
            if not self._limit_can_fill(intent, bar):
                return None
            return intent.limit_price

        elif intent.order_type == OrderType.STOP:
            if not self._stop_triggered(intent, bar):
                return None
            return intent.stop_price

        # STOP_LIMIT not implemented yet
        return None

    def _get_market_price(self, bar: Bar, config: FillSimulationConfig) -> Decimal:
        """Get fill price for market order based on config."""
        if config.fill_at == "close":
            return bar.close
        elif config.fill_at == "vwap":
            # VWAP approximation: (high + low + close) / 3
            return (bar.high + bar.low + bar.close) / 3
        elif config.fill_at == "worst":
            # Worst case would need to know side, skip for now
            return bar.open
        else:  # default: "open"
            return bar.open

    def _limit_can_fill(self, intent: OrderIntent, bar: Bar) -> bool:
        """Check if limit order can fill given bar's range."""
        if intent.limit_price is None:
            return False
            
        if intent.side == OrderSide.BUY:
            # Limit buy fills if price drops to or below limit
            return bar.low <= intent.limit_price
        else:  # SELL
            # Limit sell fills if price rises to or above limit
            return bar.high >= intent.limit_price

    def _stop_triggered(self, intent: OrderIntent, bar: Bar) -> bool:
        """Check if stop order is triggered."""
        if intent.stop_price is None:
            return False
            
        if intent.side == OrderSide.BUY:
            # Stop buy triggers when price rises to stop
            return bar.high >= intent.stop_price
        else:  # SELL
            # Stop sell triggers when price falls to stop
            return bar.low <= intent.stop_price

    def _calculate_slippage(
        self,
        price: Decimal,
        side: OrderSide,
        config: FillSimulationConfig,
    ) -> Decimal:
        """
        Calculate slippage amount.
        
        Slippage is always unfavorable:
        - BUY: pay more (positive slippage)
        - SELL: receive less (positive slippage that's subtracted)
        """
        if config.slippage_model == "fixed":
            return price * (config.slippage_bps / Decimal("10000"))
        # Future: implement volume-based, volatility-based models
        return Decimal("0")

    def _calculate_commission(
        self,
        qty: Decimal,
        price: Decimal,
        config: FillSimulationConfig,
    ) -> Decimal:
        """Calculate commission for the trade."""
        notional = qty * price
        commission = notional * (config.commission_bps / Decimal("10000"))
        return max(commission, config.min_commission)

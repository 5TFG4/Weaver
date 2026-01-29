"""
HTTP Mocking Fixtures

Provides utilities for mocking HTTP calls to external services like Alpaca.
Uses respx for httpx-based mocking.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest


@dataclass
class MockBar:
    """Mock OHLCV bar data."""
    
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "t": self.timestamp.isoformat(),
            "o": float(self.open),
            "h": float(self.high),
            "l": float(self.low),
            "c": float(self.close),
            "v": float(self.volume),
        }


@dataclass
class MockOrder:
    """Mock order data."""
    
    id: str
    client_order_id: str
    symbol: str
    qty: Decimal
    side: str
    order_type: str
    status: str
    filled_qty: Decimal = Decimal("0")
    filled_avg_price: Decimal | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "id": self.id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "qty": str(self.qty),
            "side": self.side,
            "type": self.order_type,
            "status": self.status,
            "filled_qty": str(self.filled_qty),
            "filled_avg_price": str(self.filled_avg_price) if self.filled_avg_price else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class MockAccount:
    """Mock account data."""
    
    id: str = "test-account-id"
    account_number: str = "TEST123456"
    status: str = "ACTIVE"
    currency: str = "USD"
    cash: Decimal = Decimal("100000.00")
    portfolio_value: Decimal = Decimal("100000.00")
    buying_power: Decimal = Decimal("400000.00")  # 4x for margin
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "id": self.id,
            "account_number": self.account_number,
            "status": self.status,
            "currency": self.currency,
            "cash": str(self.cash),
            "portfolio_value": str(self.portfolio_value),
            "buying_power": str(self.buying_power),
        }


class AlpacaMockBuilder:
    """
    Builder for configuring Alpaca API mock responses.
    
    Usage:
        with respx.mock:
            builder = AlpacaMockBuilder()
            builder.with_account(cash=Decimal("50000"))
            builder.with_bars("AAPL", [...])
            
            # Make API calls - they will use mock responses
    """
    
    def __init__(self) -> None:
        self._account = MockAccount()
        self._bars: dict[str, list[MockBar]] = {}
        self._orders: dict[str, MockOrder] = {}
        self._next_order_responses: list[MockOrder] = []
    
    def with_account(
        self,
        cash: Decimal | None = None,
        portfolio_value: Decimal | None = None,
        buying_power: Decimal | None = None,
    ) -> "AlpacaMockBuilder":
        """Configure account mock data."""
        if cash is not None:
            self._account.cash = cash
        if portfolio_value is not None:
            self._account.portfolio_value = portfolio_value
        if buying_power is not None:
            self._account.buying_power = buying_power
        return self
    
    def with_bars(self, symbol: str, bars: list[MockBar]) -> "AlpacaMockBuilder":
        """Configure bar data for a symbol."""
        self._bars[symbol] = bars
        return self
    
    def with_order_response(self, order: MockOrder) -> "AlpacaMockBuilder":
        """Queue an order response for the next order submission."""
        self._next_order_responses.append(order)
        return self
    
    def get_account_response(self) -> dict[str, Any]:
        """Get the mock account response."""
        return self._account.to_dict()
    
    def get_bars_response(self, symbol: str) -> dict[str, Any]:
        """Get the mock bars response for a symbol."""
        bars = self._bars.get(symbol, [])
        return {
            "bars": {symbol: [bar.to_dict() for bar in bars]},
        }
    
    def get_next_order_response(self) -> dict[str, Any] | None:
        """Get and consume the next queued order response."""
        if self._next_order_responses:
            return self._next_order_responses.pop(0).to_dict()
        return None


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def mock_account() -> MockAccount:
    """Provide a default mock account."""
    return MockAccount()


@pytest.fixture
def alpaca_mock_builder() -> AlpacaMockBuilder:
    """Provide an Alpaca mock builder."""
    return AlpacaMockBuilder()


@pytest.fixture
def sample_bars() -> list[MockBar]:
    """Provide sample bar data for testing."""
    base_time = datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc)
    return [
        MockBar(
            timestamp=base_time,
            open=Decimal("150.00"),
            high=Decimal("151.00"),
            low=Decimal("149.50"),
            close=Decimal("150.50"),
            volume=Decimal("1000000"),
        ),
        MockBar(
            timestamp=base_time.replace(minute=31),
            open=Decimal("150.50"),
            high=Decimal("152.00"),
            low=Decimal("150.25"),
            close=Decimal("151.75"),
            volume=Decimal("1200000"),
        ),
        MockBar(
            timestamp=base_time.replace(minute=32),
            open=Decimal("151.75"),
            high=Decimal("152.50"),
            low=Decimal("151.00"),
            close=Decimal("151.25"),
            volume=Decimal("800000"),
        ),
    ]

"""
Adapter Factory Functions

Factory functions for creating exchange adapters from configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.veda.adapters.alpaca_adapter import AlpacaAdapter
from src.veda.adapters.mock_adapter import MockExchangeAdapter

if TYPE_CHECKING:
    from src.config import AlpacaCredentials
    from src.veda.interfaces import ExchangeAdapter


def create_alpaca_adapter(credentials: "AlpacaCredentials") -> AlpacaAdapter:
    """
    Create AlpacaAdapter from AlpacaCredentials.

    This bridges the config layer (AlpacaCredentials) with the
    Veda layer (AlpacaAdapter).

    Args:
        credentials: AlpacaCredentials from config.alpaca.get_credentials()

    Returns:
        Configured AlpacaAdapter instance

    Example:
        config = get_config()
        creds = config.alpaca.get_credentials("paper")
        adapter = create_alpaca_adapter(creds)
    """
    return AlpacaAdapter(
        api_key=credentials.api_key,
        api_secret=credentials.api_secret,
        paper=credentials.is_paper,
    )


def create_mock_adapter() -> MockExchangeAdapter:
    """
    Create MockExchangeAdapter for testing.

    Returns:
        Fresh MockExchangeAdapter instance
    """
    return MockExchangeAdapter()


def create_adapter_for_mode(
    credentials: "AlpacaCredentials | None",
    use_mock: bool = False,
) -> "ExchangeAdapter":
    """
    Create appropriate adapter based on configuration.

    Args:
        credentials: AlpacaCredentials (None if using mock)
        use_mock: Force mock adapter even if credentials provided

    Returns:
        ExchangeAdapter instance
    """
    if use_mock or credentials is None or not credentials.is_configured:
        return create_mock_adapter()
    return create_alpaca_adapter(credentials)

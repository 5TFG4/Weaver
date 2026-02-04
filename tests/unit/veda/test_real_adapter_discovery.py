"""
Tests for Adapter Discovery in Real Adapters Directory

Tests that PluginAdapterLoader correctly discovers AlpacaAdapter and MockExchangeAdapter.
"""

import pytest

from src.veda.adapter_loader import PluginAdapterLoader
from src.veda.adapter_meta import AdapterMeta


class TestRealAdapterDiscovery:
    """Tests for discovering real adapters in src/veda/adapters/."""

    @pytest.fixture
    def loader(self) -> PluginAdapterLoader:
        """Create loader for real adapters directory."""
        return PluginAdapterLoader()

    def test_discovers_alpaca_adapter(self, loader: PluginAdapterLoader) -> None:
        """PluginAdapterLoader discovers AlpacaAdapter."""
        available = loader.list_available()
        assert any(a.id == "alpaca" for a in available)

    def test_discovers_mock_adapter(self, loader: PluginAdapterLoader) -> None:
        """PluginAdapterLoader discovers MockExchangeAdapter."""
        available = loader.list_available()
        assert any(a.id == "mock" for a in available)

    def test_alpaca_metadata_correct(self, loader: PluginAdapterLoader) -> None:
        """AlpacaAdapter has correct metadata."""
        meta = loader.get_metadata("alpaca")
        assert meta is not None
        assert meta.id == "alpaca"
        assert meta.class_name == "AlpacaAdapter"
        assert "paper_trading" in meta.features
        assert "live_trading" in meta.features

    def test_mock_metadata_correct(self, loader: PluginAdapterLoader) -> None:
        """MockExchangeAdapter has correct metadata."""
        meta = loader.get_metadata("mock")
        assert meta is not None
        assert meta.id == "mock"
        assert meta.class_name == "MockExchangeAdapter"
        assert "testing" in meta.features

    def test_load_mock_adapter(self, loader: PluginAdapterLoader) -> None:
        """Can load MockExchangeAdapter via loader."""
        from src.veda.interfaces import ExchangeAdapter

        adapter = loader.load("mock")
        assert adapter is not None
        assert isinstance(adapter, ExchangeAdapter)

    def test_load_alpaca_adapter_with_credentials(
        self, loader: PluginAdapterLoader
    ) -> None:
        """Can load AlpacaAdapter with credentials via loader."""
        from src.veda.interfaces import ExchangeAdapter

        adapter = loader.load(
            "alpaca",
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
        assert adapter is not None
        assert isinstance(adapter, ExchangeAdapter)
        assert adapter.paper is True

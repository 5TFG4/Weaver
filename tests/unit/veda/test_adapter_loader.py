"""
Tests for Plugin Adapter Loader

TDD tests for M6-1: Auto-discovery adapter loading (mirrors PluginStrategyLoader).
"""

from pathlib import Path

import pytest

from src.veda.adapter_meta import AdapterMeta


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_adapter_dir(tmp_path: Path) -> Path:
    """Create temp directory with a basic test adapter file."""
    adapter_dir = tmp_path / "adapters"
    adapter_dir.mkdir()

    # Create basic test adapter file with all required abstract methods
    (adapter_dir / "test_adapter.py").write_text('''
ADAPTER_META = {
    "id": "test-adapter",
    "name": "Test Adapter",
    "version": "1.0.0",
    "class": "TestAdapter",
    "features": ["paper_trading"],
}

from src.veda.interfaces import ExchangeAdapter

class TestAdapter(ExchangeAdapter):
    """A simple test adapter."""

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._connected = False

    async def connect(self):
        self._connected = True
    async def disconnect(self):
        self._connected = False
    @property
    def is_connected(self):
        return self._connected
    async def submit_order(self, intent):
        pass
    async def get_order(self, order_id):
        pass
    async def cancel_order(self, order_id):
        pass
    async def list_orders(self, status=None, symbols=None, limit=100):
        return []
    async def get_account(self):
        pass
    async def get_positions(self):
        return []
    async def get_position(self, symbol):
        return None
    async def get_bars(self, symbol, timeframe, start, end=None, limit=None):
        return []
    async def get_latest_bar(self, symbol):
        return None
    async def get_latest_quote(self, symbol):
        return None
    async def get_latest_trade(self, symbol):
        return None
    async def stream_quotes(self, symbols):
        yield None
    async def stream_bars(self, symbols):
        yield None
''')
    return adapter_dir


@pytest.fixture
def loader(temp_adapter_dir: Path):
    """Create PluginAdapterLoader with temp directory."""
    from src.veda.adapter_loader import PluginAdapterLoader

    return PluginAdapterLoader(plugin_dir=temp_adapter_dir)


# =============================================================================
# Import Tests
# =============================================================================


class TestPluginAdapterLoaderImport:
    """Tests that PluginAdapterLoader is importable."""

    def test_import_adapter_loader(self) -> None:
        """PluginAdapterLoader should be importable from src.veda.adapter_loader."""
        from src.veda.adapter_loader import PluginAdapterLoader

        assert PluginAdapterLoader is not None

    def test_import_adapter_loader_protocol(self) -> None:
        """AdapterLoader protocol should be importable."""
        from src.veda.adapter_loader import AdapterLoader

        assert AdapterLoader is not None


# =============================================================================
# Interface Compliance Tests
# =============================================================================


class TestPluginAdapterLoaderInterface:
    """Tests that PluginAdapterLoader implements AdapterLoader."""

    def test_is_adapter_loader(self, loader) -> None:
        """PluginAdapterLoader should implement AdapterLoader."""
        from src.veda.adapter_loader import AdapterLoader

        assert isinstance(loader, AdapterLoader)

    def test_has_load_method(self, loader) -> None:
        """PluginAdapterLoader should have load method."""
        assert hasattr(loader, "load")
        assert callable(loader.load)

    def test_has_list_available_method(self, loader) -> None:
        """PluginAdapterLoader should have list_available method."""
        assert hasattr(loader, "list_available")
        assert callable(loader.list_available)

    def test_has_get_metadata_method(self, loader) -> None:
        """PluginAdapterLoader should have get_metadata method."""
        assert hasattr(loader, "get_metadata")
        assert callable(loader.get_metadata)


# =============================================================================
# Discovery Tests
# =============================================================================


class TestPluginDiscovery:
    """Tests for adapter auto-discovery."""

    def test_discovers_adapters_in_directory(self, loader) -> None:
        """Scans adapters/ directory and finds all plugins."""
        available = loader.list_available()
        assert len(available) >= 1
        assert any(a.id == "test-adapter" for a in available)

    def test_returns_adapter_meta_objects(self, loader) -> None:
        """list_available returns AdapterMeta objects."""
        available = loader.list_available()
        assert len(available) >= 1
        meta = available[0]
        assert isinstance(meta, AdapterMeta)
        assert hasattr(meta, "id")
        assert hasattr(meta, "name")
        assert hasattr(meta, "class_name")
        assert hasattr(meta, "features")

    def test_extracts_metadata_without_importing(
        self, temp_adapter_dir: Path
    ) -> None:
        """Reads ADAPTER_META without full module import (broken import is OK)."""
        from src.veda.adapter_loader import PluginAdapterLoader

        # Create file with an import that would fail
        (temp_adapter_dir / "broken.py").write_text('''
ADAPTER_META = {
    "id": "broken-adapter",
    "name": "Broken Adapter",
    "version": "1.0.0",
    "class": "BrokenAdapter",
    "features": [],
}

import nonexistent_module_that_does_not_exist  # This would fail on import
''')

        loader = PluginAdapterLoader(plugin_dir=temp_adapter_dir)
        available = loader.list_available()

        # Should still discover the metadata via AST parsing
        assert any(a.id == "broken-adapter" for a in available)

    def test_ignores_files_starting_with_underscore(
        self, temp_adapter_dir: Path
    ) -> None:
        """Files like __init__.py are ignored."""
        from src.veda.adapter_loader import PluginAdapterLoader

        (temp_adapter_dir / "__init__.py").write_text('''
ADAPTER_META = {"id": "init-adapter", "class": "X"}
''')
        (temp_adapter_dir / "_private.py").write_text('''
ADAPTER_META = {"id": "private-adapter", "class": "Y"}
''')

        loader = PluginAdapterLoader(plugin_dir=temp_adapter_dir)
        available = loader.list_available()

        assert not any(a.id == "init-adapter" for a in available)
        assert not any(a.id == "private-adapter" for a in available)

    def test_handles_syntax_error_gracefully(
        self, temp_adapter_dir: Path
    ) -> None:
        """Syntax error in plugin file doesn't crash loader."""
        from src.veda.adapter_loader import PluginAdapterLoader

        (temp_adapter_dir / "syntax_error.py").write_text('''
ADAPTER_META = {"id": "syntax-error", "class": "X"}
def broken(
    # Missing closing paren - syntax error
''')

        # Should not raise, just skip the broken file
        loader = PluginAdapterLoader(plugin_dir=temp_adapter_dir)
        available = loader.list_available()

        # The broken file should be skipped
        assert not any(a.id == "syntax-error" for a in available)
        # But valid adapters should still be discovered
        assert any(a.id == "test-adapter" for a in available)

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """Empty adapter directory returns empty list."""
        from src.veda.adapter_loader import PluginAdapterLoader

        empty_dir = tmp_path / "empty_adapters"
        empty_dir.mkdir()

        loader = PluginAdapterLoader(plugin_dir=empty_dir)
        available = loader.list_available()

        assert available == []

    def test_nonexistent_directory_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        """Non-existent adapter directory returns empty list (no crash)."""
        from src.veda.adapter_loader import PluginAdapterLoader

        loader = PluginAdapterLoader(
            plugin_dir=tmp_path / "does_not_exist"
        )
        available = loader.list_available()

        assert available == []


# =============================================================================
# Metadata Access Tests
# =============================================================================


class TestMetadataAccess:
    """Tests for metadata retrieval."""

    def test_get_metadata_returns_meta(self, loader) -> None:
        """get_metadata returns AdapterMeta for known adapter."""
        meta = loader.get_metadata("test-adapter")
        assert meta is not None
        assert meta.id == "test-adapter"
        assert isinstance(meta, AdapterMeta)

    def test_get_metadata_returns_none_for_unknown(self, loader) -> None:
        """get_metadata returns None for unknown adapter."""
        meta = loader.get_metadata("unknown-adapter")
        assert meta is None

    def test_get_metadata_includes_features(self, loader) -> None:
        """get_metadata includes features list."""
        meta = loader.get_metadata("test-adapter")
        assert meta is not None
        assert "paper_trading" in meta.features


# =============================================================================
# Loading Tests
# =============================================================================


class TestPluginLoading:
    """Tests for adapter loading."""

    def test_load_adapter_by_id(self, loader) -> None:
        """Loads adapter by its declared ID."""
        from src.veda.interfaces import ExchangeAdapter

        adapter = loader.load("test-adapter")
        assert adapter is not None
        assert isinstance(adapter, ExchangeAdapter)

    def test_unknown_adapter_raises_not_found(self, loader) -> None:
        """AdapterNotFoundError for unknown adapter_id."""
        from src.veda.adapter_loader import AdapterNotFoundError

        with pytest.raises(AdapterNotFoundError) as exc:
            loader.load("nonexistent-adapter-id")
        assert "nonexistent-adapter-id" in str(exc.value)

    def test_load_with_credentials(self, loader) -> None:
        """Passes credentials to adapter constructor."""
        adapter = loader.load(
            "test-adapter",
            api_key="my-key",
            api_secret="my-secret",
        )
        assert adapter is not None
        assert adapter._api_key == "my-key"
        assert adapter._api_secret == "my-secret"

    def test_lazy_loading(self, temp_adapter_dir: Path) -> None:
        """Adapter not imported until load() called."""
        import io
        import sys

        from src.veda.adapter_loader import PluginAdapterLoader

        # Create adapter that prints on import
        (temp_adapter_dir / "lazy_test.py").write_text('''
ADAPTER_META = {"id": "lazy", "class": "Lazy", "features": []}
print("LAZY_ADAPTER_IMPORTED_MARKER")
from src.veda.interfaces import ExchangeAdapter
class Lazy(ExchangeAdapter):
    _connected = False
    async def connect(self): self._connected = True
    async def disconnect(self): self._connected = False
    @property
    def is_connected(self): return self._connected
    async def submit_order(self, intent): pass
    async def get_order(self, order_id): pass
    async def cancel_order(self, order_id): pass
    async def list_orders(self, status=None, symbols=None, limit=100): return []
    async def get_account(self): pass
    async def get_positions(self): return []
    async def get_position(self, symbol): return None
    async def get_bars(self, symbol, timeframe, start, end=None, limit=None): return []
    async def get_latest_bar(self, symbol): return None
    async def get_latest_quote(self, symbol): return None
    async def get_latest_trade(self, symbol): return None
    async def stream_quotes(self, symbols): yield None
    async def stream_bars(self, symbols): yield None
''')

        # Capture stdout during initialization
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        try:
            loader = PluginAdapterLoader(plugin_dir=temp_adapter_dir)
            _ = loader.list_available()
        finally:
            sys.stdout = old_stdout

        # Should NOT have imported during discovery
        assert "LAZY_ADAPTER_IMPORTED_MARKER" not in captured.getvalue()


# =============================================================================
# Delete Safety Tests
# =============================================================================


class TestDeleteSafety:
    """Tests for plugin delete safety."""

    def test_deleted_adapter_not_discovered(self, temp_adapter_dir: Path) -> None:
        """Deleted .py file is not in available list."""
        from src.veda.adapter_loader import PluginAdapterLoader

        # Create a file then delete it
        file = temp_adapter_dir / "to_delete.py"
        file.write_text('''
ADAPTER_META = {"id": "to-delete", "class": "ToDelete", "features": []}
from src.veda.interfaces import ExchangeAdapter
class ToDelete(ExchangeAdapter):
    _connected = False
    async def connect(self): self._connected = True
    async def disconnect(self): self._connected = False
    @property
    def is_connected(self): return self._connected
    async def submit_order(self, intent): pass
    async def get_order(self, order_id): pass
    async def cancel_order(self, order_id): pass
    async def list_orders(self, status=None, symbols=None, limit=100): return []
    async def get_account(self): pass
    async def get_positions(self): return []
    async def get_position(self, symbol): return None
    async def get_bars(self, symbol, timeframe, start, end=None, limit=None): return []
    async def get_latest_bar(self, symbol): return None
    async def get_latest_quote(self, symbol): return None
    async def get_latest_trade(self, symbol): return None
    async def stream_quotes(self, symbols): yield None
    async def stream_bars(self, symbols): yield None
''')

        loader1 = PluginAdapterLoader(plugin_dir=temp_adapter_dir)
        assert any(a.id == "to-delete" for a in loader1.list_available())

        # Delete the file
        file.unlink()

        # New loader should not see it
        loader2 = PluginAdapterLoader(plugin_dir=temp_adapter_dir)
        assert not any(a.id == "to-delete" for a in loader2.list_available())

    def test_system_works_after_adapter_deleted(
        self, temp_adapter_dir: Path
    ) -> None:
        """Other adapters still load after one is deleted."""
        from src.veda.adapter_loader import PluginAdapterLoader
        from src.veda.interfaces import ExchangeAdapter

        to_delete = temp_adapter_dir / "to_delete.py"
        to_delete.write_text('''
ADAPTER_META = {"id": "to-delete", "class": "X", "features": []}
''')

        # Delete the file before creating loader
        to_delete.unlink()

        loader = PluginAdapterLoader(plugin_dir=temp_adapter_dir)
        adapter = loader.load("test-adapter")  # Should work
        assert adapter is not None
        assert isinstance(adapter, ExchangeAdapter)

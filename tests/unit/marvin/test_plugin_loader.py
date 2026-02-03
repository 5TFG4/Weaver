"""
Tests for Plugin Strategy Loader

TDD tests for M5-4: Auto-discovery strategy loading with dependency resolution.
"""

from pathlib import Path

import pytest

from src.marvin.base_strategy import BaseStrategy
from src.marvin.exceptions import (
    CircularDependencyError,
    DependencyError,
    StrategyNotFoundError,
)
from src.marvin.strategy_loader import PluginStrategyLoader, StrategyLoader
from src.marvin.strategy_meta import StrategyMeta


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_plugin_dir(tmp_path: Path) -> Path:
    """Create temp directory with a basic test strategy file."""
    plugin_dir = tmp_path / "strategies"
    plugin_dir.mkdir()

    # Create basic test strategy file
    (plugin_dir / "test_strategy.py").write_text('''
STRATEGY_META = {
    "id": "test-strategy",
    "name": "Test Strategy",
    "version": "1.0.0",
    "dependencies": [],
    "class": "TestStrategy",
}

from src.marvin.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    async def on_tick(self, tick):
        return []
    async def on_data(self, data):
        return []
''')
    return plugin_dir


@pytest.fixture
def loader(temp_plugin_dir: Path) -> PluginStrategyLoader:
    """Create PluginStrategyLoader with temp directory."""
    return PluginStrategyLoader(plugin_dir=temp_plugin_dir)


# =============================================================================
# Interface Compliance Tests
# =============================================================================


class TestPluginStrategyLoaderInterface:
    """Tests that PluginStrategyLoader implements StrategyLoader."""

    def test_is_strategy_loader(self, loader: PluginStrategyLoader) -> None:
        """PluginStrategyLoader should implement StrategyLoader."""
        assert isinstance(loader, StrategyLoader)

    def test_has_load_method(self, loader: PluginStrategyLoader) -> None:
        """PluginStrategyLoader should have load method."""
        assert hasattr(loader, "load")
        assert callable(loader.load)

    def test_has_list_available_method(self, loader: PluginStrategyLoader) -> None:
        """PluginStrategyLoader should have list_available method."""
        assert hasattr(loader, "list_available")
        assert callable(loader.list_available)


# =============================================================================
# Discovery Tests
# =============================================================================


class TestPluginDiscovery:
    """Tests for strategy auto-discovery."""

    def test_discovers_strategies_in_directory(
        self, loader: PluginStrategyLoader
    ) -> None:
        """Scans strategies/ directory and finds all plugins."""
        available = loader.list_available()
        assert len(available) >= 1
        assert any(s.id == "test-strategy" for s in available)

    def test_returns_strategy_meta_objects(
        self, loader: PluginStrategyLoader
    ) -> None:
        """list_available returns StrategyMeta objects."""
        available = loader.list_available()
        assert len(available) >= 1
        meta = available[0]
        assert isinstance(meta, StrategyMeta)
        assert hasattr(meta, "id")
        assert hasattr(meta, "name")
        assert hasattr(meta, "class_name")

    def test_extracts_metadata_without_importing(
        self, temp_plugin_dir: Path
    ) -> None:
        """Reads STRATEGY_META without full module import (broken import is OK)."""
        # Create file with an import that would fail
        (temp_plugin_dir / "broken.py").write_text('''
STRATEGY_META = {
    "id": "broken-strategy",
    "name": "Broken Strategy",
    "version": "1.0.0",
    "class": "BrokenStrategy",
}

import nonexistent_module_that_does_not_exist  # This would fail on import
''')

        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        available = loader.list_available()

        # Should still discover the metadata via AST parsing
        assert any(s.id == "broken-strategy" for s in available)

    def test_ignores_files_starting_with_underscore(
        self, temp_plugin_dir: Path
    ) -> None:
        """Files like __init__.py are ignored."""
        (temp_plugin_dir / "__init__.py").write_text('''
STRATEGY_META = {"id": "init-strategy", "class": "X"}
''')
        (temp_plugin_dir / "_private.py").write_text('''
STRATEGY_META = {"id": "private-strategy", "class": "Y"}
''')

        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        available = loader.list_available()

        assert not any(s.id == "init-strategy" for s in available)
        assert not any(s.id == "private-strategy" for s in available)

    def test_handles_syntax_error_gracefully(
        self, temp_plugin_dir: Path
    ) -> None:
        """Syntax error in plugin file doesn't crash loader."""
        (temp_plugin_dir / "syntax_error.py").write_text('''
STRATEGY_META = {"id": "syntax-error", "class": "X"}
def broken(
    # Missing closing paren - syntax error
''')

        # Should not raise, just skip the broken file
        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        available = loader.list_available()

        # The broken file should be skipped
        assert not any(s.id == "syntax-error" for s in available)
        # But valid strategies should still be discovered
        assert any(s.id == "test-strategy" for s in available)

    def test_strategy_meta_without_dependencies_defaults_to_empty(
        self, temp_plugin_dir: Path
    ) -> None:
        """STRATEGY_META without dependencies field defaults to []."""
        (temp_plugin_dir / "no_deps.py").write_text('''
STRATEGY_META = {
    "id": "no-deps",
    "name": "No Dependencies",
    "class": "NoDeps",
}

from src.marvin.base_strategy import BaseStrategy

class NoDeps(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')

        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        available = loader.list_available()

        meta = next(s for s in available if s.id == "no-deps")
        assert meta.dependencies == []


# =============================================================================
# Loading Tests
# =============================================================================


class TestPluginLoading:
    """Tests for strategy loading."""

    def test_load_strategy_by_id(self, loader: PluginStrategyLoader) -> None:
        """Loads strategy by its declared ID."""
        strategy = loader.load("test-strategy")
        assert strategy is not None
        assert isinstance(strategy, BaseStrategy)
        assert hasattr(strategy, "on_tick")
        assert hasattr(strategy, "on_data")

    def test_unknown_strategy_raises_not_found(
        self, loader: PluginStrategyLoader
    ) -> None:
        """StrategyNotFoundError for unknown strategy_id."""
        with pytest.raises(StrategyNotFoundError) as exc:
            loader.load("nonexistent-strategy-id")
        assert "nonexistent-strategy-id" in str(exc.value)

    def test_lazy_loading(self, temp_plugin_dir: Path) -> None:
        """Strategy not imported until load() called."""
        import io
        import sys

        # Create strategy that prints on import
        (temp_plugin_dir / "lazy_test.py").write_text('''
STRATEGY_META = {"id": "lazy", "class": "Lazy"}
print("LAZY_STRATEGY_IMPORTED_MARKER")
from src.marvin.base_strategy import BaseStrategy
class Lazy(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')

        # Capture stdout during initialization
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        try:
            loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
            _ = loader.list_available()
        finally:
            sys.stdout = old_stdout

        # Should NOT have imported during discovery
        assert "LAZY_STRATEGY_IMPORTED_MARKER" not in captured.getvalue()


# =============================================================================
# Dependency Resolution Tests
# =============================================================================


class TestDependencyResolution:
    """Tests for strategy dependency resolution."""

    def test_resolves_dependencies(self, temp_plugin_dir: Path) -> None:
        """Loads dependent strategies before requested strategy."""
        # Create base strategy
        (temp_plugin_dir / "base_sma.py").write_text('''
STRATEGY_META = {
    "id": "base-sma",
    "name": "Base SMA",
    "class": "BaseSMA",
    "dependencies": []
}
from src.marvin.base_strategy import BaseStrategy
class BaseSMA(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')

        # Create dependent strategy
        (temp_plugin_dir / "ensemble.py").write_text('''
STRATEGY_META = {
    "id": "ensemble",
    "name": "Ensemble",
    "class": "Ensemble",
    "dependencies": ["base-sma"]
}
from src.marvin.base_strategy import BaseStrategy
class Ensemble(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')

        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        strategy = loader.load("ensemble")

        # base-sma should be loaded as dependency
        assert "base-sma" in loader._loaded
        assert strategy is not None

    def test_missing_dependency_raises_error(self, temp_plugin_dir: Path) -> None:
        """DependencyError if required strategy not found."""
        (temp_plugin_dir / "needs_missing.py").write_text('''
STRATEGY_META = {
    "id": "needs-missing",
    "name": "Needs Missing",
    "class": "NeedsMissing",
    "dependencies": ["does-not-exist"]
}
from src.marvin.base_strategy import BaseStrategy
class NeedsMissing(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')

        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)

        with pytest.raises(DependencyError) as exc:
            loader.load("needs-missing")
        assert "does-not-exist" in str(exc.value)

    def test_circular_dependency_detected(self, temp_plugin_dir: Path) -> None:
        """CircularDependencyError for A→B→A cycles."""
        (temp_plugin_dir / "cycle_a.py").write_text('''
STRATEGY_META = {
    "id": "cycle-a",
    "name": "Cycle A",
    "class": "CycleA",
    "dependencies": ["cycle-b"]
}
from src.marvin.base_strategy import BaseStrategy
class CycleA(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        (temp_plugin_dir / "cycle_b.py").write_text('''
STRATEGY_META = {
    "id": "cycle-b",
    "name": "Cycle B",
    "class": "CycleB",
    "dependencies": ["cycle-a"]
}
from src.marvin.base_strategy import BaseStrategy
class CycleB(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')

        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)

        with pytest.raises(CircularDependencyError):
            loader.load("cycle-a")


# =============================================================================
# Delete Safety Tests
# =============================================================================


class TestDeleteSafety:
    """Tests for plugin delete safety."""

    def test_deleted_strategy_not_discovered(self, temp_plugin_dir: Path) -> None:
        """Deleted .py file is not in available list."""
        # Create a file then delete it
        file = temp_plugin_dir / "to_delete.py"
        file.write_text('''
STRATEGY_META = {"id": "to-delete", "class": "ToDelete"}
from src.marvin.base_strategy import BaseStrategy
class ToDelete(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')

        loader1 = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        assert any(s.id == "to-delete" for s in loader1.list_available())

        # Delete the file
        file.unlink()

        # New loader should not see it
        loader2 = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        assert not any(s.id == "to-delete" for s in loader2.list_available())

    def test_system_works_after_strategy_deleted(
        self, temp_plugin_dir: Path
    ) -> None:
        """Other strategies still load after one is deleted."""
        (temp_plugin_dir / "keeper.py").write_text('''
STRATEGY_META = {"id": "keeper", "class": "Keeper"}
from src.marvin.base_strategy import BaseStrategy
class Keeper(BaseStrategy):
    async def on_tick(self, tick): return []
    async def on_data(self, data): return []
''')
        to_delete = temp_plugin_dir / "to_delete.py"
        to_delete.write_text('''
STRATEGY_META = {"id": "to-delete", "class": "X"}
''')

        # Delete the file before creating loader
        to_delete.unlink()

        loader = PluginStrategyLoader(plugin_dir=temp_plugin_dir)
        strategy = loader.load("keeper")  # Should work
        assert strategy is not None
        assert isinstance(strategy, BaseStrategy)

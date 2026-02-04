"""
Strategy Loader

Abstract interface and plugin-based implementation for loading strategies.
"""

from __future__ import annotations

import ast
import importlib.util
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from src.marvin.base_strategy import BaseStrategy
from src.marvin.exceptions import (
    CircularDependencyError,
    DependencyError,
    StrategyNotFoundError,
)
from src.marvin.strategy_meta import StrategyMeta

if TYPE_CHECKING:
    from types import ModuleType

logger = logging.getLogger(__name__)


class StrategyLoader(ABC):
    """Abstract strategy loader interface."""

    @abstractmethod
    def load(self, strategy_id: str) -> BaseStrategy:
        """Load a strategy by ID."""
        pass


class SimpleStrategyLoader(StrategyLoader):
    """Simple strategy loader from registry (for backwards compatibility)."""

    def __init__(self) -> None:
        self._strategies: dict[str, type[BaseStrategy]] = {}

    def register(self, strategy_id: str, strategy_class: type[BaseStrategy]) -> None:
        """Register a strategy class."""
        self._strategies[strategy_id] = strategy_class

    def load(self, strategy_id: str) -> BaseStrategy:
        """Load a strategy by ID."""
        if strategy_id not in self._strategies:
            available = ", ".join(self._strategies.keys()) or "(none)"
            raise StrategyNotFoundError(
                f"{strategy_id}. Available: {available}"
            )
        return self._strategies[strategy_id]()


class PluginStrategyLoader(StrategyLoader):
    """
    Auto-discovering strategy loader.

    Scans a plugin directory for strategy files containing STRATEGY_META,
    extracts metadata using AST parsing (without importing), and loads
    strategies on demand with dependency resolution.

    Features:
    - Zero hardcoded imports
    - Lazy loading (import only when load() called)
    - Dependency resolution with cycle detection
    - Delete safety (missing files don't crash system)
    """

    def __init__(self, plugin_dir: Path | None = None) -> None:
        """
        Initialize the plugin loader.

        Args:
            plugin_dir: Directory to scan for strategy plugins.
                       Defaults to src/marvin/strategies/
        """
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent / "strategies"
        self._plugin_dir = plugin_dir
        self._registry: dict[str, StrategyMeta] = {}
        self._loaded: dict[str, type[BaseStrategy]] = {}
        self._scan_plugins()

    def _scan_plugins(self) -> None:
        """Scan plugin directory for strategy metadata (without importing)."""
        if not self._plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {self._plugin_dir}")
            return

        for py_file in self._plugin_dir.rglob("*.py"):
            # Skip files starting with underscore
            if py_file.name.startswith("_"):
                continue

            try:
                meta = self._extract_metadata(py_file)
                if meta and meta.id:
                    self._registry[meta.id] = meta
                    logger.debug(f"Discovered strategy: {meta.id} from {py_file.name}")
            except Exception as e:
                # Log warning but don't fail - plugin is skipped
                logger.warning(f"Failed to scan {py_file}: {e}")

    def _extract_metadata(self, path: Path) -> StrategyMeta | None:
        """
        Extract STRATEGY_META from file using AST parsing.

        This reads the metadata without importing the module,
        so broken imports don't prevent discovery.
        """
        try:
            source = path.read_text()
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {path}: {e}")
            return None

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "STRATEGY_META":
                        # Evaluate the dictionary literal
                        try:
                            meta_dict = ast.literal_eval(node.value)
                            if isinstance(meta_dict, dict):
                                return StrategyMeta.from_dict(meta_dict, path)
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                f"Invalid STRATEGY_META in {path}: {e}"
                            )
                            return None
        return None

    def list_available(self) -> list[StrategyMeta]:
        """List all discovered strategies."""
        return list(self._registry.values())

    def load(self, strategy_id: str) -> BaseStrategy:
        """
        Load a strategy by ID with dependency resolution.

        Args:
            strategy_id: The strategy ID to load

        Returns:
            Instantiated strategy

        Raises:
            StrategyNotFoundError: If strategy not found
            DependencyError: If a dependency is missing
            CircularDependencyError: If circular dependencies detected
        """
        return self._load_with_cycle_detection(strategy_id, loading_stack=[])

    def _load_with_cycle_detection(
        self, strategy_id: str, loading_stack: list[str]
    ) -> BaseStrategy:
        """Internal load with cycle detection."""
        if strategy_id not in self._registry:
            raise StrategyNotFoundError(strategy_id)

        # Check for circular dependency
        if strategy_id in loading_stack:
            cycle = loading_stack + [strategy_id]
            raise CircularDependencyError(cycle)

        meta = self._registry[strategy_id]

        # Resolve dependencies first
        loading_stack.append(strategy_id)
        for dep_id in meta.dependencies:
            if dep_id not in self._registry:
                raise DependencyError(strategy_id, dep_id)
            if dep_id not in self._loaded:
                self._load_with_cycle_detection(dep_id, loading_stack)
        loading_stack.pop()

        # Now import and instantiate if not already loaded
        if strategy_id not in self._loaded:
            strategy_class = self._import_strategy(meta)
            self._loaded[strategy_id] = strategy_class

        return self._loaded[strategy_id]()

    def _import_strategy(self, meta: StrategyMeta) -> type[BaseStrategy]:
        """Import strategy class from module file."""
        if meta.module_path is None:
            raise StrategyNotFoundError(meta.id)

        # Load module from file path
        spec = importlib.util.spec_from_file_location(
            f"strategy_{meta.id}", meta.module_path
        )
        if spec is None or spec.loader is None:
            raise StrategyNotFoundError(meta.id)

        module: ModuleType = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise StrategyNotFoundError(
                f"{meta.id}: Failed to import from {meta.module_path}: {e}"
            ) from e

        # Get the strategy class
        strategy_class = getattr(module, meta.class_name, None)
        if strategy_class is None:
            raise StrategyNotFoundError(
                f"{meta.id} (class {meta.class_name} not found)"
            )

        return strategy_class

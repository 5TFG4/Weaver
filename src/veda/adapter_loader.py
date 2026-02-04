"""
Adapter Loader

Abstract interface and plugin-based implementation for loading adapters.
"""

from __future__ import annotations

import ast
import importlib.util
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.veda.adapter_meta import AdapterMeta
from src.veda.interfaces import ExchangeAdapter

if TYPE_CHECKING:
    from types import ModuleType

logger = logging.getLogger(__name__)


class AdapterNotFoundError(Exception):
    """Raised when an adapter is not found."""

    pass


class AdapterLoader(ABC):
    """Abstract adapter loader interface."""

    @abstractmethod
    def load(self, adapter_id: str, **kwargs: Any) -> ExchangeAdapter:
        """Load an adapter by ID."""
        pass


class PluginAdapterLoader(AdapterLoader):
    """
    Auto-discovering adapter loader.

    Scans a plugin directory for adapter files containing ADAPTER_META,
    extracts metadata using AST parsing (without importing), and loads
    adapters on demand.

    Features:
    - Zero hardcoded imports
    - Lazy loading (import only when load() called)
    - Delete safety (missing files don't crash system)
    - Credential passing to adapter constructors
    """

    def __init__(self, plugin_dir: Path | None = None) -> None:
        """
        Initialize the plugin loader.

        Args:
            plugin_dir: Directory to scan for adapter plugins.
                       Defaults to src/veda/adapters/
        """
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent / "adapters"
        self._plugin_dir = plugin_dir
        self._registry: dict[str, AdapterMeta] = {}
        self._scan_plugins()

    def _scan_plugins(self) -> None:
        """Scan plugin directory for adapter metadata (without importing)."""
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
                    logger.debug(f"Discovered adapter: {meta.id} from {py_file.name}")
            except Exception as e:
                # Log warning but don't fail - plugin is skipped
                logger.warning(f"Failed to scan {py_file}: {e}")

    def _extract_metadata(self, path: Path) -> AdapterMeta | None:
        """
        Extract ADAPTER_META from file using AST parsing.

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
                    if isinstance(target, ast.Name) and target.id == "ADAPTER_META":
                        # Evaluate the dictionary literal
                        try:
                            meta_dict = ast.literal_eval(node.value)
                            if isinstance(meta_dict, dict):
                                return AdapterMeta.from_dict(meta_dict, path)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid ADAPTER_META in {path}: {e}")
                            return None
        return None

    def list_available(self) -> list[AdapterMeta]:
        """List all discovered adapters."""
        return list(self._registry.values())

    def get_metadata(self, adapter_id: str) -> AdapterMeta | None:
        """
        Get metadata for a specific adapter.

        Args:
            adapter_id: The adapter ID

        Returns:
            AdapterMeta if found, None otherwise
        """
        return self._registry.get(adapter_id)

    def load(self, adapter_id: str, **kwargs: Any) -> ExchangeAdapter:
        """
        Load an adapter by ID.

        Args:
            adapter_id: The adapter ID to load
            **kwargs: Credentials and options to pass to adapter constructor

        Returns:
            Instantiated adapter

        Raises:
            AdapterNotFoundError: If adapter not found
        """
        if adapter_id not in self._registry:
            raise AdapterNotFoundError(adapter_id)

        meta = self._registry[adapter_id]
        adapter_class = self._import_adapter(meta)
        return adapter_class(**kwargs)

    def _import_adapter(self, meta: AdapterMeta) -> type[ExchangeAdapter]:
        """Import adapter class from module file."""
        if meta.module_path is None:
            raise AdapterNotFoundError(meta.id)

        # Load module from file path
        spec = importlib.util.spec_from_file_location(
            f"adapter_{meta.id}", meta.module_path
        )
        if spec is None or spec.loader is None:
            raise AdapterNotFoundError(meta.id)

        module: ModuleType = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise AdapterNotFoundError(
                f"{meta.id}: Failed to import from {meta.module_path}: {e}"
            ) from e

        # Get the adapter class
        adapter_class = getattr(module, meta.class_name, None)
        if adapter_class is None:
            raise AdapterNotFoundError(
                f"{meta.id} (class {meta.class_name} not found)"
            )

        return adapter_class

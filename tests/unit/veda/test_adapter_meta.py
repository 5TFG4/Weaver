"""
Tests for Adapter Metadata

TDD tests for M6-1: AdapterMeta dataclass (mirrors StrategyMeta).
"""

import pytest


class TestAdapterMetaDataclass:
    """Tests for AdapterMeta dataclass structure."""

    def test_import_adapter_meta(self) -> None:
        """AdapterMeta should be importable from src.veda.adapter_meta."""
        from src.veda.adapter_meta import AdapterMeta

        assert AdapterMeta is not None

    def test_has_required_fields(self) -> None:
        """AdapterMeta should have id, class_name, name, version, features."""
        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(
            id="test-adapter",
            class_name="TestAdapter",
        )
        assert meta.id == "test-adapter"
        assert meta.class_name == "TestAdapter"

    def test_default_values(self) -> None:
        """AdapterMeta should have sensible defaults."""
        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(
            id="test-adapter",
            class_name="TestAdapter",
        )
        assert meta.name == "test-adapter"  # defaults to id
        assert meta.version == "1.0.0"
        assert meta.description == ""
        assert meta.author == ""
        assert meta.features == []

    def test_custom_values(self) -> None:
        """AdapterMeta should accept custom values."""
        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(
            id="alpaca",
            class_name="AlpacaAdapter",
            name="Alpaca Markets",
            version="2.0.0",
            description="Alpaca trading adapter",
            author="Weaver Team",
            features=["paper_trading", "live_trading", "crypto"],
        )
        assert meta.id == "alpaca"
        assert meta.class_name == "AlpacaAdapter"
        assert meta.name == "Alpaca Markets"
        assert meta.version == "2.0.0"
        assert meta.description == "Alpaca trading adapter"
        assert meta.author == "Weaver Team"
        assert meta.features == ["paper_trading", "live_trading", "crypto"]

    def test_is_frozen(self) -> None:
        """AdapterMeta should be immutable (frozen dataclass)."""
        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(id="test", class_name="TestAdapter")
        with pytest.raises(AttributeError):
            meta.id = "changed"  # type: ignore[misc]

    def test_module_path_optional(self) -> None:
        """AdapterMeta should have optional module_path field."""
        from pathlib import Path

        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(
            id="test",
            class_name="TestAdapter",
            module_path=Path("/some/path.py"),
        )
        assert meta.module_path == Path("/some/path.py")


class TestAdapterMetaFromDict:
    """Tests for AdapterMeta.from_dict() class method."""

    def test_from_dict_basic(self) -> None:
        """from_dict should create AdapterMeta from dictionary."""
        from src.veda.adapter_meta import AdapterMeta

        data = {
            "id": "test-adapter",
            "class": "TestAdapter",
        }
        meta = AdapterMeta.from_dict(data)
        assert meta.id == "test-adapter"
        assert meta.class_name == "TestAdapter"

    def test_from_dict_with_all_fields(self) -> None:
        """from_dict should handle all fields."""
        from pathlib import Path

        from src.veda.adapter_meta import AdapterMeta

        data = {
            "id": "alpaca",
            "class": "AlpacaAdapter",
            "name": "Alpaca Markets",
            "version": "2.0.0",
            "description": "Full-featured adapter",
            "author": "Weaver",
            "features": ["paper_trading", "live_trading"],
        }
        module_path = Path("/path/to/adapter.py")
        meta = AdapterMeta.from_dict(data, module_path=module_path)

        assert meta.id == "alpaca"
        assert meta.class_name == "AlpacaAdapter"
        assert meta.name == "Alpaca Markets"
        assert meta.version == "2.0.0"
        assert meta.description == "Full-featured adapter"
        assert meta.author == "Weaver"
        assert meta.features == ["paper_trading", "live_trading"]
        assert meta.module_path == module_path

    def test_from_dict_missing_optional_fields(self) -> None:
        """from_dict should use defaults for missing optional fields."""
        from src.veda.adapter_meta import AdapterMeta

        data = {
            "id": "minimal",
            "class": "MinimalAdapter",
        }
        meta = AdapterMeta.from_dict(data)
        assert meta.name == "minimal"  # defaults to id
        assert meta.version == "1.0.0"
        assert meta.features == []


class TestAdapterMetaSupportsFeature:
    """Tests for AdapterMeta.supports_feature() method."""

    def test_supports_feature_true(self) -> None:
        """supports_feature returns True when feature present."""
        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(
            id="test",
            class_name="TestAdapter",
            features=["paper_trading", "crypto"],
        )
        assert meta.supports_feature("paper_trading") is True
        assert meta.supports_feature("crypto") is True

    def test_supports_feature_false(self) -> None:
        """supports_feature returns False when feature absent."""
        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(
            id="test",
            class_name="TestAdapter",
            features=["paper_trading"],
        )
        assert meta.supports_feature("live_trading") is False
        assert meta.supports_feature("unknown") is False

    def test_supports_feature_empty(self) -> None:
        """supports_feature returns False when no features."""
        from src.veda.adapter_meta import AdapterMeta

        meta = AdapterMeta(id="test", class_name="TestAdapter")
        assert meta.supports_feature("anything") is False

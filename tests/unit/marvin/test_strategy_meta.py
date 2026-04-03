"""
Tests for StrategyMeta — config_schema support (Phase 3).
"""

from src.marvin.strategy_meta import StrategyMeta


class TestStrategyMetaConfigSchema:
    """Tests for config_schema field on StrategyMeta."""

    def test_has_config_schema(self) -> None:
        meta = StrategyMeta(id="test", class_name="Test", config_schema={"type": "object"})
        assert meta.config_schema == {"type": "object"}

    def test_config_schema_defaults_none(self) -> None:
        meta = StrategyMeta(id="test", class_name="Test")
        assert meta.config_schema is None

    def test_from_dict_reads_config_schema(self) -> None:
        data = {"id": "x", "class": "X", "config_schema": {"type": "object", "properties": {}}}
        meta = StrategyMeta.from_dict(data)
        assert meta.config_schema == {"type": "object", "properties": {}}

    def test_from_dict_missing_config_schema(self) -> None:
        data = {"id": "x", "class": "X"}
        meta = StrategyMeta.from_dict(data)
        assert meta.config_schema is None

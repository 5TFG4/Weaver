"""
Tests for WallE Database Models

Unit tests for SQLAlchemy models (OutboxEvent, ConsumerOffset).
These tests verify model structure without requiring a real database.
"""

from datetime import datetime, timezone
from typing import cast

from sqlalchemy import Table, inspect

from src.walle.models import Base, ConsumerOffset, OutboxEvent


class TestOutboxEvent:
    """Tests for OutboxEvent model."""

    def test_model_has_correct_tablename(self):
        """OutboxEvent uses 'outbox' table."""
        assert OutboxEvent.__tablename__ == "outbox"

    def test_model_has_required_columns(self):
        """OutboxEvent has all required columns."""
        mapper = inspect(OutboxEvent)
        column_names = {c.key for c in mapper.columns}
        
        assert "id" in column_names
        assert "type" in column_names
        assert "payload" in column_names
        assert "created_at" in column_names

    def test_id_is_primary_key(self):
        """id column is the primary key."""
        mapper = inspect(OutboxEvent)
        pk_columns = [c.key for c in mapper.primary_key]
        assert pk_columns == ["id"]

    def test_type_column_has_index(self):
        """type column is indexed."""
        table = cast(Table, OutboxEvent.__table__)
        # Check that 'type' appears in at least one index
        type_indexed = any("type" in list(idx.columns.keys()) for idx in table.indexes)
        assert type_indexed

    def test_created_at_column_has_index(self):
        """created_at column is indexed."""
        table = cast(Table, OutboxEvent.__table__)
        created_at_indexed = any("created_at" in list(idx.columns.keys()) for idx in table.indexes)
        assert created_at_indexed

    def test_repr(self):
        """__repr__ returns readable string."""
        event = OutboxEvent(id=1, type="orders.Placed", payload={}, created_at=datetime.now(timezone.utc))
        repr_str = repr(event)
        assert "OutboxEvent" in repr_str
        assert "id=1" in repr_str
        assert "orders.Placed" in repr_str


class TestConsumerOffset:
    """Tests for ConsumerOffset model."""

    def test_model_has_correct_tablename(self):
        """ConsumerOffset uses 'consumer_offsets' table."""
        assert ConsumerOffset.__tablename__ == "consumer_offsets"

    def test_model_has_required_columns(self):
        """ConsumerOffset has all required columns."""
        mapper = inspect(ConsumerOffset)
        column_names = {c.key for c in mapper.columns}
        
        assert "consumer_id" in column_names
        assert "last_offset" in column_names
        assert "updated_at" in column_names

    def test_consumer_id_is_primary_key(self):
        """consumer_id is the primary key."""
        mapper = inspect(ConsumerOffset)
        pk_columns = [c.key for c in mapper.primary_key]
        assert pk_columns == ["consumer_id"]

    def test_repr(self):
        """__repr__ returns readable string."""
        offset = ConsumerOffset(
            consumer_id="sse_broadcaster",
            last_offset=42,
            updated_at=datetime.now(timezone.utc),
        )
        repr_str = repr(offset)
        assert "ConsumerOffset" in repr_str
        assert "sse_broadcaster" in repr_str
        assert "42" in repr_str


class TestBaseMetadata:
    """Tests for Base model metadata."""

    def test_all_tables_registered(self):
        """Both tables are registered in metadata."""
        table_names = set(Base.metadata.tables.keys())
        assert "outbox" in table_names
        assert "consumer_offsets" in table_names

    def test_metadata_has_exactly_two_tables(self):
        """Only outbox and consumer_offsets tables exist (for now)."""
        assert len(Base.metadata.tables) == 2

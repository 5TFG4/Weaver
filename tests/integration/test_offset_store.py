"""Integration tests for PostgresOffsetStore with real database.

Tests the complete offset store functionality including:
- Offset persistence
- Offset retrieval
- Concurrent access
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

import pytest

from src.events.offsets import PostgresOffsetStore
from src.walle.database import Database

if TYPE_CHECKING:
    pass


pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.environ.get("DB_URL"),
        reason="DB_URL environment variable not set (run with docker-compose)",
    ),
]


class TestPostgresOffsetStoreBasicOperations:
    """Tests for basic offset operations."""

    async def test_set_and_get_offset(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should store and retrieve offset correctly."""
        offset_store = PostgresOffsetStore(database.session_factory)

        await offset_store.set_offset("consumer-1", 100)
        offset = await offset_store.get_offset("consumer-1")

        assert offset == 100

    async def test_get_offset_for_unknown_consumer_returns_minus_one(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should return -1 for consumers with no stored offset."""
        offset_store = PostgresOffsetStore(database.session_factory)

        offset = await offset_store.get_offset("unknown-consumer")

        assert offset == -1

    async def test_update_existing_offset(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should update offset when consumer already has one."""
        offset_store = PostgresOffsetStore(database.session_factory)

        await offset_store.set_offset("consumer-1", 50)
        await offset_store.set_offset("consumer-1", 100)
        offset = await offset_store.get_offset("consumer-1")

        assert offset == 100

    async def test_multiple_consumers_have_independent_offsets(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should track offsets independently for different consumers."""
        offset_store = PostgresOffsetStore(database.session_factory)

        await offset_store.set_offset("consumer-a", 10)
        await offset_store.set_offset("consumer-b", 20)
        await offset_store.set_offset("consumer-c", 30)

        assert await offset_store.get_offset("consumer-a") == 10
        assert await offset_store.get_offset("consumer-b") == 20
        assert await offset_store.get_offset("consumer-c") == 30


class TestPostgresOffsetStoreGetAllOffsets:
    """Tests for retrieving all offsets."""

    async def test_get_all_offsets_empty(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should return empty dict when no offsets stored."""
        offset_store = PostgresOffsetStore(database.session_factory)

        offsets = await offset_store.get_all_offsets()

        assert offsets == {}

    async def test_get_all_offsets_returns_all_consumers(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should return all stored consumer offsets."""
        offset_store = PostgresOffsetStore(database.session_factory)

        await offset_store.set_offset("consumer-1", 100)
        await offset_store.set_offset("consumer-2", 200)
        await offset_store.set_offset("consumer-3", 300)

        offsets = await offset_store.get_all_offsets()

        assert offsets == {
            "consumer-1": 100,
            "consumer-2": 200,
            "consumer-3": 300,
        }


class TestPostgresOffsetStorePersistence:
    """Tests for offset persistence across instances."""

    async def test_offsets_persist_across_instances(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should persist offsets across different store instances."""
        # Create first instance and set offset
        store1 = PostgresOffsetStore(database.session_factory)
        await store1.set_offset("persistent-consumer", 999)

        # Create new instance and verify offset persists
        store2 = PostgresOffsetStore(database.session_factory)
        offset = await store2.get_offset("persistent-consumer")

        assert offset == 999


class TestPostgresOffsetStoreConcurrency:
    """Tests for concurrent access patterns."""

    async def test_concurrent_updates_same_consumer(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle concurrent updates to the same consumer."""
        offset_store = PostgresOffsetStore(database.session_factory)

        async def update_offset(value: int) -> None:
            await offset_store.set_offset("concurrent-consumer", value)

        # Update concurrently with different values
        await asyncio.gather(*[update_offset(i) for i in range(10)])

        # One of the values should have won
        offset = await offset_store.get_offset("concurrent-consumer")
        assert 0 <= offset <= 9

    async def test_concurrent_updates_different_consumers(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle concurrent updates to different consumers."""
        offset_store = PostgresOffsetStore(database.session_factory)

        async def update_consumer(consumer_id: str, value: int) -> None:
            await offset_store.set_offset(consumer_id, value)

        # Update different consumers concurrently
        await asyncio.gather(
            *[update_consumer(f"consumer-{i}", i * 10) for i in range(10)]
        )

        # Verify all consumers have correct offsets
        for i in range(10):
            offset = await offset_store.get_offset(f"consumer-{i}")
            assert offset == i * 10

    async def test_concurrent_read_write(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle concurrent reads and writes."""
        offset_store = PostgresOffsetStore(database.session_factory)
        await offset_store.set_offset("rw-consumer", 0)

        async def writer() -> None:
            for i in range(100):
                await offset_store.set_offset("rw-consumer", i)
                await asyncio.sleep(0.001)

        async def reader() -> list[int]:
            offsets = []
            for _ in range(20):
                offset = await offset_store.get_offset("rw-consumer")
                offsets.append(offset)
                await asyncio.sleep(0.005)
            return offsets

        _, read_offsets = await asyncio.gather(writer(), reader())

        # Read offsets should be monotonically non-decreasing
        # (may not be strictly increasing due to timing, but should never decrease)
        for i in range(1, len(read_offsets)):
            assert read_offsets[i] >= read_offsets[i - 1]


class TestPostgresOffsetStoreEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_large_offset_values(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle large offset values."""
        offset_store = PostgresOffsetStore(database.session_factory)
        large_offset = 2**62  # Very large but within BIGINT range

        await offset_store.set_offset("large-offset-consumer", large_offset)
        offset = await offset_store.get_offset("large-offset-consumer")

        assert offset == large_offset

    async def test_consumer_id_with_special_characters(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle consumer IDs with special characters."""
        offset_store = PostgresOffsetStore(database.session_factory)
        special_ids = [
            "consumer-with-dashes",
            "consumer_with_underscores",
            "consumer.with.dots",
            "consumer:with:colons",
            "consumer@with@at",
        ]

        for i, consumer_id in enumerate(special_ids):
            await offset_store.set_offset(consumer_id, i * 10)

        for i, consumer_id in enumerate(special_ids):
            assert await offset_store.get_offset(consumer_id) == i * 10

    async def test_zero_offset(
        self, database: Database, clean_tables: None
    ) -> None:
        """Should handle storing zero as an explicit offset."""
        offset_store = PostgresOffsetStore(database.session_factory)

        # First set a non-zero offset
        await offset_store.set_offset("zero-consumer", 100)
        assert await offset_store.get_offset("zero-consumer") == 100

        # Then set it to zero
        await offset_store.set_offset("zero-consumer", 0)
        offset = await offset_store.get_offset("zero-consumer")

        # Should return 0 (the stored value, not the default)
        assert offset == 0

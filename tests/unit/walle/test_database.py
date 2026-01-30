"""
Tests for WallE Database Session Management

Unit tests for Database class and session factory.
These tests verify the database layer without requiring a real database.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import DatabaseConfig
from src.walle.database import (
    Database,
    get_database,
    init_database,
    close_database,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig sync_url property."""

    def test_sync_url_converts_driver(self):
        """sync_url converts asyncpg to psycopg2."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://user:pass@localhost:5432/db"
        )
        assert config.sync_url == "postgresql+psycopg2://user:pass@localhost:5432/db"

    def test_sync_url_handles_default(self):
        """sync_url works with default URL."""
        config = DatabaseConfig()
        assert "+psycopg2" in config.sync_url
        assert "+asyncpg" not in config.sync_url


class TestDatabaseClass:
    """Tests for Database class."""

    def test_init_stores_config(self):
        """Database stores configuration."""
        config = DatabaseConfig()
        db = Database(config)
        assert db._config is config

    def test_init_engine_is_none(self):
        """Engine is not created until accessed."""
        config = DatabaseConfig()
        db = Database(config)
        assert db._engine is None

    def test_init_session_factory_is_none(self):
        """Session factory is not created until accessed."""
        config = DatabaseConfig()
        db = Database(config)
        assert db._session_factory is None

    @patch("src.walle.database.create_async_engine")
    def test_engine_property_creates_engine(self, mock_create_engine):
        """Accessing engine property creates it."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        config = DatabaseConfig()
        db = Database(config)
        
        engine = db.engine
        
        assert engine is mock_engine
        mock_create_engine.assert_called_once()

    @patch("src.walle.database.create_async_engine")
    def test_engine_property_reuses_engine(self, mock_create_engine):
        """Engine is created only once."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        config = DatabaseConfig()
        db = Database(config)
        
        # Access twice
        engine1 = db.engine
        engine2 = db.engine
        
        assert engine1 is engine2
        assert mock_create_engine.call_count == 1

    @patch("src.walle.database.create_async_engine")
    @patch("src.walle.database.async_sessionmaker")
    def test_session_factory_property(self, mock_sessionmaker, mock_create_engine):
        """Session factory is created with correct parameters."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_factory = MagicMock()
        mock_sessionmaker.return_value = mock_factory
        
        config = DatabaseConfig()
        db = Database(config)
        
        factory = db.session_factory
        
        assert factory is mock_factory
        mock_sessionmaker.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.walle.database.create_async_engine")
    async def test_close_disposes_engine(self, mock_create_engine):
        """close() disposes the engine."""
        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine
        
        config = DatabaseConfig()
        db = Database(config)
        
        # Access engine to create it
        _ = db.engine
        
        await db.close()
        
        mock_engine.dispose.assert_called_once()
        assert db._engine is None
        assert db._session_factory is None


class TestGlobalDatabaseFunctions:
    """Tests for global database functions."""

    def test_get_database_raises_when_not_initialized(self):
        """get_database raises RuntimeError when not initialized."""
        # Ensure clean state
        import src.walle.database as db_module
        db_module._db = None
        
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_database()

    def test_init_database_returns_database(self):
        """init_database returns Database instance."""
        import src.walle.database as db_module
        db_module._db = None
        
        config = DatabaseConfig()
        db = init_database(config)
        
        assert isinstance(db, Database)
        
        # Cleanup
        db_module._db = None

    def test_init_database_sets_global(self):
        """init_database sets global _db."""
        import src.walle.database as db_module
        db_module._db = None
        
        config = DatabaseConfig()
        db = init_database(config)
        
        assert get_database() is db
        
        # Cleanup
        db_module._db = None

    @pytest.mark.asyncio
    async def test_close_database_clears_global(self):
        """close_database clears global _db."""
        import src.walle.database as db_module
        
        config = DatabaseConfig()
        db = init_database(config)
        
        # Mock the engine so close doesn't fail
        db._engine = None
        
        await close_database()
        
        assert db_module._db is None

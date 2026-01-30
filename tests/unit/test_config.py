"""
Unit Tests for Configuration

Tests the configuration classes and credential management.
"""

import pytest

from src.config import (
    AlpacaConfig,
    AlpacaCredentials,
    DatabaseConfig,
    EventConfig,
    ServerConfig,
    TradingConfig,
    WeaverConfig,
    get_test_config,
)


class TestAlpacaCredentials:
    """Tests for AlpacaCredentials dataclass."""

    def test_credentials_creation(self) -> None:
        """Should create credentials with all fields."""
        creds = AlpacaCredentials(
            api_key="test_key",
            api_secret="test_secret",
            base_url="https://api.alpaca.markets",
            is_paper=False,
        )

        assert creds.api_key == "test_key"
        assert creds.api_secret == "test_secret"
        assert creds.base_url == "https://api.alpaca.markets"
        assert creds.is_paper is False

    def test_credentials_immutable(self) -> None:
        """Credentials should be frozen (immutable)."""
        creds = AlpacaCredentials(
            api_key="key",
            api_secret="secret",
            base_url="https://example.com",
            is_paper=True,
        )

        with pytest.raises(AttributeError):
            creds.api_key = "new_key"  # type: ignore

    def test_is_configured_true(self) -> None:
        """is_configured should return True when both key and secret are set."""
        creds = AlpacaCredentials(
            api_key="key",
            api_secret="secret",
            base_url="https://example.com",
            is_paper=True,
        )

        assert creds.is_configured is True

    def test_is_configured_false_missing_key(self) -> None:
        """is_configured should return False when key is missing."""
        creds = AlpacaCredentials(
            api_key="",
            api_secret="secret",
            base_url="https://example.com",
            is_paper=True,
        )

        assert creds.is_configured is False

    def test_is_configured_false_missing_secret(self) -> None:
        """is_configured should return False when secret is missing."""
        creds = AlpacaCredentials(
            api_key="key",
            api_secret="",
            base_url="https://example.com",
            is_paper=True,
        )

        assert creds.is_configured is False


class TestAlpacaConfig:
    """Tests for AlpacaConfig settings."""

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should have correct default values when env vars are not set."""
        # Clear any existing env vars to test true defaults
        monkeypatch.delenv("ALPACA_LIVE_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_LIVE_API_SECRET", raising=False)
        monkeypatch.delenv("ALPACA_PAPER_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_PAPER_API_SECRET", raising=False)

        config = AlpacaConfig()

        assert config.live_api_key == ""
        assert config.live_api_secret == ""
        assert config.paper_api_key == ""
        assert config.paper_api_secret == ""
        assert config.live_base_url == "https://api.alpaca.markets"
        assert config.paper_base_url == "https://paper-api.alpaca.markets"

    def test_get_credentials_live(self) -> None:
        """get_credentials('live') should return live credentials."""
        config = AlpacaConfig(
            live_api_key="live_key",
            live_api_secret="live_secret",
            paper_api_key="paper_key",
            paper_api_secret="paper_secret",
        )

        creds = config.get_credentials("live")

        assert creds.api_key == "live_key"
        assert creds.api_secret == "live_secret"
        assert creds.base_url == "https://api.alpaca.markets"
        assert creds.is_paper is False

    def test_get_credentials_paper(self) -> None:
        """get_credentials('paper') should return paper credentials."""
        config = AlpacaConfig(
            live_api_key="live_key",
            live_api_secret="live_secret",
            paper_api_key="paper_key",
            paper_api_secret="paper_secret",
        )

        creds = config.get_credentials("paper")

        assert creds.api_key == "paper_key"
        assert creds.api_secret == "paper_secret"
        assert creds.base_url == "https://paper-api.alpaca.markets"
        assert creds.is_paper is True

    def test_get_credentials_custom_base_url(self) -> None:
        """Should use custom base URLs when configured."""
        config = AlpacaConfig(
            live_api_key="key",
            live_api_secret="secret",
            live_base_url="https://custom.live.api",
            paper_base_url="https://custom.paper.api",
        )

        live_creds = config.get_credentials("live")
        paper_creds = config.get_credentials("paper")

        assert live_creds.base_url == "https://custom.live.api"
        assert paper_creds.base_url == "https://custom.paper.api"

    def test_has_live_credentials_true(self) -> None:
        """has_live_credentials should be True when both are set."""
        config = AlpacaConfig(
            live_api_key="key",
            live_api_secret="secret",
        )

        assert config.has_live_credentials is True

    def test_has_live_credentials_false(self) -> None:
        """has_live_credentials should be False when missing."""
        config = AlpacaConfig(
            live_api_key="key",
            live_api_secret="",  # Missing
        )

        assert config.has_live_credentials is False

    def test_has_paper_credentials_true(self) -> None:
        """has_paper_credentials should be True when both are set."""
        config = AlpacaConfig(
            paper_api_key="key",
            paper_api_secret="secret",
        )

        assert config.has_paper_credentials is True

    def test_has_paper_credentials_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """has_paper_credentials should be False when missing."""
        # Clear any existing env vars
        monkeypatch.delenv("ALPACA_PAPER_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_PAPER_API_SECRET", raising=False)

        config = AlpacaConfig()

        assert config.has_paper_credentials is False


class TestDatabaseConfig:
    """Tests for DatabaseConfig settings."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        config = DatabaseConfig()

        assert "postgresql+asyncpg://" in config.url
        assert config.pool_size == 5
        assert config.pool_overflow == 10
        assert config.echo is False

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://user:pass@host:5432/db",
            pool_size=10,
            echo=True,
        )

        assert config.url == "postgresql+asyncpg://user:pass@host:5432/db"
        assert config.pool_size == 10
        assert config.echo is True


class TestServerConfig:
    """Tests for ServerConfig settings."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        config = ServerConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.reload is False
        assert config.workers == 1
        assert config.log_level == "info"

    def test_log_level_validation(self) -> None:
        """Should accept valid log levels."""
        for level in ["debug", "info", "warning", "error"]:
            config = ServerConfig(log_level=level)  # type: ignore
            assert config.log_level == level


class TestEventConfig:
    """Tests for EventConfig settings."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        config = EventConfig()

        assert config.batch_size == 100
        assert config.poll_interval_ms == 100
        assert config.retention_days == 30
        assert config.max_payload_bytes == 102400  # 100KB


class TestTradingConfig:
    """Tests for TradingConfig settings."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        config = TradingConfig()

        assert config.default_timeframe == "1m"
        assert config.max_concurrent_orders == 10
        assert config.order_timeout_seconds == 60
        assert config.rate_limit_per_minute == 200


class TestWeaverConfig:
    """Tests for main WeaverConfig."""

    def test_default_values(self) -> None:
        """Should have correct default values."""
        config = WeaverConfig()

        assert config.environment == "development"
        assert config.debug is False
        assert config.database is not None
        assert config.alpaca is not None
        assert config.server is not None
        assert config.events is not None
        assert config.trading is not None

    def test_nested_configs_accessible(self) -> None:
        """Should be able to access nested config values."""
        config = WeaverConfig()

        # Access nested values
        assert config.database.pool_size == 5
        assert config.server.port == 8000
        assert config.alpaca.live_base_url == "https://api.alpaca.markets"


class TestGetTestConfig:
    """Tests for get_test_config helper."""

    def test_returns_test_environment(self) -> None:
        """get_test_config should return config with test environment."""
        config = get_test_config()

        assert config.environment == "test"
        assert config.debug is True

    def test_has_test_database_url(self) -> None:
        """get_test_config should have test database URL."""
        config = get_test_config()

        assert "weaver_test" in config.database.url

    def test_has_test_credentials(self) -> None:
        """get_test_config should have test API credentials."""
        config = get_test_config()

        assert config.alpaca.has_live_credentials is True
        assert config.alpaca.has_paper_credentials is True

        live_creds = config.alpaca.get_credentials("live")
        paper_creds = config.alpaca.get_credentials("paper")

        assert live_creds.is_configured is True
        assert paper_creds.is_configured is True

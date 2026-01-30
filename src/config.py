"""
Weaver Configuration

Centralized configuration management using pydantic-settings.
Supports environment variables and .env files.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        extra="ignore",
    )

    url: str = Field(
        default="postgresql+asyncpg://weaver:weaver@localhost:5432/weaver",
        description="Database connection URL",
    )
    pool_size: int = Field(default=5, ge=1, le=20)
    pool_overflow: int = Field(default=10, ge=0, le=20)
    echo: bool = Field(default=False, description="Echo SQL statements")


@dataclass(frozen=True)
class AlpacaCredentials:
    """
    Immutable Alpaca API credentials for a specific mode.

    This is what gets passed to the trading code - simple and clear.
    """

    api_key: str
    api_secret: str
    base_url: str
    is_paper: bool

    @property
    def is_configured(self) -> bool:
        """Check if credentials are properly configured."""
        return bool(self.api_key and self.api_secret)


class AlpacaConfig(BaseSettings):
    """
    Alpaca API configuration supporting both Live and Paper accounts.

    Environment variables:
        ALPACA_LIVE_API_KEY      - Live trading API key
        ALPACA_LIVE_API_SECRET   - Live trading API secret
        ALPACA_PAPER_API_KEY     - Paper trading API key
        ALPACA_PAPER_API_SECRET  - Paper trading API secret

    Usage:
        config = get_config().alpaca
        creds = config.get_credentials(mode="live")  # or "paper"
    """

    model_config = SettingsConfigDict(
        env_prefix="ALPACA_",
        env_file=".env",
        extra="ignore",
    )

    # Live trading credentials
    live_api_key: str = Field(default="", description="Live trading API key")
    live_api_secret: str = Field(default="", description="Live trading API secret")

    # Paper trading credentials
    paper_api_key: str = Field(default="", description="Paper trading API key")
    paper_api_secret: str = Field(default="", description="Paper trading API secret")

    # API endpoints
    live_base_url: str = Field(
        default="https://api.alpaca.markets",
        description="Live API base URL",
    )
    paper_base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        description="Paper API base URL",
    )

    def get_credentials(self, mode: Literal["live", "paper"]) -> AlpacaCredentials:
        """
        Get credentials for the specified trading mode.

        Args:
            mode: "live" for real trading, "paper" for paper/backtest

        Returns:
            AlpacaCredentials with the appropriate keys and URL
        """
        if mode == "live":
            return AlpacaCredentials(
                api_key=self.live_api_key,
                api_secret=self.live_api_secret,
                base_url=self.live_base_url,
                is_paper=False,
            )
        else:  # paper
            return AlpacaCredentials(
                api_key=self.paper_api_key,
                api_secret=self.paper_api_secret,
                base_url=self.paper_base_url,
                is_paper=True,
            )

    @computed_field
    @property
    def has_live_credentials(self) -> bool:
        """Check if live credentials are configured."""
        return bool(self.live_api_key and self.live_api_secret)

    @computed_field
    @property
    def has_paper_credentials(self) -> bool:
        """Check if paper credentials are configured."""
        return bool(self.paper_api_key and self.paper_api_secret)


class ServerConfig(BaseSettings):
    """Server configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SERVER_",
        env_file=".env",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False, description="Enable auto-reload")
    workers: int = Field(default=1, ge=1, le=16)
    log_level: Literal["debug", "info", "warning", "error"] = Field(default="info")


class EventConfig(BaseSettings):
    """Event system configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EVENT_",
        env_file=".env",
        extra="ignore",
    )

    batch_size: int = Field(default=100, ge=1, le=1000)
    poll_interval_ms: int = Field(default=100, ge=10, le=5000)
    retention_days: int = Field(default=30, ge=1, le=365)
    max_payload_bytes: int = Field(default=102400, description="Max 100KB inline")


class TradingConfig(BaseSettings):
    """Trading parameters configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADING_",
        env_file=".env",
        extra="ignore",
    )

    default_timeframe: str = Field(default="1m")
    max_concurrent_orders: int = Field(default=10, ge=1, le=100)
    order_timeout_seconds: int = Field(default=60, ge=10, le=300)
    rate_limit_per_minute: int = Field(default=200, ge=1, le=1000)


class WeaverConfig(BaseSettings):
    """Main Weaver configuration aggregating all sub-configs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    alpaca: AlpacaConfig = Field(default_factory=AlpacaConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    events: EventConfig = Field(default_factory=EventConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)

    # Global settings
    environment: Literal["development", "production", "test"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)


@lru_cache(maxsize=1)
def get_config() -> WeaverConfig:
    """
    Get the global configuration instance (cached).

    Returns:
        WeaverConfig instance loaded from environment
    """
    return WeaverConfig()


def get_test_config() -> WeaverConfig:
    """
    Get a configuration instance for testing.

    Returns:
        WeaverConfig with test-appropriate defaults
    """
    return WeaverConfig(
        environment="test",
        debug=True,
        database=DatabaseConfig(
            url="postgresql+asyncpg://test:test@localhost:5432/weaver_test",
            echo=False,
        ),
        alpaca=AlpacaConfig(
            live_api_key="test_live_key",
            live_api_secret="test_live_secret",
            paper_api_key="test_paper_key",
            paper_api_secret="test_paper_secret",
        ),
    )

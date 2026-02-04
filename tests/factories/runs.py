"""
Run Factories

Provides factory functions and classes for creating test runs and strategy configs.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class RunFactory:
    """
    Factory for creating test run objects.
    
    Usage:
        # Create with defaults
        run = RunFactory.create("sma_cross")
        
        # Create backtest run
        run = RunFactory.create(
            "sma_cross",
            mode="backtest",
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 6, 30),
        )
        
        # Use builder pattern
        run = (RunFactory()
            .with_strategy("momentum")
            .with_mode("live")
            .with_config({"fast_period": 10})
            .build())
    """
    
    _id: str | None = None
    _strategy_name: str = "test_strategy"
    _mode: str = "backtest"  # "live" | "backtest"
    _status: str = "pending"  # pending | running | stopped | completed | failed
    _config: dict[str, Any] | None = None
    _timeframe: str = "1m"
    _symbols: list[str] | None = None
    _backtest_start: datetime | None = None
    _backtest_end: datetime | None = None
    _started_at: datetime | None = None
    _stopped_at: datetime | None = None
    _created_at: datetime | None = None
    _updated_at: datetime | None = None
    
    def with_id(self, id: str) -> "RunFactory":
        """Set run ID."""
        self._id = id
        return self
    
    def with_strategy(self, strategy_name: str) -> "RunFactory":
        """Set strategy name."""
        self._strategy_name = strategy_name
        return self
    
    def with_mode(self, mode: str) -> "RunFactory":
        """Set run mode (live or backtest)."""
        self._mode = mode
        return self
    
    def with_status(self, status: str) -> "RunFactory":
        """Set run status."""
        self._status = status
        return self
    
    def with_config(self, config: dict[str, Any]) -> "RunFactory":
        """Set strategy configuration."""
        self._config = config
        return self
    
    def with_timeframe(self, timeframe: str) -> "RunFactory":
        """Set timeframe."""
        self._timeframe = timeframe
        return self
    
    def with_symbols(self, symbols: list[str]) -> "RunFactory":
        """Set trading symbols."""
        self._symbols = symbols
        return self
    
    def with_backtest_range(
        self,
        start: datetime,
        end: datetime,
    ) -> "RunFactory":
        """Set backtest date range."""
        self._backtest_start = start
        self._backtest_end = end
        return self
    
    def as_running(self) -> "RunFactory":
        """Mark run as running."""
        self._status = "running"
        self._started_at = datetime.now(timezone.utc)
        return self
    
    def as_completed(self) -> "RunFactory":
        """Mark run as completed."""
        self._status = "completed"
        self._stopped_at = datetime.now(timezone.utc)
        return self
    
    def as_failed(self) -> "RunFactory":
        """Mark run as failed."""
        self._status = "failed"
        self._stopped_at = datetime.now(timezone.utc)
        return self
    
    def build(self) -> dict[str, Any]:
        """Build the run as a dictionary."""
        now = datetime.now(timezone.utc)
        return {
            "id": self._id or str(uuid4()),
            "strategy_name": self._strategy_name,
            "mode": self._mode,
            "status": self._status,
            "config": self._config or {},
            "timeframe": self._timeframe,
            "symbols": self._symbols or ["AAPL"],
            "backtest_start": self._backtest_start,
            "backtest_end": self._backtest_end,
            "started_at": self._started_at,
            "stopped_at": self._stopped_at,
            "created_at": self._created_at or now,
            "updated_at": self._updated_at or now,
        }
    
    @classmethod
    def create(
        cls,
        strategy_name: str = "test_strategy",
        *,
        mode: str = "backtest",
        timeframe: str = "1m",
        symbols: list[str] | None = None,
        config: dict[str, Any] | None = None,
        backtest_start: datetime | None = None,
        backtest_end: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Convenience method to create a run with minimal boilerplate.
        
        Args:
            strategy_name: Name of the strategy
            mode: Run mode (default: "backtest")
            timeframe: Bar timeframe (default: "1m")
            symbols: Trading symbols (default: ["AAPL"])
            config: Strategy configuration
            backtest_start: Backtest start date
            backtest_end: Backtest end date
            
        Returns:
            Run as dictionary
        """
        factory = (
            cls()
            .with_strategy(strategy_name)
            .with_mode(mode)
            .with_timeframe(timeframe)
        )
        
        if symbols:
            factory.with_symbols(symbols)
        
        if config:
            factory.with_config(config)
        
        if backtest_start and backtest_end:
            factory.with_backtest_range(backtest_start, backtest_end)
        
        return factory.build()


def create_run(
    strategy_name: str = "test_strategy",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Simple function to create a test run.
    
    Args:
        strategy_name: Strategy name
        **kwargs: Additional fields
        
    Returns:
        Run as dictionary
    """
    return RunFactory.create(strategy_name, **kwargs)


# =============================================================================
# Pre-built Run Templates
# =============================================================================

def create_live_run(
    strategy_name: str,
    symbols: list[str],
    timeframe: str = "1m",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a live trading run."""
    return create_run(
        strategy_name=strategy_name,
        mode="live",
        symbols=symbols,
        timeframe=timeframe,
        config=config,
    )


def create_backtest_run(
    strategy_name: str,
    symbols: list[str],
    start: datetime,
    end: datetime,
    timeframe: str = "1m",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a backtest run."""
    return create_run(
        strategy_name=strategy_name,
        mode="backtest",
        symbols=symbols,
        timeframe=timeframe,
        config=config,
        backtest_start=start,
        backtest_end=end,
    )


def create_sma_cross_config(
    fast_period: int = 10,
    slow_period: int = 30,
    position_size: float = 0.1,
) -> dict[str, Any]:
    """Create configuration for SMA crossover strategy."""
    return {
        "fast_period": fast_period,
        "slow_period": slow_period,
        "position_size": position_size,
    }


def create_sma_cross_backtest(
    start: datetime,
    end: datetime,
    symbols: list[str] | None = None,
    fast_period: int = 10,
    slow_period: int = 30,
) -> dict[str, Any]:
    """Create a complete SMA crossover backtest run."""
    return create_backtest_run(
        strategy_name="sma_cross",
        symbols=symbols or ["AAPL"],
        start=start,
        end=end,
        config=create_sma_cross_config(
            fast_period=fast_period,
            slow_period=slow_period,
        ),
    )


# =============================================================================
# RunManager Factory with Dependencies
# =============================================================================

def create_run_manager_with_deps(
    event_log: Any | None = None,
    bar_repository: Any | None = None,
    strategy_loader: Any | None = None,
) -> "RunManager":
    """
    Create a RunManager with all mocked dependencies for testing.
    
    Args:
        event_log: Optional event log (will create mock if None)
        bar_repository: Optional bar repository (will create mock if None)
        strategy_loader: Optional strategy loader (will create mock if None)
        
    Returns:
        RunManager with all dependencies configured
    """
    from unittest.mock import AsyncMock, MagicMock
    from src.glados.services.run_manager import RunManager
    
    # Create event log if not provided
    if event_log is None:
        event_log = AsyncMock()
        event_log.append = AsyncMock()
    
    # Create bar repository if not provided
    if bar_repository is None:
        bar_repository = AsyncMock()
        bar_repository.get_bars = AsyncMock(return_value=[])
    
    # Create strategy loader with mock strategy if not provided
    if strategy_loader is None:
        strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.initialize = AsyncMock()
        mock_strategy.on_tick = AsyncMock(return_value=[])
        strategy_loader.load = MagicMock(return_value=mock_strategy)
    
    return RunManager(
        event_log=event_log,
        bar_repository=bar_repository,
        strategy_loader=strategy_loader,
    )

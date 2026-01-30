"""
Tests for Clock Factory

TDD tests for ClockConfig and create_clock function.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.glados.clock.factory import ClockConfig, create_clock
from src.glados.clock.backtest import BacktestClock
from src.glados.clock.realtime import RealtimeClock


class TestClockConfig:
    """Tests for ClockConfig dataclass."""

    def test_creates_realtime_config_by_default(self):
        """Default config has no backtest times."""
        config = ClockConfig()
        assert config.timeframe == "1m"
        assert config.backtest_start is None
        assert config.backtest_end is None

    def test_creates_config_with_custom_timeframe(self):
        """Can specify custom timeframe."""
        config = ClockConfig(timeframe="5m")
        assert config.timeframe == "5m"

    def test_creates_backtest_config_with_times(self):
        """Backtest config includes start and end times."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)
        config = ClockConfig(
            timeframe="1h",
            backtest_start=start,
            backtest_end=end,
        )
        assert config.backtest_start == start
        assert config.backtest_end == end

    def test_is_backtest_false_without_times(self):
        """is_backtest returns False when no backtest times set."""
        config = ClockConfig()
        assert config.is_backtest is False

    def test_is_backtest_true_with_times(self):
        """is_backtest returns True when backtest times are set."""
        config = ClockConfig(
            backtest_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            backtest_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )
        assert config.is_backtest is True

    def test_is_immutable(self):
        """ClockConfig is a frozen dataclass."""
        config = ClockConfig()
        with pytest.raises(AttributeError):
            config.timeframe = "5m"  # type: ignore

    def test_raises_if_only_start_provided(self):
        """Must provide both start and end, or neither."""
        with pytest.raises(ValueError, match="both backtest_start and backtest_end"):
            ClockConfig(
                backtest_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            )

    def test_raises_if_only_end_provided(self):
        """Must provide both start and end, or neither."""
        with pytest.raises(ValueError, match="both backtest_start and backtest_end"):
            ClockConfig(
                backtest_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
            )

    def test_raises_if_end_before_start(self):
        """End time must be >= start time."""
        with pytest.raises(ValueError, match="backtest_end must be >= backtest_start"):
            ClockConfig(
                backtest_start=datetime(2025, 1, 31, tzinfo=timezone.utc),
                backtest_end=datetime(2025, 1, 1, tzinfo=timezone.utc),
            )

    def test_allows_equal_start_and_end(self):
        """Single-tick backtest (start == end) is valid."""
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        config = ClockConfig(backtest_start=ts, backtest_end=ts)
        assert config.is_backtest is True


class TestCreateClock:
    """Tests for create_clock factory function."""

    def test_returns_realtime_clock_by_default(self):
        """Default config creates RealtimeClock."""
        config = ClockConfig()
        clock = create_clock(config)
        assert isinstance(clock, RealtimeClock)

    def test_returns_backtest_clock_with_times(self):
        """Backtest config creates BacktestClock."""
        config = ClockConfig(
            backtest_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            backtest_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )
        clock = create_clock(config)
        assert isinstance(clock, BacktestClock)

    def test_passes_timeframe_to_realtime(self):
        """Timeframe is passed to RealtimeClock."""
        config = ClockConfig(timeframe="15m")
        clock = create_clock(config)
        assert clock.timeframe == "15m"

    def test_passes_timeframe_to_backtest(self):
        """Timeframe is passed to BacktestClock."""
        config = ClockConfig(
            timeframe="1h",
            backtest_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            backtest_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )
        clock = create_clock(config)
        assert clock.timeframe == "1h"

    def test_passes_time_range_to_backtest(self):
        """Start and end times are passed to BacktestClock."""
        start = datetime(2025, 1, 1, 9, 30, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 16, 0, tzinfo=timezone.utc)
        config = ClockConfig(
            backtest_start=start,
            backtest_end=end,
        )
        clock = create_clock(config)
        assert isinstance(clock, BacktestClock)
        assert clock._start_time == start
        assert clock._end_time == end


class TestClockModuleExports:
    """Tests for module exports."""

    def test_factory_exported_from_clock_module(self):
        """create_clock is exported from glados.clock."""
        from src.glados.clock import create_clock as exported_create_clock
        assert exported_create_clock is create_clock

    def test_config_exported_from_clock_module(self):
        """ClockConfig is exported from glados.clock."""
        from src.glados.clock import ClockConfig as ExportedConfig
        assert ExportedConfig is ClockConfig

    def test_clock_classes_exported(self):
        """Clock classes are exported from glados.clock."""
        from src.glados.clock import BacktestClock as ExportedBacktest
        from src.glados.clock import RealtimeClock as ExportedRealtime
        assert ExportedBacktest is BacktestClock
        assert ExportedRealtime is RealtimeClock

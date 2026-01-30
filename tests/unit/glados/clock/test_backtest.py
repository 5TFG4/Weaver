"""
Unit Tests for BacktestClock

TDD tests for the backtest clock implementation.
BacktestClock runs as fast as possible (no sleeping) for simulation.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.glados.clock.backtest import BacktestClock
from src.glados.clock.base import ClockTick


# Test fixtures
@pytest.fixture
def sample_start_time() -> datetime:
    """Standard start time for tests."""
    return datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_end_time() -> datetime:
    """Standard end time for tests (30 minutes later)."""
    return datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def backtest_clock(sample_start_time: datetime, sample_end_time: datetime) -> BacktestClock:
    """Create a standard backtest clock for testing."""
    return BacktestClock(
        start_time=sample_start_time,
        end_time=sample_end_time,
        timeframe="1m",
    )


class TestClockTick:
    """Tests for ClockTick dataclass."""

    def test_to_dict_serialization(self) -> None:
        """Should serialize tick to dictionary."""
        tick = ClockTick(
            run_id="test-run",
            ts=datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc),
            timeframe="1m",
            bar_index=1,
            is_backtest=True,
        )

        result = tick.to_dict()

        assert result["run_id"] == "test-run"
        assert result["ts"] == "2024-01-15T09:30:00+00:00"
        assert result["timeframe"] == "1m"
        assert result["bar_index"] == 1
        assert result["is_backtest"] is True

    def test_tick_is_frozen(self) -> None:
        """ClockTick should be immutable (frozen dataclass)."""
        tick = ClockTick(
            run_id="test-run",
            ts=datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc),
            timeframe="1m",
            bar_index=1,
        )

        with pytest.raises(AttributeError, match="cannot assign to field"):
            tick.run_id = "modified"  # type: ignore[misc]


class TestBacktestClockInit:
    """Tests for BacktestClock initialization."""

    def test_initializes_with_time_range(
        self, sample_start_time: datetime, sample_end_time: datetime
    ) -> None:
        """Should store start and end times."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="1m",
        )

        assert clock._start_time == sample_start_time
        assert clock._end_time == sample_end_time

    def test_initializes_at_start_time(
        self, sample_start_time: datetime, sample_end_time: datetime
    ) -> None:
        """Current time should be start time before running."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="1m",
        )

        assert clock.current_time() == sample_start_time

    def test_initializes_with_timeframe(
        self, sample_start_time: datetime, sample_end_time: datetime
    ) -> None:
        """Should store the timeframe."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="5m",
        )

        assert clock.timeframe == "5m"

    def test_default_timeframe_is_1m(
        self, sample_start_time: datetime, sample_end_time: datetime
    ) -> None:
        """Default timeframe should be 1 minute."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
        )

        assert clock.timeframe == "1m"


class TestBacktestClockLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self, backtest_clock: BacktestClock) -> None:
        """Start should set is_running to True."""
        assert not backtest_clock.is_running

        # Start and immediately stop (don't let it run)
        await backtest_clock.start("test-run")
        assert backtest_clock.is_running

        await backtest_clock.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running_flag(self, backtest_clock: BacktestClock) -> None:
        """Stop should set is_running to False."""
        await backtest_clock.start("test-run")
        await backtest_clock.stop()

        assert not backtest_clock.is_running

    @pytest.mark.asyncio
    async def test_cannot_start_twice(self, backtest_clock: BacktestClock) -> None:
        """Starting an already running clock should be a no-op."""
        await backtest_clock.start("test-run-1")

        # Try to start again with different run_id
        await backtest_clock.start("test-run-2")

        # Should still have the original run_id
        assert backtest_clock._run_id == "test-run-1"

        await backtest_clock.stop()

    @pytest.mark.asyncio
    async def test_restart_resets_state(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Restarting after stop should reset state."""
        # Use a short time range
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=3),
            timeframe="1m",
        )

        # Collect ticks
        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        # First run - let it complete
        await clock.start("run-1")
        await clock.wait()
        first_run_tick_count = len(ticks)

        # Second run should reset bar_index
        ticks.clear()
        await clock.start("run-2")
        await clock.wait()

        # Both runs should produce similar tick counts
        assert len(ticks) == first_run_tick_count
        # Bar index should restart from 1
        assert ticks[0].bar_index == 1


class TestBacktestClockTicks:
    """Tests for tick emission."""

    @pytest.mark.asyncio
    async def test_emits_ticks_to_callbacks(self, backtest_clock: BacktestClock) -> None:
        """Should emit ticks to registered callbacks."""
        ticks: list[ClockTick] = []
        backtest_clock.on_tick(ticks.append)

        await backtest_clock.start("test-run")
        # Let it complete (30 minutes of 1m bars = 31 ticks including start)
        await backtest_clock.wait()

        assert len(ticks) > 0

    @pytest.mark.asyncio
    async def test_tick_timestamps_advance_by_timeframe(
        self,
        sample_start_time: datetime,
        sample_end_time: datetime,
    ) -> None:
        """Tick timestamps should advance by timeframe interval."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=5),
            timeframe="1m",
        )

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.wait()

        # Should have ticks at 09:30, 09:31, 09:32, 09:33, 09:34, 09:35
        assert len(ticks) == 6
        assert ticks[0].ts == sample_start_time
        assert ticks[1].ts == sample_start_time + timedelta(minutes=1)
        assert ticks[2].ts == sample_start_time + timedelta(minutes=2)

    @pytest.mark.asyncio
    async def test_stops_at_end_time(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Should stop emitting ticks after end_time."""
        end_time = sample_start_time + timedelta(minutes=3)
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=end_time,
            timeframe="1m",
        )

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.wait()

        # Last tick should be at or before end_time
        assert ticks[-1].ts <= end_time

    @pytest.mark.asyncio
    async def test_bar_index_increments(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Bar index should increment with each tick."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=5),
            timeframe="1m",
        )

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.wait()

        # Bar indices should be sequential starting from 1
        for i, tick in enumerate(ticks):
            assert tick.bar_index == i + 1

    @pytest.mark.asyncio
    async def test_is_backtest_flag_true(self, backtest_clock: BacktestClock) -> None:
        """All ticks should have is_backtest=True."""
        ticks: list[ClockTick] = []
        backtest_clock.on_tick(ticks.append)

        await backtest_clock.start("test-run")
        await backtest_clock.stop()

        for tick in ticks:
            assert tick.is_backtest is True

    @pytest.mark.asyncio
    async def test_tick_contains_run_id(self, backtest_clock: BacktestClock) -> None:
        """Ticks should contain the correct run_id."""
        ticks: list[ClockTick] = []
        backtest_clock.on_tick(ticks.append)

        await backtest_clock.start("my-backtest-run")
        await backtest_clock.stop()

        for tick in ticks:
            assert tick.run_id == "my-backtest-run"

    @pytest.mark.asyncio
    async def test_tick_contains_timeframe(
        self,
        sample_start_time: datetime,
        sample_end_time: datetime,
    ) -> None:
        """Ticks should contain the correct timeframe."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="5m",
        )

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.stop()

        for tick in ticks:
            assert tick.timeframe == "5m"


class TestBacktestClockBackpressure:
    """Tests for backpressure mechanism."""

    @pytest.mark.asyncio
    async def test_continues_without_ack_when_disabled(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Should continue emitting ticks without waiting for ack when backpressure disabled."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=5),
            timeframe="1m",
        )
        clock.disable_backpressure()

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.wait()

        # Should complete all ticks without manual acknowledgment
        assert len(ticks) == 6

    @pytest.mark.asyncio
    async def test_waits_for_ack_when_enabled(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Should wait for acknowledgment before next tick when backpressure enabled."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=5),
            timeframe="1m",
        )
        clock.enable_backpressure()

        ticks: list[ClockTick] = []

        def on_tick(tick: ClockTick) -> None:
            ticks.append(tick)
            # Acknowledge each tick
            clock.acknowledge()

        clock.on_tick(on_tick)

        await clock.start("test-run")
        await clock.wait()

        # Should complete all ticks with acknowledgment
        assert len(ticks) == 6

    @pytest.mark.asyncio
    async def test_can_toggle_backpressure(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Should be able to enable/disable backpressure."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=2),
            timeframe="1m",
        )

        # Initially disabled
        assert clock._use_backpressure is False

        # Enable
        clock.enable_backpressure()
        assert clock._use_backpressure is True

        # Disable
        clock.disable_backpressure()
        assert clock._use_backpressure is False


class TestBacktestClockProgress:
    """Tests for progress tracking."""

    def test_progress_at_start_is_zero(
        self,
        sample_start_time: datetime,
        sample_end_time: datetime,
    ) -> None:
        """Progress should be 0 at start."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="1m",
        )

        assert clock.progress == 0.0

    @pytest.mark.asyncio
    async def test_progress_at_end_is_one(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Progress should be 1.0 when complete."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=3),
            timeframe="1m",
        )

        await clock.start("test-run")
        await clock.wait()

        assert clock.progress == pytest.approx(1.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_progress_increases_during_run(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Progress should increase as simulation advances."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=10),
            timeframe="1m",
        )
        clock.enable_backpressure()

        progress_values: list[float] = []

        def on_tick(tick: ClockTick) -> None:
            progress_values.append(clock.progress)
            clock.acknowledge()

        clock.on_tick(on_tick)

        await clock.start("test-run")
        await clock.wait()

        # Progress should be monotonically increasing
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i - 1]

    def test_is_complete_false_at_start(
        self,
        sample_start_time: datetime,
        sample_end_time: datetime,
    ) -> None:
        """is_complete should be False at start."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="1m",
        )

        assert clock.is_complete is False

    @pytest.mark.asyncio
    async def test_is_complete_true_when_past_end(
        self,
        sample_start_time: datetime,
    ) -> None:
        """is_complete should be True after simulation ends."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=3),
            timeframe="1m",
        )

        await clock.start("test-run")
        await clock.wait()

        assert clock.is_complete is True


class TestBacktestClockEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_single_tick_when_start_equals_end(self) -> None:
        """Should emit exactly one tick when start == end."""
        start = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        clock = BacktestClock(
            start_time=start,
            end_time=start,  # Same as start
            timeframe="1m",
        )

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.wait()

        assert len(ticks) == 1
        assert ticks[0].ts == start

    @pytest.mark.asyncio
    async def test_handles_5m_timeframe(self) -> None:
        """Should work correctly with 5-minute timeframe."""
        start = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        clock = BacktestClock(
            start_time=start,
            end_time=end,
            timeframe="5m",
        )

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.wait()

        # 30 minutes with 5m bars = 7 ticks (09:30, 09:35, 09:40, 09:45, 09:50, 09:55, 10:00)
        assert len(ticks) == 7
        assert ticks[1].ts - ticks[0].ts == timedelta(minutes=5)

    @pytest.mark.asyncio
    async def test_handles_1h_timeframe(self) -> None:
        """Should work correctly with 1-hour timeframe."""
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock = BacktestClock(
            start_time=start,
            end_time=end,
            timeframe="1h",
        )

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        await clock.start("test-run")
        await clock.wait()

        # 3 hours with 1h bars = 4 ticks (09:00, 10:00, 11:00, 12:00)
        assert len(ticks) == 4
        assert ticks[1].ts - ticks[0].ts == timedelta(hours=1)

    def test_simulated_time_property(
        self,
        sample_start_time: datetime,
        sample_end_time: datetime,
    ) -> None:
        """Should expose simulated_time property."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="1m",
        )

        assert clock.simulated_time == sample_start_time

    @pytest.mark.asyncio
    async def test_multiple_callbacks(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Should notify all registered callbacks."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=2),
            timeframe="1m",
        )

        ticks_1: list[ClockTick] = []
        ticks_2: list[ClockTick] = []

        clock.on_tick(ticks_1.append)
        clock.on_tick(ticks_2.append)

        await clock.start("test-run")
        await clock.wait()

        assert len(ticks_1) == len(ticks_2)
        assert len(ticks_1) == 3

    @pytest.mark.asyncio
    async def test_unsubscribe_callback(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Should be able to unsubscribe from tick events."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=3),
            timeframe="1m",
        )

        ticks: list[ClockTick] = []
        unsubscribe = clock.on_tick(ticks.append)

        # Unsubscribe before starting
        unsubscribe()

        await clock.start("test-run")
        await clock.wait()

        # Should not have received any ticks
        assert len(ticks) == 0

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_stop_clock(
        self,
        sample_start_time: datetime,
    ) -> None:
        """Clock should continue even if a callback raises an exception."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_start_time + timedelta(minutes=3),
            timeframe="1m",
        )

        successful_ticks: list[ClockTick] = []

        def failing_callback(tick: ClockTick) -> None:
            raise ValueError("Callback failed!")

        def working_callback(tick: ClockTick) -> None:
            successful_ticks.append(tick)

        clock.on_tick(failing_callback)
        clock.on_tick(working_callback)

        await clock.start("test-run")
        await clock.wait()

        # Working callback should still receive all ticks
        assert len(successful_ticks) == 4

    def test_tick_count_property(
        self,
        sample_start_time: datetime,
        sample_end_time: datetime,
    ) -> None:
        """Should track total tick count."""
        clock = BacktestClock(
            start_time=sample_start_time,
            end_time=sample_end_time,
            timeframe="1m",
        )

        assert clock.tick_count == 0

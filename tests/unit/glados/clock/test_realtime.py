"""
Unit Tests for RealtimeClock

TDD tests for the realtime clock implementation.
RealtimeClock emits ticks aligned to wall-clock bar boundaries.
Uses freezegun for time mocking to avoid real waits.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time

from src.glados.clock.base import ClockTick
from src.glados.clock.realtime import RealtimeClock


class TestRealtimeClockInit:
    """Tests for RealtimeClock initialization."""

    def test_initializes_with_default_timeframe(self) -> None:
        """Default timeframe should be 1 minute."""
        clock = RealtimeClock()
        assert clock.timeframe == "1m"

    def test_initializes_with_custom_timeframe(self) -> None:
        """Should accept custom timeframe."""
        clock = RealtimeClock(timeframe="5m")
        assert clock.timeframe == "5m"

    def test_not_running_initially(self) -> None:
        """Clock should not be running after init."""
        clock = RealtimeClock()
        assert not clock.is_running

    def test_tick_count_starts_at_zero(self) -> None:
        """Tick count should be zero initially."""
        clock = RealtimeClock()
        assert clock.tick_count == 0


class TestRealtimeClockCurrentTime:
    """Tests for current_time method."""

    @freeze_time("2024-01-15 09:30:45", tz_offset=0)
    def test_returns_current_utc_time(self) -> None:
        """Should return the current wall clock time in UTC."""
        clock = RealtimeClock()
        current = clock.current_time()

        assert current == datetime(2024, 1, 15, 9, 30, 45, tzinfo=timezone.utc)

    @freeze_time("2024-01-15 09:30:45", tz_offset=0)
    def test_time_has_utc_timezone(self) -> None:
        """Returned time should have UTC timezone."""
        clock = RealtimeClock()
        current = clock.current_time()

        assert current.tzinfo == timezone.utc


class TestRealtimeClockLifecycle:
    """Tests for start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self) -> None:
        """Start should set is_running to True."""
        clock = RealtimeClock()
        assert not clock.is_running

        await clock.start("test-run")
        assert clock.is_running

        await clock.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running_flag(self) -> None:
        """Stop should set is_running to False."""
        clock = RealtimeClock()

        await clock.start("test-run")
        await clock.stop()

        assert not clock.is_running

    @pytest.mark.asyncio
    async def test_cannot_start_twice(self) -> None:
        """Starting an already running clock should be a no-op."""
        clock = RealtimeClock()

        await clock.start("run-1")
        await clock.start("run-2")

        # Should still have the original run_id
        assert clock._run_id == "run-1"

        await clock.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self) -> None:
        """Stop should cancel the running task."""
        clock = RealtimeClock()

        await clock.start("test-run")
        assert clock._task is not None

        await clock.stop()
        assert clock._task is None

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_safe(self) -> None:
        """Stopping a non-running clock should be safe."""
        clock = RealtimeClock()

        # Should not raise
        await clock.stop()
        assert not clock.is_running


class TestRealtimeClockTicks:
    """Tests for tick emission."""

    @pytest.mark.asyncio
    async def test_emits_tick_with_correct_run_id(self) -> None:
        """Ticks should contain the correct run_id."""
        clock = RealtimeClock(timeframe="1m")
        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        # Mock _sleep_until to return immediately and stop after first tick
        tick_count = 0

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 1:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("my-run-id")
            await clock.wait()

        assert len(ticks) >= 1
        assert ticks[0].run_id == "my-run-id"

    @pytest.mark.asyncio
    async def test_emits_tick_with_correct_timeframe(self) -> None:
        """Ticks should contain the correct timeframe."""
        clock = RealtimeClock(timeframe="5m")
        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        tick_count = 0

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 1:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("test-run")
            await clock.wait()

        assert len(ticks) >= 1
        assert ticks[0].timeframe == "5m"

    @pytest.mark.asyncio
    async def test_is_backtest_flag_is_false(self) -> None:
        """Ticks should have is_backtest=False."""
        clock = RealtimeClock()
        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        tick_count = 0

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 1:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("test-run")
            await clock.wait()

        assert len(ticks) >= 1
        assert ticks[0].is_backtest is False

    @pytest.mark.asyncio
    async def test_bar_index_increments(self) -> None:
        """Bar index should increment with each tick."""
        clock = RealtimeClock()
        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        tick_count = 0

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 3:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("test-run")
            await clock.wait()

        assert len(ticks) == 3
        assert ticks[0].bar_index == 1
        assert ticks[1].bar_index == 2
        assert ticks[2].bar_index == 3

    @pytest.mark.asyncio
    @freeze_time("2024-01-15 09:30:45", tz_offset=0)
    async def test_tick_ts_is_bar_start_not_emission_time(self) -> None:
        """Tick timestamp should be the bar start time, not when emitted."""
        clock = RealtimeClock(timeframe="1m")
        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        tick_count = 0
        # The next bar after 09:30:45 is 09:31:00
        expected_bar_start = datetime(2024, 1, 15, 9, 31, 0, tzinfo=timezone.utc)

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 1:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("test-run")
            await clock.wait()

        assert len(ticks) >= 1
        assert ticks[0].ts == expected_bar_start


class TestRealtimeClockSleepUntil:
    """Tests for the _sleep_until method."""

    @pytest.mark.asyncio
    async def test_returns_immediately_if_past_target(self) -> None:
        """Should return immediately if target time has passed."""
        clock = RealtimeClock()

        # Target in the past
        past_target = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Should not block
        await clock._sleep_until(past_target)

    @pytest.mark.asyncio
    async def test_stops_if_not_running(self) -> None:
        """Should exit if clock is stopped during sleep."""
        import asyncio

        clock = RealtimeClock()
        clock._running = True

        # Target in the future
        future_target = datetime.now(timezone.utc) + timedelta(seconds=2)

        # Stop the clock after a short delay
        async def stop_clock():
            await asyncio.sleep(0.02)
            clock._running = False

        asyncio.create_task(stop_clock())

        # Mock asyncio.sleep to be fast but still yield control
        original_sleep = asyncio.sleep

        async def fast_sleep(duration: float) -> None:
            await original_sleep(0.01)

        with patch("asyncio.sleep", side_effect=fast_sleep):
            # Should exit when _running becomes False
            await clock._sleep_until(future_target)


class TestRealtimeClockCallbacks:
    """Tests for callback handling."""

    @pytest.mark.asyncio
    async def test_multiple_callbacks_all_called(self) -> None:
        """All registered callbacks should be called."""
        clock = RealtimeClock()

        ticks_1: list[ClockTick] = []
        ticks_2: list[ClockTick] = []

        clock.on_tick(ticks_1.append)
        clock.on_tick(ticks_2.append)

        tick_count = 0

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 1:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("test-run")
            await clock.wait()

        assert len(ticks_1) == 1
        assert len(ticks_2) == 1

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_stop_clock(self) -> None:
        """Clock should continue even if callback raises exception."""
        clock = RealtimeClock()

        successful_ticks: list[ClockTick] = []

        def failing_callback(tick: ClockTick) -> None:
            raise ValueError("Callback error!")

        clock.on_tick(failing_callback)
        clock.on_tick(successful_ticks.append)

        tick_count = 0

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 2:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("test-run")
            await clock.wait()

        # Second callback should still receive ticks
        assert len(successful_ticks) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe_works(self) -> None:
        """Unsubscribed callbacks should not be called."""
        clock = RealtimeClock()

        ticks: list[ClockTick] = []
        unsubscribe = clock.on_tick(ticks.append)
        unsubscribe()

        tick_count = 0

        async def mock_sleep_until(target: datetime) -> None:
            nonlocal tick_count
            tick_count += 1
            if tick_count > 1:
                clock._running = False

        with patch.object(clock, "_sleep_until", side_effect=mock_sleep_until):
            await clock.start("test-run")
            await clock.wait()

        assert len(ticks) == 0


class TestRealtimeClockErrorHandling:
    """Tests for error handling in tick loop."""

    @pytest.mark.asyncio
    async def test_continues_after_exception_in_tick_loop(self) -> None:
        """Clock should recover from exceptions in tick loop."""
        clock = RealtimeClock()

        ticks: list[ClockTick] = []
        clock.on_tick(ticks.append)

        call_count = 0

        async def mock_sleep_until_with_error(target: datetime) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call raises an exception
                raise RuntimeError("Temporary error")
            elif call_count > 3:
                clock._running = False

        with patch.object(
            clock, "_sleep_until", side_effect=mock_sleep_until_with_error
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await clock.start("test-run")
                await clock.wait()

        # Should have recovered and emitted ticks
        assert len(ticks) >= 1


class TestRealtimeClockWait:
    """Tests for the wait() method."""

    @pytest.mark.asyncio
    async def test_wait_returns_when_stopped(self) -> None:
        """wait() should return when clock is stopped."""
        clock = RealtimeClock()

        await clock.start("test-run")

        # Stop in background
        import asyncio

        async def stop_soon():
            await asyncio.sleep(0.01)
            await clock.stop()

        asyncio.create_task(stop_soon())

        # Should return when stopped
        await clock.wait()
        assert not clock.is_running

    @pytest.mark.asyncio
    async def test_wait_when_not_started(self) -> None:
        """wait() should handle case when clock never started."""
        clock = RealtimeClock()

        # Should not block or raise
        await clock.wait()

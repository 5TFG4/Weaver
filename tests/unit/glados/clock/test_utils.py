"""
Unit Tests for Clock Utilities

Tests bar alignment calculations and timeframe parsing.
"""

from datetime import datetime, timezone

import pytest

from src.glados.clock.utils import (
    TIMEFRAME_SECONDS,
    calculate_bar_start,
    calculate_next_bar_start,
    parse_timeframe,
    seconds_until_next_bar,
)


class TestParseTimeframe:
    """Tests for timeframe parsing."""

    def test_parse_valid_timeframes(self) -> None:
        """Should parse all supported timeframes."""
        assert parse_timeframe("1m").seconds == 60
        assert parse_timeframe("5m").seconds == 300
        assert parse_timeframe("15m").seconds == 900
        assert parse_timeframe("30m").seconds == 1800
        assert parse_timeframe("1h").seconds == 3600
        assert parse_timeframe("4h").seconds == 14400
        assert parse_timeframe("1d").seconds == 86400

    def test_parse_invalid_timeframe(self) -> None:
        """Should raise ValueError for unknown timeframe."""
        with pytest.raises(ValueError) as exc_info:
            parse_timeframe("2m")

        assert "Unknown timeframe" in str(exc_info.value)
        assert "2m" in str(exc_info.value)

    def test_timeframe_code_preserved(self) -> None:
        """Should preserve the original timeframe code."""
        tf = parse_timeframe("5m")
        assert tf.code == "5m"


class TestCalculateNextBarStart:
    """Tests for next bar start calculation."""

    def test_next_bar_start_1m(self) -> None:
        """09:30:45 → next bar at 09:31:00."""
        current = datetime(2024, 1, 15, 9, 30, 45, tzinfo=timezone.utc)
        next_bar = calculate_next_bar_start(current, "1m")

        assert next_bar == datetime(2024, 1, 15, 9, 31, 0, tzinfo=timezone.utc)

    def test_next_bar_start_5m(self) -> None:
        """09:32:00 → next bar at 09:35:00."""
        current = datetime(2024, 1, 15, 9, 32, 0, tzinfo=timezone.utc)
        next_bar = calculate_next_bar_start(current, "5m")

        assert next_bar == datetime(2024, 1, 15, 9, 35, 0, tzinfo=timezone.utc)

    def test_next_bar_start_15m(self) -> None:
        """09:20:00 → next bar at 09:30:00."""
        current = datetime(2024, 1, 15, 9, 20, 0, tzinfo=timezone.utc)
        next_bar = calculate_next_bar_start(current, "15m")

        assert next_bar == datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

    def test_next_bar_start_1h(self) -> None:
        """09:45:30 → next bar at 10:00:00."""
        current = datetime(2024, 1, 15, 9, 45, 30, tzinfo=timezone.utc)
        next_bar = calculate_next_bar_start(current, "1h")

        assert next_bar == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def test_next_bar_start_1d(self) -> None:
        """Any time → next bar at midnight UTC next day."""
        current = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        next_bar = calculate_next_bar_start(current, "1d")

        assert next_bar == datetime(2024, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

    def test_bar_alignment_exactly_on_boundary(self) -> None:
        """Exactly on boundary should return next bar, not current."""
        # Exactly at 09:30:00
        current = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        next_bar = calculate_next_bar_start(current, "1m")

        # Should return 09:31:00, not 09:30:00
        assert next_bar == datetime(2024, 1, 15, 9, 31, 0, tzinfo=timezone.utc)

    def test_handles_naive_datetime(self) -> None:
        """Should handle naive datetime by treating as UTC."""
        current = datetime(2024, 1, 15, 9, 30, 45)  # Naive
        next_bar = calculate_next_bar_start(current, "1m")

        assert next_bar.tzinfo == timezone.utc
        assert next_bar == datetime(2024, 1, 15, 9, 31, 0, tzinfo=timezone.utc)

    def test_handles_day_boundary(self) -> None:
        """Should handle crossing midnight correctly."""
        current = datetime(2024, 1, 15, 23, 59, 30, tzinfo=timezone.utc)
        next_bar = calculate_next_bar_start(current, "1m")

        assert next_bar == datetime(2024, 1, 16, 0, 0, 0, tzinfo=timezone.utc)


class TestCalculateBarStart:
    """Tests for current bar start calculation."""

    def test_bar_start_within_bar(self) -> None:
        """Should find the start of the containing bar."""
        current = datetime(2024, 1, 15, 9, 32, 45, tzinfo=timezone.utc)
        bar_start = calculate_bar_start(current, "5m")

        assert bar_start == datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

    def test_bar_start_exactly_on_boundary(self) -> None:
        """Exactly on boundary should return that boundary."""
        current = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        bar_start = calculate_bar_start(current, "1m")

        assert bar_start == datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

    def test_bar_start_daily(self) -> None:
        """Daily bar starts at midnight UTC."""
        current = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        bar_start = calculate_bar_start(current, "1d")

        assert bar_start == datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)


class TestSecondsUntilNextBar:
    """Tests for seconds until next bar calculation."""

    def test_seconds_until_next_bar(self) -> None:
        """Should calculate correct seconds remaining."""
        current = datetime(2024, 1, 15, 9, 30, 45, tzinfo=timezone.utc)
        seconds = seconds_until_next_bar(current, "1m")

        assert seconds == 15.0  # 15 seconds until 09:31:00

    def test_seconds_at_boundary(self) -> None:
        """At boundary, should return full timeframe."""
        current = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
        seconds = seconds_until_next_bar(current, "1m")

        assert seconds == 60.0  # Full minute until next bar

    def test_seconds_with_microseconds(self) -> None:
        """Should handle microseconds correctly."""
        current = datetime(2024, 1, 15, 9, 30, 45, 500000, tzinfo=timezone.utc)
        seconds = seconds_until_next_bar(current, "1m")

        assert seconds == pytest.approx(14.5, abs=0.001)

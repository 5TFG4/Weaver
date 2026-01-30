"""
Clock Utilities

Bar alignment calculations and timeframe parsing utilities.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple


class TimeframeDuration(NamedTuple):
    """Parsed timeframe with its duration."""

    code: str
    seconds: int


# Timeframe definitions
TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


def parse_timeframe(timeframe: str) -> TimeframeDuration:
    """
    Parse a timeframe string into its duration.

    Args:
        timeframe: Timeframe code (e.g., '1m', '5m', '1h', '1d')

    Returns:
        TimeframeDuration with code and seconds

    Raises:
        ValueError: If timeframe is not recognized
    """
    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(
            f"Unknown timeframe: {timeframe}. "
            f"Supported: {', '.join(TIMEFRAME_SECONDS.keys())}"
        )
    return TimeframeDuration(code=timeframe, seconds=TIMEFRAME_SECONDS[timeframe])


def calculate_next_bar_start(
    current_time: datetime,
    timeframe: str,
) -> datetime:
    """
    Calculate the start time of the next bar.

    Bar boundaries are aligned to clock time:
    - 1m: Every minute at :00 seconds
    - 5m: Every 5 minutes at :00, :05, :10, etc.
    - 15m: Every 15 minutes at :00, :15, :30, :45
    - 1h: Every hour at :00:00
    - 1d: Every day at 00:00:00 UTC

    Args:
        current_time: The current timestamp (should be UTC)
        timeframe: Timeframe code (e.g., '1m', '5m', '1h')

    Returns:
        Start time of the next bar (UTC)

    Examples:
        >>> calculate_next_bar_start(datetime(2024, 1, 15, 9, 30, 45), "1m")
        datetime(2024, 1, 15, 9, 31, 0)

        >>> calculate_next_bar_start(datetime(2024, 1, 15, 9, 32, 0), "5m")
        datetime(2024, 1, 15, 9, 35, 0)
    """
    tf = parse_timeframe(timeframe)

    # Ensure we have a timezone-aware datetime in UTC
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    else:
        current_time = current_time.astimezone(timezone.utc)

    if timeframe == "1d":
        # Daily bars start at midnight UTC
        next_day = current_time.date() + timedelta(days=1)
        return datetime(
            next_day.year,
            next_day.month,
            next_day.day,
            0,
            0,
            0,
            tzinfo=timezone.utc,
        )

    # For intraday timeframes, calculate based on seconds since midnight
    midnight = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = (current_time - midnight).total_seconds()

    # Find the current bar boundary
    current_bar_start_seconds = (
        int(seconds_since_midnight) // tf.seconds
    ) * tf.seconds

    # Next bar starts one interval later
    next_bar_start_seconds = current_bar_start_seconds + tf.seconds

    # Handle day overflow
    if next_bar_start_seconds >= 86400:
        # Move to next day
        next_day = current_time.date() + timedelta(days=1)
        return datetime(
            next_day.year,
            next_day.month,
            next_day.day,
            0,
            0,
            0,
            tzinfo=timezone.utc,
        )

    # Calculate the next bar start time
    next_bar_start = midnight + timedelta(seconds=next_bar_start_seconds)

    # If we're exactly on a bar boundary, return the next bar
    if current_time == midnight + timedelta(seconds=current_bar_start_seconds):
        pass  # Already calculated correctly

    return next_bar_start


def calculate_bar_start(
    timestamp: datetime,
    timeframe: str,
) -> datetime:
    """
    Calculate the start time of the bar containing the given timestamp.

    Args:
        timestamp: The timestamp to find the bar for
        timeframe: Timeframe code (e.g., '1m', '5m', '1h')

    Returns:
        Start time of the containing bar (UTC)
    """
    tf = parse_timeframe(timeframe)

    # Ensure UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    if timeframe == "1d":
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

    midnight = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = (timestamp - midnight).total_seconds()
    bar_start_seconds = (int(seconds_since_midnight) // tf.seconds) * tf.seconds

    return midnight + timedelta(seconds=bar_start_seconds)


def seconds_until_next_bar(
    current_time: datetime,
    timeframe: str,
) -> float:
    """
    Calculate seconds until the next bar starts.

    Args:
        current_time: The current timestamp
        timeframe: Timeframe code

    Returns:
        Seconds until next bar (can be fractional)
    """
    next_bar = calculate_next_bar_start(current_time, timeframe)
    return (next_bar - current_time).total_seconds()

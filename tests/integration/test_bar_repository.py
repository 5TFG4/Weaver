"""Integration tests for BarRepository.

These tests use the real PostgreSQL database via DB_URL.
Run with: DB_URL=postgresql+asyncpg://... pytest tests/integration/test_bar_repository.py -v
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.walle.models import BarRecord
from src.walle.repositories.bar_repository import Bar, BarRepository


def make_bar(
    symbol: str = "BTC/USD",
    timeframe: str = "1m",
    timestamp: datetime | None = None,
    open_: Decimal = Decimal("100.00"),
    high: Decimal = Decimal("101.00"),
    low: Decimal = Decimal("99.00"),
    close: Decimal = Decimal("100.50"),
    volume: Decimal = Decimal("1000.00"),
) -> Bar:
    """Factory for creating test Bar objects."""
    return Bar(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp or datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


@pytest.mark.integration
class TestBarRepository:
    """Integration tests for BarRepository with real PostgreSQL."""

    @pytest_asyncio.fixture
    async def clean_bars(self, database):
        """Clean bars table before and after test."""
        async with database.session() as sess:
            await sess.execute(text("TRUNCATE TABLE bars RESTART IDENTITY CASCADE"))
            await sess.commit()
        yield
        async with database.session() as sess:
            await sess.execute(text("TRUNCATE TABLE bars RESTART IDENTITY CASCADE"))
            await sess.commit()

    @pytest_asyncio.fixture
    async def repo(self, database, clean_bars) -> BarRepository:
        """Create repository with test session factory."""
        return BarRepository(database.session_factory)

    async def test_save_bars_empty_list(self, repo: BarRepository) -> None:
        """Saving empty list returns 0."""
        count = await repo.save_bars([])
        assert count == 0

    async def test_save_and_get_bars(self, repo: BarRepository) -> None:
        """Can save and retrieve bars."""
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bars = [make_bar(timestamp=ts)]

        count = await repo.save_bars(bars)
        assert count == 1

        result = await repo.get_bars(
            "BTC/USD",
            "1m",
            start=ts - timedelta(minutes=1),
            end=ts + timedelta(minutes=1),
        )
        assert len(result) == 1
        assert result[0].symbol == "BTC/USD"
        assert result[0].close == Decimal("100.50")

    async def test_get_bars_returns_sorted(self, repo: BarRepository) -> None:
        """Bars are returned sorted by timestamp."""
        base = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bars = [
            make_bar(timestamp=base + timedelta(minutes=2)),
            make_bar(timestamp=base),
            make_bar(timestamp=base + timedelta(minutes=1)),
        ]

        await repo.save_bars(bars)
        result = await repo.get_bars(
            "BTC/USD",
            "1m",
            start=base - timedelta(minutes=1),
            end=base + timedelta(minutes=5),
        )

        assert len(result) == 3
        assert result[0].timestamp < result[1].timestamp < result[2].timestamp

    async def test_save_bars_upsert_skips_duplicates(self, repo: BarRepository) -> None:
        """Duplicate bars are skipped, not errored."""
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bar = make_bar(timestamp=ts)

        count1 = await repo.save_bars([bar])
        count2 = await repo.save_bars([bar])

        assert count1 == 1
        assert count2 == 0  # Duplicate skipped

        result = await repo.get_bars(
            "BTC/USD",
            "1m",
            start=ts - timedelta(minutes=1),
            end=ts + timedelta(minutes=1),
        )
        assert len(result) == 1

    async def test_get_bars_filters_by_symbol(self, repo: BarRepository) -> None:
        """Only returns bars for requested symbol."""
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bars = [
            make_bar(symbol="BTC/USD", timestamp=ts),
            make_bar(symbol="ETH/USD", timestamp=ts),
        ]

        await repo.save_bars(bars)
        result = await repo.get_bars(
            "BTC/USD",
            "1m",
            start=ts - timedelta(minutes=1),
            end=ts + timedelta(minutes=1),
        )

        assert len(result) == 1
        assert result[0].symbol == "BTC/USD"

    async def test_get_bars_filters_by_timeframe(self, repo: BarRepository) -> None:
        """Only returns bars for requested timeframe."""
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bars = [
            make_bar(timeframe="1m", timestamp=ts),
            make_bar(timeframe="5m", timestamp=ts),
        ]

        await repo.save_bars(bars)
        result = await repo.get_bars(
            "BTC/USD",
            "1m",
            start=ts - timedelta(minutes=1),
            end=ts + timedelta(minutes=1),
        )

        assert len(result) == 1
        assert result[0].timeframe == "1m"

    async def test_get_bars_respects_time_range(self, repo: BarRepository) -> None:
        """Only returns bars within requested time range."""
        base = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bars = [
            make_bar(timestamp=base),
            make_bar(timestamp=base + timedelta(minutes=1)),
            make_bar(timestamp=base + timedelta(minutes=2)),
            make_bar(timestamp=base + timedelta(minutes=3)),
        ]

        await repo.save_bars(bars)
        result = await repo.get_bars(
            "BTC/USD",
            "1m",
            start=base + timedelta(minutes=1),
            end=base + timedelta(minutes=2),
        )

        assert len(result) == 2

    async def test_get_bar_count(self, repo: BarRepository) -> None:
        """Can count bars without fetching."""
        base = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bars = [make_bar(timestamp=base + timedelta(minutes=i)) for i in range(5)]

        await repo.save_bars(bars)
        count = await repo.get_bar_count(
            "BTC/USD",
            "1m",
            start=base,
            end=base + timedelta(minutes=10),
        )

        assert count == 5

    async def test_get_latest_bar(self, repo: BarRepository) -> None:
        """Can get most recent bar."""
        base = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bars = [
            make_bar(timestamp=base, close=Decimal("100")),
            make_bar(timestamp=base + timedelta(minutes=1), close=Decimal("101")),
            make_bar(timestamp=base + timedelta(minutes=2), close=Decimal("102")),
        ]

        await repo.save_bars(bars)
        latest = await repo.get_latest_bar("BTC/USD", "1m")

        assert latest is not None
        assert latest.close == Decimal("102")

    async def test_get_latest_bar_returns_none_when_empty(
        self, repo: BarRepository
    ) -> None:
        """Returns None when no bars exist."""
        result = await repo.get_latest_bar("NONEXISTENT/USD", "1m")
        assert result is None

    async def test_bars_preserve_decimal_precision(self, repo: BarRepository) -> None:
        """Decimal precision is preserved through save/load."""
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bar = Bar(
            symbol="BTC/USD",
            timeframe="1m",
            timestamp=ts,
            open=Decimal("42123.12345678"),
            high=Decimal("42200.00000001"),
            low=Decimal("42000.99999999"),
            close=Decimal("42150.50505050"),
            volume=Decimal("12345.67890123"),
        )

        await repo.save_bars([bar])
        result = await repo.get_bars(
            "BTC/USD",
            "1m",
            start=ts - timedelta(minutes=1),
            end=ts + timedelta(minutes=1),
        )

        assert len(result) == 1
        assert result[0].open == Decimal("42123.12345678")
        assert result[0].volume == Decimal("12345.67890123")


@pytest.mark.integration
class TestBarRecordModel:
    """Tests for BarRecord model structure."""

    def test_model_has_correct_tablename(self) -> None:
        assert BarRecord.__tablename__ == "bars"

    def test_model_has_required_columns(self) -> None:
        columns = {c.name for c in BarRecord.__table__.columns}
        expected = {
            "id",
            "symbol",
            "timeframe",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }
        assert expected.issubset(columns)

    def test_repr(self) -> None:
        bar = BarRecord(
            symbol="BTC/USD",
            timeframe="1m",
            timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("1000"),
        )
        assert "BTC/USD" in repr(bar)
        assert "1m" in repr(bar)


class TestBarDataclass:
    """Unit tests for Bar dataclass (no database needed)."""

    def test_bar_is_frozen(self) -> None:
        bar = make_bar()
        with pytest.raises(AttributeError):
            bar.symbol = "ETH/USD"  # type: ignore[misc]

    def test_bar_equality(self) -> None:
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        bar1 = make_bar(timestamp=ts)
        bar2 = make_bar(timestamp=ts)
        assert bar1 == bar2

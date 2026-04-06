"""Integration tests for ResultRepository.

Tests the complete result persistence lifecycle with real PostgreSQL:
- Save and retrieve backtest results
- JSONB round-trip for complex nested payloads (stats, equity_curve, fills)
- Upsert (merge) semantics
- Missing record returns None

Run with: DB_URL=postgresql+asyncpg://... pytest tests/integration/test_result_repository.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text

from src.walle.models import BacktestResultRecord
from src.walle.repositories.result_repository import ResultRepository


def _make_record(
    run_id: str = "test-run-001",
    *,
    final_equity: str = "105000.50",
    total_bars: int = 100,
) -> BacktestResultRecord:
    """Factory for creating test BacktestResultRecord objects."""
    return BacktestResultRecord(
        run_id=run_id,
        start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        end_time=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        timeframe="1m",
        symbols=["BTC/USD", "ETH/USD"],
        final_equity=final_equity,
        simulation_duration_ms=1234,
        total_bars_processed=total_bars,
        stats={
            "total_return": "5000.50",
            "total_return_pct": "5.0",
            "annualized_return": "60.0",
            "sharpe_ratio": "1.85",
            "sortino_ratio": "2.10",
            "max_drawdown": "1200.00",
            "max_drawdown_pct": "1.14",
            "total_trades": 8,
            "winning_trades": 5,
            "losing_trades": 3,
            "win_rate": "0.625",
            "avg_win": "1500.00",
            "avg_loss": "833.50",
            "profit_factor": "3.0",
            "total_bars": total_bars,
            "bars_in_position": 42,
            "total_commission": "16.00",
            "total_slippage": "8.00",
        },
        equity_curve=[
            {"t": "2024-01-01T09:30:00+00:00", "equity": "100000.00"},
            {"t": "2024-01-01T10:00:00+00:00", "equity": "102500.00"},
            {"t": "2024-01-01T11:00:00+00:00", "equity": "105000.50"},
        ],
        fills=[
            {
                "order_id": "ord-001",
                "client_order_id": "cli-001",
                "symbol": "BTC/USD",
                "side": "buy",
                "qty": "0.5",
                "fill_price": "42000.00",
                "commission": "2.00",
                "slippage": "1.00",
                "timestamp": "2024-01-01T09:35:00+00:00",
                "bar_index": 5,
            },
            {
                "order_id": "ord-002",
                "client_order_id": "cli-002",
                "symbol": "BTC/USD",
                "side": "sell",
                "qty": "0.5",
                "fill_price": "52000.00",
                "commission": "2.00",
                "slippage": "1.00",
                "timestamp": "2024-01-01T10:30:00+00:00",
                "bar_index": 60,
            },
        ],
    )


@pytest.mark.integration
class TestResultRepository:
    """Integration tests for ResultRepository with real PostgreSQL."""

    @pytest_asyncio.fixture
    async def clean_results(self, database):
        """Clean backtest_results table before and after test."""
        async with database.session() as sess:
            await sess.execute(text("TRUNCATE TABLE backtest_results CASCADE"))
            await sess.commit()
        yield
        async with database.session() as sess:
            await sess.execute(text("TRUNCATE TABLE backtest_results CASCADE"))
            await sess.commit()

    @pytest_asyncio.fixture
    async def repo(self, database, clean_results) -> ResultRepository:
        """Create repository with test session factory."""
        return ResultRepository(database.session_factory)

    async def test_save_and_get_by_run_id(self, repo: ResultRepository) -> None:
        """Can save a result and retrieve it by run_id."""
        record = _make_record("run-roundtrip")

        await repo.save(record)
        loaded = await repo.get_by_run_id("run-roundtrip")

        assert loaded is not None
        assert loaded.run_id == "run-roundtrip"
        assert loaded.final_equity == "105000.50"
        assert loaded.timeframe == "1m"
        assert loaded.simulation_duration_ms == 1234
        assert loaded.total_bars_processed == 100

    async def test_get_by_run_id_returns_none_when_missing(self, repo: ResultRepository) -> None:
        """Returns None for a non-existent run_id."""
        result = await repo.get_by_run_id("does-not-exist")
        assert result is None

    async def test_timestamps_roundtrip(self, repo: ResultRepository) -> None:
        """Start/end times preserve timezone through DB round-trip."""
        record = _make_record("run-timestamps")

        await repo.save(record)
        loaded = await repo.get_by_run_id("run-timestamps")

        assert loaded is not None
        assert loaded.start_time == datetime(2024, 1, 1, 9, 30, tzinfo=UTC)
        assert loaded.end_time == datetime(2024, 1, 1, 11, 0, tzinfo=UTC)
        assert loaded.created_at is not None

    async def test_symbols_jsonb_roundtrip(self, repo: ResultRepository) -> None:
        """Symbols list survives JSONB serialization."""
        record = _make_record("run-symbols")

        await repo.save(record)
        loaded = await repo.get_by_run_id("run-symbols")

        assert loaded is not None
        assert loaded.symbols == ["BTC/USD", "ETH/USD"]

    async def test_stats_jsonb_roundtrip(self, repo: ResultRepository) -> None:
        """Stats dict with nested numeric strings survives JSONB round-trip."""
        record = _make_record("run-stats")

        await repo.save(record)
        loaded = await repo.get_by_run_id("run-stats")

        assert loaded is not None
        assert loaded.stats["total_return"] == "5000.50"
        assert loaded.stats["sharpe_ratio"] == "1.85"
        assert loaded.stats["total_trades"] == 8
        assert loaded.stats["profit_factor"] == "3.0"
        assert loaded.stats["total_commission"] == "16.00"

    async def test_equity_curve_jsonb_roundtrip(self, repo: ResultRepository) -> None:
        """Equity curve list of {t, equity} dicts survives JSONB round-trip."""
        record = _make_record("run-equity")

        await repo.save(record)
        loaded = await repo.get_by_run_id("run-equity")

        assert loaded is not None
        assert len(loaded.equity_curve) == 3
        assert loaded.equity_curve[0]["t"] == "2024-01-01T09:30:00+00:00"
        assert loaded.equity_curve[0]["equity"] == "100000.00"
        assert loaded.equity_curve[-1]["equity"] == "105000.50"

    async def test_fills_jsonb_roundtrip(self, repo: ResultRepository) -> None:
        """Fills list with all fill fields survives JSONB round-trip."""
        record = _make_record("run-fills")

        await repo.save(record)
        loaded = await repo.get_by_run_id("run-fills")

        assert loaded is not None
        assert len(loaded.fills) == 2
        buy = loaded.fills[0]
        assert buy["order_id"] == "ord-001"
        assert buy["symbol"] == "BTC/USD"
        assert buy["side"] == "buy"
        assert buy["qty"] == "0.5"
        assert buy["fill_price"] == "42000.00"
        assert buy["bar_index"] == 5
        sell = loaded.fills[1]
        assert sell["side"] == "sell"
        assert sell["fill_price"] == "52000.00"

    async def test_upsert_overwrites_existing(self, repo: ResultRepository) -> None:
        """save() with same run_id overwrites the previous record (merge)."""
        original = _make_record("run-upsert", final_equity="100000.00")
        await repo.save(original)

        updated = _make_record("run-upsert", final_equity="120000.00", total_bars=200)
        await repo.save(updated)

        loaded = await repo.get_by_run_id("run-upsert")
        assert loaded is not None
        assert loaded.final_equity == "120000.00"
        assert loaded.total_bars_processed == 200

    async def test_multiple_runs_isolated(self, repo: ResultRepository) -> None:
        """Results for different runs are stored and retrieved independently."""
        await repo.save(_make_record("run-A", final_equity="100000.00"))
        await repo.save(_make_record("run-B", final_equity="200000.00"))

        a = await repo.get_by_run_id("run-A")
        b = await repo.get_by_run_id("run-B")

        assert a is not None and a.final_equity == "100000.00"
        assert b is not None and b.final_equity == "200000.00"

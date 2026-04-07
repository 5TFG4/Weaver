"""
Tests for BacktestResultRecord model and ResultRepository.

M13-2: backtest_results table and repository.
TDD: RED → GREEN → REFACTOR
"""

from unittest.mock import MagicMock

from sqlalchemy import inspect

from src.walle.models import BacktestResultRecord, Base


class TestBacktestResultRecordModel:
    """M13-2: BacktestResultRecord model structure tests."""

    def test_tablename(self) -> None:
        assert BacktestResultRecord.__tablename__ == "backtest_results"

    def test_columns_exist(self) -> None:
        mapper = inspect(BacktestResultRecord)
        names = {c.key for c in mapper.columns}
        expected = {
            "run_id",
            "start_time",
            "end_time",
            "timeframe",
            "symbols",
            "final_equity",
            "simulation_duration_ms",
            "total_bars_processed",
            "stats",
            "equity_curve",
            "fills",
            "created_at",
        }
        assert expected.issubset(names)

    def test_run_id_is_primary_key(self) -> None:
        mapper = inspect(BacktestResultRecord)
        pk = [c.key for c in mapper.primary_key]
        assert pk == ["run_id"]

    def test_registered_in_base_metadata(self) -> None:
        assert "backtest_results" in Base.metadata.tables


class TestResultRepositoryInterface:
    """M13-2: ResultRepository interface tests."""

    def test_constructor_accepts_session_factory(self) -> None:
        from src.walle.repositories.result_repository import ResultRepository

        repo = ResultRepository(session_factory=MagicMock())
        assert repo._session_factory is not None

    def test_has_save_method(self) -> None:
        from src.walle.repositories.result_repository import ResultRepository

        assert callable(getattr(ResultRepository, "save", None))

    def test_has_get_by_run_id_method(self) -> None:
        from src.walle.repositories.result_repository import ResultRepository

        assert callable(getattr(ResultRepository, "get_by_run_id", None))

"""
Tests for GLaDOS Schemas

MVP-1: Bootable Skeleton
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_has_status_field(self) -> None:
        """HealthResponse should have status field."""
        from src.glados.schemas import HealthResponse

        response = HealthResponse(status="ok", version="0.1.0")

        assert response.status == "ok"

    def test_has_version_field(self) -> None:
        """HealthResponse should have version field."""
        from src.glados.schemas import HealthResponse

        response = HealthResponse(status="ok", version="0.1.0")

        assert response.version == "0.1.0"

    def test_serializes_to_dict(self) -> None:
        """HealthResponse should serialize to dict."""
        from src.glados.schemas import HealthResponse

        response = HealthResponse(status="ok", version="0.1.0")
        data = response.model_dump()

        assert data == {"status": "ok", "version": "0.1.0"}


class TestRunCreate:
    """Tests for RunCreate schema — S1 config refactor."""

    def test_run_create_requires_config(self) -> None:
        """config is required, not optional."""
        from src.glados.schemas import RunCreate

        with pytest.raises(ValidationError):
            RunCreate(strategy_id="test", mode="paper")  # missing config

    def test_run_create_accepts_config(self) -> None:
        from src.glados.schemas import RunCreate

        rc = RunCreate(strategy_id="test", mode="paper", config={"symbols": ["BTC/USD"]})
        assert rc.config == {"symbols": ["BTC/USD"]}

    def test_run_create_no_extra_fields(self) -> None:
        """RunCreate only accepts strategy_id, mode, config."""
        from src.glados.schemas import RunCreate

        with pytest.raises(ValidationError):
            RunCreate(
                strategy_id="test",
                mode="paper",
                config={},
                timeframe="5m",
            )

    def test_run_create_no_symbols_top_level(self) -> None:
        """symbols must NOT be a top-level field."""
        from src.glados.schemas import RunCreate

        with pytest.raises(ValidationError):
            RunCreate(
                strategy_id="test",
                mode="paper",
                config={"symbols": ["X"]},
                symbols=["Y"],
            )

    def test_run_create_no_start_time_top_level(self) -> None:
        """start_time must NOT be a top-level field."""
        from src.glados.schemas import RunCreate

        with pytest.raises(ValidationError):
            RunCreate(
                strategy_id="test",
                mode="paper",
                config={},
                start_time="2024-01-01T00:00:00Z",
            )


class TestRunResponse:
    """Tests for RunResponse schema — S1 config refactor."""

    def test_run_response_has_config(self) -> None:
        from src.glados.schemas import RunResponse

        resp = RunResponse(
            id="1",
            strategy_id="test",
            mode="paper",
            status="pending",
            config={"symbols": ["BTC/USD"]},
            created_at=datetime.now(UTC),
        )
        assert resp.config == {"symbols": ["BTC/USD"]}

    def test_run_response_no_symbols_field(self) -> None:
        from src.glados.schemas import RunResponse

        resp = RunResponse(
            id="1",
            strategy_id="test",
            mode="paper",
            status="pending",
            config={"symbols": ["BTC/USD"]},
            created_at=datetime.now(UTC),
        )
        assert not hasattr(resp, "symbols")

    def test_run_response_no_timeframe_field(self) -> None:
        from src.glados.schemas import RunResponse

        resp = RunResponse(
            id="1",
            strategy_id="test",
            mode="paper",
            status="pending",
            config={"symbols": ["BTC/USD"]},
            created_at=datetime.now(UTC),
        )
        assert not hasattr(resp, "timeframe")

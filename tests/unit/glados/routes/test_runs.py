"""
Tests for Runs Endpoint

MVP-2: Run Lifecycle
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient


class TestListRunsEndpoint:
    """Tests for GET /api/v1/runs."""

    def test_returns_200(self, client: TestClient) -> None:
        """GET /runs should return HTTP 200."""
        response = client.get("/api/v1/runs")

        assert response.status_code == 200

    def test_empty_returns_empty_items(self, client: TestClient) -> None:
        """GET /runs with no runs returns empty items list."""
        response = client.get("/api/v1/runs")
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_created_runs(self, client: TestClient) -> None:
        """GET /runs should return all created runs."""
        # Create a run first
        client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )

        response = client.get("/api/v1/runs")
        data = response.json()

        assert len(data["items"]) == 1
        assert data["total"] == 1


class TestCreateRunEndpoint:
    """Tests for POST /api/v1/runs."""

    def test_returns_201(self, client: TestClient) -> None:
        """POST /runs with valid data returns HTTP 201."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )

        assert response.status_code == 201

    def test_returns_run_with_id(self, client: TestClient) -> None:
        """POST /runs should return run with generated ID."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )
        data = response.json()

        assert "id" in data
        assert len(data["id"]) == 36  # UUID format

    def test_returns_pending_status(self, client: TestClient) -> None:
        """POST /runs should return run with pending status."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )
        data = response.json()

        assert data["status"] == "pending"

    def test_validates_required_fields(self, client: TestClient) -> None:
        """POST /runs without required fields returns 422."""
        response = client.post("/api/v1/runs", json={})

        assert response.status_code == 422

    def test_validates_mode_enum(self, client: TestClient) -> None:
        """POST /runs with invalid mode returns 422."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "invalid_mode",
                "config": {"symbols": ["BTC/USD"]},
            },
        )

        assert response.status_code == 422

    def test_rejects_extra_fields(self, client: TestClient) -> None:
        """POST /runs with extra top-level fields returns 422 (extra=forbid)."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
                "symbols": ["BTC/USD"],
            },
        )

        assert response.status_code == 422


class TestGetRunEndpoint:
    """Tests for GET /api/v1/runs/{id}."""

    def test_returns_run(self, client: TestClient) -> None:
        """GET /runs/{id} returns the run details."""
        # Create a run first
        create_resp = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )
        run_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/runs/{run_id}")

        assert response.status_code == 200
        assert response.json()["id"] == run_id

    def test_not_found_returns_404(self, client: TestClient) -> None:
        """GET /runs/{id} with unknown ID returns 404."""
        response = client.get("/api/v1/runs/non-existent-id")

        assert response.status_code == 404


class TestStopRunEndpoint:
    """Tests for POST /api/v1/runs/{id}/stop."""

    def test_stops_run(self, client: TestClient) -> None:
        """POST /runs/{id}/stop changes status to stopped."""
        # Create a run
        create_resp = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )
        run_id = create_resp.json()["id"]

        response = client.post(f"/api/v1/runs/{run_id}/stop")

        assert response.status_code == 200
        assert response.json()["status"] == "stopped"

    def test_not_found_returns_404(self, client: TestClient) -> None:
        """POST /runs/{id}/stop with unknown ID returns 404."""
        response = client.post("/api/v1/runs/non-existent-id/stop")

        assert response.status_code == 404


class TestStartRunEndpoint:
    """Tests for POST /api/v1/runs/{id}/start.

    M8-P0 / C-02: Start route was missing — frontend startRun() had no backend.
    """

    def test_start_run_returns_200(self, client: TestClient) -> None:
        """POST /runs/{id}/start should return 200 with RunResponse."""
        create_resp = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )
        run_id = create_resp.json()["id"]

        response = client.post(f"/api/v1/runs/{run_id}/start")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run_id
        assert data["status"] == "running"

    def test_start_unknown_run_returns_404(self, client: TestClient) -> None:
        """POST /runs/{id}/start with unknown ID returns 404."""
        response = client.post("/api/v1/runs/non-existent-id/start")

        assert response.status_code == 404

    def test_start_already_running_returns_409(self, client: TestClient) -> None:
        """POST /runs/{id}/start on already-running run returns 409."""
        create_resp = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )
        run_id = create_resp.json()["id"]

        # Start once
        client.post(f"/api/v1/runs/{run_id}/start")

        # Start again — should be 409
        response = client.post(f"/api/v1/runs/{run_id}/start")

        assert response.status_code == 409


class TestRunsPagination:
    """N-10/M-02: Server-side pagination for runs."""

    def _create_runs(self, client: TestClient, count: int) -> None:
        """Helper: create N runs."""
        for i in range(count):
            client.post(
                "/api/v1/runs",
                json={
                    "strategy_id": f"strategy-{i}",
                    "mode": "paper",
                    "config": {"symbols": ["BTC/USD"]},
                },
            )

    def test_default_pagination(self, client: TestClient) -> None:
        """GET /runs without params returns page 1 with default page_size."""
        self._create_runs(client, 3)

        response = client.get("/api/v1/runs")
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 3
        assert data["total"] == 3

    def test_page_size_limits_results(self, client: TestClient) -> None:
        """GET /runs with page_size=2 returns at most 2 items."""
        self._create_runs(client, 5)

        response = client.get("/api/v1/runs?page_size=2")
        data = response.json()

        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_page_offset(self, client: TestClient) -> None:
        """GET /runs with page=2&page_size=2 returns next slice."""
        self._create_runs(client, 5)

        response = client.get("/api/v1/runs?page=2&page_size=2")
        data = response.json()

        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 2


class TestRunsStatusFiltering:
    """M8-R3/R-08: status query param contract for run listing."""

    def test_filters_runs_by_status(self, client: TestClient) -> None:
        """GET /runs?status=running returns only running runs."""
        # Run A stays running (paper mode)
        run_a = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "s1",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        ).json()
        client.post(f"/api/v1/runs/{run_a['id']}/start")

        # Run B gets stopped
        run_b = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "s2",
                "mode": "paper",
                "config": {"symbols": ["ETH/USD"]},
            },
        ).json()
        client.post(f"/api/v1/runs/{run_b['id']}/stop")

        response = client.get("/api/v1/runs?status=running")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "running"


class TestRunResponseErrorField:
    """M13-4: RunResponse includes error field."""

    def test_run_response_includes_error_key(self, client: TestClient) -> None:
        """GET /runs/{id} response JSON must contain 'error' key."""
        run = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        ).json()

        response = client.get(f"/api/v1/runs/{run['id']}")
        data = response.json()
        assert "error" in data
        assert data["error"] is None

    def test_list_runs_items_include_error_key(self, client: TestClient) -> None:
        """GET /runs list items must include 'error' key."""
        client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )

        response = client.get("/api/v1/runs")
        items = response.json()["items"]
        assert len(items) > 0
        assert "error" in items[0]


class TestBacktestDateValidation:
    """M13-5: Validate backtest date fields on run creation."""

    def test_backtest_missing_start_returns_422(self, client: TestClient) -> None:
        """POST /runs with backtest mode but no backtest_start returns 422."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "backtest",
                "config": {
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_end": "2024-12-31T00:00:00Z",
                },
            },
        )
        assert response.status_code == 422

    def test_backtest_missing_end_returns_422(self, client: TestClient) -> None:
        """POST /runs with backtest mode but no backtest_end returns 422."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "backtest",
                "config": {
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": "2024-01-01T00:00:00Z",
                },
            },
        )
        assert response.status_code == 422

    def test_backtest_naive_datetime_returns_422(self, client: TestClient) -> None:
        """POST /runs with naive datetime (no timezone info) returns 422."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "backtest",
                "config": {
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": "2024-01-01T00:00:00",
                    "backtest_end": "2024-12-31T00:00:00",
                },
            },
        )
        assert response.status_code == 422

    def test_backtest_end_before_start_returns_422(self, client: TestClient) -> None:
        """POST /runs with backtest_end before backtest_start returns 422."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "backtest",
                "config": {
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": "2024-12-01T00:00:00Z",
                    "backtest_end": "2024-01-01T00:00:00Z",
                },
            },
        )
        assert response.status_code == 422

    def test_backtest_invalid_date_format_returns_422(self, client: TestClient) -> None:
        """POST /runs with unparseable date string returns 422."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "backtest",
                "config": {
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": "not-a-date",
                    "backtest_end": "2024-12-31T00:00:00Z",
                },
            },
        )
        assert response.status_code == 422

    def test_backtest_valid_dates_returns_201(self, client: TestClient) -> None:
        """POST /runs with valid timezone-aware backtest dates returns 201."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "backtest",
                "config": {
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": "2024-01-01T00:00:00Z",
                    "backtest_end": "2024-12-31T00:00:00Z",
                },
            },
        )
        assert response.status_code == 201

    def test_paper_mode_skips_date_validation(self, client: TestClient) -> None:
        """POST /runs with paper mode does not require date fields."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "config": {"symbols": ["BTC/USD"]},
            },
        )
        assert response.status_code == 201


class TestResultsEndpoint:
    """M13-3: GET /api/v1/runs/{run_id}/results returns backtest result."""

    def _seed_result(self, client: TestClient, run_id: str) -> None:
        """Configure the mock result_repository to return a sample result."""
        from src.walle.models import BacktestResultRecord

        record = BacktestResultRecord(
            run_id=run_id,
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 6, 30, tzinfo=UTC),
            timeframe="1m",
            symbols=["BTC/USD"],
            final_equity="105000.00",
            simulation_duration_ms=1234,
            total_bars_processed=500,
            stats={
                "total_return": 5000.0,
                "total_return_pct": 5.0,
                "sharpe_ratio": 1.25,
                "max_drawdown": 2000.0,
                "max_drawdown_pct": 1.9,
                "total_trades": 10,
                "winning_trades": 6,
                "losing_trades": 4,
                "win_rate": 0.6,
            },
            equity_curve=[
                {"timestamp": "2024-01-01T00:00:00+00:00", "equity": 100000.0},
                {"timestamp": "2024-06-30T00:00:00+00:00", "equity": 105000.0},
            ],
            fills=[
                {
                    "order_id": "o1",
                    "symbol": "BTC/USD",
                    "side": "buy",
                    "qty": "0.1",
                    "fill_price": "42000.00",
                    "timestamp": "2024-01-15T10:00:00+00:00",
                },
            ],
        )
        client.app.state.result_repository.get_by_run_id.return_value = record  # type: ignore[union-attr]

    def test_result_found_returns_200(self, client: TestClient) -> None:
        """GET /runs/{id}/results returns 200 when result exists."""
        run_id = "test-run-123"
        self._seed_result(client, run_id)

        response = client.get(f"/api/v1/runs/{run_id}/results")

        assert response.status_code == 200

    def test_result_not_found_returns_404(self, client: TestClient) -> None:
        """GET /runs/{id}/results returns 404 when no result exists."""
        response = client.get("/api/v1/runs/nonexistent-run/results")

        assert response.status_code == 404

    def test_result_has_expected_top_level_fields(self, client: TestClient) -> None:
        """Response includes all expected top-level fields."""
        run_id = "test-run-456"
        self._seed_result(client, run_id)

        response = client.get(f"/api/v1/runs/{run_id}/results")
        data = response.json()

        assert data["run_id"] == run_id
        assert data["timeframe"] == "1m"
        assert data["final_equity"] == "105000.00"
        assert data["simulation_duration_ms"] == 1234
        assert data["total_bars_processed"] == 500
        assert isinstance(data["symbols"], list)

    def test_result_stats_contains_key_metrics(self, client: TestClient) -> None:
        """Response stats dict contains key performance metrics."""
        run_id = "test-run-789"
        self._seed_result(client, run_id)

        response = client.get(f"/api/v1/runs/{run_id}/results")
        stats = response.json()["stats"]

        assert "total_return" in stats
        assert "sharpe_ratio" in stats
        assert "max_drawdown" in stats
        assert "total_trades" in stats
        assert "win_rate" in stats

    def test_result_includes_equity_curve(self, client: TestClient) -> None:
        """Response includes equity_curve as a list."""
        run_id = "test-run-eq"
        self._seed_result(client, run_id)

        response = client.get(f"/api/v1/runs/{run_id}/results")
        eq = response.json()["equity_curve"]

        assert isinstance(eq, list)
        assert len(eq) == 2
        assert "timestamp" in eq[0]
        assert "equity" in eq[0]

    def test_result_includes_fills(self, client: TestClient) -> None:
        """Response includes fills as a list."""
        run_id = "test-run-fills"
        self._seed_result(client, run_id)

        response = client.get(f"/api/v1/runs/{run_id}/results")
        fills = response.json()["fills"]

        assert isinstance(fills, list)
        assert len(fills) == 1
        assert fills[0]["symbol"] == "BTC/USD"

"""
Tests for Runs Endpoint

MVP-2: Run Lifecycle
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
                "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
            },
        )

        assert response.status_code == 422

    def test_validates_symbols_not_empty(self, client: TestClient) -> None:
        """POST /runs with empty symbols returns 422."""
        response = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "test",
                "mode": "paper",
                "symbols": [],
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
                "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
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
                    "symbols": ["BTC/USD"],
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
                "symbols": ["BTC/USD"],
            },
        ).json()
        client.post(f"/api/v1/runs/{run_a['id']}/start")

        # Run B gets stopped
        run_b = client.post(
            "/api/v1/runs",
            json={
                "strategy_id": "s2",
                "mode": "paper",
                "symbols": ["ETH/USD"],
            },
        ).json()
        client.post(f"/api/v1/runs/{run_b['id']}/stop")

        response = client.get("/api/v1/runs?status=running")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "running"

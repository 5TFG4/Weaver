"""
E2E Tests: Paper Trading Flow

Verifies paper run lifecycle — create, start (RUNNING),
active status on dashboard, stop (STOPPED), and error handling.

Note: Without Alpaca credentials, VedaService is absent.
Paper runs start and clock ticks, but orders are silently dropped.
Tests focus on lifecycle state transitions only.
"""

from __future__ import annotations

import psycopg2
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2EApiClient

DB_URL = "postgresql://weaver:weaver_e2e_password@db_e2e:5432/weaver_e2e_db"


@pytest.fixture()
def _clean_runs():
    """Clean runs table after test."""
    yield
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fills")
            cur.execute("DELETE FROM veda_orders")
            cur.execute("DELETE FROM runs")
        conn.commit()
    finally:
        conn.close()


@pytest.mark.e2e
@pytest.mark.usefixtures("_clean_runs")
class TestPaperFlow:
    """Paper trading run lifecycle E2E tests."""

    def test_create_paper_run_visible_in_ui(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Paper run created via API appears in runs table with pending status."""
        run = api_client.create_run(
            strategy_id="sample", mode="paper", symbols=["BTC/USD"]
        )
        page.goto(f"{e2e_base_url}/runs")
        run_row = page.get_by_test_id(f"run-row-{run['id']}")
        expect(run_row).to_be_visible(timeout=10000)
        expect(run_row.get_by_text("pending")).to_be_visible()
        expect(run_row.get_by_text("paper")).to_be_visible()

    def test_start_paper_run_running_status(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Starting a paper run transitions to running status."""
        run = api_client.create_run(
            strategy_id="sample", mode="paper", symbols=["BTC/USD"]
        )
        page.goto(f"{e2e_base_url}/runs")
        # Start via API
        result = api_client.start_run(run["id"])
        assert result["status"] == "running"
        # Verify in UI — may need reload for SSE to deliver
        page.reload()
        run_row = page.get_by_test_id(f"run-row-{run['id']}")
        expect(run_row.get_by_text("running")).to_be_visible(timeout=10000)
        # Stop the run to clean up
        api_client.stop_run(run["id"])

    def test_dashboard_active_runs_counter(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Dashboard Active Runs counter shows running paper runs."""
        run = api_client.create_run(
            strategy_id="sample", mode="paper", symbols=["BTC/USD"]
        )
        api_client.start_run(run["id"])

        page.goto(f"{e2e_base_url}/dashboard")
        stat_card = page.locator("text=Active Runs").locator("..")
        expect(stat_card).to_contain_text("1", timeout=10000)
        # Stop the run to clean up
        api_client.stop_run(run["id"])

    def test_stop_paper_run_stopped_status(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Stopping a running paper run transitions to stopped status."""
        run = api_client.create_run(
            strategy_id="sample", mode="paper", symbols=["BTC/USD"]
        )
        api_client.start_run(run["id"])
        api_client.stop_run(run["id"])

        # Verify in UI
        page.goto(f"{e2e_base_url}/runs")
        run_row = page.get_by_test_id(f"run-row-{run['id']}")
        expect(run_row.get_by_text("stopped")).to_be_visible(timeout=10000)

        # Double-check via API
        api_run = api_client.get_run(run["id"])
        assert api_run["status"] == "stopped"
        assert api_run["stopped_at"] is not None

    def test_error_state_invalid_strategy(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Starting a run with invalid strategy shows error status."""
        run = api_client.create_run(
            strategy_id="nonexistent-xyz-strategy",
            mode="paper",
            symbols=["BTC/USD"],
        )
        try:
            api_client.start_run(run["id"])
        except Exception:
            pass  # May return error status or raise

        page.goto(f"{e2e_base_url}/runs")
        run_row = page.get_by_test_id(f"run-row-{run['id']}")
        expect(run_row.get_by_text("error")).to_be_visible(timeout=10000)

        # Verify via API
        api_run = api_client.get_run(run["id"])
        assert api_run["status"] == "error"

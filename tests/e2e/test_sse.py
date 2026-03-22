"""
E2E Tests: SSE (Server-Sent Events)

Verifies SSE connection status indicator and real-time UI updates
delivered via SSE without page reload.
"""

from __future__ import annotations

import psycopg2
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import DB_URL
from tests.e2e.helpers import E2EApiClient


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
class TestSSE:
    """SSE connection and real-time update tests."""

    def test_connection_status_shows_connected(
        self, page: Page, e2e_base_url: str
    ) -> None:
        """ConnectionStatus indicator shows 'Connected' after SSE handshake."""
        page.goto(f"{e2e_base_url}/dashboard")
        expect(page.get_by_text("Connected")).to_be_visible(timeout=10000)

    @pytest.mark.usefixtures("_clean_runs")
    def test_sse_delivers_run_completed(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """SSE delivers run.Completed → UI updates without reload."""
        run = api_client.create_run(
            strategy_id="sample",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:50:00Z",
        )

        # Navigate to runs page and wait for SSE connection
        page.goto(f"{e2e_base_url}/runs")
        expect(page.get_by_text("Connected")).to_be_visible(timeout=10000)

        # Verify run shows as pending
        run_row = page.get_by_test_id(f"run-row-{run['id']}")
        expect(run_row.get_by_text("pending")).to_be_visible()

        # Start via API — backtest completes synchronously, SSE delivers update
        api_client.start_run(run["id"])

        # Wait for SSE to deliver completed status — no reload
        expect(run_row.get_by_text("completed")).to_be_visible(timeout=15000)

    def test_sse_reconnects_after_interruption(
        self, page: Page, e2e_base_url: str
    ) -> None:
        """SSE reconnects after network interruption."""
        page.goto(f"{e2e_base_url}/dashboard")
        expect(page.get_by_text("Connected")).to_be_visible(timeout=10000)

        # Simulate network interruption — close SSE via JS
        page.evaluate("window.__sseSource && window.__sseSource.close()")
        # Also try generic EventSource close and set offline
        page.context.set_offline(True)
        page.wait_for_timeout(4000)  # Wait for reconnect delay (3s) + buffer

        # Restore network
        page.context.set_offline(False)
        # SSE should reconnect within RECONNECT_DELAY (3s) + buffer
        expect(page.get_by_text("Connected")).to_be_visible(timeout=15000)

    @pytest.mark.usefixtures("_clean_runs")
    def test_sse_delivers_run_stopped(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """SSE delivers run.Stopped → real-time UI update."""
        run = api_client.create_run(
            strategy_id="sample", mode="paper", symbols=["BTC/USD"]
        )
        api_client.start_run(run["id"])

        # Navigate to runs page
        page.goto(f"{e2e_base_url}/runs")
        expect(page.get_by_text("Connected")).to_be_visible(timeout=10000)
        run_row = page.get_by_test_id(f"run-row-{run['id']}")
        expect(run_row.get_by_text("running")).to_be_visible(timeout=10000)

        # Stop via API — SSE delivers stopped status
        api_client.stop_run(run["id"])

        # Wait for SSE to deliver stopped status — no reload
        expect(run_row.get_by_text("stopped")).to_be_visible(timeout=15000)

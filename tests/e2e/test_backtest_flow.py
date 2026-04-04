"""
E2E Tests: Backtest Flow

Verifies backtest run lifecycle — create, start, status transitions,
and visibility across pages.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import E2EApiClient

# 20 bars of BTC/USD 1m data: bars 1-10 are lookback, bars 11-20 are trade window.
# Mean-reversion strategy (sample) uses 10-bar lookback, 1% threshold.
# Bar 11: close drops >1% below avg → BUY signal
# Bar 13: close rises >1% above avg → SELL signal
SEED_BARS = []
_base_ts = datetime(2024, 1, 15, 9, 30, tzinfo=UTC)
# Bars 1-10: stable around 100.00 (establishes moving average)
for i in range(10):
    ts = datetime(2024, 1, 15, 9, 30 + i, tzinfo=UTC)
    SEED_BARS.append(("BTC/USD", "1m", ts, 100.0, 100.5, 99.5, 100.0, 1000.0))
# Bar 11: price drops to 98.5 (>1% below 100 avg) → triggers BUY
SEED_BARS.append(
    ("BTC/USD", "1m", datetime(2024, 1, 15, 9, 40, tzinfo=UTC), 100.0, 100.0, 98.0, 98.5, 1500.0)
)
# Bar 12: price recovers slightly
SEED_BARS.append(
    ("BTC/USD", "1m", datetime(2024, 1, 15, 9, 41, tzinfo=UTC), 98.5, 99.5, 98.0, 99.5, 1200.0)
)
# Bar 13: price rises to 101.5 (>1% above avg) → triggers SELL
SEED_BARS.append(
    ("BTC/USD", "1m", datetime(2024, 1, 15, 9, 42, tzinfo=UTC), 99.5, 102.0, 99.5, 101.5, 1800.0)
)
# Bars 14-20: stable again
for i in range(7):
    ts = datetime(2024, 1, 15, 9, 43 + i, tzinfo=UTC)
    SEED_BARS.append(("BTC/USD", "1m", ts, 101.0, 101.5, 100.5, 101.0, 1000.0))


@pytest.mark.e2e
@pytest.mark.usefixtures("_clean_runs")
class TestBacktestFlow:
    """Backtest run lifecycle E2E tests."""

    def test_create_backtest_via_ui(self, page: Page, e2e_base_url: str) -> None:
        """Create a backtest run through the UI form → shows pending status."""
        page.goto(f"{e2e_base_url}/runs")
        page.get_by_role("button", name="New Run").click()

        # Strategy is now a <select> dropdown populated from /api/v1/strategies
        page.locator("#strategy-id").select_option("sample")
        page.locator("#run-mode").select_option("backtest")

        # Wait for RJSF config form to render after strategy selection
        page.locator("form.rjsf").wait_for(timeout=5000)

        # RJSF array field: click Add to insert the first symbols entry
        page.get_by_test_id("rjsf-add-item").click()
        page.locator("#root_symbols_0").select_option("BTC/USD")

        # Timeframe enum rendered as <select> by RJSF
        page.locator("#root_timeframe").select_option(label="1m")

        page.get_by_role("button", name="Create").click()
        # After creation, run should appear with pending status
        expect(page.get_by_text("pending").first).to_be_visible(timeout=10000)

    def test_create_run_via_api_visible_in_ui(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Run created via API appears in the runs table."""
        run = api_client.create_run(
            strategy_id="sample",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:50:00Z",
        )
        run_id_short = run["id"][:8]

        page.goto(f"{e2e_base_url}/runs")
        expect(page.get_by_text(run_id_short)).to_be_visible(timeout=10000)

    def test_start_backtest_completes(
        self,
        page: Page,
        e2e_base_url: str,
        api_client: E2EApiClient,
        seed_bars: None,
    ) -> None:
        """Starting a backtest transitions to completed status."""
        run = api_client.create_run(
            strategy_id="sample",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:50:00Z",
        )
        # Start via API — backtest runs synchronously and completes
        result = api_client.start_run(run["id"])
        assert result["status"] in ("completed", "running")

        # Verify in UI
        page.goto(f"{e2e_base_url}/runs")
        run_row = page.get_by_test_id(f"run-row-{run['id']}")
        expect(run_row.get_by_text("completed")).to_be_visible(timeout=15000)

    def test_backtest_run_detail_deeplink(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Deep-link to /runs/{run_id} shows run details."""
        run = api_client.create_run(
            strategy_id="sample",
            mode="backtest",
            symbols=["BTC/USD"],
        )
        page.goto(f"{e2e_base_url}/runs/{run['id']}")
        expect(page.get_by_text(run["id"][:8])).to_be_visible(timeout=10000)
        expect(page.get_by_text("backtest")).to_be_visible()
        expect(page.get_by_text("sample")).to_be_visible()

    def test_dashboard_total_runs_increments(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Dashboard 'Total Runs' stat card reflects created runs."""
        page.goto(f"{e2e_base_url}/dashboard")
        expect(page.get_by_text("Total Runs")).to_be_visible(timeout=10000)

        # Get current count
        runs_before = api_client.list_runs()
        count_before = runs_before["total"]

        api_client.create_run(strategy_id="sample", mode="backtest", symbols=["BTC/USD"])
        page.reload()
        # The stat card should show count + 1
        stat_card = page.locator("text=Total Runs").locator("..")
        expect(stat_card).to_contain_text(str(count_before + 1), timeout=10000)

    def test_multiple_runs_listed(
        self, page: Page, e2e_base_url: str, api_client: E2EApiClient
    ) -> None:
        """Multiple runs appear in the runs table."""
        # Record count before
        before = api_client.list_runs()["total"]
        for _ in range(3):
            api_client.create_run(strategy_id="sample", mode="backtest", symbols=["BTC/USD"])
        page.goto(f"{e2e_base_url}/runs")
        # Should have at least before+3 table rows
        rows = page.locator("table tbody tr")
        rows.nth(before + 2).wait_for(timeout=10000)


@pytest.mark.e2e
@pytest.mark.usefixtures("_clean_runs")
class TestFormValidation:
    """Form validation E2E tests for the Create Run form."""

    def test_create_form_rejects_empty_strategy(self, page: Page, e2e_base_url: str) -> None:
        """Submitting with an empty strategy field is blocked by browser validation."""
        page.goto(f"{e2e_base_url}/runs")
        page.get_by_role("button", name="New Run").click()

        form = page.get_by_test_id("create-run-form")
        expect(form).to_be_visible(timeout=5000)

        # Leave strategy unselected (default "Select strategy..."), click Create
        page.get_by_role("button", name="Create").click()

        # Browser blocks submission — form stays visible, button does NOT become "Creating..."
        expect(form).to_be_visible()
        expect(page.get_by_role("button", name="Create")).to_be_visible()

        # Strategy select should be in invalid state (required but value="")
        is_invalid = page.locator("#strategy-id").evaluate("el => !el.validity.valid")
        assert is_invalid, "Expected strategy-id to be invalid when empty"

    def test_create_form_renders_config_fields(self, page: Page, e2e_base_url: str) -> None:
        """Selecting a strategy renders RJSF config fields from its config_schema."""
        page.goto(f"{e2e_base_url}/runs")
        page.get_by_role("button", name="New Run").click()

        form = page.get_by_test_id("create-run-form")
        expect(form).to_be_visible(timeout=5000)

        # Select a strategy — RJSF config form should appear
        page.locator("#strategy-id").select_option("sample")

        # Wait for RJSF to render
        rjsf_form = page.locator("form.rjsf")
        expect(rjsf_form).to_be_visible(timeout=5000)

        # The sample strategy config_schema has symbols (array) and timeframe (enum)
        expect(page.get_by_test_id("rjsf-add-item")).to_be_visible()
        expect(page.locator("#root_timeframe")).to_be_visible()

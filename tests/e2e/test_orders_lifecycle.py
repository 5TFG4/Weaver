"""
E2E Tests: Orders Lifecycle

Tests order data integrity across the system.

Architecture note: In backtest mode, Greta processes orders in-memory
and emits events to the EventLog (outbox table). Orders are NOT persisted
to the veda_orders table. The /orders API falls back to MockOrderService
when VedaService is absent (no Alpaca credentials in E2E).

Therefore these tests verify:
1. Backtest order events are correctly recorded in the outbox
2. The orders API returns well-structured data
3. The orders page renders correctly
"""

from __future__ import annotations

import psycopg2
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import DB_URL
from tests.e2e.helpers import E2EApiClient

# Reuse the same seed bar data from test_backtest_flow.py
from tests.e2e.test_backtest_flow import SEED_BARS


@pytest.fixture()
def seed_bars():
    """Seed bar data for backtest execution."""
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bars WHERE symbol = 'BTC/USD' AND timeframe = '1m'")
            for bar in SEED_BARS:
                cur.execute(
                    "INSERT INTO bars (symbol, timeframe, timestamp, open, high, low, close, volume) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    bar,
                )
        conn.commit()
    finally:
        conn.close()
    yield
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bars WHERE symbol = 'BTC/USD' AND timeframe = '1m'")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def _clean_runs():
    """Clean runs and events after test."""
    yield
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fills")
            cur.execute("DELETE FROM veda_orders")
            cur.execute("DELETE FROM outbox WHERE payload->>'producer' = 'greta.service'")
            cur.execute("DELETE FROM runs")
        conn.commit()
    finally:
        conn.close()


def _get_order_events(run_id: str) -> list[dict]:
    """Query outbox for order events from a specific run."""
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT type, payload FROM outbox "
                "WHERE type LIKE 'orders.%%' AND payload->>'run_id' = %s "
                "ORDER BY id",
                (run_id,),
            )
            return [{"type": row[0], "payload": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()


@pytest.mark.e2e
@pytest.mark.usefixtures("_clean_runs")
class TestBacktestOrderEvents:
    """Verify backtest produces correct order events in the event log.

    NOTE: These tests are currently xfail due to an async race condition
    in the backtest execution path.  GretaService, StrategyRunner, and
    DomainRouter each use ``spawn_tracked_task`` (fire-and-forget), creating
    a 3-hop async chain:
        FetchWindow → data.WindowReady → PlaceRequest → PlaceOrder → place_order()
    BacktestClock only yields once (``asyncio.sleep(0)``) between ticks, which
    is insufficient for the 3 chained tasks to complete. Additionally,
    ``_cleanup_run_context()`` runs immediately after the clock exits and
    unsubscribes Greta before in-flight tasks finish.

    When the race condition is fixed these tests should turn green and the
    xfail markers can be removed.
    """

    @pytest.mark.xfail(
        reason="backtest async race: 3 spawn_tracked_task hops vs 1 sleep(0)", strict=True
    )
    def test_backtest_generates_order_events(
        self, api_client: E2EApiClient, seed_bars: None
    ) -> None:
        """Completed backtest should produce Placed and Filled events in the outbox."""
        run = api_client.create_run(
            strategy_id="sample",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:50:00Z",
        )
        result = api_client.start_run(run["id"])
        assert result["status"] == "completed"

        events = _get_order_events(run["id"])
        event_types = [e["type"] for e in events]

        # Strategy should produce at least one Placed and one Filled event
        assert "orders.Placed" in event_types, (
            f"No orders.Placed event found. Events: {event_types}"
        )
        assert "orders.Filled" in event_types, (
            f"No orders.Filled event found. Events: {event_types}"
        )

    @pytest.mark.xfail(
        reason="backtest async race: 3 spawn_tracked_task hops vs 1 sleep(0)", strict=True
    )
    def test_order_event_payloads_have_required_fields(
        self, api_client: E2EApiClient, seed_bars: None
    ) -> None:
        """Order event payloads should contain correct structure."""
        run = api_client.create_run(
            strategy_id="sample",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:50:00Z",
        )
        api_client.start_run(run["id"])

        events = _get_order_events(run["id"])

        # Verify Placed event payload
        placed = [e for e in events if e["type"] == "orders.Placed"]
        assert len(placed) > 0
        placed_payload = placed[0]["payload"]["payload"]
        assert "order_id" in placed_payload
        assert "symbol" in placed_payload
        assert "side" in placed_payload
        assert placed_payload["side"] in ("buy", "sell")
        assert "qty" in placed_payload

        # Verify Filled event payload
        filled = [e for e in events if e["type"] == "orders.Filled"]
        assert len(filled) > 0
        filled_payload = filled[0]["payload"]["payload"]
        assert "order_id" in filled_payload
        assert "fill_price" in filled_payload
        assert float(filled_payload["fill_price"]) > 0

    @pytest.mark.xfail(
        reason="backtest async race: 3 spawn_tracked_task hops vs 1 sleep(0)", strict=True
    )
    def test_backtest_strategy_signals_match_seed_data(
        self, api_client: E2EApiClient, seed_bars: None
    ) -> None:
        """
        Sample strategy (mean-reversion) should produce:
        - BUY when bar 11 drops >1% below moving average
        - SELL when bar 13 rises >1% above moving average
        """
        run = api_client.create_run(
            strategy_id="sample",
            mode="backtest",
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time="2024-01-15T09:30:00Z",
            end_time="2024-01-15T09:50:00Z",
        )
        api_client.start_run(run["id"])

        events = _get_order_events(run["id"])
        placed = [e for e in events if e["type"] == "orders.Placed"]

        # Should have at least a BUY signal
        sides = [e["payload"]["payload"]["side"] for e in placed]
        assert "buy" in sides, f"Expected BUY signal from bar 11 drop. Got: {sides}"


@pytest.mark.e2e
class TestOrdersApi:
    """Verify orders API returns well-structured data."""

    def test_list_orders_returns_paginated_response(self, api_client: E2EApiClient) -> None:
        """GET /orders should return paginated response with expected fields."""
        data = api_client.list_orders()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)

    def test_list_orders_items_have_required_fields(self, api_client: E2EApiClient) -> None:
        """Each order item should have all required fields."""
        data = api_client.list_orders()

        if data["total"] > 0:
            order = data["items"][0]
            required_fields = ["id", "symbol", "side", "order_type", "qty", "status"]
            for field in required_fields:
                assert field in order, f"Missing field: {field}"

    def test_get_order_by_id(self, api_client: E2EApiClient) -> None:
        """GET /orders/:id should return a single order."""
        data = api_client.list_orders()
        if data["total"] > 0:
            order_id = data["items"][0]["id"]
            order = api_client.get_order(order_id)
            assert order["id"] == order_id


@pytest.mark.e2e
class TestOrdersPage:
    """Verify orders page rendering with Playwright."""

    def test_orders_table_columns(self, page: Page, e2e_base_url: str) -> None:
        """Orders table should have the expected column headers."""
        page.goto(f"{e2e_base_url}/orders")

        # Wait for table to load
        page.locator("table").wait_for(timeout=10000)

        # Verify key column headers exist
        headers = page.locator("table thead th")
        header_texts = [h.text_content().strip().lower() for h in headers.all()]

        assert any("symbol" in h for h in header_texts), (
            f"No 'symbol' column. Headers: {header_texts}"
        )
        assert any("side" in h for h in header_texts), f"No 'side' column. Headers: {header_texts}"
        assert any("status" in h for h in header_texts), (
            f"No 'status' column. Headers: {header_texts}"
        )

    def test_order_detail_modal_shows_all_fields(self, page: Page, e2e_base_url: str) -> None:
        """Clicking an order row opens modal with full order details."""
        page.goto(f"{e2e_base_url}/orders")

        first_row = page.locator("table tbody tr").first
        first_row.wait_for(timeout=10000)
        first_row.click()

        modal = page.get_by_test_id("order-detail-modal")
        expect(modal).to_be_visible(timeout=5000)

        # Verify modal contains key order fields
        modal_text = modal.text_content()
        assert "BTC/USD" in modal_text or "ETH/USD" in modal_text

"""
E2E Tests: Orders Page

Verifies the orders page renders mock order data correctly
and that order detail modal works.

Note: Without VedaService, GET /orders returns MockOrderService data
(2 hardcoded orders). These tests verify the rendering pipeline,
not real order generation.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestOrders:
    """Orders page rendering tests."""

    def test_orders_page_renders_mock_data(self, page: Page, e2e_base_url: str) -> None:
        """Orders page shows the 2 mock orders with correct data."""
        page.goto(f"{e2e_base_url}/orders")

        # Wait for table to load
        rows = page.locator("table tbody tr")
        rows.first.wait_for(timeout=10000)

        # Should have 2 mock order rows
        expect(rows).to_have_count(2)

        # First order: BTC/USD, buy, filled — scope to table body
        table = page.locator("table tbody")
        expect(table.get_by_text("BTC/USD")).to_be_visible()
        expect(table.get_by_text("buy").first).to_be_visible()
        expect(table.get_by_text("filled")).to_be_visible()

        # Second order: ETH/USD, sell, submitted
        expect(table.get_by_text("ETH/USD")).to_be_visible()
        expect(table.get_by_text("sell").first).to_be_visible()
        expect(table.get_by_text("submitted")).to_be_visible()

    def test_order_detail_modal(self, page: Page, e2e_base_url: str) -> None:
        """Clicking an order row opens detail modal."""
        page.goto(f"{e2e_base_url}/orders")

        # Wait for table to load and click first row
        first_row = page.locator("table tbody tr").first
        first_row.wait_for(timeout=10000)
        first_row.click()

        # Modal should appear with order details
        modal = page.get_by_test_id("order-detail-modal")
        expect(modal).to_be_visible(timeout=5000)
        expect(modal.get_by_text("BTC/USD")).to_be_visible()
        expect(modal.get_by_text("buy").first).to_be_visible()

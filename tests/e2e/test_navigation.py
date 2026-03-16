"""
E2E Tests: Navigation & Health

Verifies all pages load correctly, navigation links work,
and system health is displayed.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestNavigation:
    """Page loading and navigation tests."""

    def test_root_redirects_to_dashboard(self, page: Page, e2e_base_url: str) -> None:
        """Navigating to / redirects to /dashboard."""
        page.goto(e2e_base_url)
        expect(page).to_have_url(f"{e2e_base_url}/dashboard")

    def test_dashboard_page_loads(self, page: Page, e2e_base_url: str) -> None:
        """Dashboard page renders with stat cards."""
        page.goto(f"{e2e_base_url}/dashboard")
        expect(page.get_by_text("Active Runs")).to_be_visible()
        expect(page.get_by_text("Total Runs")).to_be_visible()
        expect(page.get_by_text("Total Orders")).to_be_visible()

    def test_runs_page_loads(self, page: Page, e2e_base_url: str) -> None:
        """Runs page renders with heading."""
        page.goto(f"{e2e_base_url}/runs")
        expect(page).to_have_url(f"{e2e_base_url}/runs")
        expect(page.locator("h1")).to_contain_text("Runs")

    def test_orders_page_loads(self, page: Page, e2e_base_url: str) -> None:
        """Orders page renders."""
        page.goto(f"{e2e_base_url}/orders")
        expect(page).to_have_url(f"{e2e_base_url}/orders")
        expect(page.locator("h1")).to_contain_text("Orders")

    def test_404_page_for_unknown_route(self, page: Page, e2e_base_url: str) -> None:
        """Unknown route shows 404 / NotFound page."""
        page.goto(f"{e2e_base_url}/nonexistent-page")
        expect(page.get_by_text("404")).to_be_visible()

    def test_sidebar_navigation(self, page: Page, e2e_base_url: str) -> None:
        """Sidebar links navigate between pages."""
        page.goto(f"{e2e_base_url}/dashboard")
        page.get_by_role("link", name="Runs", exact=True).click()
        expect(page).to_have_url(f"{e2e_base_url}/runs")
        page.get_by_role("link", name="Orders", exact=True).click()
        expect(page).to_have_url(f"{e2e_base_url}/orders")
        page.get_by_role("link", name="Dashboard", exact=True).click()
        expect(page).to_have_url(f"{e2e_base_url}/dashboard")

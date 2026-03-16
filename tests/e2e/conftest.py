"""
E2E Test Configuration

Fixtures for Playwright-based end-to-end tests running inside
the test_runner container against the E2E Docker stack.
"""

from __future__ import annotations

import os
import time

import psycopg2
import pytest
import requests

from tests.e2e.helpers import E2EApiClient

BASE_URL = os.environ.get("BASE_URL", "http://frontend_e2e:80")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://backend_e2e:8000/api/v1")
DB_URL = os.environ.get("DB_URL", "postgresql://weaver:weaver_e2e_password@db_e2e:5432/weaver_e2e_db")


@pytest.fixture(scope="session", autouse=True)
def e2e_stack_ready() -> None:
    """Wait for SUT services to be healthy before running tests."""
    healthz = f"{API_BASE_URL}/healthz"
    deadline = time.time() + 30
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            r = requests.get(healthz, timeout=3)
            if r.status_code == 200:
                return
        except Exception as exc:
            last_err = exc
        time.sleep(1)
    raise RuntimeError(
        f"Backend not healthy at {healthz} after 30s. Last error: {last_err}"
    )


@pytest.fixture()
def e2e_base_url() -> str:
    """Base URL for the frontend SUT (port 80 stripped since browsers normalize it)."""
    url = BASE_URL
    # Browsers normalize :80 out of HTTP URLs
    url = url.replace(":80", "")
    return url.rstrip("/")


@pytest.fixture()
def api_client() -> E2EApiClient:
    """E2E API client for test setup/verification."""
    return E2EApiClient(API_BASE_URL)


@pytest.fixture()
def clean_e2e_db():
    """Clean test data between tests via direct DB access."""
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

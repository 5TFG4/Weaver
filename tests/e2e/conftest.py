"""
E2E Test Configuration

Fixtures for Playwright-based end-to-end tests.
The E2E Docker stack is started automatically if not already running.
Uses host.docker.internal to reach the stack (no docker network connect needed).
"""

from __future__ import annotations

import os
import subprocess
import time

import psycopg2
import pytest
import requests

from tests.e2e.helpers import E2EApiClient

# Override the global 30s timeout for all e2e tests (Playwright needs more time)
pytestmark = pytest.mark.timeout(120)

# Defaults use host.docker.internal (dev container → host → mapped e2e ports).
# The test_runner container in docker-compose.e2e.yml overrides these via env vars
# to use Docker-internal service names.
BASE_URL = os.environ.get("E2E_BASE_URL", "http://host.docker.internal:33579")
API_BASE_URL = os.environ.get("E2E_API_BASE_URL", "http://host.docker.internal:38919/api/v1")
DB_URL = os.environ.get(
    "E2E_DB_URL",
    "postgresql://weaver:weaver_e2e_password@host.docker.internal:35432/weaver_e2e_db",
)

_COMPOSE_CMD = ["docker", "compose", "-f", "docker/docker-compose.e2e.yml"]


def _stack_healthy() -> bool:
    """Quick probe: is the E2E backend responding?"""
    try:
        r = requests.get(f"{API_BASE_URL}/healthz", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _start_stack() -> None:
    """Start the E2E Docker stack (build + wait for healthy)."""
    subprocess.run(
        [*_COMPOSE_CMD, "up", "-d", "--wait", "--build", "db_e2e", "backend_e2e", "frontend_e2e"],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.fixture(scope="session", autouse=True)
def e2e_stack_ready() -> None:
    """Ensure E2E stack is running. Start it automatically if needed."""
    if _stack_healthy():
        return

    # Stack not running — start it
    _start_stack()

    # Wait for health (up to 120s for build + boot)
    deadline = time.time() + 120
    while time.time() < deadline:
        if _stack_healthy():
            return
        time.sleep(2)

    pytest.fail("E2E stack failed to become healthy within 120s.")


def _clean_db(*, restart_backend: bool = False) -> None:
    """Delete all test data from the e2e database.

    Args:
        restart_backend: If True, restart backend_e2e so its in-memory
            RunManager reloads from the (now empty) database.
    """
    if "e2e" not in DB_URL:
        raise RuntimeError(f"Refusing to clean non-e2e database: {DB_URL}")
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

    if restart_backend:
        subprocess.run([*_COMPOSE_CMD, "restart", "backend_e2e"], capture_output=True)
        deadline = time.time() + 30
        while time.time() < deadline:
            if _stack_healthy():
                return
            time.sleep(1)


@pytest.fixture(scope="session", autouse=True)
def _clean_db_on_start(e2e_stack_ready: None) -> None:
    """Wipe stale data and restart backend so in-memory state is fresh."""
    _clean_db(restart_backend=True)


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
    """Clean test data before and after each test."""
    _clean_db()
    yield
    _clean_db()


@pytest.fixture()
def _clean_runs():
    """Clean test data before and after each test (alias for usefixtures)."""
    _clean_db()
    yield
    _clean_db()


@pytest.fixture()
def seed_bars():
    """Seed bar data for backtest execution.

    Inserts SEED_BARS (defined in test_backtest_flow.py) into the bars table,
    yields, then cleans up. Shared by test_backtest_flow and test_orders_lifecycle.
    """
    from tests.e2e.test_backtest_flow import SEED_BARS

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

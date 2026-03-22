"""
E2E Test Helpers

API client and utilities for E2E tests running inside the test_runner container.
"""

from __future__ import annotations

import os
from typing import Any

import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://backend_e2e:8000/api/v1")


class E2EApiClient:
    """Synchronous API client for E2E test setup/verification."""

    def __init__(self, base_url: str = API_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def healthz(self) -> dict[str, Any]:
        r = self.session.get(f"{self.base_url}/healthz", timeout=5)
        r.raise_for_status()
        return r.json()

    def create_run(self, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "strategy_id": kwargs.get("strategy_id", "sample"),
            "mode": kwargs.get("mode", "backtest"),
            "symbols": kwargs.get("symbols", ["BTC/USD"]),
            "timeframe": kwargs.get("timeframe", "1m"),
        }
        if "start_time" in kwargs:
            payload["start_time"] = kwargs["start_time"]
        if "end_time" in kwargs:
            payload["end_time"] = kwargs["end_time"]
        if "config" in kwargs:
            payload["config"] = kwargs["config"]
        r = self.session.post(
            f"{self.base_url}/runs", json=payload, timeout=10
        )
        r.raise_for_status()
        return r.json()

    def get_run(self, run_id: str) -> dict[str, Any]:
        r = self.session.get(f"{self.base_url}/runs/{run_id}", timeout=5)
        r.raise_for_status()
        return r.json()

    def list_runs(self, **params: Any) -> dict[str, Any]:
        r = self.session.get(
            f"{self.base_url}/runs", params=params, timeout=5
        )
        r.raise_for_status()
        return r.json()

    def start_run(self, run_id: str) -> dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/runs/{run_id}/start", timeout=30
        )
        r.raise_for_status()
        return r.json()

    def stop_run(self, run_id: str) -> dict[str, Any]:
        r = self.session.post(
            f"{self.base_url}/runs/{run_id}/stop", timeout=10
        )
        r.raise_for_status()
        return r.json()

    def list_orders(self, **params: Any) -> dict[str, Any]:
        r = self.session.get(
            f"{self.base_url}/orders", params=params, timeout=5
        )
        r.raise_for_status()
        return r.json()

    def get_order(self, order_id: str) -> dict[str, Any]:
        r = self.session.get(f"{self.base_url}/orders/{order_id}", timeout=5)
        r.raise_for_status()
        return r.json()

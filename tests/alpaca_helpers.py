"""Shared Alpaca credential helpers used by both unit and integration tests."""

from __future__ import annotations

import os

_PLACEHOLDER_VALUES = {"your_paper_api_key", "your_paper_api_secret", ""}


def has_real_alpaca_creds() -> bool:
    """Check if real (non-placeholder) Alpaca credentials are available."""
    key = os.environ.get("ALPACA_PAPER_API_KEY", "")
    secret = os.environ.get("ALPACA_PAPER_API_SECRET", "")
    return key not in _PLACEHOLDER_VALUES and secret not in _PLACEHOLDER_VALUES

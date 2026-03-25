"""
Tests for Alpaca credential placeholder detection (M11-5 B-10).

Verifies that has_real_alpaca_creds correctly filters out
placeholder values from example.env so integration tests
don't run with bogus credentials.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from tests.alpaca_helpers import has_real_alpaca_creds


class TestHasRealAlpacaCreds:
    """Tests for has_real_alpaca_creds helper."""

    def test_returns_false_when_env_vars_missing(self) -> None:
        """No env vars set → False."""
        with patch.dict(os.environ, {}, clear=True):
            assert has_real_alpaca_creds() is False

    def test_returns_false_with_placeholder_key(self) -> None:
        """Placeholder from example.env → False."""
        with patch.dict(
            os.environ,
            {
                "ALPACA_PAPER_API_KEY": "your_paper_api_key",
                "ALPACA_PAPER_API_SECRET": "your_paper_api_secret",
            },
            clear=True,
        ):
            assert has_real_alpaca_creds() is False

    def test_returns_false_with_empty_strings(self) -> None:
        """Empty string env vars → False."""
        with patch.dict(
            os.environ,
            {
                "ALPACA_PAPER_API_KEY": "",
                "ALPACA_PAPER_API_SECRET": "",
            },
            clear=True,
        ):
            assert has_real_alpaca_creds() is False

    def test_returns_false_when_only_key_is_real(self) -> None:
        """Only key is real, secret is placeholder → False."""
        with patch.dict(
            os.environ,
            {
                "ALPACA_PAPER_API_KEY": "PK1234567890ABCDEF",
                "ALPACA_PAPER_API_SECRET": "your_paper_api_secret",
            },
            clear=True,
        ):
            assert has_real_alpaca_creds() is False

    def test_returns_true_with_real_credentials(self) -> None:
        """Real-looking credentials → True."""
        with patch.dict(
            os.environ,
            {
                "ALPACA_PAPER_API_KEY": "PK1234567890ABCDEF",
                "ALPACA_PAPER_API_SECRET": "abc123def456ghi789jkl012mno345pqr678stu901",
            },
            clear=True,
        ):
            assert has_real_alpaca_creds() is True

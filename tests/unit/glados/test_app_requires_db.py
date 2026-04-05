"""Tests for app.py DB_URL requirement (S8: Production Safety)."""

from __future__ import annotations

import pytest

from src.glados.app import create_app, lifespan


class TestAppRequiresDb:
    """App must require DB_URL to start."""

    async def test_app_raises_without_db_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """App must refuse to start when DB_URL is not set."""
        monkeypatch.delenv("DB_URL", raising=False)
        from src.config import get_test_config

        app = create_app(settings=get_test_config())
        with pytest.raises(RuntimeError, match="DB_URL"):
            async with lifespan(app):
                pass

"""
Tests for GLaDOS Schemas

MVP-1: Bootable Skeleton
TDD: Write tests first, then implement.
"""

from __future__ import annotations


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_has_status_field(self) -> None:
        """HealthResponse should have status field."""
        from src.glados.schemas import HealthResponse

        response = HealthResponse(status="ok", version="0.1.0")

        assert response.status == "ok"

    def test_has_version_field(self) -> None:
        """HealthResponse should have version field."""
        from src.glados.schemas import HealthResponse

        response = HealthResponse(status="ok", version="0.1.0")

        assert response.version == "0.1.0"

    def test_serializes_to_dict(self) -> None:
        """HealthResponse should serialize to dict."""
        from src.glados.schemas import HealthResponse

        response = HealthResponse(status="ok", version="0.1.0")
        data = response.model_dump()

        assert data == {"status": "ok", "version": "0.1.0"}

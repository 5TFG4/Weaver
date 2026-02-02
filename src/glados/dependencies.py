"""
GLaDOS Dependency Injection

Provides FastAPI dependency functions for accessing shared resources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from src.config import WeaverConfig


def get_settings(request: Request) -> WeaverConfig:
    """Get application settings from app state."""
    return request.app.state.settings

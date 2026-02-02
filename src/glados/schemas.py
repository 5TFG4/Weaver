"""
GLaDOS API Schemas

Pydantic models for API request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class RunMode(str, Enum):
    """Trading run mode."""

    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"


class RunStatus(str, Enum):
    """Run lifecycle status."""

    PENDING = "pending"  # Created, not started
    RUNNING = "running"  # Actively trading
    STOPPED = "stopped"  # Manually stopped
    COMPLETED = "completed"  # Finished (backtest end or strategy exit)
    ERROR = "error"  # Failed with error


# =============================================================================
# Health
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


# =============================================================================
# Run Schemas
# =============================================================================


class RunCreate(BaseModel):
    """Request body for creating a run."""

    strategy_id: str = Field(..., min_length=1)
    mode: RunMode
    symbols: list[str] = Field(..., min_length=1)
    timeframe: str = Field(default="1m")
    # Backtest-specific (required when mode=backtest)
    start_time: datetime | None = None
    end_time: datetime | None = None
    # Optional strategy config
    config: dict[str, Any] | None = None


class RunResponse(BaseModel):
    """Full run details response."""

    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    symbols: list[str]
    timeframe: str
    config: dict[str, Any] | None = None
    # Timestamps
    created_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    items: list[RunResponse]
    total: int
    page: int = 1
    page_size: int = 20


"""
GLaDOS - Control Plane & API

The central orchestrator for Weaver, responsible for:
- Sole northbound API (REST + SSE)
- Run lifecycle management
- Domain routing (strategy.* → live|backtest.*)
- Self-clock management (bar-aligned ticking)
- Dependency wiring
- Publishing thin events to the frontend
"""

from .app import create_app

__all__ = ["create_app"]

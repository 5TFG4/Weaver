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

# Note: GLaDOS class import deferred to avoid circular imports
# Use: from src.glados.glados import GLaDOS

__all__ = ["GLaDOS"]


def __getattr__(name: str):
    """Lazy import GLaDOS to avoid circular imports."""
    if name == "GLaDOS":
        from .glados import GLaDOS
        return GLaDOS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

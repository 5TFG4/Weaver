"""
GLaDOS Domain Exceptions

Custom exceptions for domain-specific errors.
"""

from __future__ import annotations


class RunNotFoundError(Exception):
    """Raised when a run is not found."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Run not found: {run_id}")


class RunNotStartableError(Exception):
    """Raised when a run cannot be started."""

    def __init__(self, run_id: str, current_status: str) -> None:
        self.run_id = run_id
        self.current_status = current_status
        super().__init__(
            f"Run {run_id} cannot be started: current status is {current_status}"
        )


class RunNotStoppableError(Exception):
    """Raised when a run cannot be stopped."""

    def __init__(self, run_id: str, current_status: str) -> None:
        self.run_id = run_id
        self.current_status = current_status
        super().__init__(
            f"Run {run_id} cannot be stopped: current status is {current_status}"
        )

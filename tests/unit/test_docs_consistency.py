"""Documentation consistency guards for M8 closeout.

These tests lock key execution-layer docs to the current runtime contract
and prevent known stale markers from reappearing.
"""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (_repo_root() / relative_path).read_text(encoding="utf-8")


def test_readme_runtime_contract_is_current() -> None:
    readme = _read("README.md")

    assert "GET /api/v1/healthz" in readme
    assert "GET /api/v1/events/stream" in readme

    assert "GET /healthz" not in readme
    assert "/events/tail" not in readme
    assert "http://localhost:3000" not in readme

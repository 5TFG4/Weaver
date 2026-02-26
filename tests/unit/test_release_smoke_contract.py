"""Release smoke contract tests for M8-R0 deployment blockers.

These tests enforce deployment-critical contracts in production compose and
backend Dockerfile wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.container


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_prod_compose_backend_uses_canonical_asgi_target() -> None:
    """Production compose backend command must target canonical ASGI module."""
    compose_path = _repo_root() / "docker" / "docker-compose.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert "weaver:app" in content
    assert "main:app" not in content


def test_backend_dockerfile_installs_same_requirements_file_it_copies() -> None:
    """Backend Dockerfile must copy and install requirements from matching path."""
    dockerfile_path = _repo_root() / "docker" / "backend" / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "COPY docker/backend/requirements.txt /weaver/docker/backend/requirements.txt" in content
    assert "pip install --no-cache-dir -r /weaver/docker/backend/requirements.txt" in content

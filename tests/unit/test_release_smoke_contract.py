"""Release smoke contract tests for M8-R0 deployment blockers.

These tests enforce deployment-critical contracts in production compose and
backend Dockerfile wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


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


def test_backend_dockerfile_has_production_cmd() -> None:
    """Backend Dockerfile must have a proper production CMD (not tail -f)."""
    dockerfile_path = _repo_root() / "docker" / "backend" / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "tail" not in content, "Dockerfile CMD should not be 'tail -f /dev/null'"
    assert "uvicorn" in content, "Dockerfile CMD should use uvicorn for production"
    assert "weaver:app" in content, "Dockerfile CMD should target weaver:app"


def test_backend_dockerfile_exposes_port() -> None:
    """Backend Dockerfile must EXPOSE the correct port."""
    dockerfile_path = _repo_root() / "docker" / "backend" / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "EXPOSE 8000" in content


def test_uvicorn_in_production_requirements() -> None:
    """Production requirements must include uvicorn for ASGI serving."""
    requirements_path = _repo_root() / "docker" / "backend" / "requirements.txt"
    content = requirements_path.read_text(encoding="utf-8")

    assert "uvicorn" in content, "uvicorn must be in production requirements"


def test_weaver_entrypoint_exists() -> None:
    """The ASGI entry module (weaver.py) must exist at repository root."""
    weaver_path = _repo_root() / "weaver.py"
    assert weaver_path.exists(), "weaver.py must exist at repository root"

    content = weaver_path.read_text(encoding="utf-8")
    assert "create_app" in content, "weaver.py must call create_app()"
    assert "app = " in content, "weaver.py must export 'app'"


def test_frontend_dockerfile_has_multistage_build() -> None:
    """Frontend Dockerfile must have a multi-stage build."""
    dockerfile_path = _repo_root() / "docker" / "frontend" / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "AS builder" in content, "Must have builder stage"
    assert "npm run build" in content, "Must build frontend"
    assert "nginx" in content.lower(), "Must serve via nginx"


def test_nginx_conf_proxies_api() -> None:
    """Nginx config must proxy /api/ to backend."""
    nginx_path = _repo_root() / "docker" / "frontend" / "nginx.conf"
    content = nginx_path.read_text(encoding="utf-8")

    assert "proxy_pass http://backend:8000" in content
    assert "/api/" in content

"""Release smoke contract tests for deployment-critical static contracts.

Runtime/dependency wiring is validated by compose smoke execution in CI and
local scripts. This file keeps only minimal static invariants.
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


def test_compose_smoke_workflow_checks_api_and_frontend() -> None:
    """Compose smoke workflow should validate API and frontend over HTTP."""
    workflow_path = _repo_root() / ".github" / "workflows" / "compose-smoke.yml"
    content = workflow_path.read_text(encoding="utf-8")

    assert "Wait for API health" in content
    assert "/api/v1/healthz" in content
    assert "Wait for frontend" in content
    assert "http://127.0.0.1:${FRONTEND_PORT_PROD}/" in content


def test_weaver_entrypoint_exists() -> None:
    """The ASGI entry module (weaver.py) must exist at repository root."""
    weaver_path = _repo_root() / "weaver.py"
    assert weaver_path.exists(), "weaver.py must exist at repository root"

    content = weaver_path.read_text(encoding="utf-8")
    assert "create_app" in content, "weaver.py must call create_app()"
    assert "app = " in content, "weaver.py must export 'app'"


def test_nginx_conf_proxies_api() -> None:
    """Nginx config must proxy /api/ to backend."""
    nginx_path = _repo_root() / "docker" / "frontend" / "nginx.conf"
    content = nginx_path.read_text(encoding="utf-8")

    assert "proxy_pass http://backend:8000" in content
    assert "/api/" in content

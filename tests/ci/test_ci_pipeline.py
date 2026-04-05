"""
CI Pipeline Tests — runnable from VS Code Test Explorer.

Each test calls a shared script from scripts/ci/, the same scripts used
by GitHub Actions workflows and check-all.sh.  This ensures that what
you see locally in the Testing sidebar is identical to what CI runs.

Marker: @pytest.mark.ci  (excluded from default pytest runs)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]  # /weaver
SCRIPTS = ROOT / "scripts" / "ci"


def _run(cmd: list[str]) -> None:
    """Run a command, raise on failure with captured output."""
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = f"Command failed: {' '.join(cmd)}\n"
        if result.stdout:
            msg += f"--- stdout ---\n{result.stdout[-3000:]}\n"
        if result.stderr:
            msg += f"--- stderr ---\n{result.stderr[-3000:]}\n"
        pytest.fail(msg)


def _script(name: str, *args: str) -> None:
    """Run a scripts/ci/ script."""
    _run(["bash", str(SCRIPTS / name), *args])


# ===========================================================================
# 1. Backend Lint & Type-check  (scripts/ci/backend-lint.sh)
# ===========================================================================


@pytest.mark.ci
@pytest.mark.timeout(300)
class TestBackendLint:
    """Backend code quality checks (ruff + mypy)."""

    def test_ruff_check(self) -> None:
        _script("backend-lint.sh", "ruff-check")

    def test_ruff_format(self) -> None:
        _script("backend-lint.sh", "ruff-format")

    def test_mypy(self) -> None:
        _script("backend-lint.sh", "mypy")


# ===========================================================================
# 2. Database Migration  (scripts/ci/db-migrate.sh)
# ===========================================================================


@pytest.mark.ci
@pytest.mark.timeout(120)
class TestDatabaseMigration:
    """Alembic migration check."""

    def test_alembic_upgrade_head(self) -> None:
        _script("db-migrate.sh")


# ===========================================================================
# 3. Frontend Lint & Type-check  (scripts/ci/frontend-lint.sh)
# ===========================================================================


@pytest.mark.ci
@pytest.mark.timeout(120)
class TestFrontendLint:
    """Frontend code quality checks (ESLint + TypeScript)."""

    def test_eslint(self) -> None:
        _script("frontend-lint.sh", "eslint")

    def test_typescript_check(self) -> None:
        _script("frontend-lint.sh", "tsc")


# ===========================================================================
# 4. Frontend Tests & Build  (scripts/ci/frontend-test.sh)
# ===========================================================================


@pytest.mark.ci
@pytest.mark.timeout(300)
class TestFrontendTests:
    """Frontend test suite and production build."""

    def test_vitest(self) -> None:
        _script("frontend-test.sh", "vitest")

    def test_production_build(self) -> None:
        _script("frontend-test.sh", "build")


# ===========================================================================
# 5. Compose Smoke Test  (scripts/ci/compose-smoke.sh)
# ===========================================================================


@pytest.mark.ci
@pytest.mark.timeout(600)
class TestComposeSmoke:
    """Production docker-compose build + health check."""

    def test_compose_smoke(self) -> None:
        _script("compose-smoke.sh")

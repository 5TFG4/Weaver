"""Tests that CI tooling configurations are present and correct in pyproject.toml."""

from pathlib import Path

import tomllib

import pytest

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text())


class TestCIContract:
    def test_ruff_target_version(self, pyproject: dict) -> None:
        assert pyproject["tool"]["ruff"]["target-version"] == "py313"

    def test_mypy_disallow_untyped_defs(self, pyproject: dict) -> None:
        assert pyproject["tool"]["mypy"]["disallow_untyped_defs"] is True

    def test_pytest_markers_registered(self, pyproject: dict) -> None:
        markers = pyproject["tool"]["pytest"]["ini_options"]["markers"]
        marker_names = {m.split(":")[0].strip() for m in markers}
        assert {"unit", "integration", "container", "e2e", "slow"} <= marker_names

    def test_pytest_default_excludes_container(self, pyproject: dict) -> None:
        addopts = pyproject["tool"]["pytest"]["ini_options"]["addopts"]
        assert "not container" in addopts

    def test_coverage_fail_under(self, pyproject: dict) -> None:
        assert pyproject["tool"]["coverage"]["report"]["fail_under"] == 80

    def test_ruff_lint_select_includes_core_rules(self, pyproject: dict) -> None:
        select = pyproject["tool"]["ruff"]["lint"]["select"]
        for rule in ("E", "W", "F", "I", "B"):
            assert rule in select, f"Missing core ruff rule: {rule}"

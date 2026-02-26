"""Documentation consistency guards for M8-R closeout.

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
    assert "894 tests (808 backend + 86 frontend)" not in readme


def test_test_coverage_snapshot_is_current() -> None:
    coverage_doc = _read("docs/TEST_COVERAGE.md")

    assert "908 backend + 90 frontend = 998" in coverage_doc
    assert "89.78%" in coverage_doc

    assert "904 backend + 88 frontend = 992" not in coverage_doc
    assert "89.73%" not in coverage_doc


def test_milestone_plan_keeps_runs_deeplink_wording() -> None:
    milestone_plan = _read("docs/MILESTONE_PLAN.md")

    assert "Keep /runs/:runId deep-link route" in milestone_plan
    assert "Removed unused /runs/:runId route" not in milestone_plan


def test_design_audit_status_reflects_m8r_closeout() -> None:
    design_audit = _read("docs/DESIGN_AUDIT.md")

    assert "M8-Core ✅ Complete · M8-R 🔄 Active" in design_audit

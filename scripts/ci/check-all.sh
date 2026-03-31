#!/usr/bin/env bash
set -euo pipefail
# Full CI pipeline — calls the same scripts used by GitHub Actions.
# Designed to run INSIDE the dev container (backend_dev).
#
# NO FLAGS. NO SHORTCUTS. Runs the FULL CI pipeline every time.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS="$ROOT_DIR/scripts/ci"
cd "$ROOT_DIR"

if [[ $# -gt 0 ]]; then
    echo "ERROR: check-all.sh takes NO arguments. It always runs the full CI pipeline."
    echo "Usage: bash scripts/ci/check-all.sh"
    exit 1
fi

# run_step NAME CMD...
run_step() {
    local name="$1"; shift
    local tmp
    tmp=$(mktemp)
    printf "  %-35s" "$name"
    if "$@" > "$tmp" 2>&1; then
        echo "✅"
    else
        echo "❌"
        echo ""
        cat "$tmp"
        rm -f "$tmp"
        exit 1
    fi
    rm -f "$tmp"
}

echo "=========================================="
echo " Full CI Check (no shortcuts)"
echo "=========================================="
echo ""

# ── 1. Backend CI (matches .github/workflows/backend-ci.yml) ──
run_step "Backend: ruff check"    bash "$SCRIPTS/backend-lint.sh" ruff-check
run_step "Backend: ruff format"   bash "$SCRIPTS/backend-lint.sh" ruff-format
run_step "Backend: mypy"          bash "$SCRIPTS/backend-lint.sh" mypy
run_step "Backend: alembic"       bash "$SCRIPTS/db-migrate.sh"
run_step "Backend: pytest"        bash "$SCRIPTS/backend-test.sh"

# ── 2. Frontend CI (matches .github/workflows/frontend-ci.yml) ──
echo ""
run_step "Frontend: eslint"       bash "$SCRIPTS/frontend-lint.sh" eslint
run_step "Frontend: tsc"          bash "$SCRIPTS/frontend-lint.sh" tsc
run_step "Frontend: vitest"       bash "$SCRIPTS/frontend-test.sh" vitest
run_step "Frontend: build"        bash "$SCRIPTS/frontend-test.sh" build

# ── 3. E2E (matches .github/workflows/e2e.yml) ──
echo ""
run_step "E2E: full suite"        bash "$SCRIPTS/e2e.sh"

# ── 4. Compose smoke (matches .github/workflows/compose-smoke.yml) ──
echo ""
run_step "Smoke: compose up"      bash "$SCRIPTS/compose-smoke.sh"

echo ""
echo "=========================================="
echo " All checks passed ✅"
echo "=========================================="

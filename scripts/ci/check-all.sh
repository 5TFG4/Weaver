#!/usr/bin/env bash
set -euo pipefail
# Designed to run INSIDE the dev container (backend_dev).
# All tools (Python, Node, ruff, mypy, Docker CLI) are pre-installed.
# DB_URL is set via docker-compose.dev.yml environment.
#
# NO FLAGS. NO SHORTCUTS. Runs the FULL CI pipeline every time:
#   backend-ci  → ruff, mypy, alembic, pytest (unit+integration)
#   frontend-ci → eslint, tsc, vitest --coverage, vite build
#   e2e         → docker compose E2E suite (all 33 tests)
#   smoke       → docker compose production smoke test

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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
run_step "Backend: ruff check"    ruff check src/ tests/
run_step "Backend: ruff format"   ruff format --check src/ tests/
run_step "Backend: mypy"          mypy src/

if [[ -n "${DB_URL:-}" ]]; then
    run_step "Backend: alembic upgrade head" \
        alembic upgrade head
else
    echo "  ⚠  DB_URL not set — alembic skipped (integration tests may fail)"
fi

run_step "Backend: pytest (unit+integration)" \
    pytest -m "not container" --ignore=tests/e2e --cov=src --cov-report=term-missing -q

# ── 2. Frontend CI (matches .github/workflows/frontend-ci.yml) ──
echo ""
run_step "Frontend: eslint"       bash -c 'cd haro && npm run lint --silent'
run_step "Frontend: tsc"          bash -c 'cd haro && npx tsc -b --noEmit'
run_step "Frontend: vitest"       bash -c 'cd haro && npm run test:coverage --silent'
run_step "Frontend: build"        bash -c 'cd haro && npm run build --silent'

# ── 3. E2E (matches .github/workflows/e2e.yml) ──
echo ""
run_step "E2E: full suite" \
    bash scripts/ci/e2e-local.sh

# ── 4. Compose smoke (matches .github/workflows/compose-smoke.yml) ──
echo ""
run_step "Smoke: compose up" \
    bash scripts/ci/compose-smoke-local.sh

echo ""
echo "=========================================="
echo " All checks passed ✅"
echo "=========================================="

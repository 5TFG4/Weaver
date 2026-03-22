#!/usr/bin/env bash
set -euo pipefail
# Any step that fails stops the script immediately.
# Verbose mode: pass -v to see full output from each step.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERBOSE=false
if [[ "${1:-}" == "-v" ]]; then
    VERBOSE=true
fi

# run_step NAME CMD...
# In normal mode, capture output and show one-line pass/fail.
# In verbose mode (-v), stream everything.
run_step() {
    local name="$1"; shift
    if $VERBOSE; then
        echo ""
        echo "--- $name ---"
        "$@"
        echo "  ✅ $name"
    else
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
    fi
}

echo "=========================================="
echo " Local CI Check"
echo "=========================================="
echo ""

run_step "Backend: ruff check"    ruff check src/ tests/
run_step "Backend: ruff format"   ruff format --check src/ tests/
run_step "Backend: mypy"          mypy src/
run_step "Backend: pytest"        pytest -m "not container" --ignore=tests/e2e --cov=src --cov-report=term-missing -q

if [[ -n "${DB_URL:-}" ]]; then
    echo ""
    echo "  (DB_URL detected — integration tests included above)"
else
    echo ""
    echo "  ⚠  DB_URL not set — 44 integration tests skipped"
    echo "     Set DB_URL=postgresql+asyncpg://... to include them"
fi

echo ""
run_step "Frontend: eslint"       bash -c 'cd haro && npm run lint --silent'
run_step "Frontend: tsc"          bash -c 'cd haro && npx tsc -b --noEmit'
run_step "Frontend: vitest"       bash -c 'cd haro && npm run test --silent'
run_step "Frontend: build"        bash -c 'cd haro && npm run build --silent'

echo ""
echo "=========================================="
echo " All checks passed — safe to push"
echo "=========================================="

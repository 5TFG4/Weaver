#!/usr/bin/env bash
set -euo pipefail
# Designed to run INSIDE the dev container (backend_dev).
# All tools (Python, Node, ruff, mypy, Docker CLI) are pre-installed.
# DB_URL is set via docker-compose.dev.yml environment.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MODE="full"
VERBOSE=false
RUN_E2E=false
RUN_SMOKE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fast)  MODE="fast"; shift ;;
        --full)  MODE="full"; shift ;;
        --e2e)   RUN_E2E=true; shift ;;
        --smoke) RUN_SMOKE=true; shift ;;
        --all)   RUN_E2E=true; RUN_SMOKE=true; MODE="full"; shift ;;
        -v)      VERBOSE=true; shift ;;
        *)       echo "Unknown option: $1"; exit 1 ;;
    esac
done

# run_step NAME CMD...
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
echo " CI Check (inside container)"
echo " Mode: $MODE | E2E: $RUN_E2E | Smoke: $RUN_SMOKE"
echo "=========================================="
echo ""

# ── Backend ──────────────────────────────────
run_step "Backend: ruff check"    ruff check src/ tests/
run_step "Backend: ruff format"   ruff format --check src/ tests/
run_step "Backend: mypy"          mypy src/

if [[ "$MODE" == "fast" ]]; then
    run_step "Backend: pytest (unit)" \
        pytest -m "not container" --ignore=tests/e2e --ignore=tests/integration -q
else
    if [[ -n "${DB_URL:-}" ]]; then
        run_step "Backend: alembic upgrade head" \
            alembic upgrade head
    fi

    run_step "Backend: pytest (unit+integration)" \
        pytest -m "not container" --ignore=tests/e2e --cov=src --cov-report=term-missing -q

    if [[ -z "${DB_URL:-}" ]]; then
        echo "  ⚠  DB_URL not set — skipping alembic & integration tests"
    fi
fi

# ── Frontend ─────────────────────────────────
echo ""
run_step "Frontend: eslint"       bash -c 'cd haro && npm run lint --silent'
run_step "Frontend: tsc"          bash -c 'cd haro && npx tsc -b --noEmit'

if [[ "$MODE" == "fast" ]]; then
    run_step "Frontend: vitest"   bash -c 'cd haro && npm run test --silent'
else
    run_step "Frontend: vitest"   bash -c 'cd haro && npm run test:coverage --silent'
fi

run_step "Frontend: build"        bash -c 'cd haro && npm run build --silent'

# ── E2E tests (same docker-compose.e2e.yml as GitHub Actions e2e.yml) ──
if $RUN_E2E; then
    echo ""
    run_step "E2E: full suite" \
        bash scripts/ci/e2e-local.sh
fi

# ── Compose smoke (same docker-compose.yml as GitHub Actions compose-smoke.yml) ──
if $RUN_SMOKE; then
    echo ""
    run_step "Smoke: compose up" \
        bash scripts/ci/compose-smoke-local.sh
fi

echo ""
echo "=========================================="
echo " All checks passed ✅"
echo "=========================================="

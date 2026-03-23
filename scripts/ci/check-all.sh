#!/usr/bin/env bash
set -euo pipefail
# Designed to run INSIDE the dev container (backend_dev).
# All tools (Python, Node, ruff, mypy, Docker CLI) are pre-installed.
# DB_URL is set via docker-compose.dev.yml environment.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MODE="full"
VERBOSE=false
SMOKE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fast)  MODE="fast"; shift ;;
        --full)  MODE="full"; shift ;;
        --smoke) SMOKE=true; shift ;;
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
echo " Mode: $MODE | Smoke: $SMOKE"
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
    run_step "Backend: pytest (unit+integration)" \
        pytest -m "not container" --ignore=tests/e2e --cov=src --cov-report=term-missing -q

    if [[ -z "${DB_URL:-}" ]]; then
        echo "  ⚠  DB_URL not set — integration tests may have been skipped"
    fi
fi

# ── Frontend ─────────────────────────────────
echo ""
run_step "Frontend: eslint"       bash -c 'cd haro && npm run lint --silent'
run_step "Frontend: tsc"          bash -c 'cd haro && npx tsc -b --noEmit'
run_step "Frontend: vitest"       bash -c 'cd haro && npm run test --silent'
run_step "Frontend: build"        bash -c 'cd haro && npm run build --silent'

# ── Smoke (optional) ─────────────────────────
if $SMOKE; then
    echo ""
    run_step "Compose: smoke test" \
        docker compose -f docker/docker-compose.yml up -d --wait --wait-timeout 60
    run_step "Compose: health check" \
        bash -c 'curl -sf http://localhost:8000/api/v1/health | grep -q ok'
    run_step "Compose: teardown" \
        docker compose -f docker/docker-compose.yml down
fi

echo ""
echo "=========================================="
echo " All checks passed ✅"
echo "=========================================="

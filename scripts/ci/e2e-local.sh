#!/usr/bin/env bash
set -euo pipefail
# E2E test runner — matches .github/workflows/e2e.yml exactly.
# NO FLAGS. Builds, runs ALL E2E tests, tears down. No shortcuts.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.e2e.yml"
COMPOSE_ARGS=(-f "$COMPOSE_FILE")

if [[ $# -gt 0 ]]; then
    echo "ERROR: e2e-local.sh takes NO arguments. It runs the full E2E suite."
    exit 1
fi

echo "=========================================="
echo " E2E Test Runner (Containerized)"
echo "=========================================="

teardown() {
    echo ""
    echo "--- Tearing down E2E stack ---"
    docker compose "${COMPOSE_ARGS[@]}" --profile test down -v 2>/dev/null || true
}
trap teardown EXIT

echo ""
echo "--- Building images ---"
docker compose "${COMPOSE_ARGS[@]}" --profile test build

echo ""
echo "--- Starting E2E stack (db + backend + frontend) ---"
docker compose "${COMPOSE_ARGS[@]}" up -d --wait db_e2e backend_e2e frontend_e2e

echo ""
echo "--- Running E2E tests in container ---"
docker compose "${COMPOSE_ARGS[@]}" run --rm test_runner

echo ""
echo "=========================================="
echo " E2E tests complete"
echo "=========================================="

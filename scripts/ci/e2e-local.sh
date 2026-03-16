#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.e2e.yml"
COMPOSE_ARGS=(-f "$COMPOSE_FILE")

echo "=========================================="
echo " E2E Test Runner (Containerized)"
echo "=========================================="

KEEP_UP=false
PYTEST_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --keep-up) KEEP_UP=true ;;
    *)         PYTEST_ARGS+=("$arg") ;;
  esac
done

teardown() {
  if ! $KEEP_UP; then
    echo ""
    echo "--- Tearing down E2E stack ---"
    docker compose "${COMPOSE_ARGS[@]}" --profile test down -v 2>/dev/null || true
  else
    echo ""
    echo "--- Stack left running (--keep-up). Tear down manually: ---"
    echo "  docker compose ${COMPOSE_ARGS[*]} --profile test down -v"
  fi
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
if [[ ${#PYTEST_ARGS[@]} -gt 0 ]]; then
  docker compose "${COMPOSE_ARGS[@]}" run --rm test_runner pytest tests/e2e/ -v --timeout=60 "${PYTEST_ARGS[@]}"
else
  docker compose "${COMPOSE_ARGS[@]}" run --rm test_runner
fi

echo ""
echo "=========================================="
echo " E2E tests complete"
echo "=========================================="

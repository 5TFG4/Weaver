#!/usr/bin/env bash
set -euo pipefail
# E2E test runner — single source of truth for e2e.yml and local runs.
# Builds the E2E stack, starts it, runs Playwright tests in test_runner
# container, tears down.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.e2e.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

teardown() {
    echo "--- Tearing down E2E stack ---"
    "${COMPOSE[@]}" --profile test down -v 2>/dev/null || true
    docker image prune -f 2>/dev/null || true
}
trap teardown EXIT

echo "--- Building E2E images ---"
"${COMPOSE[@]}" --profile test build

echo "--- Starting E2E stack ---"
"${COMPOSE[@]}" up -d --wait db_e2e backend_e2e frontend_e2e

echo "--- Running E2E tests ---"
"${COMPOSE[@]}" run --rm test_runner

echo "--- E2E tests complete ---"

#!/usr/bin/env bash
set -euo pipefail
# Host-side wrapper: delegates all CI checks to the dev container.
#
# Usage:
#   bash scripts/ci/check-local.sh           # full check (matches GitHub Actions)
#   bash scripts/ci/check-local.sh --fast    # lint + type + unit only
#   bash scripts/ci/check-local.sh --e2e     # full check + E2E tests
#   bash scripts/ci/check-local.sh --smoke   # full check + compose smoke test
#   bash scripts/ci/check-local.sh --all     # full + E2E + smoke (everything)
#   bash scripts/ci/check-local.sh -v        # verbose output
#
# Prerequisites: docker compose services must be running
#   docker compose -f docker/docker-compose.dev.yml up -d

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo " Local CI Check (via dev container)"
echo "=========================================="
echo ""

# Ensure dev services are running
if ! docker compose -f docker/docker-compose.dev.yml ps --status running backend_dev -q 2>/dev/null | grep -q .; then
    echo "  ⚠  backend_dev is not running. Starting dev services..."
    docker compose -f docker/docker-compose.dev.yml up -d --wait
fi

# Delegate to container-internal script, forwarding all arguments
docker compose -f docker/docker-compose.dev.yml exec -T backend_dev \
    bash scripts/ci/check-all.sh "$@"

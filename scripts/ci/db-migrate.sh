#!/usr/bin/env bash
set -euo pipefail
# Alembic database migration check.  Mirrors backend-ci.yml migration step.
# Skips (exit 0) when DB_URL is not set.

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if [[ -z "${DB_URL:-}" ]]; then
    echo "SKIP: DB_URL not set"
    exit 0
fi
alembic upgrade head

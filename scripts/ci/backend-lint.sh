#!/usr/bin/env bash
set -euo pipefail
# Backend lint & type-check.  Mirrors backend-ci.yml lint steps.
# Usage:
#   bash scripts/ci/backend-lint.sh          # run all
#   bash scripts/ci/backend-lint.sh ruff-check
#   bash scripts/ci/backend-lint.sh ruff-format
#   bash scripts/ci/backend-lint.sh mypy

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

run_ruff_check()  { ruff check src/ tests/; }
run_ruff_format() { ruff format --check src/ tests/; }
run_mypy()        { mypy src/; }

case "${1:-all}" in
    ruff-check)  run_ruff_check ;;
    ruff-format) run_ruff_format ;;
    mypy)        run_mypy ;;
    all)
        run_ruff_check
        run_ruff_format
        run_mypy
        ;;
    *) echo "Unknown check: $1" >&2; exit 1 ;;
esac

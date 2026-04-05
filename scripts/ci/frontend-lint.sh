#!/usr/bin/env bash
set -euo pipefail
# Frontend lint & type-check.  Mirrors frontend-ci.yml lint steps.
# Usage:
#   bash scripts/ci/frontend-lint.sh          # run all
#   bash scripts/ci/frontend-lint.sh eslint
#   bash scripts/ci/frontend-lint.sh tsc

cd "$(dirname "${BASH_SOURCE[0]}")/../../haro"

run_eslint() { npm run lint; }
run_tsc()    { npx tsc -b --noEmit; }

case "${1:-all}" in
    eslint) run_eslint ;;
    tsc)    run_tsc ;;
    all)
        run_eslint
        run_tsc
        ;;
    *) echo "Unknown check: $1" >&2; exit 1 ;;
esac

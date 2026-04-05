#!/usr/bin/env bash
set -euo pipefail
# Frontend tests & production build.  Mirrors frontend-ci.yml test steps.
# Usage:
#   bash scripts/ci/frontend-test.sh          # run all
#   bash scripts/ci/frontend-test.sh vitest
#   bash scripts/ci/frontend-test.sh build

cd "$(dirname "${BASH_SOURCE[0]}")/../../haro"

run_vitest() { npm run test:coverage; }
run_build()  { npm run build; }

case "${1:-all}" in
    vitest) run_vitest ;;
    build)  run_build ;;
    all)
        run_vitest
        run_build
        ;;
    *) echo "Unknown check: $1" >&2; exit 1 ;;
esac

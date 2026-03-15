#!/usr/bin/env bash
set -euo pipefail
# Any step that fails stops the script immediately.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo " Local CI Check"
echo "=========================================="

echo ""
echo "--- Backend: ruff check ---"
ruff check src/ tests/

echo "--- Backend: ruff format ---"
ruff format --check src/ tests/

echo "--- Backend: mypy ---"
mypy src/

echo "--- Backend: pytest + coverage ---"
pytest -m "not container" --cov=src --cov-report=term-missing -q

echo ""
echo "--- Frontend: eslint ---"
(cd haro && npm run lint)

echo "--- Frontend: tsc ---"
(cd haro && npx tsc -b --noEmit)

echo "--- Frontend: vitest ---"
(cd haro && npm run test)

echo "--- Frontend: build ---"
(cd haro && npm run build)

echo ""
echo "=========================================="
echo " All checks passed — safe to push"
echo "=========================================="

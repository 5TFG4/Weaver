#!/usr/bin/env bash
set -euo pipefail
# Backend pytest run (unit + integration, with coverage).
# Mirrors backend-ci.yml test step.

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
pytest --ignore=tests/e2e --ignore=tests/ci --cov=src --cov-report=term-missing -q

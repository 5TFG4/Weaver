#!/usr/bin/env bash
set -euo pipefail
# Backend pytest run (unit + integration, with coverage).
# Mirrors backend-ci.yml test step.

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
pytest -m "not container" --ignore=tests/e2e --cov=src --cov-report=term-missing -q

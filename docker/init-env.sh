#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="docker/.env.dev"
EXAMPLE_FILE="docker/example.env.dev"

# create .env if missing
if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ -f "${EXAMPLE_FILE}" ]]; then
    cp "${EXAMPLE_FILE}" "${ENV_FILE}"
    echo "Created ${ENV_FILE} from ${EXAMPLE_FILE}"
  else
    echo "Missing ${EXAMPLE_FILE}. Please add it." >&2
    exit 1
  fi
else
  echo "${ENV_FILE} already exists; skip."
fi

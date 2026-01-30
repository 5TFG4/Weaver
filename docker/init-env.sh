#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# 1. Define the list of variables to inject from GitHub Secrets/Env
#    Add any new API keys or Endpoints here.
#
#    Naming convention:
#      ALPACA_LIVE_*  -> Real money trading
#      ALPACA_PAPER_* -> Simulation / backtest
#
VARS_TO_INJECT=(
  # Live Trading (Real Money)
  "ALPACA_LIVE_API_KEY"
  "ALPACA_LIVE_API_SECRET"
  "ALPACA_LIVE_BASE_URL"
  # Paper Trading (Simulation / Backtest)
  "ALPACA_PAPER_API_KEY"
  "ALPACA_PAPER_API_SECRET"
  "ALPACA_PAPER_BASE_URL"
  # Database
  "POSTGRES_USER"
  "POSTGRES_PASSWORD"
)

# ==============================================================================
# FUNCTION DEFINITION
# ==============================================================================

# Function: sync_env_file
# Arguments:
#   $1: The target .env file path (e.g., docker/.env.dev)
#   $2: The source example file path (e.g., docker/example.env.dev)
sync_env_file() {
  local TARGET_FILE="$1"
  local EXAMPLE_FILE="$2"

  echo "----------------------------------------------------------------"
  echo "Processing: ${TARGET_FILE}"

  # Step A: Create file from example if missing
  if [[ ! -f "${TARGET_FILE}" ]]; then
    if [[ -f "${EXAMPLE_FILE}" ]]; then
      echo " -> Creating from ${EXAMPLE_FILE}..."
      cp "${EXAMPLE_FILE}" "${TARGET_FILE}"
    else
      echo " -> Error: Source '${EXAMPLE_FILE}' missing. Skipping." >&2
      return
    fi
  else
    echo " -> File already exists. checking for updates..."
  fi

  # Step B: Inject secrets
  for VAR_NAME in "${VARS_TO_INJECT[@]}"; do
    # Get value from environment (GitHub Secret or Codespace Env)
    local CURRENT_VALUE="${!VAR_NAME:-}"

    if [[ -n "$CURRENT_VALUE" ]]; then
      # Check if variable exists in file to decide replace or append
      if grep -q "^${VAR_NAME}=" "${TARGET_FILE}"; then
        # Replace existing value (using | as delimiter for URLs)
        sed -i "s|^${VAR_NAME}=.*|${VAR_NAME}=${CURRENT_VALUE}|" "${TARGET_FILE}"
        echo "    - Injected: ${VAR_NAME}"
      else
        # Append new value if missing
        echo "" >> "${TARGET_FILE}"
        echo "${VAR_NAME}=${CURRENT_VALUE}" >> "${TARGET_FILE}"
        echo "    - Appended: ${VAR_NAME}"
      fi
    fi
  done
}

# ==============================================================================
# EXECUTION
# ==============================================================================

echo "Starting Environment Initialization..."

# 1. Configure the DEV environment
#    Usage: sync_env_file "TARGET_PATH" "EXAMPLE_PATH"
sync_env_file "docker/.env.dev" "docker/example.env.dev"

# 2. Configure the PRODUCTION environment (or main .env)
#    Adjust the paths below if your prod .env is in the root folder (e.g., ".env")
sync_env_file "docker/.env" "docker/example.env"

echo "----------------------------------------------------------------"
echo "Initialization Complete."
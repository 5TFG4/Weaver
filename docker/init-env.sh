#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Environment Initialization Script
# ==============================================================================
# Creates .env from example.env and injects secrets from environment.
# Variables are auto-detected from the example file (no hardcoded list).

# Function: sync_env_file
# Arguments:
#   $1: The target .env file path
#   $2: The source example file path
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
    echo " -> File already exists. Checking for updates..."
  fi

  # Step B: Inject secrets from environment (auto-detect vars from example)
  while IFS='=' read -r VAR_NAME _; do
    # Skip comments and empty lines
    [[ -z "$VAR_NAME" || "$VAR_NAME" =~ ^[[:space:]]*# ]] && continue
    
    # Trim whitespace
    VAR_NAME=$(echo "$VAR_NAME" | xargs)
    
    # Get value from environment (GitHub Secret or Codespace Env)
    local CURRENT_VALUE="${!VAR_NAME:-}"
    
    if [[ -n "$CURRENT_VALUE" ]]; then
      # Replace existing value (using | as delimiter for URLs)
      sed -i "s|^${VAR_NAME}=.*|${VAR_NAME}=${CURRENT_VALUE}|" "${TARGET_FILE}"
      echo "    - Injected: ${VAR_NAME}"
    fi
  done < "${EXAMPLE_FILE}"
}

# ==============================================================================
# EXECUTION
# ==============================================================================

echo "Starting Environment Initialization..."

# Generate .env in project root (Compose reads from working directory)
sync_env_file ".env" "docker/example.env"

echo "----------------------------------------------------------------"
echo "Initialization Complete."
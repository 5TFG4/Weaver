#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# List of variable names to inject from GitHub Secrets/Environment into the .env files.
# The script will look for these in the system environment. If found, they overwrite the file.
VARS_TO_INJECT=(
  "ALPACA_API_ENDPOINT"
  "ALPACA_API_KEY"
  "ALPACA_API_SECRET"
  "ALPACA_PAPER_API_ENDPOINT"
  "ALPACA_PAPER_API_KEY"
  "ALPACA_PAPER_API_SECRET"
)

# ==============================================================================
# FUNCTIONS
# ==============================================================================

# Function: configure_env_file
# Arguments:
#   $1: Target file path (e.g., docker/.env)
#   $2: Example file path (e.g., docker/example.env)
configure_env_file() {
  local TARGET_FILE="$1"
  local EXAMPLE_FILE="$2"

  echo "----------------------------------------------------------------"
  echo "Processing: ${TARGET_FILE}"

  # 1. Create file from example if it doesn't exist
  if [[ ! -f "${TARGET_FILE}" ]]; then
    if [[ -f "${EXAMPLE_FILE}" ]]; then
      echo " -> Creating from ${EXAMPLE_FILE}..."
      cp "${EXAMPLE_FILE}" "${TARGET_FILE}"
    else
      echo " -> Error: Example file ${EXAMPLE_FILE} missing. Skipping." >&2
      return 1 # Skip this file but don't exit script completely
    fi
  else
    echo " -> File already exists. Preserving existing values."
  fi

  # 2. Inject Secrets
  echo " -> Checking for secrets to inject..."
  local injected_count=0

  for VAR_NAME in "${VARS_TO_INJECT[@]}"; do
    # Get the value of the variable from the environment (Host/Codespace)
    local CURRENT_VALUE="${!VAR_NAME:-}"

    if [[ -n "$CURRENT_VALUE" ]]; then
      # Check if the variable exists in the file (to decide replace vs append)
      if grep -q "^${VAR_NAME}=" "${TARGET_FILE}"; then
        # Update existing line using | as delimiter to handle URLs safely
        sed -i "s|^${VAR_NAME}=.*|${VAR_NAME}=${CURRENT_VALUE}|" "${TARGET_FILE}"
      else
        # Append to file if not found, ensuring a preceding newline
        # Check if file ends with newline, if not add one
        if [ -s "${TARGET_FILE}" ] && [ "$(tail -c1 "${TARGET_FILE}" | wc -l)" -eq 0 ]; then
             echo "" >> "${TARGET_FILE}"
        fi
        echo "${VAR_NAME}=${CURRENT_VALUE}" >> "${TARGET_FILE}"
      fi
      ((injected_count++))
    fi
  done

  if [[ "$injected_count" -gt 0 ]]; then
    echo " -> Successfully injected ${injected_count} secrets."
  else
    echo " -> No secrets found in environment (Local Dev mode). No changes made."
  fi
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

# 1. Configure Development Environment
# Adjust filename "docker/example.env.dev" if your actual file is named differently
configure_env_file "docker/.env.dev" "docker/example.env.dev"

# 2. Configure Production Environment
# Adjust filename "docker/example.env" if your actual file is named differently
configure_env_file "docker/.env" "docker/example.env"

echo "----------------------------------------------------------------"
echo "All environment configurations complete."
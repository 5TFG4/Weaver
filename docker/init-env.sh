#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
# We explicitly do NOT use -u (nounset) here to prevent errors when variables are missing in local dev.
set -e

# ==============================================================================
# 1. CONFIGURATION
#    Add your new secrets/variables here.
#    The script will look for these in the system environment (Codespaces/GitHub Secrets)
#    and inject them into your .env files if found.
# ==============================================================================
VARS_TO_INJECT=(
  "ALPACA_API_ENDPOINT"
  "ALPACA_API_KEY"
  "ALPACA_API_SECRET"
  "ALPACA_PAPER_API_ENDPOINT"
  "ALPACA_PAPER_API_KEY"
  "ALPACA_PAPER_API_SECRET"
)

# ==============================================================================
# 2. HELPER FUNCTION
# ==============================================================================
# Function: configure_env_file
# Arguments:
#   $1: Target file path (e.g., docker/.env.dev)
#   $2: Example file path (e.g., docker/example.env.dev)
configure_env_file() {
  local TARGET_FILE="$1"
  local EXAMPLE_FILE="$2"

  echo "----------------------------------------------------------------"
  echo "Processing: ${TARGET_FILE}"

  # --- Step A: Create file from example if it is missing ---
  if [[ ! -f "${TARGET_FILE}" ]]; then
    if [[ -f "${EXAMPLE_FILE}" ]]; then
      echo " -> Creating from ${EXAMPLE_FILE}..."
      cp "${EXAMPLE_FILE}" "${TARGET_FILE}"
    else
      echo " -> Error: Example file ${EXAMPLE_FILE} missing. Skipping." >&2
      return 1
    fi
  else
    echo " -> File already exists. Preserving existing values."
  fi

  # --- Step B: Inject Secrets from Environment ---
  echo " -> Checking for secrets to inject..."
  local injected_count=0

  for VAR_NAME in "${VARS_TO_INJECT[@]}"; do
    # KEY LOGIC: Use printenv to safely attempt to get the variable value.
    # "|| true" ensures that if the var is missing (exit code 1), the script doesn't crash.
    local CURRENT_VALUE
    CURRENT_VALUE=$(printenv "${VAR_NAME}" || true)

    # Only inject if we actually found a value (Codespaces/CI mode)
    if [[ -n "$CURRENT_VALUE" ]]; then
      # Check if the variable key already exists in the file
      if grep -q "^${VAR_NAME}=" "${TARGET_FILE}"; then
        # Update existing line
        # We use '|' as the delimiter for sed to handle URLs (Endpoints) safely without escaping slashes
        sed -i "s|^${VAR_NAME}=.*|${VAR_NAME}=${CURRENT_VALUE}|" "${TARGET_FILE}"
      else
        # Append new line if it doesn't exist
        # First, ensure the file ends with a newline before appending to avoid concatenation issues
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
    echo " -> No secrets found in environment. (Normal for Local Dev)"
  fi
}

# ==============================================================================
# 3. EXECUTION
# ==============================================================================

# Configure Development Environment
configure_env_file "docker/.env.dev" "docker/example.env.dev"

# Configure Production Environment (Only if example.env exists)
if [[ -f "docker/example.env" ]]; then
    configure_env_file "docker/.env" "docker/example.env"
fi

echo "----------------------------------------------------------------"
echo "Initialization complete."
#!/usr/bin/env bash
set -euo pipefail

# Configuration
ENV_FILE="docker/.env.dev"
EXAMPLE_FILE="docker/example.env.dev"

# Define the list of variables you want to sync from GitHub Secrets/Env to the .env file.
# Add any new API keys or Endpoints here.
VARS_TO_INJECT=(
  "ALPACA_API_ENDPOINT"
  "ALPACA_API_KEY"
  "ALPACA_API_SECRET"
  "ALPACA_PAPER_API_ENDPOINT"
  "ALPACA_PAPER_API_KEY"
  "ALPACA_PAPER_API_SECRET"
)

# ------------------------------------------------------------------
# Step 1: Ensure the .env file exists
# ------------------------------------------------------------------
if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ -f "${EXAMPLE_FILE}" ]]; then
    echo "Creating ${ENV_FILE} from ${EXAMPLE_FILE}..."
    cp "${EXAMPLE_FILE}" "${ENV_FILE}"
  else
    echo "Error: Missing ${EXAMPLE_FILE}. Cannot initialize environment." >&2
    exit 1
  fi
else
  echo "${ENV_FILE} already exists. Proceeding to update..."
fi

# ------------------------------------------------------------------
# Step 2: Loop through the list and inject values if they exist
# ------------------------------------------------------------------
echo "Checking environment variables for injection..."

for VAR_NAME in "${VARS_TO_INJECT[@]}"; do
  # Use indirect expansion to get the value of the variable name stored in VAR_NAME
  # e.g., if VAR_NAME is "ALPACA_API_KEY", this gets the value of $ALPACA_API_KEY
  CURRENT_VALUE="${!VAR_NAME:-}"

  if [[ -n "$CURRENT_VALUE" ]]; then
    echo " -> Found value for ${VAR_NAME}, injecting..."

    # Check if the variable already exists in the file (to decide replace vs append)
    if grep -q "^${VAR_NAME}=" "${ENV_FILE}"; then
      # Update existing line
      # We use '|' as delimiter to handle URLs safely (e.g., http://...)
      sed -i "s|^${VAR_NAME}=.*|${VAR_NAME}=${CURRENT_VALUE}|" "${ENV_FILE}"
    else
      # Append new line if it doesn't exist in the example file
      # Ensure there is a newline before appending
      echo "" >> "${ENV_FILE}"
      echo "${VAR_NAME}=${CURRENT_VALUE}" >> "${ENV_FILE}"
    fi
  fi
done

echo "Environment initialization complete."
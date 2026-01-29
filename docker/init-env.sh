#!/usr/bin/env bash
# Enable debug mode (prints commands) to see exactly where it fails, if it does.
set -x

# ==============================================================================
# 1. CONFIGURATION
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
configure_env_file() {
  local TARGET_FILE="$1"
  local EXAMPLE_FILE="$2"

  echo "----------------------------------------------------------------"
  echo "Processing: ${TARGET_FILE}"

  # --- Step A: Create file if missing ---
  if [[ ! -f "${TARGET_FILE}" ]]; then
    if [[ -f "${EXAMPLE_FILE}" ]]; then
      echo " -> Creating from ${EXAMPLE_FILE}..."
      cp "${EXAMPLE_FILE}" "${TARGET_FILE}"
    else
      echo " -> Error: Example file ${EXAMPLE_FILE} missing. Skipping." >&2
      # Return 1 to signal failure, but since we removed 'set -e', script continues.
      return 1 
    fi
  else
    echo " -> File already exists."
  fi

  # --- Step B: Inject Secrets ---
  echo " -> Checking for secrets to inject..."
  local injected_count=0

  for VAR_NAME in "${VARS_TO_INJECT[@]}"; do
    # 1. Safe Variable Expansion (Pure Bash)
    # ${!VAR_NAME} gets the value of the variable named by VAR_NAME.
    # If the variable is unset, it returns an empty string (no error).
    local VAL="${!VAR_NAME}"

    if [[ -n "$VAL" ]]; then
      # 2. Escape special characters for sed
      # We replace '|' with '\|' to prevent breaking the sed command delimiter.
      local ESCAPED_VAL="${VAL//|/\\|}"

      # 3. Check if key exists in the file (grep returns 0 if found, 1 if not)
      if grep -q "^${VAR_NAME}=" "${TARGET_FILE}"; then
        # UPDATE: Found key, perform substitution
        # We ignore sed exit code in case of weird permission issues, but usually it works.
        sed -i "s|^${VAR_NAME}=.*|${VAR_NAME}=${ESCAPED_VAL}|" "${TARGET_FILE}"
      else
        # APPEND: Key not found, append to end of file
        # Check if file ends with a newline character. If not, add one.
        # 'tail -c1' gets last byte. We use '|| true' to prevent any possible crash.
        if [ -s "${TARGET_FILE}" ]; then
           local LAST_CHAR
           LAST_CHAR=$(tail -c1 "${TARGET_FILE}" || true)
           if [ -n "$LAST_CHAR" ]; then
             echo "" >> "${TARGET_FILE}"
           fi
        fi
        echo "${VAR_NAME}=${VAL}" >> "${TARGET_FILE}"
      fi
      ((injected_count++))
    fi
  done

  echo " -> Injected ${injected_count} secrets."
}

# ==============================================================================
# 3. EXECUTION
# ==============================================================================

# Configure Development Environment
configure_env_file "docker/.env.dev" "docker/example.env.dev"

# Configure Production Environment (Only if example exists)
if [[ -f "docker/example.env" ]]; then
    configure_env_file "docker/.env" "docker/example.env"
fi

echo "----------------------------------------------------------------"
echo "Initialization complete."
# Explicitly exit with success
exit 0
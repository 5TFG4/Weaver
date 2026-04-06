#!/usr/bin/env bash
set -euo pipefail
# Compose smoke test — single source of truth for compose-smoke.yml and local runs.
# Builds the production stack, starts it, health-checks, tears down.
# Auto-detects if running inside a container (dev container) and adapts health
# check strategy accordingly.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"
REAL_ENV_FILE="$ROOT_DIR/docker/.env"
EXAMPLE_ENV="$ROOT_DIR/docker/example.env"
TIMEOUT_SECONDS=120
: "${COMPOSE_PROJECT_NAME:=weaver_smoke}"

# Use a temporary env file so we never overwrite the real .env
SMOKE_ENV="$(mktemp)"
cp "$EXAMPLE_ENV" "$SMOKE_ENV"
COMPOSE=(docker compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$SMOKE_ENV")

_in_container() { [[ -f /.dockerenv ]]; }

CONNECTED_NETWORK=""

teardown() {
    if [[ -n "$CONNECTED_NETWORK" ]]; then
        docker network disconnect "$CONNECTED_NETWORK" "$(hostname)" 2>/dev/null || true
    fi
    "${COMPOSE[@]}" down -v 2>/dev/null || true
    docker image prune -f 2>/dev/null || true
    rm -f "$SMOKE_ENV"
}
trap teardown EXIT

# --- Prepare env ---
for key in ALPACA_LIVE_API_KEY ALPACA_LIVE_API_SECRET ALPACA_PAPER_API_KEY ALPACA_PAPER_API_SECRET; do
    sed -i "s|^${key}=.*|${key}=|" "$SMOKE_ENV"
done

# Use unique ports so smoke tests don't collide with running dev/prod stacks
sed -i "s|^HOST_PORT_PROD=.*|HOST_PORT_PROD=48919|"       "$SMOKE_ENV"
sed -i "s|^FRONTEND_PORT_PROD=.*|FRONTEND_PORT_PROD=43579|" "$SMOKE_ENV"
sed -i "s|^POSTGRES_PORT_PROD=.*|POSTGRES_PORT_PROD=45432|" "$SMOKE_ENV"

# --- Build & start ---
"${COMPOSE[@]}" config > /dev/null
"${COMPOSE[@]}" build backend frontend
"${COMPOSE[@]}" up -d db
"${COMPOSE[@]}" run --rm backend alembic upgrade head
"${COMPOSE[@]}" up -d backend frontend

# --- Determine health-check URLs ---
if _in_container; then
    # Inside a container: connect to the smoke network, use container names
    CONNECTED_NETWORK="${COMPOSE_PROJECT_NAME}_default"
    docker network connect "$CONNECTED_NETWORK" "$(hostname)" 2>/dev/null || true
    API_URL="http://${COMPOSE_PROJECT_NAME}-backend-1:8000/api/v1/healthz"
    FRONT_URL="http://${COMPOSE_PROJECT_NAME}-frontend-1:80/"
else
    # Bare host (GitHub Actions): use mapped ports on localhost
    raw_backend="$("${COMPOSE[@]}" port --index 1 backend 8000)"
    BACKEND_PORT="${raw_backend##*:}"
    raw_frontend="$("${COMPOSE[@]}" port --index 1 frontend 80)"
    FRONTEND_PORT="${raw_frontend##*:}"
    API_URL="http://127.0.0.1:${BACKEND_PORT}/api/v1/healthz"
    FRONT_URL="http://127.0.0.1:${FRONTEND_PORT}/"
fi

# --- Health checks ---
wait_200() {
    local name="$1" url="$2"
    local attempts=$((TIMEOUT_SECONDS / 2))
    for i in $(seq 1 "$attempts"); do
        code="$(curl -sS -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || true)"
        if [[ "$code" == "200" ]]; then
            echo "$name healthy (try $i)"
            return 0
        fi
        sleep 2
    done
    echo "$name health check FAILED at $url"
    "${COMPOSE[@]}" logs --tail=100 backend db frontend
    return 1
}

wait_200 "API" "$API_URL"
wait_200 "Frontend" "$FRONT_URL"
echo "SMOKE OK"

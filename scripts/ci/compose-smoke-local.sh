#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"
ENV_FILE="$ROOT_DIR/docker/.env"
EXAMPLE_ENV_FILE="$ROOT_DIR/docker/example.env"

KEEP_UP=0
NO_BUILD=0
TIMEOUT_SECONDS=120

usage() {
  cat <<'USAGE'
Run local compose smoke flow aligned with .github/workflows/compose-smoke.yml.

Usage:
  scripts/ci/compose-smoke-local.sh [options]

Options:
  --keep-up           Keep backend/frontend/db running after successful smoke.
  --no-build          Skip image build step.
  --timeout <seconds> Health check timeout per service (default: 120).
  -h, --help          Show this help message.

Environment:
  COMPOSE_PROJECT_NAME   Optional project name override for docker compose
                         (default: weaver_smoke).
USAGE
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-up)
      KEEP_UP=1
      shift
      ;;
    --no-build)
      NO_BUILD=1
      shift
      ;;
    --timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required"
  exit 1
fi

: "${COMPOSE_PROJECT_NAME:=weaver_smoke}"
COMPOSE_ARGS=(-p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE")

teardown() {
  if [[ "$KEEP_UP" -eq 0 ]]; then
    log "Teardown compose stack"
    docker compose "${COMPOSE_ARGS[@]}" down -v || true
  fi
}
trap teardown EXIT

log "Prepare compose env"
cp "$EXAMPLE_ENV_FILE" "$ENV_FILE"
sed -i 's|^ALPACA_LIVE_API_KEY=.*|ALPACA_LIVE_API_KEY=|' "$ENV_FILE"
sed -i 's|^ALPACA_LIVE_API_SECRET=.*|ALPACA_LIVE_API_SECRET=|' "$ENV_FILE"
sed -i 's|^ALPACA_PAPER_API_KEY=.*|ALPACA_PAPER_API_KEY=|' "$ENV_FILE"
sed -i 's|^ALPACA_PAPER_API_SECRET=.*|ALPACA_PAPER_API_SECRET=|' "$ENV_FILE"

log "Validate compose config"
docker compose "${COMPOSE_ARGS[@]}" config

if [[ "$NO_BUILD" -eq 0 ]]; then
  log "Build backend/frontend images"
  docker compose "${COMPOSE_ARGS[@]}" build backend frontend
else
  log "Skip build (requested)"
fi

log "Start database"
docker compose "${COMPOSE_ARGS[@]}" up -d db

log "Run DB migrations"
docker compose "${COMPOSE_ARGS[@]}" run --rm backend alembic upgrade head

log "Start app services"
docker compose "${COMPOSE_ARGS[@]}" up -d backend frontend

raw_backend_port="$(docker compose "${COMPOSE_ARGS[@]}" port --index 1 backend 8000)"
HOST_PORT_PROD="${raw_backend_port##*:}"
if [[ ! "$HOST_PORT_PROD" =~ ^[0-9]+$ ]]; then
  echo "Invalid backend host port: $raw_backend_port"
  exit 1
fi

raw_frontend_port="$(docker compose "${COMPOSE_ARGS[@]}" port --index 1 frontend 80)"
FRONTEND_PORT_PROD="${raw_frontend_port##*:}"
if [[ ! "$FRONTEND_PORT_PROD" =~ ^[0-9]+$ ]]; then
  echo "Invalid frontend host port: $raw_frontend_port"
  exit 1
fi

wait_http_200() {
  local name="$1"
  local url="$2"
  local out_file="$3"
  local attempts=$((TIMEOUT_SECONDS / 2))

  for i in $(seq 1 "$attempts"); do
    local code
    code="$(curl -sS -o "$out_file" -w "%{http_code}" "$url" || true)"
    echo "$name try=$i code=$code"
    if [[ "$code" == "200" ]]; then
      return 0
    fi
    sleep 2
  done
  return 1
}

log "Wait for API health"
if ! wait_http_200 "api" "http://127.0.0.1:${HOST_PORT_PROD}/api/v1/healthz" /tmp/weaver_api_smoke.out; then
  echo "API health check failed"
  docker compose "${COMPOSE_ARGS[@]}" logs --tail=200 backend db
  exit 1
fi

log "Wait for frontend"
if ! wait_http_200 "front" "http://127.0.0.1:${FRONTEND_PORT_PROD}/" /tmp/weaver_front_smoke.out; then
  echo "Frontend smoke check failed"
  docker compose "${COMPOSE_ARGS[@]}" logs --tail=200 frontend
  exit 1
fi

log "SMOKE_OK"
cat /tmp/weaver_api_smoke.out
head -n 5 /tmp/weaver_front_smoke.out

if [[ "$KEEP_UP" -eq 1 ]]; then
  log "Keep-up enabled; stack left running for inspection (project: $COMPOSE_PROJECT_NAME)"
fi

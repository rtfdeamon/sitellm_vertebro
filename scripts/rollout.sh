#!/usr/bin/env bash

# Idempotent, non-interactive rollout for the target server.
# - Updates the repo to the latest main
# - Rebuilds images and restarts the stack via docker compose
# - Verifies health of the app service
#
# Prereqs on the server:
#   - git, docker, docker compose
#   - .env prepared once (e.g., via deploy_project.sh)

set -euo pipefail

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

APP_DIR=${APP_DIR:-$(pwd)}
BRANCH=${BRANCH:-main}
# Auto-detect whether sudo is required for docker
if [ -z "${DOCKER_BIN:-}" ]; then
  if docker info >/dev/null 2>&1; then
    DOCKER_BIN=docker
  else
    DOCKER_BIN="sudo docker"
  fi
fi

cd "$APP_DIR"

if [ ! -f "compose.yaml" ] && [ ! -f "docker-compose.yml" ]; then
  echo "[!] compose.yaml or docker-compose.yml not found in $APP_DIR"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "[!] .env not found in $APP_DIR (run initial provisioning first)"
  exit 1
fi

# Compose command (GPU override if USE_GPU=true and compose.gpu.yaml present)
COMPOSE_FILES=(-f compose.yaml)
if [ -f compose.gpu.yaml ]; then
  if grep -q '^USE_GPU=\(true\|1\|yes\)$' .env 2>/dev/null || [ "${USE_GPU:-}" = "true" ] || [ "${USE_GPU:-}" = "1" ]; then
    COMPOSE_FILES+=(-f compose.gpu.yaml)
    echo "[+] GPU override enabled (compose.gpu.yaml)"
  fi
fi
COMPOSE_CMD=("${DOCKER_BIN}" compose "${COMPOSE_FILES[@]}")

printf '[+] Updating git checkout (%s) ...\n' "$BRANCH"
if [ -d .git ]; then
  git fetch --all --prune
  git checkout "$BRANCH"
  git reset --hard "origin/${BRANCH}"
else
  echo "[!] Current directory is not a git repo. Skipping git update."
fi

printf '[+] Building images (with cache refresh) ...\n'
"${COMPOSE_CMD[@]}" pull || true
"${COMPOSE_CMD[@]}" build --pull

printf '[+] Stopping running stack (if any) ...\n'
"${COMPOSE_CMD[@]}" down --remove-orphans || true

printf '[+] Applying stack ...\n'
"${COMPOSE_CMD[@]}" up -d --remove-orphans

printf '[+] Waiting for API health ...\n'
# Resolve exposed port for app:8000 and probe health endpoints
APP_PORT=$("${COMPOSE_CMD[@]}" port app 8000 | awk -F: '{print $2}')
if [ -z "${APP_PORT}" ]; then
  echo "[!] Could not resolve app:8000 published port"
  exit 1
fi

ok=""
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/healthz" >/dev/null || \
     curl -fsS "http://127.0.0.1:${APP_PORT}/health" >/dev/null || \
     curl -fsS "http://127.0.0.1:${APP_PORT}/" >/dev/null; then
    ok=1
    break
  fi
  sleep 3
done

if [ -z "$ok" ]; then
  echo "[!] Health check failed"
  exit 1
fi

echo "[✓] Rollout complete"

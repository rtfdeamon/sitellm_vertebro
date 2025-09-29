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

PRESERVE_STATEFUL_SERVICES=0

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

update_env_var() {
  local key="$1" val="$2"
  local esc_val
  esc_val=$(printf '%s' "$val" | sed 's/[\\/&]/\\&/g')
  if grep -q "^${key}=" .env 2>/dev/null; then
    if sed --version >/dev/null 2>&1; then
      sed -i -e "s/^${key}=.*/${key}=${esc_val}/" .env
    else
      sed -i '' -e "s/^${key}=.*/${key}=${esc_val}/" .env
    fi
  else
    echo "${key}=${val}" >> .env
  fi
}

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

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python)
else
  echo "[!] python3 (or python) is required to compute component versions"
  exit 1
fi

VERSION_OUTPUT=$("$PYTHON_BIN" scripts/update_versions.py --versions-file versions.json --format shell)
if [ -z "$VERSION_OUTPUT" ]; then
  echo "[!] Failed to compute component versions"
  exit 1
fi
eval "$VERSION_OUTPUT"
: "${BACKEND_VERSION:=1}"
: "${TELEGRAM_VERSION:=1}"
: "${STATEFUL_VERSION:=1}"

stateful_changed=0
for component in $CHANGED_COMPONENTS; do
  if [ "$component" = "stateful" ]; then
    stateful_changed=1
    break
  fi
done

if [ "$stateful_changed" -eq 0 ]; then
  PRESERVE_STATEFUL_SERVICES=1
  echo '[i] No stateful changes detected; Mongo/Redis/Qdrant will remain running'
fi

update_env_var BACKEND_VERSION "$BACKEND_VERSION"
update_env_var TELEGRAM_VERSION "$TELEGRAM_VERSION"
update_env_var STATEFUL_VERSION "$STATEFUL_VERSION"
printf '[i] Component versions: backend=%s telegram=%s stateful=%s\n' "$BACKEND_VERSION" "$TELEGRAM_VERSION" "$STATEFUL_VERSION"

printf '[+] Building images (with cache refresh) ...\n'
"${COMPOSE_CMD[@]}" pull || true
"${COMPOSE_CMD[@]}" build --pull

printf '[+] Stopping running stack (if any) ...\n'
if [ "${PRESERVE_STATEFUL_SERVICES}" = "1" ]; then
  echo '[i] Skipping docker compose down to preserve databases'
else
  stop_timeout=${ROLLING_STOP_TIMEOUT:-45}
  echo "[i] Stopping services with timeout ${stop_timeout}s"
  "${COMPOSE_CMD[@]}" stop --timeout "${stop_timeout}" || true
  end_ts=$(( $(date +%s) + stop_timeout ))
  running_services=""
  while [ "$(date +%s)" -lt "${end_ts}" ]; do
    running_services=$("${COMPOSE_CMD[@]}" ps --services --status=running 2>/dev/null | tr '\n' ' ')
    if [ -z "${running_services// }" ]; then
      running_services=""
      break
    fi
    sleep 2
  done
  if [ -n "${running_services// }" ]; then
    echo "[i] Services still stopping: ${running_services}" 
  else
    echo '[✓] All services stopped gracefully'
  fi
  "${COMPOSE_CMD[@]}" rm -f || true
fi

if [ "${PRESERVE_STATEFUL_SERVICES}" = "1" ]; then
  mapfile -t active_services < <("${COMPOSE_CMD[@]}" ps --services 2>/dev/null || true)
  recreate_targets=()
  for svc in "${active_services[@]}"; do
    case "$svc" in
      mongo|redis|qdrant|"" )
        continue
        ;;
      *)
        recreate_targets+=("$svc")
        ;;
    esac
  done
  if [ ${#recreate_targets[@]} -gt 0 ]; then
    echo "[i] Forcing stateless service refresh: ${recreate_targets[*]}"
    "${COMPOSE_CMD[@]}" up -d --force-recreate "${recreate_targets[@]}"
  fi
fi

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

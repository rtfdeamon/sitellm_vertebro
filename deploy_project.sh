#!/usr/bin/env bash

# ---------------------------------------------------------------------------
# deploy_project.sh — One-shot bootstrap script for sitellm_vertebro
# ---------------------------------------------------------------------------
# Collects configuration, writes ``.env``, builds and runs Docker containers,
# performs an initial crawl and schedules a nightly crawl via systemd.
#
# Usage:
#   chmod +x deploy_project.sh && ./deploy_project.sh
# ---------------------------------------------------------------------------

set -euo pipefail

PRESERVE_STATEFUL_SERVICES=0

# Allow ports (notably the default 18000/18001 pair) a short grace period to
# be released by Docker before we pick an alternative.
PORT_REUSE_GRACE_SECONDS="${PORT_REUSE_GRACE_SECONDS:-6}"
PORT_REUSE_POLL_INTERVAL="${PORT_REUSE_POLL_INTERVAL:-1}"

# Enable Docker BuildKit for faster image builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

printf '[+] Checking requirements...\n'
if ! command -v docker >/dev/null 2>&1; then
  echo '[!] docker not found'; exit 1
fi
if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
  echo '[!] docker compose not found'; exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
  echo '[!] openssl not found'; exit 1
fi
printf '[✓] All required tools installed\n'

# Open firewall ports for external access
open_firewall_ports() {
  # Defaults
  local open_app_port=${OPEN_APP_PORT:-1}
  local open_http=${OPEN_HTTP:-0}
  local open_https=${OPEN_HTTPS:-0}

  # If DOMAIN provided, also open 80/443 by default
  if [ -n "${DOMAIN:-}" ]; then
    [ -z "${OPEN_HTTP:-}" ] && open_http=1
    [ -z "${OPEN_HTTPS:-}" ] && open_https=1
  fi

  # Resolve external app port from .env (fallbacks), tolerate missing file
  local app_port="18000"
  if [ -f .env ]; then
    local v
    v=$(awk -F= '/^HOST_APP_PORT=/{print $2}' .env 2>/dev/null | tail -n1 || true)
    if [ -n "$v" ]; then app_port="$v"; fi
  fi

  # UFW
  if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -qi active; then
      [ "$open_app_port" = "1" ] && sudo ufw allow "${app_port}/tcp" || true
      [ "$open_http" = "1" ] && sudo ufw allow 80/tcp || true
      [ "$open_https" = "1" ] && sudo ufw allow 443/tcp || true
      return
    fi
  fi

  # firewalld
  if command -v firewall-cmd >/dev/null 2>&1 && sudo firewall-cmd --state >/dev/null 2>&1; then
    [ "$open_app_port" = "1" ] && sudo firewall-cmd --permanent --add-port="${app_port}/tcp" || true
    [ "$open_http" = "1" ] && sudo firewall-cmd --permanent --add-service=http || true
    [ "$open_https" = "1" ] && sudo firewall-cmd --permanent --add-service=https || true
    sudo firewall-cmd --reload || true
  fi
}

is_port_free() {
  local p="$1"
  # try ss first, fallback to lsof
  if command -v ss >/dev/null 2>&1; then
    if ss -lnt 2>/dev/null | awk 'NR>1 {print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | grep -qx "$p"; then
      return 1
    fi
  elif command -v lsof >/dev/null 2>&1; then
    if lsof -iTCP:"$p" -sTCP:LISTEN -P -n >/dev/null 2>&1; then
      return 1
    fi
  fi

  # Fall back to an actual bind test so we do not pick a port that is busy but
  # hidden from ss/lsof (e.g. docker-proxy without root or missing tools).
  local py_cmd=""
  if command -v python3 >/dev/null 2>&1; then
    py_cmd="python3"
  elif command -v python >/dev/null 2>&1; then
    py_cmd="python"
  fi

  if [ -n "$py_cmd" ]; then
    if ! "$py_cmd" - "$p" <<'PY' >/dev/null 2>&1; then
import socket
import sys

port = int(sys.argv[1])

def can_bind(sock_family, address):
    sock = socket.socket(sock_family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "IPPROTO_IPV6") and hasattr(socket, "IPV6_V6ONLY") \
                and sock_family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.bind(address)
    except OSError:
        return False
    finally:
        sock.close()
    return True

if not can_bind(socket.AF_INET, ("0.0.0.0", port)):
    sys.exit(1)

if socket.has_ipv6:
    if not can_bind(socket.AF_INET6, ("::", port)):
        sys.exit(1)
PY
      return 1
    fi
  fi
  return 0
}

wait_for_port_release() {
  local port="$1"
  local timeout="$PORT_REUSE_GRACE_SECONDS"
  local interval="$PORT_REUSE_POLL_INTERVAL"

  if ! [[ "$timeout" =~ ^[0-9]+$ ]] || [ "$timeout" -le 0 ]; then
    return 1
  fi

  if ! [[ "$interval" =~ ^[0-9]+$ ]] || [ "$interval" -le 0 ]; then
    interval=1
  fi

  local end_ts=$(( $(date +%s) + timeout ))
  local announced=0

  while [ "$(date +%s)" -lt "$end_ts" ]; do
    if is_port_free "$port"; then
      return 0
    fi
    if [ "$announced" -eq 0 ]; then
      printf '[i] Waiting up to %ss for port %s to be released...\n' "$timeout" "$port"
      announced=1
    fi
    sleep "$interval"
  done

  # Give it one last check before returning failure
  if is_port_free "$port"; then
    return 0
  fi
  return 1
}

wait_until_port_free() {
  local port="$1"
  local timeout="${2:-15}"
  local interval="${3:-1}"
  if ! [[ "$timeout" =~ ^[0-9]+$ ]] || [ "$timeout" -le 0 ]; then
    timeout=5
  fi
  if ! [[ "$interval" =~ ^[0-9]+$ ]] || [ "$interval" -le 0 ]; then
    interval=1
  fi
  local end_ts=$(( $(date +%s) + timeout ))
  while [ "$(date +%s)" -lt "$end_ts" ]; do
    if is_port_free "$port"; then
      return 0
    fi
    sleep "$interval"
  done
  if is_port_free "$port"; then
    return 0
  fi
  return 1
}

listening_pids_for_port() {
  local port="$1"
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti TCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u)
    if [ -z "$pids" ] && command -v sudo >/dev/null 2>&1; then
      pids=$(sudo -n lsof -ti TCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u || true)
    fi
  fi
  if [ -z "$pids" ] && command -v fuser >/dev/null 2>&1; then
    pids=$(fuser -n tcp "$port" 2>/dev/null | tr -s ' ' '\n' | sort -u)
    if [ -z "$pids" ] && command -v sudo >/dev/null 2>&1; then
      pids=$(sudo -n fuser -n tcp "$port" 2>/dev/null | tr -s ' ' '\n' | sort -u || true)
    fi
  fi
  if [ -z "$pids" ] && command -v ss >/dev/null 2>&1; then
    pids=$(ss -lntp 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)
  fi
  if [ -n "$pids" ]; then
    pids=$(printf '%s\n' "$pids" | tr ' ' '\n' | grep -E '^[0-9]+$' || true)
    pids=$(printf '%s\n' "$pids" | sed '/^$/d' | sort -u)
  fi
  echo "$pids"
}

terminate_port_processes() {
  local port="$1"
  local grace="${2:-12}"
  if is_port_free "$port"; then
    return 0
  fi
  local pids
  pids=$(listening_pids_for_port "$port")
  if [ -z "$pids" ]; then
    printf '[!] Port %s is busy but owning process could not be determined.\n' "$port"
    return 1
  fi
  printf '[!] Port %s is currently in use by PID(s): %s\n' "$port" "$pids"
  printf '[+] Waiting up to %s seconds for the owning process to release the port...\n' "$grace"
  if wait_until_port_free "$port" "$grace" 1; then
    printf '[✓] Port %s released without forcing termination.\n' "$port"
    return 0
  fi
  printf '[✗] Port %s is still busy. Attempting graceful termination of PID(s): %s\n' "$port" "$pids"
  local pid
  for pid in $pids; do
    if kill "$pid" 2>/dev/null; then
      printf '[i] Sent SIGTERM to %s\n' "$pid"
    fi
  done
  if wait_until_port_free "$port" 6; then
    printf '[✓] Port %s freed after terminating PID(s).\n' "$port"
    return 0
  fi
  printf '[!] Forcing termination with SIGKILL\n'
  for pid in $pids; do
    if kill -9 "$pid" 2>/dev/null; then
      printf '[i] Sent SIGKILL to %s\n' "$pid"
    fi
  done
  if wait_until_port_free "$port" 6; then
    printf '[✓] Port %s freed after SIGKILL.\n' "$port"
    return 0
  fi
  printf '[✗] Port %s is still busy. Stop conflicting service and rerun.\n' "$port"
  return 1
}

pick_free_port() {
  local start="$1"; local max_scan=100; local p="$start"
  wait_for_port_release "$start" >/dev/null 2>&1 || true
  for _ in $(seq 1 "$max_scan"); do
    if is_port_free "$p"; then echo "$p"; return; fi
    p=$((p+1))
  done
  echo "$start"
}

ensure_nvidia_toolkit() {
  if docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q 'nvidia'; then
    echo '[✓] NVIDIA runtime already configured in Docker'
    return
  fi
  echo '[+] Installing NVIDIA Container Toolkit (Debian/Ubuntu)'
  if [ -r /etc/os-release ]; then . /etc/os-release; fi
  case "${ID:-}" in
    ubuntu|debian)
      set -e
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -y
      apt-get install -y curl gnupg ca-certificates
      distribution=$(. /etc/os-release; echo ${ID}${VERSION_ID})
      install -m 0755 -d /etc/apt/keyrings
      curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        gpg --dearmor -o /etc/apt/keyrings/nvidia-container-toolkit.gpg
      chmod a+r /etc/apt/keyrings/nvidia-container-toolkit.gpg
      curl -fsSL https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.gpg] https://#g' \
        > /etc/apt/sources.list.d/nvidia-container-toolkit.list
      apt-get update -y
      apt-get install -y nvidia-container-toolkit
      nvidia-ctk runtime configure --runtime=docker || true
      systemctl restart docker || true
      ;;
    *)
      echo '[!] Unsupported distro for automatic NVIDIA toolkit install; install manually'
      ;;
  esac
}

cleanup_previous_stack() {
  local compose_args=(-f compose.yaml)
  if [ -f compose.gpu.yaml ]; then
    compose_args+=(-f compose.gpu.yaml)
  fi

  if docker compose "${compose_args[@]}" ps >/dev/null 2>&1; then
    if [ "${PRESERVE_STATEFUL_SERVICES}" = "1" ]; then
      echo '[i] No stateful changes detected; keeping mongo/redis/qdrant running'
    else
      echo '[+] Removing previous containers (if any)...'
      if ! docker compose "${compose_args[@]}" down --remove-orphans >/dev/null 2>&1; then
        echo '[i] docker compose down reported an error; continuing'
      fi
    fi
  fi

  if [ "${PRESERVE_STATEFUL_SERVICES}" != "1" ] && docker network inspect sitellm_vertebro_default >/dev/null 2>&1; then
    echo '[+] Removing stale network sitellm_vertebro_default'
    if ! docker network rm sitellm_vertebro_default >/dev/null 2>&1; then
      echo '[i] Failed to remove network sitellm_vertebro_default; continuing'
    fi
  fi
}

verify_mongo_connection() {
  local attempts="${1:-10}"
  for i in $(seq 1 "$attempts"); do
    if "${COMPOSE_CMD[@]}" exec -T mongo mongosh "${MONGO_URI}" --quiet --eval 'db.runCommand({ping: 1})' >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

AUTO_YES=0
if [ "${1-}" = "--yes" ]; then
  AUTO_YES=1
fi

get_env_var() {
  # Temporarily disable -e because missing keys are expected.
  set +e
  local value
  value=$(grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d= -f2-)
  local status=$?
  set -e
  if [ $status -ne 0 ]; then
    return 0
  fi
  printf '%s' "$value"
}

if [ -z "${DOMAIN:-}" ]; then
  DOMAIN=$(get_env_var DOMAIN)
fi

if [ -z "${CRAWL_START_URL:-}" ]; then
  CRAWL_START_URL=$(get_env_var CRAWL_START_URL)
fi
if [ -z "${CRAWL_START_URL:-}" ] && [ -n "${DOMAIN}" ]; then
  CRAWL_START_URL="https://${DOMAIN}"
fi
export CRAWL_START_URL

if [ -z "${ENABLE_INITIAL_CRAWL:-}" ]; then
  ENABLE_INITIAL_CRAWL=$(get_env_var ENABLE_INITIAL_CRAWL)
fi
case "${ENABLE_INITIAL_CRAWL:-}" in
  1|true|TRUE|yes|YES)
    ENABLE_INITIAL_CRAWL="1"
    ;;
  *)
    ENABLE_INITIAL_CRAWL="0"
    ;;
esac
export ENABLE_INITIAL_CRAWL

slugify_project() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/-/g' | sed 's/-\{2,\}/-/g' | sed 's/^-//; s/-$//'
}

if [ -z "${PROJECT_NAME:-}" ]; then
  PROJECT_NAME=$(get_env_var PROJECT_NAME)
fi
if [ -z "${PROJECT_NAME:-}" ]; then
  if [ -n "${DOMAIN}" ]; then
    PROJECT_NAME=$(slugify_project "${DOMAIN}")
  fi
fi
: "${PROJECT_NAME:=default}"
PROJECT_NAME=$(slugify_project "${PROJECT_NAME}")
export PROJECT_NAME

# Reuse existing Mongo credentials if present, otherwise apply deterministic defaults

if [ -z "${MONGO_HOST:-}" ]; then
  MONGO_HOST=$(get_env_var MONGO_HOST)
  MONGO_HOST=${MONGO_HOST:-mongo}
fi
if [ -z "${MONGO_PORT:-}" ]; then
  MONGO_PORT=$(get_env_var MONGO_PORT)
  MONGO_PORT=${MONGO_PORT:-27017}
fi
if [ -z "${MONGO_USERNAME:-}" ]; then
  MONGO_USERNAME=$(get_env_var MONGO_USERNAME)
  MONGO_USERNAME=${MONGO_USERNAME:-root}
fi
if [ -z "${MONGO_PASSWORD:-}" ]; then
  MONGO_PASSWORD=$(get_env_var MONGO_PASSWORD)
  # Generate secure password if not provided
  if [ -z "$MONGO_PASSWORD" ]; then
    MONGO_PASSWORD=$(openssl rand -hex 16)
    echo "[+] Generated secure MongoDB password"
  fi
fi
if [ -z "${MONGO_DATABASE:-}" ]; then
  MONGO_DATABASE=$(get_env_var MONGO_DATABASE)
  MONGO_DATABASE=${MONGO_DATABASE:-smarthelperdb}
fi
if [ -z "${MONGO_AUTH:-}" ]; then
  MONGO_AUTH=$(get_env_var MONGO_AUTH)
  MONGO_AUTH=${MONGO_AUTH:-admin}
fi
export MONGO_USERNAME
export MONGO_PASSWORD
export MONGO_HOST
export MONGO_PORT
export MONGO_DATABASE
export MONGO_AUTH

USE_GPU=false

# (Firewall ports will be opened later, after .env is created)

if [ -z "${REDIS_PASS:-}" ]; then
  REDIS_PASS=$(get_env_var REDIS_PASSWORD)
fi
if [ -z "${REDIS_PASS:-}" ]; then
  REDIS_PASS=$(openssl rand -hex 8)
fi
if [ -z "${GRAFANA_PASS:-}" ]; then
  GRAFANA_PASS=$(get_env_var GRAFANA_PASSWORD)
fi
if [ -z "${GRAFANA_PASS:-}" ]; then
  GRAFANA_PASS=$(openssl rand -hex 8)
fi

REDIS_URL="redis://:${REDIS_PASS}@redis:6379/0"
QDRANT_URL="http://qdrant:6333"

detect_arch() {
  uname -m
}

case "$(detect_arch)" in
  arm64|aarch64)
    QDRANT_PLATFORM="linux/arm64"
    ;;
  x86_64|amd64)
    QDRANT_PLATFORM="linux/amd64"
    ;;
  *)
    QDRANT_PLATFORM=""
    ;;
esac

ENV_FILE_EXISTS=0
if [ -f .env ]; then
  ENV_FILE_EXISTS=1
  printf '[i] Existing .env detected — leaving configuration untouched.\n'
else
  touch .env
fi
update_env_var() {
  local key="$1" val="$2"
  local esc_val
  export "$key=$val"
  if [ "$ENV_FILE_EXISTS" -eq 1 ]; then
    return 0
  fi
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

ensure_self_signed_cert() {
  local target_dir="certs"
  if ./scripts/generate_self_signed_cert.sh "$target_dir"; then
    update_env_var APP_SSL_CERT "/certs/server.crt"
    update_env_var APP_SSL_KEY "/certs/server.key"
  else
    echo '[!] Failed to prepare self-signed TLS certificate'
  fi
}

update_env_var DOMAIN "$DOMAIN"
update_env_var CRAWL_START_URL "$CRAWL_START_URL"
update_env_var ENABLE_INITIAL_CRAWL "$ENABLE_INITIAL_CRAWL"
update_env_var PROJECT_NAME "$PROJECT_NAME"
update_env_var REDIS_PASSWORD "$REDIS_PASS"
update_env_var REDIS_URL "$REDIS_URL"
update_env_var CELERY_BROKER "$REDIS_URL"
update_env_var CELERY_RESULT "$REDIS_URL"
update_env_var QDRANT_URL "$QDRANT_URL"
if [ -n "$QDRANT_PLATFORM" ]; then
  update_env_var QDRANT_PLATFORM "$QDRANT_PLATFORM"
fi
update_env_var QDRANT_COLLECTION "documents"
update_env_var EMB_MODEL_NAME "deepvk/USER-bge-m3"
update_env_var RERANK_MODEL_NAME "DiTy/cross-encoder-russian-msmarco"
update_env_var MONGO_HOST "$MONGO_HOST"
update_env_var MONGO_PORT "$MONGO_PORT"
update_env_var MONGO_USERNAME "$MONGO_USERNAME"
update_env_var MONGO_PASSWORD "$MONGO_PASSWORD"
update_env_var MONGO_ROOT_USERNAME "$MONGO_USERNAME"
update_env_var MONGO_ROOT_PASSWORD "$MONGO_PASSWORD"
update_env_var MONGO_DATABASE "$MONGO_DATABASE"
update_env_var MONGO_AUTH "$MONGO_AUTH"
MONGO_URI="mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DATABASE}?authSource=${MONGO_AUTH}"
export MONGO_URI
update_env_var MONGO_URI "$MONGO_URI"
update_env_var USE_GPU "$USE_GPU"
update_env_var GRAFANA_PASSWORD "$GRAFANA_PASS"

APP_PORT_CANDIDATE="${HOST_APP_PORT:-}"
if [ -z "$APP_PORT_CANDIDATE" ] && [ -f .env ]; then
  APP_PORT_CANDIDATE=$(awk -F= '/^HOST_APP_PORT=/{print $2}' .env 2>/dev/null | tail -n1 || true)
fi
APP_PORT_CANDIDATE=${APP_PORT_CANDIDATE:-18000}

if ! is_port_free "$APP_PORT_CANDIDATE"; then
  printf '[!] Port %s is currently in use. Attempting to free it for the application...\n' "$APP_PORT_CANDIDATE"
  printf '[i] Port %s is busy; waiting for the existing service to stop...\n' "$APP_PORT_CANDIDATE"
  if ! wait_until_port_free "$APP_PORT_CANDIDATE" 60 2; then
    printf '[✗] Port %s is still in use after waiting. Stop the conflicting service and rerun.\n' "$APP_PORT_CANDIDATE"
    exit 1
  fi
  printf '[✓] Port %s became available.\n' "$APP_PORT_CANDIDATE"
fi

if ! wait_until_port_free "$APP_PORT_CANDIDATE" 5; then
  printf '[✗] Port %s did not become available in time.\n' "$APP_PORT_CANDIDATE"
  exit 1
fi

APP_PORT_HOST="$APP_PORT_CANDIDATE"
MONGO_PORT_HOST=$(pick_free_port "${HOST_MONGO_PORT:-27027}")
REDIS_PORT_HOST=$(pick_free_port "${HOST_REDIS_PORT:-16379}")
# Ensure HTTP/GRPC ports do not collide even if .env reuses the same value.
QDRANT_HTTP_HOST=$(pick_free_port "${HOST_QDRANT_HTTP_PORT:-16333}")

grpc_start="${HOST_QDRANT_GRPC_PORT:-}" 
if [ -z "$grpc_start" ]; then
  grpc_start=$((QDRANT_HTTP_HOST + 1))
else
  # if user configured the same port as HTTP, shift to the next available slot
  if [ "$grpc_start" = "$QDRANT_HTTP_HOST" ]; then
    grpc_start=$((grpc_start + 1))
  fi
fi

QDRANT_GRPC_HOST=$(pick_free_port "$grpc_start")

# Final sanity: never persist identical host ports
if [ "$QDRANT_GRPC_HOST" = "$QDRANT_HTTP_HOST" ]; then
  QDRANT_GRPC_HOST=$(pick_free_port "$((QDRANT_HTTP_HOST + 1))")
fi
update_env_var HOST_APP_PORT "$APP_PORT_HOST"
update_env_var HOST_MONGO_PORT "$MONGO_PORT_HOST"
update_env_var HOST_REDIS_PORT "$REDIS_PORT_HOST"
update_env_var HOST_QDRANT_HTTP_PORT "$QDRANT_HTTP_HOST"
update_env_var HOST_QDRANT_GRPC_PORT "$QDRANT_GRPC_HOST"

normalize_bool() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON)
      echo "1"
      ;;
    *)
      echo "0"
      ;;
  esac
}

RUN_LOCAL_AUTOSTART_RAW="${RUN_LOCAL_AUTOSTART_OLLAMA:-}"
if [ -z "$RUN_LOCAL_AUTOSTART_RAW" ] && [ -f .env ]; then
  RUN_LOCAL_AUTOSTART_RAW=$(awk -F= '/^RUN_LOCAL_AUTOSTART_OLLAMA=/{print $2}' .env 2>/dev/null | tail -n1 || true)
fi
AUTOSTART_LOCAL_OLLAMA=$(normalize_bool "$RUN_LOCAL_AUTOSTART_RAW")
update_env_var RUN_LOCAL_AUTOSTART_OLLAMA "$AUTOSTART_LOCAL_OLLAMA"

DEFAULT_OLLAMA_BASE_URL="http://host.docker.internal:11434"
if [ "$AUTOSTART_LOCAL_OLLAMA" = "1" ]; then
  DEFAULT_OLLAMA_BASE_URL="http://ollama:11434"
fi
update_env_var OLLAMA_BASE_URL "${OLLAMA_BASE_URL:-$DEFAULT_OLLAMA_BASE_URL}"

TLS_ENABLED_RAW=${APP_ENABLE_TLS:-}
if [ -z "$TLS_ENABLED_RAW" ] && [ -f .env ]; then
  TLS_ENABLED_RAW=$(awk -F= '/^APP_ENABLE_TLS=/{print $2}' .env 2>/dev/null | tail -n1 || true)
fi

if [ -z "$TLS_ENABLED_RAW" ]; then
  if [ -n "$DOMAIN" ]; then
    TLS_ENABLED_RAW="1"
  else
    TLS_ENABLED_RAW="0"
  fi
fi

case "$TLS_ENABLED_RAW" in
  1|true|TRUE|yes|YES)
    TLS_ENABLED_RAW="1"
    ;;
  *)
    TLS_ENABLED_RAW="0"
    ;;
esac

update_env_var APP_ENABLE_TLS "$TLS_ENABLED_RAW"
if [ "$TLS_ENABLED_RAW" = "1" ]; then
  ensure_self_signed_cert
else
  update_env_var APP_SSL_CERT ""
  update_env_var APP_SSL_KEY ""
fi

# ---------------------------------------------------------------------------
# Decide whether local LLM (llama-cpp/torch) is needed
# If an external model backend is configured (MODEL_BASE_URL) or Ollama base
# is set, disable local LLM and force CPU build to avoid NVIDIA/CUDA drivers.
# ---------------------------------------------------------------------------

# Read values back from .env (tolerate missing)
VAL_OLLAMA_BASE=$(awk -F= '/^OLLAMA_BASE_URL=/{print $2}' .env 2>/dev/null | tail -n1 || true)
VAL_MODEL_BASE=$(awk -F= '/^MODEL_BASE_URL=/{print $2}' .env 2>/dev/null | tail -n1 || true)

# Respect explicit LOCAL_LLM_ENABLED from env; otherwise derive a default.
LOCAL_LLM_ENABLED_RAW="${LOCAL_LLM_ENABLED:-}"
if [ -z "$LOCAL_LLM_ENABLED_RAW" ] && [ -f .env ]; then
  LOCAL_LLM_ENABLED_RAW=$(awk -F= '/^LOCAL_LLM_ENABLED=/{print $2}' .env 2>/dev/null | tail -n1 || true)
fi

if [ -n "$LOCAL_LLM_ENABLED_RAW" ]; then
  if [ "$(normalize_bool "$LOCAL_LLM_ENABLED_RAW")" = "1" ]; then
    LOCAL_LLM_ENABLED="true"
  else
    LOCAL_LLM_ENABLED="false"
  fi
else
  LOCAL_LLM_ENABLED="true"
  if [ -n "${VAL_MODEL_BASE}" ] || [ -n "${VAL_OLLAMA_BASE}" ]; then
    LOCAL_LLM_ENABLED="false"
  fi
fi

if [ "${LOCAL_LLM_ENABLED}" = "true" ]; then
  AUTOSTART_LOCAL_OLLAMA="1"
  update_env_var RUN_LOCAL_AUTOSTART_OLLAMA "$AUTOSTART_LOCAL_OLLAMA"
  update_env_var COMPOSE_PROFILES "local-ollama"
  if [ "$VAL_OLLAMA_BASE" != "http://ollama:11434" ]; then
    VAL_OLLAMA_BASE="http://ollama:11434"
    update_env_var OLLAMA_BASE_URL "$VAL_OLLAMA_BASE"
  fi
else
  update_env_var COMPOSE_PROFILES ""
fi

update_env_var LOCAL_LLM_ENABLED "${LOCAL_LLM_ENABLED}"
USE_GPU=false

timestamp=$(date +%Y%m%d%H%M%S)
mkdir -p deploy-backups
tar -czf "deploy-backups/${timestamp}.tar.gz" .env compose.yaml
printf '[✓] Environment saved to deploy-backups/%s.tar.gz\n' "$timestamp"

if [ "$TLS_ENABLED_RAW" = "1" ]; then
  ensure_self_signed_cert
fi

if ! grep -q "^MONGO_PASSWORD=" .env; then
  echo '[!] MONGO_PASSWORD not found in .env'; exit 1
fi
if ! grep -q "^MONGO_USERNAME=" .env; then
  echo '[!] MONGO_USERNAME not found in .env'; exit 1
fi

# Now that .env exists, open firewall ports if applicable
open_firewall_ports

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=$(command -v python)
else
  echo '[!] python3 (or python) is required to compute component versions'
  exit 1
fi

VERSION_OUTPUT=$("$PYTHON_BIN" scripts/update_versions.py --versions-file versions.json --format shell)
if [ -z "$VERSION_OUTPUT" ]; then
  echo '[!] Failed to compute component versions'
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
  echo '[i] No changes detected for stateful services; Mongo/Redis/Qdrant will remain running'
fi

cleanup_previous_stack

printf '[+] Starting containers...\n'
echo '[+] Starting project in CPU mode'

# Compose command
COMPOSE_FILES=(-f compose.yaml)
COMPOSE_CMD=(docker compose "${COMPOSE_FILES[@]}")

BACKEND_IMAGE_VALUE=$(awk -F= '/^BACKEND_IMAGE=/{print $2}' .env 2>/dev/null | tail -n1 || true)
if [ -z "$BACKEND_IMAGE_VALUE" ]; then
  BACKEND_IMAGE_VALUE="sitellm/backend"
fi
TELEGRAM_IMAGE_VALUE=$(awk -F= '/^TELEGRAM_IMAGE=/{print $2}' .env 2>/dev/null | tail -n1 || true)
if [ -z "$TELEGRAM_IMAGE_VALUE" ]; then
  TELEGRAM_IMAGE_VALUE="sitellm/telegram"
fi
update_env_var BACKEND_IMAGE "$BACKEND_IMAGE_VALUE"
update_env_var TELEGRAM_IMAGE "$TELEGRAM_IMAGE_VALUE"
update_env_var BACKEND_VERSION "$BACKEND_VERSION"
update_env_var TELEGRAM_VERSION "$TELEGRAM_VERSION"
update_env_var STATEFUL_VERSION "$STATEFUL_VERSION"
printf '[i] Component versions: backend=%s telegram=%s stateful=%s\n' "$BACKEND_VERSION" "$TELEGRAM_VERSION" "$STATEFUL_VERSION"

printf '[+] Building images sequentially...\n'
SERVICES=(app telegram-bot celery_worker celery_beat)
for svc in "${SERVICES[@]}"; do
  if ! "${COMPOSE_CMD[@]}" build --pull "$svc"; then
    printf '[!] Failed to build %s\n' "$svc"
    exit 1
  fi
done

# Enable compose profiles only when local LLM is enabled
PROFILE_ARGS=()
if [ "${LOCAL_LLM_ENABLED}" = "true" ] || [ "$AUTOSTART_LOCAL_OLLAMA" = "1" ]; then
  PROFILE_ARGS+=(--profile local-ollama)
fi

UP_CMD=(${COMPOSE_CMD[@]})
if [ ${#PROFILE_ARGS[@]} -gt 0 ]; then
  UP_CMD+=(${PROFILE_ARGS[@]})
fi
UP_CMD+=("up" "-d" "--force-recreate" "--build")
"${UP_CMD[@]}"
printf '[✓] Containers running\n'

printf '[+] Verifying Mongo connectivity...\n'
if verify_mongo_connection 10; then
  echo '[✓] Mongo reachable'
else
  echo '[!] Mongo authentication failed; resetting mongo_data volume'
  "${COMPOSE_CMD[@]}" down --remove-orphans >/dev/null 2>&1 || true
  if docker volume inspect sitellm_vertebro_mongo_data >/dev/null 2>&1; then
    docker volume rm sitellm_vertebro_mongo_data >/dev/null 2>&1 || true
  fi
  if [ ${#PROFILE_ARGS[@]} -gt 0 ]; then
    "${COMPOSE_CMD[@]}" up -d "${PROFILE_ARGS[@]}"
  else
    "${COMPOSE_CMD[@]}" up -d
  fi
  printf '[+] Retrying Mongo connectivity...\n'
  if verify_mongo_connection 15; then
    echo '[✓] Mongo reachable after volume reset'
  else
    echo '[!] Mongo remains unreachable; aborting deploy'
    exit 1
  fi
fi

if [ -d "./knowledge_base" ]; then
  printf '[+] Uploading knowledge base...\n'
  "${COMPOSE_CMD[@]}" exec app python additional/upload_files_to_mongo.py
  printf '[+] Indexing documents...\n'
  "${COMPOSE_CMD[@]}" exec celery_worker python - <<'PY'
from worker import update_vector_store
update_vector_store()
PY
  printf '[✓] Knowledge base indexed\n'
fi

printf '[+] Verifying app -> Redis connectivity...\n'
# Quick connectivity probe from inside app container using app settings
if ! "${COMPOSE_CMD[@]}" exec -T app sh -lc 'python - <<"PY"
import sys
try:
    from backend.settings import settings as s
except Exception as e:
    print("[!] cannot import settings:", e)
    sys.exit(1)

try:
    import redis
except Exception as e:
    print("[!] redis lib missing:", e)
    sys.exit(1)

url = getattr(s, "redis_url", None)
if not url:
    scheme = "rediss" if getattr(s.redis, "secure", False) else "redis"
    auth = (":" + (s.redis.password or "") + "@") if getattr(s.redis, "password", None) else ""
    url = f"{scheme}://{auth}{s.redis.host}:{s.redis.port}/0"

ok = False
try:
    r = redis.from_url(url, socket_connect_timeout=2)
    ok = bool(r.ping())
except Exception as e:
    print("[!] Redis ping failed:", url, e)
    sys.exit(1)

print("[✓] Redis reachable:", url)
PY'; then
  echo '[!] App cannot reach Redis; aborting.'
  exit 1
fi

printf '[+] Waiting for API health check...\n'
# Prefer probing from inside the container to avoid host NAT issues
ok=""
attempts=${HEALTH_MAX_ATTEMPTS:-300}
probe_interval=${HEALTH_RETRY_INTERVAL_SECONDS:-3}
for i in $(seq 1 "$attempts"); do
  printf '  - attempt %s/%s: ' "$i" "$attempts"
  if output=$("${COMPOSE_CMD[@]}" exec -T app sh -lc '
set +e
scheme="http"
curl_opts='--max-time 4 --fail --silent --show-error -o /dev/null'
if [ -n "${APP_SSL_CERT:-}" ] && [ -n "${APP_SSL_KEY:-}" ]; then
  scheme="https"
  curl_opts="-k $curl_opts"
fi
urls="${scheme}://127.0.0.1:${APP_PORT:-8000}/healthz ${scheme}://127.0.0.1:${APP_PORT:-8000}/health ${scheme}://127.0.0.1:${APP_PORT:-8000}/"
for url in $urls; do
  if curl $curl_opts "$url"; then
    printf "%s\n" "$url"
    exit 0
  fi
  status=$?
  printf "curl_failed %s exit=%s\n" "$url" "$status" >&2
done
exit 1
' 2>&1); then
    printf '[✓] API healthy (%s)\n' "$output"
    ok=1
    break
  else
    rc=$?
    echo "not ready (exit $rc)"
    if [ -n "$output" ]; then
      printf '    probe output:\n'
      printf '%s\n' "$output" | sed 's/^/    /'
    fi
    if [ $(( i % 5 )) -eq 0 ]; then
      printf '    recent app logs:\n'
      "${COMPOSE_CMD[@]}" logs --no-color --tail=20 app | sed 's/^/    /' || true
    fi
  fi
  sleep "$probe_interval"
done
[ -n "$ok" ] || { echo "[!] API health check failed"; "${COMPOSE_CMD[@]}" logs --no-color --tail=200 app || true; exit 1; }

if [ "${ENABLE_INITIAL_CRAWL}" = "1" ] && [ -n "${CRAWL_START_URL}" ]; then
  printf '[+] Initial crawl...\n'
  crawl_args=(python crawler/run_crawl.py --url "${CRAWL_START_URL}" --max-depth 2 --max-pages 500)
  if [ -n "${PROJECT_NAME}" ]; then
    crawl_args+=(--project "${PROJECT_NAME}")
  fi
  if [ -n "${DOMAIN}" ]; then
    crawl_args+=(--domain "${DOMAIN}")
  fi
  "${COMPOSE_CMD[@]}" run --rm \
    -e CRAWL_START_URL="${CRAWL_START_URL}" \
    -e CRAWL_PROJECT="${PROJECT_NAME}" \
    app "${crawl_args[@]}" || true
  echo "[✓] Done"
else
  echo '[i] Initial crawl disabled; set ENABLE_INITIAL_CRAWL=1 and CRAWL_START_URL to enable'
fi

if [ "${ENABLE_INITIAL_CRAWL}" = "1" ] && [ -n "${CRAWL_START_URL}" ]; then
  # Configure systemd timer only on Linux with systemd
  if [ -d /run/systemd/system ]; then
SERVICE=/etc/systemd/system/crawl.service
TIMER=/etc/systemd/system/crawl.timer
sudo tee "$SERVICE" >/dev/null <<EOF_SERVICE
[Unit]
Description=Daily crawl job

[Service]
Type=oneshot
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker compose -f $(pwd)/compose.yaml $( [ -f $(pwd)/compose.gpu.yaml ] && echo "-f $(pwd)/compose.gpu.yaml" ) exec -e CRAWL_START_URL=${CRAWL_START_URL} app python crawler/run_crawl.py --url ${CRAWL_START_URL} --max-depth 2 --max-pages 500
EOF_SERVICE

sudo tee "$TIMER" >/dev/null <<EOF_TIMER
[Unit]
Description=Run crawl daily

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF_TIMER

sudo systemctl daemon-reload
sudo systemctl enable --now crawl.timer
printf '[✓] Scheduled daily crawl at 02:00\n'

else
  echo '[i] Non-systemd OS detected; skipping crawl.timer setup'
fi
else
  echo '[i] Crawl timer not configured; ENABLE_INITIAL_CRAWL disabled or CRAWL_START_URL empty'
fi

printf '[✓] Deployment complete\n'

# ---------- Runtime summary ----------
resolve_host() {
  if [ -n "${DOMAIN:-}" ]; then echo "$DOMAIN"; return; fi
  local ip
  ip=$(hostname -I 2>/dev/null | awk '{print $1}') || true
  if [ -z "$ip" ] && command -v ip >/dev/null 2>&1; then
    ip=$(ip route get 1.1.1.1 2>/dev/null | awk '/src/ {for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
  fi
  echo "${ip:-127.0.0.1}"
}

HOST_NAME=$(resolve_host)
APP_EXT_PORT=$(awk -F= '/^HOST_APP_PORT=/{print $2}' .env 2>/dev/null | tail -n1)
MONGO_EXT_PORT=$(awk -F= '/^HOST_MONGO_PORT=/{print $2}' .env 2>/dev/null | tail -n1)
REDIS_EXT_PORT=$(awk -F= '/^HOST_REDIS_PORT=/{print $2}' .env 2>/dev/null | tail -n1)
: "${APP_EXT_PORT:=18000}"
: "${MONGO_EXT_PORT:=27027}"
: "${REDIS_EXT_PORT:=16379}"

echo ""
echo "Service endpoints:"
echo "- Project:    ${PROJECT_NAME}"
echo "- API:        http://${HOST_NAME}:${APP_EXT_PORT}"
echo "- Widget:     http://${HOST_NAME}:${APP_EXT_PORT}/widget"
echo "- Admin:      http://${HOST_NAME}:${APP_EXT_PORT}/admin"
echo "- MongoDB:    ${HOST_NAME}:${MONGO_EXT_PORT} (exposed)"
echo "- Redis:      ${HOST_NAME}:${REDIS_EXT_PORT} (exposed)"
echo "- Qdrant:     internal only (http://qdrant:6333 from containers)"

if docker compose ps >/dev/null 2>&1; then
  echo ""
  echo "Containers:"
  docker compose ps --format 'table {{.Name}}\t{{.Service}}\t{{.State}}\t{{.Publishers}}'
fi

# Quick external probes and copy‑paste curl examples
echo ""
echo "Quick checks:"
HURL="http://${HOST_NAME}:${APP_EXT_PORT}"
if curl -fsS --max-time 5 "${HURL}/healthz" >/dev/null 2>&1 || \
   curl -fsS --max-time 5 "${HURL}/health"  >/dev/null 2>&1; then
  echo "- API health: OK (${HURL}/healthz)"
else
  echo "- API health: not reachable (try: curl -v ${HURL}/healthz)"
fi
if curl -fsS --max-time 5 "${HURL}/widget" >/dev/null 2>&1; then
  echo "- Widget:     OK (${HURL}/widget)"
else
  echo "- Widget:     not reachable (try: curl -v ${HURL}/widget)"
fi
# Expect 401 for admin without credentials — that still proves routing works
ADMIN_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${HURL}/admin" || echo 000)
if [ "$ADMIN_CODE" = "401" ] || [ "$ADMIN_CODE" = "200" ]; then
  echo "- Admin:      reachable (${HURL}/admin, requires Basic auth)"
else
  echo "- Admin:      not reachable (code ${ADMIN_CODE})"
fi

echo ""
echo "Curl examples:"
echo "  curl -fsS ${HURL}/healthz"
echo "  curl -fsS ${HURL}/widget | head -n1"
echo "  curl -I -u admin:admin ${HURL}/admin   # if default admin creds"

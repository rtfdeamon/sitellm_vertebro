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

pick_free_port() {
  local start="$1"; local max_scan=100; local p="$start"
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
    echo '[+] Removing previous containers (if any)...'
    if ! docker compose "${compose_args[@]}" down --remove-orphans >/dev/null 2>&1; then
      echo '[i] docker compose down reported an error; continuing'
    fi
  fi

  if docker network inspect sitellm_vertebro_default >/dev/null 2>&1; then
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

if [ "$AUTO_YES" -eq 1 ]; then
  DOMAIN="${DOMAIN?DOMAIN env variable required with --yes}"
else
  printf '[+] Domain: '
  read -r DOMAIN
fi

# Autodetect crawl start URL from DOMAIN if not provided
: "${CRAWL_START_URL:=https://${DOMAIN}}"
export CRAWL_START_URL

printf '[+] Enable GPU? [y/N]: '
read -r ENABLE_GPU
ENABLE_GPU=${ENABLE_GPU:-N}
printf '[+] LLM model to use [Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it]: '
read -r LLM_MODEL
LLM_MODEL=${LLM_MODEL:-Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it}

# Reuse existing Mongo credentials if present, otherwise apply deterministic defaults
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
  MONGO_PASSWORD=${MONGO_PASSWORD:-f76DlgezffdHetX}
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

# GPU flag to boolean
if [ "$ENABLE_GPU" = "y" ] || [ "$ENABLE_GPU" = "Y" ]; then
  USE_GPU=true
else
  USE_GPU=false
fi

# (Firewall ports will be opened later, after .env is created)

REDIS_PASS=$(openssl rand -hex 8)
GRAFANA_PASS=$(openssl rand -hex 8)

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

touch .env
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

update_env_var DOMAIN "$DOMAIN"
update_env_var CRAWL_START_URL "$CRAWL_START_URL"
update_env_var LLM_MODEL "$LLM_MODEL"
update_env_var REDIS_PASSWORD "$REDIS_PASS"
update_env_var REDIS_URL "$REDIS_URL"
update_env_var CELERY_BROKER "$REDIS_URL"
update_env_var CELERY_RESULT "$REDIS_URL"
update_env_var QDRANT_URL "$QDRANT_URL"
if [ -n "$QDRANT_PLATFORM" ]; then
  update_env_var QDRANT_PLATFORM "$QDRANT_PLATFORM"
fi
update_env_var EMB_MODEL_NAME "sentence-transformers/sbert_large_nlu_ru"
update_env_var RERANK_MODEL_NAME "sbert_cross_ru"
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
APP_PORT_HOST=$(pick_free_port "${HOST_APP_PORT:-18000}")
MONGO_PORT_HOST=$(pick_free_port "${HOST_MONGO_PORT:-27027}")
REDIS_PORT_HOST=$(pick_free_port "${HOST_REDIS_PORT:-16379}")
QDRANT_HTTP_HOST=$(pick_free_port "${HOST_QDRANT_HTTP_PORT:-16333}")
QDRANT_GRPC_HOST=$(pick_free_port "${HOST_QDRANT_GRPC_PORT:-16334}")
update_env_var HOST_APP_PORT "$APP_PORT_HOST"
update_env_var HOST_MONGO_PORT "$MONGO_PORT_HOST"
update_env_var HOST_REDIS_PORT "$REDIS_PORT_HOST"
update_env_var HOST_QDRANT_HTTP_PORT "$QDRANT_HTTP_HOST"
update_env_var HOST_QDRANT_GRPC_PORT "$QDRANT_GRPC_HOST"
update_env_var OLLAMA_BASE_URL "${OLLAMA_BASE_URL:-http://host.docker.internal:11434}"

# ---------------------------------------------------------------------------
# Decide whether local LLM (llama-cpp/torch) is needed
# If an external model backend is configured (MODEL_BASE_URL) or Ollama base
# is set, disable local LLM and force CPU build to avoid NVIDIA/CUDA drivers.
# ---------------------------------------------------------------------------

# Read values back from .env (tolerate missing)
VAL_OLLAMA_BASE=$(awk -F= '/^OLLAMA_BASE_URL=/{print $2}' .env 2>/dev/null | tail -n1 || true)
VAL_MODEL_BASE=$(awk -F= '/^MODEL_BASE_URL=/{print $2}' .env 2>/dev/null | tail -n1 || true)

# Treat non-empty as configured
LOCAL_LLM_ENABLED=true
if [ -n "${VAL_MODEL_BASE}" ] || [ -n "${VAL_OLLAMA_BASE}" ]; then
  LOCAL_LLM_ENABLED=false
fi
update_env_var LOCAL_LLM_ENABLED "${LOCAL_LLM_ENABLED}"

# If remote LLM is used, always force CPU (no GPU compose / no CUDA wheels)
if [ "${LOCAL_LLM_ENABLED}" = "false" ]; then
  if [ "${USE_GPU}" = true ]; then
    echo "[i] Remote LLM detected (Ollama/model service). Disabling GPU build to avoid NVIDIA drivers."
  fi
  USE_GPU=false
  update_env_var USE_GPU "false"
fi

# Only now, after finalizing USE_GPU, configure NVIDIA runtime if needed
if [ "$USE_GPU" = true ]; then
  ensure_nvidia_toolkit
fi

timestamp=$(date +%Y%m%d%H%M%S)
mkdir -p deploy-backups
tar -czf "deploy-backups/${timestamp}.tar.gz" .env compose.yaml
printf '[✓] Environment saved to deploy-backups/%s.tar.gz\n' "$timestamp"

if ! grep -q "^MONGO_PASSWORD=" .env; then
  echo '[!] MONGO_PASSWORD not found in .env'; exit 1
fi
if ! grep -q "^MONGO_USERNAME=" .env; then
  echo '[!] MONGO_USERNAME not found in .env'; exit 1
fi

# Now that .env exists, open firewall ports if applicable
open_firewall_ports

cleanup_previous_stack

printf '[+] Starting containers...\n'
if [ "$USE_GPU" = true ]; then
  echo '[+] Starting project in GPU mode'
else
  echo '[+] Starting project in CPU mode'
fi

# Compose command (optionally include GPU overrides)
COMPOSE_FILES=(-f compose.yaml)
# Include GPU overrides only when both GPU requested and local LLM is enabled
if [ "$USE_GPU" = true ] && [ "${LOCAL_LLM_ENABLED}" = "true" ] && [ -f compose.gpu.yaml ]; then
  COMPOSE_FILES+=(-f compose.gpu.yaml)
fi
COMPOSE_CMD=(docker compose "${COMPOSE_FILES[@]}")

printf '[+] Building images sequentially...\n'
# Build only required services; skip local-LLM services if disabled
SERVICES=(app telegram-bot)
if [ "${LOCAL_LLM_ENABLED}" = "true" ]; then
  SERVICES+=(celery_worker celery_beat)
fi
for svc in "${SERVICES[@]}"; do
  if ! "${COMPOSE_CMD[@]}" build --pull "$svc"; then
    printf '[!] Failed to build %s\n' "$svc"
    exit 1
  fi
done

# Enable compose profiles only when local LLM is enabled
PROFILE_ARGS=()
if [ "${LOCAL_LLM_ENABLED}" = "true" ]; then
  PROFILE_ARGS+=(--profile local-llm)
fi

"${COMPOSE_CMD[@]}" up -d "${PROFILE_ARGS[@]}"
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
  "${COMPOSE_CMD[@]}" up -d "${PROFILE_ARGS[@]}"
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
for i in $(seq 1 "$attempts"); do
  if "${COMPOSE_CMD[@]}" exec -T app sh -lc "curl -fsS http://127.0.0.1:\${APP_PORT:-8000}/healthz || curl -fsS http://127.0.0.1:\${APP_PORT:-8000}/health || curl -fsS http://127.0.0.1:\${APP_PORT:-8000}/" >/dev/null 2>&1; then
    echo "[✓] API healthy"
    ok=1
    break
  fi
  sleep 3
done
[ -n "$ok" ] || { echo "[!] API health check failed"; "${COMPOSE_CMD[@]}" logs --no-color --tail=200 app || true; exit 1; }

printf '[+] Initial crawl...\n'
"${COMPOSE_CMD[@]}" run --rm \
  -e CRAWL_START_URL="${CRAWL_START_URL}" \
  app python crawler/run_crawl.py --url "${CRAWL_START_URL}" --max-depth 2 --max-pages 500 || true
echo "[✓] Done"

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

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

printf '[+] Enable GPU? [y/N]: '
read -r ENABLE_GPU
ENABLE_GPU=${ENABLE_GPU:-N}
printf '[+] LLM model to use [Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it]: '
read -r LLM_MODEL
LLM_MODEL=${LLM_MODEL:-Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it}

printf '[+] Mongo root username [root]: '
read -r MONGO_USERNAME
MONGO_USERNAME=${MONGO_USERNAME:-root}
export MONGO_USERNAME

printf '[+] Mongo root password [auto-generate if empty]: '
read -r MONGO_PASSWORD
if [ -z "$MONGO_PASSWORD" ]; then
  MONGO_PASSWORD=$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9' | head -c16)
fi
export MONGO_PASSWORD

# GPU flag to boolean
if [ "$ENABLE_GPU" = "y" ] || [ "$ENABLE_GPU" = "Y" ]; then
  USE_GPU=true
else
  USE_GPU=false
fi

REDIS_PASS=$(openssl rand -hex 8)
GRAFANA_PASS=$(openssl rand -hex 8)

REDIS_URL="redis://:${REDIS_PASS}@localhost:6379/0"
QDRANT_URL="http://localhost:6333"

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
update_env_var LLM_MODEL "$LLM_MODEL"
update_env_var REDIS_URL "$REDIS_URL"
update_env_var QDRANT_URL "$QDRANT_URL"
update_env_var EMB_MODEL_NAME "sentence-transformers/sbert_large_nlu_ru"
update_env_var RERANK_MODEL_NAME "sbert_cross_ru"
update_env_var MONGO_HOST "mongo"
update_env_var MONGO_PORT "27017"
update_env_var MONGO_USERNAME "$MONGO_USERNAME"
update_env_var MONGO_PASSWORD "$MONGO_PASSWORD"
update_env_var USE_GPU "$USE_GPU"
update_env_var GRAFANA_PASSWORD "$GRAFANA_PASS"

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

printf '[+] Starting containers...\n'
if [ "$USE_GPU" = true ]; then
  echo '[+] Starting project in GPU mode'
else
  echo '[+] Starting project in CPU mode'
fi

printf '[+] Building images sequentially...\n'
for svc in app telegram-bot celery_worker celery_beat; do
  if ! docker compose build --pull "$svc"; then
    printf '[!] Failed to build %s\n' "$svc"
    exit 1
  fi
done


docker compose up -d
printf '[✓] Containers running\n'

if [ -d "./knowledge_base" ]; then
  printf '[+] Uploading knowledge base...\n'
  docker compose exec app python additional/upload_files_to_mongo.py
  printf '[+] Indexing documents...\n'
  docker compose exec celery_worker python - <<'PY'
from worker import update_vector_store
update_vector_store()
PY
  printf '[✓] Knowledge base indexed\n'
fi

printf '[+] Waiting for API health check...\n'
if curl -sf http://localhost:8000/health >/dev/null; then
  echo '[✓] API is healthy'
else
  echo '[!] API health check failed'
fi

printf '[+] Initial crawl...\n'
docker compose exec app python crawler/run_crawl.py --domain "$DOMAIN" --max-depth 2 --max-pages 500
printf '[✓] Initial crawl done\n'

SERVICE=/etc/systemd/system/crawl.service
TIMER=/etc/systemd/system/crawl.timer
sudo tee "$SERVICE" >/dev/null <<EOF_SERVICE
[Unit]
Description=Daily crawl job

[Service]
Type=oneshot
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker compose exec app python crawler/run_crawl.py --domain $DOMAIN --max-depth 2 --max-pages 500
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

printf '[✓] Deployment complete\n'
echo "API: http://$DOMAIN/api"
echo "Grafana: http://$DOMAIN/grafana (login: admin, password: $GRAFANA_PASS)"

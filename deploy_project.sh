#!/usr/bin/env bash
set -euo pipefail

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
  read DOMAIN
fi

printf '[+] LLM_URL [http://localhost:8000]: '
read LLM_URL
LLM_URL=${LLM_URL:-http://localhost:8000}
printf '[+] Enable GPU? [y/N]: '
read ENABLE_GPU
ENABLE_GPU=${ENABLE_GPU:-N}

REDIS_PASS=$(openssl rand -hex 8)
QDRANT_PASS=$(openssl rand -hex 8)
GRAFANA_PASS=$(openssl rand -hex 8)

REDIS_URL="redis://:${REDIS_PASS}@localhost:6379/0"
QDRANT_URL="http://localhost:6333"

cat > .env <<ENV
DOMAIN=$DOMAIN
LLM_URL=$LLM_URL
REDIS_URL=$REDIS_URL
QDRANT_URL=$QDRANT_URL
EMB_MODEL_NAME=sentence-transformers/sbert_large_nlu_ru
RERANK_MODEL_NAME=sbert_cross_ru
GRAFANA_PASSWORD=$GRAFANA_PASS
ENV

timestamp=$(date +%Y%m%d%H%M%S)
mkdir -p deploy-backups
tar -czf "deploy-backups/${timestamp}.tar.gz" .env compose.yaml
printf '[✓] Environment saved to deploy-backups/%s.tar.gz\n' "$timestamp"

printf '[+] Starting containers...\n'
PROFILE=""
if [ "${ENABLE_GPU}" = "y" ] || [ "${ENABLE_GPU}" = "Y" ]; then
  PROFILE="--profile gpu"
fi

docker compose up -d --build $PROFILE
printf '[✓] Containers running\n'

printf '[+] Initial crawl...\n'
docker compose exec api python crawler/run_crawl.py --domain "$DOMAIN" --max-depth 2 --max-pages 500
printf '[✓] Initial crawl done\n'

SERVICE=/etc/systemd/system/crawl.service
TIMER=/etc/systemd/system/crawl.timer
sudo tee "$SERVICE" >/dev/null <<EOF_SERVICE
[Unit]
Description=Daily crawl job

[Service]
Type=oneshot
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker compose exec api python crawler/run_crawl.py --domain $DOMAIN --max-depth 2 --max-pages 500
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

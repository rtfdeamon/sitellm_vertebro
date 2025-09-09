#!/usr/bin/env bash

# Bootstrap the target machine for this project:
# - Install Docker Engine + Compose v2 (Ubuntu/Debian or generic installer)
# - Ensure repo is present in APP_DIR (clone if missing)
# - Prepare .env (generate secrets if missing)
# - Create systemd service for docker compose stack
# - Create systemd timer for daily crawl
#
# Usage (on target server):
#   APP_DIR=/opt/sitellm_vertebro \
#   REPO_URL=https://github.com/rtfdeamon/sitellm_vertebro.git \
#   CRAWL_START_URL=https://example.com \
#   bash scripts/bootstrap.sh

set -euo pipefail

APP_DIR=${APP_DIR:-/opt/sitellm_vertebro}
REPO_URL=${REPO_URL:-https://github.com/rtfdeamon/sitellm_vertebro.git}
BRANCH=${BRANCH:-main}

SUDO=""
if [ "${EUID}" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "[!] This script needs root or sudo to install packages and write systemd units"
    exit 1
  fi
fi

log() { printf "[bootstrap] %s\n" "$*"; }

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "docker already installed: $(docker --version)"
    return
  fi
  log "installing docker engine + compose"
  if [ -r /etc/os-release ]; then
    . /etc/os-release
  else
    ID=""
  fi
  case "${ID:-}" in
    ubuntu|debian)
      ${SUDO} apt-get update -y
      ${SUDO} apt-get install -y ca-certificates curl gnupg lsb-release
      if [ ! -e /etc/apt/keyrings/docker.gpg ]; then
        ${SUDO} install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/${ID}/gpg | ${SUDO} gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        ${SUDO} chmod a+r /etc/apt/keyrings/docker.gpg
      fi
      echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | ${SUDO} tee /etc/apt/sources.list.d/docker.list >/dev/null
      ${SUDO} apt-get update -y
      ${SUDO} apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
      ;;
    *)
      # Generic convenience script
      curl -fsSL https://get.docker.com | ${SUDO} sh
      ;;
  esac
  ${SUDO} systemctl enable --now docker || true
  log "docker installed"
}

ensure_repo() {
  ${SUDO} mkdir -p "${APP_DIR}"
  ${SUDO} chown -R "${USER:-$(id -un)}":"${USER:-$(id -un)}" "${APP_DIR}"
  if [ ! -d "${APP_DIR}/.git" ]; then
    if [ -z "${REPO_URL}" ]; then
      echo "[!] REPO_URL is not set and repo not present in ${APP_DIR}"
      exit 1
    fi
    log "cloning ${REPO_URL} to ${APP_DIR}"
    git clone "${REPO_URL}" "${APP_DIR}"
  fi
  cd "${APP_DIR}"
  git fetch --all --prune || true
  git checkout "${BRANCH}" || true
  git reset --hard "origin/${BRANCH}" || true
}

update_env_var() {
  local key="$1" val="$2"
  local esc
  esc=$(printf '%s' "$val" | sed 's/[\\/&]/\\&/g')
  if grep -q "^${key}=" .env 2>/dev/null; then
    if sed --version >/dev/null 2>&1; then
      sed -i -e "s/^${key}=.*/${key}=${esc}/" .env
    else
      sed -i '' -e "s/^${key}=.*/${key}=${esc}/" .env
    fi
  else
    echo "${key}=${val}" >> .env
  fi
}

prepare_env() {
  if [ ! -f .env ]; then
    if [ -f .env.example ]; then
      cp .env.example .env
    else
      touch .env
    fi
  fi
  # Generate secrets if missing
  : "${MONGO_USERNAME:=root}"
  : "${MONGO_PASSWORD:=$(openssl rand -hex 8)}"
  : "${REDIS_PASSWORD:=$(openssl rand -hex 8)}"
  : "${GRAFANA_PASSWORD:=$(openssl rand -hex 8)}"
  : "${CRAWL_START_URL:=https://mmvs.ru}"
  : "${LLM_MODEL:=Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it}"

  update_env_var MONGO_USERNAME "${MONGO_USERNAME}"
  update_env_var MONGO_PASSWORD "${MONGO_PASSWORD}"
  update_env_var MONGO_URI "mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@mongo:27017"

  update_env_var REDIS_PASSWORD "${REDIS_PASSWORD}"
  update_env_var REDIS_URL "redis://:${REDIS_PASSWORD}@redis:6379/0"
  update_env_var CELERY_BROKER "redis://:${REDIS_PASSWORD}@redis:6379/0"
  update_env_var CELERY_RESULT "redis://:${REDIS_PASSWORD}@redis:6379/0"

  update_env_var QDRANT_URL "http://qdrant:6333"
  update_env_var CRAWL_START_URL "${CRAWL_START_URL}"
  update_env_var LLM_MODEL "${LLM_MODEL}"
  update_env_var GRAFANA_PASSWORD "${GRAFANA_PASSWORD}"
}

install_units() {
  local svc=/etc/systemd/system/sitellm.service
  local crawl_svc=/etc/systemd/system/crawl.service
  local crawl_timer=/etc/systemd/system/crawl.timer

  log "installing systemd service for docker compose stack"
  ${SUDO} tee "$svc" >/dev/null <<EOF
[Unit]
Description=Sitellm stack (docker compose)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=${APP_DIR}
RemainAfterExit=yes
TimeoutStartSec=0
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

  log "installing daily crawl timer"
  ${SUDO} tee "$crawl_svc" >/dev/null <<EOF
[Unit]
Description=Daily crawl job

[Service]
Type=oneshot
WorkingDirectory=${APP_DIR}
Environment=CRAWL_START_URL=${CRAWL_START_URL}
ExecStart=/usr/bin/docker compose exec -e CRAWL_START_URL=${CRAWL_START_URL} app \
  python crawler/run_crawl.py --url ${CRAWL_START_URL} --max-depth 2 --max-pages 500
EOF

  ${SUDO} tee "$crawl_timer" >/dev/null <<EOF
[Unit]
Description=Run crawl daily

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

  ${SUDO} systemctl daemon-reload
  ${SUDO} systemctl enable --now sitellm.service
  ${SUDO} systemctl enable --now crawl.timer
}

main() {
  install_docker
  ensure_repo
  prepare_env
  install_units
  log "bootstrap complete"
}

main "$@"

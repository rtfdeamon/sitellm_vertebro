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
# Optional reverse-proxy + TLS via Caddy when DOMAIN is set
# INSTALL_PROXY=caddy to force; set LETSENCRYPT_EMAIL for ACME contact email
INSTALL_PROXY=${INSTALL_PROXY:-}
DOMAIN=${DOMAIN:-}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-}
# Firewall options: open 80/443 always if proxy installed; open 8000 if OPEN_APP_PORT=1
OPEN_APP_PORT=${OPEN_APP_PORT:-0}
USE_GPU=${USE_GPU:-}
INSTALL_NVIDIA_TOOLKIT=${INSTALL_NVIDIA_TOOLKIT:-}
INSTALL_NVIDIA_DRIVER=${INSTALL_NVIDIA_DRIVER:-}

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
  : "${DOMAIN:=${DOMAIN:-}}"
  : "${USE_GPU:=${USE_GPU:-}}"

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
  if [ -n "${DOMAIN}" ]; then
    update_env_var DOMAIN "${DOMAIN}"
  fi
  if [ -n "${USE_GPU}" ]; then
    update_env_var USE_GPU "${USE_GPU}"
  fi
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

setup_firewall() {
  # Open required ports if firewall is active
  # - Always try to open SSH (22), HTTP (80), HTTPS (443)
  # - Optionally open APP port (8000) if OPEN_APP_PORT=1
  local open_app=${OPEN_APP_PORT}
  if command -v ufw >/dev/null 2>&1; then
    # Apply rules only if ufw is active (avoid enabling automatically)
    if ufw status | grep -qi active; then
      ${SUDO} ufw allow 22/tcp || true
      ${SUDO} ufw allow 80/tcp || true
      ${SUDO} ufw allow 443/tcp || true
      if [ "$open_app" = "1" ]; then
        ${SUDO} ufw allow 8000/tcp || true
      fi
    fi
  elif command -v firewall-cmd >/dev/null 2>&1; then
    if ${SUDO} firewall-cmd --state >/dev/null 2>&1; then
      ${SUDO} firewall-cmd --permanent --add-service=ssh || true
      ${SUDO} firewall-cmd --permanent --add-service=http || true
      ${SUDO} firewall-cmd --permanent --add-service=https || true
      if [ "$open_app" = "1" ]; then
        ${SUDO} firewall-cmd --permanent --add-port=8000/tcp || true
      fi
      ${SUDO} firewall-cmd --reload || true
    fi
  else
    # No known firewall tool; skip
    :
  fi
}

install_caddy() {
  # Install and configure Caddy as reverse proxy with automatic TLS
  # Requires DOMAIN to be set and DNS pointing to this server.
  if [ -z "${DOMAIN}" ]; then
    log "DOMAIN is empty; skipping Caddy install"
    return 0
  fi
  log "installing Caddy reverse proxy for domain ${DOMAIN}"
  if [ -r /etc/os-release ]; then . /etc/os-release; fi
  case "${ID:-}" in
    ubuntu|debian)
      ${SUDO} apt-get update -y
      ${SUDO} apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
      if [ ! -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg ]; then
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | ${SUDO} gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
      fi
      if [ ! -f /etc/apt/sources.list.d/caddy-stable.list ]; then
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | ${SUDO} tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
      fi
      ${SUDO} apt-get update -y
      ${SUDO} apt-get install -y caddy
      ;;
    *)
      log "Non Debian/Ubuntu OS; attempting to install caddy from default repo"
      ${SUDO} apt-get update -y 2>/dev/null || true
      ${SUDO} apt-get install -y caddy 2>/dev/null || {
        log "Caddy install skipped (unsupported OS)."
        return 0
      }
      ;;
  esac

  # Write Caddyfile
  local cfile=/etc/caddy/Caddyfile
  if [ -n "${LETSENCRYPT_EMAIL}" ]; then
    ${SUDO} tee "$cfile" >/dev/null <<EOF
{
  email ${LETSENCRYPT_EMAIL}
}

${DOMAIN} {
  encode zstd gzip
  reverse_proxy 127.0.0.1:8000
}
EOF
  else
    ${SUDO} tee "$cfile" >/dev/null <<EOF
${DOMAIN} {
  encode zstd gzip
  reverse_proxy 127.0.0.1:8000
}
EOF
  fi

  ${SUDO} systemctl enable --now caddy
  ${SUDO} systemctl reload caddy || true
  log "caddy configured; ensure DNS for ${DOMAIN} points to this host"
}

install_nvidia_toolkit() {
  # Install NVIDIA Container Toolkit for Docker
  log "installing NVIDIA Container Toolkit"
  if [ -r /etc/os-release ]; then . /etc/os-release; fi
  case "${ID:-}" in
    ubuntu|debian)
      ${SUDO} apt-get update -y
      ${SUDO} apt-get install -y curl gnupg ca-certificates
      distribution=$(. /etc/os-release;echo $ID$VERSION_ID) && \
      curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | ${SUDO} gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
      curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        ${SUDO} tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
      ${SUDO} apt-get update -y
      ${SUDO} apt-get install -y nvidia-container-toolkit
      ${SUDO} nvidia-ctk runtime configure --runtime=docker || true
      ${SUDO} systemctl restart docker || true
      ;;
    *)
      log "NVIDIA toolkit install skipped (unsupported OS)"
      return 0
      ;;
  esac
}

install_nvidia_driver() {
  # Attempt installing NVIDIA proprietary driver (may require reboot)
  log "installing NVIDIA driver (optional)"
  if [ -r /etc/os-release ]; then . /etc/os-release; fi
  case "${ID:-}" in
    ubuntu)
      ${SUDO} apt-get update -y
      if command -v ubuntu-drivers >/dev/null 2>&1; then
        ${SUDO} apt-get install -y ubuntu-drivers-common
        ${SUDO} ubuntu-drivers install -g || true
      else
        ${SUDO} apt-get install -y nvidia-driver-535 || ${SUDO} apt-get install -y nvidia-driver || true
      fi
      ;;
    debian)
      ${SUDO} apt-get update -y
      ${SUDO} apt-get install -y nvidia-driver || true
      ;;
    *)
      log "NVIDIA driver install skipped (unsupported OS)"
      ;;
  esac
  log "NVIDIA driver installation requested; reboot may be required"
}

main() {
  install_docker
  ensure_repo
  prepare_env
  install_units
  # Decide whether to install proxy
  if [ -z "$INSTALL_PROXY" ] && [ -n "$DOMAIN" ]; then
    INSTALL_PROXY=caddy
  fi
  setup_firewall
  if [ "$INSTALL_PROXY" = "caddy" ]; then
    install_caddy
  fi
  # Optional GPU setup
  if [ "${USE_GPU}" = "true" ] || [ "${INSTALL_NVIDIA_TOOLKIT}" = "1" ]; then
    install_nvidia_toolkit
  fi
  if [ "${INSTALL_NVIDIA_DRIVER}" = "1" ]; then
    install_nvidia_driver
  fi
  log "bootstrap complete"
}

main "$@"

#!/usr/bin/env bash
set -euo pipefail

# Install a native (non-Docker) LLM model microservice as a systemd unit.
# It sets up a Python venv, installs dependencies (CPU or CUDA wheels),
# and creates `yallm-model.service` listening on MODEL_PORT (default 9000).
#
# Usage:
#   sudo bash scripts/install_model_service.sh [--gpu]
# Env (optional):
#   APP_DIR=/opt/sitellm_vertebro
#   MODEL_PORT=9000
#   LLM_MODEL=Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it
#   MODEL_API_KEY=...     # if set, required for access
#   CUDA_CHANNEL=cu121    # for GPU wheels (default cu121)

APP_DIR=${APP_DIR:-$(pwd)}
MODEL_PORT=${MODEL_PORT:-9000}
LLM_MODEL=${LLM_MODEL:-Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it}
MODEL_API_KEY=${MODEL_API_KEY:-}
CUDA_CHANNEL=${CUDA_CHANNEL:-cu121}

USE_GPU=0
if [ "${1-}" = "--gpu" ]; then USE_GPU=1; fi

log(){ printf "[model-install] %s\n" "$*"; }

require(){ command -v "$1" >/dev/null 2>&1 || { echo "[!] missing: $1"; exit 1; }; }

if ! command -v python3 >/dev/null 2>&1; then
  log "installing Python3 + venv"
  if [ -r /etc/os-release ]; then . /etc/os-release; fi
  case "${ID:-}" in
    ubuntu|debian)
      apt-get update -y
      apt-get install -y python3 python3-venv python3-pip
      ;;
    *)
      echo "[!] please install python3-venv and pip for your distro"; exit 1;;
  esac
fi

install_nvidia_driver(){
  if [ -x /usr/bin/nvidia-smi ]; then return; fi
  if [ -r /etc/os-release ]; then . /etc/os-release; fi
  case "${ID:-}" in
    ubuntu)
      apt-get update -y
      apt-get install -y ubuntu-drivers-common || true
      ubuntu-drivers install -g || true
      ;;
    debian)
      apt-get update -y
      apt-get install -y nvidia-driver || true
      ;;
  esac
  log "NVIDIA driver installation attempted. Reboot may be required."
}

[ "$USE_GPU" -eq 1 ] && install_nvidia_driver || true

mkdir -p "$APP_DIR"
cd "$APP_DIR"

VENV="$APP_DIR/.venv_model"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -U pip wheel

if [ "$USE_GPU" -eq 1 ]; then
  export PIP_EXTRA_INDEX_URL="https://download.pytorch.org/whl/${CUDA_CHANNEL} https://abetlen.github.io/llama-cpp-python/whl/${CUDA_CHANNEL}"
else
  export PIP_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"
fi

# Install project (editable) and server deps
"$VENV/bin/pip" install -e .
"$VENV/bin/pip" install uvicorn fastapi structlog orjson

SERVICE=/etc/systemd/system/yallm-model.service
cat > "$SERVICE" <<EOF
[Unit]
Description=YaLLM model microservice
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
Environment=LLM_MODEL=${LLM_MODEL}
Environment=USE_GPU=$([ "$USE_GPU" -eq 1 ] && echo true || echo false)
Environment=MODEL_API_KEY=${MODEL_API_KEY}
Environment=PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}
ExecStart=${VENV}/bin/uvicorn backend.model_service:app --host 0.0.0.0 --port ${MODEL_PORT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now yallm-model.service
log "service enabled (port ${MODEL_PORT})"

# Open firewall port if ufw / firewalld present
if command -v ufw >/dev/null 2>&1 && ufw status | grep -qi active; then
  ufw allow "${MODEL_PORT}/tcp" || true
elif command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --permanent --add-port="${MODEL_PORT}/tcp" || true
  firewall-cmd --reload || true
fi

log "done. Test: curl http://127.0.0.1:${MODEL_PORT}/healthz"


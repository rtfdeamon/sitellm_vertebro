#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
cd "${PROJECT_ROOT}"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/.env"
  set +a
fi

# Minimal local runner for the app without Docker.
# - Assumes Ollama runs on the host (default 127.0.0.1:11434)
# - Does not require Redis/Mongo/Qdrant for /api/v1/llm/chat

DEFAULT_OLLAMA_BASE_URL="http://127.0.0.1:11434"
STARTED_LOCAL_OLLAMA=0
OLLAMA_PID=""

cleanup() {
  if [[ ${STARTED_LOCAL_OLLAMA:-0} -eq 1 && -n "${OLLAMA_PID:-}" ]]; then
    kill "${OLLAMA_PID}" >/dev/null 2>&1 || true
    wait "${OLLAMA_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-${DEFAULT_OLLAMA_BASE_URL}}"
export APP_HOST="${APP_HOST:-0.0.0.0}"
export APP_PORT="${APP_PORT:-8000}"

autostart_raw="${RUN_LOCAL_AUTOSTART_OLLAMA:-0}"
case "${autostart_raw}" in
  1|[Tt][Rr][Uu][Ee]|[Yy][Ee][Ss]|[Oo][Nn])
    AUTOSTART_OLLAMA=1
    ;;
  *)
    AUTOSTART_OLLAMA=0
    ;;
esac

# Optionally spin up a local Ollama daemon based on RUN_LOCAL_AUTOSTART_OLLAMA.
if [[ ${AUTOSTART_OLLAMA} -eq 1 ]]; then
  case "${OLLAMA_BASE_URL}" in
    *host.docker.internal*)
      echo "[run_local] Overriding OLLAMA_BASE_URL for local autostart."
      OLLAMA_BASE_URL="${DEFAULT_OLLAMA_BASE_URL}"
      ;;
  esac

  ollama_ready() {
    if ! command -v curl >/dev/null 2>&1; then
      return 1
    fi
    local base="${OLLAMA_BASE_URL%/}"
    curl -fsS "${base}/api/version" >/dev/null 2>&1
  }

  wait_for_ollama() {
    if ! command -v curl >/dev/null 2>&1; then
      return 0
    fi
    local base="${OLLAMA_BASE_URL%/}"
    for _ in $(seq 1 30); do
      if curl -fsS "${base}/api/version" >/dev/null 2>&1; then
        return 0
      fi
      sleep 1
    done
    return 1
  }

  if command -v ollama >/dev/null 2>&1; then
    if ollama_ready; then
      echo "[run_local] Ollama already responding at ${OLLAMA_BASE_URL}; skip autostart."
    else
      echo "[run_local] Starting local Ollama daemon..."
      ollama serve &
      OLLAMA_PID=$!
      STARTED_LOCAL_OLLAMA=1
      if ! wait_for_ollama; then
        echo "[run_local] Warning: timed out waiting for Ollama at ${OLLAMA_BASE_URL} (continuing)" >&2
      fi
    fi
  else
    echo "[run_local] RUN_LOCAL_AUTOSTART_OLLAMA enabled but 'ollama' CLI not found." >&2
    exit 1
  fi
fi

python -m pip install -q --upgrade pip
python -m pip install -q "uv>=0.8"

# Install project deps (CPU-only)
uv pip install --system --no-cache --requirements pyproject.toml

echo "Starting app on ${APP_HOST}:${APP_PORT} (Ollama: ${OLLAMA_BASE_URL})"
exec uvicorn app:app --host "$APP_HOST" --port "$APP_PORT" --timeout-keep-alive 30 --workers 1

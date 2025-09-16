#!/usr/bin/env bash
set -euo pipefail

# Minimal local runner for the app without Docker.
# - Assumes Ollama runs on the host (default 127.0.0.1:11434)
# - Does not require Redis/Mongo/Qdrant for /api/v1/llm/chat

export OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://127.0.0.1:11434}
export APP_HOST=${APP_HOST:-0.0.0.0}
export APP_PORT=${APP_PORT:-8000}

python -m pip install -q --upgrade pip
python -m pip install -q "uv>=0.8"

# Install project deps (CPU-only)
uv pip install --system --no-cache --requirements pyproject.toml

echo "Starting app on ${APP_HOST}:${APP_PORT} (Ollama: ${OLLAMA_BASE_URL})"
exec uvicorn app:app --host "$APP_HOST" --port "$APP_PORT" --timeout-keep-alive 30 --workers 1


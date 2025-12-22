#!/usr/bin/env bash
set -euo pipefail

# Simple liveness probe for the FastAPI app container.
PORT="${APP_PORT:-${PORT:-8000}}"

TARGETS=(
  "http://127.0.0.1:${PORT}/healthz"
  "http://127.0.0.1:${PORT}/health"
  "http://127.0.0.1:${PORT}/"
)

for url in "${TARGETS[@]}"; do
  if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
    exit 0
  fi
done

exit 1

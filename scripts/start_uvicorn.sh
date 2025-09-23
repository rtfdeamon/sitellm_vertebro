#!/usr/bin/env bash
set -euo pipefail

HOST=${APP_HOST:-0.0.0.0}
PORT=${APP_PORT:-${PORT:-8000}}
WORKERS=${APP_WORKERS:-${UVICORN_WORKERS:-1}}
KEEP_ALIVE=${APP_TIMEOUT_KEEP_ALIVE:-30}
CERT=${APP_SSL_CERT:-}
KEY=${APP_SSL_KEY:-}

cmd=(uvicorn app:app --host "$HOST" --port "$PORT" --workers "$WORKERS" --timeout-keep-alive "$KEEP_ALIVE")

if [[ -n "$CERT" && -n "$KEY" && -f "$CERT" && -f "$KEY" ]]; then
  echo "[start_uvicorn] Enabling TLS with cert: $CERT"
  cmd+=(--ssl-certfile "$CERT" --ssl-keyfile "$KEY")
else
  echo "[start_uvicorn] TLS disabled (certificate not found or APP_SSL_CERT/KEY unset)" >&2
fi

exec "${cmd[@]}"

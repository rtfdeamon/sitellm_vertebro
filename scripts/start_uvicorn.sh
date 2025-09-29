#!/usr/bin/env bash
set -euo pipefail

HOST=${APP_HOST:-0.0.0.0}
PORT=${APP_PORT:-${PORT:-8000}}
WORKERS=${APP_WORKERS:-${UVICORN_WORKERS:-1}}
KEEP_ALIVE=${APP_TIMEOUT_KEEP_ALIVE:-30}
CERT=${APP_SSL_CERT:-}
KEY=${APP_SSL_KEY:-}
ENABLE_TLS_RAW=${APP_ENABLE_TLS:-}
EXPLICIT_TLS_FLAG=0

case "${ENABLE_TLS_RAW,,}" in
  1|true|yes)
    ENABLE_TLS=1
    EXPLICIT_TLS_FLAG=1
    ;;
  *)
    ENABLE_TLS=0
    if [[ -n "${ENABLE_TLS_RAW}" ]]; then
      EXPLICIT_TLS_FLAG=1
    fi
    ;;
esac

if [[ $EXPLICIT_TLS_FLAG -eq 0 && $ENABLE_TLS -eq 0 && -n "${DOMAIN:-}" ]]; then
  ENABLE_TLS=1
fi

cmd=(uvicorn app:app --host "$HOST" --port "$PORT" --workers "$WORKERS" --timeout-keep-alive "$KEEP_ALIVE")

if [[ $ENABLE_TLS -eq 1 ]]; then
  if [[ -n "$CERT" && -n "$KEY" && -f "$CERT" && -f "$KEY" ]]; then
    echo "[start_uvicorn] TLS enabled (cert: $CERT)"
    cmd+=(--ssl-certfile "$CERT" --ssl-keyfile "$KEY")
  else
    echo "[start_uvicorn] TLS requested but certificate missing; falling back to HTTP" >&2
  fi
else
  echo "[start_uvicorn] TLS disabled for localhost access"
fi

exec "${cmd[@]}"

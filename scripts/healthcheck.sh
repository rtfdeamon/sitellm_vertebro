#!/usr/bin/env bash
set -euo pipefail

PORT=${APP_PORT:-${PORT:-8000}}

raw_tls=${APP_ENABLE_TLS:-}
case "${raw_tls,,}" in
  1|true|yes)
    USE_TLS=1
    ;;
  *)
    USE_TLS=0
    ;;
esac

if [[ $USE_TLS -eq 0 && -n "${DOMAIN:-}" ]]; then
  USE_TLS=1
fi

if [[ $USE_TLS -eq 0 && -n "${APP_SSL_CERT:-}" && -n "${APP_SSL_KEY:-}" ]]; then
  USE_TLS=1
fi

schemes=()
if [[ $USE_TLS -eq 1 ]]; then
  schemes+=(https)
fi
schemes+=(http)

for scheme in "${schemes[@]}"; do
  CURL_OPTS=(--fail --silent --show-error)
  if [[ $scheme == https ]]; then
    CURL_OPTS+=(--insecure)
  fi
  TARGETS=("${scheme}://127.0.0.1:${PORT}/healthz" "${scheme}://127.0.0.1:${PORT}/health" "${scheme}://127.0.0.1:${PORT}/")
  for url in "${TARGETS[@]}"; do
    if curl "${CURL_OPTS[@]}" "$url" >/dev/null 2>&1; then
      exit 0
    fi
  done
done

exit 1

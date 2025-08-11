#!/usr/bin/env bash
set -euo pipefail

# Параметры запуска uvicorn
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
APP_MODULE="${APP_MODULE:-app.main:app}"
WORKERS="${WEB_CONCURRENCY:-1}"

echo "[+] Starting API: ${APP_MODULE} on ${HOST}:${PORT} (workers=${WORKERS})"

# Стартуем uvicorn в foreground — пусть PID будет PID процесса контейнера
exec uvicorn "${APP_MODULE}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --workers "${WORKERS}"

# Если когда-то понадобится «тёплый» прогрев/краулить:
# ENABLE_INITIAL_CRAWL=1 CRAWL_START_URL=https://example.org
# Тогда можно раскомментировать блок ниже и дополнить командой проекта:
# if [[ "${ENABLE_INITIAL_CRAWL:-0}" = "1" ]]; then
#   if [[ -n "${CRAWL_START_URL:-}" ]]; then
#     echo "[i] Initial crawl from ${CRAWL_START_URL} ..."
#     python -m app.crawler --url "${CRAWL_START_URL}" || echo "[!] Initial crawl failed, continue."
#   else
#     echo "[i] ENABLE_INITIAL_CRAWL=1 but CRAWL_START_URL is empty. Skipping."
#   fi
# fi

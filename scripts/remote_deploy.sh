#!/usr/bin/env bash

# Remote one-liner deploy helper.
# Usage:
#   scripts/remote_deploy.sh user@server [--dir /opt/sitellm_vertebro] [--url https://example.com] [--domain example.com] [--repo URL] [-i key] [-p 22]
# Defaults:
#   APP_DIR=/opt/sitellm_vertebro
#   REPO_URL=https://github.com/rtfdeamon/sitellm_vertebro.git

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 user@server [--dir DIR] [--url URL] [--repo REPO_URL] [-i key] [-p port]" >&2
  exit 1
fi

HOST=$1; shift
APP_DIR=/opt/sitellm_vertebro
CRAWL_START_URL=${CRAWL_START_URL:-}
DOMAIN=${DOMAIN:-}
REPO_URL=https://github.com/rtfdeamon/sitellm_vertebro.git
SSH_OPTS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) APP_DIR="$2"; shift 2 ;;
    --url) CRAWL_START_URL="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    -i) SSH_OPTS+=("-i" "$2"); shift 2 ;;
    -p) SSH_OPTS+=("-p" "$2"); shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

echo "[remote-deploy] Target: $HOST, APP_DIR=$APP_DIR"

# Check for curl remotely
if ssh "${SSH_OPTS[@]}" "$HOST" 'command -v curl >/dev/null 2>&1'; then
  echo "[remote-deploy] Using remote curl to run bootstrap"
  ssh "${SSH_OPTS[@]}" "$HOST" \
    "APP_DIR='$APP_DIR' REPO_URL='$REPO_URL' CRAWL_START_URL='$CRAWL_START_URL' DOMAIN='$DOMAIN' bash -lc 'curl -fsSL https://raw.githubusercontent.com/rtfdeamon/sitellm_vertebro/main/scripts/bootstrap.sh | bash'"
else
  echo "[remote-deploy] No curl on remote, sending local bootstrap.sh"
  SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
  ssh "${SSH_OPTS[@]}" "$HOST" \
    "APP_DIR='$APP_DIR' REPO_URL='$REPO_URL' CRAWL_START_URL='$CRAWL_START_URL' DOMAIN='$DOMAIN' bash -s" < "$SCRIPT_DIR/bootstrap.sh"
fi

echo "[remote-deploy] Running rollout"
ssh "${SSH_OPTS[@]}" "$HOST" \
  "APP_DIR='$APP_DIR' BRANCH='main' bash -lc 'cd "'$APP_DIR'" && bash scripts/rollout.sh'"

echo "[remote-deploy] Done"

#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR=${1:-certs}
CERT_FILE=${TARGET_DIR%/}/server.crt
KEY_FILE=${TARGET_DIR%/}/server.key
CONFIG_FILE="${TARGET_DIR%/}/openssl.cnf"

if [[ -f "$CERT_FILE" && -f "$KEY_FILE" ]]; then
  echo "[generate_cert] Existing certificate found in $TARGET_DIR"
  exit 0
fi

mkdir -p "$TARGET_DIR"

cat >"$CONFIG_FILE" <<'CFG'
[req]
default_bits        = 4096
default_md          = sha256
prompt              = no
distinguished_name  = dn
req_extensions      = v3_req

[dn]
C                   = RU
ST                  = Local
L                   = Local
O                   = SiteLLM
OU                  = DevOps
CN                  = localhost

[v3_req]
subjectAltName      = @alt_names
keyUsage            = digitalSignature, keyEncipherment
extendedKeyUsage    = serverAuth

[alt_names]
DNS.1               = localhost
IP.1                = 127.0.0.1
CFG

openssl req -x509 -nodes -days 825 -newkey rsa:4096 \
  -keyout "$KEY_FILE" -out "$CERT_FILE" \
  -config "$CONFIG_FILE" >/dev/null 2>&1

chmod 600 "$KEY_FILE"
rm -f "$CONFIG_FILE"

printf '[✓] Self-signed certificate generated at %s\n' "$TARGET_DIR"

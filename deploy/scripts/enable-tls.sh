#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_lib.sh"
load_env

usage() {
  cat <<'EOF'
Usage: enable-tls.sh --cert <path> --key <path>

Copies TLS certificate and private key into deploy/certs/,
activates the HTTPS Nginx config, and reloads Nginx.

Options:
  --cert <path>   Path to the server certificate (PEM)
  --key  <path>   Path to the private key (PEM)
  --help          Show this help

The certificate file may include intermediate CA certs (bundle).
For enterprise internal CA, concatenate: server cert + intermediate(s).

Example:
  ./scripts/enable-tls.sh --cert /tmp/mica.crt --key /tmp/mica.key
EOF
  exit 0
}

CERT_FILE=""
KEY_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cert) CERT_FILE="$2"; shift 2 ;;
    --key)  KEY_FILE="$2";  shift 2 ;;
    --help) usage ;;
    *) log_err "Unknown option: $1"; exit 1 ;;
  esac
done

[[ -z "$CERT_FILE" ]] && { log_err "--cert is required"; exit 1; }
[[ -z "$KEY_FILE" ]]  && { log_err "--key is required";  exit 1; }
[[ -f "$CERT_FILE" ]] || { log_err "Certificate file not found: $CERT_FILE"; exit 1; }
[[ -f "$KEY_FILE" ]]  || { log_err "Key file not found: $KEY_FILE";          exit 1; }

log_head "Enabling TLS for Mica"

CERTS_DIR="${DEPLOY_DIR}/certs"
NGINX_CONF_DIR="${DEPLOY_DIR}/nginx/conf.d"
TEMPLATE="${NGINX_CONF_DIR}/mica-tls.conf.template"

[[ -f "$TEMPLATE" ]] || { log_err "TLS config template not found: $TEMPLATE"; exit 1; }

log_info "Validating certificate..."
if ! openssl x509 -in "$CERT_FILE" -noout 2>/dev/null; then
  log_err "Invalid certificate file (not a valid PEM X.509 certificate)"
  exit 1
fi

log_info "Validating private key..."
if ! openssl rsa -in "$KEY_FILE" -check -noout 2>/dev/null && \
   ! openssl ec -in "$KEY_FILE" -check -noout 2>/dev/null; then
  log_err "Invalid private key file"
  exit 1
fi

CERT_MOD=$(openssl x509 -in "$CERT_FILE" -noout -modulus 2>/dev/null | openssl md5)
KEY_MOD=$(openssl rsa -in "$KEY_FILE" -noout -modulus 2>/dev/null | openssl md5)
if [[ "$CERT_MOD" != "$KEY_MOD" ]]; then
  log_err "Certificate and private key do not match (modulus mismatch)"
  exit 1
fi

SUBJECT=$(openssl x509 -in "$CERT_FILE" -noout -subject 2>/dev/null)
EXPIRY=$(openssl x509 -in "$CERT_FILE" -noout -enddate 2>/dev/null | cut -d= -f2)
log_info "Certificate: $SUBJECT"
log_info "Expires: $EXPIRY"

mkdir -p "$CERTS_DIR"
cp "$CERT_FILE" "${CERTS_DIR}/server.crt"
cp "$KEY_FILE"  "${CERTS_DIR}/server.key"
chmod 644 "${CERTS_DIR}/server.crt"
chmod 600 "${CERTS_DIR}/server.key"
log_ok "Certificate and key installed to ${CERTS_DIR}/"

if [[ -f "${NGINX_CONF_DIR}/mica.conf" ]]; then
  cp "${NGINX_CONF_DIR}/mica.conf" "${NGINX_CONF_DIR}/mica.conf.bak"
  log_info "Backed up mica.conf → mica.conf.bak"
fi

cp "$TEMPLATE" "${NGINX_CONF_DIR}/mica.conf"
log_ok "Nginx config switched to TLS mode"

log_info "Restarting Nginx..."
(cd "$DEPLOY_DIR" && docker compose restart nginx)
log_ok "Nginx restarted"

sleep 2
HTTPS_PORT="${HTTPS_PORT:-443}"
if curl -sk "https://localhost:${HTTPS_PORT}/health" >/dev/null 2>&1; then
  log_ok "HTTPS smoke test passed"
else
  log_warn "HTTPS smoke test failed — check 'docker compose logs nginx'"
  log_warn "HTTP→HTTPS redirect is active; if curl can't verify the cert, that's expected for internal CA"
fi

log_head "TLS enabled successfully"
log_info "HTTP  → https redirect (port ${HTTP_PORT:-80})"
log_info "HTTPS → active (port ${HTTPS_PORT})"
log_info ""
log_info "For internal CA: users must install the CA root certificate in their browsers/OS."

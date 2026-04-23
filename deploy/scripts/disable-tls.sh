#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_lib.sh"
load_env

log_head "Disabling TLS for Mica"

NGINX_CONF_DIR="${DEPLOY_DIR}/nginx/conf.d"

cp "${NGINX_CONF_DIR}/mica.conf.default" "${NGINX_CONF_DIR}/mica.conf"
log_ok "Restored HTTP-only Nginx config from default"

log_info "Restarting Nginx..."
(cd "$DEPLOY_DIR" && docker compose restart nginx)
log_ok "Nginx restarted — HTTP only on port ${HTTP_PORT:-80}"

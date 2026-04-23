#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_lib.sh"
load_env

log_head "Disabling TLS for Mica"

NGINX_CONF_DIR="${DEPLOY_DIR}/nginx/conf.d"

if [[ -f "${NGINX_CONF_DIR}/mica.conf.bak" ]]; then
  cp "${NGINX_CONF_DIR}/mica.conf.bak" "${NGINX_CONF_DIR}/mica.conf"
  log_ok "Restored HTTP-only Nginx config from backup"
else
  cat > "${NGINX_CONF_DIR}/mica.conf" <<'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Accept-Language $http_accept_language;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://backend:8000/health;
    }

    location / {
        proxy_pass http://frontend:80/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX
  log_ok "Wrote default HTTP-only Nginx config"
fi

log_info "Restarting Nginx..."
(cd "$DEPLOY_DIR" && docker compose restart nginx)
log_ok "Nginx restarted — HTTP only on port ${HTTP_PORT:-80}"

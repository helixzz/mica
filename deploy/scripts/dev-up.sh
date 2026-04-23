#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
cd "$DEPLOY_DIR"

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "[dev-up] Created .env from .env.example"
fi

if [[ ! -f nginx/conf.d/mica.conf ]]; then
    cp nginx/conf.d/mica.conf.default nginx/conf.d/mica.conf
    echo "[dev-up] Created nginx/conf.d/mica.conf from default"
fi

echo "[dev-up] Building images..."
docker compose build

echo "[dev-up] Starting stack..."
docker compose up -d

echo ""
echo "=========================================================="
echo "  Mica | 觅采 is starting up..."
echo ""

LAN_IPS=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -vE '^(127\.|172\.(17|18|19|20)\.)' || hostname -I | tr ' ' '\n' | grep -v ':')

HTTP_PORT_EFFECTIVE="${HTTP_PORT:-8900}"
echo "  Local:     http://localhost:${HTTP_PORT_EFFECTIVE}"
if [[ -n "$LAN_IPS" ]]; then
    for ip in $LAN_IPS; do
        echo "  LAN:       http://$ip:${HTTP_PORT_EFFECTIVE}"
    done
fi
echo "  API docs:  http://localhost:${HTTP_PORT_EFFECTIVE}/api/docs"
echo ""
echo "  Test users (password: MicaDev2026!):"
echo "    alice  — IT Buyer"
echo "    bob    — Department Manager"
echo "    carol  — Finance Auditor"
echo "    dave   — Procurement Manager"
echo "    admin  — Administrator"
echo ""
echo "  View logs:   docker compose logs -f"
echo "  Stop stack:  ./scripts/dev-down.sh"
echo "=========================================================="

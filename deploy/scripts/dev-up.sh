#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
cd "$DEPLOY_DIR"

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "[dev-up] Created .env from .env.example"
fi

echo "[dev-up] Building images..."
docker compose build

echo "[dev-up] Starting stack..."
docker compose up -d

echo ""
echo "=========================================================="
echo "  Mica | 觅采 is starting up..."
echo ""
echo "  Frontend:  http://localhost"
echo "  API docs:  http://localhost/api/docs"
echo "  Postgres:  localhost:5432"
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

#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"
echo "[dev-down] Stopping stack..."
docker compose down
echo "[dev-down] Stack stopped. Data preserved in volume mica_postgres_data."
echo "           To wipe data: docker volume rm mica_postgres_data"

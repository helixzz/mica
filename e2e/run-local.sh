#!/usr/bin/env bash
#
# One command to run the Playwright suite against a throwaway database.
#
#   ./e2e/run-local.sh                 # everything
#   ./e2e/run-local.sh tests/rfq-collection.spec.ts
#
# Why this exists: specs that need business objects (an order, a sent RFQ) used to
# skip, so every feature ended up being accepted by hand. This seeds what the specs
# need first, then runs them for real.
#
# Requirements: PostgreSQL reachable as in E2E_DATABASE_URL, backend venv at
# ../backend/.venv (or BACKEND_PYTHON), node deps installed in e2e/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_URL="${E2E_DATABASE_URL:-postgresql+asyncpg://mica:mica@localhost:5432/mica_e2e}"
PSQL_URL="${E2E_PSQL_URL:-postgresql://mica:mica@localhost:5432/mica_e2e}"
BACKEND_PORT="${E2E_BACKEND_PORT:-8012}"
FRONTEND_PORT="${E2E_FRONTEND_PORT:-5178}"
PYTHON="${BACKEND_PYTHON:-$REPO_ROOT/backend/.venv/bin/python}"
SPEC="${1:-}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "==> database: $PSQL_URL"
# Probe with a socket: the psql client is not always installed, and a missing client
# must not look like a missing database.
"$PYTHON" -c "import socket,sys; socket.create_connection((sys.argv[1], int(sys.argv[2])), 2).close()" \
  "${E2E_DB_HOST:-127.0.0.1}" "${E2E_DB_PORT:-5432}"

echo "==> migrations"
(cd "$REPO_ROOT/backend" && DATABASE_URL="$DB_URL" "$PYTHON" -m alembic upgrade head >/dev/null)

echo "==> seed"
(cd "$REPO_ROOT/backend" && DATABASE_URL="$DB_URL" APP_ENV=development "$PYTHON" "$REPO_ROOT/e2e/seed_data.py")

echo "==> backend :$BACKEND_PORT"
mkdir -p /tmp/mica-e2e-media
(cd "$REPO_ROOT/backend" && DATABASE_URL="$DB_URL" APP_ENV=development \
  MEDIA_ROOT=/tmp/mica-e2e-media \
  "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
  >/tmp/mica-e2e-backend.log 2>&1) &
BACKEND_PID=$!

echo "==> frontend :$FRONTEND_PORT"
(cd "$REPO_ROOT/frontend" && VITE_API_TARGET="http://127.0.0.1:$BACKEND_PORT" \
  npx vite --port "$FRONTEND_PORT" --host 127.0.0.1 \
  >/tmp/mica-e2e-frontend.log 2>&1) &
FRONTEND_PID=$!

for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1 && break
  sleep 1
done
for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null 2>&1 && break
  sleep 1
done

echo "==> playwright"
cd "$REPO_ROOT/e2e"
BASE_URL="http://127.0.0.1:$FRONTEND_PORT" npx playwright test ${SPEC:-} --reporter=list

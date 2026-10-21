#!/usr/bin/env bash
#
# Everything CI checks, in one command, before a release.
#
#   ./scripts/verify.sh            # lint + types + tests + build + e2e (if db reachable)
#   ./scripts/verify.sh --fast     # skip the E2E suite
#
# Why this exists: release checks used to be "backend tests + type-check + build",
# which quietly skipped `npm test`. Six releases shipped without a What's new entry
# because the guard that catches that lives in a frontend test. A checklist you have
# to remember is not a check.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAST=0
[ "${1:-}" = "--fast" ] && FAST=1

# Worktrees share the main checkout's virtualenv, so look in both places.
find_venv() {
  for candidate in "$REPO_ROOT/backend/.venv" "$REPO_ROOT/../mica/backend/.venv"; do
    [ -x "$candidate/bin/python" ] && { echo "$candidate"; return; }
  done
  echo ""
}
VENV="${BACKEND_VENV:-$(find_venv)}"
if [ -z "$VENV" ]; then
  echo "backend virtualenv not found; set BACKEND_VENV to its directory" >&2
  exit 1
fi
PYTHON="${BACKEND_PYTHON:-$VENV/bin/python}"
RUFF="${BACKEND_RUFF:-$VENV/bin/ruff}"

step() { printf '\n==> %s\n' "$1"; }

step "backend: lint + format"
cd "$REPO_ROOT/backend"
"$RUFF" check app tests
"$RUFF" format --check app tests

step "backend: tests"
"$PYTHON" -m pytest tests/ -q

step "frontend: types"
cd "$REPO_ROOT/frontend"
npm run type-check

step "frontend: unit tests"
npm test

step "frontend: build"
npm run build

if [ "$FAST" -eq 0 ]; then
  step "e2e"
  if command -v psql >/dev/null 2>&1 && psql "${E2E_PSQL_URL:-postgresql://mica:mica@localhost:5432/mica_e2e}" -c 'SELECT 1' >/dev/null 2>&1; then
    "$REPO_ROOT/e2e/run-local.sh"
  else
    echo "skipped: no e2e database reachable (set E2E_PSQL_URL, or run e2e/run-local.sh)"
  fi
fi

printf '\n✅ all checks passed\n'

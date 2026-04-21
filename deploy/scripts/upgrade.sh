#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "${SCRIPT_DIR}/_lib.sh"
load_env

TAG=""; SKIP_BACKUP=0; DRY_RUN=0; NO_AUTO_ROLLBACK=0
while (( $# )); do
  case "$1" in
    --tag) TAG="$2"; shift 2 ;;
    --skip-backup) SKIP_BACKUP=1; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --no-auto-rollback) NO_AUTO_ROLLBACK=1; shift ;;
    --help|-h) sed -n '2,20p' "$0"; exit 0 ;;
    *) log_err "Unknown arg: $1"; exit 1 ;;
  esac
done

[[ -z "${TAG}" ]] && TAG="$(git_describe)"

mkdir -p "${DEPLOY_DIR}/logs"
LOG_FILE="${DEPLOY_DIR}/logs/upgrade-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "${LOG_FILE}") 2>&1

BACKUP_ARCHIVE=""
START_SHA="$(git_sha)"
START_EPOCH="$(date +%s)"

rollback() {
  local code=$?
  trap - ERR EXIT
  if (( NO_AUTO_ROLLBACK )); then
    log_err "Upgrade failed (exit ${code})."
    [[ -n "${BACKUP_ARCHIVE}" ]] && log_err "To rollback manually: ${SCRIPT_DIR}/restore.sh ${BACKUP_ARCHIVE} --yes-i-know --skip-confirm"
    exit 8
  fi
  if [[ -z "${BACKUP_ARCHIVE}" ]]; then
    log_err "Upgrade failed (exit ${code}) and no backup exists. Manual recovery required."; exit 9
  fi
  log_err "Upgrade failed (exit ${code}). Auto-rollback from ${BACKUP_ARCHIVE}…"
  if "${SCRIPT_DIR}/restore.sh" "${BACKUP_ARCHIVE}" --yes-i-know --skip-confirm; then
    log_warn "Rollback complete. Upgrade aborted."; exit 8
  else
    log_err "Rollback FAILED. System may be in inconsistent state."; exit 9
  fi
}

log_head "Mica Upgrade · from ${START_SHA} → ${TAG}  $((( DRY_RUN )) && printf '(dry-run)' || printf '')"
(( DRY_RUN )) && log_warn "DRY-RUN mode: will not modify system state"

log_info "[preflight] docker compose v2"
require_compose_v2 || exit 2
log_info "[preflight] disk space ≥ 5 GB free"
FREE_GB="$(df -BG --output=avail /var/lib/docker 2>/dev/null | tail -1 | tr -dc '0-9' || echo 0)"
if (( FREE_GB < 5 )); then log_err "only ${FREE_GB}G free in /var/lib/docker"; exit 2; fi
log_ok "disk: ${FREE_GB}G free"

log_info "[preflight] current containers healthy"
if ! wait_healthy 30; then
  log_err "Pre-upgrade containers are NOT healthy. Fix that first."
  compose ps
  exit 2
fi
log_ok "all 4 containers healthy pre-upgrade"

if (( DRY_RUN )); then
  log_info "would: ./backup.sh"
  log_info "would: docker compose build"
  log_info "would: docker compose stop backend frontend nginx"
  log_info "would: docker compose run --rm migrate alembic upgrade head"
  log_info "would: docker compose up -d"
  log_info "would: wait_healthy 120"
  log_info "would: smoke_test"
  printf '\n%sDry-run complete. No changes made.%s\n' "${C_GRN}${C_BOLD}" "${C_RST}"
  exit 0
fi

trap rollback ERR

if (( ! SKIP_BACKUP )); then
  log_info "[1/6] pre-upgrade backup"
  BACKUP_ARCHIVE="$("${SCRIPT_DIR}/backup.sh" 2>&1 | tee /dev/stderr | grep -oE "${DEPLOY_DIR}/backups/mica-[^ ]*\.tar\.gz" | head -1 || true)"
  if [[ -z "${BACKUP_ARCHIVE}" || ! -f "${BACKUP_ARCHIVE}" ]]; then
    log_err "backup.sh produced no archive"; exit 3
  fi
  log_ok "backup saved: ${BACKUP_ARCHIVE}"
else
  log_warn "SKIP-BACKUP requested — rollback will not be possible"
fi

log_info "[2/6] docker compose build"
compose build || exit 4
log_ok "images built"

log_info "[3/6] stopping backend/frontend/nginx (postgres stays up)"
compose stop backend frontend nginx >/dev/null

log_info "[4/6] alembic upgrade head"
compose run --rm migrate alembic upgrade head || exit 5
log_ok "migration done"

log_info "[5/6] starting containers"
compose up -d >/dev/null

log_info "[6/6] waiting for health (up to 120s)"
if ! wait_healthy 120; then compose ps; exit 6; fi
log_ok "all containers healthy"

log_info "smoke test"
if ! smoke_test; then exit 7; fi

trap - ERR
DURATION=$(( $(date +%s) - START_EPOCH ))
END_SHA="$(git_sha)"
printf '\n%s✓ Upgrade complete%s\n' "${C_GRN}${C_BOLD}" "${C_RST}"
printf '  from:    %s\n' "${START_SHA}"
printf '  to:      %s (%s)\n' "${END_SHA}" "${TAG}"
printf '  backup:  %s\n' "${BACKUP_ARCHIVE:-(skipped)}"
printf '  took:    %ss\n' "${DURATION}"
printf '  log:     %s\n' "${LOG_FILE}"

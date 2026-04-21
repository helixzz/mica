#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "${SCRIPT_DIR}/_lib.sh"
load_env

ARCHIVE=""; YES_I_KNOW=0; SKIP_MEDIA=0; SKIP_CONFIRM=0
while (( $# )); do
  case "$1" in
    --yes-i-know) YES_I_KNOW=1; shift ;;
    --skip-media) SKIP_MEDIA=1; shift ;;
    --skip-confirm) SKIP_CONFIRM=1; shift ;;
    --help|-h) sed -n '2,20p' "$0"; exit 0 ;;
    -*) log_err "Unknown flag: $1"; exit 1 ;;
    *) ARCHIVE="$1"; shift ;;
  esac
done

[[ -z "${ARCHIVE}" ]] && { log_err "Usage: $0 <archive.tar.gz> --yes-i-know [--skip-media] [--skip-confirm]"; exit 1; }
[[ -f "${ARCHIVE}" ]] || { log_err "archive not found: ${ARCHIVE}"; exit 1; }
(( YES_I_KNOW )) || { log_err "Refusing to restore without --yes-i-know"; exit 1; }
tar -tzf "${ARCHIVE}" >/dev/null 2>&1 || { log_err "archive corrupt: ${ARCHIVE}"; exit 1; }

TMPDIR="$(mktemp -d -t mica-restore-XXXXXX)"
trap 'rm -rf "${TMPDIR}"' EXIT
tar xzf "${ARCHIVE}" -C "${TMPDIR}"

[[ -f "${TMPDIR}/manifest.json" ]] || { log_err "archive missing manifest.json"; exit 1; }
[[ -f "${TMPDIR}/mica.dump" ]]     || { log_err "archive missing mica.dump"; exit 1; }
if (( ! SKIP_MEDIA )); then
  [[ -f "${TMPDIR}/mica-media.tar.gz" ]] || { log_err "archive missing mica-media.tar.gz (use --skip-media to bypass)"; exit 1; }
fi

log_head "Mica Restore · ${ARCHIVE}"
printf '\n%s--- manifest ---%s\n' "${C_DIM}" "${C_RST}"
cat "${TMPDIR}/manifest.json"
printf '\n'

if (( ! SKIP_CONFIRM )); then
  if [[ ! -t 0 ]]; then log_err "No TTY for confirmation; pass --skip-confirm in scripted mode"; exit 1; fi
  printf '%sDatabase %s%s AND media volume %sWILL BE OVERWRITTEN%s. Type YES to proceed: ' \
    "${C_RED}${C_BOLD}" "${PG_DB}" "${C_RST}" "${C_RED}${C_BOLD}" "${C_RST}"
  read -r CONFIRM </dev/tty
  [[ "${CONFIRM}" == "YES" ]] || { log_err "Aborted by user"; exit 1; }
fi

log_info "stopping backend/frontend/nginx"
compose stop backend frontend nginx >/dev/null

log_info "recreating database ${PG_DB}"
compose exec -T postgres psql -U "${PG_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${PG_DB} WITH (FORCE);" >/dev/null
compose exec -T postgres psql -U "${PG_USER}" -d postgres -c "CREATE DATABASE ${PG_DB};" >/dev/null
log_ok "database recreated"

log_info "pg_restore (this may take a minute…)"
cat "${TMPDIR}/mica.dump" | compose exec -T postgres pg_restore -U "${PG_USER}" -d "${PG_DB}" --no-owner --no-privileges 2>&1 | tail -20 || true
log_ok "pg_restore complete"

if (( ! SKIP_MEDIA )); then
  log_info "clearing media volume"
  docker run --rm -v mica_media:/data alpine sh -c 'find /data -mindepth 1 -delete'
  log_info "untar media → mica_media volume"
  docker run --rm \
    -v mica_media:/data \
    -v "${TMPDIR}":/backup:ro \
    alpine tar xzf /backup/mica-media.tar.gz -C /data
  log_ok "media restored"
fi

log_info "starting containers"
compose up -d >/dev/null

log_info "waiting for health (up to 120s)…"
if wait_healthy 120; then log_ok "all containers healthy"; else log_err "containers failed health check"; compose ps; exit 1; fi

if smoke_test; then
  printf '\n%s✓ Restore complete%s\n' "${C_GRN}${C_BOLD}" "${C_RST}"
else
  log_err "smoke test failed — inspect containers manually"; exit 1
fi

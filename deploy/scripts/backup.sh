#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "${SCRIPT_DIR}/_lib.sh"
load_env

OUTPUT_DIR="${DEPLOY_DIR}/backups"
RETAIN_DAYS=14

while (( $# )); do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --retain)     RETAIN_DAYS="$2"; shift 2 ;;
    --help|-h)    sed -n '2,20p' "$0"; exit 0 ;;
    *) log_err "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"
if ! [[ -w "${OUTPUT_DIR}" ]]; then log_err "Not writable: ${OUTPUT_DIR}"; exit 1; fi

FREE_KB="$(df -k --output=avail "${OUTPUT_DIR}" 2>/dev/null | tail -1 | tr -dc '0-9' || echo 0)"
if (( FREE_KB < 2097152 )); then
  log_err "< 2 GB free at ${OUTPUT_DIR} (${FREE_KB} KB). Aborting."; exit 1
fi

TS="$(date +%Y%m%d-%H%M%S)"
SHA="$(git_sha)"
ARCHIVE="${OUTPUT_DIR}/mica-${TS}-${SHA}-$$.tar.gz"
TMPDIR="$(mktemp -d -t mica-backup-XXXXXX)"
trap 'rm -rf "${TMPDIR}"' EXIT

log_head "Mica Backup · ${TS} · ${SHA}"

log_info "postgres dump → ${TMPDIR}/mica.dump"
compose exec -T postgres pg_dump -U "${PG_USER}" -Fc "${PG_DB}" > "${TMPDIR}/mica.dump"
DB_BYTES="$(stat -c '%s' "${TMPDIR}/mica.dump")"
log_ok "db.dump: $(human_bytes "${DB_BYTES}")"

log_info "media snapshot → ${TMPDIR}/mica-media.tar.gz"
docker run --rm \
  -v mica_media:/data:ro \
  -v "${TMPDIR}":/backup \
  alpine tar czf /backup/mica-media.tar.gz -C /data . 2>/dev/null
MEDIA_BYTES="$(stat -c '%s' "${TMPDIR}/mica-media.tar.gz")"
log_ok "media.tar.gz: $(human_bytes "${MEDIA_BYTES}")"

PG_VER="$(compose exec -T postgres postgres --version 2>/dev/null | tr -d '\r' || echo unknown)"
cat > "${TMPDIR}/manifest.json" <<EOF
{
  "mica_version": "$(git_describe)",
  "git_sha": "${SHA}",
  "timestamp": "$(date -Iseconds)",
  "postgres_version": "${PG_VER}",
  "db_bytes": ${DB_BYTES},
  "media_bytes": ${MEDIA_BYTES},
  "db_name": "${PG_DB}",
  "db_user": "${PG_USER}"
}
EOF

log_info "combining archive → ${ARCHIVE}"
tar czf "${ARCHIVE}" -C "${TMPDIR}" mica.dump mica-media.tar.gz manifest.json
if ! tar -tzf "${ARCHIVE}" >/dev/null 2>&1; then
  log_err "archive verification failed"; rm -f "${ARCHIVE}"; exit 1
fi
TOTAL_BYTES="$(stat -c '%s' "${ARCHIVE}")"
log_ok "archive: $(human_bytes "${TOTAL_BYTES}")"

log_info "pruning archives older than ${RETAIN_DAYS} days"
PRUNED=0
while IFS= read -r -d '' old; do
  rm -f "${old}"
  PRUNED=$(( PRUNED + 1 ))
done < <(find "${OUTPUT_DIR}" -maxdepth 1 -name 'mica-*.tar.gz' -type f -mtime "+${RETAIN_DAYS}" -print0 2>/dev/null || true)
log_ok "pruned ${PRUNED} archive(s)"

printf '\n%sBackup complete:%s %s (%s)\n' "${C_GRN}${C_BOLD}" "${C_RST}" "${ARCHIVE}" "$(human_bytes "${TOTAL_BYTES}")"
printf '%s%s archives total in %s%s\n' \
  "${C_DIM}" "$(find "${OUTPUT_DIR}" -maxdepth 1 -name 'mica-*.tar.gz' 2>/dev/null | wc -l)" \
  "${OUTPUT_DIR}" "${C_RST}"

#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "${SCRIPT_DIR}/_lib.sh"
load_env

JSON_MODE=0
for arg in "$@"; do [[ "${arg}" == "--json" ]] && JSON_MODE=1; done

SVCS=(mica-postgres mica-backend mica-frontend mica-nginx)

declare -A ST UPT CPU MEM
for s in "${SVCS[@]}"; do
  ST[$s]="$(container_status "${s}")"
  if [[ "${ST[$s]}" == "absent" ]]; then
    UPT[$s]=0; CPU[$s]="n/a"; MEM[$s]="n/a"
    continue
  fi
  started="$(docker inspect -f '{{.State.StartedAt}}' "${s}" 2>/dev/null || echo "")"
  if [[ -n "${started}" ]]; then
    start_s="$(date -d "${started}" +%s 2>/dev/null || echo 0)"
    now_s="$(date +%s)"
    UPT[$s]=$(( now_s - start_s ))
  else
    UPT[$s]=0
  fi
  stats="$(docker stats --no-stream --format '{{.CPUPerc}}|{{.MemUsage}}' "${s}" 2>/dev/null || echo "|")"
  CPU[$s]="${stats%%|*}"
  MEM[$s]="${stats#*|}"; MEM[$s]="${MEM[$s]%% /*}"
  [[ -z "${CPU[$s]}" ]] && CPU[$s]="n/a"
  [[ -z "${MEM[$s]}" ]] && MEM[$s]="n/a"
done

DB_SIZE="unknown"; MEDIA_SIZE="unknown"; ALEMBIC="unknown"; SP_COUNT="unknown"
if [[ "${ST[mica-postgres]}" == "healthy" || "${ST[mica-postgres]}" == "up" ]]; then
  DB_SIZE="$(compose exec -T postgres psql -U "${PG_USER}" -d "${PG_DB}" -At -c "SELECT pg_size_pretty(pg_database_size('${PG_DB}'));" 2>/dev/null || echo "unknown")"
  ALEMBIC="$(compose exec -T postgres psql -U "${PG_USER}" -d "${PG_DB}" -At -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "unknown")"
  SP_COUNT="$(compose exec -T postgres psql -U "${PG_USER}" -d "${PG_DB}" -At -c "SELECT count(*) FROM system_parameters;" 2>/dev/null || echo "unknown")"
fi
MEDIA_SIZE="$(docker run --rm -v mica_media:/data alpine du -sh /data 2>/dev/null | awk '{print $1}' || echo "unknown")"

DISK_FREE="$(df -BG --output=avail /var/lib/docker 2>/dev/null | tail -1 | tr -dc '0-9' || echo "0")"

API_CODE="$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://localhost:${HTTP_PORT}/api/v1/auth/login" 2>/dev/null)"
[[ -z "${API_CODE}" ]] && API_CODE="000"
FE_CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${HTTP_PORT}/" 2>/dev/null)"
[[ -z "${FE_CODE}" ]] && FE_CODE="000"
API_OK=0; FE_OK=0
[[ "${API_CODE}" =~ ^4[0-9][0-9]$ ]] && API_OK=1
[[ "${FE_CODE}" == "200" ]] && FE_OK=1

OVERALL="healthy"; EXIT=0
for s in "${SVCS[@]}"; do
  case "${ST[$s]}" in
    healthy|up) ;;
    *) OVERALL="degraded"; EXIT=1 ;;
  esac
done
if (( ! API_OK || ! FE_OK )); then OVERALL="degraded"; [[ ${EXIT} -eq 0 ]] && EXIT=2; fi

if (( JSON_MODE )); then
  printf '{\n'
  printf '  "timestamp": "%s",\n' "$(date -Iseconds)"
  printf '  "overall": "%s",\n' "${OVERALL}"
  printf '  "containers": [\n'
  first=1
  for s in "${SVCS[@]}"; do
    (( first )) || printf ',\n'
    first=0
    printf '    {"name": "%s", "status": "%s", "uptime_s": %s, "cpu": "%s", "mem": "%s"}' \
      "${s}" "${ST[$s]}" "${UPT[$s]}" "${CPU[$s]}" "${MEM[$s]}"
  done
  printf '\n  ],\n'
  printf '  "disk_free_gb": %s,\n' "${DISK_FREE:-0}"
  printf '  "db_size": "%s",\n' "${DB_SIZE}"
  printf '  "media_size": "%s",\n' "${MEDIA_SIZE}"
  printf '  "alembic_head": "%s",\n' "${ALEMBIC}"
  printf '  "system_params_count": "%s",\n' "${SP_COUNT}"
  printf '  "api": {"status_code": %s, "ok": %s},\n' "${API_CODE}" "$(( API_OK ))"
  printf '  "frontend": {"status_code": %s, "ok": %s}\n' "${FE_CODE}" "$(( FE_OK ))"
  printf '}\n'
  exit ${EXIT}
fi

now="$(date '+%Y-%m-%d %H:%M:%S %Z')"
printf '%s%sMica Health Report @ %s%s\n' "${C_BOLD}" "${C_BLU}" "${now}" "${C_RST}"
printf '─────────────────────────────────────────\n'
printf '%-18s %-10s %-10s %-8s %-12s\n' Container Status Uptime CPU Mem
for s in "${SVCS[@]}"; do
  st="${ST[$s]}"
  color="${C_GRN}"
  case "${st}" in
    healthy|up) color="${C_GRN}" ;;
    unhealthy|exited|absent) color="${C_RED}" ;;
    *) color="${C_YLW}" ;;
  esac
  u="${UPT[$s]}"
  if (( u >= 86400 )); then uptime_str="$(( u/86400 ))d $(( (u%86400)/3600 ))h"
  elif (( u >= 3600 )); then uptime_str="$(( u/3600 ))h $(( (u%3600)/60 ))m"
  elif (( u > 0 )); then uptime_str="$(( u/60 ))m $(( u%60 ))s"
  else uptime_str="n/a"
  fi
  printf '%-18s %b%-10s%b %-10s %-8s %-12s\n' \
    "${s}" "${color}" "${st}" "${C_RST}" "${uptime_str}" "${CPU[$s]}" "${MEM[$s]}"
done
printf '\n'
printf 'DB size:           %s\n' "${DB_SIZE}"
printf 'Media size:        %s\n' "${MEDIA_SIZE}"
printf 'Disk free:         %sG\n' "${DISK_FREE:-?}"
printf 'Alembic head:      %s\n' "${ALEMBIC}"
printf 'System params:     %s configured\n' "${SP_COUNT}"
if (( API_OK )); then printf 'API smoke:         %s✓%s POST /api/v1/auth/login → %s\n' "${C_GRN}" "${C_RST}" "${API_CODE}"
else                  printf 'API smoke:         %s✗%s POST /api/v1/auth/login → %s\n' "${C_RED}" "${C_RST}" "${API_CODE}"
fi
if (( FE_OK )); then printf 'Frontend smoke:    %s✓%s GET / → %s\n' "${C_GRN}" "${C_RST}" "${FE_CODE}"
else                 printf 'Frontend smoke:    %s✗%s GET / → %s\n' "${C_RED}" "${C_RST}" "${FE_CODE}"
fi
printf '─────────────────────────────────────────\n'
if [[ "${OVERALL}" == "healthy" ]]; then
  printf 'Overall: %s✓ HEALTHY%s (exit 0)\n' "${C_GRN}${C_BOLD}" "${C_RST}"
else
  printf 'Overall: %s✗ DEGRADED%s (exit %s)\n' "${C_RED}${C_BOLD}" "${C_RST}" "${EXIT}"
fi
exit ${EXIT}

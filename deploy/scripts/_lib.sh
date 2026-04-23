#!/usr/bin/env bash
SCRIPT_DIR_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR_LIB}/.." && pwd)"
REPO_DIR="$(cd "${DEPLOY_DIR}/.." && pwd)"

if [[ -t 1 && -n "${TERM:-}" ]] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1; then
  C_RED="$(tput setaf 1)"; C_GRN="$(tput setaf 2)"; C_YLW="$(tput setaf 3)"
  C_BLU="$(tput setaf 4)"; C_DIM="$(tput dim)"; C_RST="$(tput sgr0)"; C_BOLD="$(tput bold)"
else
  C_RED=""; C_GRN=""; C_YLW=""; C_BLU=""; C_DIM=""; C_RST=""; C_BOLD=""
fi

log_info()  { printf '%s[INFO]%s  %s\n'  "${C_BLU}" "${C_RST}" "$*" >&2; }
log_ok()    { printf '%s[OK]%s    %s\n' "${C_GRN}" "${C_RST}" "$*" >&2; }
log_warn()  { printf '%s[WARN]%s  %s\n' "${C_YLW}" "${C_RST}" "$*" >&2; }
log_err()   { printf '%s[ERR]%s   %s\n' "${C_RED}" "${C_RST}" "$*" >&2; }
log_head()  { printf '\n%s%s═══ %s ═══%s\n' "${C_BOLD}" "${C_BLU}" "$*" "${C_RST}" >&2; }

load_env() {
  if [[ -f "${DEPLOY_DIR}/.env" ]]; then
    set -a; . "${DEPLOY_DIR}/.env"; set +a
  fi
  PG_USER="${POSTGRES_USER:-mica}"
  PG_DB="${POSTGRES_DB:-mica}"
  HTTP_PORT="${HTTP_PORT:-80}"
  HTTPS_PORT="${HTTPS_PORT:-443}"
  BACKEND_PORT="${BACKEND_PORT:-8000}"
}

compose() {
  ( cd "${DEPLOY_DIR}" && docker compose "$@" )
}

require_compose_v2() {
  if ! docker compose version >/dev/null 2>&1; then
    log_err "docker compose v2 is required"
    return 2
  fi
}

container_status() {
  local name="$1"
  local state health
  state="$(docker inspect -f '{{.State.Status}}' "${name}" 2>/dev/null || echo "absent")"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${name}" 2>/dev/null || echo "none")"
  if [[ "${health}" == "healthy" ]]; then echo "healthy"
  elif [[ "${health}" == "unhealthy" ]]; then echo "unhealthy"
  elif [[ "${state}" == "running" ]]; then echo "up"
  elif [[ "${state}" == "absent" ]]; then echo "absent"
  else echo "${state}"
  fi
}

wait_healthy() {
  local timeout="${1:-120}"; local deadline=$(( $(date +%s) + timeout ))
  local svcs=(mica-postgres mica-backend mica-frontend)
  local nginx_name
  nginx_name="$(docker ps --filter "name=mica.*nginx" --format '{{.Names}}' 2>/dev/null | head -1)"
  [[ -n "${nginx_name}" ]] && svcs+=("${nginx_name}")
  while [[ $(date +%s) -lt ${deadline} ]]; do
    local all_ok=1
    for s in "${svcs[@]}"; do
      local st; st="$(container_status "${s}")"
      if [[ "${st}" != "healthy" && "${st}" != "up" ]]; then all_ok=0; break; fi
    done
    if (( all_ok )); then return 0; fi
    sleep 2
  done
  return 1
}

smoke_test() {
  local base_url="http://localhost:${HTTP_PORT}"
  if [[ -f "${DEPLOY_DIR}/certs/server.crt" ]]; then
    base_url="https://localhost:${HTTPS_PORT:-443}"
  fi
  local api_code frontend_code
  api_code="$(curl -sk -o /dev/null -w '%{http_code}' -X POST "${base_url}/api/v1/auth/login" 2>/dev/null)"
  [[ -z "${api_code}" ]] && api_code="000"
  frontend_code="$(curl -sk -o /dev/null -w '%{http_code}' "${base_url}/" 2>/dev/null)"
  [[ -z "${frontend_code}" ]] && frontend_code="000"
  if [[ ! "${api_code}" =~ ^4[0-9][0-9]$ ]]; then
    log_err "API smoke failed: POST ${base_url}/api/v1/auth/login → ${api_code}"
    return 1
  fi
  if [[ "${frontend_code}" != "200" ]]; then
    log_err "Frontend smoke failed: GET ${base_url}/ → ${frontend_code}"
    return 1
  fi
  log_ok "smoke: API=${api_code} frontend=${frontend_code}"
  return 0
}

git_sha() {
  ( cd "${REPO_DIR}" && git rev-parse --short HEAD 2>/dev/null ) || echo "nogit"
}

git_describe() {
  ( cd "${REPO_DIR}" && git describe --tags --dirty 2>/dev/null ) || git_sha
}

human_bytes() {
  local b="${1:-0}"
  if   (( b >= 1073741824 )); then printf '%.2f GB' "$(awk "BEGIN{print ${b}/1073741824}")"
  elif (( b >= 1048576 ));    then printf '%.2f MB' "$(awk "BEGIN{print ${b}/1048576}")"
  elif (( b >= 1024 ));       then printf '%.2f KB' "$(awk "BEGIN{print ${b}/1024}")"
  else printf '%d B' "${b}"
  fi
}

has_jq() { command -v jq >/dev/null 2>&1; }

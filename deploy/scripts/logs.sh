#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
. "${SCRIPT_DIR}/_lib.sh"
load_env

SERVICE=""; SINCE=""; TAIL=""; FOLLOW=1; GREP_PAT=""; ERRORS_ONLY=0
while (( $# )); do
  case "$1" in
    --since)  SINCE="$2"; shift 2 ;;
    --tail)   TAIL="$2"; FOLLOW=0; shift 2 ;;
    --grep)   GREP_PAT="$2"; shift 2 ;;
    --errors-only) ERRORS_ONLY=1; shift ;;
    --no-follow) FOLLOW=0; shift ;;
    --help|-h) sed -n '2,20p' "$0"; exit 0 ;;
    -*) log_err "Unknown flag: $1"; exit 1 ;;
    *)  SERVICE="$1"; shift ;;
  esac
done

args=()
(( FOLLOW )) && args+=(--follow)
[[ -n "${TAIL}" ]]  && args+=(--tail "${TAIL}")
[[ -n "${SINCE}" ]] && args+=(--since "${SINCE}")

if [[ -n "${SERVICE}" ]]; then
  printf '%s=== mica-%s ===%s\n' "${C_BOLD}${C_BLU}" "${SERVICE}" "${C_RST}" >&2
  CMD=(compose logs "${args[@]}" "${SERVICE}")
else
  CMD=(compose logs "${args[@]}")
fi

if (( ERRORS_ONLY )); then
  "${CMD[@]}" 2>&1 | grep --color=auto -iE 'error|warn|critical|exception|traceback|failed' || true
elif [[ -n "${GREP_PAT}" ]]; then
  "${CMD[@]}" 2>&1 | grep --color=auto -E "${GREP_PAT}" || true
else
  "${CMD[@]}"
fi

# Payment execution hotfix release — v1.51.2

## Objective and authority
- Explicit authorization: commit, push, GitHub release, production deployment of the reviewed candidate.
- No production payment execution or business-record modification, destructive reset, volume removal, automatic DB restore, amend, force-push, or hook bypass.
- This delegated session owns only this workstream; lead-owned PROJECT_STATE and DECISIONS remain untouched. Agent state stays uncommitted.

## Confirmed release scope
- Local main and remote main start at `269fe07fae7e5be84226d78ffe0abf84984c3a5b`, v1.51.1; local main has no upstream configured.
- Production checkout `/home/ubuntu/mica` starts at the same commit, no tracked changes; untracked `.rsync-exclude` must be preserved.
- Candidate: shared schedule execution numeric-max numbering and schedule-before-PO locking, four new regression/support files, four version files, changelog. No migrations or frontend behavior changes.
- CHANGELOG release date updated to 2026-09-24; removed obsolete unpublished-candidate line.
- Prior lead evidence: 693 backend passed, 19 new regressions, coverage 71.96%, frontend type/build and Ruff passed; final isolated browser execution returned 200 with old 002 preserved/new 003 and correct amounts. Oracle follow-up had no blockers.

## Deployment safety decision
- Production compose path: `/home/ubuntu/mica/deploy/docker-compose.yml`; live backend media mount is `/data/media` (bind mount).
- Remote upgrade/backup/lib/compose checksums match local files. `backup.sh` incorrectly snapshots legacy `mica_media`; `upgrade.sh` checks out paths rather than moving HEAD and may invoke destructive DB restoration. `health.sh` assumes obsolete nginx naming and issues a POST smoke request.
- Use the documented backup/build/migrate/start sequence manually, substituting the observed bind mount for the obsolete named volume and GET-only checks. Back up database, actual media and configuration before source/container changes; preserve prior images. Do not invoke those unsafe script paths.
- Production has ~14 GiB Docker filesystem free and ~313 MiB media. No production cron backup script was found in inspected standard locations.
- Commit plan: fix plus all direct tests; backend versions; frontend version; README release link; dated changelog. Only those ten files will be staged.

## Publication and preparation
- Pushed five commits: `de87f5c` fix/tests; `1345c05` backend versions; `52ad544` frontend version; `0994184` README; `a662921804fbf74f0532a3c91c7110554499eda7` changelog/release target.
- Release: https://github.com/helixzz/mica/releases/tag/v1.51.2 (explicit full-SHA target).
- Release preflight: Ruff check passed; 95 files formatted; frontend type-check/build passed; definitive PTY run `pty_aec3d4a2` exited 0 with 19 passed in 1.97s. Earlier combined test command output ended before summary, so it is not claimed as a completed full-suite rerun.
- Environment-correct basedpyright reports only nine known existing errors (eight untouched service bare-dict annotations plus config PostgresDsn assignment); no execution/test errors. Required LSP was run on all six Python candidate files and showed the known workspace environment issues.
- Production backup folder `/data/backups/mica-v1.51.2-jerVcoi5`: PostgreSQL custom dump (pg_restore list validated), actual media archive, private config archive (env/certs/nginx), source/image identity. Archives remain only on production with private directory permissions.
- Preparation PTY `pty_69ba2ea3` exited 0: backup succeeded, production fast-forwarded to release SHA, backend/frontend `1.51.2` images built successfully.
- Temporary non-secret operational scripts: `/tmp/opencode/mica-1512-prepare.sh`, `/tmp/opencode/mica-1512-activate.sh`, `/tmp/opencode/mica-1512-verify.sh`. Activation was designed for no-deps/pull-never exact-version images, production APP_ENV guard, no-op migration at existing 0055, version-only env patch, Compose health wait and nginx reload. It did not finish; see below. Do not rerun blindly.
- CI **success**, wait PTY `pty_8aadc1c1` exited 0: https://github.com/helixzz/mica/actions/runs/35975081791.

## Activation anomaly and verified outcome
- First activation `pty_5bd47dd5` exited 0 after no-op Alembic output, without the required activation marker. Compose run's default interactive stdin consumed the rest of the SSH-streamed script. Exit 0 was not accepted as success.
- Updated only the temporary script to disable Compose stdin attachment. Continuation `pty_2034821e` exited 1 at the existing-backend APP_ENV guard because the backend container was being replaced concurrently; it never reached the env patch or its own container replacement.
- Immediate inspection found backend/frontend/scheduler already on **1.51.2**, migrate exited 0, nginx restarted. This is an observed concurrent rollout, **not attributed to this session's incomplete activation command**. Further production mutations stopped to avoid competing operations.
- **Outstanding configuration mismatch:** `/home/ubuntu/mica/deploy/.env` still had `APP_VERSION=1.51.1` at inspection. Lead must coordinate with the concurrent deployer and persist 1.51.2 before any future unqualified Compose up; otherwise it can select old images. This session did not edit .env.
- One final read-only verification script exited 0 at ~2026-09-24 08:32 UTC: production Git HEAD exact release SHA, tracked tree clean, only original `.rsync-exclude` untracked; backend/scheduler/postgres/Cerbos healthy, frontend/nginx running.
- `GET /health`: healthy, version **1.51.2**, DB=true, Cerbos=true. `GET /`: backend version **1.51.2**. TLS frontend GET and proxied login-options GET both **200**. Alembic remains **0055**.
- Deployed source hashes equal local committed candidate: `payment_schedule.py` = `da1afbba218d375cff9786aca3877f8e1221b5ff874b364b3cdb0b5dcae90965`; `config.py` = `bb1b450cc11b8f15d28b6237591a08065334549d4208a1b82fd66d82533342dd`.
- Recent backend/scheduler logs show startup complete, scheduler six jobs, GET 200s; no traceback/error in inspected output. No production payment executed, business records changed, destructive restore, or volume deletion by this session.

## Handoff / remaining risks
- Published/pushed tagged code and current healthy production runtime verified. Backup retained under the private production directory above; old images/data/config retained.
- APP_VERSION mismatch resolved safely after rollout ownership cleared: the version-only production `.env` setting now persists `APP_VERSION=1.51.2`; Compose image resolution was read-only verified for backend/frontend `1.51.2`. No container restart or business write was performed by this config-only correction.
- Known pre-existing static limitation: backend LSP environment/import resolution and untouched service bare-dict/config PostgresDsn diagnostics. No suppressions or unrelated fixes authorized.
- Existing Dockerfiles resolve unpinned dependencies/base tags; production rebuild succeeded, but this hotfix does not introduce dependency locking. Runtime payment-execution proof remains the isolated browser/test evidence, deliberately not a real production payment.

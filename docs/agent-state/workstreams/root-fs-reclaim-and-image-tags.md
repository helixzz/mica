# Root-filesystem exhaustion: stale images and the tag that never changed

## Objective

Explain and fix a production root filesystem at 90% while `/data` — which holds
the database and media — sat at 3%.

## Diagnosis

| Mount | Size | Used | Free |
|---|---|---|---|
| `/dev/sda2` (root) | 98G | **83G (90%)** | 9.9G |
| `/dev/sdb1` (`/data`) | 200G | 4.6G (3%) | **196G** |

The root filesystem held **no business data**: `mica-postgres` bind-mounts
`/data/postgres` and `mica-backend` bind-mounts `/data/media`. It was almost
entirely Docker:

```
Images        125   73.02GB   reclaimable 61.38GB (84%)
Build Cache   152   19GB      reclaimable 9.617GB
Containers      7   1.368MB
Local Volumes   7   0B
```

`mica-frontend` and `mica-backend` each had 42 tagged versions, from **1.8.0**
through 1.55.1, spanning months.

## Two root causes

**1. The image tag never changed.** `docker-compose.yml` names the images
`mica-backend:${APP_VERSION}` / `mica-frontend:${APP_VERSION}`, and
`APP_VERSION` lives only in `.env`, which nothing in the upgrade path ever
updated. Every build therefore re-tagged the same name: the previous image was
orphaned into a dangling `<none>` layer, and the running containers ended up
labelled with an old version. v1.57.0 was being served by
`mica-frontend:1.55.1`.

**2. History was never pruned.** No cleanup step existed; images accumulated
since the project began.

## Reclaim

Executed in two steps, both authorized:

```bash
docker image prune -f          # dangling layers
docker builder prune -af       # build cache
docker rmi <102 historical tags>   # 1.51.0 and older; 1.55.0/1.55.1 kept as rollback points
```

| | Before | After |
|---|---|---|
| Root used | 83G (90%) | **22G (23%)** |
| Root free | 9.9G | **72G** |
| Images | 125 | 4 |
| Build cache | 19GB | 0 |

Roughly **66GB reclaimed**. The database and media were untouched throughout.

## Fix

`upgrade.sh` now writes the tag being deployed into `.env` after the checkout,
so each release produces a distinct, identifiable, prunable image.

That fix needed a second pass. `.env` is sourced by `load_env` via
`set -a; . .env`, so `APP_VERSION` was already **exported** into the script
process — and `docker compose` prefers an exported variable over the `.env`
file. Editing only the file changed nothing for the running build. v1.57.3 adds
`export APP_VERSION` in all three branches.

Verified on v1.57.3 → deployed twice, second run reported
`APP_VERSION already 1.57.3` and produced `mica-backend:1.57.3` /
`mica-frontend:1.57.3`, with the containers referencing the same tag. **`.env`,
image tags and container references now agree.**

## Correction to the released history

Both `mica-backend:1.55.1` and `mica-backend:1.57.2` were **misnamed** — each
held the code of a later release, because the tag lagged the checkout. Both were
deleted rather than kept as rollback points, since rolling back to a
misleadingly-named image is worse than not having one. Rollback should use
`upgrade.sh --tag vX.Y.Z`, which rebuilds from the tag and does not depend on
any locally retained image.

## Parallel-work incidents (2026-10-16)

Recorded because they cost real time and are avoidable:

1. **Version collision.** This workstream and a concurrent one both bumped to
   **v1.57.1**; the other `gh release create` won and this one moved to 1.57.2,
   then 1.57.3. `AGENTS.md` §8 now says: `git fetch --tags` and check
   `git rev-parse "v$VERSION"` before bumping.
2. **Shared working directory.** Another agent switched `/home/helixzz/mica` to
   its own branch mid-way; this session's `git merge` / `git add` / `git commit`
   then landed on *that* branch. Its real work was on its own worktree
   (`/home/helixzz/mica-v2fix`, branch `chore/drop-v2-release`) and was not
   affected, but `refactor/drop-v2-prefix` in the shared checkout now carries two
   commits from this session. All subsequent work here was done strictly inside
   the isolated worktree `../mica-feat-address-book`.
3. **`upgrade.sh` replaces itself while running.** bash reads a script by byte
   offset, so code introduced by the very checkout that deployment performs does
   not execute until the *next* run. Expect any change to `deploy/scripts/*` to
   take effect one deployment later.
4. **A stale exported variable beats a fresh `.env`.** See the fix above.

## Housekeeping note

Two items are still untidy and are not this workstream's to remove:

- `/home/ubuntu/mica/deploy/.env` had `APP_VERSION=1.55.1` for a long time; it is
  now `1.57.3` and maintained by the script.
- The shared checkout `/home/helixzz/mica` is left on `refactor/drop-v2-prefix`
  (someone else's branch, carrying two commits from this session). Switching it
  back to `main` is safe; it was deliberately left alone rather than touched
  while another agent may still be using it.

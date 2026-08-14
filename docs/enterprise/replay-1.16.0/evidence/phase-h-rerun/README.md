# Phase H Rerun Evidence — Offline Artifact Chain (Rebuilt Images)

Validator: `replay-116-b8-phase-h-rerun`
Branch: `ctyun/replay-116-b8-phase-h-rerun`
Head: `c7c98b220d49b8b651bf87f47850a9dff5ddbd6b`
Base: `codex/enterprise-candidate-1.16.0-20260718`
Date: 2026-08-14 (Asia/Shanghai)
Decision sheet: `/tmp/replay-116-phase-h-decision-sheet.md` options H1=A, H2=A, H3=A, H4=A, H5=A, H6=A, H7=A

## Verdict: PASS

The offline artifact chain rerun succeeded end-to-end with the **rebuilt**
enterprise images and the **hardened** B7 reuse gate:

- The reuse gate accepted the new API image (`dify-api-enterprise:1.16.0-enterprise`
  = `sha256:566bdf4c88cf1bf3be5f7f6c7c39b338d5f1973ebe10f115050d9ac527930680`).
- The manifest records `enterprise_commit = c7c98b220d...` (candidate HEAD) and
  api image id `sha256:566bdf4c88cf...`.
- On a FRESH PostgreSQL 15 database the migration head after API boot is
  **`e7c0a9d2b8f3`** (NOT `b416e5c4e702`), and all 12 marketplace ID/FK columns
  are **`uuid`**. This directly closes the release-blocking finding from the
  first Phase H run (the pre-fix API image stopped at `b416e5c4e702` with
  `VARCHAR(36)` columns).

## What ran (all PASS)

1. `scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse -OutputDir /tmp/replay-116-phase-h-rerun` — exit 0; reuse gate ACCEPTS the new API image (content check: migration file set match + `_align_snapshot_to_composition` present). See `reuse-gate-checkonly.log`.
2. `scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse -OutputDir /tmp/replay-116-phase-h-rerun` — exit 0, 5m53s; produced `dify-enterprise-offline-1.16.0-enterprise.tar` (8,276,790,272 B), `images-1.16.0-enterprise.txt`, `manifest-1.16.0-enterprise.json`. All dependency images reused locally (no pull). See `build-offline.log`.
3. `scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise` — exit 0; `dify-enterprise-config-1.16.0-enterprise.tar.gz` (32,036 B). See `config-package.log`.
4. `scripts/ci/check-enterprise-offline.sh` with synthetic 0600 pattern — exit 0, **13 PASS / 0 FAIL / 1 NOT_RUN** (NOT_RUN = image-bundle layer scan, OCI blob layout; same known B7 ceiling). See `offline-scan.log`, `secret-scan.log`.
5. `docker load < ...offline-1.16.0-enterprise.tar` — 12 images loaded (exit 0). See `docker-load.log`.
6. Isolated stack `dify-b8-phase-h-rerun`: temp override mapped every `./volumes/**`
   bind of the started services to named volumes `dify-b8-phase-h-rerun-*`; nginx
   on `127.0.0.1:18080:80` only; started `db_postgres redis api web nginx` with
   `--pull never` (db_postgres/redis needed for api to boot, both isolated with
   remapped volumes — same deviation as the first run). `init_permissions`
   one-shot ran first (storage chown so api can persist `.dify_secret_key`).
7. **Fresh PG15 migration head = `e7c0a9d2b8f3`**; marketplace ID/FK columns
   (id, source_app_id, source_tenant_id, submitter_account_id,
   reviewer_account_id, published_snapshot_id, asset_id) are **`uuid`** in both
   `enterprise_marketplace_assets` and `enterprise_marketplace_asset_snapshots`
   (12/12). See `migration-check.log`.
8. Smoke (minimal, H3-A): nginx `/` HTTP 200 (`phase-h-rerun-nginx-ok`); api
   `/health` via `/apihealth` HTTP 200 (`{"status":"ok","version":"1.16.0"}`);
   web `/webpage/signin` HTTP 200 (Next.js shell, html lang=en-US, Dify); web
   `/webpage/` HTTP 307 -> `/install` (fresh-DB install redirect). No `Pulling`
   line in the up log; enterprise images created 2026-08-14/08-11 (pre-existing)
   vs containers started 2026-08-13T16:30Z. See `smoke.log`, `pull-never-up.log`.
9. Teardown `docker compose -p dify-b8-phase-h-rerun down -v` — exit 0; no
   `dify-b8-phase-h-rerun-*` containers/volumes/networks remain; `docker/volumes/**`
   unchanged from baseline (myscale/oceanbase/opensearch/sandbox only, no new
   dirs); 1.15 `docker-*` stack untouched. See `teardown.log`.

## Deviations from plan (all recorded honestly)

1. **OutputDir handling**: `scripts/build-enterprise-offline.sh` joins
   `$REPO_ROOT/$OUTPUT_DIR` (line 51), so an absolute `-OutputDir /tmp/...`
   would write into `<repo>/tmp/...`. As in the Phase F Rebuild run, a transient
   untracked symlink `<repo>/tmp -> /tmp` was created before the build and
   removed after; output physically landed in `/tmp/replay-116-phase-h-rerun`.
   No tracked path was touched.
2. **Config-package member paths**: the check script requires
   `dist/offline/manifest-*.json` + `dist/offline/images-*.txt` inside the config
   archive, but `-OutputDir /tmp/...` made the members `tmp/replay-116-phase-h-rerun/...`
   (2 FAIL on the first scan attempt, exit 1). Fixed by re-running the config
   package against the gitignored `dist/offline` path (a transient symlink
   `dist/offline -> /tmp/replay-116-phase-h-rerun`, removed after) so physical
   files stayed under /tmp while tar members got the expected `dist/offline/...`
   paths. Final scan: 13 PASS / 0 FAIL / 1 NOT_RUN.
3. **Compose override merge tags**: compose v5 appended nginx base binds
   (`./volumes/certbot/...`) and ports (80/443) to the override instead of
   replacing them; `!override` tags on the nginx `volumes` and `ports` lists
   fixed it (validated via `compose config` before `up`). Same tag behavior the
   first Phase H run noted.
4. **Started `db_postgres` and `redis`** (isolated, volumes remapped to
   `dify-b8-phase-h-rerun-*` named volumes) in addition to `api web nginx`: the
   api image entrypoint requires Redis (`create_app`) and Postgres
   (`flask upgrade-db`) to boot. Same deviation as the first run.
5. **Ran `init_permissions` one-shot** (storage volume chown) so api could
   persist its generated `.dify_secret_key`. Same deviation as the first run.
6. **Custom nginx conf**: nginx was given a static config from /tmp (its own
   `nginx.conf` + `default.conf`, entrypoint `nginx -g 'daemon off;'`) instead of
   the repo templates, so no repo `docker/nginx/conf.d` writes and no
   `./volumes/certbot/**` binds were needed. Port `127.0.0.1:18080:80` only.

## Known limitations (honest)

- Same-daemon simulation: images already present locally, so `--pull never`
  cannot prove a truly offline host; a network-isolated Docker host remains
  NOT_RUN. No pull was attempted on this run (up log + pre-existing image
  timestamps).
- Image-bundle layer content scan NOT_RUN (Docker 29 OCI blob layout not matched
  by the B7 `*/layer.tar` scan; gate reported NOT_RUN, not fake PASS).
- Secret scan used synthetic patterns only (no protected-environment real
  pattern was available); booleans reported, no values printed.

## NOT_RUN (honest)

- Truly offline (no-network) Docker host load + boot.
- Real-secret pattern scan (no protected pattern file in this environment).
- Image-bundle layer-internal secret scan (OCI blob layout, see above).

## Evidence files

- `PLAN.md`, `reuse-gate-checkonly.log`, `build-offline.log`,
  `config-package.log`, `offline-scan.log`, `secret-scan.log`,
  `docker-load.log`, `compose-config.log`, `pull-never-up.log`,
  `init-permissions.log`, `migration-check.log`, `smoke.log`, `teardown.log`,
  `README.md`

## Guardrails honored

- 1.15 `docker-*` stack untouched (12 containers running throughout).
- No host ports other than `127.0.0.1:18080`.
- No access/modification of `docker/volumes/**`; baseline unchanged after run.
- No B7 scripts, compose files, or api/web source modified (`git diff --check` clean).
- No commit, push, merge, or PR (see final report).

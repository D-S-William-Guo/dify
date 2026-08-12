# Phase H Evidence — Offline Artifact Chain Validation

Validator: `replay-116-b8-phase-h-validator`
Branch: `ctyun/replay-116-b8-phase-h-validator`
Head: `7e2afa6e7535b8aa56e8342b680d90a0f8efe7b9`
Base: `codex/enterprise-candidate-1.16.0-20260718`
Date: 2026-08-12 (Asia/Shanghai)
Decision sheet: H1=A, H2=A, H3=A, H4=A, H5=A, H6=A, H7=A

## Verdict: FAIL (offline chain mechanics PASS, image-content-vs-source consistency FAIL)

The offline artifact chain ran end-to-end (build → scan → load → `--pull never`
boot → smoke → teardown) with the scripts all green, **but a release-blocking
consistency failure was found**: the Phase F built enterprise images do not
contain the Phase G fixes, so the offline bundle packages a pre-fix API image.

## What ran (all PASS mechanics)

1. `scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse` — exit 0.
2. `scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse` — exit 0,
   6m57s; produced `dify-enterprise-offline-1.16.0-enterprise.tar` (8,276,784,128 B),
   `images-1.16.0-enterprise.txt`, `manifest-1.16.0-enterprise.json`.
   Reuse gate PASS: `COMMIT_SHA=1.16.0-enterprise` on both enterprise images;
   all dependency images already local (no pull).
3. `scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise` — exit 0;
   `dify-enterprise-config-1.16.0-enterprise.tar.gz` (32,028 B).
4. `scripts/ci/check-enterprise-offline.sh` with synthetic 0600 pattern — exit 0,
   13 PASS / 0 FAIL / 1 NOT_RUN (NOT_RUN = image-bundle layer scan, see secret-scan.log).
5. `docker load < ...offline-1.16.0-enterprise.tar` — 12 images loaded (exit 0).
6. Isolated stack `dify-b8-phase-h`: temp override mapped every `./volumes/**`
   bind of the started services to named volumes `dify-b8-phase-h-*`; nginx on
   `127.0.0.1:18080:80` only; started `db_postgres redis api web nginx` with
   `--pull never` (db_postgres/redis needed for api to boot, both isolated with
   remapped volumes — deviation, see below).
7. Smoke (minimal, H3-A): nginx `/` HTTP 200; api `/health` HTTP 200
   (`{"status":"ok","version":"1.16.0"}`); web `/webpage/signin` HTTP 200
   (Next.js shell); web `/` HTTP 307 -> `/install` (fresh-DB install redirect).
   No `Pulling` line in the up log; enterprise images dated 2026-08-11
   (pre-existing) vs containers started 2026-08-12.
8. Teardown `docker compose -p dify-b8-phase-h down -v` — exit 0; no
   `dify-b8-phase-h-*` containers/volumes/networks remain; `docker/volumes/**`
   unchanged from baseline (myscale/oceanbase/opensearch/sandbox only, no new
   dirs); 1.15 `docker-*` stack (12 containers) untouched.

## Release-blocking finding: offline API image predates Phase G fixes

- The Phase F image `dify-api-enterprise:1.16.0-enterprise` (`cb4d99a45ac1`,
  built 2026-08-11 15:28) does **not** contain Phase G fix commit
  `85b445c0e1` (merged 2026-08-12 23:00).
- Evidence (checked inside the image):
  - GPH-01 migration `e7c0a9d2b8f3` is absent from `/app/api/migrations/versions/`.
    A fresh PostgreSQL 15 boot of the bundle ran migrations and stopped at
    `b416e5c4e702` (`alembic_version`), NOT the required single enterprise head
    `e7c0a9d2b8f3`. Marketplace ID/FK columns stay `VARCHAR(36)` → the GPH-01
    submit/review/copy/unlist 500 bug would persist on a fresh offline install.
  - GPH-02 `_align_snapshot_to_composition` (agent knowledge snapshot alignment)
    is absent from `/app/api/clients/agent_backend/request_builder.py` (diff vs
    repo HEAD confirms the 60-line fix block is missing) → the agent-knowledge
    binding chat bug would persist.
- Root cause: the B7 reuse gate only compares `COMMIT_SHA` (which carries the
  version tag `1.16.0-enterprise`, B6R-01), so it cannot distinguish a pre-fix
  build from a post-fix build of the same tag. Phase H cross-checked image
  content against candidate HEAD and caught the drift.
- **Required fix (out of Phase H scope, recorded for coordinator):** rebuild
  `dify-api-enterprise:1.16.0-enterprise` from candidate HEAD (Phase F
  re-run), re-run Phase H offline chain, and confirm the image's migration head
  is `e7c0a9d2b8f3` and `request_builder.py` contains the fix before the
  offline bundle is considered release-ready. Web image content was not
  implicated by the Phase G fixes (backend-only).

## Deviations from plan (all recorded honestly)

1. **Started `db_postgres` and `redis`** (isolated, volumes remapped to
   `dify-b8-phase-h-*` named volumes) in addition to `api web nginx`: the api
   image entrypoint requires Redis (`create_app`) and Postgres
   (`flask upgrade-db`) to boot; without them api crash-looped and `/health`
   never became reachable. These services mount no forbidden `docker/volumes/**`
   bind after remapping. Deviation from "api/web/nginx only", justified by the
   H3-A smoke requirement that api health actually respond.
2. **Ran `init_permissions` one-shot** (storage volume chown) so api could
   persist its generated `.dify_secret_key`; without it api aborted with
   `ValueError: SECRET_KEY is not set and could not be generated`.
3. **Cleared stale `db_upgrade_lock`** in the isolated redis once: the first
   post-restart boot reported "Database migration skipped" because a prior
   crash-loop incarnation's lock had not yet expired; after clearing, the full
   migration ran to the image's head (`b416e5c4e702`).
4. **Override merge tag**: compose v5 `!reset` produced empty volume lists;
   `!override` was used instead (validated via `compose config` before `up`).
5. **Fresh-DB migration head is `b416e5c4e702`**, not the required
   `e7c0a9d2b8f3` — this is the release-blocking finding above, not a pass.

## Known limitations (honest)

- Same-daemon simulation: images already present locally, so `--pull never`
  cannot prove a truly offline host; a network-isolated Docker host remains
  NOT_RUN. No pull was attempted on this run (up log + pre-existing image
  timestamps).
- Image-bundle layer content scan NOT_RUN (Docker 29 OCI blob layout not
  matched by the B7 `*/layer.tar` scan; gate reported NOT_RUN, not fake PASS).
- Secret scan used synthetic patterns only (no protected-environment real
  pattern was available); booleans reported, no values printed.

## NOT_RUN (honest)

- Truly offline (no-network) Docker host load + boot.
- Real-secret pattern scan (no protected pattern file in this environment).
- Image-bundle layer-internal secret scan (OCI blob layout, see above).

## Evidence files

- `PLAN.md`, `build-offline.log`, `config-package.log`, `offline-scan.log`,
  `docker-load.log`, `pull-never-up.log`, `init-permissions.log`, `smoke.log`,
  `secret-scan.log`, `teardown.log`, `README.md`

## Guardrails honored

- 1.15 `docker-*` stack untouched (12 containers running throughout).
- No host ports other than `127.0.0.1:18080`.
- No access/modification of `docker/volumes/**`; baseline unchanged after run.
- No B7 scripts, compose files, or api/web source modified (`git diff --check` clean).
- No commit, push, merge, or PR (see final report).

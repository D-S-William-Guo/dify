# Phase H Rerun Plan — Offline Artifact Chain with Rebuilt Images

Validator: `replay-116-b8-phase-h-rerun`
Expected branch: `ctyun/replay-116-b8-phase-h-rerun`
Expected HEAD: `c7c98b220d49b8b651bf87f47850a9dff5ddbd6b`
Base integration branch: `codex/enterprise-candidate-1.16.0-20260718`
Base SHA: `c7c98b220d49b8b651bf87f47850a9dff5ddbd6b`
Decision sheet: `/tmp/replay-116-phase-h-decision-sheet.md` options H1=A, H2=A, H3=A, H4=A, H5=A, H6=A, H7=A (same-daemon simulation)
Date: 2026-08-14 (Asia/Shanghai)

## Objective

Rerun the Phase H offline artifact chain with the rebuilt enterprise images
(API `sha256:566bdf4c88cf1bf3be5f7f6c7c39b338d5f1973ebe10f115050d9ac527930680`,
Web `sha256:b76919e99830040e603d6c5c1e189b839e816f9829b43cb0e44584fe9e5dd725`)
and the hardened B7 reuse gate. The prior Phase H run FAILED because the Phase F
images lacked the Phase G fixes; Phase F Rebuild rebuilt them from candidate HEAD.

## Guardrails

- Never touch the 1.15 `docker-*` stack, `docker/volumes/**`, or any B7 script /
  compose / api / web source. Port `127.0.0.1:18080` only.
- Never push / merge / commit (unless separately authorized by coordinator).
- Same-daemon simulation known limitation: images already present locally, so
  `--pull never` cannot prove a truly offline host; recorded as known limitation.
- Output under `/tmp/replay-116-phase-h-rerun/` (transient `<repo>/tmp -> /tmp`
  symlink used because the script joins `$REPO_ROOT/$OUTPUT_DIR`).

## Steps

1. **Prep**: verify branch/HEAD/clean; temp dir `/tmp/replay-116-phase-h-rerun/`;
   temp `docker/.env` (copy of `docker/.env.example`, gitignored `*.env`, removed
   at teardown); transient symlink `<repo>/tmp -> /tmp`; record `docker/volumes/**`
   baseline (read-only).
2. **H1 offline bundle**:
   - `scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse -OutputDir /tmp/replay-116-phase-h-rerun`
   - `scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse -OutputDir /tmp/replay-116-phase-h-rerun`
   - Confirm gate accepts new API image; manifest `images[].id` for
     `dify-api-enterprise:1.16.0-enterprise` = `sha256:566bdf4c88cf...`.
3. **H2 config package**:
   - `scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise -OutputDir /tmp/replay-116-phase-h-rerun`
4. **H3/H4 static scan** with synthetic `0600` secret pattern:
   - `scripts/ci/check-enterprise-offline.sh -Archive ... -ConfigArchive ... -Manifest ... -Images ... -SecretsPattern <0600 file>`
5. **docker load**: `docker load < dify-enterprise-offline-1.16.0-enterprise.tar`.
6. **Isolated stack** project `dify-b8-phase-h-rerun`, temp override in `/tmp`:
   - map every `./volumes/**` bind of started services to named volumes
     `dify-b8-phase-h-rerun-*`; nginx `127.0.0.1:18080:80` only.
   - start `db_postgres redis api web nginx` with `--pull never` (db/redis needed
     for api to boot; both isolated with remapped volumes — same deviation as the
     first Phase H run, justified by the H3-A smoke requirement).
   - run `init_permissions` one-shot first so api can persist `.dify_secret_key`.
7. **Migration head check** on the fresh PG15 database: after api boots,
   `alembic_version` must be `e7c0a9d2b8f3` (NOT `b416e5c4e702`) and marketplace
   ID/FK columns must be `uuid`.
8. **H3-A minimal smoke**: nginx `127.0.0.1:18080` HTTP 200; api `/health` HTTP
   200; web page HTTP 200; no `Pulling` line in the up log.
9. **Teardown**: `docker compose -p dify-b8-phase-h-rerun down -v`; remove temp
   `docker/.env`, override, nginx conf, secret pattern, `/tmp/replay-116-phase-h-rerun/**`;
   verify no `dify-b8-phase-h-rerun-*` containers/volumes/networks remain and no
   new `docker/volumes/**` dirs created.
10. **Evidence**: logs + README under
    `docs/enterprise/replay-1.16.0/evidence/phase-h-rerun/**`; update
    `DECISION_RISK_LEDGER.md` Phase H row to PASS if all checks pass.

## Required verification

- `git status --porcelain=v1`, `git rev-parse HEAD`
- `git merge-base --is-ancestor b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4 HEAD`
- `ss -ltn | rg ':18080' || true`
- `docker image inspect dify-api-enterprise:1.16.0-enterprise --format '{{.Id}}'`
- `scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse`
- `git diff --check`
- `git status --short --branch`

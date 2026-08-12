# Phase H Plan — Offline Artifact Chain Validation

Validator: `replay-116-b8-phase-h-validator`
Expected branch: `ctyun/replay-116-b8-phase-h-validator`
Expected HEAD: `7e2afa6e7535b8aa56e8342b680d90a0f8efe7b9`
Decision sheet: H1=A, H2=A, H3=A, H4=A, H5=A, H6=A, H7=A
Date: 2026-08-12 (Asia/Shanghai)

## Guardrails

- Never touch the 1.15 `docker-*` stack or `docker/volumes/**`; port 18080 only.
- Never modify B7 scripts / compose / api / web source; never push / merge / commit
  (unless separately authorized by the coordinator).
- Same-daemon simulation known limitation: images already exist locally, so
  `--pull never` cannot prove a truly offline host; recorded as a known limitation.

## Steps

1. **Prep**: verify branch/HEAD/clean; create temp `docker/.env` (copy of
   `docker/.env.example`, gitignored `*.env`, removed at teardown); temp dir
   `/tmp/replay-116-phase-h/`; record `docker/volumes/**` baseline (read-only).
2. **H1 offline bundle**:
   - `scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse`
   - `scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse`
   - Artifacts: `dist/offline/images-1.16.0-enterprise.txt`,
     `dist/offline/manifest-1.16.0-enterprise.json`,
     `dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar` (gitignored).
3. **H2 config package**:
   - `scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise`
   - Artifact: `dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz`.
4. **H3/H4 static scan** with synthetic `0600` secret pattern under `/tmp`
   (boolean output only):
   - `scripts/ci/check-enterprise-offline.sh -Archive ... -ConfigArchive ... -Manifest ... -Images ... -SecretsPattern <0600>`
5. **H2-A docker load**:
   - `docker load < dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar`
6. **Isolated stack** project `dify-b8-phase-h`, temp override in `/tmp`:
   - all `./volumes/**` binds for started services -> named volumes
     `dify-b8-phase-h-*`; nginx only `127.0.0.1:18080:80`; minimal nginx
     proxy conf (api health + web) in /tmp.
   - Start with `--pull never --no-deps` only `api web nginx`
     (services mounting `docker/volumes/**` are not started).
   - `docker compose --env-file docker/.env -p dify-b8-phase-h \
     -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml \
     -f /tmp/replay-116-phase-h/dify-b8-phase-h.override.yaml \
     up -d --pull never --no-deps api web nginx`
   - Record logs; confirm no pull attempt.
7. **H3-A minimal smoke**:
   - nginx `127.0.0.1:18080` HTTP 200;
   - api health endpoint reachable (through nginx proxy to `api:5001`);
   - web page reachable (through nginx proxy to `web:3000`).
8. **Teardown**: `docker compose -p dify-b8-phase-h down -v`; remove temp
   `docker/.env`, override, nginx conf, secret pattern, `dist/offline/**`;
   verify no `dify-b8-phase-h-*` containers/volumes/networks remain and no new
   `docker/volumes/**` dirs created.
9. **Evidence**: write logs + README under
   `docs/enterprise/replay-1.16.0/evidence/phase-h/**`; update
   `DECISION_RISK_LEDGER.md` Phase H row.

## Required verification

- `git status --porcelain=v1`, `git rev-parse HEAD`
- `git merge-base --is-ancestor b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4 HEAD`
- `ss -ltn | rg ':18080' || true`
- `docker image inspect dify-api-enterprise:1.16.0-enterprise --format '{{.Id}}'`
- `docker image inspect dify-web-enterprise:1.16.0-enterprise --format '{{.Id}}'`
- `scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse`
- `git diff --check`

# Phase F Evidence — Image Build + Container Identity

Validator: `replay-116-b8-phase-f-validator`
Head: `0f63806aa3143067a4b4e0f9c0d2fd24102a4152`
Base: `codex/enterprise-candidate-1.16.0-20260718`
Date: 2026-08-11 (Asia/Shanghai), UTC start 07:36
Option: **F-A** (isolated Compose project `dify-b8-phase-f` + temporary override in `/tmp`)

## Result: PASS

## Scope

- Build `dify-api-enterprise:1.16.0-enterprise` and `dify-web-enterprise:1.16.0-enterprise`
  from the current overlay + official `api/Dockerfile` and `web/Dockerfile`.
- Recreate api / worker / worker_beat / api_websocket / web / nginx in an isolated
  Compose project, inspect immutable `.Image` IDs, assert identity.
- Record RepoDigest, `COMMIT_SHA`, start time, compose project and workdir.
- Verify all bind mounts resolve to the current 1.16 deploy dir (no 1.15/old paths).
- Teardown and confirm no `dify-b8-phase-f-*` containers/volumes/networks remain.

## Identity assertions (all PASS)

| Container | Image ID | Assert |
| --- | --- | --- |
| `dify-b8-phase-f-api-1` | `sha256:cb4d99a45ac1fcadbe02336e4633053c2234e775e8e65fb8bd2c8d7fdc70c347` | == API image ID |
| `dify-b8-phase-f-worker-1` | same | == api |
| `dify-b8-phase-f-worker_beat-1` | same | == api |
| `dify-b8-phase-f-api_websocket-1` | same | == api |
| `dify-b8-phase-f-web-1` | `sha256:0ae50b4527b8968f89ffb9bc70f100216b2f2002a0a807af2de4cc45f556990d` | == Web image ID |
| `dify-b8-phase-f-nginx-1` | `nginx:latest` (`sha256:6c3a6ea6...`) | nginx, not asserted |

- `dify-api-enterprise:1.16.0-enterprise` → `sha256:cb4d99a45ac1...`
- `dify-web-enterprise:1.16.0-enterprise` → `sha256:0ae50b4527b8...`
- RepoDigest: **empty** (locally built, never pushed — expected; recorded in `repo-digests.log`)
- `COMMIT_SHA=1.16.0-enterprise` in all 5 runtime containers
- Start times: api/worker/beat/websocket ~`2026-08-11T07:37:xxZ`, web `07:36:49Z`,
  nginx `07:37:29Z` (see `commit-sha.log`)
- Project `dify-b8-phase-f`; workdir `<repo>/docker`; config files =
  `docker/docker-compose.yaml`, `docker/docker-compose.enterprise.yaml`, `/tmp/dify-b8-phase-f.override.yaml`
- nginx bound to `127.0.0.1:18080:80` only; verified listening + HTTP 200 `phase-f-ok`

## Build

Two images, built with `docker compose build` (isolated project). The api group needed
`build.network: host` + proxy build-args because the sandbox reaches `github.com` only via
a local proxy (`127.0.0.1:7897`) that BuildKit bridge containers cannot use for git fetch
(uv `flask-restx` git dependency). Details and full logs: `build.log`.

- api/worker/worker_beat/api_websocket build: PASS (final attempt exit 0)
- web build: PASS (final attempt exit 0)

## Compose static config (isolated project)

- `docker compose ... config -q` → exit 0
- `docker compose ... config --images | sort -u` → see `compose-config.log`

## Isolation / guardrails honored

- Temp override `/tmp/dify-b8-phase-f.override.yaml` — never committed (removed).
- Temp `docker/.env` (copy of `.env.example`, gitignored `*.env`) — created only to satisfy
  compose v5 hard requirement on `./.env` (same procedure as Phase E), removed after teardown.
- `--no-deps` start: services that bind `docker/volumes/**` (db_postgres, redis, weaviate,
  sandbox, plugin_daemon) were never started, so those bind mounts never materialized.
- api/worker storage and nginx certbot paths remapped to temp named volumes `dify-b8-phase-f-*`.
- Host port: only `127.0.0.1:18080`. Ports 80/443 (used by the 1.15 stack) never touched.
- 1.15 `docker-*` stack (12 containers) untouched and still running.
- No compose/source modified (`git diff --check` clean).

## Deviations from plan

1. **Build network**: initial builds failed at `uv sync` cloning
   `github.com/asukaminato0721/flask-restx` (git fetch reset / unreachable from BuildKit
   bridge). Fixed via `build.network: host` (override, temp) + proxy build-args. This is a
   build-environment adaptation inside the temp override, no source change.
2. **nginx runtime**: base nginx config references upstreams (`plugin_daemon`, sandbox,
   agent_backend, local_sandbox) that were not started (`--no-deps`), so stock nginx
   crash-looped (`host not found in upstream`). Started those upstreams would have mounted
   forbidden `docker/volumes/**`. Fixed by overriding nginx (temp override) to run the real
   `nginx:latest` with a minimal `default.conf` on `127.0.0.1:18080:80`. nginx identity is
   not part of the Phase F assertion.
3. **Host leftover**: one intermediate nginx recreate used the base compose certbot bind
   mounts, so the Docker daemon auto-created **empty root-owned dirs**
   `docker/volumes/certbot/{conf/live,conf,www}` (0 files, gitignored at `.gitignore:174`,
   not present before this run). Removal needs root: `sudo rm -rf docker/volumes/certbot`.
   No data was written to `docker/volumes/**`.
4. RepoDigests empty (locally built, not pushed) — recorded, not a failure.

## NOT_RUN (honest)

- Phase G browser/API/Agent runtime acceptance.
- Phase H offline load + `--pull never`.
- MySQL / non-PostgreSQL database rows.

## Evidence files

- `PLAN.md`, `build.log`, `image-ids.log`, `repo-digests.log`, `commit-sha.log`,
  `compose-config.log`, `teardown.log`, `README.md`

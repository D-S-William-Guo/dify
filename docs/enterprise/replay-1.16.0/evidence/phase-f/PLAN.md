# Phase F Execution Plan (Option F-A)

Validator: `replay-116-b8-phase-f-validator`
Start head: `0f63806aa3143067a4b4e0f9c0d2fd24102a4152`
Base: `codex/enterprise-candidate-1.16.0-20260718` (`0f63806aa3143067a4b4e0f9c0d2fd24102a4152`)
Date: 2026-08-11 (Asia/Shanghai)

Decision sheet: `/tmp/replay-116-phase-f-decision-sheet.md` → **F-A** (isolated Compose
project + temporary override), nginx `127.0.0.1:18080:80`, build allowed, temp named
volumes allowed, executed by this Phase F Validator.

## Guardrails

- Never touch the running 1.15 stack (`docker-*` project) or its containers/volumes.
- Never touch `docker/volumes/**` (this repo) or the 1.15 volume dir
  `/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/docker/volumes/**`.
- Host port bindings: ONLY `127.0.0.1:18080`. Port 80/443 are in use by the 1.15 stack
  and must never be bound by this project.
- No modifications to compose/source under `docker/`, `api/`, `web/`, `dify-agent/`,
  `packages/`. Only evidence paths + DECISION_RISK_LEDGER.md are written.
- No commit/amend/push.

## Override design (`/tmp/dify-b8-phase-f.override.yaml`, never committed)

Because `docker-compose.yaml` hard-requires `docker/.env` (short-syntax `env_file: ./.env`,
compose v5 fails without it), and Phase E precedent accepted a temporary `docker/.env`
(copy of `.env.example`, gitignored by `docker/.gitignore: *.env`), the same procedure is
followed: create `docker/.env` for the isolated run, remove it after teardown, verify
`git status` clean.

Temp env overrides applied to `docker/.env` (only nginx port interpolation):
- `EXPOSE_NGINX_PORT=127.0.0.1:18080`
- `EXPOSE_NGINX_SSL_PORT=127.0.0.1:18080`
- `NGINX_SSL_PORT=80`

These collapse both base nginx host mappings (`80:80` and `443:443`) into a single
identical `127.0.0.1:18080:80` spec, so the merged config binds ONLY host `127.0.0.1:18080`.

Override replaces (compose merge by same target):
- `init_permissions`/`api`/`worker` `./volumes/app/storage` → `dify-b8-phase-f-storage`
- `nginx` `./volumes/certbot/{conf/live,conf,www}` → `dify-b8-phase-f-certbot-*`
- `nginx` `./nginx/conf.d` → `dify-b8-phase-f-nginx-conf` (entrypoint writes
  `/etc/nginx/conf.d/default.conf`; must not write through to `docker/nginx/conf.d`)
- `nginx` `./nginx/conf.d/default.conf.template` mounted read-only at
  `/etc/nginx/conf.d/default.conf.template`

Services with `docker/volumes/**` bind mounts (db_postgres, redis, weaviate, sandbox,
plugin_daemon) are NOT started (`up -d --no-deps` for the 6 target services only), so
their bind mounts never materialize.

## Steps

1. Verify branch/HEAD/clean status (done at start).
2. Write override `/tmp/dify-b8-phase-f.override.yaml` + temp `docker/.env`.
3. `docker compose config -q` and `config --images | sort -u` for isolated project.
4. Build:
   `DIFY_ENTERPRISE_VERSION=1.16.0-enterprise COMPOSE_PROFILES=weaviate,postgresql,collaboration`
   `docker compose -p dify-b8-phase-f -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml -f /tmp/dify-b8-phase-f.override.yaml build api worker worker_beat api_websocket web`
5. Up:
   `up -d --no-deps --force-recreate api worker worker_beat api_websocket web nginx`
6. Inspect `.Image` of the 6 containers; assert api==worker==worker_beat==api_websocket
   and equals `dify-api-enterprise:1.16.0-enterprise` image ID; web ==
   `dify-web-enterprise:1.16.0-enterprise` image ID.
7. Record RepoDigest, COMMIT_SHA, start time, compose project, workdir; verify no
   bind mount resolves to an old/1.15 path.
8. Teardown: `docker compose -p dify-b8-phase-f down -v`, remove `/tmp/dify-b8-phase-f.override.yaml`,
   remove temp `docker/.env`, verify no `dify-b8-phase-f-*` containers/volumes/networks.
9. Write evidence under `docs/enterprise/replay-1.16.0/evidence/phase-f/**` and update
   `DECISION_RISK_LEDGER.md` Phase F row.

## Evidence files

- `PLAN.md` (this file)
- `build.log` — build command / exit / duration
- `image-ids.log` — 6 container `.Image` IDs + equality assertions
- `repo-digests.log` — API/Web image ID + RepoDigest
- `commit-sha.log` — COMMIT_SHA / start time / compose project / workdir
- `compose-config.log` — `config -q` + `config --images | sort -u`
- `teardown.log` — teardown + residual check
- `README.md` — results/assertions/teardown summary

## NOT_RUN (honest)

- Browser/API acceptance (Phase G), offline load (Phase H), MySQL rows (Phase D) — out of scope.

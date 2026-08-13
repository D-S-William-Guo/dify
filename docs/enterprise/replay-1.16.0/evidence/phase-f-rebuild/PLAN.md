# Phase F Rebuild Plan — Rebuild enterprise API + Web images from candidate HEAD

Validator: `replay-116-b8-phase-f-rebuild`
Branch: `ctyun/replay-116-b8-phase-f-rebuild`
Start head: `a7dd727ddfad1dce75be6a52ea8d7da18dfb4cb8`
Base integration branch: `codex/enterprise-candidate-1.16.0-20260718`
Base SHA: `a7dd727ddfad1dce75be6a52ea8d7da18dfb4cb8`
Date: 2026-08-14 (Asia/Shanghai)

## Context

Phase H found the Phase F-built enterprise API image `cb4d99a45ac1`
(2026-08-11) lacks the Phase G fixes (`85b445c0e1`, merged 2026-08-12):
migration `e7c0a9d2b8f3` is absent and `request_builder.py` has no
`_align_snapshot_to_composition`. The B7 reuse gate now hardens against this
(commit `437c59ab8b`), but the offline bundle still packages the stale image.
This task rebuilds `dify-api-enterprise:1.16.0-enterprise` and
`dify-web-enterprise:1.16.0-enterprise` from the candidate HEAD so the offline
bundle carries the fixed API image.

## Guardrails

- Isolated Compose project `dify-b8-phase-f-rebuild` only; never touch the
  running 1.15 `docker` stack, `ai-platform-square-hb`, or any other project.
- No `up`, no containers, no ports, no volumes; build only.
- Never touch `docker/volumes/**` (this repo) or the 1.15 volume dir
  `/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/docker/volumes/**`.
- No modifications to compose/source/Dockerfiles/scripts/migrations/contracts.
- Temp override under `/tmp` (never committed); temp `docker/.env` (copy of
  `.env.example`, gitignored) removed after.
- Write only under `docs/enterprise/replay-1.16.0/evidence/phase-f-rebuild/**`
  and update `DECISION_RISK_LEDGER.md`.
- No commit/amend/push/merge/rebase/reset/cherry-pick.

## Steps (planned vs actual will be reported)

1. Verify start branch/HEAD/clean status (done at start).
2. Write `/tmp/dify-b8-phase-f-rebuild.override.yaml` and temp `docker/.env`.
   - Override: `build.network: host` + proxy build-args (`HTTP_PROXY`,
     `HTTPS_PROXY`, `NO_PROXY`) for `api` and `web` — same environment
     adaptation as Phase F (sandbox reaches github.com/npm only via local
     proxy `127.0.0.1:7897`, unreachable from BuildKit bridge network).
3. `docker compose -p dify-b8-phase-f-rebuild -f docker/docker-compose.yaml -f
   docker/docker-compose.enterprise.yaml -f /tmp/dify-b8-phase-f-rebuild.override.yaml
   config -q`
4. Build:
   `DIFY_ENTERPRISE_VERSION=1.16.0-enterprise COMPOSE_PROFILES=weaviate,postgresql,collaboration
   docker compose -p dify-b8-phase-f-rebuild -f docker/docker-compose.yaml -f
   docker/docker-compose.enterprise.yaml -f /tmp/dify-b8-phase-f-rebuild.override.yaml
   build api web`
   (no up, no containers/ports)
5. Record new image IDs for `dify-api-enterprise:1.16.0-enterprise` and
   `dify-web-enterprise:1.16.0-enterprise`; assert API ID != `cb4d99a45ac1`.
6. `docker run --rm` read-only content checks inside the new API image:
   migration `2026_08_12_0000-e7c0a9d2b8f3_align_marketplace_uuid_columns.py`
   present under `/app/api/migrations/versions/`; `request_builder.py` contains
   `_align_snapshot_to_composition`.
7. `scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise
   -Mode reuse -OutputDir /tmp/b8-phase-f-rebuild-check` — expect exit 0
   (hardened reuse gate accepts the new image). Remove temp output dir.
8. Write evidence under `docs/enterprise/replay-1.16.0/evidence/phase-f-rebuild/**`
   and update `DECISION_RISK_LEDGER.md`.
9. Teardown: remove `/tmp/dify-b8-phase-f-rebuild.override.yaml` and temp
   `docker/.env`; verify no `dify-b8-phase-f-rebuild-*` artifacts; `git status`
   clean; `git diff --check`.

## Evidence files

- `PLAN.md` (this file)
- `compose-config.log` — `config -q` result
- `build.log` — build command / exit / duration
- `image-ids.log` — new image IDs + vs-old comparison
- `content-check.log` — migration + request_builder presence inside new image
- `reuse-gate.log` — `-CheckOnly` run output / exit / cleanup
- `README.md` — results / deviations / NOT_RUN

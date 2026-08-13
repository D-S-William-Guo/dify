# Phase F Rebuild Evidence — Enterprise API + Web images rebuilt from candidate HEAD

Validator: `replay-116-b8-phase-f-rebuild`
Branch: `ctyun/replay-116-b8-phase-f-rebuild`
Start head: `a7dd727ddfad1dce75be6a52ea8d7da18dfb4cb8`
Base integration branch: `codex/enterprise-candidate-1.16.0-20260718`
Base SHA: `a7dd727ddfad1dce75be6a52ea8d7da18dfb4cb8`
Date: 2026-08-14 (Asia/Shanghai)

## Result: PASS

The pre-fix Phase F API image `cb4d99a45ac1` (which lacked the Phase G fixes
and caused the Phase H release-blocking finding) has been replaced: the
enterprise API and Web images were rebuilt from candidate HEAD under the
isolated Compose project `dify-b8-phase-f-rebuild` (build only, no containers,
no ports, no volumes). The hardened B7 reuse gate now accepts the new API
image (exit 0), so a subsequent offline bundle will package the fixed image.

## Images (old vs new)

| Image | Old (pre-fix) | New (rebuilt) | Assert |
| --- | --- | --- | --- |
| `dify-api-enterprise:1.16.0-enterprise` | `sha256:cb4d99a45ac1...` (2026-08-11) | `sha256:566bdf4c88cf1bf3be5f7f6c7c39b338d5f1973ebe10f115050d9ac527930680` | new != old (PASS) |
| `dify-web-enterprise:1.16.0-enterprise` | `sha256:0ae50b4527b8...` | `sha256:b76919e99830040e603d6c5c1e189b839e816f9829b43cb0e44584fe9e5dd725` | rebuilt (PASS) |

Web was not implicated by the Phase G fixes (backend-only) but was rebuilt
anyway per task scope.

## Build

Command (isolated project, build only, no up):

```
DIFY_ENTERPRISE_VERSION=1.16.0-enterprise COMPOSE_PROFILES=weaviate,postgresql,collaboration \
docker compose -p dify-b8-phase-f-rebuild -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml -f /tmp/dify-b8-phase-f-rebuild.override.yaml \
  build api web
```

Exit 0. Layers were mostly BuildKit-cached; the api `COPY api /app/api/`
steps re-ran against candidate HEAD (producing the new content-bearing image).
Temp override `/tmp/dify-b8-phase-f-rebuild.override.yaml` (never committed)
replicated the Phase F environment adaptation: `build.network: host` + proxy
build-args (`HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` → `127.0.0.1:7897`) so
BuildKit can reach github.com (uv `flask-restx` git dep), deb.nodesource.com,
PyPI, npm, and nltk data. Full log: `build.log`.

## Content checks inside the new API image (read-only `docker run --rm`)

- GPH-01 migration present:
  `/app/api/migrations/versions/2026_08_12_0000-e7c0a9d2b8f3_align_marketplace_uuid_columns.py` → **PRESENT**
- GPH-02 fix present: `grep -Fq _align_snapshot_to_composition
  /app/api/clients/agent_backend/request_builder.py` → **PRESENT**
- Image migration file set == repo `api/migrations/versions` file set at HEAD
  (206 files) → **MATCH**
- (The old image `cb4d99a45ac1` fails all three: migration ABSENT, function
  ABSENT — confirmed before the rebuild.)

See `content-check.log`.

## Hardened B7 reuse gate

```
./scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise \
  -Mode reuse -OutputDir /tmp/b8-phase-f-rebuild-check
```

- Exit **0** (gate ACCEPTS the new API image: `COMMIT_SHA=1.16.0-enterprise`
  + migration file set match + `_align_snapshot_to_composition` present).
- Reused all local dependency images; no build/pull/save executed (CheckOnly).
- Manifest `enterprise_commit = a7dd727ddfad1dce75be6a52ea8d7da18dfb4cb8`
  (candidate HEAD); api image id in manifest = `sha256:566bdf4c88cf...`.
- Temp output dir `/tmp/b8-phase-f-rebuild-check` removed after.
- `bash -n scripts/build-enterprise-offline.sh` → OK.

See `reuse-gate.log`.

## Guardrails honored

- Only isolated project `dify-b8-phase-f-rebuild`; never started containers,
  never bound host ports, never created volumes; build only.
- 1.15 `docker` stack (12 containers) untouched and still running.
- `docker/volumes/**` in this repo untouched (baseline unchanged).
- No compose/Dockerfile/source/scripts/migrations/contracts modified
  (`git diff --check` clean).
- Temp override `/tmp/dify-b8-phase-f-rebuild.override.yaml` removed; temp
  `docker/.env` (copy of `.env.example`, gitignored `*.env`) removed.
- No commit, push, merge, rebase, reset, cherry-pick (see final report).

## Deviations from plan

1. **Script OutputDir handling**: `scripts/build-enterprise-offline.sh` joins
   `$REPO_ROOT/$OUTPUT_DIR` (line 62), so the literal `-OutputDir
   /tmp/b8-phase-f-rebuild-check` would have written the manifest/images into
   `<repo>/tmp/...` instead of `/tmp`. To keep output under `/tmp` as the task
   requires, a transient untracked symlink `<repo>/tmp -> /tmp` was created
   before the run and removed after; output physically landed in
   `/tmp/b8-phase-f-rebuild-check` and was deleted. No `docker/`, `api/`,
   `web/`, `scripts/` or tracked path was touched.
2. **Cache reuse**: most build layers were BuildKit-cached from the prior
   build; only the source-copy steps re-ran. This is correct (dependencies
   unchanged) and the resulting image ID differs from the old image — verified
   by content checks, not assumed.
3. **Image IDs**: new API `566bdf4c88cf`, new web `b76919e998` — recorded, and
   the manifest confirms the API id differs from old `cb4d99a45ac1`.

## NOT_RUN (honest)

- Full offline chain (Phase H re-run: load + `--pull never` boot + smoke) —
  out of scope for this rebuild task.
- Web image content check — Phase G fixes were backend-only; web not asserted.
- Truly no-network Docker host.

## Evidence files

- `PLAN.md`, `compose-config.log`, `build.log`, `image-ids.log`,
  `content-check.log`, `reuse-gate.log`, `README.md`

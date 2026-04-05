---
name: enterprise-docker-workflow
description: Enterprise Docker development, validation, image rebuild, and project-scoped image cleanup workflow for this Dify repository. Use when changing enterprise features that must be verified through Docker Desktop, when deciding whether current containers reflect the latest source, when rebuilding `dify-api-enterprise` or `dify-web-enterprise`, when classifying compose services as required or optional for enterprise-page work, or when analyzing and cleaning only this project's Docker images.
---

# Enterprise Docker Workflow

## Intent

- Follow the repository maintenance priority from `README.enterprise-maintenance.md`: sync official upstream first, preserve enterprise features second, and handle route 2 or other phase-based optimizations after that.
- Treat `Windows 11 + Docker Desktop + Git` as the default local enterprise development baseline.
- Prefer `docker/docker-compose.yaml` plus `docker/docker-compose.enterprise.yaml` as the execution surface for enterprise work, and treat `docker/docker-compose-template.yaml` as the generated source template rather than the file to edit directly.
- Validate enterprise changes against the current source tree, not against already-running old images.
- For frontend build issues, treat `upstream/main` as the current build baseline. Do not lock onto a specific historical toolchain; first analyze how `upstream/main` builds now, then bring `enterprise/main` back to the same direction before reapplying enterprise-only differences.
- Keep enterprise image naming, version tags, and `COMMIT_SHA` checks aligned with `docker/README.enterprise.md`.
- Restrict Docker image cleanup to this repository's enterprise images and explicitly project-owned helper images.
- On Windows + Docker Desktop, prefer [`build-enterprise-web.ps1`](D:\CodexSpace\dify\docker\scripts\build-enterprise-web.ps1) for web image rebuilds when local `node_modules` reparse points would otherwise break compose build context loading.

## Workflow

1. Confirm the verification surface before touching Docker state.
   - Read `docker/README.enterprise.md` for enterprise image naming, compose overlay, packaging, and rebuild rules.
   - Read `README.enterprise-maintenance.md` when the task involves deployment packaging, offline bundles, or fresh-machine initialization.
   - Read `README.performance-route2.md` when the task is part of route 2 and needs browser-click plus container-log validation.
   - Use `docker/docker-compose.yaml` plus `docker/docker-compose.enterprise.yaml` for build, up, exec, ps, logs, and config. Only inspect `docker/docker-compose-template.yaml` to understand generated service definitions or when upstream template changes are involved.
2. Classify the local workspace.
   - Keep `.codex/**`, `docker/.env`, and `docker/nginx/conf.d/default.conf` in place unless the user explicitly wants them changed.
   - Remove disposable runtime leftovers such as `dist/` and `api/**/__pycache__/` when cleanup is requested.
   - Do not delete active runtime data under `docker/volumes/**` unless the user explicitly asks for it, or you first explain the impact and receive approval.
   - Isolate unrelated retained files instead of mixing them into enterprise development on `enterprise/main`.
3. Verify whether running containers represent the latest source.
   - Inspect mounts for `api` and `web`; do not assume they are bind mounts.
   - If `api` or `web` run from built images instead of source mounts, treat them as stale until current-source validation succeeds.
   - If `web` fails to build after an upstream sync, first decide whether the failure comes from build-context hygiene or from `enterprise/main` drifting away from `upstream/main`'s current frontend build baseline.
4. Run current-source validation with compose-first commands.
   - Prefer `docker compose ... build`, `up`, `exec`, `logs`, and `ps` against the enterprise overlay instead of ad hoc standalone containers.
   - Frontend runtime changes are validated by `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml build web`, because `web/Dockerfile` compiles the app during image build.
   - On Windows, if local dependency trees make the root build context unreadable for Docker sender, prepare a minimal context through `docker/scripts/build-enterprise-web.ps1` rather than manually moving `node_modules`.
   - Backend runtime changes are validated by rebuilding the enterprise API image through compose and, when test tooling is needed, running it through compose-owned containers or another compose-aligned flow instead of bypassing the project definitions.
   - Use standalone `docker run` only as a fallback when compose cannot express the needed verification step, and call out that exception explicitly.
   - Do not claim enterprise code is verified if only old compose containers were observed.
   - Keep runtime artifacts such as `docker/volumes/**`, `.venv/**`, `node_modules/**`, and `.codex/**` in the "build-context hygiene" bucket; do not confuse them with the frontend source baseline itself.
5. Decide whether enterprise images must be rebuilt.
   - Rebuild `dify-api-enterprise:<official-version-enterprise>` when backend runtime logic, backend dependencies, or Docker build inputs affecting the API image change.
   - Rebuild `dify-web-enterprise:<official-version-enterprise>` when frontend runtime logic, frontend dependencies, or Docker build inputs affecting the web image change.
   - Reuse `dify-api-enterprise` for `worker` and `worker_beat`.
   - After rebuilding the API enterprise image, run compose with `--force-recreate` for `api`, `worker`, and `worker_beat` together so they all land on the current tagged image instead of leaving old worker containers on a now-dangling layer.
   - For release or packaging work, check both the tag and the internal `COMMIT_SHA`; tag equality alone is not enough.
6. Run compose runtime verification only after current-source validation passes.
   - Use the enterprise overlay compose files.
   - For route 2 enterprise-page work, validate in the browser and correlate behavior with container logs.
7. Apply compose restart granularity deliberately.
   - Do not restart the entire compose stack by default.
   - After rebuilding the web enterprise image, recreate `web` and `nginx` together with `--force-recreate`.
   - After rebuilding the API enterprise image, recreate `api`, `worker`, `worker_beat`, and `nginx` together with `--force-recreate`.
   - If only Nginx-facing config changed, recreate only `nginx`.
   - Use a broader compose restart only when the affected surface cannot be isolated cleanly.

## Service Tiers

- Minimal enterprise-page validation set:
  - `api`
  - `web`
  - `db_postgres`
  - `redis`
  - `nginx`
- Recommended realistic set:
  - `worker`
  - `worker_beat`
  - Keep these when the flow touches invitations, async jobs, or scheduled tasks.
- Non-essential for current enterprise-page route 2 work:
  - `weaviate`
  - `plugin_daemon`
  - `sandbox`
  - `ssrf_proxy`
  - These support knowledge, plugin, sandbox, or SSRF-proxy paths rather than the main enterprise-page verification surface.

## Image Rules

- Canonical enterprise image names:
  - `dify-api-enterprise:<official-version-enterprise>`
  - `dify-web-enterprise:<official-version-enterprise>`
- Local temporary tags such as `local` or `enterprise-local` are acceptable for short-lived development verification.
- Official packaging and delivery must use `official-version-enterprise`.
- Never treat `docker/volumes/**` as deliverable artifacts for a fresh machine.

## Project-Scoped Cleanup Rules

- Only analyze or delete images that clearly belong to this repository:
  - `dify-api-enterprise:*`
  - `dify-web-enterprise:*`
  - anonymous local build images currently referenced by this compose project
  - temporary helper images intentionally used for this repo, such as `python:3.12-slim-bookworm` or `node:22-alpine`, when the user wants them reviewed
- Never touch unrelated local images such as model-serving, OCR, observability, or other side projects.
- Cleanup order:
  1. Identify images used by the current compose project and keep them.
  2. Identify old enterprise images or dangling images that are not referenced by the current compose project.
  3. Remove only the confirmed-unused project images the user wants cleaned.

## Validation Checklist

- `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config --services`
- `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml ps`
- `docker inspect` on `api`, `web`, `worker`, and `worker_beat` when mount or image provenance matters
- `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml build web`
- `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml build api worker worker_beat`
- compose `exec` or `logs` checks against rebuilt services
- browser-click plus container-log verification for enterprise-page route 2 behavior

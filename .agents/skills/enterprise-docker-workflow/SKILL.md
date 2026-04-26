---
name: enterprise-docker-workflow
description: Enterprise Docker development, validation, image rebuild, and project-scoped image cleanup workflow for this Dify repository. Use when changing enterprise features that must be verified through Docker Desktop, when deciding whether current containers reflect the latest source, when rebuilding `dify-api-enterprise` or `dify-web-enterprise`, when classifying compose services as required or optional for enterprise-page work, or when analyzing and cleaning only this project's Docker images.
---

# Enterprise Docker Workflow

## Current Source Truth

- Read `AGENTS.md`, `README.enterprise-maintenance.md`, `ENTERPRISE_REPLAY_PLAN.md`, and `docker/README.enterprise.md` before changing enterprise Docker or release behavior.
- `codex/enterprise-candidate-20260424` is the current clean enterprise candidate.
- The previous `enterprise/main` and `codex/protect-enterprise-main-20260424-103050` are historical references only.
- Do not copy old Docker hacks, runtime data, or broad route-2 changes from the dirty branch unless they are documented and re-validated on the current candidate.

## Core Rules

- Use `docker/docker-compose.yaml` plus `docker/docker-compose.enterprise.yaml` as the enterprise runtime surface.
- Keep upstream `docker/docker-compose.yaml` intact; put enterprise behavior in the overlay.
- Validate enterprise changes against rebuilt images from the current source tree, not against already-running old containers.
- Never treat local tests alone as release validation after runtime code changed.
- Never copy populated `docker/volumes/**` to a fresh offline Linux deployment.

## Rebuild Decisions

- Backend runtime or API Docker input changed: rebuild `api`, then recreate `api`, `worker`, `worker_beat`, and `nginx`.
- Frontend runtime or web Docker input changed: rebuild `web`, then recreate `web` and `nginx`.
- Only Nginx config changed: recreate `nginx`.
- Formal release packaging must export the same enterprise image IDs that already passed compose runtime validation.

## Standard Commands

```powershell
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml build api
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml build web
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml up -d --force-recreate api worker worker_beat web nginx
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml ps
```

Use `scripts/build-enterprise-offline.ps1` or `scripts/build-enterprise-offline.sh` only after the image batch has been validated.

## Cleanup Boundaries

- Project image cleanup may inspect/remove only confirmed unused `dify-api-enterprise:*`, `dify-web-enterprise:*`, and compose-owned helper layers for this repo.
- Do not touch unrelated local images from other projects.
- Do not delete `docker/volumes/**` unless the user explicitly asks to reset runtime data or approves after the impact is explained.

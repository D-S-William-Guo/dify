# Dify Enterprise Overlay

This repository keeps the upstream `docker/docker-compose.yaml` intact and layers enterprise-specific behavior through `docker/docker-compose.enterprise.yaml`.

## What the enterprise overlay changes

- Replaces `api`, `worker`, and `worker_beat` with your self-built `dify-api-enterprise` image.
- Replaces `web` with your self-built `dify-web-enterprise` image.
- Injects enterprise defaults through environment variables:
  - `PLATFORM_ADMIN_EMAILS`
  - `ALLOW_REGISTER=false`
  - `ALLOW_CREATE_WORKSPACE=false`

## Recommended deployment flow

1. Copy `docker/.env.example` to `docker/.env` and fill in deployment values.
1. Set `PLATFORM_ADMIN_EMAILS` to the comma-separated enterprise admin mailbox list.
1. Choose one enterprise image version string for this release.
1. Use the same version string for compose startup, image build, and offline packaging.

Recommended image tag rule:

- `official-version-enterprise`
- Example: `1.13.3-enterprise`

Notes:

- `docker/docker-compose.enterprise.yaml` already reads `DIFY_ENTERPRISE_VERSION`, so you do not need to hardcode version text into compose.
- The canonical enterprise image names are:
  - `dify-api-enterprise:<official-version-enterprise>`
  - `dify-web-enterprise:<official-version-enterprise>`
- `worker` and `worker_beat` reuse `dify-api-enterprise:<official-version-enterprise>` at runtime.
- If you temporarily add separate `worker` or `worker_beat` tags for local inspection, treat them as convenience aliases rather than formal release image names.
- For local temporary verification, `local` or `enterprise-local` is still acceptable.

Example in PowerShell:

```powershell
$env:DIFY_ENTERPRISE_VERSION = "1.13.3-enterprise"
```

1. Build and export images on an online build machine:

```powershell
.\scripts\build-enterprise-offline.ps1 -Version 1.13.3-enterprise
```

1. Transfer the generated `.tar` archive to the offline server.
1. Load images on the offline server:

```bash
docker load -i dify-enterprise-offline-1.13.3-enterprise.tar
```

1. Start services with the upstream compose file plus the enterprise overlay:

```bash
cd docker
docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d
```

## Final packaging commands

### Windows 11 + Docker Desktop

```powershell
cd D:\CodexSpace\dify
python docker/dify-env-sync.py --dir docker --no-backup
$env:DIFY_ENTERPRISE_VERSION = "1.13.3-enterprise"
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
.\scripts\build-enterprise-offline.ps1 -Version $env:DIFY_ENTERPRISE_VERSION -Mode smart
```

### GUI Ubuntu cloud desktop

```bash
cd ~/dify
python3 docker/dify-env-sync.py --dir docker --no-backup
export DIFY_ENTERPRISE_VERSION=1.13.3-enterprise
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
./scripts/build-enterprise-offline.sh -Version $DIFY_ENTERPRISE_VERSION -Mode smart
```

Notes:

- Replace `1.13.3-enterprise` with the real release version for the current upstream sync.
- `Mode=smart` is the recommended default only when this packaging run follows an already-completed current-source compose validation and image rebuild decision:
  - reuse existing enterprise images when the tag exists and the internal `COMMIT_SHA` matches
  - rebuild automatically only when the image is missing or the internal version does not match
- If this round includes backend or frontend runtime code changes and the enterprise images have not yet been rebuilt from the current source tree, do not rely on `Mode=smart` to discover that drift for you.
- After current-source compose validation has rebuilt the required enterprise images for this source tree, prefer `Mode=reuse` for packaging so the exported bundle is forced to use the just-validated images instead of rebuilding again with a different path.
- Use `Mode=rebuild` when you want to force a clean rebuild.
- Use `Mode=reuse` when you want packaging to fail instead of rebuilding.
- If you only want a local runtime check and do not need an offline bundle, you can skip the last step and run compose directly from `docker/`.

## Development validation and image rebuild rules

Use `Windows 11 + Docker Desktop + Git` as the default local enterprise development baseline. For route 2 and similar performance work, validate with browser clicks plus container logs, but only after confirming the running containers represent the code you just changed.

Compose rules:

- Treat `docker/docker-compose.yaml` as the runtime skeleton.
- Treat `docker/docker-compose.enterprise.yaml` as the enterprise build and override layer.
- Treat `docker/docker-compose-template.yaml` as the generator source for the main compose file, not as the file to edit casually for local enterprise verification.
- Prefer `docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml ...` for `config`, `build`, `up`, `exec`, `ps`, and `logs`.

Rules:

- Do not assume the running `api` or `web` containers are source bind mounts. Inspect mounts first.
- If `api` or `web` run from prebuilt images, treat them as old runtime snapshots until current-source validation succeeds.
- Local regression checks such as `pytest`, `pnpm type-check`, or targeted frontend tests are the first gate only. They do not prove that the enterprise runtime images used by compose or offline packaging contain the current source tree.
- After changing enterprise code, validate the current source tree through compose before trusting runtime behavior:
  - frontend runtime changes: run `docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml build web`, because `web/Dockerfile` compiles the app during the image build
  - backend runtime changes: rebuild the API enterprise image through compose, then use compose-owned containers for follow-up runtime or targeted checks
  - if a standalone container is ever needed for a special case, treat it as an exception and keep the command aligned with the compose-defined image and environment
- Treat the following as frontend runtime changes that require enterprise web image rebuild before packaging:
  - files under `web/app/**`, `web/components/**`, `web/context/**`, `web/service/**`, `web/utils/**`
  - frontend i18n resources used at runtime
  - frontend build helpers that affect bundled output, such as `web/tailwind-css-plugin.ts`
- Treat the following as backend runtime changes that require enterprise API image rebuild before packaging:
  - files under `api/**` except pure test-only changes
  - backend dependency or Docker build-input changes
- Rebuild `dify-api-enterprise:<official-version-enterprise>` when backend runtime code, backend dependencies, or API image build inputs change.
- Rebuild `dify-web-enterprise:<official-version-enterprise>` when frontend runtime code, frontend dependencies, or web image build inputs change.
- `worker` and `worker_beat` reuse the API enterprise image at runtime, so API image rebuild decisions also affect them.
- After rebuilding `dify-api-enterprise:<official-version-enterprise>`, recreate `api`, `worker`, and `worker_beat` through the enterprise compose stack with `--force-recreate` so all three services switch to the same current image ID.
- Otherwise, old `worker` or `worker_beat` containers may keep running on a previous image layer while the tag already points to a newer image, leaving the old layer as a dangling `<none>` image.
- For packaging or release checks, verify both the version tag and the image-internal `COMMIT_SHA`.
- If runtime code changed in this round, the required compose image rebuild must happen before offline packaging. Do not package first and assume `smart` mode will catch stale runtime images.

For enterprise-page route 2 work, the default service tiers are:

- Minimal validation set:
  - `api`
  - `web`
  - `db_postgres`
  - `redis`
  - `nginx`
- Recommended realistic set:
  - `worker`
  - `worker_beat`
- Non-essential for this route:
  - `weaviate`
  - `plugin_daemon`
  - `sandbox`
  - `ssrf_proxy`

Project-scoped image cleanup rules:

- Only analyze and clean images that belong to this repository, such as `dify-api-enterprise:*`, `dify-web-enterprise:*`, compose-owned local build layers, and explicit helper images used for this repo's validation.
- Never clean unrelated local images from other projects or model stacks.
- Identify compose-in-use images first and do not remove them.

Runtime data protection rules:

- Do not delete active runtime data under `docker/volumes/**` as part of routine development, route 2 work, image rebuilds, or compose recreates.
- These directories can hold the local database, uploaded files, Redis state, plugin state, and vector-store state for the current environment.
- Only remove them when the user explicitly asks to reset the environment, or after proposing the deletion and getting the user's approval.
- Treat cleanup of images and cleanup of runtime data as different operations. Image cleanup can be routine; runtime-data cleanup requires explicit user permission.

Compose restart granularity rules:

- Do not default to restarting the entire compose stack after every enterprise build.
- Prefer the smallest compose-owned recreate set that matches the changed runtime surface.
- After rebuilding the web enterprise image, recreate `web` and `nginx` together:
  - `docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d --force-recreate web nginx`
- On Windows 11 + Docker Desktop, rebuild the web enterprise image through [`build-enterprise-web.ps1`](D:\CodexSpace\dify\docker\scripts\build-enterprise-web.ps1) so compose receives a prepared minimal build context instead of traversing local `node_modules` reparse points.
- After rebuilding the API enterprise image, recreate `api`, `worker`, `worker_beat`, and `nginx` together:
  - `docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d --force-recreate api worker worker_beat nginx`
- If only Nginx templates, proxy rules, or HTTPS assets changed, recreate only `nginx`.
- Escalate to a broader compose restart only when service scope is unclear, dependency state is inconsistent, or network state appears stale.

## Fresh environment initialization

If the target machine is meant to be a fresh deployment, do not copy your local runtime data directories.

Bring these:

- `docker/` configuration files and templates
- your finalized `docker/.env`
- the offline image archive and image list
- certificates if HTTPS is enabled

Do not copy these local data directories into the new machine:

- `docker/volumes/app/storage`
- `docker/volumes/db/data`
- `docker/volumes/redis/data`
- `docker/volumes/plugin_daemon`
- `docker/volumes/weaviate`
- other populated `docker/volumes/**` runtime data

On the target machine, Docker Compose will create empty data directories and volumes on first startup.

## First startup on the target machine

```bash
cd ~/dify/docker
cp .env.example .env
# fill in the real deployment values in .env
docker load -i ../dist/offline/dify-enterprise-offline-1.13.3-enterprise.tar
docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d
```

Notes:

- Replace `1.13.3-enterprise` with the current release version.
- If you already prepared a finalized `.env`, use it directly instead of copying `.env.example`.

## Upgrade workflow

1. Sync the latest upstream changes into your enterprise branch.
1. Run `docker/dify-env-sync.py` or `docker/dify-env-sync.sh` to align `docker/.env` with the latest `docker/.env.example`.
1. Confirm the upstream Dify version included in this sync.
1. Set `DIFY_ENTERPRISE_VERSION` to `official-version-enterprise`.
1. Run local regression checks first, but treat them only as the first gate.
1. Rebuild the required enterprise images through compose from the current source tree:
   - frontend runtime changes: rebuild `web`
   - backend runtime changes: rebuild `api`, `worker`, and `worker_beat`
1. If runtime behavior needs verification, validate against the rebuilt compose services before packaging.
1. Re-export the offline bundle from the rebuilt images, preferably with `Mode=reuse`, and deliver it to the production server.

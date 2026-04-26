# Dify Enterprise Overlay

This repository keeps the upstream `docker/docker-compose.yaml` intact and layers enterprise-specific behavior through `docker/docker-compose.enterprise.yaml`.

## Current enterprise source baseline

The enterprise overlay must follow the clean-candidate workflow described in `../README.enterprise-maintenance.md`.

- `main` tracks `upstream/main`.
- `codex/enterprise-candidate-20260424` is the current validated enterprise candidate.
- The previous `enterprise/main` and `codex/protect-enterprise-main-20260424-103050` are historical references only.
- Do not bring Docker changes from the old dirty branch unless they are deployment-safe, documented here, and validated against the current candidate source tree.
- Do not copy populated `docker/volumes/**` from a local machine to a fresh offline Linux deployment.

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
1. Read the synced upstream version from `api/pyproject.toml` and `web/package.json`.
1. Confirm those two source-of-truth files report the same official version.
1. Generate one enterprise image version string for this release as `official-version-enterprise`.
1. Use that same version string for local validation, compose startup, image build, offline packaging, and production deployment.

Recommended image tag rule:

- `official-version-enterprise`
- Example: `1.13.3-enterprise`

Notes:

- `api/pyproject.toml` and `web/package.json` are the golden sources for the upstream official version included in this sync.
- If those two files disagree on the version, stop. Resolve the sync or merge inconsistency first, and do not continue local validation, image rebuilds, offline packaging, or production delivery.
- `docker/docker-compose.enterprise.yaml` already reads `DIFY_ENTERPRISE_VERSION`, so you do not need to hardcode version text into compose.
- The canonical enterprise image names are:
  - `dify-api-enterprise:<official-version-enterprise>`
  - `dify-web-enterprise:<official-version-enterprise>`
- `worker` and `worker_beat` reuse `dify-api-enterprise:<official-version-enterprise>` at runtime.
- If you temporarily add separate `worker` or `worker_beat` tags for local inspection, treat them as convenience aliases rather than formal release image names.
- After you derive `official-version-enterprise`, keep that exact `DIFY_ENTERPRISE_VERSION` value unchanged across compose validation, rebuilt runtime containers, offline packaging, and the target-machine deployment.
- For local temporary verification, `local` or `enterprise-local` is still acceptable only when you are explicitly not treating that run as the formal validation or release path.

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
- Derive that real release version from the synced `api/pyproject.toml` and `web/package.json`, not from memory or a manually guessed tag.
- `Mode=smart` is the recommended default only when this packaging run follows an already-completed current-source compose validation and image rebuild decision:
  - reuse existing enterprise images when the tag exists and the internal `COMMIT_SHA` matches
  - rebuild automatically only when the image is missing or the internal version does not match
- If this round includes backend or frontend runtime code changes and the enterprise images have not yet been rebuilt from the current source tree, do not rely on `Mode=smart` to discover that drift for you.
- After current-source compose validation has rebuilt the required enterprise images for this source tree, prefer `Mode=reuse` for packaging so the exported bundle is forced to use the just-validated images instead of rebuilding again with a different path.
- Use `Mode=rebuild` when you want to force a clean rebuild.
- Use `Mode=reuse` when you want packaging to fail instead of rebuilding.
- If you only want a local runtime check and do not need an offline bundle, you can skip the last step and run compose directly from `docker/`.

## Minimal offline package rule

After a candidate has passed source checks, rebuilt-image compose validation, browser-click validation, and log inspection, package the smallest release artifact that can reproduce that validated runtime.

Use two artifacts:

- Image bundle: a single `docker save` archive generated by `scripts/build-enterprise-offline.ps1` or `scripts/build-enterprise-offline.sh` with `Mode=reuse`.
- Configuration bundle: a small archive containing only deployment configuration files needed to run the enterprise compose stack.

Do not rebuild during final packaging after runtime validation. `Mode=reuse` is the release default because it fails fast if `dify-api-enterprise:<version>` or `dify-web-enterprise:<version>` is missing or has a mismatched internal `COMMIT_SHA`.

Minimal configuration bundle contents:

- `docker/docker-compose.yaml`
- `docker/docker-compose.enterprise.yaml`
- `docker/.env.example`
- `docker/middleware.env.example`
- `docker/dify-env-sync.py`
- `docker/dify-env-sync.sh`
- `docker/README.enterprise.md`
- `docker/nginx/**`
- `docker/ssrf_proxy/**`
- `dist/offline/manifest-<version>.json`
- `dist/offline/images-<version>.txt`

Exclude all local runtime and build artifacts:

- `docker/volumes/**`
- `docker/.build/**`
- `node_modules/**`
- `web/.next/**`
- `api/.venv/**`
- `.git/**`
- local logs, caches, and temporary test data

The minimal configuration bundle is intentionally separate from the image bundle. This keeps the image archive immutable and easy to verify, while allowing operators to compare or merge configuration files before touching an existing deployment.

### Existing remote deployment compatibility

The minimal configuration bundle is compatible with a remote machine that already has Dify runtime state, as long as the deployment is upgraded as configuration plus images rather than as a copied workspace tree.

For an existing remote deployment:

1. Back up the remote `docker/.env` and any customized `docker/nginx/**` or `docker/ssrf_proxy/**` files.
1. Load the new image bundle with `docker load -i dify-enterprise-offline-<version>.tar`.
1. Copy the new compose and template files into the remote `docker/` directory, but do not overwrite the remote `.env` blindly.
1. Run `python3 docker/dify-env-sync.py --dir docker --no-backup` or the shell equivalent to merge new `.env.example` keys into the existing `.env`.
1. Review enterprise-required variables such as `PLATFORM_ADMIN_EMAILS`, `DIFY_ENTERPRISE_VERSION`, `ALLOW_REGISTER`, and `ALLOW_CREATE_WORKSPACE`.
1. Run `docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml config -q`.
1. Recreate only the affected services, or run the normal enterprise compose `up -d` if the target environment is a controlled maintenance window.

Never copy local `docker/volumes/**` onto an existing remote deployment. Existing database, storage, Redis, plugin, and vector-store state must remain on the remote machine unless a deliberate restore or reset is being performed.

If the remote deployment has local customizations in compose, nginx, or SSRF proxy files, compare those customizations before replacing files. The minimal bundle is designed to make this review small; it is not a license to overwrite operator-owned changes without inspection.

## Verified-image rule

For enterprise development, treat source verification, compose runtime verification, and offline packaging as one continuous chain. Do not switch validation targets in the middle.

Hard rules:

- Local regression checks such as `pytest`, `pnpm type-check`, and targeted frontend tests only prove the source tree is plausible. They do not prove that the running enterprise containers or the final offline package contain that source tree.
- If runtime code changed in this round, rebuild the required enterprise images first, then recreate the affected compose services, then do browser clicks and log inspection against those rebuilt containers.
- Treat browser clicks, compose `logs`, compose `exec`, and smoke checks against older enterprise containers as invalid for release decisions once newer source changes exist locally.
- Offline packaging must export the same enterprise image IDs that already passed this round's compose-based runtime verification.
- If the local source tree and the running enterprise containers are not on the same rebuilt image batch, stop and rebuild before continuing validation or packaging.
- `Mode=reuse` is the preferred release mode after successful rebuild plus runtime verification, because it guarantees packaging reuses the exact verified images.
- `Mode=smart` is only acceptable before runtime verification when deciding whether a rebuild is needed, or in low-risk local convenience flows that are not being treated as release validation.

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
- When `api`, `worker`, and `worker_beat` share the same enterprise image name, treat `api` as the single rebuild source. Rebuild the shared API image from the `api` service definition first, then recreate `api`, `worker`, and `worker_beat` from that rebuilt tag.
- Do not assume that a multi-service `docker compose build api worker worker_beat` run proves the three services now point at one identical validated image batch. Confirm the rebuilt shared tag and the running container image IDs after recreate.
- After rebuilding `dify-api-enterprise:<official-version-enterprise>`, recreate `api`, `worker`, and `worker_beat` through the enterprise compose stack with `--force-recreate` so all three services switch to the same current image ID.
- Otherwise, old `worker` or `worker_beat` containers may keep running on a previous image layer while the tag already points to a newer image, leaving the old layer as a dangling `<none>` image.
- For packaging or release checks, verify both the version tag and the image-internal `COMMIT_SHA`.
- If runtime code changed in this round, the required compose image rebuild must happen before offline packaging. Do not package first and assume `smart` mode will catch stale runtime images.
- After the required rebuild, recreate the affected compose services before browser validation so clicks and logs are taken from the same image batch that will later be packaged.
- For release readiness, treat "latest rebuilt compose containers" as the only valid runtime verification target. Source-only checks or older still-running containers are not sufficient.

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
- If the release only changes backend runtime code, you still package the full offline bundle, but only the API enterprise image needs rebuilding in this round. The rest of the bundle may be reused from the already-verified image batch.
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

Required enterprise variables for a fresh target:

- `DIFY_ENTERPRISE_VERSION`: must match the offline image bundle version, for example `1.13.3-enterprise`. If this is missing, compose falls back to `local` and the target may fail to find the loaded enterprise images.
- `PLATFORM_ADMIN_EMAILS`: comma-separated platform administrator email addresses.
- `ALLOW_REGISTER`: normally `false` for a locked-down enterprise deployment.
- `ALLOW_CREATE_WORKSPACE`: normally `false` for a locked-down enterprise deployment.
- `CONSOLE_API_URL` and `APP_API_URL`: leave empty for same-domain nginx deployment; set them only when API and web are served from different external domains.
- `DIFY_INTERNAL_API_URL`: normally do not set it. The enterprise overlay defaults web SSR/API-internal calls to `http://api:5001` inside the compose network.

## First startup on the target machine

```bash
cd ~/dify/docker
cp .env.example .env
# fill in the real deployment values in .env:
# DIFY_ENTERPRISE_VERSION=1.13.3-enterprise
# PLATFORM_ADMIN_EMAILS=admin@example.com
# ALLOW_REGISTER=false
# ALLOW_CREATE_WORKSPACE=false
docker load -i ../dist/offline/dify-enterprise-offline-1.13.3-enterprise.tar
docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d
```

Notes:

- Replace `1.13.3-enterprise` with the current release version.
- If you already prepared a finalized `.env`, use it directly instead of copying `.env.example`.

## Upgrade workflow

1. Sync `main` to the latest `upstream/main`.
1. Create a new clean enterprise candidate branch from `main`.
1. Replay only the required enterprise patch groups documented in `../ENTERPRISE_REPLAY_PLAN.md`.
1. Run `docker/dify-env-sync.py` or `docker/dify-env-sync.sh` to align `docker/.env` with the latest `docker/.env.example`.
1. Read the synced upstream version from `api/pyproject.toml` and `web/package.json`, and confirm they match.
1. If those files do not match, stop and fix the sync inconsistency before any validation, rebuild, packaging, or deployment step.
1. Set `DIFY_ENTERPRISE_VERSION` to the derived `official-version-enterprise`.
1. Run local regression checks first, but treat them only as the first gate.
1. Rebuild the required enterprise images through compose from the current source tree:
   - frontend runtime changes: rebuild `web`
   - backend runtime changes: rebuild `api`, `worker`, and `worker_beat`
1. Recreate the affected compose services so runtime verification uses the same rebuilt images that are about to be packaged.
1. If runtime behavior needs verification, validate against the rebuilt and recreated compose services before packaging.
1. Re-export the offline bundle from the verified rebuilt images, preferably with `Mode=reuse`, and deliver it to the production server with the same `DIFY_ENTERPRISE_VERSION`.

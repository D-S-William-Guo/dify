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
- `Mode=smart` is the recommended default:
  - reuse existing enterprise images when the tag exists and the internal `COMMIT_SHA` matches
  - rebuild automatically only when the image is missing or the internal version does not match
- Use `Mode=rebuild` when you want to force a clean rebuild.
- Use `Mode=reuse` when you want packaging to fail instead of rebuilding.
- If you only want a local runtime check and do not need an offline bundle, you can skip the last step and run compose directly from `docker/`.

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
1. Rebuild enterprise images with that version tag.
1. Re-export the offline bundle and deliver it to the production server.

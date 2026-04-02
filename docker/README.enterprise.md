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
- `api`, `worker`, `worker_beat`, and `web` should all use the same enterprise version string.
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

## Upgrade workflow

1. Sync the latest upstream changes into your enterprise branch.
1. Run `docker/dify-env-sync.py` or `docker/dify-env-sync.sh` to align `docker/.env` with the latest `docker/.env.example`.
1. Confirm the upstream Dify version included in this sync.
1. Set `DIFY_ENTERPRISE_VERSION` to `official-version-enterprise`.
1. Rebuild enterprise images with that version tag.
1. Re-export the offline bundle and deliver it to the production server.

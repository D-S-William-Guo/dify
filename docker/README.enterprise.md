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
1. Build and export images on an online build machine:

```powershell
.\scripts\build-enterprise-offline.ps1 -Version 2026.03.28
```

1. Transfer the generated `.tar` archive to the offline server.
1. Load images on the offline server:

```bash
docker load -i dify-enterprise-offline-2026.03.28.tar
```

1. Start services with the upstream compose file plus the enterprise overlay:

```bash
cd docker
docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d
```

## Upgrade workflow

1. Sync the latest upstream changes into your enterprise branch.
1. Run `docker/dify-env-sync.py` or `docker/dify-env-sync.sh` to align `docker/.env` with the latest `docker/.env.example`.
1. Rebuild enterprise images with a new version tag.
1. Re-export the offline bundle and deliver it to the production server.

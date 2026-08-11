# Phase D Row 1 — Production PostgreSQL 15 (enterprise 1.15) → enterprise 1.16

Validator: `replay-116-b8-phase-d-validator` (2026-08-11)
Evidence root: `docs/enterprise/replay-1.16.0/evidence/phase-d/db-matrix/row-1-prod-pg15-enterprise-upgrade.md`
Scope: VALIDATION_PLAN Phase D "必须运行" row 1; decision sheet matrix row 1.

## Result: PASS

Isolated copy only. No production data, `docker/volumes/**`, or the running
`docker-db_postgres-1` data were touched or copied to the repo. Online consistent
`pg_dump` created under `/tmp/replay-116-phase-d/` (0700, never committed).

## Steps and exact commands

| # | Command | Exit | Result |
| --- | --- | ---: | --- |
| 1 | `git branch --show-current` / `git rev-parse HEAD` / `git status --short --branch` | 0 | `ctyun/replay-116-b8-phase-d-validator` / `6ff8d99f377571b0cccc4f398a9ffd094c90b66c` / clean |
| 2 | read-only inventory on production (B2 baseline): `docker exec -e PGOPTIONS='-c default_transaction_read_only=on' docker-db_postgres-1 psql -X -U postgres -d dify` | 0 | see PRE |
| 3 | `docker exec docker-db_postgres-1 pg_dump --version` | 0 | `pg_dump (PostgreSQL) 15.17` |
| 4 | online dump: `docker exec docker-db_postgres-1 pg_dump -U postgres -d dify --format=custom --no-owner --no-acl --lock-wait-timeout=10 > /tmp/replay-116-phase-d/prod-pg15-enterprise-115.dump` | 0 | 2,314,617 bytes custom-format |
| 5 | `docker network create dify-b8-phase-d-net` / `docker volume create dify-b8-phase-d-pg15-data` | 0 | isolated bridge net + ephemeral volume |
| 6 | `docker run -d --name dify-b8-phase-d-pg15-r1 --network dify-b8-phase-d-net -p 127.0.0.1:15432:5432 -e POSTGRES_PASSWORD=phased_isolated_pw -e POSTGRES_DB=dify -v dify-b8-phase-d-pg15-data:/var/lib/postgresql/data postgres:15-alpine` | 0 | fresh PostgreSQL 15.17 isolated copy |
| 7 | restore: `docker exec -i dify-b8-phase-d-pg15-r1 pg_restore -U postgres -d dify --no-owner --no-acl --exit-on-error < prod-pg15-enterprise-115.dump` | 0 | restored |
| 8 | pre-upgrade inventory on restored copy | 0 | matches production PRE exactly |
| 9 | `env -u ALL_PROXY -u all_proxy UV_CACHE_DIR=../.uv-cache FLASK_APP=app.py DB_HOST=127.0.0.1 DB_PORT=15432 DB_USERNAME=postgres DB_PASSWORD=phased_isolated_pw DB_DATABASE=dify uv run flask db upgrade` | 0 | see migration log |
| 10 | post-upgrade inventory + schema check on restored copy | 0 | see POST |

## Alembic version

| State | alembic_version |
| --- | --- |
| PRE (production and restored copy) | `e2f0a9b7c6d5` (old enterprise head) |
| POST | `b416e5c4e702` (single enterprise head) |

## Migration log (row 1)

```
Running upgrade d9e8f7a6b5c4 -> a6f1c9d2e8b4, add input placeholder to sites
Running upgrade a6f1c9d2e8b4 -> e4f5a6b7c8d9, add agent config drafts
Running upgrade e4f5a6b7c8d9 -> a2b3c4d5e6f7, add agent backing app id
Running upgrade a2b3c4d5e6f7 -> c3d4e5f6a7b8, add agent active config is published
Running upgrade c3d4e5f6a7b8 -> 7a1c2d9e4b60, add workflow run archive bundle index table
Running upgrade e2f0a9b7c6d5, 7a1c2d9e4b60 -> a71e16c0de01, merge 1.16.0 enterprise migration heads
Running upgrade a71e16c0de01 -> b416e5c4e702, finalize enterprise marketplace schema
```

Exactly the required sequence: 5 official 1.16 revisions → empty merge `a71e16c0de01` → B4 `b416e5c4e702`. No duplicate table creation, no stamp.

## Pre/Post inventory (redacted counts)

| Metric | PRE | POST |
| --- | ---: | ---: |
| server_version | 15.17 | 15.17 |
| alembic_version | e2f0a9b7c6d5 | b416e5c4e702 |
| accounts | 3 | 3 |
| tenants | 5 | 5 |
| tenant_account_joins | 6 | 6 |
| apps | 6 | 6 |
| workflows | 9 | 9 |
| datasets | 4 | 4 |
| documents | 2 | 2 |
| document_segments | 63 | 63 |
| conversations | 2407 | 2407 |
| marketplace_rows | 1 | 1 |
| marketplace status | approved:1 | approved:1 |
| marketplace source_app_id NULL | 0 | 0 |
| marketplace source_app_id non-NULL | 1 | 1 |
| snapshot_table_exists | false | true |
| uuidv7_public | 1 | 1 |
| uuidv7_pg_catalog | 0 | 0 |

## Table/index/constraint checks (POST)

`enterprise_marketplace_assets` 22 columns (16 legacy + 6 B4:
`publication_status`, `published_snapshot_id`, `next_snapshot_version`, `row_version`,
`snapshot_state`, `snapshot_error_code`). Indexes:
`enterprise_marketplace_asset_pkey`,
`enterprise_marketplace_asset_publication_idx`,
`enterprise_marketplace_asset_source_tenant_id_idx`,
`enterprise_marketplace_asset_status_idx`,
`enterprise_marketplace_asset_submitter_idx`,
`unique_enterprise_marketplace_source_app`.
Constraints: pkey, `unique_enterprise_marketplace_source_app`, 3 B4 CHECKs
(publication_status/snapshot_state/next_snapshot_version).

`enterprise_marketplace_asset_snapshots` created with 25 columns, 4 indexes
(pkey, asset_version_uq, asset_frozen_idx, sha256_idx) and 2 CHECK constraints.

## Marketplace row mapping (POST)

`status=approved` preserved unchanged; `publication_status=unpublished`,
`snapshot_state=backfill_pending`, `next_snapshot_version=1`, `row_version=0`,
`snapshot_error_code=NULL`, `published_snapshot_id=NULL`. Matches B4 deterministic
CASE mapping for legacy `approved`.

## Teardown

`docker rm -f dify-b8-phase-d-pg15-r1` and `docker volume rm dify-b8-phase-d-pg15-data`
executed after evidence capture. Dump file retained only under `/tmp/replay-116-phase-d/`.

# Phase D Row 2 — Official 1.15 (`d9e8f7a6b5c4`) → enterprise 1.16

Validator: `replay-116-b8-phase-d-validator` (2026-08-11)
Evidence root: `docs/enterprise/replay-1.16.0/evidence/phase-d/db-matrix/row-2-official-115-enterprise-upgrade.md`
Scope: VALIDATION_PLAN Phase D "必须运行" row 2 (current production PG version, official upgrade);
decision sheet matrix row 2.

## Result: PASS

Official 1.15 baseline DB generated from a temporary git worktree of tag `1.15.0`,
then upgraded with the enterprise 1.16 candidate code. All isolated, nothing
touched production.

## Steps and exact commands

| # | Command | Exit | Result |
| --- | --- | ---: | --- |
| 1 | `git worktree add /tmp/replay-116-phase-d/wt-1.15.0 1.15.0` | 0 | worktree at `3aa26fb6374bbd47e5469f7d7cc25f3e0075a60c` (tag 1.15.0) |
| 2 | `docker run -d --name dify-b8-phase-d-pg15-r2 --network dify-b8-phase-d-net -p 127.0.0.1:15433:5432 -e POSTGRES_PASSWORD=phased_isolated_pw -e POSTGRES_DB=dify postgres:15-alpine` | 0 | fresh empty PostgreSQL 15.17 |
| 3 | from `/tmp/replay-116-phase-d/wt-1.15.0/api`: `env -u ALL_PROXY -u all_proxy UV_CACHE_DIR=../.uv-cache FLASK_APP=app.py DB_HOST=127.0.0.1 DB_PORT=15433 DB_USERNAME=postgres DB_PASSWORD=phased_isolated_pw DB_DATABASE=dify uv run flask db upgrade` | 0 | official 1.15.0 migrations; head `d9e8f7a6b5c4` |
| 4 | pre-upgrade inventory | 0 | empty tables, `alembic_version=d9e8f7a6b5c4` |
| 5 | from candidate `/api`: same env + `uv run flask db upgrade` | 0 | see migration log |
| 6 | post-upgrade inventory + schema check | 0 | see POST |

## Alembic version

| State | alembic_version |
| --- | --- |
| PRE | `d9e8f7a6b5c4` (official 1.15 head, single value) |
| POST | `b416e5c4e702` (single enterprise head) |

## Migration log (row 2)

```
Running upgrade d9e8f7a6b5c4 -> a6f1c9d2e8b4, add input placeholder to sites
Running upgrade a6f1c9d2e8b4 -> e4f5a6b7c8d9, add agent config drafts
Running upgrade e4f5a6b7c8d9 -> a2b3c4d5e6f7, add agent backing app id
Running upgrade a2b3c4d5e6f7 -> c3d4e5f6a7b8, add agent active config is published
Running upgrade c3d4e5f6a7b8 -> 7a1c2d9e4b60, add workflow run archive bundle index table
Running upgrade 227822d22895 -> c8f3d9d4a1be, add enterprise marketplace assets
Running upgrade a4f2d8c9b731, c8f3d9d4a1be -> f1a14e1e9b41, merge 1.14.2 enterprise migration heads
Running upgrade f1a14e1e9b41, d9e8f7a6b5c4 -> e2f0a9b7c6d5, merge 1.15.0 enterprise migration heads
Running upgrade e2f0a9b7c6d5, 7a1c2d9e4b60 -> a71e16c0de01, merge 1.16.0 enterprise migration heads
Running upgrade a71e16c0de01 -> b416e5c4e702, finalize enterprise marketplace schema
```

Required sequence satisfied: 5 official 1.16 revisions + enterprise history branch
(marketplace table created once in `c8f3d9d4a1be`) + empty merge + B4. No duplicate
table creation, no stamp.

## Pre/Post inventory (redacted counts)

| Metric | PRE | POST |
| --- | ---: | ---: |
| alembic_version | d9e8f7a6b5c4 | b416e5c4e702 |
| accounts / tenants / joins | 0 / 0 / 0 | 0 / 0 / 0 |
| apps / workflows | 0 / 0 | 0 / 0 |
| datasets / documents / segments | 0 / 0 / 0 | 0 / 0 / 0 |
| conversations | 0 | 0 |
| marketplace_table_exists | false | true |
| marketplace_rows | — | 0 |
| snapshot_table_exists | false | true |

Official baseline is empty, so counts stay 0; the point of this row is schema
convergence without duplicate creation.

## Table/index/constraint checks (POST)

`enterprise_marketplace_assets` indexes: pkey, publication_idx, source_tenant_id_idx,
status_idx, submitter_idx, unique_enterprise_marketplace_source_app. Constraints:
pkey, unique_enterprise_marketplace_source_app, 3 B4 CHECKs.
`enterprise_marketplace_asset_snapshots` with pkey, asset_version_uq and 2 CHECKs.

## Teardown

`docker rm -f dify-b8-phase-d-pg15-r2` and `docker volume rm dify-b8-phase-d-pg15-r2-data`
executed after evidence capture. Worktree `/tmp/replay-116-phase-d/wt-1.15.0` removed
after all rows that use it (row 2 done; retained until teardown phase).

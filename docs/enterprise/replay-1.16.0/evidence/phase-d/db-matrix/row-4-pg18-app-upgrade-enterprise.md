# Phase D Row 4 — PostgreSQL 18 application upgrade (enterprise 1.15 restore → 1.16)

Validator: `replay-116-b8-phase-d-validator` (2026-08-11)
Evidence root: `docs/enterprise/replay-1.16.0/evidence/phase-d/db-matrix/row-4-pg18-app-upgrade-enterprise.md`
Scope: VALIDATION_PLAN Phase D "必须运行" row 4; decision sheet matrix row 4.

## Result: PASS

An enterprise 1.15 production copy (the same online dump used in row 1) is restored
into a fresh PostgreSQL 18.4 database, then upgraded with the enterprise 1.16
candidate code. The `1c9ba48be8e4` PG18-compatible path is effective (native
`uuidv7()` used), no 1.15-present migration is re-run, all data is preserved.

## Steps and exact commands

| # | Command | Exit | Result |
| --- | --- | ---: | --- |
| 1 | `docker exec dify-b8-phase-d-pg18-r3 psql -U postgres -c "CREATE DATABASE dify_r4;"` | 0 | new empty DB on PG18.4 |
| 2 | `docker exec -i dify-b8-phase-d-pg18-r3 pg_restore -U postgres -d dify_r4 --no-owner --no-acl --exit-on-error < /tmp/replay-116-phase-d/prod-pg15-enterprise-115.dump` | 0 | enterprise 1.15 copy restored |
| 3 | pre-upgrade inventory on `dify_r4` | 0 | `alembic_version=e2f0a9b7c6d5`, all counts match production baseline |
| 4 | from candidate `/api`: `env -u ALL_PROXY -u all_proxy UV_CACHE_DIR=../.uv-cache FLASK_APP=app.py DB_HOST=127.0.0.1 DB_PORT=15434 DB_USERNAME=postgres DB_PASSWORD=phased_isolated_pw DB_DATABASE=dify_r4 uv run flask db upgrade` | 0 | see migration log |
| 5 | post-upgrade inventory + `SELECT uuidv7()` | 0 | see POST |

## Alembic version

| State | alembic_version |
| --- | --- |
| PRE | `e2f0a9b7c6d5` (old enterprise head) |
| POST | `b416e5c4e702` (single head) |

## Migration log (row 4)

```
Running upgrade d9e8f7a6b5c4 -> a6f1c9d2e8b4, add input placeholder to sites
Running upgrade a6f1c9d2e8b4 -> e4f5a6b7c8d9, add agent config drafts
Running upgrade e4f5a6b7c8d9 -> a2b3c4d5e6f7, add agent backing app id
Running upgrade a2b3c4d5e6f7 -> c3d4e5f6a7b8, add agent active config is published
Running upgrade c3d4e5f6a7b8 -> 7a1c2d9e4b60, add workflow run archive bundle index table
Running upgrade e2f0a9b7c6d5, 7a1c2d9e4b60 -> a71e16c0de01, merge 1.16.0 enterprise migration heads
Running upgrade a71e16c0de01 -> b416e5c4e702, finalize enterprise marketplace schema
```

The migration log does NOT re-run `1c9ba48be8e4` (uuidv7) nor the three 1.15-modified
Agent migrations — they are already applied in the enterprise 1.15 lineage and are
correctly not treated as pending. This satisfies the Phase D requirement that these
revisions must not be re-executed on upgrade.

## Pre/Post inventory (redacted counts)

| Metric | PRE | POST |
| --- | ---: | ---: |
| server_version | 18.4 | 18.4 |
| alembic_version | e2f0a9b7c6d5 | b416e5c4e702 |
| accounts / tenants / joins | 3 / 5 / 6 | 3 / 5 / 6 |
| apps / workflows | 6 / 9 | 6 / 9 |
| datasets / documents / segments | 4 / 2 / 63 | 4 / 2 / 63 |
| conversations | 2407 | 2407 |
| marketplace_rows | 1 | 1 |
| marketplace status | approved:1 | approved:1 |
| marketplace source_app_id NULL / non-NULL | 0 / 1 | 0 / 1 |
| snapshot_table_exists | false | true |
| uuidv7_public / uuidv7_pg_catalog | 1 / 2 | 1 / 2 |

## uuidv7

`SELECT substr(uuidv7()::text,15,1)` returns `7` on `dify_r4` post-upgrade (version 7).
The dump-restored `public.uuidv7()` and the native `pg_catalog.uuidv7()` both exist;
queries resolve to a valid version-7 UUID.

## Teardown

PG18 container and volume removed after rows 3/4 evidence capture.

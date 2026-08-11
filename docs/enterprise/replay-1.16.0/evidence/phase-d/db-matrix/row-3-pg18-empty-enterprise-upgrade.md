# Phase D Row 3 — PostgreSQL 18 empty DB → enterprise 1.16

Validator: `replay-116-b8-phase-d-validator` (2026-08-11)
Evidence root: `docs/enterprise/replay-1.16.0/evidence/phase-d/db-matrix/row-3-pg18-empty-enterprise-upgrade.md`
Scope: VALIDATION_PLAN Phase D "必须运行" row 3; decision sheet matrix row 3.

## Result: PASS

Full enterprise migration history runs from zero tables on PostgreSQL 18.4 and
converges to single head `b416e5c4e702`. `SELECT uuidv7()` succeeds and returns a
version-7 UUID.

## Steps and exact commands

| # | Command | Exit | Result |
| --- | --- | ---: | --- |
| 1 | `docker pull postgres:18-alpine` | 0 | `postgres:18-alpine` (PostgreSQL 18.4), digest `sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15` |
| 2 | `docker run -d --name dify-b8-phase-d-pg18-r3 --network dify-b8-phase-d-net -p 127.0.0.1:15434:5432 -e POSTGRES_PASSWORD=phased_isolated_pw -e POSTGRES_DB=dify -v dify-b8-phase-d-pg18-r3-data:/var/lib/postgresql postgres:18-alpine` | 0 | fresh empty PostgreSQL 18.4. Note: PG18 images mount at `/var/lib/postgresql` (new layout), not `/var/lib/postgresql/data`. |
| 3 | `docker exec dify-b8-phase-d-pg18-r3 psql -U postgres -d dify -tAc "SELECT uuidv7();"` | 0 | native `019fef3a-69c9-78a5-b040-8d79e80d8563` (version 7) pre-upgrade |
| 4 | from candidate `/api`: `env -u ALL_PROXY -u all_proxy UV_CACHE_DIR=../.uv-cache FLASK_APP=app.py DB_HOST=127.0.0.1 DB_PORT=15434 DB_USERNAME=postgres DB_PASSWORD=phased_isolated_pw DB_DATABASE=dify uv run flask db upgrade` | 0 | 205 `Running upgrade` steps, ends at `b416e5c4e702` |
| 5 | post-upgrade inventory + schema check + `SELECT uuidv7()` | 0 | see POST |

## Alembic version

| State | alembic_version |
| --- | --- |
| PRE | `<none>` (empty DB) |
| POST | `b416e5c4e702` (single head) |

## uuidv7

- Pre-upgrade: `SELECT uuidv7()` returns `019fef3a-…` (third group `78a5` → version 7), native `pg_catalog.uuidv7`.
- Post-upgrade: `SELECT substr(uuidv7()::text,15,1)` returns `7`; `uuidv7_public=0` and
  `uuidv7_pg_catalog=2` — the `1c9ba48be8e4` PG18-compatible path correctly detected the
  built-in `pg_catalog.uuidv7` via the DO-block existence check and skipped creating a
  colliding `public.uuidv7()`.

## Post inventory (empty baseline, so all counts 0)

marketplace_table_exists=true, marketplace_rows=0, snapshot_table_exists=true,
alembic_version=b416e5c4e702.

## Table/index/constraint checks (POST)

`enterprise_marketplace_assets`: 22 columns, indexes pkey/publication_idx/source_tenant_id_idx/
status_idx/submitter_idx/unique_enterprise_marketplace_source_app, constraints include the 3 B4
CHECKs (`ck_marketplace_asset_next_*`, `ck_marketplace_asset_publ_*`,
`ck_marketplace_asset_snap_*`) and `unique_enterprise_marketplace_source_app`.
`enterprise_marketplace_asset_snapshots`: 25 columns, pkey/asset_version_uq/asset_frozen_idx/
sha256_idx and 2 CHECKs.

Observation: on PG18 the `ALTER COLUMN SET NOT NULL` operations materialize as named
`<table>_<column>_not_null` entries in `pg_constraint` (PG18 native representation);
NOT NULL enforcement and the B4 CHECK constraints are unaffected. Recorded as a
version-representation difference, not a defect.

## Teardown

PG18 container and volume removed after rows 3/4 evidence capture.

# Phase D Row 6 — Backup/restore rollback drill

Validator: `replay-116-b8-phase-d-validator` (2026-08-11)
Evidence root: `docs/enterprise/replay-1.16.0/evidence/phase-d/rollback-drill/row-6-backup-restore-rollback.md`
Scope: VALIDATION_PLAN §3 "唯一受支持的回滚方法"; decision sheet matrix row 6.

## Result: PASS

The only supported rollback method is: stop 1.16, isolate the migrated database,
restore the pre-upgrade full consistent backup into a new recovery target. This
drill proves that sequence at the database level on isolated copies.

## Method (aligned to VALIDATION_PLAN §3)

1. Pre-upgrade full consistent backup = online custom-format `pg_dump` of
   `docker-db_postgres-1` (`/tmp/replay-116-phase-d/prod-pg15-enterprise-115.dump`,
   created with `--lock-wait-timeout=10`).
2. Container A = migrated copy: backup restored → enterprise 1.16 `flask db upgrade`
   applied (the state that would be rolled back from).
3. Container B = recovery target: same backup restored into a fresh container and
   left at 1.15 (simulating restore of the archived backup to a new target).
4. Inventory comparison A vs B proves B is a clean 1.15 state identical to the
   pre-upgrade baseline.

## Steps and exact commands

| # | Command | Exit | Result |
| --- | --- | ---: | --- |
| 1 | create two isolated PG15 containers `dify-b8-phase-d-pg15-r6a` / `-r6b` on `dify-b8-phase-d-net` (ports 15436/15437) | 0 | PostgreSQL 15.17 both |
| 2 | `docker exec -i dify-b8-phase-d-pg15-r6a pg_restore -U postgres -d dify --no-owner --no-acl --exit-on-error < prod-pg15-enterprise-115.dump` | 0 | restore A |
| 3 | same command for `-r6b` | 0 | restore B |
| 4 | from candidate `/api`: `uv run flask db upgrade` against A (port 15436) | 0 | A now `b416e5c4e702` |
| 5 | inventory on A and B | 0 | see comparison |

## Result comparison (redacted counts)

| Metric | Pre-upgrade baseline | A (migrated) | B (recovered) |
| --- | ---: | ---: | ---: |
| alembic_version | e2f0a9b7c6d5 | b416e5c4e702 | e2f0a9b7c6d5 |
| accounts / tenants / joins | 3 / 5 / 6 | 3 / 5 / 6 | 3 / 5 / 6 |
| apps / workflows | 6 / 9 | 6 / 9 | 6 / 9 |
| datasets / documents / segments | 4 / 2 / 63 | 4 / 2 / 63 | 4 / 2 / 63 |
| conversations | 2407 | 2407 | 2407 |
| marketplace_rows | 1 | 1 | 1 |
| marketplace status | approved:1 | approved:1 | approved:1 |
| marketplace source_app_id NULL / non-NULL | 0 / 1 | 0 / 1 | 0 / 1 |
| snapshot_table_exists | false | true | false |

Recovered target B matches the pre-upgrade baseline exactly, including
`alembic_version=e2f0a9b7c6d5` and no B4 snapshot table. This confirms the backup
restore returns a clean, complete 1.15 state on a new target without re-running any
migration and without using `alembic downgrade`.

## Scope notes

- The full "start 1.15 and verify account/workspace/app/workflow/dataset/plugin/file/
  vector" application-level verification is a Phase G runtime gate and remains NOT_RUN
  here; this drill covers the database restore/inventory level that Phase D is scoped to.
- The migrated container A was isolated (not reused, not deleted until teardown), per the
  "isolate migrated DB" rule.

## Teardown

`docker rm -f dify-b8-phase-d-pg15-r6a dify-b8-phase-d-pg15-r6b` and volumes removed
after evidence capture.

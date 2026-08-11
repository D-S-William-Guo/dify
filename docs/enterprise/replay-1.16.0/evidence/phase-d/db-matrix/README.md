# Phase D Database Upgrade Matrix — Summary

Validator: `replay-116-b8-phase-d-validator` (2026-08-11)
Head: `6ff8d99f377571b0cccc4f398a9ffd094c90b66c`

All six "必须运行" rows executed on isolated copies only. Production data was only
read (read-only inventory + online `pg_dump` via `docker exec docker-db_postgres-1`).
No production data, `docker/volumes/**`, or the running stack was modified. All dumps
and logs lived under `/tmp/replay-116-phase-d/` (0700) and were never committed.

## Matrix results

| Row | Scenario | Source | Target head | Result |
| --- | --- | --- | --- | --- |
| 1 | Current production PG15, enterprise upgrade | enterprise 1.15 `e2f0a9b7c6d5` (online pg_dump) | `b416e5c4e702` | PASS |
| 2 | Current production PG15, official upgrade | official 1.15 `d9e8f7a6b5c4` (tag 1.15.0 worktree DB) | `b416e5c4e702` | PASS |
| 3 | PostgreSQL 18 empty DB | `<none>` | `b416e5c4e702` | PASS |
| 4 | PostgreSQL 18 application upgrade | enterprise 1.15 `e2f0a9b7c6d5` restored on PG18 | `b416e5c4e702` | PASS |
| 5 | Current production PG15, official 1.16 | official 1.16 `7a1c2d9e4b60` (tag 1.16.0 worktree DB) | `b416e5c4e702` | PASS |
| 6 | Backup/restore rollback drill | pre-upgrade dump → migrated A vs recovered B | A `b416e5c4e702`, B `e2f0a9b7c6d5` | PASS |

## Per-row evidence

- `db-matrix/row-1-prod-pg15-enterprise-upgrade.md`
- `db-matrix/row-2-official-115-enterprise-upgrade.md`
- `db-matrix/row-3-pg18-empty-enterprise-upgrade.md`
- `db-matrix/row-4-pg18-app-upgrade-enterprise.md`
- `db-matrix/row-5-official-116-enterprise-upgrade.md`
- `rollback-drill/row-6-backup-restore-rollback.md`

## Cross-row assertions

1. Single final enterprise head `b416e5c4e702` reached on every row.
2. Historical revisions `c8f3d9d4a1be`, `f1a14e1e9b41`, `e2f0a9b7c6d5` resolve and apply
   on the official 1.15/1.16 upgrade paths (rows 2, 5).
3. Empty merge `a71e16c0de01` parents = `e2f0a9b7c6d5` + `7a1c2d9e4b60`; no business DDL
   in the merge (verified via file review `2026_07_21_1000-a71e16c0de01_*.py`).
4. B4 `b416e5c4e702` sits after the merge; all 1.16 marketplace columns/indexes/
   constraints live only there.
5. Row 2 ran exactly 5 official 1.16 revisions; no duplicate table creation on any row.
6. Rows 1/4 did NOT re-run `1c9ba48be8e4` (uuidv7) or the three 1.15-modified Agent
   migrations (already applied in the 1.15 lineage; verified in migration logs).
7. `SELECT uuidv7()` returns version-7 UUIDs on PG18 (native `pg_catalog.uuidv7`, rows 3/4).
8. Marketplace rows/status/`source_app_id` preserved identically on every data-bearing
   row (rows 1, 4, 6).
9. Rollback drill: backup restore into a new target returns an exact 1.15 state
   (`e2f0a9b7c6d5`, no snapshot table, identical counts).

## NOT_RUN / scope

- Application-level (start 1.15/1.16 stack, browser, API, vector hit testing) verification
  is Phase G, separately authorized, NOT_RUN here.
- MySQL conditional rows: NOT_RUN (outside current release blocker set PostgreSQL + Weaviate).
- `docker compose`/Phase E static rows were done by B6/B8; not re-executed by this validator.

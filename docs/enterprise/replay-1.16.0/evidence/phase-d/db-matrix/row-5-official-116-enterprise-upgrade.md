# Phase D Row 5 — Official 1.16 (`7a1c2d9e4b60`) → enterprise 1.16

Validator: `replay-116-b8-phase-d-validator` (2026-08-11)
Evidence root: `docs/enterprise/replay-1.16.0/evidence/phase-d/db-matrix/row-5-official-116-enterprise-upgrade.md`
Scope: VALIDATION_PLAN Phase D "必须运行" row 5 (current production PG version, official 1.16);
decision sheet matrix row 5.

## Result: PASS

Official 1.16.0 baseline DB generated from a temporary git worktree of tag `1.16.0`
(`5c6372d2f76d240265b92fd27c16bc772ffcb107`), then upgraded with the enterprise 1.16
candidate code. Enterprise history branch restored, empty merge executed, B4 applied.
No duplicate table creation.

## Steps and exact commands

| # | Command | Exit | Result |
| --- | --- | ---: | --- |
| 1 | `git worktree add /tmp/replay-116-phase-d/wt-1.16.0 1.16.0` | 0 | worktree at `5c6372d2f76d240265b92fd27c16bc772ffcb107` (tag 1.16.0) |
| 2 | `docker run -d --name dify-b8-phase-d-pg15-r5 --network dify-b8-phase-d-net -p 127.0.0.1:15435:5432 -e POSTGRES_PASSWORD=phased_isolated_pw -e POSTGRES_DB=dify postgres:15-alpine` | 0 | fresh empty PostgreSQL 15.17 |
| 3 | from `/tmp/replay-116-phase-d/wt-1.16.0/api`: `env -u ALL_PROXY -u all_proxy UV_CACHE_DIR=../.uv-cache FLASK_APP=app.py DB_HOST=127.0.0.1 DB_PORT=15435 DB_USERNAME=postgres DB_PASSWORD=phased_isolated_pw DB_DATABASE=dify uv run flask db upgrade` | 0 | official 1.16.0 migrations; head `7a1c2d9e4b60` |
| 4 | from candidate `/api`: same env + `uv run flask db upgrade` | 0 | see migration log |
| 5 | post-upgrade inventory | 0 | see POST |

## Alembic version

| State | alembic_version |
| --- | --- |
| PRE | `7a1c2d9e4b60` (official 1.16 head) |
| POST | `b416e5c4e702` (single enterprise head) |

## Migration log (row 5)

```
Running upgrade 227822d22895 -> c8f3d9d4a1be, add enterprise marketplace assets
Running upgrade a4f2d8c9b731, c8f3d9d4a1be -> f1a14e1e9b41, merge 1.14.2 enterprise migration heads
Running upgrade f1a14e1e9b41, d9e8f7a6b5c4 -> e2f0a9b7c6d5, merge 1.15.0 enterprise migration heads
Running upgrade e2f0a9b7c6d5, 7a1c2d9e4b60 -> a71e16c0de01, merge 1.16.0 enterprise migration heads
Running upgrade a71e16c0de01 -> b416e5c4e702, finalize enterprise marketplace schema
```

Required sequence: enterprise history branch restored (marketplace table created once),
empty merge `a71e16c0de01`, then B4 `b416e5c4e702`. No official revision re-run, no
duplicate table creation, no stamp.

## Post inventory

alembic_version=b416e5c4e702; empty official baseline so all business counts are 0;
marketplace_table_exists=true, marketplace_rows=0, snapshot_table_exists=true.

## Teardown

`docker rm -f dify-b8-phase-d-pg15-r5` and `docker volume rm dify-b8-phase-d-pg15-r5-data`
executed after evidence capture. Worktree `/tmp/replay-116-phase-d/wt-1.16.0` removed
during teardown phase.

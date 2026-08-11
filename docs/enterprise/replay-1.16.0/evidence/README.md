# B8 Validation Evidence Index

Evidence root: `docs/enterprise/replay-1.16.0/evidence/` (B8 Builder 2026-08-11; Phase D
database matrix added by `replay-116-b8-phase-d-validator` 2026-08-11).

Every artifact below is the honest output of a command that actually ran in this
B8 Builder sandbox, or an explicit NOT_RUN record. Missing evidence is NOT_RUN,
never PASS (`B8_MISSING_EVIDENCE_IS_NOT_RUN`). Real database/vector/container/
volume runtime operations and Phase F/G/H runtime gates are separately authorized
(`B8_PHASE_DFGH_NOT_RUN`) and are NOT_RUN here. No secrets, endpoints, keys or
plaintext business identifiers appear in any artifact; targets are SHA-256
redacted or booleans/counts only.

| Phase | Artifact | Status | Command | Exit | SHA-256 prefix | Date |
| --- | --- | --- | --- | ---: | --- | --- |
| A | `phase-a/scope.txt` | PASS | `git rev-parse HEAD` / `git merge-base 1.16.0 HEAD` / `git diff --name-status 1.16.0...HEAD` / `git diff --check` / `git grep -n 'PLATFORM_ADMIN_EMAILS' 1.16.0 -- api web docker` | 0 | `55c35c33c8cd9b61` | 2026-08-11 |
| B | `phase-b/focused-backend.log` | PASS | `uv run --project api pytest -o addopts="" api/tests/unit_tests/services/enterprise/test_enterprise_service.py api/tests/unit_tests/services/test_account_service.py -q` | 0 (158 passed) | `ad34414f7824a498` | 2026-08-11 |
| B | `phase-b/checker-fixture-tests.log` | PASS | `scripts/ci/check-enterprise-vector-indexes-tests.sh` | 0 (47 passed) | `8bfb12414dedfd38` | 2026-08-11 |
| B | `phase-b/notrun.txt` | NOT_RUN | recorded reasons | — | `0e644cf4e94e5adf` | 2026-08-11 |
| C | `phase-c/contracts.log` | NOT_RUN | B4 unique contract generator; read-only reference only | — | `df50af125846f74b` | 2026-08-11 |
| D | `phase-d/migration-graph-tests.log` | PASS | `uv run --project api pytest -o addopts="" api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py -q` | 0 (61 passed) | `66addb709be5970e` | 2026-08-11 |
| D | `phase-d/heads.txt` | PASS | `FLASK_APP=app.py uv run --project api flask db heads` (single head `b416e5c4e702`) | 0 | `b416e5c4e702` | 2026-08-11 |
| D | `phase-d/history.txt` | PASS | `FLASK_APP=app.py uv run --project api flask db history` (204 revisions; key revisions resolve) | 0 | `history.txt` | 2026-08-11 |
| D | `phase-d/db-matrix/row-1-prod-pg15-enterprise-upgrade.md` | PASS | enterprise 1.15 `e2f0a9b7c6d5` (online pg_dump) → `b416e5c4e702` on isolated PG15.17 | 0 | `row-1…` | 2026-08-11 |
| D | `phase-d/db-matrix/row-2-official-115-enterprise-upgrade.md` | PASS | official 1.15 `d9e8f7a6b5c4` (tag 1.15.0 worktree DB) → `b416e5c4e702` | 0 | `row-2…` | 2026-08-11 |
| D | `phase-d/db-matrix/row-3-pg18-empty-enterprise-upgrade.md` | PASS | PG18.4 empty → `b416e5c4e702`; `SELECT uuidv7()` version 7 | 0 | `row-3…` | 2026-08-11 |
| D | `phase-d/db-matrix/row-4-pg18-app-upgrade-enterprise.md` | PASS | PG18.4 enterprise 1.15 restore → `b416e5c4e702`; no re-run of `1c9ba48be8e4` | 0 | `row-4…` | 2026-08-11 |
| D | `phase-d/db-matrix/row-5-official-116-enterprise-upgrade.md` | PASS | official 1.16 `7a1c2d9e4b60` (tag 1.16.0 worktree DB) → `b416e5c4e702` | 0 | `row-5…` | 2026-08-11 |
| D | `phase-d/rollback-drill/row-6-backup-restore-rollback.md` | PASS | backup restore → recovered target = exact 1.15 state `e2f0a9b7c6d5` | 0 | `row-6…` | 2026-08-11 |
| D | `phase-d/db-matrix/README.md` | PASS | matrix summary + cross-row assertions | — | `README.md` | 2026-08-11 |
| E | `phase-e/compose-config.log` | NOT_RUN | `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q` | 1 (no `docker/.env`) | `6720bc5a4179c4d0` | 2026-08-11 |
| Vector | `vector-checker/checker-notrun.txt` | NOT_RUN | `scripts/check-enterprise-vector-indexes.sh` with incomplete environment (no live PostgreSQL/Weaviate) | 0 | `0468b1122fb1f7d1` | 2026-08-11 |
| F | — | NOT_RUN | image build / container identity (Phase F) | — | — | — |
| G | — | NOT_RUN | runtime acceptance (Phase G), incl. secret runtime scan | — | — | — |
| H | — | NOT_RUN | offline `docker load` + `up --pull never` smoke (Phase H) | — | — | — |
| Rollback | `phase-d/rollback-drill/row-6-backup-restore-rollback.md` | PASS | backup/restore rollback drill (DB level; app-level is Phase G) | 0 | `row-6…` | 2026-08-11 |

Notes:

- `docker compose` two-layer static validation is NOT_RUN because `docker/.env` is
  absent and creating it is forbidden; the B6 overlay was already validated and
  merged.
- `flask db heads/history` were re-executed by the Phase D validator (2026-08-11) and are
  now PASS with artifacts `phase-d/heads.txt` / `phase-d/history.txt`.
- The vector checker runs here are NOT_RUN demonstrations (no live
  PostgreSQL/Weaviate); the checker's PASS/FAIL/NOT_RUN logic is proven by the
  fixture suite under `scripts/ci/check-enterprise-vector-indexes-tests.sh`
  (`phase-b/checker-fixture-tests.log`).
- The completeness-check scripts
  (`scripts/ci/check-enterprise-validation-evidence.sh` / `-tests.sh`) are NOT
  created or run: they are not authorized without an explicit coordinator
  allowlist extension (`B8_COMPLETENESS_CHECK`).

# B8 Validation Evidence Index

Evidence root: `docs/enterprise/replay-1.16.0/evidence/` (B8 Builder, 2026-08-11).

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
| D | `phase-d/flask-db.log` | NOT_RUN | `FLASK_APP=app.py uv run --project api flask db heads` / `... history` | 2 | `22206b16b8fceecb` | 2026-08-11 |
| D | `phase-d/db-matrix/notrun.md` | NOT_RUN | real DB upgrade/rollback matrix requires separate authorization | — | `a6ced17c7d33766c` | 2026-08-11 |
| E | `phase-e/compose-config.log` | NOT_RUN | `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q` | 1 (no `docker/.env`) | `6720bc5a4179c4d0` | 2026-08-11 |
| Vector | `vector-checker/checker-notrun.txt` | NOT_RUN | `scripts/check-enterprise-vector-indexes.sh` with incomplete environment (no live PostgreSQL/Weaviate) | 0 | `0468b1122fb1f7d1` | 2026-08-11 |
| F | — | NOT_RUN | image build / container identity (Phase F) | — | — | — |
| G | — | NOT_RUN | runtime acceptance (Phase G), incl. secret runtime scan | — | — | — |
| H | — | NOT_RUN | offline `docker load` + `up --pull never` smoke (Phase H) | — | — | — |
| Rollback | — | NOT_RUN | backup/restore rollback drill | — | — | — |

Notes:

- `docker compose` two-layer static validation is NOT_RUN because `docker/.env` is
  absent and creating it is forbidden; the B6 overlay was already validated and
  merged.
- `flask db heads/history` is NOT_RUN because the Flask app import needs the full
  runtime environment (DB/Redis/config); the merged migration graph tests provide
  the static Phase D evidence.
- The vector checker runs here are NOT_RUN demonstrations (no live
  PostgreSQL/Weaviate); the checker's PASS/FAIL/NOT_RUN logic is proven by the
  fixture suite under `scripts/ci/check-enterprise-vector-indexes-tests.sh`
  (`phase-b/checker-fixture-tests.log`).
- The completeness-check scripts
  (`scripts/ci/check-enterprise-validation-evidence.sh` / `-tests.sh`) are NOT
  created or run: they are not authorized without an explicit coordinator
  allowlist extension (`B8_COMPLETENESS_CHECK`).

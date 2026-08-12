# B8 Phase G Rereview — replay-116-b8-phase-g-rereviewer

Role: rereviewer · Instance: `replay-116-b8-phase-g-rereviewer`
Branch: `ctyun/replay-116-b8-phase-g-rereviewer` · HEAD: `85b445c0e1225d6513d50ef5c7cb1fdea88c12d7`
Reviewed fixer range: `8a2d571d2569df10e2767997fcbda41b96ed6124..85b445c0e1225d6513d50ef5c7cb1fdea88c12d7`
Reviewed commit: `85b445c0e1` "fix: resolve Phase G marketplace uuid and agent knowledge findings"

## 1. Start-state verification

| Check | Result |
| --- | --- |
| `git branch --show-current` | `ctyun/replay-116-b8-phase-g-rereviewer` ✓ |
| `git rev-parse HEAD` | `85b445c0e1225d6513d50ef5c7cb1fdea88c12d7` ✓ |
| `git status --short --branch` | `## ctyun/replay-116-b8-phase-g-rereviewer` (clean) ✓ |

No mismatch; no repair operations (merge/rebase/reset/checkout/cherry-pick) performed.

## 2. Scope verification

```
git diff --name-status 8a2d571..HEAD
M  api/clients/agent_backend/request_builder.py
A  api/migrations/versions/2026_08_12_0000-e7c0a9d2b8f3_align_marketplace_uuid_columns.py
M  api/tests/unit_tests/clients/agent_backend/test_request_builder.py
M  api/tests/unit_tests/core/app/apps/agent_app/test_runtime_request_builder.py
M  api/tests/unit_tests/core/workflow/nodes/agent_v2/test_runtime_request_builder.py
M  api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py
M  api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py
M  docs/enterprise/replay-1.16.0/DECISION_RISK_LEDGER.md
```

- Exactly **8 files**, **+599/-14** (matches contract).
- Diff SHA-256: `d7708375a59f2c10116f1014b8f11602583d625b1e6f0551bcec54c26556b09c` ✓
- `git diff --check` → exit 0 (clean).
- No forbidden file changed: `api/models/model.py` untouched, `b416e5c4e702` migration untouched (both last modified by B4 commit `1fb4e813af`), no `api/core`/`api/services`/`api/controllers`/`docker`/`web`/`dify-agent`/`packages`.

## 3. GPH-01 — Marketplace schema type mismatch → new migration

Verified against `api/migrations/versions/2026_08_12_0000-e7c0a9d2b8f3_align_marketplace_uuid_columns.py`:

| Requirement | Evidence | Status |
| --- | --- | --- |
| Exactly one new migration `e7c0a9d2b8f3` after `b416e5c4e702` | `revision="e7c0a9d2b8f3"`, `down_revision="b416e5c4e702"` (L32–33); only one new revision in range | PASS |
| `b416e5c4e702` and `api/models/model.py` unmodified | Not present in fixer diff | PASS |
| All 12 ID/FK columns converted on PostgreSQL | 6 assets (`id, source_app_id, source_tenant_id, submitter_account_id, reviewer_account_id, published_snapshot_id`) + 6 snapshots (`id, asset_id, source_app_id, source_tenant_id, submitter_account_id, reviewer_account_id`) (L42–57); `ALTER TABLE … ALTER COLUMN … TYPE UUID USING col::uuid` (L59–76) | PASS |
| Data-preserving `USING col::uuid` | L59–61, L76 | PASS |
| No-op on other dialects | `_is_postgresql()` guard in both `upgrade()`/`downgrade()` (L64–70, L79–82); StringUUID→CHAR(36) compatible, documented L16–20 | PASS |
| Downgrade reverses | `TYPE VARCHAR(36) USING col::text` for same 12 columns (L87–90) | PASS |
| Indexes/constraints preserved | PG ALTER TYPE rewrite preserves them; documented L19–20; no drop/create of indexes | PASS |
| Unique head now `e7c0a9d2b8f3` | Graph tests updated: `test_graph_has_exactly_one_final_head_and_it_is_e7c0a9d2b8f3` (`heads == [E7C0]`), `test_head_parent_is_b416e5c4e702`, `test_b416_parent_is_a71e16c0de01`, ancestry converges through A71E/B416E | PASS |
| Docstring + ledger upstream-reconciliation note | Docstring L22–26 ("enterprise fix … no official Dify release … reconcile … drop once official schema is uuid"); ledger §"Phase G 修复（Fixer）" GPH-01 (L415–428) incl. "企业修复 / 上游对账（upstream reconciliation）" | PASS |

Test evidence: `test_upgrade_uses_data_preserving_alter_type_on_postgresql` asserts the exact 12 `ALTER TABLE … TYPE UUID USING col::uuid` statements on a mocked PG bind; `test_upgrade_is_noop_on_non_postgresql` / `test_downgrade_is_noop_on_non_postgresql` assert zero `op.execute` on mysql/sqlite; `test_downgrade_reverses_columns_to_varchar` asserts the 12 reverse statements; `test_docstring_records_upstream_reconciliation`, `test_b416_file_unchanged`.

**GPH-01 CLOSED.**

## 4. GPH-02 — Agent knowledge binding → snapshot alignment

Verified against `api/clients/agent_backend/request_builder.py`:

| Requirement | Evidence | Status |
| --- | --- | --- |
| Inject knowledge layer only when composition has it and snapshot lacks it | `_align_snapshot_to_composition` (L87–128): rebuilds only when `snapshot_names != composition_names`; injects `DIFY_KNOWLEDGE_BASE_LAYER_ID` entry (NEW lifecycle, `runtime_state={"eager_config_fingerprint": None, "eager_results": []}`) only when `name == DIFY_KNOWLEDGE_BASE_LAYER_ID` is in composition but absent from snapshot | PASS |
| Drops stale entries | Entries in snapshot not in composition are not carried into `aligned_layers` (L112–127) | PASS |
| Knowledge-absent path byte-compatible | Matching snapshot returned as the same object (L106–110 `if snapshot_names == list(...): return snapshot`; same-object guard L126); test `test_knowledge_absent_with_matching_snapshot_passes_through_unchanged` asserts `is` identity | PASS |
| Both agent_app and workflow node paths use alignment | `build_for_agent_app` (L524–528) and `build_for_workflow_node` (L760–764) both call `_align_snapshot_to_composition(run_input.session_snapshot, [layer.name for layer in layers])` | PASS |
| Tests cover present/absent cases | New `TestSessionSnapshotKnowledgeAlignment` (clients/request_builder) 5 cases: inject-into-stale, present+matching pass-through, absent+matching pass-through, absent drops stale knowledge layer, workflow-node inject; plus agent_app runtime `test_build_injects_knowledge_layer_into_stale_session_snapshot` / `test_build_knowledge_absent_keeps_matching_snapshot_unchanged` and agent_v2 runtime equivalents | PASS |

No changes to dify-agent/agenton; only API request-building path touched. Existing behavior (no snapshot, matching snapshot) preserved.

**GPH-02 CLOSED.**

## 5. Focused test verification

```
env -u ALL_PROXY -u all_proxy UV_CACHE_DIR=/tmp/uv-cache-b8 PYTHONDONTWRITEBYTECODE=1 uv run --project api pytest \
  -o addopts='' -p no:cacheprovider \
  api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py \
  api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py -q
→ 74 passed, 1 warning ✓ (contract: 74)

env -u ALL_PROXY -u all_proxy UV_CACHE_DIR=/tmp/uv-cache-b8 PYTHONDONTWRITEBYTECODE=1 uv run --project api pytest \
  -o addopts='' -p no:cacheprovider \
  api/tests/unit_tests/core/app/apps/agent_app/test_runtime_request_builder.py \
  api/tests/unit_tests/core/workflow/nodes/agent_v2/test_runtime_request_builder.py \
  api/tests/unit_tests/clients/agent_backend/test_request_builder.py -q
→ 101 passed, 1 warning ✓ (contract: 101)
```

Both counts match the fixer contract exactly. No NOT_RUN (both suites are unit-level, runnable without external systems).

## 6. Stale-head audit: `b416e5c4e702` references

`rg -n 'b416e5c4e702' docs/enterprise/replay-1.16.0` (56 hits) classified.

### 6.1 Live gates — REQUIRED_UPDATE (P3, doc-only)

| ID | Severity | Location | Stale claim | Required change |
| --- | --- | --- | --- | --- |
| B8GPRR-01 | P3 | `CURRENT_STATE.md:30` | "Alembic 最终 head `b416e5c4e702`（唯一 head）" — current-state table | Update to `e7c0a9d2b8f3`（parent `b416e5c4e702`）; `b416e5c4e702` no longer the final head |
| B8GPRR-02 | P3 | `B8_IMPLEMENTATION_PLAN.md:78` | "Alembic 唯一企业 head `b416e5c4e702`（CURRENT_STATE §1…）" — accepted product fact | Update to `e7c0a9d2b8f3`; note Phase G fixer revision appended after `b416e5c4e702` |
| B8GPRR-03 | P3 | `VALIDATION_PLAN.md:14` | Acceptance criterion "Alembic 只有一个最终企业 head `b416e5c4e702`" | Update final head to `e7c0a9d2b8f3`; invariant "single final head" still holds |
| B8GPRR-04 | P3 | `VALIDATION_PLAN.md:87,90,98` | "所有 1.16 智慧广场新增列、索引、约束和数据迁移只在此 revision [b416e5c4e702]" and upgrade-matrix rows' final head `b416e5c4e702` | Add `e7c0a9d2b8f3` to schema-DDL statement; matrix target head becomes `e7c0a9d2b8f3` for future re-runs |

Disposition: all four files are on the rereviewer forbidden path (`CURRENT_STATE.md`, `B8_IMPLEMENTATION_PLAN.md`) or outside the allowed write path (`VALIDATION_PLAN.md`), so the rereviewer records them as required doc updates owned by the coordinator / next phase. Doc-only; no functional, migration, or security impact.

### 6.2 Historical context — may remain

| ID | Severity | Location | Rationale |
| --- | --- | --- | --- |
| B8GPRR-05 | INFO | `B8_IMPLEMENTATION_PLAN.md:61,523` | Recorded plan-time baseline snapshot (5 migration files, head `b416e5c4e702` at B8 plan creation); immutable record of what `ls`/checks showed then |
| B8GPRR-06 | INFO | `CURRENT_STATE.md:202` | Quoted B4 final-review verification transcript ("Alembic unique head = b416e5c4e702") inside the B4 completed-record block |
| B8GPRR-07 | INFO | `ARCHITECT_HANDOFF.md`, `ARCHITECT_REREVIEW.md`, `B2_REVIEW.md`, `B4_IMPLEMENTATION_PLAN.md`, `B4_A_REVIEW.md`, `B4_A_REREVIEW.md`, `B4_FINAL_REVIEW.md`, `B4_FINAL_REREVIEW.md`, `OFFICIAL_RELEASE_ANALYSIS.md`, `PATCH_DECISION_MATRIX.md` | B2/B4 phase plans and review records that described `b416e5c4e702` as B4's final head at that time; phase-complete historical artifacts |
| B8GPRR-08 | INFO | `DECISION_RISK_LEDGER.md:195,207` | B4 decision-record rows; the ledger's live header (L30) was already updated to `e7c0a9d2b8f3` and the new Phase G fixer section documents the revision — ledger is internally consistent |
| B8GPRR-09 | INFO | `evidence/README.md`, `evidence/phase-a/scope.txt`, `evidence/phase-d/**`, `evidence/phase-g/PLAN.md:55`, `evidence/phase-g/README.md:21,45,76` | Immutable run evidence; Phase D/G validations genuinely ended at `b416e5c4e702`. Evidence must not be rewritten retroactively |

## 7. Verdict

**PASS**

- GPH-01 CLOSED: one new migration `e7c0a9d2b8f3` after `b416e5c4e702`; `b416e5c4e702` and `api/models/model.py` untouched; 12 ID/FK columns → `uuid` with data-preserving `USING col::uuid` on PostgreSQL; no-op elsewhere; downgrade reverses; indexes/constraints preserved; unique head `e7c0a9d2b8f3`; docstring + ledger carry the enterprise-fix/upstream-reconciliation note.
- GPH-02 CLOSED: `request_builder` injects the knowledge layer only when composition has it and snapshot lacks it, drops stale entries, keeps the matching-snapshot/knowledge-absent path byte-identical, applied in both `build_for_agent_app` and `build_for_workflow_node`; present/absent cases covered in all three test files.
- Scope exact: 8 files, +599/−14, diff SHA-256 `d7708375…b09c`.
- Tests: 74 + 101 passed (both match contract; NOT_RUN none).
- No new P0/P1/P2; only P3 doc-only findings (B8GPRR-01…04) requiring later updates to `CURRENT_STATE.md`, `B8_IMPLEMENTATION_PLAN.md`, `VALIDATION_PLAN.md`, explicitly dispositioned. INFO findings (B8GPRR-05…09) are historical evidence/records that must remain.
- `git diff --check`: clean (exit 0).

## 8. Command record

| Command | Result |
| --- | --- |
| `git branch --show-current` | `ctyun/replay-116-b8-phase-g-rereviewer` |
| `git rev-parse HEAD` | `85b445c0e1225d6513d50ef5c7cb1fdea88c12d7` |
| `git status --short --branch` | clean |
| `git diff --name-status 8a2d571d..HEAD` | 8 files (1 A, 7 M) |
| `git diff --stat 8a2d571d..HEAD` | 8 files, +599/−14 |
| `git diff --check 8a2d571d..HEAD` | exit 0 |
| `git diff --binary 8a2d571d..HEAD \| sha256sum` | `d7708375a59f2c10116f1014b8f11602583d625b1e6f0551bcec54c26556b09c` |
| pytest migration graph + marketplace | **74 passed** |
| pytest agent_app + agent_v2 + clients request_builder | **101 passed** |
| `rg -n 'b416e5c4e702' docs/enterprise/replay-1.16.0` | 56 hits, audited (§6) |
| `git diff --check` | exit 0 |
| `git status --porcelain=v1` | empty (clean) |

## 9. Authorized-write and commit statement

Only write performed: this file, `docs/enterprise/replay-1.16.0/B8_PHASE_G_REREVIEW.md` (the sole allowed write path). No commit, amend, push, PR, merge, rebase, reset, or cherry-pick occurred, and no external system/database/container/volume was touched. Working tree remains clean at the reviewed HEAD.

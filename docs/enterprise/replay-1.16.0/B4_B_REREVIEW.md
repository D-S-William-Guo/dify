# Dify Enterprise 1.16.0 Replay B4-B 独立复审报告

## 1. 复审元数据

- 角色：独立 B4-B Rereviewer
- 复审分支：`ctyun/replay-116-b4-b-rereviewer`
- 复审 HEAD：`3c538a975afbdca6f23a6bf2a53e6103cb16cd82`
- 被审 B4-B 原始实现 HEAD：`9d899de0db9be693ebaf17a7bc5eb22c5f459722`
- 被审 B4-B 原始实现 parent / B4-A 接受点：`82c4b49591aef06c25687abb9bbb4ca1100ac5ce`
- 工作区：复审前干净（`git status --short` 无输出）
- 独立验证方法：逐项源码审查 + 测试执行 + diff 分析

## 2. 强制 Gate 核验

| 检查项 | 预期 | 实际 | 状态 |
| --- | --- | --- | --- |
| 分支 | `ctyun/replay-116-b4-b-rereviewer` | 一致 | PASS |
| HEAD | `3c538a975afbdca6f23a6bf2a53e6103cb16cd82` | 一致 | PASS |
| 工作区 | 干净 | 干净 | PASS |
| git diff --check | 无 whitespace error | clean | PASS |

## 3. 审查范围

计划与历史审查：

- `docs/enterprise/replay-1.16.0/B4_IMPLEMENTATION_PLAN.md`
- `docs/enterprise/replay-1.16.0/B4_IMPLEMENTATION_PLAN_REVIEW.md`
- `docs/enterprise/replay-1.16.0/B4_IMPLEMENTATION_PLAN_REREVIEW.md`
- `docs/enterprise/replay-1.16.0/B4_B_REVIEW.md`

B4-B 实现及 Fixer：

- `api/services/enterprise_marketplace_service.py`
- `api/services/errors/enterprise_marketplace.py`
- `api/commands/data_migrate.py`
- `api/tests/unit_tests/services/test_enterprise_marketplace_service.py`
- `api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py`

重点 diff：

```
git diff 82c4b49591aef06c25687abb9bbb4ca1100ac5ce..3c538a975afbdca6f23a6bf2a53e6103cb16cd82 --stat
 6 files changed, 3923 insertions(+), 1 deletion(-)

git diff 9d899de0db9be693ebaf17a7bc5eb22c5f459722..3c538a975afbdca6f23a6bf2a53e6103cb16cd82 --stat
 5 files changed, 1675 insertions(+), 428 deletions(-)
```

## 4. 测试结果

```text
ALL_PROXY= all_proxy= no_proxy=* uv run --project api pytest \
  -o addopts='' --override-ini="addopts=" \
  api/tests/unit_tests/services/test_enterprise_marketplace_service.py \
  api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py \
  -q -p no:cacheprovider
```

| 结果 | 数量 |
| --- | --- |
| **PASSED** | 150 |
| **FAILED** | 0 |
| **总计** | 150 |

## 5. 原 Review 11 项 Finding 逐项 Disposition

### P1-1：submit/resubmit TOCTOU → CLOSED

**源码证据**：`api/services/enterprise_marketplace_service.py:148-181`

- L153：`locked_app = self._lock_and_get_source_app(source_app.id, tid)`——替换原 `_lock_source_app`，使用 `scalar(...)` 读取锁定行
- L154-155：锁后重新验证 `locked_app.tenant_id != tid` 和 `locked_app.status != "normal"`
- L159：`source_app=locked_app`——使用锁后 App 对象创建资产
- L162-163：`_query_asset_by_source(source_app.id, for_update=True)`——锁资产
- 锁序为 source App → asset，与 approve/backfill 一致
- 锁后使用 locked_app 的 id/tenant_id；stale 输入对象不影响最终判断

**测试证据**：
- `test_stale_input_deleted_but_db_normal_succeeds`（L780）：证明 stale 输入 deleted → DB normal 仍成功
- `test_locked_app_missing_after_lock`（L827）：锁空结果 → SourceAppNotFound
- `test_locked_app_non_normal_after_lock`（L838）：锁后非normal → SourceAppUnavailable
- `test_submit_uses_locked_app_for_create`（L850）：证明使用 locked_app 而非 stale 输入
- `test_lock_order_source_then_asset`（L863）：验证 lock order source→asset

### P1-2：backfill retry → CLOSED

**源码证据**：`api/services/enterprise_marketplace_service.py:69, 374`

- L69：`_BACKFILL_RETRYABLE_STATES = frozenset({"backfill_pending", "source_missing", "failed"})`
- L374：`if leg not in _BACKFILL_ELIGIBLE_STATUSES or old_state not in _BACKFILL_RETRYABLE_STATES:`——source_missing 和 failed 现在可进入 retry
- pre-lock 和 post-lock（L391, L493, L518）使用一致的 `_BACKFILL_RETRYABLE_STATES`
- apply 模式下 source_missing→ready（L445-451 的 _bf_ready 路径 + 实际 backfill success 路径）和 failed→ready（L396-451）均可恢复
- snapshot pointer/version/row_version 在 apply mode 正确：next_snapshot_version 从 pre_next_v 递增（L424），row_version+1（L448），published_snapshot_id 指向新 snapshot，snapshot_error_code 清为 None（L448）
- 非 eligible 状态（pending/rejected/unlisted/unknown status + none 状态）仍然返回 `ineligible` fail closed ✓

**测试证据**：
- `test_source_missing_retry_succeeds_when_source_restored`（L902）
- `test_failed_retry_succeeds_when_dsl_fixed`（L917）
- `test_approved_none_still_ineligible`（L933）
- `test_apply_retry_from_source_missing_to_ready`（L1357）：验证 snapshot invariants
- `test_apply_retry_from_failed_to_ready`（L1391）：验证 snapshot invariants

### P1-3：CLI 统计与阈值 → CLOSED

**源码证据**：`api/commands/data_migrate.py:248-403`

- L248-249：`_SUCCESS_CODES`/`_SKIPPED_CODES` 分类准确
- L297-300：`attempted`、`succeeded`、`skipped`、`failed` 四个计数器
- L305-307：`consecutive_failures >= error_threshold` 触发停止
- L314-320：`not_found` 明确计入 `failed += 1`、`consecutive_failures += 1`
- L355-363：success 重置 `consecutive_failures = 0`；skipped 重置；else（含所有未知 result_code）计入 failed 并递增 `consecutive_failures`
- L381-390：summary 含 `attempted`、`succeeded`、`skipped`、`failed`、`remaining`、`processed`，一致性验证：`total == attempted + remaining`、`processed == attempted`
- L400-401：manifest SHA-256 基于实际 `written_lines` 字节

**测试证据**：
- `test_not_found_is_failure_in_summary`（L619）：验证 not_found 计入 failed ≥ 1
- `test_business_failure_triggers_threshold`（L502）：validation_failed 触发阈值
- `test_success_resets_consecutive_failures`（L540）：success 重置连续失败
- `test_summary_has_accurate_fields`（L588）：验证 summary 字段完整性

### P1-4：Admin/Public 字段 → CLOSED

**源码证据**：`api/services/enterprise_marketplace_service.py:119-135, 670-714`

- `AssetSnapshotRow`（L124, L134-135）：包含 `source_tenant_id`、`snapshot_error_code`、`review_note`、`reviewed_at`
- `_row_admin`（L670-688）：填入真实值 `a.source_tenant_id`、`a.snapshot_error_code`、`a.review_note`、`a.reviewed_at`
- `_row_public`（L690-714）：四个审计字段全部设为 `None`，另外 `source_app_id=None`、`submitter_account_id=None`、`reviewer_account_id=None` 也继续隐藏

**测试证据**：
- `test_admin_row_includes_real_audit_fields`（L957）：验证 admin 返回四字段真实值
- `test_public_row_hides_all_audit_fields`（L970）：验证 public 全部隐藏

### P1-5：backfill app metadata → CLOSED

**源码证据**：`api/services/enterprise_marketplace_service.py:408-409, 780-789`

- L408-409：backfill 路径调用 `self._validate_app_metadata(app_data)`
- L780-789：`_validate_app_metadata` 静态方法：
  - `isinstance(app_data, dict)` else `ValueError("App must be mapping")`
  - `isinstance(aname, str) and aname.strip()` else `ValueError("App name must be a non-empty string")`
  - `isinstance(amode, str) and amode.strip()` else `ValueError("App mode must be a non-empty string")`
- approve 路径（L233-237）和 backfill 路径使用完全一致的 `_validate_app_metadata`
- backfill 的 `ValueError` 在 L416 的 `except Exception` 中被稳定映射为 `"parse_failed"`

**测试证据**：
- `test_app_is_list_fails_parse`（L996）：list → parse_failed
- `test_app_is_string_fails_parse`（L1010）：str → parse_failed
- `test_app_missing_name_fails_parse`（L1024）：无 name → parse_failed
- `test_app_empty_mode_fails_parse`（L1038）：空 mode → parse_failed
- `test_name_int_rejected`（L1257）：int name → ValueError
- `test_name_bool_rejected`（L1262）：bool name → ValueError
- `test_name_none_rejected`（L1267）：None name → ValueError
- `test_name_whitespace_only_rejected`（L1272）：空白 name → ValueError
- `test_name_int_backfill_maps_to_parse_failed`（L1307）
- `test_mode_bool_backfill_maps_to_parse_failed`（L1321）

### P1-6：Pydantic error → CLOSED

**源码证据**：`api/services/enterprise_marketplace_service.py:848-866`

- L858-859：`except PydanticValidationError: raise MarketplaceError("Invalid dependency")`——approve 路径不再泄漏 PydanticValidationError
- `_extract_and_normalize_dependencies` 是所有路径的唯一依赖解析入口，一致覆盖 approve 和 backfill
- copy 路径使用独立的 `_parse_deps`（L869-877），同样映射 PydanticValidationError → SnapshotIntegrityError

**测试证据**：
- `test_approve_path_rejects_invalid_dependency`（L1086）：断言 `MarketplaceError("Invalid dependency")` 而非 Pydantic
- `test_malformed_dep_in_backfill`（L1072）：backfill → parse_failed

### P1-7：snapshot version invariant → CLOSED

**源码证据**：`api/services/enterprise_marketplace_service.py:317-318, 470-473`

- `copy_asset`（L317-318）：
  - `snap.snapshot_version < 1` → SnapshotIntegrityError
  - `snap.snapshot_version >= asset.next_snapshot_version` → SnapshotIntegrityError
- `_bf_ready_skip`（L470-473）：
  - `snap.snapshot_version < 1` → version_invalid
  - `snap.snapshot_version >= a.next_snapshot_version` → version_invalid
- 两条路径均已验证 asset_id、source IDs、hash、pointer 一致性
- 不合法版本 fail closed

**测试证据**：
- `test_copy_version_zero_raises`（L1104）
- `test_copy_version_at_next_raises`（L1115）
- `test_copy_version_beyond_next_raises`（L1127）
- `test_ready_skip_version_beyond_next_fails`（L1139）
- `test_copy_owner_mismatch_fails`（L1153）
- `test_ready_skip_hash_mismatch_fails`（L1165）

### P2-1：retry parser summary guard → CLOSED

**源码证据**：`api/commands/data_migrate.py:469`

- 原：`if "summary" in obj and "total" in obj: continue`
- 现：`if "total" in obj and "asset_id" not in obj: continue`
- 正确跳过 summary 行（有 `total` 无 `asset_id`），不依赖不存在的 `"summary"` key

**测试证据**：
- `test_retry_manifest_skip_summary_guard`（L649）：验证 summary 行被正确跳过

### P2-2：retryable_codes 不含 "failed" → CLOSED

**源码证据**：`api/commands/data_migrate.py:436-455`

- `_RETRYABLE_RESULT_CODES` 包含 18 个真实结果码：queued、error、source_missing、source_unavailable、export_failed、parse_failed、validation_failed、private_dependency、tenant_mismatch、state_changed、reviewer_missing、source_id_changed、pointer_missing、snapshot_missing、pointer_mismatch、version_invalid、snapshot_source_changed、hash_mismatch
- 不包含 `"failed"`（不存在的通用码）
- final 码（ok、dry_run_ok、ready_skip、ineligible、not_found）不重试
- 未知码（如 "ancient_magic"）不重试（fail closed）

**测试证据**：
- `test_parse_retry_manifest_failed_string_not_retried`（L708）："failed" 不入 retry
- `test_parse_retry_manifest_final_codes_excluded`（L696）：5 个 final code 全部排除
- `test_parse_retry_manifest_unknown_code_not_retried`（L715）：未知码不重试
- `test_parse_retry_manifest_all_retryable`（L675）：18 个 retryable 全部可重试

### P2-3：CLI test 重复 → CLOSED

**源码证据**：

- `api/tests/unit_tests/services/test_enterprise_marketplace_service.py`：仅包含 service-level 测试（状态机、sanitizer、dependencies、copy、public reads、backfill、DSL/hash、TOCTOU、retry、admin/public fields、app validation、version invariant、owner-bound types、metadata validation、apply-mode retry）。无 `TestCLI` 类。
- `api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py`：仅包含 CLI-focused 测试（CLI runner、dry-run、apply、id-file、error threshold、retry manifest、output 0600、JSONL canary、summary）。stdout 通过 JSONL 解析 (`json.loads`) 而非字符串误命中。

两文件分工明确，无显著重复。

### P2-4：owner-bound key int zero → CLOSED

**源码证据**：`api/services/enterprise_marketplace_service.py:827-844`

`_check_owner_bound_key` 使用明确的类型链：
1. `value is None` → return（允许）
2. `isinstance(value, str)` → 空字符串 pass，非空 raise
3. `isinstance(value, list)` → 空 list pass，非空 raise
4. `isinstance(value, dict)` → 空 dict pass，非空 raise
5. 其他（int/bool/tuple/任意非预期类型）→ `raise NonportableResourceReference()`

`int 0`、`bool False` 等不再绕过分类型检查，落入 catch-all `raise`。

**测试证据**：
- `test_int_zero_rejected`（L1185）
- `test_bool_rejected`（L1191）
- `test_tuple_rejected`（L1197）
- `test_none_passes`（L1203）
- `test_empty_string_passes`（L1208）
- `test_empty_list_passes`（L1213）
- `test_empty_dict_passes`（L1218）
- `test_non_empty_str_rejected`（L1223）
- `test_non_empty_list_rejected`（L1229）
- `test_non_empty_dict_rejected`（L1235）

## 6. 额外回归检查

| 检查项 | 状态 | 证据 |
| --- | --- | --- |
| service 只使用显式注入 Session | PASS | `__init__(self, session: Session)`，全局搜索 `db.session` 无结果 |
| snapshot append-only | PASS | 所有 snapshot 创建使用 `session.add()`，无 UPDATE/DELETE |
| raw DSL 与 SHA-256 语义未被破坏 | PASS | DSL 直接由 `export_dsl` 返回字符串原样保存；SHA-256 对 UTF-8 字节计算 |
| backfill 日志不泄漏 DSL/异常文本/token/credential | PASS | JSONL entry 仅含 asset_id/result_code/hash_fingerprint 等稳定字段 |
| CLI 每资产独立 transaction | PASS | `with Session(db.engine, ...) as asset_session` 每资产独立 |
| dry-run 零写入 | PASS | `dry_run=True` 跳过 `session.add()`/状态更新 |
| copy 不查询源 App | PASS | `test_no_source_query` 验证无 `session.get(App, ...)` 调用 |
| 未回退 B4-A schema/model/migration | PASS | diff 范围不含 model/migration 文件 |
| 未修改 controller/contracts/web/docker/B2/B3 文件 | PASS | diff 仅 5 个 allowlist 内文件 |
| File allowlist 符合 | PASS | 仅修改 5 个 Builder 文件 |

## 7. NOT_RUN

- 真实 PostgreSQL 并发/DDL
- Migration
- 容器
- Redis
- Weaviate
- volume
- B8 集成验证

## 8. 最终结论

**PASS**

| 项目 | 值 |
| --- | --- |
| **结论** | **PASS** |
| 复审 HEAD | `3c538a975afbdca6f23a6bf2a53e6103cb16cd82` |
| P0 | **0** |
| P1 | **0**（7 项全部 CLOSED） |
| P2 | **0**（4 项全部 CLOSED） |
| ACCEPTED_KNOWN_LIMITATION | **2**（保持不变：官方 import 内部 commit 残留、DSL 未来字段绕过 sanitizer） |
| 新发现 | **0** |
| 测试结果 | **150 passed, 0 failed** |
| 范围外修改 | **0** |
| git diff --check | **clean** |
| 工作区状态 | **clean** |

### B4_B_ACCEPTED

### B4_C_GATE_RECOMMENDED

## 9. Disposition 摘要

| Finding | 级别 | Disposition |
| --- | --- | --- |
| P1-1 submit/resubmit TOCTOU | P1 | **CLOSED** |
| P1-2 backfill retry blocked | P1 | **CLOSED** |
| P1-3 CLI threshold/summary | P1 | **CLOSED** |
| P1-4 admin/public fields | P1 | **CLOSED** |
| P1-5 backfill app validation | P1 | **CLOSED** |
| P1-6 Pydantic error leak | P1 | **CLOSED** |
| P1-7 snapshot version invariant | P1 | **CLOSED** |
| P2-1 retry summary guard | P2 | **CLOSED** |
| P2-2 retryable dead code | P2 | **CLOSED** |
| P2-3 CLI test duplication | P2 | **CLOSED** |
| P2-4 owner-bound int zero | P2 | **CLOSED** |

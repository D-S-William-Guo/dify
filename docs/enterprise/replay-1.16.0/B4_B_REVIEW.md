# Dify Enterprise 1.16.0 Replay B4-B 独立审查报告（修正版）

## 0. 审查元数据

- 角色：独立 B4-B Reviewer
- 审查分支：`ctyun/replay-116-b4-b-reviewer`
- 角色：独立 B4-B Reviewer
- 审查分支：`ctyun/replay-116-b4-b-reviewer`
- 被审 B4-B 实现 HEAD：`9d899de0db9be693ebaf17a7bc5eb22c5f459722`
- 被审实现 parent / B4-A 接受点：`82c4b49591aef06c25687abb9bbb4ca1100ac5ce`
- 审查范围：`git diff 82c4b495...9d899de0db`
- 报告修订起点：`da3e8a21a7320f7c5bd344638eb368ecc9510545`（amend 后引用此 SHA 可能变化）
- 工作区：审查前干净（`git status --short` 无输出）
- 独立验证方法：逐项源码审查 + mock 行为验证 + 测试执行 + 独立 Python 验证 + 跨路径竞争条件分析

## 1. 强制 Gate 核验

| 检查项 | 预期 | 实际 | 状态 |
| --- | --- | --- | --- |
| 分支 | `ctyun/replay-116-b4-b-reviewer` | 一致 | PASS |
| 被审实现 HEAD | `9d899de0db9be693ebaf17a7bc5eb22c5f459722` | 一致 | PASS |
| 被审实现 parent | `82c4b49591aef06c25687abb9bbb4ca1100ac5ce` | 一致 | PASS |
| 工作区 | 干净 | 干净 | PASS |
| git diff --check | 无 whitespace error | clean | PASS |
| 修改文件数 | 5 个 Builder 文件 | 5 | PASS |

## 2. 最终结论

**CHANGES_REQUIRED**

- **是否接受 B4-B 实现**：不接受
- **是否推荐打开 B4-C 人工门禁**：不允许
- **P0/P1/P2**：**P0=0, P1=7, P2=4**
- **B4_B_NOT_ACCEPTED**：是
- **B4_C_NOT_ALLOWED**：是
- **ACCEPTED_KNOWN_LIMITATION**：2（官方 import 内部 commit 残留、DSL 未来字段绕过 sanitizer）

## 3. P1 Findings

### P1-1：submit/resubmit 使用 `_lock_source_app` 而非 `_lock_and_get_source_app`，导致 TOCTOU 竞争

**文件**：`api/services/enterprise_marketplace_service.py:151, 709-711`
**类型**：数据完整性与安全

```python
# Line 151 (submit_asset):
self._lock_source_app(source_app.id, tid)

# Line 709-711 (_lock_source_app):
def _lock_source_app(self, app_id, tenant_id):
    self._session.execute(select(App.id).where(
        App.id == app_id, App.tenant_id == tenant_id).with_for_update())
```

**证据**：`_lock_source_app` 仅执行 `FOR UPDATE` 行锁，但：
1. 不检查返回行是否存在（使用 `execute()` 而非 `scalar()`，不读取结果）
2. 不返回锁定后的 App 对象
3. 锁后不重新验证 `tenant_id` 和 `status`

**竞争时序**：

```
T1: Controller 读取 source_app（status="normal"）
T2: 管理员删除 App 或修改 status → 行已删除/status 变更
T3: submit_asset 调用 _lock_source_app → FOR UPDATE 锁空结果（不报错）
T4: 使用 T1 的陈旧 source_app 继续创建/修改 marketplace asset
```

`submit_asset`（L149-150）在锁前检查 `source_app.tenant_id` 和 `source_app.status`，但锁后不重新验证。resubmit 路径（L159-177）同样使用锁前 `source_app` 对象。

对比 `approve_asset`（L211-218）使用 `_lock_and_get_source_app`（L703-707）正确锁后验证存在、tenant 和 status。

**影响**：source App 删除后可创建孤立的 marketplace asset；source App 变为非 normal 后仍可通过 submit/resubmit 生成 pending submission。

**评价**：**P1**。

**建议 Fixer**：将 `_lock_source_app` 替换为 `_lock_and_get_source_app`，并在锁后重新验证：
```python
locked = self._lock_and_get_source_app(source_app.id, tid)
if locked.tenant_id != tid: raise SourceAppNotFound()
if locked.status != "normal": raise SourceAppUnavailable()
```

---

### P1-2：`failed`/`source_missing` 状态的 retry 被永久阻塞

**文件**：`api/services/enterprise_marketplace_service.py:67-68, 367`
**类型**：功能缺陷

```python
_BACKFILL_ELIGIBLE_STATUSES = frozenset({"approved"})
_BACKFILL_ELIGIBLE_STATES = frozenset({"backfill_pending"})
```

**证据**：`backfill_legacy_snapshot`（L367）在进入任何 retry 逻辑前检查 `old_state not in _BACKFILL_ELIGIBLE_STATES`。一旦资产在第一次 backfill 尝试后进入 `snapshot_state=source_missing` 或 `snapshot_state=failed`，`_BACKFILL_ELIGIBLE_STATES` 不包含这些状态，后续调用立即返回 `result_code="ineligible"`，不会再次尝试 export/validation。

**计划要求**：计划 §12.6 明确要求 "failed/pending 使用 manifest/DB 最新 row_version 按 ID retry"。§12.5 要求 "apply 的成功、source_missing、failed 状态更新都递增 row_version"，明确预期 `failed`/`source_missing` 是可在后续 retry 中重试的状态。

**影响**：一旦 backfill 因为 source 临时不可用或 DSL 验证失败，即使 source 恢复或 DSL 被修复，asset 也无法再次回填。永久 stuck 在 `source_missing`/`failed` 状态。

**评价**：**P1**。

**建议 Fixer**：将 `_BACKFILL_ELIGIBLE_STATES` 扩展为包含 `frozenset({"backfill_pending", "source_missing", "failed"})`，或改为 `frozenset({"backfill_pending"})` + 单独 `_BACKFILL_RETRYABLE_STATES`。在锁后重新验证 eligibility 时对 retryable 状态也允许进入 export/validation 流程。

---

### P1-3：CLI `--error-threshold` 对业务失败不生效，summary `failed` 失真

**文件**：`api/commands/data_migrate.py:294-354`
**类型**：监控/运维缺陷

**证据**：

`consecutive_errors`（L295）只在 `except Exception` 块（L345）中递增。当 `backfill_legacy_snapshot` 返回业务失败结果码（如 `"validation_failed"`、`"export_failed"`、`"source_missing"`、`"source_unavailable"`）时，不抛出异常，代码走正常路径（L318-344）：
```python
consecutive_errors = 0  # Line 343 — 重置
processed += 1           # Line 344 — 计数为已处理
```

`summary.failed`（L360）定义为 `total_assets - processed`。因此当所有资产都返回业务失败码时，`processed = total_assets`，`failed = 0`——完全失真。

**影响**：
1. `--error-threshold` 无法被业务失败触发——即使连续 100 个 `validation_failed` 也不会中断
2. summary 报告的 `failed: 0` 掩盖了实际上全部失败的事实
3. `marketplace.backfill_completed` 的 `failed` 字段同样失真

**评价**：**P1**。

**建议 Fixer**：定义 success/skipped/failure result code 集合，not_found 归为 failure：

- **Success**：`ok`、`dry_run_ok`
- **Skipped/neutral**：`ready_skip`、`ineligible`
- **Failure**：`not_found`、`error`、`source_missing`、`source_unavailable`、`validation_failed`、`export_failed`、`parse_failed`、`private_dependency`、`tenant_mismatch`、`state_changed`、`reviewer_missing`、`source_id_changed`、`pointer_missing`、`snapshot_missing`、`pointer_mismatch`、`version_invalid`、`snapshot_source_changed`、`hash_mismatch`，以及其他所有未被识别的非成功 result code（fail closed）。

据此分别统计 `attempted`（尝试处理的资产数）、`succeeded`（成功数）、`skipped`（跳过数）、`failed`（失败数）、`remaining`（未处理数）。当前 summary 的 `"failed"` 字段必须改名或废弃。

`consecutive_errors` 改为基于连续 `_FAILURE_CODES` 返回 + `except Exception`，错误阈值也基于 `consecutive_failures` 而非异常数。

---

### P1-4：admin/my service 返回值缺少 B4-C 必需字段

**文件**：`api/services/enterprise_marketplace_service.py:118-135, 661-675`
**类型**：接口缺陷

**证据**：`AssetSnapshotRow` NamedTuple（L118-131）和 `_row_admin`（L661-675）未包含以下四个 Model 已有字段：

| 字段 | Model 存在 | AssetSnapshotRow 字段 | _row_admin 设置 |
| --- | --- | --- | --- |
| `source_tenant_id` | ✓ | **缺失** | 未设置 |
| `snapshot_error_code` | ✓ | **缺失** | 未设置 |
| `review_note` | ✓ | **缺失** | 未设置 |
| `reviewed_at` | ✓ | **缺失** | 未设置 |

**计划要求**（§7）：admin/my response 必须返回 "moderation/publication/snapshot state、row version、审计 ID 和失败分类"。审计 ID 包括 `source_tenant_id`、`source_app_id`、`submitter_account_id`、`reviewer_account_id`。失败分类即 `snapshot_error_code`。

**影响**：B4-C Controller 禁止直接查询 SQLAlchemy。当前 service 返回值不足以构造要求的 marketplace response DTO。缺少 `source_tenant_id` 和 `snapshot_error_code` 是计划明确要求的字段；`review_note` 和 `reviewed_at` 是 admin 管理的合理必需字段。

**评价**：**P1**。

**建议 Fixer**：

1. `AssetSnapshotRow` 增加 `source_tenant_id`、`snapshot_error_code`、`review_note`、`reviewed_at` 字段
2. `_row_admin` 填入真实值（`a.source_tenant_id`、`a.snapshot_error_code`、`a.review_note`、`a.reviewed_at`）
3. `_row_public` 对这四个字段明确返回 `None`——public response 不得泄漏审计与 moderation 信息
4. 增加 admin/my 返回与 public 隐藏的对应测试

---

### P1-5：backfill 路径缺少 `app` 字段类型检查和 name/mode 空值校验

**文件**：`api/services/enterprise_marketplace_service.py:415-417`
**类型**：健壮性缺陷

**证据**：backfill 成功路径（L415-417）：
```python
app_data = data.get("app", {})
aname, amode = app_data.get("name", ""), app_data.get("mode", "")
```

对比 approve 路径（L229-232）：
```python
app_data = data.get("app", {})
if not isinstance(app_data, dict): raise MarketplaceError("App must be mapping")
aname, amode = app_data.get("name", ""), app_data.get("mode", "")
if not aname or not amode: raise MarketplaceError("App name/mode required")
```

backfill 缺少：
1. `isinstance(app_data, dict)` 检查——若 `data["app"]` 是 `list`/`str`，`app_data.get(...)` 抛出 `AttributeError`
2. `if not aname or not amode` 检查——可能生成 `app_name=""`/`app_mode=""` 的空 snapshot

**影响**：
- 若 `data["app"]` 非 dict（如 list/str）：`AttributeError` 不在 `try/except Exception` 范围内（L394-408 已结束），propagate 到 CLI 的 `except Exception`，记录为泛化 `"error"` 而非稳定的 `"parse_failed"`
- 若 name/mode 为空字符串：snapshot 写入空值。空字符串不违反数据库 NOT NULL，但违反计划 §5.2 要求 app_name/app_mode 从 DSL 冻结且语义保障；可能发布不可用的空 app_name/app_mode snapshot

**要求**：app 非 mapping 和 name/mode 空值的检查都必须进入稳定的 parse/validation 分类，不得产生未分类 AttributeError。

**评价**：**P1**。

**建议 Fixer**：在 L416-417 之前增加与 approve 路径相同的检查。

---

### P1-6：approve_asset 中 `_extract_and_normalize_dependencies` 未处理 `PydanticValidationError`

**文件**：`api/services/enterprise_marketplace_service.py:226, 816-830`
**类型**：错误泄漏

**证据**：`approve_asset`（L226）调用 `_extract_and_normalize_dependencies(data)`（L816-830）：
```python
@staticmethod
def _extract_and_normalize_dependencies(data):
    ...
    for d in rd:
        ...
        pd = PluginDependency.model_validate(d)  # 可能抛 PydanticValidationError
        ...
```

当 `d` 缺少 `PluginDependency` 必填字段时，`model_validate` 抛出 `PydanticValidationError`（继承 `Exception`，非 `MarketplaceError`）。在 approve 路径中，该调用不在任何 `try/except` 块内，异常会 propagate 到 Controller。

对比：
- backfill 路径（L400）在同一 `try/except Exception` 块内，被捕获为稳定的 `"parse_failed"` ✓
- copy 路径（L313）使用 `_parse_deps`（L833-841），其中显式 `except PydanticValidationError: raise SnapshotIntegrityError()` ✓

**影响**：approve 路径可能向 Controller 泄漏 `PydanticValidationError` 内部细节，而非稳定的 `MarketplaceError`。

**评价**：**P1**。

**建议 Fixer**：在 `_extract_and_normalize_dependencies` 中或 `approve_asset` 的调用处捕获 `PydanticValidationError` 并映射为 `MarketplaceError("Invalid dependency")`。

---

### P1-7：copy_asset 和 _bf_ready_skip 缺少 snapshot_version invariant

**文件**：`api/services/enterprise_marketplace_service.py:451-473, 299-312`
**类型**：完整性校验

**证据**：`copy_asset`（L306-311）验证了 `snap.asset_id`、hash、source IDs，但未验证 `snap.snapshot_version >= 1`。对比 `_bf_ready_skip`（L463-464）验证了 `snap.snapshot_version < 1` 返回 `"version_invalid"`。

计划 §9 copy 规则要求 "重新计算 SHA-256 并核对 asset/version/source IDs"。

`_bf_ready_skip` 验证了 version >= 1（L463），但未验证 `snap.snapshot_version < asset.next_snapshot_version`。

**影响**：copy 路径在指针完整性检查中缺少 snapshot version 维度，理论上可能使用 version=0（尚未正式分配）的 snapshot。

**评价**：**P1**。

**建议 Fixer**：copy 和 ready skip 都必须验证：
- `snapshot_version >= 1`
- `snapshot_version < asset.next_snapshot_version`
- `snapshot.asset_id == asset.id`（copy 已有，ready skip 已有）
- `snapshot.source_app_id/source_tenant_id` 与 asset 一致（copy 已有，ready skip 已有）
- pointer/hash 一致（copy 已有，ready skip 已有）

缺少上述任一项检查即为失败。`_bf_ready_skip` 的 L463 检查 `snap.snapshot_version < 1` 已存在，需在其基础上增加 `snap.snapshot_version >= asset.next_snapshot_version` 的校验。

---

## 4. P2 Findings（保留自原报告）

### P2-1：`_parse_retry_manifest` summary 跳过 guard 是误导性死代码

**文件**：`api/commands/data_migrate.py:425`

```python
if "summary" in obj and "total" in obj:
    continue
```

实际 summary 条目（L356-367）不含 `"summary"` key，`"summary" in obj` 永远为 False。summary 被正确跳过仅因后续 `if not aid: continue`。Test `test_retry_manifest` 的 `{"total": 2}` 同样无 `"summary"`，测试通过是巧合。

**建议**：改为 `if "total" in obj and "asset_id" not in obj: continue`。

### P2-2：retryable_codes 包含未使用的 `"failed"`

**文件**：`api/commands/data_migrate.py:407`

`"failed"` 不在 backfill service 产出的任何 result_code 中（实际产出 `"error"` 和各类具体原因码）。无害但混淆。

### P2-3：两个测试文件的 TestCLI 显著重复

约 60% 的 CLI test（12 个）在 `test_enterprise_marketplace_service.py` 和 `test_marketplace_snapshot_backfill.py` 中重复，mock 设置高度相似。非功能缺陷但维护负担。

### P2-4：`_check_owner_bound_key` 条件对 int zero 不生效

**文件**：`api/services/enterprise_marketplace_service.py:891-896`

Python `and`/`or` 优先级导致 `value=0`（int zero）绕过 `NonportableResourceReference`。理论缺陷（real owner-bound IDs 非零）。

**建议**：不得简单改为 `if value:`（整数 0 仍会漏过）。应使用明确的类型规则：
- `None`、空字符串、空 list、空 dict 视为空，不拒绝
- 非空字符串、非空 list、非空 dict 一律拒绝
- `int`/`bool` 等非预期类型，无论值是否为 `0`/`False`，均 fail closed 拒绝
- 其他未知容器/标量类型也 fail closed

---

## 5. ACCEPTED_KNOWN_LIMITATION 验证

### KNOWN-LIMITATION-1：官方 import 内部 commit 后可能 FAILED

**状态**：诚实保留。`copy_asset`（L322-354）在 import 前完成所有 B4 自有校验（snapshot/hash/pointer/dependency/tenant），零 DB 写入。import 后无 B4 自有校验。PENDING/FAILED 映射为 CopyPendingUnsupported/CopyFailed。预分配 import_app_id 供 reconciliation。

### KNOWN-LIMITATION-2：DSL export 未来字段可能绕过已知 sanitizer

**状态**：诚实保留。sanitizer 使用递归遍历 + key pattern substring 匹配，未识别字段 fail closed。

---

## 6. 已验证通过的关键条目（无问题）

- 构造函数注入显式 Session，无 `db.session` ✓
- approve 锁序：非锁 asset → source App(FOR UPDATE) → asset(FOR UPDATE) → 重新验证 ✓
- reject/unlist 仅锁 asset ✓
- backfill 锁序：非锁 asset → source App(FOR UPDATE) → asset(FOR UPDATE) ✓
- CLI apply 每资产独立 session/commit，一个失败不污染后续 ✓
- dry-run 不 commit ✓
- `export_dsl(include_secret=False)` 原字符串逐字保存 ✓
- SHA-256 对 UTF-8 原始字节计算，不重新 dump ✓
- snapshot append-only ✓
- sanitizer fail-closed：secret value_type、credential/token/API key/private key ✓
- sanitizer 拒绝 dataset_ids/file_id/account_id/webhook_url/LINK icon/private dependency ✓
- canary 不进入 error message、日志、JSONL ✓
- public list 使用 inner join（`published_snapshot_id == snapshot.id`），`snapshot.asset_id == asset.id` 额外指针校验 ✓
- public 不暴露 submitter/reviewer/source App ID ✓
- frozen_at 排序不访问不存在的 updated_at ✓
- copy 不查询 source App ✓
- copy 预分配 import_app_id ✓
- COMPLETED/PENDING/FAILED/COMPLETED_WITH_WARNINGS 映射正确 ✓
- copy warning 只返回稳定 code ✓
- 不泄漏 Import.error ✓
- JSONL 无 DSL/token/credential ✓
- CLI JSONL 0600 + 完整 SHA-256 ✓
- 首次 submit row_version=0→1 ✓
- duplicate pending → SubmissionAlreadyPending ✓
- reject/unlist/approve row_version+1 ✓
- stale row_version → StaleAssetVersion ✓

---

## 7. 实际运行测试结果

```text
ALL_PROXY= all_proxy= PYTHONPATH="$PWD/api" \
/home/ctyun/BigData/.system-data/app-data/claude-squad/worktrees/ctyun/replay-116-b4-a-builder_18c60cb1a64fcac0/api/.venv/bin/pytest \
-o addopts='' \
api/tests/unit_tests/services/test_enterprise_marketplace_service.py \
api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py \
-q -p no:cacheprovider
```

| 结果 | 数量 |
| --- | --- |
| **PASSED** | 97 |
| **FAILED** | 0 |
| **总计** | 97 |

测试全绿不矛盾——7 个 P1 是逻辑/竞争/接口缺陷，当前 mock 测试无法覆盖（TOCTOU、retry 状态循环、聚合失真、字段缺失、非 dict `app`、Pydantic 未捕获、version 校验缺失）。

---

## 8. File Allowlist 符合性

仅修改 5 个 Builder 文件。B4-A model/migration、B2/B3、controller/init/contracts/Web/Docker 未被修改。

---

## 9. Fixer Allowlist

Fixer 仅可修改以下文件。不得修改 B4-A model/migration、errors、controller、contracts 或其他文件：

```
api/services/enterprise_marketplace_service.py
api/commands/data_migrate.py
api/tests/unit_tests/services/test_enterprise_marketplace_service.py
api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py
```

### 逐项 Fixer 范围

| P1 | Fixer 范围 |
| --- | --- |
| P1-1 submit/resubmit TOCTOU | 替换 `_lock_source_app`→`_lock_and_get_source_app`，锁后重验 tenant/status |
| P1-2 retry blocked | 扩展 `_BACKFILL_ELIGIBLE_STATES` 含 `source_missing`/`failed` |
| P1-3 CLI threshold/summary | 定义 success/neutral/failure code 集，重算 failed/processed/consecutive |
| P1-4 admin 字段不足 | AssetSnapshotRow 加 4 字段，_row_admin 填入，_row_public 返回 None |
| P1-5 backfill app 校验 | 加 `isinstance(app_data, dict)` 和 name/mode 空值检查，必须是稳定分类错误 |
| P1-6 Pydantic 泄漏 | approve 路径映射 PydanticValidationError→MarketplaceError |
| P1-7 snapshot version | copy + _bf_ready_skip 验证 version>=1、version<next、asset_id/IDs/hash/pointer 一致 |

**Fixer 必须同时运行并通过**：
```text
pytest api/tests/unit_tests/services/test_enterprise_marketplace_service.py
pytest api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py
```

---

## 10. 审查 Disposition 摘要

| 项目 | 值 |
| --- | --- |
| **结论** | **CHANGES_REQUIRED** |
| **B4_B_NOT_ACCEPTED** | 是 |
| **B4_C_NOT_ALLOWED** | 是 |
| P0 | 0 |
| P1 | **7**（TOCTOU、retry blocked、CLI threshold、response 字段、backfill app 校验、Pydantic 泄漏、version invariant） |
| P2 | 4（guard 死代码、retryable dead code、CLI test 重复、owner-bound int zero） |
| ACCEPTED_KNOWN_LIMITATION | 2 |
| 测试结果 | **97 passed, 0 failed** |
| NOT_RUN | 真实 PostgreSQL 并发/DDL、迁移、容器、Redis、Weaviate、volume（属 B8） |
| 被审实现 HEAD | `9d899de0db9be693ebaf17a7bc5eb22c5f459722` |
| 被审实现 parent | `82c4b49591aef06c25687abb9bbb4ca1100ac5ce` |
| 工作区状态 | 干净 |
| 未 push | 是 |

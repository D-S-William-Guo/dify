# Dify Enterprise 1.16.0 Replay B4-A 独立审查报告

## 0. 审查元数据

- 角色：独立 B4-A Reviewer
- 审查分支：`ctyun/replay-116-b4-a-reviewer`
- 审查 HEAD：`1fb4e813af568ca192917210a3f6be98ababa729`
- 工作区：审查前干净（`git status --short` 无输出）
- B4-A 实现起点：`b62a304b46073a6c79e8d87a5672502c2608cdad`（Rereview PASS commit）
- 独立验证方法：源码审查 + Alembic ScriptDirectory 真实 graph 解析 + 测试执行

## 1. 强制起点核验

| 检查项 | 预期 | 实际 | 状态 |
| --- | --- | --- | --- |
| 分支 | `ctyun/replay-116-b4-a-reviewer` | 一致 | PASS |
| HEAD | `1fb4e813af568ca192917210a3f6be98ababa729` | 一致 | PASS |
| 工作区 | 干净 | 干净 | PASS |
| HEAD == 预期 SHA | `1fb4e813af...` | 匹配 | PASS |

## 2. 最终结论

**CHANGES_REQUIRED**

- **是否接受 B4-A schema/model/migration 实现**：接受（审查本身 PASS）
- **B4-A 阶段是否整体闭环**：否（陈旧 B2 head 测试造成确定性的 1 failure）
- **是否允许启动 B4-B**：不允许。必须先完成有限 B4-A Fixer，并复审通过
- **P0/P1/P2**：**P0=0、P1=1、P2=1**
- **ACCEPTED_KNOWN_LIMITATION**：0

## 3. 审查范围与方法

审查严格对照 B4 Implementation Plan §3（复审）和 B4-A 规范（§5、§11、§16 B4-A），独立核验了以下全部三层：

1. **Alembic graph 拓扑**：真实 `ScriptDirectory` 解析，不依赖文件内容正则匹配
2. **Model 一致性**：Table metadata（列集、类型、nullable、default、index、constraint），不依赖 docstring 自我证明
3. **Migration upgrade/downgrade 安全性**：AST 检查 + in-memory SQLite 执行 + mock add_column capture
4. **测试有效性**：逐项检查是否存在宽松断言、吞异常、源码字符串自证、或重复实现被测 SQL

### 3.1 审查证据清单

| 证据类型 | 关键文件 | 行参考 |
| --- | --- | --- |
| Alembic graph | `scripts.py` head resolution | test result §6 |
| Model table metadata | `model.py` | L2775–L2950 |
| Migration DDL | `2026_07_21_1400-b416e5c4e702_*` | L56–L289 |
| CASE SQL | module constant `_ASSET_INIT_SQL` | L28–L53 |
| Model tests | `test_enterprise_marketplace.py` | 57 tests |
| Migration tests | `test_enterprise_1_16_marketplace_migration.py` | 45 tests |
| B2 graph test | `test_enterprise_1_16_migration_graph.py` | 15 pass / 1 fail (see §7) |

## 4. 逐项 Findings

### 4.1 Alembic Graph

#### F-1：revision=b416e5c4e702, down_revision=a71e16c0de01 — PASS

**证据**：
- 文件 `2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py`
  - L23：`revision = "b416e5c4e702"`
  - L24：`down_revision = "a71e16c0de01"`
- 测试 `test_revision_value`（PASS）、`test_down_revision_value`（PASS）
- alembic graph 确认 parent 为 a71e16c0de01

#### F-2：唯一 head 为 b416e5c4e702 — PASS

**证据**：Alembic ScriptDirectory.get_heads() 返回 `["b416e5c4e702"]`，测试 `test_unique_head_is_b416e5c4e702`（PASS）。不存在双 head。

#### F-3：B2 四个历史 migration 未被修改 — PASS

**证据**：`git diff b62a304b46..HEAD` 显示 `c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5`、`a71e16c0de01` 四个文件 zero diff。B4-A 的 5 文件 diff 不包含任何 B2 migration。

#### F-4：B2 merge a71e16c0de01 仍为空 merge — PASS

**证据**：文件内容 L15-L20，`upgrade()` 和 `downgrade()` 均为 `pass`，无 sa/op import。测试 `test_b2_merge_upgrade_is_pass_only`（PASS）。

### 4.2 Model 与 Migration 一致性

#### F-5：主表保留旧 16 列并新增 6 列 — PASS

**证据**：测试 `test_all_legacy_columns_present` 验证了 `id, source_tenant_id, source_app_id, submitter_account_id, reviewer_account_id, status, title, description, category, tags, scenario, allow_show_workspace_name, review_note, created_at, updated_at, reviewed_at` 共 16 个旧列全部存在。测试 `test_all_b4_columns_present` 验证了 `publication_status, published_snapshot_id, next_snapshot_version, row_version, snapshot_state, snapshot_error_code` 共 6 个新列全部存在。

#### F-6：snapshot 表包含计划规定的 25 列 — PASS

**证据**：模型列集（`model.py` L2936–L2950）含 25 列：`id, asset_id, snapshot_version, dsl_content, dsl_version, content_sha256, frozen_at, source_app_id, source_tenant_id, source_tenant_name, submitter_account_id, reviewer_account_id, title, description, category, tags, scenario, allow_show_workspace_name, app_name, app_description, app_mode, app_icon_type, app_icon, app_icon_background, dependencies`。

测试 `test_all_required_columns_present` 验证全部 25 列存在。

#### F-7：类型、nullable、Python default、server_default — PASS

| 检查项 | 证据 |
| --- | --- |
| content_sha256 为 VARCHAR(64) 非 CHAR(64) | `model.py` L2943 使用 `sa.VARCHAR(64)`；migration L65 使用 `sa.VARCHAR(length=64)` |
| tags 为 `list[str]` | `model.py` L2803 声明 `Mapped[list[str]]`；测试验证 type hints 为 `list[str]` |
| dependencies 为 `list[dict[str, Any]]` | `model.py` L2947 声明 `Mapped[list[dict[str, Any]]]`；测试验证 |
| publication_status NOT NULL, server_default='unpublished' | model test: `test_publication_status_not_nullable`, `test_publication_status_server_default` PASS |
| published_snapshot_id NULLABLE, no server_default | model test: `test_published_snapshot_id_nullable` PASS; migration test: `test_published_snapshot_id_no_server_default` PASS |
| snapshot_error_code NULLABLE, no server_default | model test: `test_snapshot_error_code_nullable` PASS; migration test: `test_snapshot_error_code_no_server_default` PASS |
| snapshot_state NOT NULL, server_default='none' | model tests PASS |

#### F-8：索引 — PASS

**evidence**：

- B2 旧索引保留：`enterprise_marketplace_asset_source_tenant_id_idx(source_tenant_id)`、`enterprise_marketplace_asset_status_idx(status, updated_at)` — 模型 `__table_args__` L2794-L2795
- B4 新索引：
  - `enterprise_marketplace_asset_publication_idx(publication_status, updated_at, id)` — model L2796-L2801, migration L206-L211; 测试 `test_publication_idx_name_and_columns` PASS
  - `enterprise_marketplace_asset_submitter_idx(source_tenant_id, submitter_account_id, updated_at, id)` — model L2802-L2807, migration L212-L217; 测试 `test_submitter_idx_name_and_columns` PASS
  - `enterprise_marketplace_snapshot_asset_frozen_idx(asset_id, frozen_at, id)` — model L2921, migration L101-L106; 测试 PASS
  - `enterprise_marketplace_snapshot_sha256_idx(content_sha256)` — model L2923, migration L107-L112; 测试 PASS

#### F-9：唯一约束 — PASS

**证据**：
- `unique_enterprise_marketplace_source_app(source_app_id)` — B2 保留，model test 验证
- `enterprise_marketplace_snapshot_asset_version_uq(asset_id, snapshot_version)` — B4 新增，测试 `test_asset_version_unique_name_and_columns` PASS

#### F-10：CHECK 名称及列集合一致 — PASS

**证据**：

| CHECK 名 | 列/表达式 | Model (line) | Migration (line) | Test |
| --- | --- | --- | --- | --- |
| `ck_marketplace_asset_publication_status` | `publication_status IN ('unpublished','published','unlisted')` | L2809-L2810 | L189-L193 | PASS |
| `ck_marketplace_asset_snapshot_state` | `snapshot_state IN ('none','ready','backfill_pending','source_missing','failed')` | L2811-L2812 | L194-L198 | PASS |
| `ck_marketplace_asset_next_snapshot_version` | `next_snapshot_version >= 1` | L2813-L2814 | L199-L203 | PASS |
| `ck_marketplace_snapshot_version` | `snapshot_version >= 1` | L2925-L2926 | L92-L95 | PASS |
| `ck_marketplace_snapshot_content_sha256_length` | `char_length(content_sha256) = 64` | L2929-L2930 | L96-L99 | PASS |

#### F-11：无物理 FK、无 cascade delete、无 legacy status CHECK — PASS

**证据**：
- 模型测试 `test_no_physical_fks`、`test_published_snapshot_id_no_fk`、`test_asset_id_no_fk` 全部 PASS
- 模型测试 `test_no_legacy_status_check` PASS：遍历所有 CheckConstraint，确保任何含 `status` 的非 B4 CHECK 不存在
- Migration 测试 `test_no_legacy_status_check` PASS：对 AST `create_check_constraint` 调用做字符串分析
- 模型无任何 `ForeignKey` 或 `ForeignKeyConstraint` 声明
- 无 cascade delete 配置

### 4.3 Upgrade 安全

#### F-12：操作顺序正确 — PASS

**证据**：migration L56-L217，顺序确认为：
1. L58-L112：`op.create_table("enterprise_marketplace_asset_snapshots")` + 创建索引
2. L116-L151：`op.add_column(...)` 6 次，全部 `nullable=True, server_default=...`
3. L168：`op.execute(sa.text(_ASSET_INIT_SQL))` — 确定性 CASE 初始化
4. L171-L186：`op.alter_column(... nullable=False)` 对 4 个 B4 列设置 NOT NULL
5. L189-L203：`op.create_check_constraint(...)` 3 个 CHECK
6. L206-L217：`op.create_index(...)` 2 个 B4 索引

顺序完全符合计划 §11.1：先建表、再加 nullable 列、再 CASE 初始化、再 NOT NULL/CHECK/index。

#### F-13：CASE 初始化映射正确 — PASS

**证据**：`_ASSET_INIT_SQL` (L28-L53)：

| 旧 status | publication_status | published_snapshot_id | next_snapshot_version | row_version | snapshot_state | snapshot_error_code |
| --- | --- | --- | --- | --- | --- | --- |
| `approved` | `unpublished` | NULL | 1 | 0 | `backfill_pending` | NULL |
| `unlisted` | `unlisted` | NULL | 1 | 0 | `none` | NULL |
| `pending` | `unpublished` | NULL | 1 | 0 | `none` | NULL |
| `rejected` | `unpublished` | NULL | 1 | 0 | `none` | NULL |
| 未知 | `unpublished` | NULL | 1 | 0 | `failed` | `legacy_status_unknown` |

In-memory SQLite 测试 `TestUnknownLegacyStatusInMemory` 已验证全部 5 种映射。
原 status、source IDs、metadata、reviewer、行数、三个时间戳不修改 — 测试 `test_unknown_status_preserved_and_mapped` 验证 `status` 保持原值、`source_app_id`/`source_tenant_id`/`created_at`/`updated_at`/`reviewed_at` 不变。

#### F-14：未知 status 处理正确 — PASS

**证据**：ELSE 分支映射为 `publication_status='unpublished'`（不公开）、`snapshot_state='failed'`、`snapshot_error_code='legacy_status_unknown'`。不 UPDATE 原 status 列。测试 `test_unknown_status_preserved_and_mapped` 以 `status='ancient_status'` 验证。

#### F-15：不修改 source IDs、metadata、reviewer、行数和三个旧时间戳 — PASS

**证据**：`_ASSET_INIT_SQL` 只 SET 6 个 B4 新列，不触及 `source_app_id`、`source_tenant_id`、`submitter_account_id`、`reviewer_account_id`、`title`、`description`、`category`、`tags`、`scenario`、`allow_show_workspace_name`、`review_note`、`created_at`、`updated_at`、`reviewed_at`。测试验证 `source_app_id`、`source_tenant_id`、`created_at`、`updated_at`、`reviewed_at` 保持不变。

#### F-16：PostgreSQL/MySQL 方言兼容性 — PASS（对 PostgreSQL 安全）

**证据**：
- 所有类型对 PostgreSQL 兼容：`sa.VARCHAR`、`sa.Integer`、`sa.Boolean`、`sa.Text`、`sa.DateTime`、`sa.JSON`、`sa.String`
- CHECK 约束 PostgreSQL 原生支持
- MySQL 不在本轮发布阻断范围（计划 §17.2 明确）

#### F-17：migration 不导入 service、不访问外部系统 — PASS

**证据**：migration 文件仅 import `sqlalchemy as sa`、`alembic.op`。测试 `test_no_import_service_or_network` 对 AST 遍历验证不导入 `services`、`redis`、`network`、`httpx`、`requests`、`plugin`。测试 `test_no_business_service_imports` 验证不导入 `controller`、`app_dsl`、`export`、`import_app`、`workflow_service`、`dependencies_analysis`。全部 PASS。

### 4.4 Downgrade 安全

#### F-18：snapshot 非空或 published pointer 非空时必须拒绝 — PASS

**证据**：migration L228-L243：
```python
snapshot_count = conn.scalar(sa.text("SELECT COUNT(1) FROM enterprise_marketplace_asset_snapshots"))
published_count = conn.scalar(sa.text("SELECT COUNT(1) FROM enterprise_marketplace_assets WHERE published_snapshot_id IS NOT NULL"))
if snapshot_count or published_count:
    raise RuntimeError(...)
```
测试 `test_guard_against_data_loss` PASS。

#### F-19：空数据时删除顺序正确 — PASS

**证据**：downgrade L245-L289：
1. 先 `drop_index` B4 索引
2. `drop_constraint` B4 CHECK
3. `drop_column` B4 新增 6 列
4. `drop_index` snapshot 索引
5. `drop_table("enterprise_marketplace_asset_snapshots")`

顺序正确：先删依赖项（索引→约束→列），最后删表。

#### F-20：不会静默丢失 snapshot 或 published pointer — PASS

**证据**：数据保护 gate 在删除任何数据结构前执行。若 gate 通过（snapshot 表空且所有 `published_snapshot_id` 为 NULL），删除的只是 B4 新增结构，不会丢失用户数据。

#### F-21：保留旧 16 列及旧数据 — PASS

**证据**：downgrade 只 drop B4 新增列和 B4 新增约束/索引。不触及原 `c8f3d9d4a1be` 创建的 16 列和数据。

### 4.5 测试有效性

#### F-22：NOT_RUN 清单

| 测试 | 原因 |
| --- | --- |
| `flask db heads` | 需要完整 Flask app context 和数据库配置，工具指令 §5 禁止执行 flask db upgrade/downgrade/stamp；db heads 虽不修改 DB，但在缺少完整配置的环境中无法运行。Alembic ScriptDirectory head 解析已在 pytest 中验证（`test_unique_head_is_b416e5c4e702`），可替代。 |
| `api/tests/unit_tests/controllers/*` | B4-A 不涉及 controller |
| `api/tests/unit_tests/services/*` | B4-A 不涉及 service |
| `flask db upgrade/downgrade/stamp` | 工具指令 §5 禁止 |
| PostgreSQL 真实数据库测试 | 工具指令 §5 禁止访问真实 PostgreSQL |
| B8/隔离副本测试 | B4-A Reviewer 职责范围外 |

#### F-23：测试不依赖宽松断言 — PASS

**独立审查**：所有 57 个 model 测试 + 45 个 migration 测试均使用精确断言而非模糊宽松条件。举例：
- 非 `assert col.server_default`（truthy），而是 `assert col.server_default.arg.text == "'unpublished'"`
- 非 `assert "VARCHAR" in str(col_type)`，而是 `assert isinstance(col_type, sa.VARCHAR)`

#### F-24：无吞异常 — PASS

**独立审查**：测试中的 try/except 不存在。所有异常通过 pytest 标准断言机制传播。

#### F-25：无源码字符串自我证明 — PASS

**独立审查**：测试不通过 re.match 源码文本来证明 DDL 的语义。相反：
- 模型测试直接查询 `EnterpriseMarketplaceAsset.__table__` 的 metadata（Column 对象、Index 对象、Constraint 对象）
- Migration 测试通过 mock `op.add_column` side_effect 捕获实际 `sa.Column` 对象，对真实 SQLAlchemy 类型做类型安全检查
- Alembic graph 测试使用真实 `ScriptDirectory.from_config()` 解析，不硬编码文件内容

#### F-26：无重复实现被测 SQL — PASS

**独立审查**：`TestUnknownLegacyStatusInMemory` 类（migration test L329-L455）通过 `module._ASSET_INIT_SQL` 获取 migration 模块同一 SQL 字符串常量，对 in-memory SQLite 执行。这是**复用**被测 SQL，不是**重复实现**被测 SQL。fixture 注入方式正确：
```python
@pytest.fixture(scope="class")
def asset_init_sql(self) -> str:
    module = _load_migration_module(B416E)
    return module._ASSET_INIT_SQL  # same string constant the migration uses
```

#### F-27：server-default 测试捕获实际 add_column Column 对象 — PASS

**独立审查**：`TestMigrationServerDefaults` 类通过 mock `op.add_column` side_effect 记录传入的 `sa.Column` 参数，然后对 Column 对象的 `.server_default.arg.text` 做精确断言。这是对 Alembic 实际将传递给数据库的 Column 对象的验证，不依赖字符串解析。

## 5. 已知 B2 Head 测试的正式 Disposition

### 5.1 事实描述

文件：`api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py`
测试：`TestSingleHead.test_graph_has_exactly_one_head_and_it_is_a71e16c0de01` (L116-L120)

```python
def test_graph_has_exactly_one_head_and_it_is_a71e16c0de01(
    self, script_directory: ScriptDirectory
) -> None:
    heads = script_directory.get_heads()
    assert heads == [A71E]  # expects ["a71e16c0de01"]
```

**实际结果**：`script_directory.get_heads()` 返回 `["b416e5c4e702"]`。

### 5.2 独立判断

**独立验证步骤**：
1. 已运行 `pytest api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py`，15 passed / 1 failed
2. 已独立运行 B4-A migration test `test_unique_head_is_b416e5c4e702` — PASS，确认唯一 head 为 `b416e5c4e702`
3. 已独立运行 B2 merge parent test `test_head_parent_is_a71e16c0de01` — PASS，确认 `b416e5c4e702` 父为 `a71e16c0de01`
4. 检查 `ScriptDirectory.get_heads()` 源码：它返回所有无子节点的 revision ID 列表。B4-A 添加 `b416e5c4e702` 作为 `a71e16c0de01` 的子节点后，`a71e16c0de01` 不再是 head

**结论**：
- **这不是双 head**：`get_heads()` 仅返回 `["b416e5c4e702"]`，只有一个 head
- **这是 B4-A 引入后的陈旧 B2 测试**：B2 测试创建时 `a71e16c0de01` 是唯一 head；B4-A 正确地将 `b416e5c4e702` 堆叠在其上，使之成为新的唯一 head
- **Alembic graph 拓扑完全正确**：chain 为 `c8f3d9d4a1be → f1a14e1e9b41 → e2f0a9b7c6d5 → a71e16c0de01 → b416e5c4e702`（单链，无分支）

### 5.3 是否必须在进入 B4-B 前修复

**是，必须在 B4-B 启动前修复**。

原因：
- 当前候选分支整体测试并非全绿 — B2 graph suite 存在确定性的 1 failure
- B4-A 阶段尚未整体闭环；带着已知 failure 进入 B4-B 不可接受
- 该测试位于 B2 文件，不在 B4-A Builder allowlist 内；B4-A Builder 正确遵守了 denylist 未修改 B2 测试，B4-A Reviewer 也不能修改。纠正职责属于独立的 B4-A Fixer 步骤

**Fixer 必须**：在 B4-A 当前 worktree 上精确修复一项测试断言，不改任何 migration 或 B4-A 实现文件。

### 5.4 精确 Fixer 建议

**唯一 allowlist**：
```
api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py
```

**精确修复方向**：

1. 保留 `A71E` 常量：仍用于验证 B2 merge revision 存在、父节点和历史链（这些测试已经 PASS，不需修改）
2. 将旧的 single-head 测试重命名，使名称不再声称 head 是 a71
3. 新增 `B416E = "b416e5c4e702"` 常量
4. 精确断言当前唯一 head：
   ```python
   assert heads == [B416E]
   ```
5. **不得**使用 `contains`、`len >= 1`、`A71E in heads` 或其他宽松断言
6. **不得**修改任何 migration 文件或 B4-A 实现文件（`model.py`、`__init__.py`、migration、B4-A tests）

**Fixer 后必须同时运行并通过**：
- `api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py`
- `api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py`
- `api/tests/unit_tests/models/test_enterprise_marketplace.py`

## 6. 实际运行测试及精确结果

### 6.1 B4-A Model Tests

```bash
uv run --project api pytest \
  api/tests/unit_tests/models/test_enterprise_marketplace.py \
  -v --tb=short -p no:cov --override-ini="addopts="
```

| 结果 | 数量 |
| --- | --- |
| **PASSED** | 57 |
| **FAILED** | 0 |
| **总计** | 57 |

内部分布：TestPublicationStatusEnum(2)、TestSnapshotStateEnum(2)、TestEnterpriseMarketplaceAssetTable(25)、TestEnterpriseMarketplaceAssetSnapshotTable(18)、TestModelExportRegistration(4)、TestModelTypeAnnotations(3)。

### 6.2 B4-A Migration Tests

```bash
uv run --project api pytest \
  api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py \
  -v --tb=short -p no:cov --override-ini="addopts="
```

| 结果 | 数量 |
| --- | --- |
| **PASSED** | 45 |
| **FAILED** | 0 |
| **总计** | 45 |

内部分布：TestRevisionIdentity(4)、TestAlembicGraph(2)、TestB2MigrationsUnchanged(5)、TestMigrationServerDefaults(6)、TestMigrationUpgradeAST(12)、TestDowngradeAST(3)、TestUpgradeNoStamp(3)、TestKnownStatusMapping(4)、TestUnknownLegacyStatusInMemory(6)。

### 6.3 B2 Migration Graph Tests（非 B4-A，信息性运行）

```bash
uv run --project api pytest \
  api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py \
  -v --tb=short -p no:cov --override-ini="addopts="
```

| 结果 | 数量 |
| --- | --- |
| **PASSED** | 15 |
| **FAILED** | 1 (`test_graph_has_exactly_one_head_and_it_is_a71e16c0de01`) |
| **总计** | 16 |

### 6.4 flask db heads

**NOT_RUN** — 需要完整 Flask app context 和数据库配置（见 §4.5 F-22）。等效验证由 Alembic ScriptDirectory head 解析（migration test `test_unique_head_is_b416e5c4e702` PASS）提供。

## 7. File Allowlist 符合性

| 文件 | 计划 allowlist | 实际变更 | 符合 |
| --- | --- | --- | --- |
| `api/models/__init__.py` | ✓ | +8 lines (4 imports + 4 \_\_all\_\_ entries) | ✓ |
| `api/models/model.py` | ✓ | +209 lines (2 enums + 2 models) | ✓ |
| `api/migrations/versions/2026_07_21_1400-b416e5c4e702_*.py` | ✓ | +289 lines (new) | ✓ |
| `api/tests/unit_tests/models/test_enterprise_marketplace.py` | ✓ | +433 lines (new) | ✓ |
| `api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py` | ✓ | +498 lines (new) | ✓ |
| **总计** | 5 files | 1437 insertions, 0 deletions | ✓ |

Denylist 无违规：B2 文件（4 个 migration）未被修改、B3 独占文件未被修改、controller/service/contracts 未被修改、Web/Docker 未被修改。

## 8. B4-B 启动门禁

**B4-B 不允许启动**。B4-A 阶段尚未整体闭环：B2 graph suite 存在确定性的 1 failure。必须先在当前 worktree 上执行有限 Fixer（见 §5.4），将 B2 single-head 测试断言从 `a71e16c0de01` 更新为 `b416e5c4e702`，并复审通过。

Fixer 通过后，B4-B 的门禁为：

1. B4-A Fixer 复审 PASS
2. Alembic graph 唯一 head 为 `b416e5c4e702`
3. 全部三个 test suite 绿色（graph + marketplace migration + model）
4. B4-B Builder 必须从 Fixer 接受的精确 commit SHA 启动，禁止 merge/rebase/reset/cherry-pick、用分支名或 HEAD 代替

### B4-B 必须注意的已知点

- B4-A 不产生需要 B4-B 矫正的 schema defect
- `row_version >= 0` CHECK 已按计划删除（仅保留 `next_snapshot_version >= 1`）
- B4-B 不得修改 B4-A model/migration 文件

## 9. P2 Finding

### P2-1：迁移中 StringUUID 列的 nullable 使用 nullable=True 但模型使用 `sa.VARCHAR(64)` 类型而非统一使用 `StringUUID`

**文件**：`api/migrations/versions/2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py`
**行**：L61, L62, L68, L69, L70, L71, L83 等

**证据**：migration 中 `sa.Column("id", sa.String(length=36))` 和 `sa.Column("asset_id", sa.String(length=36))` 使用 `sa.String(length=36)` 作为类型声明，而模型中使用 `StringUUID` type decorator（如 `model.py` L2795 `mapped_column(StringUUID)`）。官方旧 migration `c8f3d9d4a1be`（L22）也使用 `sa.String(length=36)`，这是现有惯例。

**影响**：Alembic 在迁移层面不执行 `StringUUID` type decorator 的 Python 层 UUID 验证/转换。对于 schema DDL 生成，`String(length=36)` 和 `StringUUID` 生成相同的 SQL 类型（都是 `VARCHAR(36)`）。因此这是风格一致性差异而非功能差异。

**评价**：不影响正确性，但为追求一致性，可在未来 migration 风格统一专项中调整。**P2**，非阻塞。

## 10. 审查 Disposition 摘要

| 项目 | 值 |
| --- | --- |
| 最终结论 | **CHANGES_REQUIRED** |
| B4-A schema/model/migration 实现审查 | 接受（PASS） |
| B4-A 阶段整体闭环 | 否（B2 head 测试 1 failure） |
| 是否允许启动 B4-B | **不允许**（必须 Fixer 先闭环） |
| 阻断 P0 | 0 |
| 阻断 P1 | 1 — 陈旧 B2 single-head 测试造成确定性的测试失败 / CI 红灯 |
| 非阻断 P2 | 1 — `sa.String(36)` vs `StringUUID` 风格差异，非功能性 |
| ACCEPTED_KNOWN_LIMITATION | 0 |
| B2 head 测试 disposition | 陈旧 B2 测试断言 `a71e16c0de01` 仍是唯一 head；非双 head；必须 Fixer 修复 |
| Fixer allowlist | `api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py` |
| NOT_RUN | `flask db heads`（等效验证已由 Alembic ScriptDirectory 测试覆盖） |
| B4-A 实现文件修改数量 | 5 |

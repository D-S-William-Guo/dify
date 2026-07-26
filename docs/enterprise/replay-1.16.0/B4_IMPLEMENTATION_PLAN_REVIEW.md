# Dify Enterprise 1.16.0 Replay B4 独立实施计划审查

## 0. 审查元数据

- 角色：独立 B4 Plan Reviewer
- 审查分支：`ctyun/replay-116-b4-plan-reviewer`
- 审查 HEAD：`09741522dee1da743ea3effca26942090716b260`
- 工作区：审查前干净（`git status --short` 无输出）
- 官方源码基准：`1.16.0` tag / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 独立验证方法：逐项对照官方 1.16 源码，不接受计划文档自我证明

## 1. 最终结论

**CHANGES_REQUIRED**

**B4_READY_WITH_CONDITIONS — 不接受**。现有条件不足以安全启动全部 Builder。

**P0=2, P1=5, P2=4**（计划声明 P1=3, P2=3，显著低估）。

## 2. 门禁核验

| 检查项 | 预期 | 实际 | 状态 |
| --- | --- | --- | --- |
| 分支 | `ctyun/replay-116-b4-plan-reviewer` | `ctyun/replay-116-b4-plan-reviewer` | PASS |
| HEAD | `09741522dee1da743ea3effca26942090716b260` | 一致 | PASS |
| 工作区 | 干净 | 干净 | PASS |

## 3. P0 Findings

### P0-1：copy 路径 `import_app()` 内部 commit 破坏原子 rollback 承诺

**源码证据**：

```python
# api/services/workflow_service.py:384-386
# sync_draft_workflow 方法：
        # commit db session changes
        if commit:
            session.commit()
```

```python
# api/services/app_dsl_service.py:510-521
# _create_or_update_app 方法中：
                draft_workflow = workflow_service.sync_draft_workflow(
                    ...
                    session=self._session,
                    commit=not raw_agent_packages,   # 无 agent package 时为 True
                    ...
                )
```

```python
# api/controllers/console/app/app_import.py:88-90
# 官方 controller 已明确认知此行为：
        # AppDslService performs internal commits for some creation paths, so use a plain
        # Session here instead of nesting it inside sessionmaker(...).begin().
        with Session(db.engine, expire_on_commit=False) as session:
```

**影响**：

B4 计划 §9 copy 流程声称：
> "import 后再次 `check_dependencies`；出现 leaked dependency 则 rollback"

但 `import_app()` 在无 agent packages 时（这是 marketplace snapshot 的正常路径 — snapshot 不含 agent packages），`sync_draft_workflow(commit=True)` 在 `workflow_service.py:386` 调用了 `session.commit()`。此时：

- App、Workflow、InstalledApp、Site 已持久化到数据库
- `app_draft_workflow_was_synced` signal 已触发 webhook/trigger 同步（独立 session）
- B4 的 `session.begin()` 上下文管理器和 `with_session` decorator 提交均变为 no-op

若 post-import `check_dependencies` 失败："rollback" 是**空操作** — 已 committed 的 App 不会被回滚。Redis dependency key 的 best-effort 清理无法补偿已持久化的数据库记录。

计划 P1 风险 #2 只提到 "DB rollback 不能自动回滚 Redis"，但未提及 DB 自身已无法回滚。这是更严重的缺失。

**要求修复**：

必须重新设计 copy 事务边界。选项包括：
1. **预检唯一**：只做预检（`DependenciesAnalysisService.get_leaked_dependencies`），移除 post-import check。预检成功后才 import。这是最安全的方案。
2. **复用官方模式**：参考官方 `app_import.py:88-109`，使用 plain `Session` + 显式 `session.commit()`/`session.rollback()`，不在 import 外包裹 `session.begin()`。
3. **设置 agent_packages**：在 snapshot DSL 中注入一个空/占位 agent packages 结构使 `commit=False`，但此方案会改变 DSL 语义、增加不确定性和 agent import 路径复杂度，不推荐。

**B4-A 影响**：无。但 B4-B copy 实现必须在修正本问题后才能开始。

---

### P0-2：submit 与 review 锁顺序相反导致真实死锁

**源码证据**：

B4 计划 §10 明确描述：
> - submit：锁 source App；查询/锁 asset
> - review：锁 asset 后锁 source App

官方代码库中 `platform_admin_service.py` 的 `update_member_role` 方法严格按固定顺序锁多行（`Tenant → TenantAccountJoin → Account`），注释明确提到底层 PostgreSQL 行级锁的序列化语义。这是现有代码中的锁顺序约定。

**影响**：

两个并发事务：
- T1 (submit): `FOR UPDATE source App A` → 等待 `FOR UPDATE asset X`
- T2 (review): `FOR UPDATE asset X` → 等待 `FOR UPDATE source App A`

这是经典的循环等待，PostgreSQL 死锁检测将在 `deadlock_timeout` 后中止其中一个事务。

计划 §10 的声称：
> "固定锁顺序均为 asset → source App"

与 submit 路径的 source App → asset 描述**自相矛盾**。

计划 §10 的辩解：
> "submit 只有 source App → asset，因此 review 不得同时等待 source lock 后回取另一 asset"

不是有效的死锁避免证明。只要两个路径以相反顺序获取相同两个资源，就存在死锁可能。

**要求修复**：

统一两条路径的锁获取顺序。两种方案：

**方案 A（推荐）**：两条路径均使用 **source App → asset**。
- submit：自然顺序
- review：先锁 source App（验证存在、normal、归属），再锁 asset（检查 pending、check expected row version、生成 snapshot）

**方案 B**：两条路径均使用 **asset → source App**。
- review：自然顺序
- submit：先查询 asset（验证不存在 pending 提交），再锁 source App，再插入 asset

方案 A 在 review 中仍需要检查 asset 的 pending 状态，但可在 source 锁获取后、asset 锁获取前做非锁定读取。方案 B 在 submit 中需要先检查 asset 是否存在 pending，再锁 source App 后重新检查。

无论选择哪种方案，都必须：
1. 在计划文档中明确写出统一的锁顺序
2. 说明两条路径如何以相同顺序获取锁
3. B4-B 测试中包含并发 submit+review 死锁验证用例

**B4-A 影响**：无。但必须在 B4-B 开始前修正计划。

---

## 4. P1 Findings

### P1-1：`status` check constraint 对未知客户数据不安全

**源码证据**：

官方代码库中**没有任何** varchar 列的 `CHECK` 约束。状态验证完全在应用层（Pydantic `Literal`、`StrEnum` + `EnumText` type decorator）。这是官方有意为之的设计模式 — 数据库层不限制状态值，允许应用演进。

B2 inventory 仅包含 1 行（status=`approved`）。该 inventory 文档 §4.3 明确声明：

> "当前只有一行来源正常是已核实的本地 inventory，不能被写成所有客户数据都来源正常。"

**影响**：

若任何客户数据库中 `enterprise_marketplace_assets.status` 包含非规范值（如旧版本特有的状态、运维修复遗留值、或未来线下 SQL 写入），`ALTER TABLE ... ADD CONSTRAINT ... CHECK (status IN (...))` 将失败，阻断整个 migration。

迁移失败意味着：
- 整个 Alembic upgrade 中止
- `alembic_version` 不会更新
- 数据库处于半迁移状态（新列可能已添加但约束未建立）
- 需要人工介入恢复

**要求修复**：

三种可行方案：

**方案 A（推荐）**：添加约束前先处理异常数据。
```python
# migration upgrade() 中，添加 CHECK 前：
op.execute(sa.text("""
    UPDATE enterprise_marketplace_assets
    SET status = 'unlisted'
    WHERE status NOT IN ('pending', 'approved', 'rejected', 'unlisted')
"""))
# 记录受影响行数到日志
```

**方案 B**：不加 CHECK 约束，仅在应用层校验。
- 优点：与官方模式一致，zero migration 风险
- 缺点：没有数据库层安全网

**方案 C**：NOT VALID 约束 + 单独验证步骤。
```sql
ALTER TABLE enterprise_marketplace_assets
ADD CONSTRAINT ck_marketplace_asset_status
CHECK (status IN ('pending','approved','rejected','unlisted')) NOT VALID;
```
然后由独立验证步骤检查 `NOT VALID` 约束是否有违反行。

**B4-A 影响**：必须在 B4-A migration 实现中解决。

---

### P1-2：`row_version` 乐观并发没有现有模式且语义模糊

**源码证据**：

官方代码库中**没有** `row_version`、SQLAlchemy `version_id_col`、或应用层版本号乐观锁模式。所有现有并发控制通过以下方式实现：

1. `FOR UPDATE` 行级锁（`platform_admin_service.py:205,340,424`）
2. Redis 分布式锁（`credit_pool_service.py:69`）
3. Unique constraint 竞争映射为并发错误

**影响**：

B4 计划 §5.1 定义 `row_version` 为每次 mutation `+1`，§6.2 要求 resubmit/review/unlist 传 `expected_row_version`。但计划**同时**使用 `FOR UPDATE` 锁（§10）。两套机制的交互未明确：

- 如果 `FOR UPDATE` 已序列化所有写操作，`row_version` 检查是冗余的（不可能看到 stale version）
- 如果依赖 `row_version` 检测并发，`FOR UPDATE` 增加了不必要的锁竞争
- 回填路径 §12.5 说 "失败只更新 snapshot_state…不改旧 status"，此时 `row_version` 如何变化未定义

计划 §5.1 的 CHECK `row_version >= 0` 约束无实际意义（整数永远 `>= 0`）。

**要求修复**：

1. 明确 `FOR UPDATE` 与 `row_version` 的分工：`FOR UPDATE` 用于序列化写操作（保证在锁内读到的 version 是最新的），`row_version` 用于 API 层的乐观并发检测（调用者传递 `expected_row_version`，与锁内读出的当前值比较）
2. 说明：即使有 `FOR UPDATE` 保护，仍然做 version 比较，因为 HTTP 调用者可能在另一个事务中读取了 stale 版本后发送请求
3. 删除或改为有实际意义的 CHECK 约束（如 `row_version >= 0` → 仅文档化）
4. 明确回填操作修改 `snapshot_state` 时是否递增 `row_version`（§12.5 的问题）

---

### P1-3：`import_app()` 中间 commit 导致 DB 副作用无法回滚

**源码证据**：

当 `import_app` 内部 `sync_draft_workflow(commit=True)` 提交时，以下数据已被持久化：

1. **App 行**：`_create_or_update_app` 中 `session.add(app)` + `session.flush()`（`app_dsl_service.py:458-459`）
2. **InstalledApp 行**：`app_was_created` signal → `create_installed_app_when_app_created` handler（`create_installed_app_when_app_created.py:18-24`）
3. **Site 行**：同上 signal → `create_site_record_when_app_created` handler
4. **Workflow 及其节点/边**：`sync_draft_workflow` 中 `session.add()` + `session.flush()`（`workflow_service.py:360-372`）
5. **Webhook 同步**（独立 session）：`app_draft_workflow_was_synced` signal → `sync_webhook_when_app_created` handler（`sync_webhook_when_app_created.py:22`），在自己的 `sessionmaker(...).begin()` 中自动提交
6. **Plugin trigger 同步**（独立 session）：同上 signal → `sync_plugin_trigger_when_app_created` handler
7. **AppModelConfig**（CHAT/AGENT_CHAT/COMPLETION 模式）：`_create_or_update_app` 中 `session.add()` + `session.flush()`（`app_dsl_service.py:548-552`）

以上所有 effect（除独立 session 的 webhook/trigger）在 `sync_draft_workflow(commit=True)` 的 `session.commit()` 中一次性提交。

**影响**：

B4 计划 §9 copy 流程中 "import 后再次 `check_dependencies`；出现 leaked dependency 则 rollback" **不可能回滚**已持久化的 App/Workflow/InstalledApp/Site。post-import dependency 二次检查失败后，系统中残留一个完整但无法使用的 App。

Redis dependency key 的 best-effort 清理同样不足以恢复。已创建 Web/trigger/AppModelConfig 等副作用同样无法撤销。

**要求修复**：

同 P0-1。根本解决方案是**不做 post-import check**，只做预检。若预检通过 → import → 成功。若 import 返回 FAILED/PENDING → 已由 `import_app` 语义处理（FAILED 时官方 controller 做 rollback）。

若必须保留 post-import check，需采用以下之一：
1. 如上所述，确保 DSL 不含 agent packages 路径下 import 不 commit（需要修改官方 import 调用方式或接受官方 service 的行为）
2. 在 post-import check 失败后调用 `RemoveAppAndRelatedDataTask`（官方已有 Celery task 用于删除 app 及其关联数据），但这是异步清理，不是原子回滚

---

### P1-4：canonical YAML 再序列化与官方 DSL 兼容性未验证

**源码证据**：

计划 §9.3：
> "yaml.safe_load 后要求 mapping、kind=app、version 为当前受支持字符串，重新用 canonical dumper 输出 UTF-8 YAML；hash 对 canonical 字节计算。"

官方 `export_dsl()` 使用 `yaml.dump(data, allow_unicode=True, sort_keys=False)`（`app_dsl_service.py:635`）输出 YAML。plan 的 canonical dumper 使用不同参数（如 `sort_keys=True`、不同的缩进/换行规则等）会产生不同结构的 YAML。

**影响**：

- 若 canonical YAML 在结构上与原始 export 等价（YAML 语义相同），import 行为应一致
- 若 canonical 改变 key 顺序、多行字符串格式、null 表示、或列表缩进而影响 DSL import 解析，可能导致 import 行为差异（如 workflow graph 连接关系丢失、环境变量绑定错误等）
- Hash 稳定性依赖于 canonical dumper 的实现细节；dumper 参数的任何变化（如 PyYAML 版本升级）都会改变 hash

**要求修复**：

1. 必须包含 round-trip 测试：`export_dsl → yaml.safe_load → canonical dump → yaml.safe_load → import_app`，验证 import 结果与原始 export 的再次 import 结果一致
2. 文档化 canonical dumper 的精确参数和依赖版本
3. 若官方未来升级 YAML 库版本、改变 `export_dsl` 输出格式，必须有对应的 snapshot 兼容性测试

---

### P1-5：Redis dependency key 预检和清理链路不完整

**源码证据**：

`DependenciesAnalysisService` 不在 B4 允许修改范围内（官方 `api/services/plugin/dependencies_analysis.py`）。其 `get_leaked_dependencies` 方法（line 39-73）通过 HTTP POST 向 Plugin Daemon 查询缺失依赖。`check_dependencies` 方法定义在 `AppDslService` 中（`app_dsl_service.py:375-396`），从 Redis key `app_check_dependencies:{app_id}` 读取数据，TTL 为 10 分钟。

B4 计划 §9 copy 流程：
> "import 后再次 `check_dependencies`；出现 leaked dependency 则 rollback，清理本次 import 对应的短期 dependency Redis key（best effort、仅使用本次新 app ID），返回 `dependency_unavailable`"

**影响**：

1. 预检使用的是 snapshot 声明的 dependencies（独立 JSON 列），post-import check 使用的是 import 后 Redis 中写入的 dependency data
2. 两套数据可能不一致（snapshot DSL 中的 dependencies 与 Redis 中的 check_dependencies pending data 可能因序列化/解析差异而不同）
3. 计划未说明如何"清理本次 import 对应的短期 dependency Redis key" — Redis key 是 `app_check_dependencies:{app_id}`（TTL 10 分钟），删除它不会撤销 Plugin Daemon 端的任何状态
4. 若 import 返回 FAILED/PENDING，Redis key 可能已被写入但 DB 未创建 App。此时 `app_id` 引用一个不存在的 App，无法通过 `check_dependencies` 正常读取

**要求修复**：

1. 明确预检（`get_leaked_dependencies`）和后检使用相同的数据源（snapshot 的 `dependencies` JSON 列）
2. 移除 post-import check（见 P0-1），改为仅预检
3. 若保留 post-import check，需文档化清理步骤的精确范围：仅删除 Redis key，不涉及 Plugin Daemon 状态

---

## 5. P2 Findings

### P2-1：无物理 FK 增加孤儿数据风险且缺少完整性验证测试

**源码证据**：

计划 §5.3 明确不在 `snapshot.asset_id` 和 `asset.published_snapshot_id` 上建 FK。理由：历史表原本无 FK，双向指针增加 migration 顺序和级联风险。

**影响**：

- B4 API 不提供删除，但未来若任何代码路径删除 asset 行，snapshot 表将包含孤儿行
- `published_snapshot_id` 可能指向已删除/错误的 snapshot 行
- 无 DB 层约束意味着 service invariant 是唯一防线；任何绕过 service 的写入（如 migration、回填、手动修复）都可能破坏引用完整性

**要求修复**：

1. B4-B 测试必须包含 snapshot→asset 完整性验证（例如：`SELECT count(*) FROM snapshots WHERE asset_id NOT IN (SELECT id FROM assets)` 期望为 0）
2. 在 `published_snapshot_id` 非空的条件下，验证指向的 snapshot 存在且 `asset_id` 匹配
3. 若后续任何 Builder 添加对 `enterprise_marketplace_assets` 的删除能力，必须先评估 FK 的必要性

---

### P2-2：`content_sha256` 使用 `CHAR(64)` 而非 `VARCHAR(64)` 可能引入填充问题

PostgreSQL 的 `CHAR(n)` 类型会用空格填充到固定长度，查询比较时可能产生意外行为。`VARCHAR(64)` 更适合哈希存储，且与代码库中其他哈希存储模式一致。虽不影响功能正确性（hex 字符串天然是 64 字符），但 `CHAR` 是不必要的语义混淆。

---

### P2-3：回填 runner 脚本不入库削弱可审计性和可复现性

**源码证据**：

计划 §12：
> "实际 runner 使用 `/tmp` 中不提交仓库的一次性、审阅过的调用脚本，逐 ID 调用"

**影响**：

- 回填执行没有版本化的源码记录，无法复现或审计实际执行的操作
- "审阅过的调用脚本"依赖人工流程，缺乏自动化门禁
- 若多名运维人员在不同时间执行回填，无法保证使用相同版本的 runner
- B8/隔离 PostgreSQL 副本的执行结果无法与特定 runner 版本关联

**要求修复**：

方案：
1. 将 runner 脚本提交到 `scripts/enterprise/` 或 `dev/`，使其版本受控
2. 脚本仅为 `backfill_legacy_snapshot()` service primitive 的薄封装（调用 B4-B 提供的 public method）
3. 若必须不提交：至少在 B4-B handoff 中包含 runner 的 SHA-256 摘要和精确内容的引用，使其可被外部验证

---

### P2-4：审计日志、分页信息泄漏和错误内容泄漏缺乏具体设计

**源码证据**：

计划 §8 列出了错误码和 HTTP 映射，但未定义：

1. **操作审计日志**：submit/review/unlist 是否产生 `OperationLog` 记录（官方 `OperationLog` model 在 `api/models/model.py` 中已存在）？B3 有明确的日志事件表（如 `platform_admin.identity_checked`、`platform_admin.workspace_renamed`），但 B4 计划未文档化
2. **分页信息泄漏**：错误响应中是否返回 page/limit/total？错误路径中分页参数是否经过验证？
3. **错误内容泄漏**：§8 说 "内部细节不回显"，但 plan 未描述如何防止 `Import.error` 的异常文本泄漏到 HTTP response。官方代码库中有 `Import` NamedTuple（`dsl_entities.py`），包含 `error: str` 字段，可能包含敏感信息

**要求修复**：

B4-B 实施前补充：
1. 审计日志事件表（类似 B3 的 §7/§9），定义 submit/review/unlist/copy 的操作级别、包含字段、脱敏策略
2. 明确 `MarketplaceErrorResponse` 在分页/过滤错误时不回显查询参数
3. 明确 `Import.error` 不被透传到 HTTP response body

---

## 6. 细化发现（编号 1-35 逐一检查）

### 检查 1：B4-A/B/C 拆分、文件所有权和起点可执行性

B4-A 文件 allowlist（model 两文件、migration、model/migration tests）与计划声明一致。B3 独占文件（`platform_admin.py`、`platform_admin_service.py`、`platform_admin.py` lib）在 denylist 中正确排除。

B4-A 起点 `925b01e9d2486bd230bffdb5f3ecb41b83bdf8e4` 是 Architect handoff 的精确 commit。

**结论**：PASS，但等待修正 P1-1（migration check constraint）。

### 检查 2：最终 schema 字段、类型、默认值、JSON、约束、索引符合模型惯例

**与官方模型对比**：

| 特征 | 官方模式 | B4 计划 | 符合性 |
| --- | --- | --- | --- |
| Base class | `TypeBase` 或 `Base` + `DefaultFieldsMixin` | 未指定 | 需在 B4-A 明确 |
| ID | `StringUUID` with `uuidv4()`/`uuidv7()` | `varchar(36)` NOT NULL | 应使用 `StringUUID` type decorator |
| JSON | `sa.JSON` | JSON | 一致 |
| Boolean | `sa.Boolean` + `server_default=sa.text("false")` | boolean / false | 一致 |
| Integer | `sa.Integer` + `server_default=sa.text("0")` | integer / 0 | 一致 |
| String | `String(255)` 或 `String(32)` | varchar(255)/varchar(32) | 应指定具体 `String` 长度 |
| Text | `LongText` | text/LongText | 应统一使用 `LongText` |
| DateTime | `sa.DateTime` + `server_default=func.current_timestamp()` | datetime / CURRENT_TIMESTAMP | 一致 |
| Enum | `EnumText(StrEnum, length=N)` | varchar(32) + CHECK | **偏离**：官方使用 `EnumText` type decorator，不使用 CHECK 约束 |
| Unique con. | `sa.UniqueConstraint(...)` | 保留旧 unique | 一致 |
| Index | `sa.Index(...)` | 三个新索引 | 一致 |

**结论**：PASS，但需注意 `CHECK` 约束偏离官方模式（见 P1-1）。建议使用 `EnumText` 类型或仅应用层校验而非数据库 CHECK。

### 检查 3：`b416e5c4e702` upgrade/downgrade 在 PostgreSQL 上安全且确定

Plan §11.1 的 upgrade 步骤：先加 nullable 列 → SQL CASE 初始化 → 加 NOT NULL/check/index。这是正确的 PostgreSQL schema migration 模式。

Downgrade §11.2 包含安全阀：若 snapshot 表非空或 `published_snapshot_id` 非空，显示失败。这符合计划文档声明的保护级别。

**但 P0-1 和 P1-1 是阻止安全结论的未解决问题**。若 `status` CHECK 约束在未知客户数据上失败，整个 upgrade 是不安全的。

### 检查 4：对未知 status 的 check constraint 升级失败风险

已在 P1-1 中详述。**P1**。

### 检查 5：`status` 与 `publication_status` 两套状态矛盾组合

计划 §6.1/§6.2 定义两套枚举和合法操作矩阵。合法组合由数据库 CHECK 约束和服务 invariant 双重定义。

**服务 invariant 逻辑**：
- 首次 submit: `status=pending` + `publication_status=unpublished` + `snapshot_state=none`
- approve: `status=approved` + `publication_status=published` + `snapshot_state=ready`
- reject: `status=rejected` + `publication_status` 不变（保持 unpublished 或 published）
- unlist: `publication_status=unlisted` + `status` 不变（保持 approved 或 rejected）
- resubmit after reject: `status=pending` + `publication_status=unpublished`
- resubmit after unlist: `status=pending` + `publication_status=unlisted`（不自动重上架）

**矛盾组合分析**：

`status=unlisted` 与 `publication_status=published` 的矛盾：计划 §5.1 明确说"旧 unlisted 行两者均保持/映射为 unlisted；新下架不需要破坏正在审核的 status"。新代码中 `status=unlisted` 仅出现在 legacy 数据。新操作使用 `publication_status=unlisted` 配合 `status` 保持 approved/rejected。

但 migration SQL CASE §11.1.3 将旧 `unlisted` 映射为 `publication_status=unlisted` + `snapshot_state=none`，此时 `status` 仍为 `unlisted`。这意味着旧 unlisted 行有 `status=unlisted` + `publication_status=unlisted`。新 unlist 操作产生 `status` 保持 approved/rejected + `publication_status=unlisted`。

这不是矛盾 — 旧 legacy `status=unlisted` 和新 `publication_status=unlisted` 有明确的分野。但 service 代码必须能处理两种形态。

**结论**：PASS。两套状态的设计可区分"旧 legacy 下架"和"新 moderation-published-unlisted"语义。但 service invariant 应在 docstring 中明确记录。

### 检查 6：published 后 resubmit/reject、unlist、重新 approve 语义一致性

计划 §6.2 操作矩阵合法路径：

1. **resubmit after published**: `status=approved, publication=published` → `status=pending, publication=published`。已发布快照继续公开。这是预期行为：重新提交正在审核的新版本期间，旧发布版本继续可见。

2. **reject after published**: `status=pending` → `status=rejected`。publication 保持 published。旧快照继续可见。

3. **unlist after published**: `publication=published` → `publication=unlisted`。快照保留不删除。

4. **re-approve after unlist**: `status=pending, publication=unlisted` → `status=approved, publication=published`。新 snapshot 发布。

语义一致。已发布快照的"指向"变更（从旧 snapshot 移到新 snapshot）通过 approve 流程内的 pointer→新快照 INSERT 实现。

**结论**：PASS。

### 检查 7：snapshot append-only、pointer、version、hash 和 row_version 并发正确性

Append-only 语义：snapshot 表禁止 UPDATE/DELETE。计划 §5.2 明确 "B4 service 不提供 update/delete；审核通过只 INSERT"。

并发版本分配 §6.2：在 asset `FOR UPDATE` 锁内读取并递增 `next_snapshot_version`。由于 `FOR UPDATE` 序列化并发，version 单调性由单线程保证。

Hash：`content_sha256` 在 canonical YAML 上计算，unique constraint `(asset_id, snapshot_version)` 防止同 asset/version 重复。

**但 P0-2（锁顺序）影响 review 路径的并发正确性**。若 review 与 submit 死锁，review 事务将被 PostgreSQL 中止，导致 approve 失败。这需要通过统一锁顺序解决。

**结论**：PASS with caveat（P0-2 需修复后重新验证）。

### 检查 8：锁顺序死锁风险

已在 P0-2 中完整分析。**P0**。

### 检查 9：`with_session`、`session.begin()`、autobegin、commit/rollback 边界

**源码证据**：

`with_session` (`controllers/common/session.py:49-56`) 在 write 模式下：
```python
session = session_factory.create_session()
result = view(self, session, *args, **kwargs)
session.commit()  # 若 service 已在自己 begin() 内 commit，此为 no-op
```

`session.begin()` 是 B3 引入的非标准模式（官方的 `TenantService` 使用 `session.commit()` 直接提交，不使用 `begin()` context manager）。B3 文档确认：
- begin 前禁止任何 DB 查询（防 autobegin）
- begin 块内完成所有 DB 操作
- begin 正常退出时自动 commit，异常时自动 rollback
- `with_session` wrapper commit 在 begin 已提交后为 no-op

B4 计划 §10 沿用此模式。**本身可行**，但需确保：
- `import_app()` 调用不破坏事务边界（见 P0-1）
- 外部 I/O（Redis 锁、dependency preflight）在 begin 前完成

**结论**：PASS（若 P0-1 修复）。

### 检查 10：`AppDslService.import_app()`、`_create_or_update_app()`、`WorkflowService.sync_draft_workflow()` 内部 commit 追踪

已在 P0-1 和 P1-3 中完整追踪。关键发现：

- `import_app()`：不直接 commit，但调用 `_create_or_update_app()`
- `_create_or_update_app()`：不直接 commit，但通过 `workflow_service.sync_draft_workflow(commit=True)` 间接 commit
- `sync_draft_workflow(commit=True)`：**直接 `session.commit()`**（`workflow_service.py:386`）
- signals/hooks：`app_was_created` 和 `app_draft_workflow_was_synced` 的 handlers 用同一 session flush 或在独立 session 中操作
- Redis dependency state：`check_dependencies` 从 Redis key `app_check_dependencies:{app_id}` 读取，TTL 10 分钟

**结论**：VERIFIED。计划对内部 commit 的认知不足（见 P0-1）。

### 检查 11：普通 workflow import 是否通过 `sync_draft_workflow(commit=True)` 中途提交

**是的**。当 DSL 不含 `agent_packages` 时（`raw_agent_packages = data.get("agent_packages") or {}` 为空 dict，falsy），`commit=True` → `session.commit()` at `workflow_service.py:386`。

普通 marketplace snapshot（不含 Agent 特性）必然走此路径。

### 检查 12：计划所称 copy 原子 rollback 是否错误；应复用何种官方路径

**结论**：copy 原子 rollback 承诺**错误**，原因见 P0-1。

**应复用官方模式**：
- 预检 dependencies（已在计划中，在 import 前，零 DB 写入）
- 使用 plain `Session`（参考 `app_import.py:90`）+ 显式 commit/rollback
- 移除 post-import check（因为在 plain Session 下若 import FAILED 做 `session.rollback()` 是可靠的 — 前提是没有内部 commit）
- 但内部 commit 破坏了这一点，所以最佳方案是**只做预检**

### 检查 13：import 返回 FAILED/PENDING 时是否已产生 DB、Redis、signal 副作用

**源码证据**：

- **FAILED**：`app_dsl_service.py` 中 `import_app()` 在多个阶段可能返回 FAILED（版本不兼容、YAML 解析失败、`_create_or_update_app` 失败）。若失败在 `sync_draft_workflow` commit 之前，DB 副作用未被 commit。若失败在 commit 之后（如 post-sync 代码异常），DB 已持久化但返回 FAILED。官方 controller 在 FAILED 时调用 `session.rollback()`（`app_import.py:107`），但对已 commit 的数据无效果。
- **PENDING**：当 DSL 版本为未来版本时，import 存储 payload 到 Redis `app_import_info:{import_id}`（TTL 10 分钟），不做 DB 写入。官方 controller 做 `session.rollback()` 并返回 202（`app_import.py:107-108`）。
- **Signal 副作用**：`app_was_created` → InstalledApp/Site 创建。`app_draft_workflow_was_synced` → webhook/trigger 同步（独立 session，不可回滚）。

**结论**：PENDING 安全（无 DB 副作用）。FAILED 可能已产生不可回滚的副作用（取决于失败点在 commit 前后）。

### 检查 14：copy 后 dependency 二次检查失败时真能删除全部残留

**不能**。原因见 P0-1 和 P1-3。已持久化的 App/Workflow/InstalledApp/Site 无法通过 "rollback" 清除。Redis key best-effort 清理不触及 DB。

### 检查 15：`include_secret=False` 实际清除与保留

**源码证据**：

`export_dsl(app_model, session=session, include_secret=False)` 在 `app_dsl_service.py:579-636`：

清除的内容：
- workflow secret variable values（设为空字符串）
- tool/agent config 中的 `credential_id`
- webhook URL、trigger subscription 等运行绑定

可能保留的内容：
- 加密后的 dataset IDs（通过 `encrypt_export_doc_id` 加密）
- workflow node 的 provider/model 配置名称（不含 credentials）
- plugin marketplace/github 标识
- agent config 结构（不含 model credentials）
- environment_variables 的 key 名称（不含 value 如果 value_type=secret）
- 文件引用的 metadata（非实际文件内容）

**结论**：`include_secret=False` 清除了已知的 credential 和 secret 字段，但 B4 额外的 sanitizer 层（§9.4）是合理的 defense-in-depth，不应仅依赖 `export_dsl` 作为唯一安全证明。

### 检查 16：sanitizer 对各类敏感资源的判断

计划 §9.4 的 sanitizer 检查项覆盖面：secret variables、credentials、API keys、tokens、private keys、dataset_ids、file IDs、private plugins（Package type）、URL icons、未识别 credential-bearing 字段。

所有检查项都有明确的、可实现的技术标准。`IconType.LINK` 拒绝和 URL icon 检查是 fail-closed 设计（不认识的 = 拒绝）。这与官方 SSRF 保护策略一致。

**误报风险评估**：低。DSL 结构稳定，已识别字段的检查基于已知 schema。
**漏报风险评估**：中等。未来官方新增的 DSL 字段可能绕过（计划 P1 风险 #1 已识别），需版本化 validator。

**结论**：PASS with accepted risk。

### 检查 17：canonical YAML 再序列化对官方 DSL、hash 稳定性、导入语义的影响

已在 P1-4 中详述。

### 检查 18：dependencies 列与 DSL dependencies 的唯一事实来源

计划 §9.5：
> "从已校验 DSL 提取 dependencies，排序、去重并同时写入 DSL 与独立 JSON 列；两者不一致则拒绝。"

这建立了明确的 invariant：DSL 中的 dependencies 和 JSON 列中的 dependencies 必须一致，否则发布失败。这使得 JSON 列可以被快速索引查询（用于预检），而 DSL 是完整表示的单一事实来源。

**结论**：PASS。

### 检查 19：source App 删除后 copy 不查询 source 的方案

计划 §9 copy 规则：
> "不查询 source App，不检查 source App 是否存在"

这是正确的。snapshot 已冻结所有必要信息（`app_name`、`app_description`、`app_mode`、`app_icon`、`dependencies`）。`import_app()` 不需要 source App。

**结论**：PASS。测试应当通过 mock 证明没有 source App DB query。

### 检查 20：不设置 snapshot→asset FK、pointer→snapshot FK 的孤儿数据风险

已在 P2-1 中详述。

### 检查 21：回填方案评估

计划 §12 的回填设计：仅提供 service primitive（`backfill_legacy_snapshot`），runner 在 `/tmp` 不提交。评估：

- **独立**：是，与 migration 分离
- **可重试**：是，按 ID retry
- **有 inventory**：是，read-only inventory 步骤
- **dry-run**：是，`--dry-run` 参数
- **失败恢复**：中断后从 manifest 未完成 ID 继续

**不足**：
- runner 不提交（P2-3）
- 建议为 service primitive 本身写 focused unit test；实际的完整回填流程在 B8/隔离 PostgreSQL 副本执行

**结论**：PASS with caveat（P2-3）。

### 检查 22：版本化、受测试的 CLI/command 路径

计划未提及 CLI command。回填通过临时 runner 脚本执行，不通过 Flask CLI。若需要 CLI，应属于 B4-B（定义 `backfill_legacy_snapshot` service primitive）或 B8（实际执行脚本）。

**建议**：在 `scripts/enterprise/backfill_marketplace_snapshots.py` 中提供版本化的薄封装，导入 B4-B service 并暴露参数（asset_id, dry_run, expected_row_version）。

### 检查 23：回填失败时更新 snapshot_state 是否会改变 row_version

计划 §12.5：
> "失败只更新 snapshot state 为 source_missing/failed 和稳定 reason，不改旧 status、不删行"

未说明回填更新 `snapshot_state` 时是否递增 `row_version`。若递增，`expected_row_version` 在 retry 时会改变。若不变，则并发检测不生效（expected row_version 在两次失败间相同）。这是语义需要明确的点。

**要求修复**：明确回填操作是否修改 `row_version`：
- 若修改（推荐）：retry 时必须使用更新后的 `expected_row_version`，从 manifest 中读取实际失败后的 state
- 若不修改：retry 可以使用原始 `expected_row_version`，但无法检测到回填间的其他 mutation

### 检查 24：旧 approved 行升级后暂时隐藏

计划 §11.3 表格：旧 approved 行在回填前不可公开（`backfill_pending`）。copy/list/detail 均不可访问。这是有意的设计，在回填完成前这些资产对用户不可见。

**可接受性**：对于 1 行历史数据的本地 inventory，回填窗口极小。对于有大量历史 approved 行的环境，需要评估回填时长。计划将此列为 P1 风险 #3，评级合理。

**结论**：PASS with accepted planned downtime window。

### 检查 25：controller 精确 8 条 route、DTO、decorator 顺序和 Session 注入

已在汇总中确认 8 条 route 定义。

**Submit route decorator 顺序**（§7）：
```
setup_required, login_required, account_initialization_required, edit_permission_required, with_session, get_app_model
```

**验证**：`@with_session` 在 `@get_app_model` 之前（外层）。根据官方 `wraps.py:106-109`，`get_app_model` 通过 `_get_injected_session(args)` 检测 `with_session` 注入的 session。顺序正确。

DTO 数量：计划列出 10 个 DTO（7 个 request/query + 3 个 response）+ `MarketplaceErrorResponse`。与 B3 的 14 DTO 对比，B4 DTO 数量合理。

**结论**：PASS。

### 检查 26：submit route 中 `with_session` 与 `get_app_model` 确保同一 Session

**已验证**。`get_app_model` 的 `_get_injected_session()` 从 `args[1]` 获取 `with_session` 注入的 session。两者使用同一个 Session 对象。`get_app_model` 查询 App 后注入 `app_model` kwargs，handler 再将同一 session 传递给 service。

**结论**：PASS。

### 检查 27：B3 平台管理员 controller 注册后精确 7 route、无 DELETE

B3 源码确认 7 条 route（来自 B3_REVIEW.md 和独立检查）：
1. GET `/account/platform-admin-status`
2. GET `/platform-admin/workspaces`
3. GET `/platform-admin/workspaces/<uuid:workspace_id>`
4. PATCH `/platform-admin/workspaces/<uuid:workspace_id>`
5. GET `/platform-admin/workspaces/<uuid:workspace_id>/members`
6. POST `/platform-admin/workspaces/<uuid:workspace_id>/members/invitations`
7. PATCH `/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>/role`

无 DELETE。无 workspace create/delete/archive。无 owner mutation。

**结论**：PASS。B4 注册 B3 controller 后应保持此契约。

### 检查 28：OpenAPI/contracts 生成命令、allowlist、二次生成稳定性

Plan §13 指定：
```bash
pnpm --dir packages/contracts gen-api-contract
```

生成 allowlist 仅 `packages/contracts/generated/api/console/**`。生成后要求 `git diff` 无变化（二次运行确定性）。

**潜在问题**：
- 生成器可能产生浮动的排序（如 JSON key ordering）
- 第一次和第二次生成之间若有时间戳或随机元素，会破坏确定性

**要求修复**：B4-C 第一次生成后应保存 `git diff --name-only` 基准，第二次生成后验证 diff 为空。若不为空，需记录差异原因和生成器版本。

**结论**：PASS with verification requirement。

### 检查 29：generator 是否可能修改 `generated/api` 下非 console 文件

官方 `gen-api-contract` 命令可能生成 `packages/contracts/generated/api/` 下除 console 外的其他命名空间（如 openapi、webapp 等）。B4 计划 §13.3 说 "generated diff 必须仅在 `packages/contracts/generated/api/console/**`"。

若 generator 同时触发了其他命名空间的重新生成（即使是 formatting only），diff 将超出 allowlist。这不应阻止 B4-C（因为这不是 B4 引入的变化），但需要区分"B4 引入的变化"和"generator 自身的确定性波动"。

**要求修复**：B4-C 在首次生成前保存基线 `git diff --name-only`，生成后区分：
1. B4 引入（console/** 下的新 route/schema）
2. Generator 确定性波动（其他命名空间），若有则记录但不阻塞 B4-C

### 检查 30：B4-C 发现 B3 schema 缺陷的退回流程

计划 §13 末尾和 B3 Plan §9 定义了完整的退回流程：
1. B4-C 记录最小复现
2. 停止 B4-C
3. 工作区保持可审
4. 交回 B3 Fixer
5. B4 不编辑 B3 controller/service/libs/tests/config

**结论**：PASS。流程完整且可执行。

### 检查 31：MySQL 无意使用无法跨方言解析的类型

计划 §5.1 使用 `char(64)` 和 `varchar(32)` 等类型。MySQL 中 `CHAR` 填充行为不同。`JSON` 类型在 MySQL 5.7 中不原生支持（使用 `TEXT` 或 `LONGTEXT`）。CHECK 约束在 MySQL 8.0.16 以下被解析但忽略。

**但本轮发布阻断数据库为 PostgreSQL**。MySQL 仅为条件验证（Validation Plan Phase D）。计划中的类型选择对 PostgreSQL 是正确的。

**结论**：PASS（MySQL 不在本轮门禁范围）。若未来声明支持 MySQL，`CHAR(64)` → `VARCHAR(64)` 和 CHECK 约束的方言差异需单独评审。

### 检查 32：四起点 migration 测试覆盖率

Plan §16.2 定义四起点：
1. 空库 → 1.16
2. 官方 1.16 head → 企业 1.16
3. 旧企业 `e2f0a9b7c6d5` → 1.16
4. B2 merge head → 1.16

B4-A 仅执行静态 graph test（验证 revision 链和 head）。实际数据库迁移和四起点验证在 §16.2 隔离 PostgreSQL 副本/B8 执行。

**结论**：PASS。测试矩阵覆盖了静态和动态两个层面。B4-A 单元测试的范围（静态 graph）定义正确。

### 检查 33：操作审计日志、敏感日志限制、分页信息泄漏、错误内容泄漏

已在 P2-4 中详述。

### 检查 34：P1/P2 风险计数低估

计划声明 P1=3, P2=3。本审查发现：

| 分类 | 计划声明 | 实际 | 新增项 |
| --- | --- | --- | --- |
| P0 | 0 | **2** | 内部 commit 破坏 copy 原子性、deadlock 锁顺序 |
| P1 | 3 | **5** | +check constraint 风险、+row_version 语义 |
| P2 | 3 | **4** | +审计日志缺失、+回填 runner 不入库、+CHAR vs VARCHAR、+FK 孤儿 |
| **合计** | 6 | **11** | |

计划声明的风险（DSL 未来字段、Redis marker、回填隐藏、无 FK、分页漂移、shared lock 超时）在新发现面前显著低估。

### 检查 35：是否存在必须人工决定才能开始 B4-A 的问题

**是**。以下问题必须在 B4-A 开始前解决：

1. **P1-1（migration check constraint）**：B4-A 的 migration 代码直接受影响。必须在 B4-A Builder 接手前决定是使用方案 A（UPDATE 异常 status）、方案 B（不加 CHECK）、还是方案 C（NOT VALID）。
2. **P0-1（内部 commit）和 P0-2（deadlock）不阻碍 B4-A**，因为 B4-A 仅涉及 model/migration，不涉及 service 事务逻辑。但 B4-B 必须在 P0-1 和 P0-2 修正后才能开始。

**HUMAN_DECISION_REQUIRED**：选择 P1-1 的修复方案。

## 7. B4-A 启动判断

**允许启动 B4-A**，但附带以下硬性要求：

1. B4-A Builder 必须在 migration 中实现 P1-1 修复（处理未知 status 值）
2. B4-A Reviewer 必须在审查时验证 CHECK 约束不会在未知客户数据上升级失败
3. B4-B 不得在 P0-1（内部 commit）、P0-2（deadlock）、P1-3（不可回滚副作用）修正前开始
4. B4-B 任务单必须引用本审查接受后的计划修正 commit

## 8. 风险总结

### 已关闭

- B3 controller 精确 7 route、无 DELETE（已由 B3_REVIEW 验证）
- B4 精确 8 route 定义（plan §7 明确）
- B2 migration graph 正确（B2_REVIEW PASS）
- 官方 DSL export/import、session、signal 行为（本审查独立验证）

### 仍开放

| ID | 级别 | 描述 | 阻塞范围 | 建议方案 |
| --- | --- | --- | --- | --- |
| P0-1 | P0 | `import_app()` 内部 commit 破坏 copy 原子性 | B4-B, B4-C | 移除 post-import check，仅预检 |
| P0-2 | P0 | submit/review 锁顺序相反导致死锁 | B4-B, B4-C | 统一为 source App → asset 顺序 |
| P1-1 | P1 | `status` CHECK 约束对未知客户数据不安全 | B4-A | 方案 A: UPDATE 异常 status 后加约束 |
| P1-2 | P1 | `row_version` 语义模糊且无现有模式 | B4-B | 明确与 FOR UPDATE 分工 |
| P1-3 | P1 | post-import 副作用不可回滚（同 P0-1 根源） | B4-B | 同 P0-1 |
| P1-4 | P1 | canonical YAML 兼容性未验证 | B4-B | round-trip 测试 |
| P1-5 | P1 | Redis dependency 清理链路不完整 | B4-B | 移除 post-import check |
| P2-1 | P2 | 无物理 FK 孤儿风险 | B4-B 测试 | integrity 验证测试 |
| P2-2 | P2 | `CHAR(64)` vs `VARCHAR(64)` | B4-A | 改为 VARCHAR |
| P2-3 | P2 | 回填 runner 不入库 | B4-B / B8 | 提交到 scripts/ |
| P2-4 | P2 | 审计日志缺失设计 | B4-B | 补充审计事件表 |

## 9. 最终授权声明

- **结论**：**CHANGES_REQUIRED**
- **是否接受 B4_READY_WITH_CONDITIONS**：**不接受**。现有条件不足以安全启动全部 Builder
- **P0/P1/P2**：**2 / 5 / 4**
- **是否允许 B4-A**：**允许**，但必须在 migration 中修复 P1-1（CHECK 约束安全），且必须有人工决定选择修复方案
- **是否允许 B4-B**：**不允许**，必须等待 P0-1（内部 commit）和 P0-2（deadlock）在计划层面修正后
- **是否允许 B4-C**：**不允许**，等待 B4-B 解决后
- **HUMAN_DECISION_REQUIRED**：是 — 选择 P1-1 的三种修复方案之一（方案 A: UPDATE 异常 status 后加约束；方案 B: 不加 CHECK 仅应用层校验；方案 C: NOT VALID 约束 + 独立验证步骤）
- **唯一修改文件**：`docs/enterprise/replay-1.16.0/B4_IMPLEMENTATION_PLAN_REVIEW.md`

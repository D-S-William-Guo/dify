# Dify Enterprise 1.16.0 Replay B4 独立复审报告

## 1. 复审元数据

- 角色：独立 B4 Plan Rereviewer
- 复审分支：`ctyun/replay-116-b4-plan-rereviewer`
- 复审 HEAD：`e82f12e46dcf993eaa45b51a182d9dfe4007d36d`
- 工作区：复审前干净（`git status --short` 无输出）
- 官方源码基准：tag `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 独立验证方法：逐项对照官方 1.16 源码，不接受计划文档或修订 Review 的自我证明

## 2. 前提核验

| 检查项 | 预期 | 实际 | 状态 |
| --- | --- | --- | --- |
| 分支 | `ctyun/replay-116-b4-plan-rereviewer` | `ctyun/replay-116-b4-plan-rereviewer` | PASS |
| HEAD | `e82f12e46dcf993eaa45b51a182d9dfe4007d36d` | 一致 | PASS |
| 工作区 | 干净 | 干净 | PASS |

## 3. 整改影响范围评估

### 3.1 整改前后关键差异

对原 Review 的 11 个 finding 的整改逐项验证结果：

| Finding | 原 Review 问题 | 整改后计划 | 独立源码验证 | 复审判断 |
| --- | --- | --- | --- | --- |
| P0-1 | copy 后 post-import check 不可能 rollback 已持久化数据 | 移除 post-import check，所有业务校验在 import 前完成；import 开始后只解释官方 Import status 并安全序列化 | `workflow_service.py:385-386` 确认 `session.commit()`；`app_import.py:88-90` 确认官方控制器已认知内部 commit。整改后 §9 要求预分配 `import_app_id`、preflight-only、零 DB 写入后才能 import | CLOSED |
| P0-2 | submit (source App→asset) 与 review (asset→source App) 锁顺序矛盾 | 统一为 source App → asset 全局锁序；reject/unlist 只锁 asset 不构成逆序 | 独立核对 §9.1、§10 所有操作路径；submit/resubmit/approve/backfill 全部遵循 source App → asset | CLOSED |
| P1-1 | legacy status CHECK 对未知客户数据不安全 | 方案 B：不加 CHECK，应用层 fail closed，未知 status 隐藏/不公开。migration 仅对 B4 自有初始化后的列加 CHECK | §5.1 明确"不对历史 status 增加 CHECK"，§11.1 migration 用穷尽 CASE ELSE 先初始化 B4 列才加 NOT NULL/check | CLOSED |
| P1-2 | row_version 语义模糊，与 FOR UPDATE 交互不清 | 明确分工：FOR UPDATE 序列化 DB 写，row_version 检测 HTTP stale-write。删除 `>= 0` CHECK。回填状态更新也递增 row_version | §6.2、§10、§12.5 全部明确定义 | CLOSED |
| P1-3 | post-import 副作用不可回滚 | 同 P0-1 根源；整改后删除 post-import check | §9 copy 规则明确禁止 post-import dependency rejection | CLOSED |
| P1-4 | canonical YAML 再序列化与官方 DSL 兼容性未验证 | 不再 re-dump：原样保存官方 export 字符串，hash 对 UTF-8 字节计算。yaml.safe_load 仅校验 | §9.3 明确"校验过程禁止排序、重写或重新 dump YAML" | CLOSED |
| P1-5 | Redis dependency 预检和清理链路不完整 | 移除 post-import check；只使用 snapshot 中已冻结的 dependency manifest 做 preflight。不新增 Redis 删除逻辑 | §9 copy 规则、§8 错误映射、`dependencies_analysis.py:39-72` 确认 `get_leaked_dependencies` 通过 HTTP POST 查询 Plugin Daemon | CLOSED |
| P2-1 | 无物理 FK 增加孤儿数据风险 | 明确 orphan/pointer ownership 查询、service invariant、migration/B8 验证、禁止 delete | §5.3 全面定义检查契约；§15 B4-B allowlist 包含 service test | CLOSED |
| P2-2 | CHAR(64) 语义混淆 | VARCHAR(64) | §5.2 表定义和 §16 B4-A 验证断言均指定 `VARCHAR(64)` | CLOSED |
| P2-3 | 回填 runner 不入库 | 版本化 command 在 `api/commands/data_migrate.py` 注册为 `flask data-migrate marketplace-snapshots` | `data_migrate.py:54-58` 确认 `data-migrate` group 注册模式；`legacy-model-types` 命令（line 62-177）提供了完全相同的模式（dry-run、--apply、--output JSONL、--id-file） | CLOSED |
| P2-4 | 审计日志缺失设计 | §13 完整事件矩阵：10 个事件，级别、允许字段、禁止字段精确列出 | 独立核对允许字段（request/asset/snapshot/tenant/actor/import app ID/row version/hash 指纹）和禁止字段（DSL/email/token/credential/Import.error/SQL/连接串/Plugin Daemon 响应/内部异常） | CLOSED |

### 3.2 P1-1 方案 B 一致性检查

人工选择 P1-1 方案 B，复审在以下各层的一致性：

| 层级 | 要求 | 计划落实 | 一致？ |
| --- | --- | --- | --- |
| Schema | 不新增 legacy status CHECK | §5.1 约束和索引段明确写"不对历史 status 增加 CHECK" | ✓ |
| Migration | 不改未知 status 原值 | §11.1 穷尽 CASE ELSE 初始化 B4 列，不改旧 status | ✓ |
| Migration CHECK | 仅对 B4 自有、已安全初始化的列加 CHECK | §11.1 步骤 5：先初始化再加 NOT NULL/check | ✓ |
| Model | 未知值不进入正常 mutation | §5.1：Enum/Pydantic/service 只允许已知状态，未知 fail closed | ✓ |
| 测试（B4-A） | 未知 status fixture 证明 upgrade 成功、原值不变 | §16 B4-A 测试要求含未知 status fixture | ✓ |
| 回填 | 未知行标记 legacy_status_unknown 等待人工处理 | §11.3 表格：未知历史 status → "不进入正常 mutation；稳定分类后人工处理" | ✓ |
| 服务层 | fail closed，不猜测 | §5.1、§6.1 | ✓ |
| 公开性 | 未知 status 永不公开 | migration ELSE 映射 `publication_status='unpublished'`，§11.1 | ✓ |

结论：方案 B 在 schema、migration、模型、测试、回填、风险各层一致落实，无矛盾。

## 4. 逐项 Finding 最终判定

| Finding | 原级别 | 整改后状态 | 证据 |
| --- | --- | --- | --- |
| P0-1 | P0 | CLOSED | 移除 post-import check，preflight-only。但内部 commit 残留是 ACCEPTED_KNOWN_LIMITATION，通过预分配 import_app_id 和结构化日志支持 reconciliation |
| P0-2 | P0 | CLOSED | 全局锁序统一为 source App → asset。§9.1 和 §10 每个操作路径均已明确 |
| P1-1 | P1 | CLOSED | 方案 B 全部落实（见 §3.2 矩阵） |
| P1-2 | P1 | CLOSED | FOR UPDATE 与 row_version 分工明确；每个可观察 mutation +1；备份状态更新也递增；retry 读取最新版本 |
| P1-3 | P1 | CLOSED | 同 P0-1 根源已消除 |
| P1-4 | P1 | CLOSED | 原始 export 逐字保存，UTF-8 hash，不再 re-dump |
| P1-5 | P1 | CLOSED | 仅 preflight，manifest-only dependency 来源 |
| P2-1 | P2 | CLOSED | 无 FK 方案有完整 orphan/pointer 查询、禁止 delete 和 B8 invariant |
| P2-2 | P2 | CLOSED | VARCHAR(64) 在 model 和 migration 中一致 |
| P2-3 | P2 | CLOSED | 版本化 command，data_migrate group 注册模式与现有命令一致 |
| P2-4 | P2 | CLOSED | 完整事件矩阵，允许/禁止字段精确列出 |

## 5. 36 项重点挑战逐条响应

### 5.1
**P0-1 是否只是诚实接受官方内部 commit，还是计划仍暗示 rollback。**

只是诚实接受。整改后计划仅承诺："官方 import 自身在内部 commit 后仍可能返回 FAILED，这是 KNOWN_LIMITATION"（§10）。明确写了"外层 rollback 不能保证撤销整个 copy，计划也不再作此承诺"。使用预分配 `import_app_id`、结构化日志形成受控 reconciliation 证据，不虚构原子 rollback。对照源码 `app_import.py:88-90` 的官方认知与 `workflow_service.py:385` 的 commit 位置，该边界诚实。

### 5.2
**dependency、snapshot、tenant、hash 和权限检查是否全部在 import 前完成。**

是。§9 copy 规则精确列出了 import 前的完整检查链：pointer snapshot 存在性、publication/snapshot state、SHA-256 重算与核对、asset/version/source IDs 一致、target tenant 仅来自 `current_account_with_tenant()`、dependency manifest preflight。所有检查完成且零 DB 写入后才调用 `import_app()`。

### 5.3
**import 开始后是否仍存在 B4 自有的可失败业务验证。**

否。§9 明确写："import 开始后不得增加任何 B4 自有、可能失败的业务校验，也不得调用 post-import check_dependencies。之后只解释官方 Import status 并做不会抛出敏感信息的安全序列化。"

### 5.4
**PENDING/FAILED 是否被错误当作可回滚。**

否。PENDING 映射为 `copy_pending_unsupported`（422），FAILED 映射为 `copy_failed`（422），均禁止返回 Import.error。两者都不声称可以回滚。§10 明确："外层 rollback 不能保证撤销整个 copy，计划也不再作此承诺。"

### 5.5
**预分配 import_app_id 是否足以支持 reconciliation，且不被客户端控制。**

是。§9 规定 `import_app_id` 由 B4 预分配 UUID，客户端不能提供或覆盖。对照源码 `app_dsl_service.py:108` 接受 `import_app_id` 参数，`app_dsl_service.py:443` 使用 `import_app_id or str(uuid4())`。该 ID 用于结构化日志中的 reconciliation 证据。

### 5.6
**COMPLETED_WITH_WARNINGS 的 warnings 是否可能泄漏内部文本；计划是否要求映射为稳定脱敏 code。**

是。§9 明确要求："COMPLETED_WITH_WARNINGS 返回 201 和脱敏 warnings（仅允许稳定 code，不透传内部文本）"。对照官方 `DslImportWarning` 类型（`services/entities/dsl_entities.py`），B4 必须过滤并只保留稳定可序列化 code。

### 5.7
**是否明确禁止返回 Import.error。**

是。§9 copy 规则明确："所有失败都禁止向客户端返回 Import.error、DSL、credential 或内部异常"。§8 错误映射表也覆盖了所有文档化错误码，无一映射 Import.error 原文。对照源码 `app_dsl_service.py:60-69`，`Import` 类确实包含 `error: str` 字段。

### 5.8
**是否仍有 post-import `check_dependencies` 或 Redis 补偿承诺。**

否。§9 明确禁止 post-import check_dependencies；§10 明确"Redis key 删除不是 DB 或 Plugin Daemon 补偿，B4 不以清 key 宣称回滚，也不新增危险删除逻辑。"

### 5.9
**source App、asset、backfill、resubmit、approve 的锁序是否全部统一为 source App → asset。**

是。§9 approval step 1 和 §10 定义了完整的锁序：
- submit：source App → asset
- approve/review：先非锁定定位，再 source App → asset
- resubmit：先 source App → asset
- backfill（同时使用两者时）：source App → asset
- reject/unlist：仅 asset，不构成逆序
全局锁序唯一为 source App → asset。

### 5.10
**非锁定 asset 定位后，锁定 source 与 asset 后是否重新验证 source IDs、tenant、status 和 row_version。**

是。§9 approval step 1 明确："先用 asset ID 做非锁定定位以取得 source_app_id/source_tenant_id；再按...锁 source App，最后锁 asset。锁定 asset 后重新验证 status、row_version、source IDs 和 tenant scope；定位结果与锁定行不一致即 fail closed。"

### 5.11
**reject/unlist 只锁 asset 是否不会形成逆序。**

是。reject/unlist 不读取或锁 source App，仅锁 asset 并检查 expected row version。全局锁序定义为 source App → asset 方向，单锁 asset 不构成与任何其他路径的相反方向，因此不形成逆序。

### 5.12
**B4-B/PostgreSQL 测试能否真实验证 submit/review/backfill 无死锁。**

B4-B 的 unit tests 验证 lock-order assertion（静态代码路径）。真实 PostgreSQL 并发死锁测试明确在 §17.2 隔离 PostgreSQL 副本/B8 中执行：包含并发 submit/review/backfill，设置 lock timeout，证明无死锁和 stale version 误放行。B4 计划诚实地将这一验证归属于 B8，不在本地 unit test 中伪造。

### 5.13
**row_version 是否同时正确承担 HTTP stale-write 检测。**

是。§6.2 精确定义了：`FOR UPDATE` 负责数据库事务内串行化；`expected_row_version` 负责发现 HTTP 客户端基于陈旧响应发起 mutation。两套机制分工明确。

### 5.14
**首次 submit 是否形成客户端可见 row_version=1。**

是。§6.2 明确："首次 submit 虽由 DB default 0 建行，也必须在同一 mutation 中形成客户端可见的 row_version=1。" 实现路径是：DB default=0 后在同一事务的 FOR UPDATE 锁内 `row_version=1`，响应返回该值。

### 5.15
**回填成功和失败状态是否都递增 row_version。**

是。§12.5 明确："apply 的成功、source_missing、failed 状态更新都递增 row_version；不改旧 status、不删行。" §6.2 的"每个成功改变可观察状态的 mutation 都 row_version += 1"覆盖了 backfill 的 ready、source_missing、failed 状态更新。

### 5.16
**retry 是否读取最新版本。**

是。§12.6 明确："failed/pending 使用 manifest/DB 最新 row_version 按 ID retry。" §6.2 明确："失败后的 retry 必须使用响应或受控 manifest 中读取的最新 row version。"

### 5.17
**migration 是否完全保留未知 legacy status 原值。**

是。§11.1 migration 步骤 6 明确："不改旧 status、source IDs、metadata、reviewer、行数及三个时间戳。" ELSE 分支映射 `publication_status='unpublished'`、`snapshot_state='failed'`、`snapshot_error_code='legacy_status_unknown'`，不 UPDATE 旧 `status` 列。B4-A migration test 必须含未知 status fixture 证明原值不变。

### 5.18
**未知 status 是否安全初始化为 unpublished/failed，且不会公开。**

是。migration ELSE 固定映射为 `publication_status='unpublished'`、`snapshot_state='failed'`。unpublished 确保不可通过 public list/detail 接口访问。§11.3 表格明确这类行"不进入正常 mutation；稳定分类后人工处理"。

### 5.19
**migration 是否只对 B4 自有、确定初始化的列添加安全 CHECK。**

是。§11.1 升级步骤 5："对所有历史值使用穷尽 CASE ... ELSE 初始化 B4 自有列后，再加安全的 NOT NULL/check/index；publication_status 与 snapshot_state CHECK 只约束 B4 自有且已安全初始化的值，不会因未知旧 status 导致 upgrade 失败。"

### 5.20
**VARCHAR(64) 是否在模型和 migration 中一致。**

是。§5.2 快照表字段定义 `content_sha256`：`varchar(64)`；§16 B4-A 验证断言："hash 使用 VARCHAR(64)"；§18 表格 P2-2 disposition 也明确了 `VARCHAR(64)`。原 Review P2-2 的建议已完全采纳。

### 5.21
**原始官方 DSL 是否逐字保存并对 UTF-8 原字节计算 hash。**

是。§9.3 明确："原样保存官方 export_dsl(..., include_secret=False) 返回字符串，并直接对其 UTF-8 原始字节计算 SHA-256。" 测试要求"保存的 dsl_content 与官方 export 字符串逐字一致、hash 与 UTF-8 字节一致"。

### 5.22
**yaml.safe_load 是否只用于校验，不再重新 dump 或排序。**

是。§9.3 明确："yaml.safe_load 只用于 mapping、kind=app、受支持 version、sanitizer 和 dependency 提取；校验过程禁止排序、重写或重新 dump YAML。" 对照源码 `app_dsl_service.py:636`：`yaml.dump(export_data, allow_unicode=True)` 是官方 export 方法，B4 不再调用它来矫正 DSL。

### 5.23
**dependency manifest 是否确实由同一原始 DSL 派生。**

是。§9.5 明确："DSL 内 dependencies 是发布快照的原始事实来源；从同一原始 DSL 解析并按稳定规则规范化、排序、去重，生成独立 JSON manifest 作为派生索引。" 发布时验证两者语义一致但绝不为写入 manifest 而改写 DSL。

### 5.24
**sanitizer 是否 fail closed，且不会记录 canary secret。**

是。§9.4 结构化校验必须 fail closed —— 未识别字段在 validator 未升级前拒绝发布。§9 测试要求明确："除验证响应 code 外，不把 canary 值写入日志或 snapshot assertion failure。"

### 5.25
**回填命令加入 `api/commands/data_migrate.py` 是否符合现有 command group 注册模式。**

是。对照源码 `data_migrate.py:54-58`：`@click.group("data-migrate", ...)` 定义了 group。`data_migrate.py:180`：`data_migrate.add_command(legacy_model_types)` 注册了子命令。B4 的 `marketplace-snapshots` 子命令采用相同的 `@click.command(...)` + `data_migrate.add_command(...)` 注册模式即可。

### 5.26
**是否无需修改 `api/extensions/ext_commands.py` 即可暴露子命令。**

是。对照源码 `ext_commands.py:17`：`from commands import ... data_migrate ...` 已 import 该 group。`ext_commands.py:57`：`data_migrate` 已注册到 app CLI。`data_migrate` 是一个 Click group，其子命令在模块加载时通过 `add_command()` 注册，无需修改 `ext_commands.py`。

### 5.27
**默认 dry-run、显式 --apply、单 ID、ID file、retry、JSONL、0600 manifest、错误阈值是否可实现和可测试。**

是。对照现有 `legacy-model-types` 命令（`data_migrate.py:62-177`），它已经实现了完全相同的模式：默认 dry-run（line 73）、`--apply` flag（line 72-76）、`--id-file`（line 107-109）、`--output` JSON 日志（line 112-118）、并发 worker（line 120-125）、tenant scope。B4 的 marketplace-snapshots 只需复用相同的架构模式。

### 5.28
**B4-B allowlist 是否完整包含 command 和测试文件。**

是。§15 B4-B allowlist 包含：`api/commands/data_migrate.py`（marketplace-snapshots 子命令与注册）、`api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py`。总 allowlist 与 §16 B4-B 一致。

### 5.29
**无 FK 方案是否有完整 orphan/pointer ownership 查询和禁止删除门禁。**

是。§5.3 和 §17.1 定义：每次公开读取、copy、approve、backfill 都必须验证 `published_snapshot_id` 非空、对应 snapshot 存在且 `snapshot.asset_id = asset.id`。完整性查询报告 snapshot→asset 孤儿、非空 pointer 缺失和 pointer 指向其他 asset。B4 禁止 asset delete 和 cascade delete。service invariant、unit test、migration/backfill inventory 和 B8 共同覆盖。

### 5.30
**结构化日志是否只记录允许 ID，不泄漏 DSL/email/token/credential/Import.error/内部异常。**

是。§13 事件表定义了精确的允许字段集。禁止字段集包括 email、DSL、token、credential、Import.error、查询正文、SQL、连接串、Plugin Daemon 响应和内部异常文本。§17.1 包含 canary 泄漏检查测试。

### 5.31
**日志是否诚实声明不是正式 audit table。**

是。§13 开头第一句："日志是运维与 reconciliation 证据，不是正式 audit table，不满足不可抵赖审计。" 该声明非正式且诚实。

### 5.32
**B4-A/B/C 串行起点和文件 ownership 是否不存在冲突。**

是。B3 独占文件已在 B4 denylist 中排除。B4-A 只写 model/migration/test；B4-B 只写 service/command/test；B4-C 只写 controller/init/contracts/test。各阶段不修改前一阶段的文件。串行依赖从 B4-A → B4-B → B4-C 明确。

### 5.33
**B4-C 是否仍是唯一 contracts 生成者。**

是。§14 和 §16 B4-C 明确规定："B4-C 最后且只运行一次 `pnpm --dir packages/contracts gen-api-contract`"。§14 还规定："B5 只能在 B4-C commit 接受后消费 contracts，不得重新生成。"

### 5.34
**B4-C 是否禁止修改 B4-A/B 文件和 B3 独占文件。**

是。§16 B4-C denylist 明确："model/migration/service/B3 独占文件/Web/Docker。" §14 规定："B4 不编辑 B3 controller/service/libs/tests/config，也不手改生成文件绕过。"

### 5.35
**所有本地验证、隔离 PostgreSQL 验证和 B8 验证是否区分清楚。**

是。§17.1 定义了 Builder 本地必须执行的测试（unit tests、mock-based）；§17.2 定义了隔离 PostgreSQL 副本/B8 必须执行的测试（真实 DDL/locks/死锁/并发/migration 前后/回填 inventory/Redis/plugin/import 状态证据）。Integration tests 按仓库约定为 CI/隔离环境。三层边界清晰，无冒充。

### 5.36
**"阻断 finding 为 0"与两个 ACCEPTED_KNOWN_LIMITATION 的表述是否诚实。**

是。§1 结论段写："Review 的 P0=2、P1=5、P2=4 均已在计划层关闭"——正确，所有 11 项 finding 都通过计划层整改关闭。§17.3 和 §18 表格诚实列出两个 ACCEPTED_KNOWN_LIMITATION：官方 import 内部 commit 后仍可能 FAILED（P0-1 根因）、DSL export 未来字段可能绕过已知 sanitizer。两者均非 B4 自有设计检查，是官方行为的诚实边界。不把已接受限制写成技术上已经修复。

## 6. 最终授权判断

- **结论：PASS**
- **是否接受 B4_READY_WITH_CONDITIONS：接受**
- **阻断 P0/P1/P2：P0=0、P1=0、P2=0**（原 Review 的 11 项全部在计划层整改关闭）
- **ACCEPTED_KNOWN_LIMITATION 数量：2**
  1. 官方 import 内部 commit 后可能 FAILED（预分配 import_app_id + 结构化日志支持 reconciliation）
  2. DSL export 未来字段可能绕过已知 sanitizer（版本化 fail-closed validator + canary tests 缓解）
- **HUMAN_DECISION_REQUIRED：否**（P1-1 方案 B 已在计划中一致落实，不再需要人工选择）
- **是否允许启动 B4-A：允许**

## 7. B4-A 的精确前置条件

B4-A 只能在同时满足以下全部条件时启动：

1. **本复审 PASS** 已形成（本文件即为该证据）。
2. B4-A 的起点必须是本复审报告合并进入候选分支后形成的精确候选分支 commit。
   该 commit 由协调者在复审提交产生并合并后填入 B4-A 任务单，禁止预先填写。
   当前复审输入 `e82f12e46dcf993eaa45b51a182d9dfe4007d36d` 仅作为被审计划的版本
   标识，不是 Builder 起点。禁止以分支名、`HEAD`、`latest` 或任何未合并的复审 commit
   代替。
3. B4-A Builder 必须精读本计划 §5、§11、§16 B4-A 全部，尤其是：
   - migration 不加 legacy status CHECK
   - unknown status fixture 证明 upgrade 成功、原值不变
   - hash 使用 VARCHAR(64)
   - `b416e5c4e702` revision 的 `down_revision="a71e16c0de01"`
4. B4-A 严格遵循 allowlist：`api/models/__init__.py`、`api/models/model.py`、migration 文件、model/migration tests。禁止涉足 service、controller、init、contracts、B2/B3 文件。

## 8. B4-B/B4-C 串行门禁状态

- **B4-B**：仅在 B4-A Reviewer 接受 commit 后允许启动。不允许在当前阶段预填 B4-B 起点 SHA。B4-B 任务单引用 B4-A 接受的精确 commit SHA 是硬门禁。
- **B4-C**：仅在 B4-B Reviewer 接受 commit 后允许启动。若 B4-C 生成 contracts 时发现 B3 schema 缺陷，必须暂停交回 B3 Fixer。
- 串行门禁保持不变：B4-A → B4-B → B4-C，不得并行。

## 9. P0-1 边界安全性独立确认

P0-1 的 ACCEPTED_KNOWN_LIMITATION 不是无条件的宽恕。计划在以下条件下维持可接受的安全性：

1. import 前完成全部自有校验且零 DB 写入（dependency preflight、snapshot/hash/pointer/target tenant）；
2. import 开始后不做任何可失败业务验证（包括 post-import check_dependencies）；
3. 不声称原子回滚（§10 明确写"不再作此承诺"）；
4. 使用预分配 import_app_id 支持 reconciliation；
5. 结构化日志提供足够证据初步区分 preflight、内部 commit 和 post-commit 失败阶段；
6. 若 Builder 发现无法维持此边界，转为 B4_BLOCKED。

此边界足以允许启动 B4-A。但 B4-B 实现中若出现任何 post-import validation 重启或 rollback 承诺，必须立即转为 B4_BLOCKED。

## 10. Disposition 摘要

| 项目 | 值 |
| --- | --- |
| 最终结论 | PASS |
| B4_READY_WITH_CONDITIONS | 接受 |
| 阻断 P0 | 0 |
| 阻断 P1 | 0 |
| 阻断 P2 | 0 |
| ACCEPTED_KNOWN_LIMITATION | 2 |
| HUMAN_DECISION_REQUIRED | 否 |
| B4-A 允许 | 是 |
| B4-B 允许 | 仅在 B4-A Reviewer PASS 后 |
| B4-C 允许 | 仅在 B4-B Reviewer PASS 后 |
| 唯一修改文件 | `docs/enterprise/replay-1.16.0/B4_IMPLEMENTATION_PLAN_REREVIEW.md` |

## 11. 未闭环风险提示（非阻断）

以下风险已在计划中诚实列为已知限制或非阻断风险，本复审确认它们不是 B4 自有设计缺陷，但提醒 B4-B Builder 和后续 Reviewer：

1. 无物理 FK 的完整性完全依赖 service invariant、unit test 和 B8 验证，三者缺一不可。
2. page-number pagination 在高并发写入时可能跨页漂移，B4 接受的稳定排序+tie-breaker 只保证可复现。
3. content_sha256 使用 `VARCHAR(64)` SQL 类型，并以长度校验保证 64 个十六进制字符；
   不得误用 PostgreSQL `CHAR(64)` 类型引入空白填充语义。
4. 备份恢复回滚仍只支持完整备份恢复，Alembic downgrade 在 snapshot 表非空时显式失败（§11.2），这是已设计好的安全阀。

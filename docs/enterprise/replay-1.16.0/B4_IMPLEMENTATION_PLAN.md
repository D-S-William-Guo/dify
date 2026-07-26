# Dify Enterprise 1.16.0 Replay B4 智慧广场后端实施计划

## 1. 结论与边界

最终结论：**B4_READY_WITH_CONDITIONS**

B4 可以进入串行 Builder 阶段，但必须同时满足以下条件：

1. Builder 从本计划核验的基线 `925b01e9d2486bd230bffdb5f3ecb41b83bdf8e4`
   开始，不 merge、rebase、reset、cherry-pick 或复制旧企业实现。
2. B4-A、B4-B、B4-C 严格串行；后继 Builder 的任务单必须填写并核验前一阶段
   Reviewer 接受的精确 commit，禁止用分支名、`HEAD` 或未审工作树代替。
3. 复杂旧数据 DSL 回填不得进入 Alembic；它是 schema 部署后的独立、可 dry-run、
   可重试运维步骤，并且只能在隔离 PostgreSQL 副本先执行。
4. B4-C 生成 contracts 时若发现 B3 schema 缺陷，立即停止并交回 B3 Fixer；
   B4 不修改 B3 独占文件。
5. 本计划不授权数据库 migration、容器、Weaviate、volume、Docker、依赖或 Web 修改。

当前不需要产品/人工重新决定状态机或 API。需要人工执行的只是既有发布门禁：
批准各 Builder 的精确起点和 allowlist、批准隔离副本上的回填与 migration 演练。

风险计数：**P0=0，P1=3，P2=3**，详见 §16。

## 2. 当前基线和证据

### 2.1 强制起点

本次 Architect 开始时实际核验：

```text
branch: ctyun/replay-116-b4-architect
HEAD:   925b01e9d2486bd230bffdb5f3ecb41b83bdf8e4
status: clean
```

### 2.2 B2 migration graph

- B2 已逐字恢复 `c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5`。
- 空 merge `a71e16c0de01` 的 parents 精确为
  `("e2f0a9b7c6d5", "7a1c2d9e4b60")`，upgrade/downgrade 均为 `pass`。
- 当前源码图的唯一 B2 head 是 `a71e16c0de01`。
- B4 只能新增
  `2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py`；
  `revision="b416e5c4e702"`，`down_revision="a71e16c0de01"`。
- B4 完成后唯一 Alembic head 必须为 `b416e5c4e702`。

### 2.3 B2 只读 inventory

旧 PostgreSQL 15.17 的 `enterprise_marketplace_assets`：

- 16 列，1 行，状态为 `approved`；
- `source_app_id` 非空，来源 App 存在、tenant 匹配且状态 normal；
- 唯一约束 `unique_enterprise_marketplace_source_app(source_app_id)`；
- 索引 `(source_tenant_id)` 与 `(status, updated_at)`；
- 无外键；
- 实际 schema 与历史 migration `c8f3d9d4a1be` 一致。

因此 migration 不得重建表、删除行、重写原 16 列或改变旧
`source_app_id`、状态和时间戳。当前只有一行来源正常是已核实的本地 inventory，
不能被写成所有客户数据都来源正常。

### 2.4 B3 已合并代码

B3 Review 已接受以下实现：

- `api/libs/platform_admin.py` 的 `platform_admin_required`；
- 精确 7 条 route、14 个 DTO、6 个 service public method；
- 无 member DELETE、无 workspace create/delete/archive、无 owner mutation；
- controller 尚未在 `api/controllers/console/__init__.py` 注册；
- contracts 尚未生成。

B4 只负责 import/注册 B3 controller 并验证真实 Flask route，不修改
`api/libs/platform_admin.py`、`api/services/platform_admin_service.py`、
`api/controllers/console/platform_admin.py` 或 B3 测试/配置。

## 3. 官方 1.16 可复用能力

1. `AppDslService.export_dsl(app_model, session=session, include_secret=False)`：
   使用调用者显式 Session；workflow secret variable 值被清空；tool/agent
   `credential_id` 被移除；webhook URL、subscription 等运行绑定被清理；输出当前
   DSL version 与 dependencies。
2. `AppDslService(session).import_app(..., import_mode=ImportMode.YAML_CONTENT,
   yaml_content=snapshot)`：只从数据库中保存的快照复制，不走 URL fetch。
3. `DependenciesAnalysisService` 和 `PluginDependency`：解析、记录并检查目标
   workspace 缺失 plugin dependencies。
4. `controllers.common.session.with_session`：controller 注入 request-scoped
   Session；write handler 成功后 commit，异常 rollback。
5. `controllers.common.schema`、`fields.base.ResponseModel` 与 `dump_response`：
   Pydantic v2 request/query/response 和 Swagger 的唯一模式。
6. `setup_required`、`login_required`、`account_initialization_required`、
   `edit_permission_required` 与 B3 `platform_admin_required`：不建立平行授权。
7. `remote_fetcher`/官方 SSRF helper 已存在，但 B4 API 不接收 URL，也不执行网络
   获取，因此本实现禁止所有 marketplace 网络 fetch；未来若增加 URL，必须另行安全设计。

不能把 `include_secret=False` 当作唯一安全证明。发布还必须经过 §9 的结构化、
fail-closed 可移植性检查。

## 4. 旧实现仅作为需求与风险证据

旧 ref `origin/codex/enterprise-candidate-1.15.0-20260626` 证明：

- 业务需要 submit、本人提交、公开 list/detail/copy、平台 list/review/unlist；
- 旧状态值为 `pending/approved/rejected/unlisted`；
- 标题、描述、分类、tags、scenario、是否展示 workspace 名称需要保留；
- 旧实现曾在 copy 时动态 export 当前 source App，导致发布后修改/删除破坏复制；
- 旧实现使用全局 `db.session`、controller 旧 schema 注册模式，并在序列化时依赖
  source App；这些均不得复制；
- 旧实现的依赖泄漏结果和重复提交行为只作为测试输入，不是最终契约。

## 5. 最终数据模型

### 5.1 主表 `enterprise_marketplace_assets`

保留全部 16 个旧列，语义如下；未列出的默认值不得变化。

| 字段 | 类型 | nullable / default | 最终语义 |
| --- | --- | --- | --- |
| `id` | varchar(36) | NOT NULL | PK，保留旧值 |
| `source_tenant_id` | varchar(36) | NOT NULL | 来源 workspace 审计 ID，不设 FK |
| `source_app_id` | varchar(36) | NOT NULL | 来源 App 审计 ID，不设 FK |
| `submitter_account_id` | varchar(36) | NOT NULL | 最近提交者审计 ID，不设 FK |
| `reviewer_account_id` | varchar(36) | NULL | 最近审核/下架操作者，不设 FK |
| `status` | varchar(32) | NOT NULL / `pending` | moderation 状态，保留旧值 |
| `title` | varchar(255) | NOT NULL | 当前待审 metadata |
| `description` | text/LongText | NOT NULL / `''` | 当前待审 metadata |
| `category` | varchar(255) | NOT NULL / `General` | 当前待审 metadata |
| `tags` | JSON | NOT NULL | 当前待审规范化 tags |
| `scenario` | text/LongText | NOT NULL / `''` | 当前待审场景 |
| `allow_show_workspace_name` | boolean | NOT NULL / false | 当前待审展示选择 |
| `review_note` | text/LongText | NULL | 最近 moderation note |
| `created_at` | datetime | NOT NULL / CURRENT_TIMESTAMP | 原始首次提交时间，不重写 |
| `updated_at` | datetime | NOT NULL / CURRENT_TIMESTAMP | 最近主记录变更 |
| `reviewed_at` | datetime | NULL | 最近审核/下架时间 |

B4 migration 新增：

| 字段 | 类型 | nullable / default | 说明 |
| --- | --- | --- | --- |
| `publication_status` | varchar(32) | NOT NULL / `unpublished` | `unpublished/published/unlisted` |
| `published_snapshot_id` | varchar(36) | NULL | 当前公开快照 ID；审计软引用 |
| `next_snapshot_version` | integer | NOT NULL / `1` | 行锁内分配的下一快照版本 |
| `row_version` | integer | NOT NULL / `0` | 每次 mutation `+1`，DTO 乐观并发 |
| `snapshot_state` | varchar(32) | NOT NULL / `none` | `none/ready/backfill_pending/source_missing/failed` |
| `snapshot_error_code` | varchar(64) | NULL | 回填/校验稳定失败分类，不保存异常文本 |

约束和索引：

- 保留 PK、`unique_enterprise_marketplace_source_app(source_app_id)` 和两个旧索引；
- 新增 check：`status IN ('pending','approved','rejected','unlisted')`；
- 新增 check：
  `publication_status IN ('unpublished','published','unlisted')`；
- 新增 check：
  `snapshot_state IN ('none','ready','backfill_pending','source_missing','failed')`；
- 新增 check：`next_snapshot_version >= 1 AND row_version >= 0`；
- 新增索引
  `enterprise_marketplace_asset_publication_idx(publication_status, updated_at, id)`；
- 新增索引
  `enterprise_marketplace_asset_submitter_idx(source_tenant_id, submitter_account_id, updated_at, id)`；
- `published_snapshot_id` 不建 unique：历史恢复和逐步回填期间允许 NULL；service 保证一个
  snapshot 只属于一个 asset。

`status` 继续保留旧 `unlisted` 以兼容历史，但新代码的下架权威字段是
`publication_status`。对旧 unlisted 行两者均保持/映射为 unlisted；新下架不需要
破坏正在审核的 `status`。

### 5.2 追加式表 `enterprise_marketplace_asset_snapshots`

| 字段 | 类型 | nullable / default | 说明 |
| --- | --- | --- | --- |
| `id` | varchar(36) | NOT NULL | PK |
| `asset_id` | varchar(36) | NOT NULL | 主资产软引用 |
| `snapshot_version` | integer | NOT NULL | 每资产从 1 单调递增 |
| `dsl_content` | text/LongText | NOT NULL | canonical、无 secret YAML |
| `dsl_version` | varchar(32) | NOT NULL | YAML 顶层 `version` |
| `content_sha256` | char(64) | NOT NULL | UTF-8 canonical DSL 的 lowercase hex SHA-256 |
| `frozen_at` | datetime | NOT NULL | 审核通过冻结时间 |
| `source_app_id` | varchar(36) | NOT NULL | 冻结时来源 App 审计 ID |
| `source_tenant_id` | varchar(36) | NOT NULL | 冻结时来源 workspace ID |
| `source_tenant_name` | varchar(255) | NULL | 冻结时名称；仅按展示规则返回 |
| `submitter_account_id` | varchar(36) | NOT NULL | 此版提交者 |
| `reviewer_account_id` | varchar(36) | NOT NULL | 此版审核者 |
| `title` | varchar(255) | NOT NULL | 冻结展示 metadata |
| `description` | text/LongText | NOT NULL / `''` | 冻结 metadata |
| `category` | varchar(255) | NOT NULL / `General` | 冻结 metadata |
| `tags` | JSON | NOT NULL | 冻结 metadata |
| `scenario` | text/LongText | NOT NULL / `''` | 冻结 metadata |
| `allow_show_workspace_name` | boolean | NOT NULL / false | 冻结展示规则 |
| `app_name` | varchar(255) | NOT NULL | 从 DSL 冻结，不再读 source App |
| `app_description` | text/LongText | NOT NULL / `''` | 从 DSL 冻结 |
| `app_mode` | varchar(32) | NOT NULL | 从 DSL 冻结 |
| `app_icon_type` | varchar(32) | NULL | 只允许可移植 icon 类型 |
| `app_icon` | text/LongText | NULL | 冻结 icon 值 |
| `app_icon_background` | varchar(32) | NULL | 冻结 icon background |
| `dependencies` | JSON | NOT NULL | 排序、去重后的 `PluginDependency` JSON |

约束和索引：

- PK `(id)`；
- unique `enterprise_marketplace_snapshot_asset_version_uq(asset_id, snapshot_version)`；
- check `snapshot_version >= 1`；
- check `content_sha256` 为 64 字符；
- 索引 `(asset_id, frozen_at, id)` 和 `(content_sha256)`。

快照表是 append-only：B4 service 不提供 update/delete；审核通过只 INSERT，新发布只移动
主表 pointer。测试必须使任何“覆盖旧 snapshot”实现失败。

### 5.3 外键策略

不向 App、Tenant、Account 建数据库 FK。原因是这些是不可变发布的审计身份，来源
App/workspace/account 可能被删除，而历史资产与快照必须保留。

也不为 `asset_id`/`published_snapshot_id` 建物理 FK：历史表原本无 FK，双向指针会增加
migration 顺序和删除级联风险。service 在同一 Session 校验归属，删除主资产不是 B4 API；
一致性由 migration/unit/integration invariant tests 检查。禁止 cascade delete。

## 6. 状态机、重复操作与版本语义

### 6.1 枚举

- moderation `status`：`pending`、`approved`、`rejected`、`unlisted`（legacy only）。
- publication：`unpublished`、`published`、`unlisted`。
- snapshot state：`none`、`ready`、`backfill_pending`、`source_missing`、`failed`。

### 6.2 合法操作矩阵

| 操作 | 前置 | 结果 |
| --- | --- | --- |
| 首次 submit | 无 asset；source App 属于当前 workspace 且 normal | 创建 `pending/unpublished/none` |
| duplicate submit | 已 `pending` 且相同/不同 payload | 409 `submission_already_pending`，不静默覆盖 |
| resubmit | `approved/rejected/unlisted`；expected row version 匹配 | metadata 更新，`status=pending`；已 published 快照继续公开，已 unlisted 不自动重上架 |
| approve | `status=pending`；source 正常；expected row version 匹配 | 生成并 INSERT 新快照；status approved；publication published；state ready；pointer 前移 |
| reject | `status=pending`；expected row version 匹配 | status rejected；不创建快照；既有 published 版本保持公开 |
| repeat review | 非 pending | 409 `invalid_status_transition` |
| unlist | publication published；expected row version 匹配 | publication unlisted；快照/pointer 保留；不删除历史 |
| repeat unlist | publication unlisted | 409 `asset_already_unlisted` |
| copy | publication published、state ready、pointer 对应快照 | 只导入 pointer 快照 |

每次成功 submit/review/unlist 均 `row_version += 1`。review/unlist payload 必须传
`expected_row_version`；resubmit 也必须传。首次 submit 不传。版本不匹配返回
409 `stale_asset_version`。

审核通过在主资产 `FOR UPDATE` 锁内读取并递增 `next_snapshot_version`。同一
source App 的并发首次提交由 source App row lock + unique constraint 收敛，冲突映射
`concurrent_operation`。旧 published version 永不修改；新版本可使用相同 DSL hash，
因为 metadata、审核时间与版本仍是新的发布事件。

## 7. 精确 route、DTO 与权限契约

所有 route 位于 `/console/api`，表中为 namespace path。请求 DTO
`ConfigDict(extra="forbid")`；response 继承 `ResponseModel`。

| Method/path | Request | Response / status | decorator（外到内） |
| --- | --- | --- | --- |
| POST `/apps/<uuid:app_id>/enterprise-marketplace/submissions` | `MarketplaceSubmissionPayload` | `MarketplaceAssetResponse`, 201 | setup, login, account initialization, edit permission, with_session, get_app_model |
| GET `/enterprise-marketplace/submissions` | `MarketplaceMySubmissionListQuery` | `MarketplaceAssetPaginationResponse`, 200 | setup, login, account initialization, with_session(write=False) |
| GET `/enterprise-marketplace/assets` | `MarketplacePublicAssetListQuery` | `MarketplaceSnapshotPaginationResponse`, 200 | setup, login, account initialization, with_session(write=False) |
| GET `/enterprise-marketplace/assets/<uuid:asset_id>` | 无 | `MarketplaceSnapshotDetailResponse`, 200 | setup, login, account initialization, with_session(write=False) |
| POST `/enterprise-marketplace/assets/<uuid:asset_id>/copies` | `MarketplaceCopyPayload` | `MarketplaceCopyResponse`, 201 | setup, login, account initialization, edit permission, with_session |
| GET `/platform-admin/enterprise-marketplace/assets` | `MarketplaceAdminAssetListQuery` | `MarketplaceAssetPaginationResponse`, 200 | setup, login, platform admin required, platform admin current tenant required, account initialization, with_session(write=False) |
| POST `/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/reviews` | `MarketplaceReviewPayload` | `MarketplaceAssetResponse`, 200 | setup, login, platform admin required, platform admin current tenant required, account initialization, with_session |
| POST `/platform-admin/enterprise-marketplace/assets/<uuid:asset_id>/unlist` | `MarketplaceUnlistPayload` | `MarketplaceAssetResponse`, 200 | 同上 write |

DTO：

- `MarketplaceSubmissionPayload`：title 1..255、description/scenario max 5000、
  category 1..255、tags 最多 10 个且每个 1..64、`allow_show_workspace_name`、
  `expected_row_version: int | None`；首次提交必须为空，已有资产 resubmit 必须提供。
- `MarketplaceReviewPayload`：`decision: Literal["approved","rejected"]`、
  `review_note: str | None` max 5000、`expected_row_version: int >= 0`。
- `MarketplaceUnlistPayload`：`review_note: str | None` max 5000、
  `expected_row_version`。
- `MarketplaceCopyPayload`：空 DTO；目标 workspace 不可由 body/path/header 指定。
- list query：`page=1 ge1`、`limit=24 ge1 le100`；admin/my 默认 50；
  `keyword` trim max255；category；admin 可按 moderation/publication/snapshot state
  过滤。
- 排序仅允许 `updated_at_desc`（default）、`created_at_desc`、`title_asc`；
  SQL 始终追加 `id` 作为 tie-breaker。响应含 page/limit/total/has_more。
- public list/detail 返回当前 published snapshot 的冻结字段、版本、hash、frozen_at、
  dependencies；不返回 reviewer note、隐藏 workspace 名称或 source account IDs。
- admin/my response 返回 moderation/publication/snapshot state、row version、审计 ID
  和失败分类，但不返回 DSL 内容。
- copy response：`app_id`、`import_status`、`warnings`、snapshot version/hash；
  不返回 DSL、secret 或内部异常。
- 统一 `MarketplaceErrorResponse`：`code/message/status`。

本人提交列表的 scope 为当前 `tenant_id` 且 `submitter_account_id=current account`；
不因平台管理员身份扩大。source App submit 必须同时匹配 path App、当前 tenant 和
`get_app_model` 授权。

## 8. 错误映射

| error code | HTTP | 条件 |
| --- | ---: | --- |
| official unauthenticated | 401 | 未登录 |
| `permission_denied` / `platform_admin_required` | 403 | workspace 编辑权限或平台授权失败 |
| `invalid_request` | 400 | Pydantic/排序/过滤错误 |
| `asset_not_found` / `source_app_not_found` | 404 | 不存在或 tenant scope 不匹配；public 非公开也返回 404 |
| `submission_already_pending` | 409 | pending 重复提交 |
| `invalid_status_transition` | 409 | 非法审核状态 |
| `asset_already_unlisted` | 409 | 重复下架 |
| `stale_asset_version` | 409 | expected row version 不匹配 |
| `concurrent_operation` | 409 | unique/锁竞争或重检失败 |
| `source_app_unavailable` | 409 | 审核时来源删除、跨 tenant 或非 normal |
| `snapshot_not_ready` | 409 | 旧 approved 尚未回填或 backfill failed |
| `snapshot_integrity_error` | 409 | hash/owner/version invariant 不符 |
| `snapshot_contains_secret` | 422 | 发布校验发现 secret/credential/token |
| `nonportable_resource_reference` | 422 | workspace 私有资源或外链 icon |
| `private_plugin_dependency` | 422 | package/private plugin 不能跨 workspace |
| `dependency_unavailable` | 409 | 目标 workspace 缺少声明依赖；无 App 被创建 |
| `copy_failed` | 422 | snapshot DSL import failed/pending；内部细节不回显 |

controller 只捕获 Pydantic validation 并把 domain/service error 映射为
`MarketplaceHTTPError(BaseHTTPException)`；不得直接 SQLAlchemy、abort 或泄漏
`Import.error`/异常文本。每个 documented error response 注册
`MarketplaceErrorResponse`。

## 9. 不可变、无 secret、可移植 DSL 快照

审核通过的固定顺序：

1. 在 service-owned transaction 中锁 asset，再按
   `(App.id=source_app_id, App.tenant_id=source_tenant_id)` 锁 source App；要求 normal。
2. 精确调用：

   ```python
   AppDslService.export_dsl(
       app_model=source_app,
       session=session,
       include_secret=False,
   )
   ```

3. `yaml.safe_load` 后要求 mapping、`kind=app`、version 为当前受支持字符串，重新用
   canonical dumper 输出 UTF-8 YAML；hash 对 canonical 字节计算。
4. 结构化校验必须 fail closed：
   - workflow `value_type=secret` 的 value 必须为空；
   - 所有 tool/agent/model config 不得含 `credential_id`、credentials、API key、
     bearer/token/private key 等 credential-bearing 字段；
   - webhook/debug URL、trigger subscription 等运行绑定必须为空；
   - 不得含 tenant/workspace/account credential IDs；
   - knowledge `dataset_ids`、私有 file/upload IDs 或其他 owner-bound resource ID
     必须为空；本轮不尝试跨 workspace 映射；
   - plugin dependency 类型 `Package` 拒绝；Marketplace/GitHub 只记录公开标识和版本，
     不保存安装凭据；
   - `IconType.LINK` 与任何需要网络拉取的内容拒绝；B4 不发 HTTP；
   - 未识别的 credential/resource-bearing DSL 字段在 validator 未升级前拒绝发布。
5. 从已校验 DSL 提取 dependencies，排序、去重并同时写入 DSL 与独立 JSON 列；
   两者不一致则拒绝。
6. 插入 snapshot、更新主表 pointer/state/version；绝不 UPDATE 旧 snapshot。

测试使用 canary credentials、secret variables、API keys/tokens、私有 plugin
credentials、knowledge IDs、file IDs 和 URL icon；除验证响应 code 外，不把 canary
值写入日志或 snapshot assertion failure。

复制固定规则：

- 只锁并读取 `publication_status=published`、`snapshot_state=ready` 的 pointer snapshot；
- 重新计算 SHA-256 并核对 asset/version/source IDs；
- 不查询 source App，不检查 source App 是否存在；
- target tenant 只能来自 `current_account_with_tenant()`，且 `account.current_tenant_id`
  必须与之相同；body 不接受 tenant ID；
- 用 snapshot dependencies 对目标 tenant 预检；缺失时 409，零 DB 写入；
- 调用 `AppDslService(session).import_app(account=caller,
  import_mode=ImportMode.YAML_CONTENT, yaml_content=snapshot.dsl_content, ...)`；
- 仅接受 completed/completed-with-warnings 且 app_id 属于当前 tenant；pending/failed
  均 rollback 并返回稳定错误；
- import 后再次 `check_dependencies`；出现 leaked dependency 则 rollback，清理本次
  import 对应的短期 dependency Redis key（best effort、仅使用本次新 app ID），返回
  `dependency_unavailable`；
- 不允许客户端覆盖已有 app_id/import_app_id。

发布后 source App 修改或删除不会改变 snapshot；copy 路径的测试必须使任何 source
App query 直接失败，从而证明没有动态回读。

## 10. Session、事务和并发

- controller 通过 `with_session` 注入唯一 Session，只做 DTO、service 调用、序列化。
- read service 只使用该 Session；write public method 在首个 DB query 前进入
  `with session.begin():`，不调用会内部 commit 的 service。
- submit：锁 source App；查询/锁 asset；首次 unique race 映射 409。
- review：锁 asset 后锁 source App；export、校验、snapshot INSERT、pointer/state 更新
  在同一事务。校验失败 rollback，不留下部分 snapshot。
- reject/unlist：锁 asset，检查 expected row version 后 mutation。
- copy：用 PostgreSQL shared row lock使多个 copy 可并发、unlist 等更新等待；导入和
  新 App 创建在同一事务。数据库外 plugin/Redis 调用必须在写入前预检；失败不产生 App。
- 固定锁顺序均为 asset → source App；submit 只有 source App → asset，因此 review 不得
  同时等待 source lock 后回取另一 asset。并发 PostgreSQL 测试验证无死锁。
- `with_session` handler 返回后的 commit 只有 no-op；有效业务 commit/rollback 由 service
  transaction 所有。禁止隐式 `db.session` 和第二 Session。
- copy 的 plugin preflight 是外部 I/O，可能在 shared lock 下延长事务；设置明确 service
  timeout，超时映射 dependency unavailable，不无限等待。

## 11. Migration 与旧数据

### 11.1 upgrade

Alembic 只执行确定性 schema 和轻量状态初始化：

1. create snapshot table；
2. add 六个主表列（先 nullable/带 server default，兼容已有行）；
3. 仅用 SQL `CASE` 初始化：
   - old `approved` → publication `unpublished`、snapshot `backfill_pending`；
   - old `unlisted` → publication `unlisted`、snapshot `none`；
   - pending/rejected → publication `unpublished`、snapshot `none`；
4. `next_snapshot_version=1`、`row_version=0`；
5. 加 NOT NULL/check/index；
6. 不改旧 status、source IDs、metadata、reviewer、行数及三个时间戳。

migration 禁止 import 应用 service、export DSL、访问 Redis/plugin/network、逐行解析复杂
DSL、删除来源丢失记录或猜测状态。

### 11.2 downgrade

downgrade 仅允许在未发布环境做 schema reversal：

- 先 drop 新索引/check/列，再 drop snapshot table；
- 旧 16 列及其数据保持；
- 若 snapshot table 非空或任一 `published_snapshot_id` 非空，downgrade 必须显式失败，
  防止静默丢失发布数据。

生产回滚仍严格使用完整备份恢复，不把 Alembic downgrade 当作支持的回滚方法。

### 11.3 旧数据分类

| 来源情况 | Alembic 后 | 独立回填 |
| --- | --- | --- |
| normal 且 tenant 匹配 | approved 保留，隐藏 | 生成 snapshot v1；成功后 published/ready |
| source 已删除 | 行保留，隐藏 | `source_missing`；不造 DSL，不删除 |
| source 异常状态 | 行保留，隐藏 | `failed`，reason 分类 `source_unavailable` |
| tenant 不匹配/重复异常 | 行保留，隐藏 | `failed`，需人工 inventory |
| old approved 无 snapshot | 必为 backfill_pending | 回填成功前 list/detail/copy 都不可公开 |
| pending/rejected/unlisted | 原 status 保留 | 默认不 export；报告 inventory，后续正常 resubmit/review |

## 12. 独立回填步骤

回填不是 migration。B4-B 在 service 中提供一个仅供受控运维调用的
`backfill_legacy_snapshot(asset_id, dry_run, expected_row_version)`，但不新增公开 HTTP
route。实际 runner 使用 `/tmp` 中不提交仓库的一次性、审阅过的调用脚本，逐 ID 调用；
不得把连接串、DSL 或 secret 输出到命令行/日志。

执行协议：

1. read-only inventory 输出 count by status/snapshot state/source classification，不输出 DSL；
2. `--dry-run` 对每行做 source scope、export、sanitizer、dependency/hash 验证，但不写 DB；
3. 保存结构化 manifest：asset ID、旧状态、source 分类、预期 version、结果 code、hash 指纹前
   12 位；权限 0600；
4. apply 每资产一个 transaction，`FOR UPDATE` + expected row version；成功写 v1 并发布；
5. 失败只更新 snapshot state 为 source_missing/failed 和稳定 reason，不改旧 status、不删行；
6. 重跑时 ready 行校验 hash 后 skip；failed/pending 可按 ID retry；同 asset/version unique
   防重复；
7. 中断后从 manifest 的未完成 ID 继续；错误阈值触发停止；
8. 隔离副本先验证总行数、状态、source IDs、时间戳和抽样 hash，再申请生产窗口；
9. 恢复只用升级前备份；不自动删除 snapshot 或 downgrade。

本地 Builder 只测试 service/dry-run contract，不连接真实数据库。B8/隔离 PostgreSQL 副本才
执行实际 inventory、dry-run/apply/恢复演练。

## 13. B3 注册与最终 contracts

`api/controllers/console/__init__.py` 只做两项显式 import：

```python
from . import enterprise_marketplace, platform_admin
```

并在 `__all__` 加两个模块名。不得复制 resource、动态扫描或改 namespace path。

注册后的真实 Flask route test 从 app `url_map` 过滤 `/console/api`：

- B3 精确得到 §2.4 的 7 个 method/path pair；
- member path 没有 DELETE；
- workspace create/delete/archive、owner mutation、password、break-glass route 不存在；
- B4 精确得到 §7 的 8 个 method/path pair；
- 对不存在的 DELETE 真实 request 返回 router 404/405。

B4-C 最后且只运行一次：

```bash
pnpm --dir packages/contracts gen-api-contract
```

生成前保存 `git diff --name-only`；生成后：

1. 禁止手改 `packages/contracts/generated/**`；
2. OpenAPI JSON/YAML 先断言 B3 7 + B4 8 routes/schema；
3. generated diff 必须仅在 `packages/contracts/generated/api/console/**`；
4. 将 base 与 generated spec 做 path/schema semantic diff，新增只能是 B3+B4；排序/格式化
   噪音须由生成器重跑可复现；
5. 清理生成器临时 openapi 输出若它不属于允许提交路径；
6. 第二次运行生成命令后 `git diff` 不再变化，证明 deterministic。

若生成失败或暴露 B3 DTO/response/schema 缺陷：记录最小复现、停止 B4-C、工作区保持可审，
交回 B3 Fixer。B4 不编辑 B3 controller/service/libs/tests/config，也不手改生成文件绕过。
B5 只能在 B4-C commit 接受后消费 contracts，不得重新生成。

## 14. 文件 allowlist / denylist

### B4 总 allowlist

- `api/controllers/console/__init__.py`
- `api/models/__init__.py`
- `api/models/model.py`
- `api/controllers/console/enterprise_marketplace.py`
- `api/services/enterprise_marketplace_service.py`
- 经 Reviewer 预先批准、且只服务 B4 的
  `api/services/errors/enterprise_marketplace.py` 或 controller-local error/DTO
- `api/tests/unit_tests/models/test_enterprise_marketplace.py`
- `api/tests/unit_tests/services/test_enterprise_marketplace_service.py`
- `api/tests/unit_tests/controllers/console/test_enterprise_marketplace.py`
- `api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py`
- 必要的 container integration test，路径在 Builder 开始前精确登记
- `api/migrations/versions/2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py`
- `packages/contracts/generated/api/console/**`（仅 B4-C generator）

### 总 denylist

- B2 四个 migration；
- `api/libs/platform_admin.py`
- `api/services/platform_admin_service.py`
- `api/controllers/console/platform_admin.py`
- B3 独占 tests/config；
- `web/**`、`docker/**`、`docker/volumes/**`、`dify-agent/**`；
- 依赖、lockfile、版本号；
- `packages/contracts` 非 generated console 文件；
- 真实数据库、Redis、Weaviate、容器和 volume。

出现未登记文件立即停止；若实现证明必须修改 denylist，结论转为
`B4_BLOCKED` 或 `HUMAN_DECISION_REQUIRED`，不得扩 scope。

## 15. Builder 拆分与串行 handoff

推荐拆为三个严格串行 Builder；不得并行修改 model/service/controller/contracts。

### B4-A：schema/model/migration

- 精确起点：`925b01e9d2486bd230bffdb5f3ecb41b83bdf8e4`。
- allowlist：model 两文件、最终 migration、model/migration focused tests。
- denylist：service/controller/init/contracts、B2/B3/Web/Docker。
- 交付：§5/§11 完整 schema、model、migration graph tests。
- 测试：

  ```bash
  uv run --project api pytest \
    api/tests/unit_tests/models/test_enterprise_marketplace.py \
    api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py
  uv run --project api flask db heads
  ```

- handoff：Reviewer 接受 commit、DDL 摘要、唯一 head、NOT_RUN、四起点隔离 DB 计划。

### B4-B：domain/service/state/snapshot/backfill primitive

- 精确起点规则：任务单必须填入“B4-A Reviewer 接受的单一 commit SHA”；该 SHA 在 B4-A
  完成前客观不存在，禁止预填、用 `HEAD` 或分支名替代。起点不满足则不得启动。
- allowlist：enterprise marketplace service、专用 error/domain 文件、service tests。
- denylist：model/migration/controller/init/contracts、B3/Web/Docker。
- 依赖：只能在 B4-A review PASS 后开始。
- 交付：§6、§8–§12 service、sanitizer、copy、backfill primitive。
- 测试：

  ```bash
  uv run --project api pytest \
    api/tests/unit_tests/services/test_enterprise_marketplace_service.py
  ```

- handoff：接受 commit、public method/exception 清单、状态矩阵、session/lock 证据、
  sanitizer fixtures、NOT_RUN。

### B4-C：controller/注册/contracts/integration source tests

- 精确起点规则：任务单必须填入“B4-B Reviewer 接受的单一 commit SHA”；不得预填符号值。
- allowlist：enterprise controller、console init、controller/route/contract tests、
  generated console contracts。
- denylist：model/migration/service/B3 独占文件/Web/Docker。
- 依赖：B4-B review PASS。
- 交付：8 条 B4 route、B3+B4 注册、真实 route tests、唯一 final contracts。
- 测试：

  ```bash
  uv run --project api pytest \
    api/tests/unit_tests/controllers/console/test_enterprise_marketplace.py \
    api/tests/unit_tests/controllers/console/test_platform_admin.py \
    api/tests/unit_tests/commands/test_generate_swagger_specs.py \
    api/tests/unit_tests/controllers/test_swagger.py
  pnpm --dir packages/contracts gen-api-contract
  pnpm --dir packages/contracts test
  pnpm --dir packages/contracts type-check
  ```

- handoff：接受 commit、B3 7/B4 8 route manifest、无 DELETE 证据、OpenAPI semantic diff、
  generated file list、二次生成无 diff、NOT_RUN。

由于后两阶段 commit 尚未产生，本计划不能诚实地伪造其 SHA；“先 review、再把接受 SHA
写入下一任务单”是启动硬门禁。这也是采用 `B4_READY_WITH_CONDITIONS` 而非 `B4_READY`
的原因之一。最终 contracts 只能由 B4-C 生成。

## 16. 测试矩阵、验证地点与风险

### 16.1 Builder 本地必须执行

- tenant scope、admin/non-admin、DTO extra forbid、稳定 error body；
- 完整状态转换和非法状态；
- duplicate/concurrent submit 的 mock/unique mapping；
- source App 修改/删除后 copy 不查询 source；
- canary secret、credential、token、private plugin、workspace resource 被拒；
- hash/version/frozen_at、append-only snapshot；
- target workspace 只来自 current caller；
- rollback/exception injection、显式 Session、controller 无 SQLAlchemy；
- dependency manifest/leak/missing 语义；
- B3 精确 7 routes、无 DELETE/延期高风险 routes；
- B4 精确 8 routes；
- contract generation、semantic generated diff、二次生成稳定；
- static migration graph 唯一 `b416e5c4e702`；
- `git diff --check` 与 scope checker。

### 16.2 隔离 PostgreSQL 副本/B8 必须执行

- 四起点：空库、官方 1.16 head、旧企业 `e2f0a9b7c6d5`、B2 merge head；
- 实际 DDL/check/index/unique、row/shared locks、并发 approve/unlist/copy、死锁测试；
- migration 前后旧表行数/status/source_app_id/created/updated/reviewed 时间；
- 回填 inventory → dry-run → apply → retry → failure recovery；
- 来源 normal/deleted/abnormal/tenant mismatch fixture；
- 旧 approved 无 snapshot 在回填前隐藏，回填后可复制；
- Redis/plugin dependency integration 和失败残留清理；
- 官方 import 创建 App 的完整 transaction/rollback；
- A workspace 提交、admin 审核、B current workspace 复制并运行；
- 备份恢复回滚；不得在实际 volume 原地演练。

Integration tests 按仓库约定为 CI/隔离环境，不冒充本地已运行。MySQL 仅在将来声明支持时
条件执行；本轮发布阻断数据库为 PostgreSQL。

### 16.3 风险

P1：

1. DSL export 的未来字段可能绕过已知 sanitizer；以版本化、fail-closed validator 和 canary
   tests 缓解。
2. App import 同时涉及 Redis dependency marker；DB rollback 不能自动回滚 Redis，必须用本次
   app ID best-effort 清理并在隔离环境验证。
3. 旧 approved 行在独立回填前不可公开，升级窗口存在功能暂时不可用；通过 inventory、
   dry-run、分批重试和明确发布门禁控制。

P2：

1. 无物理 FK 依赖 service invariant；这是为保留来源删除后的历史而接受的限制。
2. page-number pagination 在高并发写入时可能跨页漂移；稳定排序/id tie-breaker 可复现顺序，
   B5 首版接受。
3. shared lock 下 dependency preflight 可能延长 copy transaction；以 timeout、多个 copy 共享锁
   和 PostgreSQL integration test 控制。

## 17. 人工门禁与最终验收

人工/Reviewer 必须确认：

1. 每阶段精确起点与 diff allowlist；
2. B4-A/B/C 串行 review PASS；
3. 隔离 PostgreSQL 备份、migration 和回填窗口；
4. 旧数据 inventory 没有未解释的数据减少；
5. B3 schema defect 不由 B4 越权修复；
6. generated contracts 只来自 B3+B4 且未手改；
7. B5 只消费 B4-C 接受 commit。

在这些条件满足前不得声称 runtime upgrade、旧数据回填或生产发布完成。

**最终结论：B4_READY_WITH_CONDITIONS**

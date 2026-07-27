# Dify Enterprise 1.16.0 Replay B4 智慧广场后端实施计划

## 1. 结论与边界

最终结论：**B4_READY_WITH_CONDITIONS**

B4 可以进入串行 Builder 阶段，但必须同时满足以下条件：

1. B4-A 只能在本修订计划复审 PASS 后，从 Reviewer 指定的精确接受 commit
   开始；不得沿用本文历史 Architect commit 作为实现起点，不 merge、rebase、reset、
   cherry-pick 或复制旧企业实现。
2. B4-A、B4-B、B4-C 严格串行；后继 Builder 的任务单必须填写并核验前一阶段
   Reviewer 接受的精确 commit，禁止用分支名、`HEAD` 或未审工作树代替。
3. 复杂旧数据 DSL 回填不得进入 Alembic；它由仓库内版本化、可测试、默认 dry-run 的
   `flask data-migrate marketplace-snapshots` 命令执行，并且只能先在隔离 PostgreSQL
   副本演练。
4. B4-C 生成 contracts 时若发现 B3 schema 缺陷，立即停止并交回 B3 Fixer；
   B4 不修改 B3 独占文件。
5. 本计划不授权数据库 migration、容器、Weaviate、volume、Docker、依赖或 Web 修改。

当前不需要产品/人工重新决定状态机或 API。需要人工执行的只是既有发布门禁：
批准各 Builder 的精确起点和 allowlist、批准隔离副本上的回填与 migration 演练。

Review 的 **P0=2、P1=5、P2=4 均已在计划层关闭**；唯一保留项是 P0-1 所揭示的
官方 import 内部提交残留风险，按 `ACCEPTED_KNOWN_LIMITATION` 管理，不再虚构原子回滚。
finding disposition 见 §18。

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
- **不**对历史 `status` 增加 CHECK；不 UPDATE、规范化、删除或猜测任何未知历史值；
  Enum/Pydantic/service 只允许已知状态进入正常 mutation，未知值 fail closed 并分类为
  `legacy_status_unknown` 等待人工处理；
- 新增 check：
  `publication_status IN ('unpublished','published','unlisted')`；
- 新增 check：
  `snapshot_state IN ('none','ready','backfill_pending','source_missing','failed')`；
- 新增 check：`next_snapshot_version >= 1`；删除无实际并发保护价值的
  `row_version >= 0` CHECK；
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
| `dsl_content` | text/LongText | NOT NULL | 官方 export 原字符串、无 secret YAML |
| `dsl_version` | varchar(32) | NOT NULL | YAML 顶层 `version` |
| `content_sha256` | varchar(64) | NOT NULL | 官方 export 原字符串 UTF-8 字节的 lowercase hex SHA-256 |
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
migration 顺序和删除级联风险。每次公开读取、copy、approve 和 backfill 都必须验证：
`published_snapshot_id` 非空、对应 snapshot 存在且
`snapshot.asset_id = asset.id`；完整性查询还必须报告 snapshot→asset 孤儿、非空 pointer
缺失以及 pointer 指向其他 asset。service invariant、unit test、migration/backfill
inventory 和 B8 PostgreSQL 验证共同覆盖。B4 禁止 asset delete 和 cascade delete；
未来新增任何删除能力必须重新做 schema、保留和级联评审。

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

`FOR UPDATE` 负责数据库事务内串行化；`expected_row_version` 负责发现 HTTP 客户端基于
陈旧响应发起 mutation。service 必须先按统一锁序锁行，再比较 expected/current version。
每个成功改变可观察状态的 mutation 都 `row_version += 1`，包括 submit/resubmit、
approve/reject/unlist，以及 backfill 的 ready、source_missing、failed 等
`snapshot_state` 更新。review/unlist/resubmit 必须传版本，首次 submit 不传；失败后的
retry 必须使用响应或受控 manifest 中读取的最新 row version。版本不匹配返回
409 `stale_asset_version`。首次 submit 虽由 DB default 0 建行，也必须在同一 mutation
中形成客户端可见的 `row_version=1`。

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
| `dependency_unavailable` | 409 | 目标 workspace 缺少声明依赖；import 未开始、无 App 被创建 |
| `dependency_service_unavailable` | 503 | dependency preflight timeout/Plugin Daemon 不可用；import 未开始 |
| `copy_pending_unsupported` | 422 | 官方 import 返回 PENDING，不视为成功 |
| `copy_failed` | 422 | 官方 import 返回 FAILED；内部细节不回显 |

controller 只捕获 Pydantic validation 并把 domain/service error 映射为
`MarketplaceHTTPError(BaseHTTPException)`；不得直接 SQLAlchemy、abort 或泄漏
`Import.error`/异常文本。每个 documented error response 注册
`MarketplaceErrorResponse`。

## 9. 不可变、无 secret、可移植 DSL 快照

审核通过的固定顺序：

1. 先用 asset ID 做非锁定定位以取得 `source_app_id/source_tenant_id`；再按
   `(App.id=source_app_id, App.tenant_id=source_tenant_id)` 锁 source App，最后锁
   asset。锁定 asset 后重新验证 status、row_version、source IDs 和 tenant scope；
   定位结果与锁定行不一致即 fail closed。要求 source App normal。
2. 精确调用：

   ```python
   AppDslService.export_dsl(
       app_model=source_app,
       session=session,
       include_secret=False,
   )
   ```

3. 原样保存官方 `export_dsl(..., include_secret=False)` 返回字符串，并直接对其 UTF-8
   原始字节计算 SHA-256。`yaml.safe_load` 只用于 mapping、`kind=app`、受支持 version、
   sanitizer 和 dependency 提取；校验过程禁止排序、重写或重新 dump YAML。
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
5. DSL 内 dependencies 是发布快照的原始事实来源；从同一原始 DSL 解析并按稳定规则
   规范化、排序、去重，生成独立 JSON manifest 作为派生索引。发布时验证两者语义一致，
   但绝不为写入 manifest 而改写 DSL。
6. 插入 snapshot、更新主表 pointer/state/version；绝不 UPDATE 旧 snapshot。

测试使用 canary credentials、secret variables、API keys/tokens、私有 plugin
credentials、knowledge IDs、file IDs 和 URL icon；除验证响应 code 外，不把 canary
值写入日志或 snapshot assertion failure。另验证保存的 `dsl_content` 与官方 export
字符串逐字一致、hash 与 UTF-8 字节一致，并执行 export → validate → import round-trip。

复制固定规则：

- 只锁并读取 `publication_status=published`、`snapshot_state=ready` 的 pointer snapshot；
- 重新计算 SHA-256 并核对 asset/version/source IDs；
- 不查询 source App，不检查 source App 是否存在；
- target tenant 只能来自 `current_account_with_tenant()`，且 `account.current_tenant_id`
  必须与之相同；body 不接受 tenant ID；
- 只使用发布时已验证与 DSL 一致的 snapshot dependency manifest，对目标 tenant 做
  import 前预检；禁止在 copy 时重新从其他来源推导。缺失或不允许的依赖必须在零 DB
  写入状态下返回稳定错误；
- timeout、Plugin Daemon 不可用统一映射可重试的 `dependency_service_unavailable`；
  私有/Package/Remote 依赖映射不可重试的 `private_plugin_dependency`，不得泄漏 daemon
  响应、连接信息或内部异常；
- 预分配 UUID `import_app_id`，并调用
  `AppDslService(session).import_app(account=caller,
  import_mode=ImportMode.YAML_CONTENT, yaml_content=snapshot.dsl_content,
  import_app_id=import_app_id, ...)`；客户端不能提供或覆盖它；
- import 开始后不得增加任何 B4 自有、可能失败的业务校验，也不得调用 post-import
  `check_dependencies`。之后只解释官方 Import status 并做不会抛出敏感信息的安全序列化；
- `COMPLETED` 返回 201；`COMPLETED_WITH_WARNINGS` 返回 201 和脱敏 warnings（仅允许稳定
  code，不透传内部文本）；`PENDING` 绝不视为成功，映射 `copy_pending_unsupported`；
  `FAILED` 映射 `copy_failed`。所有失败都禁止向客户端返回 `Import.error`、DSL、credential
  或内部异常；
- 官方 import 创建的 dependency Redis key遵循官方 TTL/生命周期。Redis key 删除不是
  DB 或 Plugin Daemon 补偿，B4 不以清 key 宣称回滚，也不新增危险删除逻辑；
- 不允许客户端覆盖已有 app_id/import_app_id。

发布后 source App 修改或删除不会改变 snapshot；copy 路径的测试必须使任何 source
App query 直接失败，从而证明没有动态回读。

## 10. Session、事务和并发

- controller 通过 `with_session` 注入唯一 Session，只做 DTO、service 调用、序列化。
- read service 只使用该 Session。submit/review/reject/unlist/backfill 的 DB-only
  mutation 可由 service-owned transaction 管理；copy 必须遵循官方 plain Session/import
  行为，不在官方内部 commit 外虚构 `session.begin()` 嵌套原子事务。
- submit：锁 source App；查询/锁 asset；首次 unique race 映射 409。
- review/approve：先非锁定定位 asset 的 source IDs，再锁 source App，最后锁 asset并
  重验 status、row_version、source IDs、tenant scope；export、校验、snapshot INSERT、
  pointer/state 更新在同一事务。
- resubmit：先锁 source App，再锁 asset并重验；backfill 同时使用两者时也必须先 source
  App 后 asset。
- reject/unlist：锁 asset，检查 expected row version 后 mutation。
- **全局锁序唯一为 source App → asset**；禁止任何 asset → source App 路径。reject/
  unlist 不读取或锁 source App 时只锁 asset，不构成逆序。
- copy 在 import 前完成 snapshot/pointer/hash/manifest/tenant 与 dependency 的全部
  fail-closed 检查，且此前零 DB 写入；import 开始后只解释官方结果和安全序列化。
- `AppDslService.import_app()` 的普通 workflow 路径会调用
  `WorkflowService.sync_draft_workflow(commit=True)`，可能中途提交 App、InstalledApp、
  Site、Workflow，并触发 signal/Redis 状态。因此外层 rollback 不能保证撤销整个 copy，
  计划也不再作此承诺。官方 import 自身在内部 commit 后仍可能返回 FAILED，这是
  `KNOWN_LIMITATION`：使用预分配 `import_app_id`、asset/snapshot/tenant/request ID 和稳定
  status 日志形成受控 reconciliation 证据，但不自动删除对象。
- 若实现审查发现上述边界仍不足以达到可接受安全性，必须把结论改为 `B4_BLOCKED`，
  不得用 rollback 或 Redis 清理文字掩盖。
- 禁止隐式 `db.session` 和第二 Session。B4-B 必须规划真实 PostgreSQL 的并发
  submit/review/backfill 测试，设置 lock timeout，并证明无死锁和 stale version 误放行。

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
5. 对所有历史值使用穷尽 `CASE ... ELSE` 初始化 B4 自有列后，再加安全的
   NOT NULL/check/index；`publication_status` 与 `snapshot_state` CHECK 只约束 B4 自有
   且已安全初始化的值，不会因未知旧 status 导致 upgrade 失败；
6. 不改旧 status、source IDs、metadata、reviewer、行数及三个时间戳。

未知 old status 的 `ELSE` 映射固定为：
`publication_status='unpublished'`、`snapshot_state='failed'`、
`snapshot_error_code='legacy_status_unknown'`。它保持旧 `status` 原值、永不公开并进入
人工 inventory。migration 绝不 UPDATE、规范化或删除未知 status。

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
| 未知历史 status | 原 status 保留；unpublished/failed | 不进入正常 mutation；稳定分类后人工处理 |

## 12. 独立回填步骤

回填不是 migration。B4-B 在 service 中提供仅供受控运维调用的
`backfill_legacy_snapshot(asset_id, dry_run, expected_row_version)`，不新增公开 HTTP
route；同时在 `api/commands/data_migrate.py` 增加并注册版本化
`marketplace-snapshots` 子命令，由现有 `api/extensions/ext_commands.py` 注册的
`data-migrate` group 暴露为 `flask data-migrate marketplace-snapshots`。默认 dry-run，
只有显式 `--apply` 才写入；禁止 `/tmp` 一次性未版本化 runner。

执行协议：

1. 支持全量 read-only inventory、单 `--asset-id`、`--id-file`、retry manifest 和错误阈值；
   输出 count by status/snapshot state/source classification，不输出 DSL；
2. 默认 dry-run 对每行做 source scope、export、sanitizer、dependency/hash 验证但不写 DB；
3. stdout/`--output` 只输出 JSONL 稳定事件；manifest 包含 asset ID、旧状态、source 分类、
   操作前后 row version、结果 code、hash 指纹前 12 位，文件必须 0600 并记录完整文件
   SHA-256；禁止 email、DSL、secret、token、credential、连接串、SQL 或内部异常；
4. apply 每资产一个 transaction，`FOR UPDATE` + expected row version；成功写 v1 并发布；
5. apply 的成功、source_missing、failed 状态更新都递增 row_version；不改旧 status、不删行；
6. 重跑时 ready 行校验 hash 后 skip；failed/pending 使用 manifest/DB 最新 row_version 按 ID
   retry；同 asset/version unique 防重复；
7. 中断后从 manifest 的未完成 ID 继续；错误阈值触发停止；
8. 隔离副本先验证总行数、状态、source IDs、时间戳和抽样 hash，再申请生产窗口；
9. 恢复只用升级前备份；不自动删除 snapshot 或 downgrade。

command/service focused tests覆盖默认 dry-run、显式 apply、单 ID/ID file、retry、阈值、
JSONL 脱敏、manifest 权限/hash 和未知 status。实际 inventory、dry-run/apply/恢复演练仍只在
B8/隔离 PostgreSQL 副本执行。

## 13. 结构化日志与信息泄漏边界

日志是运维与 reconciliation 证据，不是正式 audit table，不满足不可抵赖审计。所有事件使用
稳定 event/code 字段；允许记录 request ID、asset ID、snapshot ID/version、source app ID、
target tenant ID、预分配 import app ID、actor account ID、row version 和脱敏 hash 指纹。
一律禁止 email、DSL、token、credential、`Import.error`、查询正文、SQL、连接串、Plugin
Daemon 响应或内部异常文本。

| event | level | 必要语义 |
| --- | --- | --- |
| `marketplace.submission_created` | info | asset/source/tenant/actor/new row version |
| `marketplace.submission_resubmitted` | info | asset/source/actor/old+new row version |
| `marketplace.review_approved` | info | asset/snapshot/version/reviewer/new row version |
| `marketplace.review_rejected` | info | asset/reviewer/new row version/stable reason code |
| `marketplace.asset_unlisted` | info | asset/reviewer/new row version |
| `marketplace.asset_copied` | info | asset/snapshot/target tenant/import app/status |
| `marketplace.copy_failed` | warning（预期状态/依赖失败）或 error（内部异常/可能残留） | 稳定阶段与错误 code；已知可能残留时含 import app ID |
| `marketplace.backfill_started` | info | run/manifest hash/mode/count |
| `marketplace.backfill_completed` | info | run/counts/manifest hash |
| `marketplace.backfill_failed` | error | run/asset/stable code/latest row version |

public response 不返回 reviewer、submitter、隐藏 workspace、source tenant/account 信息；
错误响应不回显分页 keyword/query 原文、`Import.error`、SQL、Plugin Daemon 或内部异常。
controller/service tests用 canary 值断言 response、日志与 JSONL 均无泄漏。

## 14. B3 注册与最终 contracts

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

## 15. 文件 allowlist / denylist

### B4 总 allowlist

- `api/controllers/console/__init__.py`
- `api/models/__init__.py`
- `api/models/model.py`
- `api/controllers/console/enterprise_marketplace.py`
- `api/services/enterprise_marketplace_service.py`
- `api/commands/data_migrate.py`（仅 B4-B marketplace-snapshots 子命令与注册）
- 经 Reviewer 预先批准、且只服务 B4 的
  `api/services/errors/enterprise_marketplace.py` 或 controller-local error/DTO
- `api/tests/unit_tests/models/test_enterprise_marketplace.py`
- `api/tests/unit_tests/services/test_enterprise_marketplace_service.py`
- `api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py`
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

## 16. Builder 拆分与串行 handoff

推荐拆为三个严格串行 Builder；不得并行修改 model/service/controller/contracts。

### B4-A：schema/model/migration

- 启动门禁：本修订计划 Reviewer PASS 后，任务单填写该 Reviewer 接受的精确 commit；
  未通过复审不得启动。
- 精确 allowlist：
  `api/models/__init__.py`、`api/models/model.py`、
  `api/migrations/versions/2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py`、
  `api/tests/unit_tests/models/test_enterprise_marketplace.py`、
  `api/tests/unit_tests/migrations/test_enterprise_1_16_marketplace_migration.py`。
- denylist：service/controller/init/contracts、B2/B3/Web/Docker。
- 交付：§5/§11 完整 schema、model、migration graph tests；不加 legacy status CHECK，
  hash 使用 VARCHAR(64)。migration test 必须含未知 status fixture，证明 upgrade 成功、
  原 status/source IDs/时间戳不变且 publication 不公开。
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
- 起点必须是 B4-A Reviewer 接受的单一 commit。
- allowlist：enterprise marketplace service、专用 error/domain 文件、
  `api/commands/data_migrate.py` 中 marketplace-snapshots 子命令/注册、
  service tests 和
  `api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py`。
- denylist：model/migration/controller/init/contracts、B3/Web/Docker。
- 依赖：只能在 B4-A review PASS 后开始。
- 交付：§6、§8–§13 service、sanitizer、原始 DSL/hash、统一 source App → asset
  锁序、manifest-only dependency preflight、遵循官方内部 commit 已知限制的 copy，以及
  版本化 backfill command。禁止 post-import dependency rejection；禁止修改 B3 独占文件。
- 测试：

  ```bash
  uv run --project api pytest \
    api/tests/unit_tests/services/test_enterprise_marketplace_service.py \
    api/tests/unit_tests/commands/test_marketplace_snapshot_backfill.py
  ```

- handoff：接受 commit、public method/exception 清单、状态矩阵、session/lock 证据、
  sanitizer fixtures、NOT_RUN。

### B4-C：controller/注册/contracts/integration source tests

- 精确起点规则：任务单必须填入“B4-B Reviewer 接受的单一 commit SHA”；不得预填符号值。
- allowlist：enterprise controller、console init、controller/route/contract tests、
  generated console contracts。
- denylist：model/migration/service/B3 独占文件/Web/Docker。
- 依赖：B4-B review PASS。
- 不修改 B4-A model/migration 或 B4-B service/command 文件。
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

## 17. 测试矩阵、验证地点与风险

### 17.1 Builder 本地必须执行

- tenant scope、admin/non-admin、DTO extra forbid、稳定 error body；
- 完整状态转换和非法状态；
- duplicate/concurrent submit 的 mock/unique mapping；
- source App 修改/删除后 copy 不查询 source；
- canary secret、credential、token、private plugin、workspace resource 被拒；
- hash/version/frozen_at、append-only snapshot；
- 官方 export 原字符串逐字保存、原始 UTF-8 hash、export→validate→import round-trip；
- target workspace 只来自 current caller；
- 官方 import status/内部 commit exception injection、显式 Session、controller 无 SQLAlchemy；
- dependency manifest 与 DSL 一致、preflight missing/private/timeout/daemon unavailable，
  且无 post-import dependency rejection；
- unknown legacy status fail closed、row version 每次可观察 mutation 递增；
- snapshot→asset/pointer 完整性查询和禁止删除；
- structured log/response/JSONL canary 泄漏检查；
- B3 精确 7 routes、无 DELETE/延期高风险 routes；
- B4 精确 8 routes；
- contract generation、semantic generated diff、二次生成稳定；
- static migration graph 唯一 `b416e5c4e702`；
- `git diff --check` 与 scope checker。

### 17.2 隔离 PostgreSQL 副本/B8 必须执行

- 四起点：空库、官方 1.16 head、旧企业 `e2f0a9b7c6d5`、B2 merge head；
- 实际 DDL/check/index/unique、row locks，以及并发 submit/review/backfill 的真实
  PostgreSQL 死锁/锁顺序测试；
- migration 前后旧表行数/status/source_app_id/created/updated/reviewed 时间；
- 回填 inventory → dry-run → apply → retry → failure recovery；
- 来源 normal/deleted/abnormal/tenant mismatch fixture；
- 旧 approved 无 snapshot 在回填前隐藏，回填后可复制；
- Redis/plugin dependency preflight integration 与官方 TTL/生命周期；
- 官方 import 创建 App、InstalledApp、Site、Workflow、signal、Redis 的状态证据，以及
  internal-commit 后 FAILED 的已知残留/reconciliation 证据；
- A workspace 提交、admin 审核、B current workspace 复制并运行；
- 备份恢复回滚；不得在实际 volume 原地演练。

Integration tests 按仓库约定为 CI/隔离环境，不冒充本地已运行。MySQL 仅在将来声明支持时
条件执行；本轮发布阻断数据库为 PostgreSQL。

### 17.3 已知限制与非阻断风险

1. `ACCEPTED_KNOWN_LIMITATION`：官方 import 内部 commit 后仍可能 FAILED；预分配
   import app ID 和结构化日志支持受控 reconciliation，但 B4 不宣称原子化也不自动删除。
2. DSL export 的未来字段可能绕过已知 sanitizer；以版本化、fail-closed validator 和 canary
   tests 缓解。
3. 旧 approved 行在独立回填前不可公开；通过 inventory、dry-run、分批 retry 和发布门禁控制。
4. 无物理 FK 依赖 service/inventory/B8 invariant；未来删除能力必须重审。
5. page-number pagination 在高并发写入时可能跨页漂移；稳定排序/id tie-breaker 只保证可复现。

## 18. Review finding disposition 与最终验收

人工决定 P1-1 **方案 B 已落实**：不加 legacy status CHECK、不改未知 status，应用层
fail closed，migration 将未知行初始化为隐藏且待人工处理的 B4 状态。

| Finding | disposition | 修订章节 | Builder 验证 |
| --- | --- | --- | --- |
| P0-1 copy/内部 commit | `ACCEPTED_KNOWN_LIMITATION` | §9 copy、§10、§17.3 | B4-B 证明全部自有校验在 import 前且零 DB 写入；无 post-import dependency rejection；覆盖四种 Import status、预分配 ID 和 internal-commit 后 FAILED reconciliation |
| P0-2 锁顺序 | `CLOSED` | §9、§10、§17.2 | B4-B unit lock-order assertion；真实 PostgreSQL submit/review/backfill 并发死锁测试 |
| P1-1 legacy status | `CLOSED` | §5.1、§11、§16 B4-A | 未知 status fixture upgrade 不失败、不改原值、不公开；DDL 无 legacy status CHECK |
| P1-2 row_version | `CLOSED` | §6.2、§10、§12 | 锁后比较 expected/current；每个可观察 mutation +1；retry 使用最新版本 |
| P1-3 post-import 副作用 | `ACCEPTED_KNOWN_LIMITATION` | §9 copy、§10、§17.3 | 删除完整 rollback 承诺；记录 App/InstalledApp/Site/Workflow/signal/Redis 与受控 reconciliation 证据 |
| P1-4 DSL/hash | `CLOSED` | §5.2、§9 | 原 export 逐字保存、UTF-8 hash、无 dump、round-trip |
| P1-5 Redis/dependencies | `CLOSED` | §8、§9、§10 | DSL/manifest 一致；仅 preflight；timeout/daemon/private 稳定错误；无 Redis 补偿宣称 |
| P2-1 无 FK | `CLOSED` | §5.3、§17 | orphan/pointer ownership 查询、service/migration/B8 invariant、禁止 delete |
| P2-2 hash 类型 | `CLOSED` | §5.2、§16 B4-A | model/DDL 精确断言 `VARCHAR(64)` |
| P2-3 回填 runner | `CLOSED` | §12、§15、§16 B4-B | 版本化 command、默认 dry-run、apply/ID/retry/JSONL/manifest tests |
| P2-4 审计/泄漏 | `CLOSED` | §13 | event matrix、level/ID allowlist、canary log/response/JSONL 测试 |

Review finding 的阻断剩余数为 **P0=0、P1=0、P2=0**。上述两个
`ACCEPTED_KNOWN_LIMITATION` 是同一官方 import 内部 commit 根因的诚实边界，不是未解决的
B4 自有设计检查；如 Builder 无法维持该边界，立即转为 `B4_BLOCKED`。

B4-A 在本计划 Reviewer PASS 且精确起点登记后允许启动；B4-B 仅在 B4-A Reviewer 接受
commit 后允许启动；B4-C 仅在 B4-B Reviewer 接受 commit 后允许启动。B4-C 若暴露 B3
defect 必须暂停交回 B3 Fixer。

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

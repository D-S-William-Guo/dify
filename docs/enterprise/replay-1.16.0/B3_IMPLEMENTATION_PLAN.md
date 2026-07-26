# Dify Enterprise 1.16.0 Replay B3 平台管理员后端实施契约

## 1. 结论、流程状态与授权边界

- 技术建议：**B3_READY**
- 流程状态：**PENDING_INDEPENDENT_REREVIEW**
- Builder 授权：**不授权**

`B3_READY` 仅表示本计划在技术上已形成可实施契约，不表示独立 Review 已通过。修订后的本文件必须由独立
Reviewer 复审并取得明确 `PASS`；在此之前不得启动 B3 Builder、B4 注册/contract generation 或 B5。

实现真相按以下优先级确定：

1. 官方 tag `1.16.0` 的 model、Pydantic Console schema、显式 `Session`、account/tenant/member/RBAC
   与错误处理模式；
2. 已完成的 HD-1、HD-2 和 P0 人工决定；
3. `DESIGN_GATE.md` 的 DG-02/DG-09、`ARCHITECT_HANDOFF.md`、decision matrix 与 validation plan；
4. 旧 1.15 企业提交仅作为需求和历史缺陷证据，不作为可复制实现。

禁止复制旧实现中的全局 `db.session`、controller SQLAlchemy、legacy RESTX field dict、
`schema_model`、`marshal_with`、动态 `Account.is_platform_admin`、逐项 commit、直接给 ACTIVE 账号建
join、仅删除 join、响应 token/activation URL 等模式。

### 1.1 Review 整改映射

下表只记录 Architect/Fixer 对 Review 的处理，不宣称 Review 已通过。

| Review 项 | 处理 | 本计划位置 |
| --- | --- | --- |
| P0-1 成员移除副作用不完整 | **DEFERRED**：成员移除整体 `DEFERRED + REJECTED`，B3 无删除路径 | §2、§3.2、§5.5、§10 |
| P1-1 ACTIVE 邀请偏离官方 | **FIXED**：不直接建 join，经 `/activate` 接受后建立 | §2、§5.4、§6.3 |
| P1-2 billing email freeze | **FIXED**：新建 Account 前按 billing 配置检查，命中则整批原子拒绝 | §5.4、§6.5、§10 |
| P1-3 token 撤销 key 错配 | **FIXED**：只用 `revoke_token(None, None, token)` 撤销生成 key | §5.4、§6.6、§10 |
| P1-4 RBAC read role 误导 | **FIXED**：nullable role、显式 `role_source` 与 `mutation_supported` | §3.1、§6.8、§10 |
| P1-5 workspace limit 双算 | **FIXED**：enterprise/billing 分支各使用单一官方来源 | §6.4、§10 |
| P2-1 Redis 无限等待 | **FIXED**：明确 TTL、`blocking_timeout`、顺序和异常策略 | §5.3、§10 |
| P2-2 `session.begin()` 前 autobegin | **FIXED**：首个 DB 操作位于 begin 内，外部 I/O 位置明确 | §5.2、§5.4、§10 |
| P2-3 current tenant 隐含依赖 | **FIXED**：status 去除不必要依赖；管理路由稳定拒绝无 current tenant | §4.3、§10 |
| P2-4 token 不返回导致邮件依赖 | **FIXED**：邮件是接受链接唯一通道，delivery 语义明确 | §3.1、§6.7、§10 |
| P2-5 LoginConfig 放置 | **ACCEPTED**：当前允许范围内的 pragmatic 选择 | §4.1 |
| HD-1 RBAC mutation 策略 | **ACCEPTED**：RBAC 开启时 invite/role mutation 503 fail-closed | §6.8 |
| HD-2 ACTIVE 邀请语义 | **ACCEPTED**：使用官方邀请—接受流程 | §5.4、§6.3 |
| P1-RR-1 `requires_setup` 契约 | **FIXED**：四种发 token 状态均显式传值，并验证 Redis payload 与激活分支 | §5.4、§6.3、§10 |
| P1-RR-2 ACTIVE 延迟接受 capacity | **ACCEPTED_LIMITATION**：改正为邀请时瞬时门禁；无 reservation/recheck，最终成员数可能超限 | §6.4、§10、§11.2 |
| P2-RR-1 capacity 精确 guard | **FIXED**：补齐零增量、enterprise seat-zero、billing enabled/unlimited 条件 | §6.4、§10 |
| P2-RR-2 上游治理文档陈旧措辞 | **FIXED_BY_GOVERNANCE_SYNC**：同步 Design Gate、handoff、decision matrix 与 validation plan 的 7-route/无删除契约 | §2、§9、§10 |
| 2026-07-26 最新人工决定 | **ACCEPTED**：保持官方 ACTIVE 邀请—接受流程，接受 capacity 既有限制，成员移除继续整体延期 | §2、§6.4、§11.2 |

### 1.2 已核实的官方事务事实

- `AccountService.create_account()`、`TenantService` 多个写方法及 legacy
  `RBACService.MemberRoles.replace()` 会自行 commit。
- `RegisterService.invite_new_member()` 在 commit 前后混合数据库、Redis token 与 Celery dispatch。
- `TenantService.remove_member_from_tenant()` 除删除 join 外还有资源 maintainer、pending Account、
  billing、enterprise sync 与 RBAC 等副作用。
- `controllers.common.session.with_session` 注入显式 `Session`，handler 正常返回后还会调用 commit。
- `FeatureService`/`BillingService`/Redis 可能产生外部 I/O；不能让其在 begin 前意外触发 Session 查询。

B3 不调用会自行 commit 的官方写方法；允许的写入由一个注入 Session 和 service-owned transaction 完成。

## 2. 精确功能范围

`DEFERRED` 表示本轮没有 endpoint；`REJECTED` 表示不得借通用 mutation、隐藏 route 或内部 helper 绕过。

| 能力 | 决定 | B3 精确边界 |
| --- | --- | --- |
| 平台管理员身份判断 | INCLUDED | 配置 email 与当前已认证 `ACTIVE` Account 的规范化 email 比较；提供 B5 status endpoint。 |
| workspace 列表/详情 | INCLUDED | 跨 workspace 分页、搜索、状态过滤和详情；读取 normal/archive。 |
| workspace 改名 | INCLUDED | 仅 normal；保持官方允许重名语义。 |
| workspace 创建 | DEFERRED | 不提供 create route；官方初始化链不能在 B3 边界安全组合。 |
| workspace 删除/归档 | DEFERRED | 不提供 delete/archive route。 |
| workspace 成员列表 | INCLUDED | RBAC 关闭时返回 legacy fixed role；RBAC 开启时明确角色不可用。 |
| 新账号邀请 | INCLUDED | 创建 `PENDING` Account 与 join；commit 后 token/邮件。 |
| 既有 PENDING 邀请 | INCLUDED | 未加入则事务内建 join；已加入只 resend；commit 后 token/邮件。 |
| 既有 ACTIVE 邀请 | INCLUDED | 未加入不建 join，commit 后 token/邮件，接受时由官方 `/activate` 建 join；已加入返回 `already_member`。 |
| 成员角色变更 | INCLUDED | fixed non-owner roles；RBAC 开启时 503 fail-closed。 |
| **成员移除** | **DEFERRED + REJECTED** | **B3 不提供成员删除路径，不实现 `remove_member`，不直接 `session.delete(TenantAccountJoin)`。** |
| owner 分配/转移/降级/移除 | DEFERRED + REJECTED | invite/role DTO 不接受 owner；普通 mutation 不处理 owner 生命周期。 |
| 密码重置、break-glass | DEFERRED | 无 DTO、route、service method。 |
| 新 audit model | DEFERRED | B3 不新增 model/migration。 |

未定义的 member `DELETE` 请求只能得到 Flask/router 的 404 或 405；不得注册隐藏的通用 member mutation。

后续若恢复成员移除，必须另立任务并复用官方逻辑或等价完整覆盖：

- App maintainer 重分配；
- Dataset maintainer 重分配；
- 孤立 `PENDING` Account 处理；
- billing cache 清理；
- `sync_workspace_member_removal`；
- RBAC binding cleanup；
- owner、current workspace、last workspace 保护；
- 数据库 transaction、外部副作用补偿、通知和审计。

不得接受“只删除 join”的实现。last/current workspace protection 仍是未来移除任务的强制门禁；本轮没有可
绕过这些门禁的删除路径。

## 3. 路由、DTO 与错误契约

DTO 定义在 `api/controllers/console/platform_admin.py`。请求继承 Pydantic `BaseModel` 并使用
`ConfigDict(extra="forbid")`；响应继承 `fields.base.ResponseModel`。使用
`register_schema_models`、`register_response_schema_models`、`query_params_from_model` 和
`dump_response`。

### 3.1 DTO 清单（14 个）

1. `PlatformAdminStatusResponse`
   - `is_platform_admin: bool`
   - `mutation_supported: bool`（仅平台管理员且 RBAC 关闭时为 true）
2. `PlatformAdminWorkspaceListQuery`
   - `page: int = 1`（`ge=1`）
   - `limit: int = 50`（`ge=1, le=100`）
   - `keyword: str | None`（trim，最长 255，空串为 `None`）
   - `status: Literal["normal", "archive", "all"] = "normal"`
3. `PlatformAdminWorkspaceOwnerResponse`
   - `id/name/email`
4. `PlatformAdminWorkspaceResponse`
   - `id/name/plan/status/created_at/updated_at/member_count/owner`
5. `PlatformAdminWorkspacePaginationResponse`
   - `items/page/limit/total/has_more`
6. `PlatformAdminWorkspaceRenamePayload`
   - `name: str`（strip，1～255）
7. `PlatformAdminMemberResponse`
   - `id/name/email/status/current/created_at/last_login_at/last_active_at`
   - `role: Literal["owner", "admin", "editor", "normal", "dataset_operator"] | None`
   - `role_source: Literal["tenant_account_join", "rbac_unavailable"]`
   - `mutation_supported: bool`
8. `PlatformAdminMemberListResponse`
   - `items: list[PlatformAdminMemberResponse]`
   - `mutation_supported: bool`（即使空列表也能让 B5 正确禁用操作）
9. `PlatformAdminMemberInvitePayload`
   - `emails: list[EmailStr]`（1～50；trim/lower 后拒绝重复）
   - `role: Literal["admin", "editor", "normal", "dataset_operator"]`
   - `language: str | None`
10. `PlatformAdminMemberInviteResultResponse`
    - `email`
    - `action: Literal["account_created", "membership_created", "invitation_queued", "invitation_resent", "already_member"]`
    - `email_delivery: Literal["queued", "failed", "not_applicable"]`
    - 不含 token、activation URL 或内部异常文本
11. `PlatformAdminMemberInviteResponse`
    - `workspace_id/results`
12. `PlatformAdminMemberRoleUpdatePayload`
    - `role: Literal["admin", "editor", "normal", "dataset_operator"]`
13. `PlatformAdminMemberRoleUpdateResponse`
    - `result: Literal["success"]`
    - `workspace_id/member_id`
14. `PlatformAdminErrorResponse`
    - `code/message/status`

不再定义通用于 remove 的 `PlatformAdminMemberMutationResponse`，role endpoint 使用专用 response。
RBAC 关闭时 `role` 来自 fixed legacy `TenantAccountJoin.role`、`role_source="tenant_account_join"`；
RBAC 开启时 `role=None`、`role_source="rbac_unavailable"`、`mutation_supported=false`，不得把 join.role
冒充权威 RBAC 角色。B3 不调用外部 RBAC read/write API。

B3 response 永不返回 invitation token 或 activation URL。邮件是用户取得接受链接的唯一通道。B5 以
status/list response 的 `mutation_supported` 控制批量邀请按钮，以 member response 的同名字段控制行级
角色按钮。

### 3.2 最终 endpoint 表（仅 7 条）

| Method | route | request | response | success | service | 日志 |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/account/platform-admin-status` | 无 | `PlatformAdminStatusResponse` | 200 | 纯 helper | DEBUG `platform_admin.identity_checked` |
| GET | `/platform-admin/workspaces` | list query | pagination response | 200 | `list_workspaces` | DEBUG `workspace_listed` |
| GET | `/platform-admin/workspaces/<uuid:workspace_id>` | 无 | workspace response | 200 | `get_workspace` | DEBUG `workspace_viewed` |
| PATCH | `/platform-admin/workspaces/<uuid:workspace_id>` | rename payload | workspace response | 200 | `rename_workspace` | INFO `workspace_renamed` |
| GET | `/platform-admin/workspaces/<uuid:workspace_id>/members` | 无 | member list response | 200 | `list_members` | DEBUG `members_listed` |
| POST | `/platform-admin/workspaces/<uuid:workspace_id>/members/invitations` | invite payload | invite response | 201 | `invite_members` | INFO `members_invited`；delivery failure warning |
| PATCH | `/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>/role` | role payload | role update response | 200 | `update_member_role` | INFO `member_role_updated` |

明确不包含 member DELETE、workspace create/delete/archive、owner mutation、password 或 break-glass route。

### 3.3 稳定错误映射

| code | HTTP | 条件 |
| --- | --- | --- |
| 官方 unauthenticated contract | 401 | 未认证 |
| `platform_admin_required` | 403 | 非 ACTIVE 或 email 未授权 |
| `invalid_request` / `duplicate_email` / `invalid_role` | 400 | DTO/批次/role 错误 |
| `workspace_not_found` / `member_not_found` | 404 | 不存在或不属于目标 workspace |
| router 404/405 | 404/405 | 未定义的 member DELETE 等 route |
| `workspace_unavailable` | 409 | mutation 目标非 normal |
| `role_already_assigned` | 409 | fixed role 未变化 |
| `owner_operation_deferred` / `owner_assignment_deferred` | 409 | owner 生命周期操作 |
| `account_uninitialized` / `account_disabled` | 409 | 不允许的 Account 状态 |
| `email_identity_ambiguous` | 409 | case-insensitive email 命中多个 Account |
| `email_in_freeze` | 409 | billing freeze 命中；整批无副作用 |
| `current_tenant_required` | 409 | 管理 route 调用者无 `current_tenant_id` |
| `concurrent_operation` | 409 | Redis 错误、锁超时、unique race 或 recheck 失败 |
| `workspace_member_limit_exceeded` | 403 | 对应官方分支的 workspace capacity 不足 |
| `seat_limit_exceeded` | 403 | enterprise seat 不足 |
| `rbac_mode_not_supported` | 503 | RBAC 开启时 invite/role mutation |

删除专属于成员移除的 `last_workspace_membership`、`current_workspace_membership`、`last_owner_protected`
错误路径；这些 guard 只记录为未来成员移除任务的强制要求，不是 B3 可调用契约。

## 4. 身份、配置与 decorator

### 4.1 LoginConfig

在当前允许文件 `api/configs/feature/__init__.py` 的 `LoginConfig` 增加唯一配置：

```python
PLATFORM_ADMIN_EMAILS: str = Field(
    description="Comma-separated platform administrator email addresses.",
    default="",
)
```

这是当前允许范围内的 pragmatic 选择：默认空且 fail closed；配置在进程启动时加载，变更需重启。不得新增
第二个同义配置，不修改 `EnterpriseConfig`。

### 4.2 授权 helper

`api/libs/platform_admin.py` 提供纯规范化/解析/predicate 和薄 decorator：

- email 使用 `strip().lower()`；空值为 `None`；
- 配置按逗号解析为去重 `frozenset`；
- 只有 `AccountStatus.ACTIVE` 且规范化 email 命中才是平台管理员；
- 不缓存或返回配置，不注入 Account 动态字段；
- 身份仅来自 `login_required` 建立的 `current_user`，不读取 tenant/header/query/body。

### 4.3 current tenant 与 decorator 顺序

status endpoint 只需判断已登录 Account 是否为 ACTIVE 且配置命中，不需要 workspace 上下文：

```text
setup_required
login_required
```

它不得使用 `account_initialization_required`，从而避免对 `current_tenant_id` 的不必要依赖；这不降低 setup、
login 或 CSRF 安全要求。

六条管理 route 使用：

```text
setup_required
login_required
platform_admin_required
platform_admin_current_tenant_required
account_initialization_required
with_session
```

`platform_admin_current_tenant_required` 在官方 `account_initialization_required` 之前检查
`current_user.current_tenant_id`；缺失时返回稳定 409 `current_tenant_required`，不得让
`current_account_with_tenant()` 的 AssertionError 变成 500。因而，无 current tenant 的平台管理员不能使用
管理 route。测试必须覆盖 decorator 短路、顺序、setup/login 不降级及稳定错误。

service 始终从 path `workspace_id` 查询目标 Tenant，不信任调用者 current tenant 来决定管理目标。

## 5. Service、事务与锁

### 5.1 public API

controller 只用 `with_session` 注入的唯一 `Session` 构造 `PlatformAdminService(session)`。public methods：

```text
list_workspaces(*, page, limit, keyword, status) -> WorkspacePage
get_workspace(workspace_id) -> WorkspaceView
list_members(workspace_id) -> list[MemberView]
rename_workspace(*, workspace_id, name, operator_account_id) -> WorkspaceView
invite_members(*, workspace_id, emails, role, language, operator) -> InviteBatchResult
update_member_role(*, workspace_id, member_id, new_role,
                   operator_account_id) -> MemberRoleUpdateResult
```

没有 `remove_member` 或通用 delete/mutation method。service 返回自身 frozen dataclass/TypedDict，不依赖
controller DTO。

### 5.2 一个有效业务事务

- controller 使用官方 `with_session` 注入唯一 Session；不修改 `with_session`。
- write service 在任何数据库 query/flush 之前进入 `with self._session.begin():`。
- 所有 Tenant/Account/Join query、`FOR UPDATE`、add/update/flush 都在 begin 块内，禁止第二 Session。
- begin context 正常退出完成唯一有效数据库 commit；异常退出 rollback；禁止中途 commit。
- `with_session` 在 handler 返回后的最后一次 commit 仍会被调用，但没有 pending change，只是 no-op。
  因此准确表述是“一个有效业务事务/一次有效业务提交”，而不是“commit 方法只调用一次”。
- Redis 锁获取发生在 begin 前且不得访问数据库；FeatureService/BillingService 调用的具体位置见 §5.4。
  禁止在 begin 前调用可能通过同一 Session 查询数据库的 helper，避免 autobegin 后再次 begin。
- post-commit token/task 只能在 begin 成功退出后执行。
- 所有 post-commit 异常在 service 内捕获并转换为每项 `email_delivery="failed"`，不得冒泡为 HTTP 500。
- controller 在 service 返回后先预构造并校验 response model，再 dump；测试注入序列化异常。即使如此，
  数据库已提交后仍可能发生 controller/框架序列化故障，计划明确承认无法回滚这一窗口。

rename 与 role 分别在自己的 begin 块内锁 Tenant/Join，完成状态和 owner guard 后更新；不调用会 commit 的
`TenantService.update_member_role` 或 `RBACService.MemberRoles.replace`。

### 5.3 可执行 Redis 锁策略

invite 使用项目现有 `redis_client.lock` context manager：

```text
LOCK_TTL_SECONDS = 60
LOCK_BLOCKING_TIMEOUT_SECONDS = 5
```

调用必须显式传 `timeout=LOCK_TTL_SECONDS` 和
`blocking_timeout=LOCK_BLOCKING_TIMEOUT_SECONDS`。固定获取顺序：

1. `platform_admin:invite:tenant:<tenant_id>`
2. `platform_admin:invite:seats`
3. `platform_admin:invite:email:<sha256(normalized_email)>`，按 hash 字典序逐个获取

context manager 保证逆序释放，包括业务异常路径。Redis error、未取得锁或 lock timeout 全部 fail closed
为 `concurrent_operation`；测试验证已取得锁会释放。key 不含明文 email。

每类锁的目的：

- tenant lock：串行化同 workspace 的 B3 批量邀请和 capacity recheck；
- seats lock：串行化 B3 新 Account 的全局 seat 竞争。因为 begin 前禁止用 DB 预判批次是否含新 Account，
  invite 批次统一取得该锁，这是有意的保守选择；
- email lock：保护没有可供 `FOR UPDATE` 的 Account row 时，B3 内相同规范化 email 的并发创建。

role/rename 已有明确数据库 row lock，不额外使用 Redis 锁。B3 锁不能约束范围外官方注册/邀请流程，不得声称
提供全局唯一性；Account email 无数据库 unique constraint 仍是未闭环风险。

### 5.4 invite 时序与官方语义

1. DTO 产生规范化、无重复 email tuple；RBAC 开启则在任何锁、DB、token/task 前返回 503。
2. 按 §5.3 获取全部 Redis 锁。
3. 立即进入 `session.begin()`，此前没有 DB query。
4. 锁定并验证 normal Tenant；批量查询 Account、目标 joins，发现同 email 多 Account 则整批拒绝。
5. 分类并定义计数：
   - `new_account_count`：不存在 Account 的 email 数；仅此计数用于 enterprise seat。
   - `immediate_join_count`：新 Account 加既有 `PENDING` 且未加入的数量；这些 join 在本地事务建立。
   - `pending_invitation_count`：既有 `ACTIVE` 且未加入的数量；本次不建 join，但邀请时仍计入 workspace
     capacity 检查。
   - `required_memberships = immediate_join_count + pending_invitation_count`。
   - 已加入的 ACTIVE/PENDING 不计新 capacity。
6. 在 begin 块内调用 §6.4 对应部署分支的 FeatureService/system features。调用位置明确为分类之后、
   数据写入之前；它可能产生 I/O，但不会造成 begin 前 autobegin。
7. 仅当 `dify_config.BILLING_ENABLED=true`，对每个将创建新 Account 的 email 调用
   `BillingService.is_email_in_freeze(email)`。任何命中都抛稳定 `email_in_freeze`，begin rollback，
   整批不创建 Account/join。该官方调用可能 fail-open，但 B3 不得删除或绕过检查。
8. 写入动作：
   - **ACTIVE + 未加入**：不创建 join，不修改 current；记录 `invitation_queued` 待 dispatch。
   - **ACTIVE + 已加入**：不修改既有 join 或 current；`already_member`，不生成 token、不发信。
   - **既有 PENDING + 未加入**：创建 join 且 `join.current=False`，不修改该账号已有 current workspace；
     记录 `membership_created`。
   - **既有 PENDING + 已加入**：不重复 join，不修改原 `join.current`；记录 `invitation_resent`。
   - **新账号**：构造 `PENDING` Account 和目标 workspace join，明确设置 `join.current=True`；
     使用官方 language/timezone/初始字段语义；这等价于官方新邀请账号创建 membership 后
     `switch_tenant` 的最终 current 语义；记录 `account_created`。
9. `flush()` 触发约束并预构造不含 token 的内部结果；begin 正常退出完成有效业务提交。
10. 若 `immediate_join_count > 0` 且 `dify_config.BILLING_ENABLED=true`，在有效数据库提交后
    best-effort 调用 `BillingService.clean_billing_info_cache(tenant.id)`。失败只记录脱敏 warning，
    不回滚、不冒充数据库失败，并继续后续 dispatch。
11. 仅对需要邮件的四类结果逐项调用 `RegisterService.generate_invite_token`，再调用
    `send_invite_member_mail_task.delay(...)`。调用必须等价于：

    ```python
    RegisterService.generate_invite_token(
        tenant,
        account,
        role,
        requires_setup=requires_setup,
    )
    ```

    其中新建 `PENDING`、既有 `PENDING` 未加入、既有 `PENDING` 已加入 resend 均显式使用
    `requires_setup=True`；`ACTIVE` 未加入显式使用 `requires_setup=False`；`ACTIVE` 已加入不生成
    token/task。`generate_invite_token` 默认值为 `False`，Builder 不得省略参数或依赖默认值。生成后的
    Redis invitation JSON 必须包含与状态矩阵一致的 `requires_setup`。
12. token 或 task dispatch 失败不回滚数据库；若 token 已生成，必须调用
    `RegisterService.revoke_token(None, None, token)`，或等价关键字
    `workspace_id=None, email=None, token=token`。不得传 workspace id/email。
13. 捕获每项 post-commit 异常，返回 `email_delivery="failed"`；成功入队为 `queued`；
    `already_member` 为 `not_applicable`。批次 HTTP response 仍稳定返回，不泄漏异常。

`PENDING` 用户通过官方 `/activate` 接受时，`requires_setup=True` 使该流程收集 setup fields 并把
Account 更新为 `ACTIVE`。`ACTIVE` 用户使用 `requires_setup=False`，不进入 PENDING setup 分支；其只有
通过官方 `/activate` 接受后才由官方流程创建 join。B3 邀请既不改变其 current workspace，也不冒充永久
seat 已被预留。

### 5.5 成员移除不存在

B3 controller、DTO、service、测试和 B4 handoff 均不得出现 member DELETE、`remove_member`、
`member_removed` 或 `session.delete(TenantAccountJoin)`。未来删除设计见 §2，不能在 Builder 阶段恢复。

## 6. Guard、容量、RBAC 与 delivery

### 6.1 tenant/account/owner

- 所有 workspace path 从注入 Session 重新查询 Tenant；mutation 只允许 normal。
- email 先 trim/lower，批次重复为 400；case-insensitive 多 Account 为 409。
- `UNINITIALIZED`、`BANNED`、`CLOSED` 不可 invite/role；仅 ACTIVE/PENDING 使用 §5.4 语义。
- invite/role DTO 排除 owner。role target 当前是 owner 时返回 `owner_operation_deferred`；不得降级。

### 6.2 计数原子性

capacity/billing freeze 任一失败均在写入前终止并由 begin rollback；批次不做部分数据库成功。数据库 unique
race 映射 `concurrent_operation`。post-commit delivery 是另一阶段，其失败不改变数据库结果。

### 6.3 邀请状态矩阵

| 输入 | DB commit 内容 | action | token/task | 显式 `requires_setup` |
| --- | --- | --- | --- | --- |
| ACTIVE，未加入 | 无 join；不修改 current | `invitation_queued` | commit 后生成/投递 | `False` |
| ACTIVE，已加入 | 不修改既有 join/current | `already_member` | 无 | 不生成 token |
| 既有 PENDING，未加入 | 新 join，`join.current=False`；已有 current workspace 不变 | `membership_created` | commit 后生成/投递 | `True` |
| 既有 PENDING，已加入 | 不重复 join；原 `join.current` 不变 | `invitation_resent` | commit 后生成/投递 | `True` |
| Account 不存在 | 新 PENDING Account + join，`join.current=True` | `account_created` | commit 后生成/投递 | `True` |

每个生成 token 的分支都必须使用 §5.4 的显式五参数调用语义，不得依赖默认
`requires_setup=False`。token payload 与 `/activate` 行为以本表为唯一契约：PENDING 接受必须收集 setup
fields 并激活 Account；ACTIVE 接受不得错误进入 PENDING setup 分支。

### 6.4 workspace member limit 的唯一来源

不得对同一限制同时使用 DB count 与 feature payload size。

**所有部署分支的首个 guard：** `required_memberships <= 0` 时立即返回并跳过全部 capacity 检查。因而
`already_member` 和纯 resend 批次不得获取 capacity features、调用 workspace limit 或调用 seat limit。

**`ENTERPRISE_ENABLED=true`：**

- 仅当 `required_memberships > 0` 时获取 workspace features 并调用
  `features.workspace_members.is_available(required_memberships)`；
- 仅当 `new_account_count > 0` 时调用
  `system_features.license.seats.is_available(new_account_count)`；`new_account_count=0` 时不得调用 seat 检查；
- 不再用 DB join count 对 enterprise workspace limit 做第二次拒绝。

**`ENTERPRISE_ENABLED=false` 且 `BILLING_ENABLED=true`：**

- 与官方 `controllers/console/workspace/members.py` 一致，只有 `features.billing.enabled is True` 才应用
  billing member limit；billing feature disabled 时不拒绝；
- 只有 `0 < features.members.limit < current_db_member_count + required_memberships` 时拒绝；
  `members.limit=0` 表示 unlimited，不拒绝；总数正好等于 limit 时不拒绝；
- 不同时调用 enterprise `workspace_members.is_available`，也不应用 enterprise seat license。

两种配置都未启用时不发明容量限制。enterprise 与 billing 分支互斥。feature payload size 可能陈旧是
外部一致性限制；B3 不增加第二套互相矛盾的拒绝。

**已接受的官方既有限制：** `ACTIVE` 未加入虽计入邀请时的 `required_memberships`，但此 capacity check
只是瞬时门禁，不是 reservation。B3 此时不创建 join，也不建立任何持久 reservation；官方 `/activate`
不调用 workspace capacity 检查，B3 Redis 锁也不覆盖该接受路径。因此多个延迟或并发接受可能使最终
workspace 成员数超过 limit，不能声称最终一致性或最终 limit 保证已被维护。2026-07-26 人工决定明确接受
该限制，同时要求 B3 继续使用官方邀请—接受流程：不得偷偷修改 `/activate`，也不得恢复 ACTIVE 直接建
join。若未来产品不能接受，必须另建跨流程 reservation/recheck 任务，重新审查 API、Redis/DB 状态、过期
释放、并发、用户错误体验与 migration 需求。

### 6.5 billing freeze

freeze 只针对本批将创建的新 Account，且只在 billing enabled 时调用。任一命中采用整批原子拒绝：
无 Account、join、token 或 task。官方方法的异常语义可能 fail-open；B3 保留该语义但不得省略调用。

### 6.5.1 billing membership cache invalidation

`BillingService.is_email_in_freeze` 是创建新 Account **之前**的门禁；
`BillingService.clean_billing_info_cache(tenant.id)` 是 immediate membership **有效提交之后**的缓存失效，
两者不得混淆。

- 仅当 `immediate_join_count > 0` 且 billing enabled 时，在 begin 成功退出后 best-effort 清理一次；
- ACTIVE invitation 尚未创建 join，不触发清理；
- `already_member`、PENDING resend 等无 join 变化的批次不触发清理；
- 清理失败不得回滚已提交数据库、不得改写为数据库失败，也不得阻止 token/task dispatch；
- warning 只记录 tenant ID 和稳定失败分类，不记录 email、token、payload 或异常敏感内容；
- 失败后 billing membership cache 可能短暂陈旧，这是明确保留的外部一致性风险。

### 6.6 token key 与撤销

`generate_invite_token` 创建 `member_invite:token:{token}`。dispatch 失败只用
`revoke_token(None, None, token)` 删除该路径。传 workspace id/email 会选择不同且未创建的 key，明确禁止。
token 不进入日志、response、异常文本或 snapshot。

### 6.7 邮件唯一通道

- B3 response 不返回 token 或 activation URL；
- 邀请邮件是接受链接唯一通道；
- `queued` 仅表示 Celery `.delay()` 已成功入队，不表示邮件送达；
- `failed` 不回滚已提交数据；
- 无 outbox，不保证 exactly-once、持久重试或自动补偿；
- ACTIVE 在接受前不是 workspace 成员；
- B5 必须原样展示 `queued`/`failed`/`not_applicable`，不得显示伪造“邀请成功”。

### 6.8 RBAC 模式

HD-1 已决定：

- `RBAC_ENABLED=true` 时 invite 与 role mutation 都在任何 DB/Redis/token/task 前返回
  503 `rbac_mode_not_supported`；
- 不调用外部 RBAC read/write API，不进行本地 join/role 写入；
- read 使用 `role=None`、`role_source="rbac_unavailable"`、`mutation_supported=false`；
- RBAC 关闭时 read 使用 fixed legacy role、`role_source="tenant_account_join"`，
  `mutation_supported=true`（仍受 workspace/account/owner guard）；
- RBAC 写支持另立任务，设计 outbox/补偿/审计和 platform actor 权限。

当前部署 `RBAC_ENABLED` 未设置并采用官方默认 `False` 只是部署事实，不是永久产品保证。

## 7. 日志与隐私

允许事件：

- DEBUG/可降频 read：`identity_checked`、`workspace_listed`、`workspace_viewed`、`members_listed`；
- INFO write success（有效 commit 后）：`workspace_renamed`、`members_invited`、
  `member_role_updated`；
- WARNING：稳定业务拒绝 code、资源 ID；delivery failed 只记录 tenant/account ID 与稳定原因分类。

没有 `member_removed`。`logger.exception` 不得记录完整 payload、email list、token、activation URL、配置值
或可能含这些内容的异常文本；可预期业务拒绝仅记录稳定 error code 和资源 ID。生产启用会记录 request body
的 DEBUG logger 会泄漏 invite email，必须作为部署门禁关闭。上述日志用于运维诊断，不是 audit model，
不能据此恢复高风险操作。

## 8. Builder 文件边界

独立复审 PASS 后，B3 Builder 只允许修改：

- `api/configs/feature/__init__.py`
- `api/libs/platform_admin.py`
- `api/services/platform_admin_service.py`
- `api/controllers/console/platform_admin.py`
- `api/tests/unit_tests/configs/test_platform_admin_config.py`
- `api/tests/unit_tests/libs/test_platform_admin.py`
- `api/tests/unit_tests/services/test_platform_admin_service.py`
- `api/tests/unit_tests/controllers/console/test_platform_admin.py`

如需 B3→B4 handoff artifact，只能新增
`docs/enterprise/replay-1.16.0/B3_TO_B4_HANDOFF.md`，且必须由任务明确授权；本 Fixer 不创建它。

禁止修改 controller 注册、models、migrations、contracts、Web、Docker、依赖、`with_session`、
`EnterpriseConfig` 或其他文档。B3 不注册 controller、不生成 contracts。

## 9. B4/B5 handoff

B3 合并并通过复审后，B4 接收：

1. controller module 与上列 14 个 DTO/schema；
2. §3.2 精确 7 条 route；不得添加 member DELETE；
3. 6 个 service public methods；没有 `remove_member`；
4. 错误表、RBAC role 降级契约、`mutation_supported`；
5. 全部 B3 focused tests 与未运行项；
6. B4 只在 `api/controllers/console/__init__.py` 注册 7 条 route，并作为唯一生成者生成最终 contracts；
7. generated contract 必须证明没有 member DELETE。

B5 只消费 generated contract：

- 以 status endpoint 决定平台管理员入口；
- `mutation_supported=false` 时不得启用 invite/role 按钮；
- 不显示成员删除操作；
- delivery 只显示 `queued`/`failed`/`not_applicable`；
- 不手写 route/type，不把 RBAC unavailable role 显示为 legacy 权威角色。

若 B4 contract generation 暴露 B3 schema defect，B4 暂停并交回 B3 独立修订，不得顺手扩大 route。

## 10. 测试矩阵

所有测试均是后续 Builder 计划项，不表示已运行。

| 类别 | 必须证明 |
| --- | --- |
| config | `PLATFORM_ADMIN_EMAILS` 默认空串；显式配置可由 Settings 正确读取；不新增第二个同义配置 |
| config/helper ownership | config tests 不重复解析逻辑；trim/lower/去重继续由 libs helper tests 覆盖 |
| route/service absence | route map、source/API 断言没有 member DELETE、`remove_member` 或隐藏通用 mutation；DELETE 为 404/405 |
| status/auth | ACTIVE/email 规范化；非 admin 403；status 无 current tenant 稳定返回布尔；setup/login 安全不降级 |
| management current tenant | 无 current tenant 返回稳定 `current_tenant_required`，无 AssertionError/500；decorator 顺序正确 |
| ACTIVE 未加入/已加入 | 未加入不创建 join；两者均不修改 current；已加入不修改 join且无 token/task |
| invite token 参数/payload | 对新建 PENDING、既有 PENDING 未加入、既有 PENDING 已加入 resend 分别断言 `generate_invite_token(..., requires_setup=True)`；对 ACTIVE 未加入断言 `requires_setup=False`；ACTIVE 已加入断言不调用；逐类断言 Redis invitation JSON 中的 `requires_setup` |
| 既有 PENDING 未加入/已加入 | 未加入创建 `current=False` join且已有 current 不变；已加入保留原 `join.current`；均显式传 `requires_setup=True` 并验证对应 post-commit 行为 |
| 新账号 | PENDING Account + `current=True` join，一个有效业务事务；commit 后显式以 `requires_setup=True` 生成 token/task |
| activation integration | 隔离 integration 验证 PENDING 经官方 `/activate` 收集 setup fields 后成为 ACTIVE；ACTIVE 接受使用 `requires_setup=False` 且不错误触发 setup 流程 |
| counts/capacity | 分类计数；`required_memberships=0`、`new_account_count=0`、billing disabled、billing limit=0、正好等于 limit、超过 limit、enterprise/billing 互斥；ACTIVE pending invitation 计入瞬时 `required_memberships` 但不构成 reservation |
| capacity accepted limitation | unit 验证邀请时 capacity 检查；source/integration 证据证明 B3 未修改 `/activate` 且该路径不受 B3 锁覆盖；integration 将并发接受超限风险记录为 `KNOWN_LIMITATION`，不得写成最终 limit 保证通过 |
| billing freeze | 仅 billing enabled 调用；命中整批 rollback，无 Account/join/token/task；验证官方 fail-open 语义未被改写 |
| billing cache | immediate join 且 billing enabled 时有效 commit 后清理一次；ACTIVE/no-change 不调用；失败 warning、数据保留且继续 dispatch |
| token revoke | dispatch 失败调用 `revoke_token(None, None, token)`；验证删除 `member_invite:token:{token}`，错误 key 未触碰 |
| token privacy | response/log/snapshot 均无 token/activation URL |
| RBAC enabled reads | role `None`、source unavailable、mutation unsupported；不调用外部 RBAC |
| RBAC enabled writes | invite/role 503；无锁、外部 RBAC、DB write、token/task |
| limit branches | enterprise 只用 workspace `is_available` + new-account seat；billing 只用 limit + DB count；不双算 |
| Redis | TTL 60、blocking timeout 5、tenant→seats→sorted hashes；timeout/Redis error fail closed；异常逆序释放 |
| transaction sequence | begin 前无 DB query；所有 query/flush 在 begin；一个有效业务事务；wrapper commit no-op |
| exception injection | Feature/Billing、flush、token、Celery、response model/dump 逐点注入；DB rollback或稳定 delivery 状态符合阶段 |
| logs | 无 email list/token/config/payload；read 可用 DEBUG；无 `member_removed` |
| DTO/errors | 14 DTO、extra forbid、nullable RBAC role、role source、mutation supported 与稳定 error/status |
| B4/B5 | contract 精确 7 route、无 DELETE；B5 不显示 delete，按 mutation/delivery 字段降级 |
| B0 scope checker | 按实际 checker 范围运行并记录；不得把路径未覆盖冒充通过 |

明确删除任何“成员 remove 成功”、last/current workspace 删除成功或直接删除 join 的测试。

建议 focused 命令：

```bash
uv run --project api pytest \
  api/tests/unit_tests/configs/test_platform_admin_config.py \
  api/tests/unit_tests/libs/test_platform_admin.py \
  api/tests/unit_tests/services/test_platform_admin_service.py \
  api/tests/unit_tests/controllers/console/test_platform_admin.py
```

integration 环境后续才验证真实 PostgreSQL unique/row lock、Redis/Celery 与官方 `/activate` 接受流程。本计划
修订任务不安装依赖，不运行 Docker、数据库、Redis、Weaviate、migration 或 contract generation。

## 11. 风险与最终建议

### 11.1 已整改

- P0-1：通过整体延期并拒绝成员移除解决。
- P1-1：恢复官方 ACTIVE 邀请—接受语义。
- P1-2：补 billing freeze。
- P1-3：固定正确 token revoke 路径。
- P1-4：RBAC read 使用明确降级契约。
- P1-5：enterprise/billing 各用单一 limit 来源。
- P2-1～P2-5：锁等待、事务时序、current tenant、邮件依赖、LoginConfig 放置均已记录或修订。

### 11.2 未闭环风险

- RBAC mutation 不支持，开启时 fail closed；
- Account email 无数据库 unique constraint，B3 lock 不能约束官方注册流；
- notification 无 outbox，不保证 exactly-once/自动重试；
- billing membership cache 清理是 post-commit best-effort，失败时可能短暂陈旧；
- request DEBUG body 可能泄漏 PII，必须由部署门禁关闭；
- 运维日志不是 audit model；
- `PLATFORM_ADMIN_EMAILS` 配置变更需重启；
- ACTIVE invitation capacity 只是邀请时瞬时门禁，无 reservation/recheck；延迟或并发接受可能突破最终
  workspace member limit，这是 2026-07-26 人工明确接受的 `KNOWN_LIMITATION`；
- service commit 后仍存在 controller/framework 序列化故障窗口。

## 12. 最终状态

- 技术建议：**B3_READY**
- 流程状态：**PENDING_INDEPENDENT_REREVIEW**
- Review 声明：**未宣称 PASS**
- Builder：**不授权；等待独立复审 PASS**

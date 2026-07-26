# Dify Enterprise 1.16.0 Replay B3 平台管理员后端实施契约

## 1. 结论与依据

结论：**B3_READY**。

本文件只定义 B3 Builder 的实施契约，不实现业务代码，也不授权 B4、B5 或运行时发布。实现真相按以下
优先级确定：

1. 官方 tag `1.16.0` 的 model、Pydantic Console schema、显式 `Session`、account/tenant/member/RBAC
   和错误处理模式；
2. `DESIGN_GATE.md` 的 DG-02/DG-09、现有 replay handoff、decision matrix、validation plan；
3. 旧提交 `d70f1c3bbd`、`d83e4bb351`、`3f883e23b1` 及
   `origin/codex/enterprise-candidate-1.15.0-20260626` 只作为需求和历史缺陷证据。

旧 1.15 实现中的全局 `db.session`、`console_ns.schema_model`、`marshal_with`、动态
`Account.is_platform_admin` 字段、controller SQLAlchemy、逐项 commit、响应邀请 token/URL 等模式一律不得复制。

### 1.1 已核实的官方 1.16 事务事实

以下结论来自当前代码，不是推测：

- `AccountService.create_account()` 会 `session.commit()`。
- `RegisterService.register()` 使用 nested transaction，但其下游 `create_account()` 和可能的 workspace
  创建仍会 commit，最后自己也 commit/rollback。
- `RegisterService.invite_new_member()` 会调用上述写方法；它还会在返回前写 Redis invitation token 并调用
  `send_invite_member_mail_task.delay()`。
- `TenantService.create_tenant()` 分阶段多次 commit，并调用同样会 commit 的
  `CreditPoolService.create_default_pool()`。
- `TenantService.create_tenant_member()`、`switch_tenant()`、`remove_member_from_tenant()` 和
  `update_member_role()` 都会 commit；remove 还会在 commit 后产生 enterprise/RBAC 外部副作用。
- `RBACService.MemberRoles.replace()` 在 legacy 分支会 commit，在 `RBAC_ENABLED=true` 时调用外部 inner
  RBAC API，无法与本地数据库事务形成原子提交。
- `FeatureService.get_features()`/`get_system_features()` 是容量信息入口；workspace member license 的
  `size/limit/enabled` 来自 enterprise workspace info，seat license 来自 system features。
- `controllers.common.session.with_session` 为 controller 提供显式 `Session`，默认在 handler 正常返回后
  commit、异常时 rollback；当前 session factory 默认 `expire_on_commit=False`。

因此 B3 不调用以上会 commit 的官方写 API。B3 在自己的 service 中以同一个注入 Session 完成允许的
本地数据库写入；只复用不会提交数据库的查询/枚举/语言与 invitation-token 能力。workspace 创建因必须
组合多个会 commit 的官方初始化器和 RBAC/信号副作用，本阶段延期。

## 2. 精确功能范围

`DEFERRED` 表示本轮没有 endpoint；`REJECTED` 表示普通 B3 endpoint 必须显式拒绝该变体，不能借通用
“成员管理”绕过。

| 能力 | 决定 | B3 精确边界 |
| --- | --- | --- |
| 平台管理员身份判断 | INCLUDED | 配置 email 与当前已认证、`ACTIVE` Account 的规范化 email 比较；另提供 B5 可消费的布尔 status endpoint。 |
| 全局 workspace 列表 | INCLUDED | 平台管理员可分页、按名称搜索、按 `normal/archive/all` 过滤；默认只列 `normal`。 |
| 全局 workspace 详情 | INCLUDED | 返回 workspace、owner 和 member count；可读取 `normal`/`archive`。 |
| workspace 创建 | DEFERRED | 官方创建链存在多次 commit、credit pool/plugin strategy/key/signal/RBAC 副作用，B3 允许文件内无法安全原子组合。不得恢复旧创建实现或创建无 owner workspace。 |
| workspace 改名 | INCLUDED | 仅 `normal` workspace；沿用官方允许重名语义，不发明全局 workspace-name 唯一约束。 |
| workspace 删除/归档 | DEFERRED | DG-02 明确延期；不得提供 DELETE/POST archive endpoint。 |
| workspace 成员列表 | INCLUDED | 可读取 `normal`/`archive` workspace；角色来自 `TenantAccountJoin.role`，响应明确为 legacy fixed role。 |
| 邀请新 pending 账号 | INCLUDED | 原子创建 `PENDING` Account 和 join；非 owner role；commit 后才生成 token/投递邮件。 |
| 邀请既有 pending 账号 | INCLUDED | 不在目标 workspace 时新增 join；已在 workspace 时只做 commit 后 resend，不重复 join。 |
| 邀请既有 active 账号 | INCLUDED | 不在目标 workspace 时新增 join并发送 workspace invitation；已在时返回 `already_member`，不写入、不发信。 |
| 成员角色变更 | INCLUDED | 仅 `admin/editor/normal/dataset_operator` 之间；target 为 `ACTIVE/PENDING`；`RBAC_ENABLED=true` 时 fail closed。 |
| 成员移除 | INCLUDED | 非 owner 成员；保护 target 当前 workspace、最后 workspace membership；不删除 Account。 |
| owner 分配/转移 | DEFERRED + REJECTED | 不接受 invite `role=owner`，也不接受普通 role endpoint 晋升 owner；需独立 owner-transfer/audit/RBAC 设计。 |
| owner 降级 | DEFERRED + REJECTED | 普通 role endpoint 遇 owner target：若是最后 owner 返回 `last_owner_protected`；即使异常数据有多个 owner，也返回 `owner_operation_deferred`。 |
| owner 移除 | DEFERRED + REJECTED | 普通 remove endpoint 同上；不得以“多 owner”为由恢复高风险操作。 |
| 密码重置 | DEFERRED | DG-02 明确延期；不得出现 password DTO、route 或 service method。 |
| break-glass | DEFERRED | 不实现紧急接管、header/key bypass、隐式 owner 变更。 |
| 需要新 audit model 的操作 | DEFERRED | B3 不新增 audit model/model/migration。 |

必须等待真正 audit model、migration、通知与恢复设计后才能重新评审的操作：workspace 强制归档/删除、
owner 分配/转移/降级/移除、密码重置、break-glass，以及任何可绕过正常账号生命周期或持久改变全局
安全主体的操作。workspace 创建另因官方初始化链不可原子组合而延期；它不能通过创建后补 owner 的两步
流程恢复。

## 3. 路由、DTO 与错误契约

所有 DTO 均定义在 `api/controllers/console/platform_admin.py`，请求继承 Pydantic `BaseModel`，
`model_config = ConfigDict(extra="forbid")`；响应继承 `fields.base.ResponseModel`。使用
`register_schema_models`、`register_response_schema_models`、`query_params_from_model` 和
`dump_response`。禁止新建 legacy RESTX field dict、`schema_model`、`marshal_with` 或 GET
`ns.expect`。

### 3.1 DTO 清单

- `PlatformAdminStatusResponse`
  - `is_platform_admin: bool`
- `PlatformAdminWorkspaceListQuery`
  - `page: int = 1`，`ge=1`
  - `limit: int = 50`，`ge=1, le=100`
  - `keyword: str | None`，trim 后最长 255，空串转 `None`
  - `status: Literal["normal", "archive", "all"] = "normal"`
- `PlatformAdminWorkspaceOwnerResponse`
  - `id: str`
  - `name: str`
  - `email: str`
- `PlatformAdminWorkspaceResponse`
  - `id/name/plan/status/created_at/updated_at`
  - `member_count: int`
  - `owner: PlatformAdminWorkspaceOwnerResponse | None`
- `PlatformAdminWorkspacePaginationResponse`
  - `items/page/limit/total/has_more`
- `PlatformAdminWorkspaceRenamePayload`
  - `name: str`，strip whitespace，`min_length=1, max_length=255`
- `PlatformAdminMemberResponse`
  - `id/name/email/status/role/current/created_at/last_login_at/last_active_at`
  - `role` 是 `TenantAccountJoin.role` 的 fixed legacy role，不伪装成自定义 RBAC role
- `PlatformAdminMemberListResponse`
  - `items: list[PlatformAdminMemberResponse]`
- `PlatformAdminMemberInvitePayload`
  - `emails: list[EmailStr]`，1～50；先 trim/lower，再检查规范化重复项
  - `role: Literal["admin", "editor", "normal", "dataset_operator"]`
  - `language: str | None`
- `PlatformAdminMemberInviteResultResponse`
  - `email`
  - `action: Literal["account_created", "membership_created", "invitation_resent", "already_member"]`
  - `email_delivery: Literal["queued", "failed", "not_applicable"]`
  - 不含 token、activation URL 或内部异常文本
- `PlatformAdminMemberInviteResponse`
  - `workspace_id`
  - `results`
- `PlatformAdminMemberRoleUpdatePayload`
  - `role: Literal["admin", "editor", "normal", "dataset_operator"]`
- `PlatformAdminMemberMutationResponse`
  - `result: Literal["success"]`
  - `workspace_id/member_id`
- `PlatformAdminErrorResponse`
  - `code/message/status`

Pydantic validation failure沿用 Console 的 400 validation contract。重复 email 必须是稳定的
`duplicate_email` 400，不允许 DTO 静默去重，因为静默去重会掩盖 seat/capacity 计算错误。

### 3.2 endpoint 表

“日志”列中的 write success 必须在数据库 commit 后记录；read success 在 service 成功返回后记录。

| Method | route | request | response | success | platform admin | service | 日志 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/account/platform-admin-status` | 无 | `PlatformAdminStatusResponse` | 200 | 否；仅 login/setup/init | 纯 helper，无 service SQL | `platform_admin.identity_checked`，仅 account id/结果 |
| GET | `/platform-admin/workspaces` | `PlatformAdminWorkspaceListQuery` query | `PlatformAdminWorkspacePaginationResponse` | 200 | 是 | `list_workspaces` | `platform_admin.workspace_listed` |
| GET | `/platform-admin/workspaces/<uuid:workspace_id>` | 无 | `PlatformAdminWorkspaceResponse` | 200 | 是 | `get_workspace` | `platform_admin.workspace_viewed` |
| PATCH | `/platform-admin/workspaces/<uuid:workspace_id>` | `PlatformAdminWorkspaceRenamePayload` | `PlatformAdminWorkspaceResponse` | 200 | 是 | `rename_workspace` | `platform_admin.workspace_renamed` |
| GET | `/platform-admin/workspaces/<uuid:workspace_id>/members` | 无 | `PlatformAdminMemberListResponse` | 200 | 是 | `list_members` | `platform_admin.members_listed` |
| POST | `/platform-admin/workspaces/<uuid:workspace_id>/members/invitations` | `PlatformAdminMemberInvitePayload` | `PlatformAdminMemberInviteResponse` | 201 | 是 | `invite_members` | `platform_admin.members_invited`；delivery failure 单独 warning |
| PATCH | `/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>/role` | `PlatformAdminMemberRoleUpdatePayload` | `PlatformAdminMemberMutationResponse` | 200 | 是 | `update_member_role` | `platform_admin.member_role_updated` |
| DELETE | `/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>` | 无 | 空 body | 204 | 是 | `remove_member` | `platform_admin.member_removed` |

不提供 `POST /platform-admin/workspaces`、workspace DELETE/archive、owner、password 或 break-glass route。
对 204 必须返回真正空 body。

### 3.3 明确错误映射

| code | HTTP | 适用条件 |
| --- | --- | --- |
| Console 既有 unauthenticated contract | 401 | 未认证；由 `login_required` 处理 |
| `platform_admin_required` | 403 | 已认证但非平台管理员、非 ACTIVE 账号；所有已定义 `/platform-admin/**` route 一致 |
| `invalid_request` | 400 | Pydantic/路径以外的普通参数错误 |
| `duplicate_email` | 400 | 同一批中 trim/lower 后重复 |
| `invalid_role` | 400 | owner 或不支持的 fixed role |
| `workspace_not_found` | 404 | workspace id 不存在 |
| `member_not_found` | 404 | account 不存在或不属于目标 workspace；不得泄露跨 workspace account 是否存在 |
| `workspace_unavailable` | 409 | mutation 的 tenant 非 `TenantStatus.NORMAL` |
| `role_already_assigned` | 409 | fixed role 无变化 |
| `member_already_exists` | 409 | 单成员 mutation 发现状态冲突；批量 invite 用结构化 `already_member` 结果 |
| `last_owner_protected` | 409 | target 是最后 owner |
| `owner_operation_deferred` | 409 | target 是 owner 但不是最后 owner |
| `owner_assignment_deferred` | 409 | 尝试把 member 晋升 owner |
| `last_workspace_membership` | 409 | remove 后账号将没有 workspace |
| `current_workspace_membership` | 409 | target join 的 `current=True` |
| `account_uninitialized` | 409 | invite/role target 为 `UNINITIALIZED` |
| `account_disabled` | 409 | invite/role target 为 `BANNED` 或 `CLOSED` |
| `email_identity_ambiguous` | 409 | 历史数据中 case-insensitive email 命中多个 Account |
| `concurrent_operation` | 409 | lock 超时、join unique race 或 optimistic recheck 失败 |
| `workspace_member_limit_exceeded` | 403 | workspace 容量不足 |
| `seat_limit_exceeded` | 403 | 创建新 Account 所需全局 seat 不足 |
| `rbac_mode_not_supported` | 503 | `RBAC_ENABLED=true` 时调用 B3 member mutation；见 §6.9 |

意外异常使用官方通用 500 响应，controller 不回传 `str(exception)`。service domain exception 在
controller 映射为上述稳定 code；预期业务失败记 warning，意外失败使用 `logger.exception`。

### 3.4 B5 身份发现

B5 只调用生成 contract 中的 `GET /account/platform-admin-status`。非管理员得到
`{"is_platform_admin": false}`，不会探测 `/platform-admin/**`，也不会收到配置列表。

status endpoint 故意位于 `/account/**` 而不是 `/platform-admin/**`：若位于后者，非管理员必须 403，
前端就无法安全区分“不是 admin”和网络/权限故障。它只返回调用者自己的单个布尔值，不返回
`PLATFORM_ADMIN_EMAILS`、匹配 email、数量或其他管理员身份，因此不违反“非管理员访问管理端
`/platform-admin/**` 一律 403”。未知、未注册的 route 仍由 Flask 返回 404；这里的 403 保证覆盖 B3/B4
实际注册的全部管理 route。

B3 只定义 controller module，**不得**在 `api/controllers/console/__init__.py` import/register。
B4 在 B3 合并后完成注册和最终 contract generation。

## 4. 鉴权设计

### 4.1 配置

在允许文件 `api/configs/feature/__init__.py` 的现有 `LoginConfig` 增加：

```python
PLATFORM_ADMIN_EMAILS: str = Field(
    description="Comma-separated platform administrator email addresses.",
    default="",
)
```

不修改只读的 `api/configs/enterprise/__init__.py`。默认空串表示没有平台管理员，fail closed。

### 4.2 纯 helper

`api/libs/platform_admin.py` 仅包含无 ORM mutation 的 helper 和 decorator：

- `normalize_platform_admin_email(email: str | None) -> str | None`
  - `strip().lower()`；空值返回 `None`。
- `parse_platform_admin_emails(raw: str) -> frozenset[str]`
  - 逗号切分；每项 trim/lower；忽略空项；set 去重。
- `is_platform_admin_email(email: str | None, configured_emails: str) -> bool`
  - 只组合前两个纯函数；不自己读取 env、数据库或 request。
- `is_platform_admin_account(account: Account | None, configured_emails: str) -> bool`
  - 仅 `AccountStatus.ACTIVE` 且 email 命中时为 true。
- `platform_admin_required(view)`
  - request-aware 薄 decorator；从 Flask-Login `current_user` proxy 解析真实 `Account`，把
    `dify_config.PLATFORM_ADMIN_EMAILS` 传给上述纯 predicate；失败抛 `Forbidden`。

不得缓存或返回原始配置，不得把 config 注入 Account。不得实现
`apply_platform_admin_flag`/`apply_platform_admin_flag_for_accounts`。

### 4.3 decorator 顺序与身份来源

管理 route 统一使用：

```text
setup_required
login_required
account_initialization_required
platform_admin_required
with_session
```

身份只来自已经通过 `login_required` 的 Flask-Login Account/cookie 与 CSRF 保护。鉴权 helper 不读取
URL workspace、`current_tenant_id`、`X-Tenant-Id`、query、JSON 或任意自定义 admin header。因此攻击者
伪造 tenant/header 只能改变未使用的输入，不能使 email predicate 变真。service 再从 path 中的
`workspace_id` 重新查询目标 Tenant，不信任 caller 的 current tenant。

B3 不修改 `wraps.py`、Account model、member fields 或现有 account response；不动态设置 ORM 未声明字段。

## 5. Service 与事务边界

### 5.1 构造与 public API

controller 获得 `with_session` 注入的同一个 `Session` 后，仅执行：

```python
service = PlatformAdminService(session)
```

精确构造：

```python
class PlatformAdminService:
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session
```

public methods：

```text
list_workspaces(*, page: int, limit: int, keyword: str | None,
                status: WorkspaceStatusFilter) -> WorkspacePage
get_workspace(workspace_id: str) -> WorkspaceView
list_members(workspace_id: str) -> list[MemberView]
rename_workspace(*, workspace_id: str, name: str,
                 operator_account_id: str) -> WorkspaceView
invite_members(*, workspace_id: str, emails: tuple[str, ...],
               role: TenantAccountRole, language: str | None,
               operator: Account) -> InviteBatchResult
update_member_role(*, workspace_id: str, member_id: str,
                   new_role: TenantAccountRole,
                   operator_account_id: str) -> MemberMutationResult
remove_member(*, workspace_id: str, member_id: str,
              operator_account_id: str) -> None
```

`WorkspacePage/WorkspaceView/MemberView/InviteBatchResult/MemberMutationResult` 是 service 文件内的 frozen
dataclass 或 TypedDict，不导入 controller DTO，避免 service→controller 依赖。

### 5.2 硬规则

- service 不 import 或使用 `extensions.ext_database.db`；禁止全局 `db.session`。
- controller 不 import SQLAlchemy/model 并且不写查询；只做 DTO、auth、service 调用和 response dump。
- 每个 public write method 从拿锁后第一条 DB 查询起就在唯一的 `with self._session.begin():` 中。
- service 是事务 owner：context 正常退出时一次 commit，异常时 rollback；禁止中途 commit。
- controller 的 `with_session` 负责 Session 生命周期并提供异常安全网；service 已完成的 commit 之后，
  wrapper 的最终 commit 是无新增工作量的 no-op。任何 post-commit dispatch exception必须在 service 内捕获，
  不能冒泡成“整个操作失败”。
- 一个操作中的 Tenant、Account、TenantAccountJoin 查询/flush 必须使用 `self._session`；禁止创建第二个
  Session。
- 只用 `flush()` 获得新 id 或触发约束检查；flush 不是 commit。

### 5.3 禁止调用的官方写 API

B3 write path 禁止调用：

- `AccountService.create_account`
- `RegisterService.register`
- `RegisterService.invite_new_member`
- `TenantService.create_tenant/create_owner_tenant/create_tenant_member/switch_tenant`
- `TenantService.remove_member_from_tenant/update_member_role`
- legacy 分支会 commit 的 `RBACService.MemberRoles.replace`

这些方法适用于各自现有 controller，但不能作为 B3 组合事务的 no-commit primitive。B3 可复用
`get_valid_language`、language→timezone mapping、enum、只读 FeatureService，以及 commit 后的
`RegisterService.generate_invite_token/revoke_token`。

### 5.4 invite 数据库事务

1. DTO 已得到规范化、无重复的 tuple。
2. 获取按 key 排序的分布式锁：
   - tenant：`platform_admin:invite:tenant:<tenant_id>`
   - 全局 seats：`platform_admin:invite:seats`
   - 每个 email：`platform_admin:invite:email:<sha256(normalized_email)>`
   - key 不含明文 email；blocking timeout 后返回 `concurrent_operation`。
3. 进入唯一 `session.begin()`。
4. `SELECT Tenant ... FOR UPDATE`；必须存在且 `NORMAL`。
5. case-insensitive 批量查询 Account。每个 email 0/1 行；多于 1 行报
   `email_identity_ambiguous`。
6. 批量查询目标 tenant joins，计算：
   - `new_account_count`：无 Account 的唯一 email 数；
   - `new_membership_count`：无目标 join 的唯一 email 数；
   - pending 已有 join、active 已有 join均不消耗新容量。
7. 重新读取 `FeatureService` 容量；workspace limit 用当前 DB join count 加
   `new_membership_count`，seat limit 同时要求官方 `seats.is_available(new_account_count)`。任一不足时
   不写入。
8. 新账号直接构造官方 `Account` model：normalized email、本地部分 name、有效 language/timezone、
   `interface_theme="light"`、`status=PENDING`、`initialized_at=naive_utc_now()`、无 password；
   `session.add/flush`。创建逻辑必须保持与官方当前字段默认一致，不能复制旧 password/flag 字段。
9. 为所有需要的新 membership 构造 `TenantAccountJoin`，role 必须 non-owner；新账号的 join
   `current=True`，既有账号的新 join `current=False`，不得改写既有账号的 current workspace。
10. flush；若 unique join 约束或并发 recheck 失败，整个事务 rollback。
11. context 正常退出，单次 commit。
12. commit 后才逐项生成 invitation token 并调用 Celery `.delay()`。active 新 membership 的
    `requires_setup=False`；new/pending 为 `True`。active already-member 不发信；pending already-member
    允许 resend。
13. token/dispatch 失败不回滚已经 commit 的账号/join；best-effort revoke 刚生成的 token，记录
    `platform_admin.invite_delivery_failed`，响应 `email_delivery="failed"`。不得返回 500 或声称 DB
    操作失败。

这保证不会出现已创建 Account 但没有预期 join、或一批邀请只提交一半。邮件队列成功只表示 queued，
不表示最终送达；B3 没有持久化 outbox/audit，不能宣称 exactly-once delivery。

### 5.5 rename、role、remove 事务

- rename：锁 Tenant；检查 `NORMAL`；更新 name；一次 commit。
- role：锁 Tenant 和 target join；检查状态/owner/RBAC/role；更新 join.role；一次 commit。
- remove：锁 Tenant、target join、该 account 的全部 joins 和 tenant owner joins；依次执行 owner、
  current、last-membership guard；只删除 join；一次 commit。B3 不删除 pending Account，不调用 account
  deletion sync，不改 app/dataset maintainer，因为 owner 不允许移除，普通 member 的 maintainer 处理需要
  后续明确契约。

## 6. 安全 guard 算法

### 6.1 tenant 与跨 tenant scope

- read：Tenant 必须存在；list/detail/member list 可读 `NORMAL` 和 `ARCHIVE`。
- write：Tenant 必须存在且 `status == NORMAL`，否则 404/409。
- 所有跨 tenant route 先通过真实认证 Account 的 platform-admin email predicate。
- path workspace id 是唯一 scope 输入；service 每次重新解析，不使用当前 tenant/header 代替。

### 6.2 email 规范化与唯一性

- 配置与邀请 email 都 `strip().lower()`；配置忽略空项并去重。
- invite batch 对规范化重复值报 400，不静默折叠。
- Account 查询使用 `func.lower(Account.email) == normalized`；若历史大小写数据导致多行则 fail closed。
- Account 表当前只有 email index、没有数据库 unique constraint；B3 不允许改 model/migration，因此
  B3 并发创建以 email hash Redis lock 串行化并在锁内重新查询。与范围外官方注册流的极端并发仍列为 P1，
  不伪称数据库已全局保证唯一。

### 6.3 account 状态

| 状态 | invite | role update | remove |
| --- | --- | --- | --- |
| 不存在 | 创建 `PENDING` + join | 不适用 | 404 |
| `PENDING` | join 或 resend | 允许 non-owner role | 允许，但受 owner/current/last-membership guard |
| `ACTIVE` | join；已 join 返回 already_member | 允许 non-owner role | 允许，同上 |
| `UNINITIALIZED` | 409，不能借 invitation 改写独立初始化流程 | 409 | 允许清理非 owner、非 current、非 last join |
| `BANNED/CLOSED`（disabled） | 409 | 409 | 允许清理非 owner、非 current、非 last join |

### 6.4 seat 与 workspace capacity

- 只对真正新增 Account 计算 seat；既有 active/pending 加入新 workspace 不消耗新 seat。
- 只对真正新增 join 计算 workspace member；resend/already-member 为 0。
- batch 先全量分类再检查，禁止边写边检查。
- enterprise workspace limit：若 enabled 且 limit 非 0，要求
  `current_db_join_count + new_membership_count <= limit`，同时保留官方 feature payload 的
  `is_available(new_membership_count)` 检查；两者任一失败即拒绝。
- seat：要求官方 authenticated system features 的 `seats.is_available(new_account_count)`；在全局 B3
  seat lock 内重读。
- 任何 limit failure 整批 rollback，不逐 email 部分成功。

### 6.5 owner

- invite DTO 与 service 双重拒绝 owner。
- role new value owner：`owner_assignment_deferred`。
- role/remove target 当前 role owner：锁住所有 owner joins并计数；`<=1` 为
  `last_owner_protected`；`>1` 仍为 `owner_operation_deferred`。
- 因此普通 API 不能通过“先增加 owner、再删旧 owner”绕过延期边界。

### 6.6 last workspace 与 current workspace

remove 前锁住 target account 的全部 `TenantAccountJoin`：

1. target join 不存在 → `member_not_found`；
2. `join.current is True` → `current_workspace_membership`，B3 不自动切换；
3. join 总数 `<=1` → `last_workspace_membership`；
4. 通过后才删除 target join。

检查对象是被移除 member 的 current/last membership，不是 operator 的 current tenant。

### 6.7 重复邀请

- active + 已 join：结构化 `already_member`，不发 token。
- pending + 已 join：`invitation_resent`，不重复 join，commit 后新 token/邮件。
- active/pending + 未 join：新增 join。
- 同批重复：400。
- unique constraint race：409，整批 rollback。

### 6.8 竞态

- tenant row `FOR UPDATE` 串行化 B3 对同 workspace 的 invite/role/remove。
- target join `FOR UPDATE` 防止角色更新/删除丢失更新。
- owner joins 与 account 全部 joins锁定后再计数，避免 B3 内部 last-owner/last-membership TOCTOU。
- Redis email/seat/tenant locks解决不存在 Account row 无法 `FOR UPDATE` 和 license counter 无数据库约束的
  缺口；锁 key 不含 PII。
- 约束异常统一转换为 `concurrent_operation`，不返回 SQL/constraint 文本。

### 6.9 RBAC mode

`RBAC_ENABLED=true` 时，官方 role source 和 mutation 是外部 inner RBAC API；平台管理员未必是目标
tenant member，且 B3 禁止新增 outbox/audit model，无法把本地 join commit 与远端 role binding
原子化。为避免“DB 成功、RBAC 失败”或反向半完成：

- workspace/member reads仍可返回 legacy join role，并在 contract 文档中明确来源；
- invite、role update、member remove 全部 fail closed 为 503 `rbac_mode_not_supported`；
- 不调用外部 RBAC API，不尝试补偿事务，不冒充成功。

这是安全限制，不是隐藏的 TODO。若目标部署要求 `RBAC_ENABLED=true` 下的平台管理 mutation，必须另建
任务决定权威 role source、platform actor 授权、outbox/补偿和审计后再实现。

### 6.10 敏感信息

- token 不进 response、日志、异常或测试快照。
- 日志不记录 `PLATFORM_ADMIN_EMAILS`、原始 email list、完整 payload。
- invite 日志只记录 account id（已有时）或 email SHA-256 的短指纹、数量与分类。
- controller 不回传内部 exception/SQL/RBAC/Redis 内容。

## 7. 日志方案

使用 `logging.getLogger(__name__)` 和官方 request logging context。`core.logging.context`/logging filter
已为日志注入 `req_id/trace_id`；B3 不生成第二套 correlation id。

| event | level/时机 | 标识 |
| --- | --- | --- |
| `platform_admin.identity_checked` | INFO，status helper 返回时 | operator account id、boolean |
| `platform_admin.authorization_denied` | WARNING，decorator 403 时 | operator account id、request path；无 email/config |
| `platform_admin.workspace_listed` | INFO，查询成功 | operator id、page/limit/result count |
| `platform_admin.workspace_viewed` | INFO，查询成功 | operator id、tenant id |
| `platform_admin.workspace_renamed` | INFO，commit 后 | operator id、tenant id；不记录旧/新名称 |
| `platform_admin.members_listed` | INFO，查询成功 | operator id、tenant id、count |
| `platform_admin.members_invited` | INFO，commit 后 | operator id、tenant id、new account/join/resend/already counts |
| `platform_admin.invite_delivery_failed` | WARNING，commit 后 dispatch 失败 | operator id、tenant id、account id或 email fingerprint、异常类型 |
| `platform_admin.member_role_updated` | INFO，commit 后 | operator id、tenant id、member id、old/new fixed role |
| `platform_admin.member_removed` | INFO，commit 后 | operator id、tenant id、member id |
| `platform_admin.operation_rejected` | WARNING，业务 guard 失败 | operator id、tenant/member id（若已安全解析）、稳定 error code |
| `platform_admin.operation_failed` | ERROR + exception，未知失败/rollback 后 | operator id、允许的资源 id、异常类型；无 payload |

官方全局 debug request logger可能记录 JSON body；生产不得启用包含 request body 的 DEBUG 日志。B3 自身
logger 和响应不记录 token/config；controller/source test 对 token/config 字样和 logger 参数做负向断言。

这些是可检索运行日志，不是不可篡改、可查询、具 retention/访问控制的持久化审计表。它不能满足合规
审计、回放或 exactly-once 通知要求，这正是 owner/password/delete/break-glass 等操作保持延期的原因。

## 8. 文件所有权

### 8.1 Builder 允许写入

- `api/configs/feature/__init__.py`
- `api/libs/platform_admin.py`
- `api/services/platform_admin_service.py`
- `api/controllers/console/platform_admin.py`
- `api/tests/unit_tests/configs/test_platform_admin_config.py`
- `api/tests/unit_tests/libs/test_platform_admin.py`
- `api/tests/unit_tests/services/test_platform_admin_service.py`
- `api/tests/unit_tests/controllers/console/test_platform_admin.py`
- `api/tests/unit_tests/controllers/console/test_platform_admin_contract_source.py`
- 可选隔离 integration tests：
  - `api/tests/test_containers_integration_tests/services/test_platform_admin_service.py`
  - `api/tests/test_containers_integration_tests/controllers/console/test_platform_admin.py`

不需要单独 B3 handoff 文档；本文件 §10 是唯一 handoff source，避免第二份清单漂移。若 Reviewer 强制要求
独立文档，必须先精确批准
`docs/enterprise/replay-1.16.0/B3_TO_B4_HANDOFF.md`，否则 Builder 不得创建。

### 8.2 明确禁止

- `api/controllers/console/__init__.py`
- `api/controllers/console/wraps.py`
- `api/models/**`
- `api/migrations/**`
- `packages/contracts/**`
- `web/**`
- `docker/**`
- 任何生成 contract/OpenAPI artifact
- B2 的四个 migration 文件，尤其空 merge `a71e16c0de01`
- 任何未列出的现有文件、依赖、lockfile、运行配置、volume

## 9. 测试矩阵

### 9.1 Builder 必须运行的 unit/source tests

| 场景 | 必须断言 |
| --- | --- |
| admin/non-admin | normalized 配置命中；non-admin 每个已定义 `/platform-admin/**` route 均 403；status endpoint 分别 true/false |
| email normalization | trim/lower、空配置、空项、重复配置、mixed case；原始配置不泄露 |
| forged tenant/header | 改 path 以外 header/query/current tenant不能改变 admin predicate或 service path scope |
| workspace list/detail | pagination/search/status、owner/member count、archive read、404 |
| rename | normal 成功；archive 409；只 commit 一次；允许同名 |
| invite new pending | 一个 Account + 一个 join；pending/current；commit 后 token/task |
| invite existing pending | 未 join 新增；已 join只 resend；不重复 Account/join |
| invite existing active | 未 join新增且不改 current；已 join already_member、不发信 |
| duplicate batch email | 大小写/空白归一后重复为 400；没有 DB/task 调用 |
| seat limit | 只计算新 Account；整批 403/rollback |
| workspace member limit | 只计算新 join；整批 403/rollback |
| account states | uninitialized/disabled invite和 role 409；remove按 guard执行 |
| role update | non-owner fixed roles成功；same role 409；owner assignment rejected |
| last owner | owner count 1 为 `last_owner_protected`；多 owner仍 deferred |
| last workspace membership | count 1 时拒绝且 join保留 |
| current workspace | target join.current 时拒绝；不自动 switch |
| member not in tenant | 统一 404，不泄露 Account 是否存在 |
| RBAC enabled | member mutation全部 503，外部 RBAC/DB write均未调用 |
| explicit Session identity | constructor注入的对象是所有查询/flush/begin使用的唯一 Session；service 无 `db.session` |
| failure injection | account staged 后、join staged 后、flush/guard异常均 rollback，无半完成 join |
| email timing | rollback 时 token/task从不调用；commit 发生在 token/task 前 |
| email delivery failure | DB 保留，token best-effort revoke，响应 delivery failed，不抛全操作失败 |
| DTO/errors | extra forbid、limit、email、role、query/status和每个稳定 code/status |
| log redaction | 无 token、activation URL、完整 email list、payload、`PLATFORM_ADMIN_EMAILS` |
| controller source | AST/guard确认无 SQLAlchemy/model/db.session/Session constructor/select；无 legacy schema_model/marshal |
| scope checker | B0 diff-owner、controller SQLAlchemy、implicit service session、generated contract guard通过 |

建议命令（依赖已存在时）：

```bash
uv run --project api pytest \
  api/tests/unit_tests/configs/test_platform_admin_config.py \
  api/tests/unit_tests/libs/test_platform_admin.py \
  api/tests/unit_tests/services/test_platform_admin_service.py \
  api/tests/unit_tests/controllers/console/test_platform_admin.py \
  api/tests/unit_tests/controllers/console/test_platform_admin_contract_source.py

scripts/ci/check-enterprise-replay-scope.sh 1.16.0 HEAD
git diff --check
```

Builder 还必须以 B3 的固定 base/head 运行 diff-owner 审核，确认仅 §8.1 路径。不得因当前环境缺依赖而安装
依赖；缺失时记录 `NOT_RUN`。

### 9.2 B4 注册/contract generation 后运行

- 显式 import controller 后的 route registry 测试，确认 §3.2 全部且没有 deferred route。
- `api/tests/unit_tests/controllers/common/test_schema.py`
- `api/tests/unit_tests/commands/test_generate_swagger_specs.py`
- `api/tests/unit_tests/commands/test_lint_response_contracts.py`
- `api/tests/unit_tests/controllers/test_swagger.py` 中对应 Console spec assertions。
- `pnpm --dir packages/contracts gen-api-contract`
- 检查 GET query 在 query、request body/response `$ref`、204 空响应、400/401/403/404/409/503 schema。
- 检查生成 `packages/contracts/generated/api/console/**` 含 status route和全部管理 route；由 B4 提交。

### 9.3 隔离环境 integration tests

在专用 PostgreSQL/Redis/Celery fake或受控 worker环境运行：

- 真实 unique join、row lock、两个并发 invite/role/remove 的竞态。
- seat/workspace feature payload与实际 join计数。
- account+join commit/rollback、current flag保持。
- task仅在 commit后可见；broker失败时 DB仍已提交且响应准确。
- admin cookie/CSRF/non-admin/伪造 header 的完整 HTTP 流。
- archive tenant、last owner、last/current workspace guard。
- B4 生成 OpenAPI与实际响应 validation。

### 9.4 当前明确 NOT_RUN

本 Architect 任务不运行：

- 任何依赖安装或锁定环境创建；
- Docker/Compose；
- PostgreSQL、Redis、Weaviate、volume；
- migration/upgrade/downgrade/stamp；
- Celery worker、真实邮件；
- runtime browser/B5；
- contract generation；
- integration/runtime/发布验证。

文档中的测试均为未来契约，不写成已经通过。

## 10. B4 handoff

B3 合并后，B4 必须接收：

1. controller module：`api/controllers/console/platform_admin.py`。
2. route：§3.2 的 8 条；不得新增 deferred route。
3. request/response DTO：§3.1 全部。
4. schema source：controller 中 Pydantic model registrations、query params、response decorators。
5. tests：
   - `api/tests/unit_tests/controllers/console/test_platform_admin.py`
   - `api/tests/unit_tests/controllers/console/test_platform_admin_contract_source.py`
   - 其余 config/helper/service tests作为不可回归基线。
6. B4 注册动作：
   - 在 `api/controllers/console/__init__.py` import `platform_admin`；
   - 按当前 `__all__` 规则加入 module；
   - 确认 import 一次且所有 route进入 Console namespace。
7. B4 contract 动作：
   - 同智慧广场 endpoint 一次性运行最终 Console OpenAPI/contracts generation；
   - 运行 §9.2 tests；
   - 只提交 generator 产物，不手改 generated files。
8. B5 身份入口：只消费生成的 `/account/platform-admin-status`；管理 query/mutation只消费生成 route/types。

B4 不得回头修改 B3 独占文件：

- `api/configs/feature/__init__.py`
- `api/libs/platform_admin.py`
- `api/services/platform_admin_service.py`
- `api/controllers/console/platform_admin.py`
- B3 的 config/helper/service/controller/source tests

若 contract generation 暴露 B3 schema defect，B4 必须暂停并交回 B3 owner形成独立修复，不得在 B4 顺手
修改平台管理员实现。

## 11. 风险与最终建议

### P0

0。允许范围、鉴权、route/DTO、单事务、post-commit 邮件、owner/last/current/seat guard 和 B3/B4 文件
边界已形成可执行契约。

### P1

1. `RBAC_ENABLED=true` 的远端 role authority 无法与本地 join原子提交；B3 明确 fail closed，后续若要求
   支持必须独立设计 outbox/补偿、platform actor权限与审计。
2. Account email 当前没有数据库 unique constraint；B3 Redis email lock覆盖 B3 并发，但不能约束同时
   发生的范围外官方注册流。发现多行时 fail closed，后续 schema修复需独立 model/migration任务。
3. 没有持久化 notification outbox；broker故障只能准确返回/记录 delivery failure，不能保证自动重试。
4. 官方 DEBUG request logging可能记录 invite email payload；生产必须关闭 request-body DEBUG，B3 自身
   logger仍保持脱敏。

### P2

1. 运行日志不是持久化 audit model，不能用于合规证明或可靠回放。
2. `PLATFORM_ADMIN_EMAILS` 是启动配置；变更按当前 Settings 生命周期需重启，不提供运行时管理 API。
3. read success日志在超大部署可能有量；上线时通过现有日志级别/采集策略控制，不在 B3 新增采样系统。

最终建议：**B3_READY**。Builder 必须严格实现本文件的低风险子集；不得用旧 1.15 CRUD、官方会自行
commit 的 service 方法、通用“成员管理”措辞或 B4 contract generation扩大范围。

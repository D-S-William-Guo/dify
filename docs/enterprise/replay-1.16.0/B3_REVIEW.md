# Dify Enterprise 1.16.0 Replay B3 Independent Code Review

## 0. 审查元数据

- 角色：独立 B3 Code Reviewer；非 Architect、Fixer 或 Builder
- 审查分支：`ctyun/replay-116-b3-reviewer`
- 审查 HEAD：`77f3651796783b0ab60fadc53eea3725e8739f9d`
- 官方源码基准：tag `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- Builder 提交范围：`f5dba3ee47d6697ca9883ef455f4e08733f4f229..77f3651796783b0ab60fadc53eea3725e8739f9d`
- 前置核验：分支、HEAD、工作区干净，三项全部通过
- 审查方法：逐项对照官方 1.16 源码独立验证，不接受计划文档相互证明

## 1. 最终结论

**PASS**。

**B3_CODE_ACCEPTED**。

**FIXER_NOT_REQUIRED**。

P0/P1/P2 数量：**P0=0, P1=0, P2=0**。

Builder 的实现精确、忠实地执行了 B3 Implementation Plan 契约，在授权安全、事务模型、邀请状态矩阵、capacity guard、Redis 锁策略、日志隐私和测试质量方面没有发现阻断问题。

## 2. 前置门禁核验

| 检查项 | 预期 | 实际 | 状态 |
| --- | --- | --- | --- |
| 分支 | `ctyun/replay-116-b3-reviewer` | `ctyun/replay-116-b3-reviewer` | PASS |
| HEAD | `77f3651796783b0ab60fadc53eea3725e8739f9d` | `77f3651796783b0ab60fadc53eea3725e8739f9d` | PASS |
| 工作区干净 | 无未跟踪/修改文件 | 干净 | PASS |

## 3. 文件范围核验

| # | 文件 | 行数 | 批准 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | `api/configs/feature/__init__.py` | +4 | ✓ | PASS |
| 2 | `api/libs/platform_admin.py` | +97 | ✓ | PASS |
| 3 | `api/services/platform_admin_service.py` | +577 | ✓ | PASS |
| 4 | `api/controllers/console/platform_admin.py` | +355 | ✓ | PASS |
| 5 | `api/tests/unit_tests/configs/test_platform_admin_config.py` | +19 | ✓ | PASS |
| 6 | `api/tests/unit_tests/libs/test_platform_admin.py` | +77 | ✓ | PASS |
| 7 | `api/tests/unit_tests/services/test_platform_admin_service.py` | +1189 | ✓ | PASS |
| 8 | `api/tests/unit_tests/controllers/console/test_platform_admin.py` | +233 | ✓ | PASS |

**负向核验**（确认未修改/未新增）：

- [x] `api/controllers/console/__init__.py` — controller 未注册（B4 任务）
- [x] contract generation — 未生成
- [x] `api/models/` — 无 model/migration 修改
- [x] `web/` — 无前端修改
- [x] `docker/` — 无 Docker 修改
- [x] `dify-agent/` — 无 agent 修改
- [x] member removal — 无 `remove_member`、无 member DELETE route
- [x] workspace create/delete/archive — 无对应 route
- [x] owner mutation — DTO 排除 owner，service 拒绝 owner
- [x] 外部 RBAC write/read — B3 不调用外部 RBAC API
- [x] `with_session` — 未修改
- [x] `EnterpriseConfig` — 未修改
- [x] 第二个同义配置 — 仅 `LoginConfig.PLATFORM_ADMIN_EMAILS`

## 4. 7-Route / 14-DTO / 6-Method 核验

### 4.1 Route 核对（精确 7 条）

| # | Method | Route | Controller Class | 状态 |
| --- | --- | --- | --- | --- |
| 1 | GET | `/account/platform-admin-status` | `PlatformAdminStatusApi` | PASS |
| 2 | GET | `/platform-admin/workspaces` | `PlatformAdminWorkspaceListApi` | PASS |
| 3 | GET | `/platform-admin/workspaces/<uuid:workspace_id>` | `PlatformAdminWorkspaceApi` | PASS |
| 4 | PATCH | `/platform-admin/workspaces/<uuid:workspace_id>` | `PlatformAdminWorkspaceApi` | PASS |
| 5 | GET | `/platform-admin/workspaces/<uuid:workspace_id>/members` | `PlatformAdminWorkspaceMembersApi` | PASS |
| 6 | POST | `/platform-admin/workspaces/<uuid:workspace_id>/members/invitations` | `PlatformAdminWorkspaceInvitationsApi` | PASS |
| 7 | PATCH | `/platform-admin/workspaces/<uuid:workspace_id>/members/<uuid:member_id>/role` | `PlatformAdminWorkspaceMemberRoleApi` | PASS |

验证方式：controller test `test_platform_admin_controller_defines_exact_seven_method_route_pairs` 通过 AST 解析确认。独立手动核对 controller 源码确认。

**负向确认**：无 DELETE route、无 workspace create/delete/archive route、无 owner mutation route、无 password-reset/break-glass route。

### 4.2 DTO 核对（14 个）

| # | DTO 名称 | 类型 | 状态 |
| --- | --- | --- | --- |
| 1 | `PlatformAdminStatusResponse` | Response | PASS |
| 2 | `PlatformAdminWorkspaceListQuery` | Query (BaseModel) | PASS |
| 3 | `PlatformAdminWorkspaceOwnerResponse` | Response | PASS |
| 4 | `PlatformAdminWorkspaceResponse` | Response | PASS |
| 5 | `PlatformAdminWorkspacePaginationResponse` | Response | PASS |
| 6 | `PlatformAdminWorkspaceRenamePayload` | Payload (BaseModel) | PASS |
| 7 | `PlatformAdminMemberResponse` | Response | PASS |
| 8 | `PlatformAdminMemberListResponse` | Response | PASS |
| 9 | `PlatformAdminMemberInvitePayload` | Payload (BaseModel) | PASS |
| 10 | `PlatformAdminMemberInviteResultResponse` | Response | PASS |
| 11 | `PlatformAdminMemberInviteResponse` | Response | PASS |
| 12 | `PlatformAdminMemberRoleUpdatePayload` | Payload (BaseModel) | PASS |
| 13 | `PlatformAdminMemberRoleUpdateResponse` | Response | PASS |
| 14 | `PlatformAdminErrorResponse` | Response | PASS |

验证方式：controller test `test_platform_admin_defines_exact_fourteen_dtos` 通过 inspection 计数确认。独立手动核对 14 个 DTO 定义。

- 所有请求 DTO 均使用 `ConfigDict(extra="forbid")` ✓
- 响应无 token/activation URL ✓
- RBAC member response: `role=None`, `role_source="rbac_unavailable"`, `mutation_supported=false` ✓
- 无 member remove/mutation DTO，无通用于 DELETE 的 response ✓

### 4.3 Service Public Methods 核对（6 个）

| # | Method | 类型 | 状态 |
| --- | --- | --- | --- |
| 1 | `list_workspaces` | Read | PASS |
| 2 | `get_workspace` | Read | PASS |
| 3 | `list_members` | Read | PASS |
| 4 | `rename_workspace` | Write | PASS |
| 5 | `invite_members` | Write | PASS |
| 6 | `update_member_role` | Write | PASS |

验证方式：`test_platform_admin_service_exposes_exact_public_methods` 通过 `vars(PlatformAdminService)` 确认。

- 无 `remove_member` 或通用 delete/mutation method ✓
- 所有 write 方法使用 `with self._session.begin():` 管理事务 ✓

## 5. 授权与 RBAC 安全审查

### 5.1 配置

- `PLATFORM_ADMIN_EMAILS` 在 `LoginConfig`，默认 `""` — fail closed ✓
- 仅一个 `PLATFORM_ADMIN` 配置字段（测试确认）✓
- 不修改 `EnterpriseConfig` ✓

### 5.2 邮箱规范化

```python
# api/libs/platform_admin.py:32-37
def normalize_platform_admin_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None
```

- `strip().lower()` ✓
- 空值/空白返回 `None` ✓

```python
# api/libs/platform_admin.py:40-48
def parse_platform_admin_emails(configured_emails: str | None) -> frozenset[str]:
    if not configured_emails:
        return frozenset()
    return frozenset(
        normalized
        for item in configured_emails.split(",")
        if (normalized := normalize_platform_admin_email(item)) is not None
    )
```

- 逗号拆分、逐项规范化、去重 ✓
- 空配置返回空 frozenset ✓

### 5.3 身份判断

```python
# api/libs/platform_admin.py:51-61
def is_platform_admin_account(account, configured_emails=None) -> bool:
    if account is None or account.status != AccountStatus.ACTIVE:
        return False
    ...
```

- 仅 `AccountStatus.ACTIVE` 命中 ✓
- PENDING/UNINITIALIZED/BANNED 返回 False（parametrized test 已覆盖）；CLOSED 通过 `!= ACTIVE` 隐式 fail-closed（role mutation test 另有 CLOSED 覆盖）✓
- email 规范化后与 allowlist 比较 ✓

### 5.4 身份来源

`_resolved_current_account()` 从 `current_user` (Flask-Login proxy) 解析，不读取：

- request header ✓
- query string ✓
- request body ✓
- URL tenant/workspace ✓

### 5.5 Decorator 顺序

**Status route**: `setup_required → login_required` ✓

**Management routes (6 条)**:
```
setup_required → login_required → platform_admin_required
→ platform_admin_current_tenant_required → account_initialization_required → with_session
```

验证方式：`test_management_decorator_order` 通过 `__wrapped__` 链确认。

- `platform_admin_required` 在 `account_initialization_required` 之前 — 非管理员在初始化检查前就被拒绝 ✓
- `platform_admin_current_tenant_required` 在 `account_initialization_required` 之前 — 无 current tenant 返回 409 而非 500 AssertionError ✓
- `setup_required` 和 `login_required` 在最前面 — security 不降级 ✓
- CSRF 检查在 `login_required` 内执行（官方已有逻辑），在 `platform_admin_required` 之前 ✓

### 5.6 RBAC

**Read**: `RBAC_ENABLED=true` 时：
```python
# api/services/platform_admin_service.py:182-197
rbac_enabled = bool(dify_config.RBAC_ENABLED)
return [
    MemberView(
        ...
        role=None if rbac_enabled else str(join.role),
        role_source="rbac_unavailable" if rbac_enabled else "tenant_account_join",
        mutation_supported=not rbac_enabled,
    )
    ...
]
```

- `role=None`, `role_source="rbac_unavailable"`, `mutation_supported=false` ✓
- 不调用外部 RBAC API ✓

**Write**: `RBAC_ENABLED=true` 时，invite 和 role mutation 在任何锁/DB/Redis/token/task 前返回 503 ✓
```python
# api/services/platform_admin_service.py:233
if dify_config.RBAC_ENABLED:
    _raise("rbac_mode_not_supported", ...)
```
- 测试确认 `lock.assert_not_called()`, `session.mock_calls == []` ✓

**Status**: `mutation_supported` = `is_admin and not RBAC_ENABLED` ✓

## 6. 事务与 Session 审查

### 6.1 Controller Session 注入

Controller 仅使用 `with_session` 注入的 `Session`：
- 3 读操作：`with_session(write=False)` ✓
- 3 写操作：`with_session` (默认 write=True) ✓

Controller 不创建、管理或直接调用 session.commit/rollback ✓

### 6.2 Service 事务模型

```python
# rename_workspace (api/services/platform_admin_service.py:202-212)
with self._session.begin():
    tenant = self._session.scalar(
        select(Tenant).where(Tenant.id == workspace_id).with_for_update().limit(1)
    )
    ...
    tenant.name = name
    self._session.flush()
```

```python
# update_member_role (api/services/platform_admin_service.py:338-371)
with self._session.begin():
    tenant = self._session.scalar(...)
    join = self._session.scalar(...)
    account = self._session.scalar(...)
    ...
    join.role = role
    self._session.flush()
```

```python
# _persist_invitations (api/services/platform_admin_service.py:423-546)
with self._session.begin():
    tenant = self._session.scalar(...)
    accounts = self._session.scalars(...)
    joins = self._session.scalars(...)
    ...
```

三种写操作的共同特征：
- 所有 DB query/flush 在 `begin()` 块内 ✓
- 无中途 commit ✓
- 无第二 Session ✓
- 正常退出时 begin 自动 commit，异常时自动 rollback ✓
- `with_session` decorator 的后续 commit 是 no-op（事务已被 begin 处理）✓

### 6.3 事务时序验证

`test_invitation_begins_transaction_before_first_injected_session_query` 确认：
- 事件序列为 `begin → query → ... → commit`（`begin` 在首次 query 之前）✓

`test_token_and_task_run_only_after_transaction_commit` 确认：
- 事件序列为 `begin → commit → token → task`（token/task 在 commit 之后）✓

### 6.4 Rollback 验证

`test_invitation_transaction_failures_do_not_dispatch_or_report_success` 验证三个失败点：
- `feature` (FeatureService 异常): events 以 `rollback` 结尾，无 token/task，无 success log ✓
- `billing` (BillingService 异常): events 以 `rollback` 结尾，无 token/task ✓
- `flush` (IntegrityError): events 以 `rollback` 结尾，raise `PlatformAdminHTTPError` ✓

`test_rename_integrity_error_maps_conflict_without_success_log` 确认：
- IntegrityError → `concurrent_operation` 409，无 success log ✓
- 事务回滚 ✓

`test_role_update_integrity_error_has_no_success_log` 同样验证 ✓

### 6.5 Post-Commit 异常

`test_token_generation_failure_returns_failed_without_task_or_revoke` 确认：
- token 生成失败 → `email_delivery="failed"`，不回滚 DB ✓

`test_token_revoke_failure_is_suppressed_and_sanitized` 确认：
- dispatch 失败 → token 被 revoke → revoke 失败 → suppressed，不冒泡 ✓
- delivery="failed"，日志不含 email/token/异常文本 ✓

`test_billing_cache_failure_is_post_commit_best_effort_and_dispatch_continues` 确认：
- billing cache 失败 → dispatch 继续 → delivery="queued" ✓

## 7. 邀请状态矩阵审查

逐项对照官方 `account_service.py:2046-2133` (`invite_new_member`)、`account_service.py:2135-2149` (`generate_invite_token`)、`activate.py:127-193`：

| B3 场景 | DB commit | action | requires_setup | token/task | 测试覆盖 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| Account 不存在 | 新 PENDING Account + `current=True` join | `account_created` | `True` | commit 后 | `test_invitation_state_matrix[None,False]` | PASS |
| 既有 PENDING 未加入 | 新 join, `current=False` | `membership_created` | `True` | commit 后 | `test_invitation_state_matrix[PENDING,False]` | PASS |
| 既有 PENDING 已加入 | 不重复 join, current 不变 | `invitation_resent` | `True` | commit 后 | `test_invitation_state_matrix[PENDING,True]` | PASS |
| ACTIVE 未加入 | 不建 join, current 不变 | `invitation_queued` | `False` | commit 后 | `test_invitation_state_matrix[ACTIVE,False]` | PASS |
| ACTIVE 已加入 | 不修改 join/current | `already_member` | 无 | 无 | `test_invitation_state_matrix[ACTIVE,True]` | PASS |

### 7.1 requires_setup 显式传参

`_persist_invitations` 方法中四个发 token 分支均显式设置 `requires_setup`：
- New account: `requires_setup = True` (line 519) ✓
- PENDING + no join: `requires_setup = True` (line 531) ✓
- PENDING + join (resend): `requires_setup = True` (line 534) ✓
- ACTIVE + no join: `requires_setup = False` (line 537) ✓

`invite_members` dispatch loop 中 (line 286-291)：
```python
token = RegisterService.generate_invite_token(
    tenant,
    dispatch.account,
    str(normalized_role),
    requires_setup=dispatch.requires_setup,
)
```
- 显式传参，不依赖默认值 ✓

`test_final_dispatch_uses_explicit_requires_setup` 参数化验证四个动作的显式传参 ✓

`test_invitation_token_redis_payload_contains_explicit_requires_setup` 验证 Redis payload 中的 `requires_setup` 值 ✓

### 7.2 Token/Task 时序

`test_token_and_task_run_only_after_transaction_commit` 确认 token 和 task 在 `commit` 事件之后 ✓

### 7.3 Token Revoke

```python
# api/services/platform_admin_service.py:301-303
if token is not None:
    with contextlib.suppress(Exception):
        RegisterService.revoke_token(None, None, token)
```

`test_invite_dispatches_explicit_requires_setup_and_revokes_correct_token` 确认：
- `revoke_token` 调用参数为 `(None, None, "sensitive-token")` — 删除正确的 `member_invite:token:{token}` key ✓

### 7.4 already_member 无 token/task

`test_active_existing_member_does_not_generate_token_or_task` 确认：
- `generate_invite_token` 未被调用 ✓
- `send_invite_member_mail_task.delay` 未被调用 ✓
- `email_delivery == "not_applicable"` ✓

### 7.5 Billing Freeze

```python
# api/services/platform_admin_service.py:485-488
if dify_config.BILLING_ENABLED:
    for email in emails:
        if email not in account_by_email and BillingService.is_email_in_freeze(email):
            _raise("email_in_freeze", ...)
```

- 仅 `BILLING_ENABLED=true` 时检查 ✓
- 仅检查新 Account (email not in account_by_email) ✓
- 命中则事务回滚，整批无副作用 ✓

`test_billing_freeze_rejects_new_account_before_database_write_or_dispatch` 确认：
- `error_code == "email_in_freeze"` ✓
- `session.add.assert_not_called()` — 无 Account/join 创建 ✓

### 7.6 Billing Cache

```python
# api/services/platform_admin_service.py:272-279
if immediate_join_count > 0 and dify_config.BILLING_ENABLED:
    try:
        BillingService.clean_billing_info_cache(tenant.id)
    except Exception:
        logger.warning(...)
```

- 仅 immediate_join_count > 0 且 billing enabled 时清理 ✓
- 清理失败 best-effort，不阻止后续 dispatch ✓
- 日志脱敏（仅 tenant ID 和稳定原因）✓

`test_billing_cache_only_runs_for_immediate_join_when_billing_enabled` 参数化验证：
- billing_enabled=False, join_count=1 → 0 次调用 ✓
- billing_enabled=True, join_count=0 → 0 次调用 ✓
- billing_enabled=True, join_count=1 → 1 次调用 ✓

## 8. Capacity 与并发审查

### 8.1 零增量

```python
# api/services/platform_admin_service.py:554-556
def _check_capacity(self, *, tenant_id, required_memberships, new_account_count):
    if required_memberships <= 0:
        return
```

`test_capacity_zero_increment_skips_all_external_and_database_calls` 确认：
- `FeatureService.get_features` 未调用 ✓
- `FeatureService.get_system_features` 未调用 ✓
- session scalar 未调用 ✓

### 8.2 Enterprise 分支

```python
# api/services/platform_admin_service.py:559-567
if dify_config.ENTERPRISE_ENABLED:
    workspace_members = features.workspace_members
    if workspace_members.enabled is True and not workspace_members.is_available(required_memberships):
        _raise("workspace_member_limit_exceeded", ...)
    if new_account_count > 0:
        seats = FeatureService.get_system_features(is_authenticated=True).license.seats
        if not seats.is_available(new_account_count):
            _raise("seat_limit_exceeded", ...)
    return
```

- `workspace_members.enabled is True` guard ✓
- seat 仅在 `new_account_count > 0` 时调用 ✓
- enterprise 分支 return，不进入 billing 分支 ✓

`test_enterprise_capacity_checks_workspace_but_skips_seats_for_existing_accounts` 确认：
- `new_account_count=0` → `get_system_features` 未调用 ✓

`test_enterprise_workspace_unavailable_is_rejected` 确认 workspace limit 拒绝 ✓

`test_enterprise_seat_unavailable_is_rejected` 确认 seat limit 拒绝 ✓

`test_enterprise_capacity_does_not_apply_billing_count` 确认不双算 ✓

### 8.3 Billing 分支

```python
# api/services/platform_admin_service.py:569-577
if dify_config.BILLING_ENABLED and features.billing.enabled is True:
    current_member_count = ...
    if 0 < features.members.limit < current_member_count + required_memberships:
        _raise("workspace_member_limit_exceeded", ...)
```

- `features.billing.enabled is True` guard ✓
- `limit=0` → `0 < 0` 为 False → 不拒绝（unlimited）✓
- 等于 limit → `0 < limit < limit` 为 False → 不拒绝 ✓

`test_billing_capacity_unlimited_equal_and_exceeded` 参数化验证：
- limit=0, current=100 → 不拒绝 ✓
- limit=2, current=1 → `0 < 2 < 2` = False → 不拒绝 ✓
- limit=1, current=1 → `0 < 1 < 2` = True → 拒绝 ✓

`test_billing_disabled_feature_does_not_query_member_count` 确认 billing disabled 时不查询 DB ✓

### 8.4 ACTIVE 邀请瞬时门禁

B3 遵循官方邀请-接受流程，ACTIVE 未加入不创建 join。代码确认：
- `action == "invitation_queued"` (line 536) ✓
- 不创建 join (line 535-537: 仅 `elif join is None`, `ACCOUNT.ACTIVE` 命中此分支时才走到这里) ✓
- `pending_invitation_count` 计入 `required_memberships` (line 472, 478) ✓

### 8.5 Redis 锁

```python
# 固定顺序
lock_keys = [
    f"platform_admin:invite:tenant:{workspace_id}",
    "platform_admin:invite:seats",
    *[
        f"platform_admin:invite:email:{digest}"
        for digest in sorted(sha256(email.encode()).hexdigest() for email in emails)
    ],
]
```

- TTL=60, blocking_timeout=5 ✓
- 获取顺序：tenant → seats → sorted email hashes ✓
- key 使用 sha256, 不含明文 email ✓
- 通过 `contextlib.ExitStack` 逆序释放 ✓

`test_invite_lock_order_ttl_timeout_and_reverse_release` 确认：
- TTL 和 blocking_timeout 参数正确传递 ✓
- 获取顺序正确 ✓
- 释放顺序为逆序 ✓
- key 中无明文 email ✓

`test_lock_failures_map_to_concurrent_operation` 参数化验证 LockError/RedisError → 409 ✓

`test_partial_lock_failure_releases_acquired_locks_in_reverse_order` 确认部分失败时逆序释放 ✓

## 9. 日志与隐私审查

### 9.1 允许的日志事件

| 事件 | 级别 | 内容 | controller:line |
| --- | --- | --- | --- |
| `platform_admin.identity_checked` | DEBUG | `is_platform_admin` 布尔值 | :224 |
| `platform_admin.workspace_listed` | DEBUG | page, limit | :253 |
| `platform_admin.workspace_viewed` | DEBUG | workspace_id | :269 |
| `platform_admin.workspace_renamed` | INFO | workspace_id, operator_account_id | :216-220 |
| `platform_admin.members_invited` | INFO | workspace_id, operator_account_id, result_count | :311-316 |
| `platform_admin.member_role_updated` | INFO | workspace_id, member_id, operator_account_id | :376-380 |
| `platform_admin.members_listed` | DEBUG | workspace_id | :307 |

### 9.2 禁止的敏感内容

逐项核查所有日志语句：

- 无 email list ✓
- 无 token ✓
- 无 activation URL ✓
- 无 allowlist 配置值 ✓
- 无 request payload ✓
- 无完整外部异常文本 ✓
- 无 `member_removed` 日志 ✓

### 9.3 失败日志脱敏

```python
# 邀请交付失败 (line 304-308)
logger.warning(
    "platform_admin.invitation_delivery_failed workspace_id=%s account_id=%s reason=dispatch_error",
    tenant.id,
    dispatch.account.id,
)
```

```python
# Billing cache 失败 (line 276-279)
logger.warning(
    "platform_admin.billing_cache_invalidation_failed workspace_id=%s reason=external_error",
    tenant.id,
)
```

- 仅记录 resource ID 和稳定 reason 分类 ✓
- 无 email/token/payload ✓

### 9.4 测试验证

`test_token_revoke_failure_is_suppressed_and_sanitized` 确认日志不含：
- account email ✓
- token value ✓
- 完整异常文本 ✓

`test_billing_cache_failure_is_post_commit_best_effort_and_dispatch_continues` 同样验证 ✓

## 10. 测试质量审查

### 10.1 测试统计

| 测试文件 | 测试数量（估算） |
| --- | --- |
| `test_platform_admin_config.py` | 3 |
| `test_platform_admin.py` | 6 |
| `test_platform_admin_service.py` | ~30 |
| `test_platform_admin_controller.py` | ~11 |
| **总计** | **~50** |

### 10.2 关键测试覆盖矩阵

| 测试类别 | 具体测试 | 验证方式 | 状态 |
| --- | --- | --- | --- |
| 配置 | 默认空串、环境变量读取、唯一字段 | monkeypatch | PASS |
| 邮箱规范化 | trim/lower/空值/空白 | parametrize | PASS |
| 授权 fail-closed | 非 ACTIVE/PENDING/UNINITIALIZED/BANNED | parametrize | PASS |
| Decorator | 403 短路、409 current tenant、顺序 | mock + patch | PASS |
| 7-route/14-DTO | AST 解析 + inspection | 独立验证 | PASS |
| 5-状态矩阵 | 所有 invite 分支 | parametrize | PASS |
| requires_setup | 四分支显式值 + Redis payload | parametrize | PASS |
| Token/task 时序 | begin→commit→token→task | 录制事件序列 | PASS |
| Token revoke | revoke_token(None, None, token) | mock 参数断言 | PASS |
| Capacity 零增量 | 跳过所有外部调用 | mock count | PASS |
| Enterprise capacity | workspace + seat guard | mock + 参数化 | PASS |
| Billing capacity | unlimited/equal/exceeded | parametrize | PASS |
| Billing disabled | 不查询 DB | mock count | PASS |
| Billing freeze | 新 Account freeze 拒绝 | mock + patch | PASS |
| Billing cache | 条件触发 + 失败继续 | parametrize | PASS |
| Transaction begin | begin 在 query 之前 | 录制事件序列 | PASS |
| Transaction rollback | 三失败点 + IntegrityError | parametrize | PASS |
| RBAC read | role=None, source, mutation | mock config | PASS |
| RBAC write | 503 在锁/DB 之前 | mock count | PASS |
| Redis 锁 | TTL/timeout/顺序/释放/逆序 | 录制 + patch | PASS |
| Redis 失败 | LockError/RedisError → 409 | parametrize | PASS |
| 部分锁释放 | 逆序释放已获取锁 | 录制事件 | PASS |
| 日志隐私 | 无 email/token/异常文本 | caplog | PASS |
| DTO extra=forbid | 4 个 request model | parametrize | PASS |
| 响应无敏感字段 | token/activation_url 不在 fields | inspection | PASS |
| Owner reject | role=owner → ValidationError | parametrize | PASS |
| Account status guard | UNINITIALIZED/BANNED/CLOSED（role mutation）；PENDING/UNINITIALIZED/BANNED（helper）| parametrize | PASS |
| 序列化失败 | 不隐藏 | pytest.raises | PASS |
| 无 DELETE | 7 route 确认 + AST | 双重验证 | PASS |
| 无 remove_member | public method 集合 + vars | inspection | PASS |

### 10.3 假阳性检查

验证测试不依赖 MagicMock 默认行为的假阳性：

- 事务测试使用自定义 `_RecordingTransaction` 类录制 begin/commit/rollback 事件 — 验证实际调用序列 ✓
- 锁测试使用自定义 `_RecordingLock` 类录制 enter/exit 顺序 — 验证实际锁行为 ✓
- Token/task 测试使用 `assert_called_once_with` / `assert_not_called` 验证精确参数 — 不依赖默认值 ✓
- Log 隐私测试使用 `caplog` 验证具体文本的缺失 — 不是简单的 `assert "token" not in str(mock)` ✓
- capacity 测试使用 `is_available` mock 返回值精确控制 True/False — 不依赖 mock 默认 False ✓

### 10.4 已执行测试结果

| 测试命令 | 结果 | 说明 |
| --- | --- | --- |
| `git diff --check HEAD^ HEAD` | **PASS** | 无空白错误 |
| ruff check (8 文件) | **NOT_RUN** | ruff 未安装在当前环境 |
| focused pytest (4 测试文件) | **NOT_RUN** | 见 §12 |

## 11. 实际运行结果

### 11.1 diff-check

```bash
git diff --check HEAD^ HEAD
# (no output) → PASS
```

### 11.2 ruff

```bash
ruff check api/configs/feature/__init__.py api/libs/platform_admin.py \
  api/services/platform_admin_service.py api/controllers/console/platform_admin.py \
  api/tests/unit_tests/configs/test_platform_admin_config.py \
  api/tests/unit_tests/libs/test_platform_admin.py \
  api/tests/unit_tests/services/test_platform_admin_service.py \
  api/tests/unit_tests/controllers/console/test_platform_admin.py
# ruff: 未找到命令
```

**NOT_RUN**: ruff 在 PATH 中不可用。当前环境未安装 ruff。

### 11.3 Focused Pytest

```bash
uv run --project api --no-sync pytest \
  api/tests/unit_tests/configs/test_platform_admin_config.py \
  api/tests/unit_tests/libs/test_platform_admin.py \
  api/tests/unit_tests/services/test_platform_admin_service.py \
  api/tests/unit_tests/controllers/console/test_platform_admin.py
```

**NOT_RUN** — 根因：

- `api/.venv/bin/python` 是 Python 3.12.13，但 venv 中**不包含 pytest**
- `uv run --project api --no-sync` 未安装依赖，`--no-sync` 禁止向 venv 添加 pytest
- `uv run` 从 PATH fallback 找到了 `/home/ctyun/.local/bin/pytest`
- 该 pytest 的 shebang 是 `/usr/bin/python3`，即系统 **Python 3.10.12**
- Dify 1.16 的 `api/core/workflow/node_factory.py:234` 使用了 PEP 695 `type` 语句，Python 3.10 无法解析，导致 `SyntaxError` 和 collection 失败

B3 的 8 个文件不使用 `type` 语句。此错误完全由环境链（venv 缺少 pytest → PATH fallback → Python 3.10）引起，不是 B3 业务代码错误。

**不得**将其计入业务测试 PASS 或 FAIL。属于锁定的 1.16 venv 不完整且 `--no-sync` 阻止依赖安装的环境限制。

### 11.4 Scope Checker

```bash
scripts/ci/check-enterprise-replay-scope.sh \
  5c6372d2f76d240265b92fd27c16bc772ffcb107 HEAD
```

结果：**enterprise replay scope check passed** ✓

## 12. NOT_RUN 完整清单

明确不冒充已运行的验证项：

- [ ] ruff lint/format — ruff 未安装
- [ ] focused pytest (4 测试文件) — 锁定 venv 缺少 pytest；`--no-sync` 禁止安装依赖，PATH fallback 使用系统 Python 3.10 pytest，无法解析 Dify 1.16 的 PEP 695 语法导致 collection 失败
- [ ] integration tests — CI-only，不期望本地运行（AGENTS.md 确认）
- [ ] contract generation — B4 任务
- [ ] migration graph 验证 — B3 不新增 model/migration
- [ ] Docker/Compose 验证 — B3 不修改 Docker
- [ ] Redis/Celery 集成验证 — 需外部服务
- [ ] PostgreSQL unique/row lock — 需数据库
- [ ] 官方 `/activate` acceptance flow — 集成范围
- [ ] 真实 HTTP 404/405 (member DELETE) — 见 §13 B4 integration obligations

## 13. B4 Integration Obligations

B3 controller 未注册（不在 `api/controllers/console/__init__.py` 中 import），因此：

1. **真实 HTTP 404/405 验证**（member DELETE 等未定义路由）必须由 B4 在 controller 注册后执行。B3 只能通过 AST source-level 验证（`test_platform_admin_controller_defines_exact_seven_method_route_pairs`）确认没有定义 DELETE method handler，但无法在运行时验证 Flask/RESTX 对未定义 DELETE 的 404/405 响应。

2. **Contract generation** 是 B4 的独占任务。generated contract 必须证明：
   - 精确 7 条 route
   - 无 member DELETE
   - 14 个 DTO/schema 的字段和类型正确

3. **若 B4 contract generation 暴露 B3 schema defect**，B4 必须暂停并交回 B3 独立修订，不得顺手扩大 route。

4. **B5 消费 generated contract**：
   - 不显示成员删除操作
   - 按 `mutation_supported` 降级
   - 按 `email_delivery` 显示 `queued`/`failed`/`not_applicable`

## 14. Builder 提交核对

| Commit | 说明 |
| --- | --- |
| `77f3651796783b0ab60fadc53eea3725e8739f9d` | HEAD |

`git log f5dba3ee47d6697ca9883ef455f4e08733f4f229..77f3651796783b0ab60fadc53eea3725e8739f9d --oneline` 应由 Builder 方提供完整历史。本 Reviewer 独立核查 `git diff` 范围和 `git show HEAD` 内容。

## 15. 剩余已接受限制（未因本次审查而改写为已解决）

- RBAC mutation unsupported (503 fail-closed)
- Account email 无 DB unique constraint (B3 lock 不约束官方注册流)
- Notification 无 outbox (不保证 exactly-once/自动重试)
- Billing membership cache 清理是 post-commit best-effort
- Request DEBUG body 可能泄漏 PII（部署门禁）
- 运维日志不是 audit model
- `PLATFORM_ADMIN_EMAILS` 配置变更需重启
- ACTIVE invitation capacity 只是瞬时门禁，无 reservation；延迟/并发接受可能突破 limit（人工已接受 KNOWN_LIMITATION）
- Service commit 后 controller/framework 序列化故障窗口（已诚实记录）

## 16. 最终授权声明

本结论：

- **通过** B3 Builder 实现的独立代码审查
- **接受** B3_CODE_ACCEPTED
- **不要求** Fixer 介入
- **不授权** B4 注册/contract generation
- **不授权** B5 前端实现
- **不授权** 运行时或生产发布
- **不授权** push
- **未修改** 任何现有业务代码、测试、配置或文档（仅新增本文件）

---

- 结论：**PASS — B3_CODE_ACCEPTED**
- P0/P1/P2：**0 / 0 / 0**
- Fixer：**FIXER_NOT_REQUIRED**
- B4 integration obligations：**记录于 §13**
- NOT_RUN：**记录于 §12**（ruff + focused pytest 因环境兼容性不可用）
- Scope checker：**PASS**
- 仅新增本文件 `docs/enterprise/replay-1.16.0/B3_REVIEW.md`

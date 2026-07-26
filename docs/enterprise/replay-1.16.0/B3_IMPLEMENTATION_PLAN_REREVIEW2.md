# Dify Enterprise 1.16.0 Replay B3 Implementation Plan Final Re-review

## 0. 复审元数据

- 角色：独立 B3 Plan Final Rereviewer；非 Architect、Fixer 或 Builder
- 当前分支：`ctyun/replay-116-b3-plan-rereviewer2`
- 复审 HEAD：`0936825530385cca4f503536582be2cff973495a`
- 前置核验：分支、HEAD、工作区干净，三项全部通过
- 阅读范围：完整阅读 B3_IMPLEMENTATION_PLAN.md、B3_IMPLEMENTATION_PLAN_REVIEW.md、
  B3_IMPLEMENTATION_PLAN_REREVIEW.md、DESIGN_GATE.md、ARCHITECT_HANDOFF.md、
  PATCH_DECISION_MATRIX.md、VALIDATION_PLAN.md 共 7 份文档
- 官方源码基准：tag `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 验证方式：逐项对照官方 1.16 源码独立核验；未安装依赖，未运行 Docker、数据库、Redis、
  Weaviate、migration、contracts 或业务测试

## 1. 最终结论

**PASS**。

- **B3_READY_ACCEPTED**
- **BUILDER_GATE_RECOMMENDED**

B3 Implementation Plan 在本次独立复审中无阻断项。五份治理文档不存在当前口径冲突。Builder 可据此无歧义
实现。启动 Builder 仍需人工门禁决定。

P0/P1/P2 数量：**P0=0, P1=0, P2=0**。

## 2. 前置门禁核验

| 检查项 | 状态 |
| --- | --- |
| 分支 `ctyun/replay-116-b3-plan-rereviewer2` | PASS |
| HEAD `0936825530385cca4f503536582be2cff973495a` | PASS |
| 工作区干净 | PASS |

## 3. 第一次 Review 每项发现的关闭状态

| Review 项 | 状态 | 复核结论 |
| --- | --- | --- |
| P0-1 成员移除副作用不完整 | **CLOSED** | B3 整体延期并拒绝成员移除。官方源码证据：`TenantService.remove_member_from_tenant()`（`api/services/account_service.py:1739-1841`）含 App/Dataset maintainer 重分配、孤立 PENDING Account 删除、billing cache 清理、`sync_workspace_member_removal` 企业同步、RBAC binding cleanup，共 6 类副作用。B3 plan §2/§5.5 明确无 member DELETE、无 `remove_member` public API、无直接 join delete。未来恢复清单（§2）完整覆盖上述所有副作用及 owner/current/last workspace 保护。 |
| P1-1 ACTIVE 邀请偏离官方 | **CLOSED** | ACTIVE 未加入不建 join、不改 current，post-commit 生成 token/投递；join 由官方 `/activate` 接受时创建。官方源码证据：`invite_new_member()`（`account_service.py:2095`）条件 `not ta and (account.status == AccountStatus.PENDING or dify_config.RBAC_ENABLED)` 对 ACTIVE 非 RBAC 为 False，不创建 join。`/activate`（`activate.py:180-181`）在 `membership_id is None` 时创建 join。 |
| P1-2 billing email freeze | **CLOSED** | 仅对将创建的新 Account、仅 `BILLING_ENABLED=true` 调用；命中时事务回滚且整批无副作用。官方源码证据：`AccountService.create_account()`（`account_service.py:450-456`）在 `BILLING_ENABLED` 时调用 `BillingService.is_email_in_freeze(email)`；该方法（`billing_service.py:468-474`）fail-open（异常返回 False），B3 plan 保留该语义。 |
| P1-3 token 撤销 key 错配 | **CLOSED** | 明确调用 `revoke_token(None, None, token)`。官方源码证据：`generate_invite_token`（`account_service.py:2148`）写 key `member_invite:token:{token}`（`_get_invitation_token_key` 返回 `f"member_invite:token:{token}"`，line 1927）。`revoke_token`（line 2157-2163）：传 workspace_id 和 email 则删 `member_invite_token:{workspace_id}, {email_hash}:{token}`（不同格式），不传则删 `member_invite:token:{token}`（正确）。 |
| P1-4 RBAC read role 误导 | **CLOSED** | RBAC read 返回 `role=None`、`role_source="rbac_unavailable"`、`mutation_supported=false`；invite/role 503 先于任何 DB/Redis/token/task。不调用外部 RBAC。 |
| P1-5 workspace member limit 双算 | **CLOSED** | enterprise 与 billing 分支各用单一来源，不再同时使用 DB count + feature payload size 做双重拒绝。官方源码证据：`_check_member_invite_limits()`（`members.py:190-210`）enterprise 只用 `workspace_members.is_available`，billing 只用 `members.limit` + DB count。B3 plan §6.4 与官方一致。 |
| P2-1 Redis 锁 blocking_timeout | **CLOSED** | 显式指定 `LOCK_TTL_SECONDS=60`、`LOCK_BLOCKING_TIMEOUT_SECONDS=5`（plan §5.3）。 |
| P2-2 session.begin() 前 autobegin | **CLOSED** | begin 前无 DB query，所有 query/flush 在 begin 内（plan §5.2/§5.4）。 |
| P2-3 current tenant 隐含依赖 | **CLOSED** | status 去除不必要依赖；管理 route 先稳定返回 `current_tenant_required`（plan §4.3）。 |
| P2-4 token 不返回的邮件依赖 | **CLOSED** | 邮件是接受链接唯一通道，delivery 语义明确（plan §3.1/§6.7）。 |
| P2-5 LoginConfig 放置 | **CLOSED** | 在允许范围内的 pragmatic 选择，唯一配置，不新增第二个同义配置（plan §4.1）。 |
| HD-1 RBAC mutation 策略 | **CLOSED** | RBAC 开启时 invite/role 503 fail-closed，已落实（plan §6.8）。 |
| HD-2 ACTIVE 邀请语义 | **CLOSED** | 使用官方邀请—接受流程，已落实（plan §5.4/§6.3）。 |

## 4. 第一次 Rereview 每项发现的关闭状态

| Rereview 项 | 状态 | 复核结论 |
| --- | --- | --- |
| P1-RR-1 requires_setup 契约缺失 | **CLOSED** | Plan §5.4 step 11 明确要求四种发 token 状态均显式传 `requires_setup` 值；§6.3 邀请状态矩阵逐项列出显式值。官方源码证据：`generate_invite_token` 默认 `requires_setup=False`（`account_service.py:2137`）；`invite_new_member` 对新 Account 和 PENDING 置 `requires_setup=True`（lines 2085, 2093）；`/activate` 仅在 `requires_setup` 为 True 时收集 setup fields 并激活 Account（`activate.py:168-189`）。 |
| P1-RR-2 ACTIVE 容量最终一致性描述错误 | **CLOSED** | Plan §6.4/§11.2 已改正：invitation-time capacity check 只是瞬时门禁，不是 reservation；官方 `/activate` 不复查 workspace capacity（源码证据：`activate.py:145-191` 无 `_check_member_invite_limits`、`workspace_members.is_available` 或 billing member-limit 调用）；B3 Redis 锁不覆盖接受路径；延迟/并发接受可能突破 workspace member limit。明确记录为 `KNOWN_LIMITATION`，不得声称最终一致性。 |
| P2-RR-1 capacity 官方 guard 不完整 | **CLOSED** | Plan §6.4 已补齐：`required_memberships <= 0` 跳过全部检查；enterprise 分支 seat 仅在 `new_account_count > 0` 时调用；billing 分支要求 `features.billing.enabled is True`；`members.limit=0` 表示 unlimited；等于 limit 时不拒绝。与官方 `_check_member_invite_limits`（`members.py:190-210`）完全对齐。 |
| P2-RR-2 上游治理文档陈旧措辞 | **CLOSED** | 已通过治理同步修复（plan §1.1 P2-RR-2 标记 `FIXED_BY_GOVERNANCE_SYNC`），五份文档当前口径一致（见 §9）。 |

## 5. 7-Route 范围核验

B3 v1 精确 7 条 route（plan §3.2），逐项对照五份治理文档：

| Route | B3 Plan | Design Gate | Handoff | Decision Matrix | Validation Plan |
| --- | --- | --- | --- | --- | --- |
| GET `/account/platform-admin-status` | ✓ | ✓ | ✓ | ✓ | ✓ |
| GET `/platform-admin/workspaces` | ✓ | ✓ | ✓ | ✓ | ✓ |
| GET `/platform-admin/workspaces/<id>` | ✓ | ✓ | ✓ | ✓ | ✓ |
| PATCH `/platform-admin/workspaces/<id>` | ✓ | ✓ | ✓ | ✓ | ✓ |
| GET `/platform-admin/workspaces/<id>/members` | ✓ | ✓ | ✓ | ✓ | ✓ |
| POST `/platform-admin/workspaces/<id>/members/invitations` | ✓ | ✓ | ✓ | ✓ | ✓ |
| PATCH `/platform-admin/workspaces/<id>/members/<id>/role` | ✓ | ✓ | ✓ | ✓ | ✓ |

**负向核验**：所有五份文档均不包含 member DELETE、workspace create/delete/archive、owner mutation、
password reset 或 break-glass route。

PATCH_DECISION_MATRIX.md:50 明确标注"旧候选曾提供 8 组 endpoint 与 service 测试；这是'旧实现证据'，
不代表当前 7-route 契约"，消除了历史引用歧义。

**结论：7-route 范围在所有治理文档中精确一致，无歧义。**

## 6. requires_setup 状态矩阵核验

逐项对照官方源码 `invite_new_member()`（`account_service.py:2046-2133`）、
`generate_invite_token()`（`account_service.py:2135-2149`）和 `/activate`（`activate.py:127-193`）：

| B3 场景 | B3 plan §6.3 规定 | 官方对应逻辑 | 一致性 |
| --- | --- | --- | --- |
| 新建 PENDING Account | `requires_setup=True`，创建 Account + `current=True` join | `invite_new_member` line 2085: `requires_setup = True` | ✓ |
| 既有 PENDING 未加入 | `requires_setup=True`，创建 `current=False` join | `invite_new_member` line 2093: `requires_setup = account.status == AccountStatus.PENDING` → True | ✓ |
| 既有 PENDING 已加入 | `requires_setup=True`，不重复 join，不修改 current，resend | 同上，`requires_setup = True` | ✓ |
| ACTIVE 未加入 | `requires_setup=False`，不创建 join，不修改 current | `invite_new_member` line 2070 初始 `requires_setup = False`，line 2093 条件 `account.status == AccountStatus.PENDING` → False | ✓ |
| ACTIVE 已加入 | 不生成 token，`already_member` | 官方抛 `AccountAlreadyInTenantError` | ✓ |

`generate_invite_token` 默认值 `requires_setup=False`（`account_service.py:2137`）。`/activate` 仅在
`requires_setup=True` 时收集 setup fields 并联机 PENDING → ACTIVE（`activate.py:168-189`），
`requires_setup` 为 None 时回退 `account.status == AccountStatus.PENDING`（line 169-170）。

B3 plan §5.4 step 11 要求 Builder **显式传递** `requires_setup`，不得依赖默认值。§6.3
矩阵表第五列表格列出每个分支的显式值。§10 测试矩阵要求逐类断言生成参数和 Redis payload。

**结论：requires_setup 矩阵与官方源码完全对齐，Builder 无歧义。**

## 7. Capacity Guard 核验

逐项对照官方 `_check_member_invite_limits()`（`members.py:190-210`）和 `_count_new_member_invites()`
（`members.py:163-181`）：

| Guard 条件 | B3 plan §6.4 | 官方源码 | 一致性 |
| --- | --- | --- | --- |
| `required_memberships <= 0` 跳过全部 | ✓ | `new_member_count <= 0: return` (line 191-192) | ✓ |
| Enterprise workspace check 仅在 `required_memberships > 0` | ✓ | 同上，`<= 0` 时 return 不进入分支 | ✓ |
| Enterprise seat 仅在 `new_account_count > 0` | ✓ | `if new_account_count > 0:` (line 200) | ✓ |
| Billing 仅 `features.billing.enabled is True` | ✓ | `features.billing.enabled is True` (line 206) | ✓ |
| `members.limit=0` 表示 unlimited | ✓ | `0 < members.limit < ...` (line 209)，limit=0 不满足 `0 < 0`，不拒绝 | ✓ |
| 等于 limit 时不拒绝 | ✓ | `members.limit < current + new`，等于不触发 | ✓ |
| Enterprise 与 billing 互斥 | ✓ | `if ENTERPRISE: ... return` → `if BILLING:` 不会同时执行 | ✓ |
| 不混用 feature capacity + DB count 双重拒绝 | ✓ | 各自只用单一来源 | ✓ |

**结论：capacity guard 与官方源码完全对齐，Builder 无歧义。**

## 8. KNOWN_LIMITATION 核验

| 声明 | B3 Plan | Design Gate | Handoff | Decision Matrix | Validation Plan | 官方源码证据 |
| --- | --- | --- | --- | --- | --- | --- |
| Invitation-time check 只是瞬时门禁，不是 reservation | §6.4/§11.2 | 2026-07-26 §5 | B3 节 | E03 §ACTIVE 限制 | §G 平台管理员 | — |
| 官方 `/activate` 不复查 workspace capacity | §6.4 | 2026-07-26 §5 | B3 节 | E03 §ACTIVE 限制 | §G | `activate.py:145-191` 无 capacity 调用 |
| B3 Redis 锁不覆盖接受路径 | §6.4 | 2026-07-26 §5 | B3 节 | E03 §ACTIVE 限制 | §G | B3 锁只在 invite service 内，`/activate` 独立 |
| 延迟/并发接受可能突破 limit | §6.4/§11.2 | 2026-07-26 §5 | B3 节 | E03 §ACTIVE 限制 | §G | 无跨流程 reservation |
| 不声称最终一致性 | §6.4/§11.2 | 2026-07-26 §5 | B3 节 | E03 | §G | — |
| 不直接创建 ACTIVE join 或暗改 `/activate` | §6.4 | 2026-07-26 §5 | B3 节 | E03 | — | — |
| 人工已接受（2026-07-26） | §1.1/§6.4 | 2026-07-26 §5 | B3 节 | E03 | — | — |

**结论：KNOWN_LIMITATION 在所有文档中表述一致，如实描述了官方既有限制，不声称超过现实的能力。**

## 9. Member Removal 延期与治理文档一致性核验

| 声明 | B3 Plan | Design Gate | Handoff | Decision Matrix | Validation Plan |
| --- | --- | --- | --- | --- | --- |
| B3 不提供 member removal | §2, §5.5 | 2026-07-26 §1 | B3 节 | E03 延期范围 | §G |
| 无 member DELETE route | §2, §3.2 | 2026-07-26 §2 | B3 节 | E03 单元测试 | §G 负向验证 |
| current/last workspace guard 不属于 B3 验收 | §2, §3.3 | 2026-07-26 §3 | B3 节 | E03 延期范围 | §G |
| 完整删除能力另立任务 | §2 | 2026-07-26 §3 | B3 节 | E03 延期范围 | — |
| 未来任务覆盖 maintainer/孤立 PENDING/billing/enterprise/RBAC/通知/审计 | §2 | 2026-07-26 §3 | B3 节 | E03 延期范围 | — |

**结论：五份治理文档对 member removal 延期的表述完全一致，无歧义。**

## 10. 其他既有 P0/P1 核验

| 检查项 | B3 Plan 位置 | 官方源码证据 | 状态 |
| --- | --- | --- | --- |
| RBAC_ENABLED=true 时 invite/role 503 fail-closed | §6.8 | 503 在任何 Redis/DB/token/task 前 | PASS |
| ACTIVE 邀请遵循官方流程 | §5.4 | `invite_new_member` 对 ACTIVE 不建 join | PASS |
| billing email freeze 检查存在 | §5.4 step 7 | `account_service.py:450-456` | PASS |
| token revoke 正确 key | §5.4 step 12 | `_get_invitation_token_key` = `member_invite:token:{token}` | PASS |
| RBAC read role 不冒充权威 | §3.1, §6.8 | `role=None`, `role_source="rbac_unavailable"` | PASS |
| billing cache best-effort 清理 | §5.4 step 10, §6.5.1 | `clean_billing_info_cache` deletes `tenant:{id}:billing_info` | PASS |
| 单一显式 Session，一个有效业务事务 | §5.2 | `with self._session.begin()` 含所有 DB 操作 | PASS |
| token/邮件仅在 DB commit 成功后 | §5.4 step 11-12 | post-commit 在 begin 成功退出后 | PASS |

## 11. 官方源码证据索引

| 证据 | 文件 | 行号 | 证明内容 |
| --- | --- | --- | --- |
| `generate_invite_token` 默认 `requires_setup=False` | `api/services/account_service.py` | 2137 | 必须显式传值，不可依赖默认 |
| `invite_new_member` 对新 Account 设 `requires_setup=True` | `api/services/account_service.py` | 2085 | 新建 PENDING 必须 True |
| `invite_new_member` 对 PENDING 设 `requires_setup=True` | `api/services/account_service.py` | 2093 | 所有 PENDING 分支 True |
| `invite_new_member` 对 ACTIVE 不建 join | `api/services/account_service.py` | 2095 | 条件 `PENDING or RBAC`，排除 ACTIVE |
| `/activate` 无 capacity 检查 | `api/controllers/console/auth/activate.py` | 145-191 | KNOWN_LIMITATION 成立 |
| `/activate` 仅 `requires_setup=True` 时激活 Account | `api/controllers/console/auth/activate.py` | 168-189 | requires_setup 是 PENDING→ACTIVE 的关键 |
| `_check_member_invite_limits` 零增量 skip | `api/controllers/console/workspace/members.py` | 191-192 | capacity guard 正确 |
| `_check_member_invite_limits` enterprise 分支 | `api/controllers/console/workspace/members.py` | 196-204 | enterprise 只用 workspace + seat |
| `_check_member_invite_limits` billing 分支 | `api/controllers/console/workspace/members.py` | 206-210 | billing enabled + limit > 0 |
| `revoke_token` 双路径 key 格式 | `api/services/account_service.py` | 2157-2163 | 传 workpace_id/email 删错误 key |
| `remove_member_from_tenant` 完整副作用 | `api/services/account_service.py` | 1739-1841 | B3 延期正确原因 |
| `is_email_in_freeze` fail-open 语义 | `api/services/billing_service.py` | 468-474 | B3 保留该语义 |
| `_get_invitation_token_key` 格式 | `api/services/account_service.py` | 1927 | `member_invite:token:{token}` |

## 12. 实际执行的验证与 NOT_RUN 项

### 已执行验证

- [x] git 分支/HEAD/工作区核验
- [x] 官方 `invite_new_member()` 完整读取（`account_service.py:2046-2133`）
- [x] 官方 `generate_invite_token()` 完整读取（`account_service.py:2135-2149`）
- [x] 官方 `revoke_token()` 完整读取（`account_service.py:2157-2163`）
- [x] 官方 `_get_invitation_token_key()` 读取（`account_service.py:1927`）
- [x] 官方 `/activate` endpoint 完整读取（`activate.py:1-193`）
- [x] 官方 `_check_member_invite_limits()` 完整读取（`members.py:190-210`）
- [x] 官方 `_count_new_member_invites()` 完整读取（`members.py:163-181`）
- [x] 官方 `_count_current_members()` 完整读取（`members.py:184-187`）
- [x] 官方 `remove_member_from_tenant()` 完整读取（`account_service.py:1739-1841`）
- [x] 官方 `AccountService.create_account()` 完整读取（`account_service.py:425-490`）
- [x] 官方 `BillingService.is_email_in_freeze()` 完整读取（`billing_service.py:468-474`）
- [x] 官方 `clean_billing_info_cache()` 读取（`billing_service.py:551-552`）
- [x] 七份文档交叉核验
- [x] requires_setup 矩阵逐项核验
- [x] capacity guard 逐条件核验
- [x] KNOWN_LIMITATION 五文档一致性核验
- [x] member removal 延期五文档一致性核验
- [x] 7-route 范围五文档一致性核验

### NOT_RUN（明确不冒充已运行）

以下项属于 Builder 阶段或集成环境的验证，本复审明确不运行：

- [ ] pytest focused test suite（需安装依赖和数据库）
- [ ] Redis/Celery 集成验证
- [ ] 官方 `/activate` 接受流程集成验证
- [ ] PostgreSQL unique constraint / row lock 验证
- [ ] contract generation（B4 任务）
- [ ] migration graph 验证
- [ ] Docker/Compose 验证
- [ ] volume 升级验证
- [ ] B0 scope checker

## 13. 最终授权声明

本结论：

- **通过** B3 Implementation Plan 的独立复审
- **推荐** 打开 Builder 人工门禁
- **不授权** 自动启动 Builder（需独立 Builder 授权流程）
- **不授权** B4 注册/contract generation
- **不授权** B5 前端实现
- **不授权** 运行时或生产发布
- **不授权** Docker、数据库、Redis 或 volume 操作
- **不授权** push
- **未修改** 任何现有计划、治理文档、代码、测试、配置或 migration

## 14. 交付总结

- 结论：**PASS** — B3_READY_ACCEPTED
- P0/P1/P2：0 / 0 / 0
- Builder Gate：**BUILDER_GATE_RECOMMENDED**
- 五份治理文档当前口径一致
- 7-route 范围、requires_setup 矩阵、capacity guard、KNOWN_LIMITATION、member removal 延期
  均在本次复审中独立获得官方源码证据支持
- 仅新增本文件 `B3_IMPLEMENTATION_PLAN_REREVIEW2.md`
- 未修改现有文件
- 工作区干净
- 未 push

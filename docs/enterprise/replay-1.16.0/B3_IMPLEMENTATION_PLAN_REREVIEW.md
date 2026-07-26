# Dify Enterprise 1.16.0 Replay B3 Implementation Plan Re-review

## 0. 复审元数据

- 角色：独立 B3 Plan Re-reviewer；非 Architect、Fixer 或 Builder
- 当前分支：`ctyun/replay-116-b3-plan-rereviewer`
- 复审 HEAD：`15b0063d90f355429dff2d6af7f766ef4a3b7b54`
- 原计划：`62ce6f0bf253c39641e97fb477fcdb5769012906`
- 原 Review：`e6e8f638bb4e82c10b310600fd105db21038f5e8`
- 修订提交：`15b0063d90f355429dff2d6af7f766ef4a3b7b54`
- 官方源码基准：tag `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 前置核验：分支、HEAD 均匹配，复审开始时工作区干净
- 阅读范围：完整阅读 `DESIGN_GATE.md`、`ARCHITECT_HANDOFF.md`、
  `PATCH_DECISION_MATRIX.md`、`VALIDATION_PLAN.md`、修订后的
  `B3_IMPLEMENTATION_PLAN.md` 与原 `B3_IMPLEMENTATION_PLAN_REVIEW.md`
- 验证方式：只读检查文档、指定提交差异及官方 1.16 源码；未安装依赖，未运行 Docker、数据库、
  Redis、Weaviate、migration、contracts 或业务测试

## 1. 结论

**CHANGES_REQUIRED**。

- **不接受**技术建议 `B3_READY`。
- **不允许**进入人工 Builder 启动门禁。
- B3 Builder、B4 注册/contract generation、B5、运行时和生产发布均继续保持未授权。

修订已经关闭成员移除 P0，并正确修复 ACTIVE 邀请、billing freeze、token 撤销和 RBAC read/mutation
等原 P1 的主体问题；但独立源码核对发现两个新的 P1：

1. PENDING invitation token 未规定 `requires_setup=True`，Builder 按当前契约可生成不能完成账号激活的
   token。
2. ACTIVE 延迟接受的容量语义描述不实；官方 `/activate` 不复查 workspace capacity，不能声称它维护
   该限制的最终一致性。

此外，capacity 分支的官方零增量和 billing enabled/unlimited 条件没有完整固化，原 P1-5 因此只能判定为
主体修复但尚未完整关闭。

## 2. 原 P0/P1 关闭状态

| 原 Review 项 | 状态 | 复核结论 |
| --- | --- | --- |
| P0-1 成员移除副作用不完整 | **CLOSED** | B3 整体延期并拒绝成员移除；最终 7 条 route 无 member DELETE；无 `remove_member` public API、直接 join delete、`member_removed` 或成功删除测试。未来恢复清单覆盖 maintainer、孤立 PENDING Account、billing cache、enterprise sync、RBAC、owner/current/last-workspace、事务补偿、通知和审计。 |
| P1-1 ACTIVE 邀请偏离官方 | **CLOSED** | ACTIVE 未加入不建 join、不改 current，post-commit 生成 token/投递；join 由官方 `/activate` 接受时创建。ACTIVE 已加入返回 `already_member`，无 token/task。 |
| P1-2 billing email freeze | **CLOSED** | 仅对将创建的新 Account、仅 `BILLING_ENABLED=true` 调用；命中时事务回滚且整批无 DB/token/task 副作用；保留官方异常 fail-open 语义并列有测试。 |
| P1-3 token 撤销 key 错配 | **CLOSED** | 已明确 `generate_invite_token` 写 `member_invite:token:{token}`，dispatch 失败只调用 `revoke_token(None, None, token)`，并要求验证正确 key 与 token 脱敏。 |
| P1-4 RBAC read role 误导 | **CLOSED** | RBAC read 返回 `role=None`、`role_source=rbac_unavailable`、`mutation_supported=false`；invite/role 在锁、DB、token/task 前 503；不调用外部 RBAC read/write。legacy 来源与当前默认 `False` 的非永久性均有准确说明。 |
| P1-5 workspace member limit 双算 | **PARTIALLY_CLOSED** | enterprise 与 billing 分支已改为单一来源，seat 只使用 `new_account_count`，原“双重拒绝”已消除；但零增量、billing enabled/unlimited guard 及 ACTIVE 延迟接受的最终限制语义未完整、准确固化，见 P1-RR-2 与 P2-RR-1。 |

## 3. 新发现

### P0

无新增 P0。

### P1-RR-1：PENDING invitation token 缺少 `requires_setup=True` 契约

修订计划在 `B3_IMPLEMENTATION_PLAN.md:345-346` 只要求调用
`RegisterService.generate_invite_token(...)`，没有规定参数矩阵，也没有测试 token payload 的
`requires_setup`。

官方 1.16 的事实：

- `api/services/account_service.py:2070-2093` 对新 Account 和既有 PENDING Account 设置
  `requires_setup=True`；
- `api/services/account_service.py:2121` 将该值显式传给 `generate_invite_token`；
- `api/services/account_service.py:2136-2145` 的默认值是 `False`，且该布尔值总会写入 token payload；
- `api/controllers/console/auth/activate.py:168-189` 只有 `requires_setup=True` 才收集 setup fields 并把
  PENDING Account 更新为 ACTIVE。

因此 Builder 若使用默认值，官方 `/activate` 不会走 PENDING setup/激活分支。计划必须明确：

- 新 Account、既有 PENDING 未加入、既有 PENDING 已加入 resend：`requires_setup=True`；
- ACTIVE 未加入：`requires_setup=False`；
- ACTIVE 已加入：不生成 token；
- unit tests 必须断言参数和 Redis payload，integration 计划必须断言 PENDING 接受后成为 ACTIVE。

### P1-RR-2：ACTIVE 延迟接受的 workspace capacity 最终一致性描述错误

修订计划 `B3_IMPLEMENTATION_PLAN.md:404-406` 声称邀请时检查不构成永久 reservation，但“接受时仍由官方
`/activate` 流程维护最终一致性”。

官方 `api/controllers/console/auth/activate.py:145-191` 只做 token/account、billing freeze、role、
membership existence、setup、join 创建和 tenant switch；没有调用
`_check_member_invite_limits`、`workspace_members.is_available` 或 billing member-limit 检查。

ACTIVE 未加入时 B3 又不创建 join，所以邀请期间没有持久 reservation。多个 ACTIVE invitation 可以先后
通过同一时点的 capacity 检查，之后接受并超过 workspace member limit。该风险不能通过 B3 Redis 锁消除，
因为锁不覆盖官方 `/activate`。

计划必须如实写明：

- invitation-time capacity check 只是瞬时门禁，不是 reservation；
- 官方 `/activate` 不复查 workspace capacity；
- 最终 workspace member limit 可能因延迟/并发接受被突破；
- 这是采用人工决定 HD-2 后保留的限制，不能描述为已经维护最终一致性；
- 增加可执行测试证明邀请时检查，以及接受路径不受 B3 锁约束；若产品不能接受该限制，必须另立跨流程设计，
  不得在 B3 中偷偷改为直接建 join。

### P2-RR-1：capacity 官方分支条件没有完整固化

官方 `api/controllers/console/workspace/members.py:190-210`：

- `new_member_count <= 0` 立即返回；
- enterprise 分支只使用 `workspace_members.is_available(new_member_count)`，seat 仅在
  `new_account_count > 0` 时检查；
- billing 分支还要求 `features.billing.enabled is True`，并仅在
  `0 < members.limit < current_count + new_member_count` 时拒绝。

修订计划 `B3_IMPLEMENTATION_PLAN.md:397-402` 只写“比较 count 与 billing limit”，测试矩阵也未覆盖
零增量、billing disabled payload 和 `limit=0` unlimited。应补齐这些条件，避免 `already_member`/纯 resend
批次或 unlimited tenant 被错误拒绝。

### P2-RR-2：上游 handoff/validation 仍有删除路径陈旧措辞

当前 B3 计划通过明确优先级和负向约束阻止隐藏删除路径，故不升级为 P0；但完整文档链仍有容易误导后续
执行者的陈旧文字：

- `PATCH_DECISION_MATRIX.md:268` 仍要求 invite/role/**remove** integration；
- `PATCH_DECISION_MATRIX.md:55` 仍写“当前 workspace 防删除”；
- `VALIDATION_PLAN.md:183-184` 仍把 current/last-workspace guard 放在首版平台成员操作验收中。

`PATCH_DECISION_MATRIX.md:49` 的“旧候选提供 8 组 endpoint”是历史证据，不是现行 route 契约；
原 Review 中的 8-route/remove 内容也是被复审的历史对象。现行 B3/B4/B5 handoff 只能以修订计划的 7-route
负向契约为准。后续允许修订文档时应清理上述执行性措辞，避免重新引入删除测试。

## 4. 已批准人工决定落实情况

| 人工决定 | 状态 | 复核 |
| --- | --- | --- |
| RBAC 开启时 B3 首版 invite/role mutation 503 fail-closed | **落实** | 503 位于任何 Redis、DB、token/task 之前；read 明确降级；不调用外部 RBAC。 |
| ACTIVE 账号遵循官方邀请—接受流程 | **落实** | 未加入不建 join，已加入 `already_member`；但容量最终一致性限制描述需按 P1-RR-2 修正。 |
| B3 首版整体延期成员移除 | **落实** | route、DTO、service、日志、测试和 B4/B5 handoff 均没有可执行删除能力。 |

本复审不推翻上述人工决定。

## 5. 14 项专项核对

| 项目 | 结果 |
| --- | --- |
| 1. P0-1 成员移除 | **PASS**；无隐藏删除路径，未来恢复覆盖项完整。 |
| 2. P1-1 ACTIVE 邀请 | **PASS with limitation correction required**；官方状态流正确，容量最终一致性描述错误。 |
| 3. P1-2 billing freeze | **PASS**。 |
| 4. P1-3 token 撤销 | **PASS**。 |
| 5. P1-4 RBAC read/mutation | **PASS**。 |
| 6. P1-5 容量 | **CHANGES_REQUIRED**；单一来源已修，官方精确 guard 与延迟接受限制未闭环。 |
| 7. Redis 锁 | **PASS**；TTL/等待、顺序、hash、异常释放、fail-closed 和作用域限制均明确。 |
| 8. 事务模型 | **PASS**；begin 前无注入 Session 查询，一个有效业务事务/提交，wrapper 后续 no-op，post-commit 边界和序列化窗口均诚实记录；无需修改 `with_session`。 |
| 9. join.current | **PASS**；新 PENDING 为 true、既有 PENDING 未加入为 false、已加入保持、ACTIVE 邀请不改 join/current，矩阵/时序/测试一致。 |
| 10. billing cache | **PASS**；immediate join + billing 后提交清理一次，无 join 变化不清，失败不阻断 dispatch 且日志脱敏。 |
| 11. status/current tenant | **PASS**；status 不依赖 current tenant，管理 route 先稳定返回 `current_tenant_required`，非管理员实际 `/platform-admin/**` 403。 |
| 12. 配置与测试范围 | **PASS**；唯一 LoginConfig 配置、默认空/fail-closed/重启语义、config test allowlist/focused command 和 helper test 归属均明确。 |
| 13. route/DTO/handoff | **PASS**；现行契约精确 7/14/6，无 remove DTO/error/success test，B4 只注册/生成 7 条，B5 不显示删除并消费 mutation/delivery 字段；contract defect 交回 B3。 |
| 14. 文档质量 | **CHANGES_REQUIRED**；测试均未冒充已运行，授权边界准确，但 P1-RR-1/P1-RR-2 及陈旧 cross-doc 措辞尚未消除。 |

## 6. 7 条 route / 14 DTO / 6 service public methods

核对结果：**7 / 14 / 6，数量与名称一致**。

- 7 routes：status；workspace list/detail/rename；member list/invite/role update。无 member DELETE。
- 14 DTO：1 status、4 workspace list/view、1 rename、2 member read、3 invite、2 role update、1 error。
- 6 public methods：`list_workspaces`、`get_workspace`、`list_members`、`rename_workspace`、
  `invite_members`、`update_member_role`。无 `remove_member` 或通用 delete/mutation method。

B4 handoff 明确只注册并生成 7 条；B5 不显示删除操作，并以 `mutation_supported` 和
`email_delivery` 驱动降级 UI。

## 7. 剩余已接受限制

以下限制继续保留，不因本次复审而被误写为已解决：

- RBAC mutation unsupported；
- email 无 DB unique；
- notification 无 outbox；
- request DEBUG PII；
- 日志非 audit；
- 配置需重启。

另外，billing cache best-effort、response 序列化窗口和 B3 锁不约束官方注册流均已在计划中诚实记录。
ACTIVE 延迟接受的 capacity 非 reservation 风险必须按 P1-RR-2 纠正后，才能判断其是否作为已接受限制进入
最终契约。

## 8. 授权与后续条件

本结论只要求 Architect/Fixer 修订计划；Reviewer 不修改计划、Review 或业务代码。

再次复审前至少必须：

1. 固化 `requires_setup` 状态矩阵及 unit/integration assertions；
2. 删除官方 `/activate` 会维护 capacity 最终一致性的错误声称，准确记录无复查/无 reservation 风险；
3. 固化 capacity 的零增量、billing enabled、unlimited 和 seat-zero guard 测试；
4. 保持成员移除整体延期，不得以修复上述问题为由恢复第 8 条 route。

即使后续复审得到 **PASS**，也只表示技术上可提交人工 Builder 启动门禁判断；**PASS 不等于自动启动
Builder，不授权 B4、运行时、Docker/数据库操作或生产发布**。

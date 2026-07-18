# Dify Enterprise 1.16.0 Architect Handoff

## 1. 工作树与提交身份

- 当前工作树分支：`ctyun/replay-116-architect`
- 用户指定候选来源：`codex/enterprise-candidate-1.16.0-20260718`
- 官方基线标签：`1.16.0`
- 基线提交：`5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 架构工作开始时 HEAD：`5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 本次提交：提交主题 `docs: plan enterprise replay for 1.16.0`；最终 hash 由包含本文件的 Git 提交确定，并在交付报告中给出（Git 对象不能在自身内容中稳定自引用其最终 hash）。

本地仓库未提供 `origin/codex/enterprise-candidate-1.16.0-20260718` 跟踪引用，因此只能证明当前 HEAD 与用户指定提交及官方标签完全一致，不能用远端引用名再次证明候选分支来源。Builder 开始前由维护者确认/创建目标候选分支，不要改变基线。

## 2. 本次交付范围

本提交只应包含：

1. `ENTERPRISE_REPLAY_PLAN.md`
2. `docs/enterprise/replay-1.16.0/OFFICIAL_RELEASE_ANALYSIS.md`
3. `docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md`
4. `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md`
5. `docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md`

未修改业务代码、Docker 配置、migration、版本号或运行数据；未启动 Docker；未访问、复制或修改 `docker/volumes`。

## 3. 主要结论

1. 官方 1.16 是不可妥协的实现真相。`1.15.0..1.16.0` 变更达 8,708 文件，Agent、契约、session、状态与工具链都已换代，旧候选不能 cherry-pick。
2. 官方已经实现企业默认 workspace 自动加入和注册/workspace 创建开关，删除平行实现，只保留配置与验证。
3. 平台管理员、智慧广场、企业 overlay/镜像、离线包、vector 升级检查和旧企业 migration 兼容仍需企业交付。
4. 平台管理员/智慧广场必须使用 1.16 的 Pydantic Console contracts、生成 routes/types、`consoleQuery`、显式 SQLAlchemy `Session`、tenant/owner scope 和 Jotai/bootstrap；旧 controller/service/Web hooks 全部只作需求证据。
5. 旧 OAuth 专用加密器与官方实现密文兼容且行为重复，`DROP_UPSTREAMED`。生成器 model mode 归一化仍未上游覆盖，`KEEP_MINIMAL_PATCH`。
6. Workflow、HITL、Plugin、Dataset、install/sign-in/public routes 和旧 session bug 大多 `VERIFY_ONLY`；只有失败测试先证明 1.16 差距后才能新增补丁。
7. 1.16 新增 `agent_backend` 和 `local_sandbox`。overlay 不得覆盖其安全边界；离线包必须包含两镜像，生产必须替换 Agent server secret，Landlock 默认开启。
8. migration 文案不一致已按代码澄清：Release 标题说 9、实际列 8、升级说明说 8；从官方 1.15 到 1.16 实际新增 5 个 revision。官方 1.16 静态 head 是 `7a1c2d9e4b60`。
9. 旧企业库可能记录 `e2f0a9b7c6d5`。必须保留旧 revision 可解析并新增 1.16 merge；直接删除旧 migration 或 stamp 都会破坏升级可审计性。
10. “企业会话管理”范围不明，当前 `DEFER`。不得擅自把 account sessions、conversation 或 Agent shell session 中任一种当成完整需求。

## 4. Builder 任务拆分

### B0：基线、生成链和安全护栏

- 交付：基线/diff allowlist、OpenAPI generation 命令、官方安全回归集合、Compose 静态断言。
- 允许文件：测试/CI/开发脚本的最小范围，需 Reviewer 预先确认。
- 完成标准：能阻止旧 contract、controller SQLAlchemy、旧镜像/volume 文件进入 diff。

### B1：生成器 mode 归一化

- 交付：纯函数、automatic/code generator 接入和聚焦测试。
- 旧证据：`normalize-generator-model.ts` 及两个旧 spec。
- 1.16 边界：使用当前 TypeScript/Vite+/i18n/test mocks，不复制旧格式。
- 完成标准：`chat`、`completion`、`agent-chat`、stale localStorage 的 API payload 合法。

### B2：migration 图和智慧广场 schema

- 交付：历史 revision 可解析、最终 schema、新 1.16 merge、四起点 upgrade tests。
- 关键 head：旧企业 `e2f0a9b7c6d5`；官方 `7a1c2d9e4b60`。
- 完成标准：单 head，空库/官方 1.15/企业 1.15/官方 1.16 都可升级且数据不丢。

### B3：平台管理员后端

- 交付：授权/审计设计、session-injected service、DTO/controller、生成 contract、后端测试。
- 先决决策：密码重置、workspace 归档是否首版交付；无审计则延后高风险操作。
- 完成标准：admin/non-admin、跨 tenant scope、owner/last workspace/seat limit、rollback 全覆盖。

### B4：智慧广场后端

- 交付：提交/审核/发布/下架/复制状态机、生成 contract、无 secret DSL copy。
- 先决决策：发布时生成不可变快照，或持续引用 source app；必须二选一并形成数据保留规则。
- 完成标准：A 提交→admin 审核→B 复制的完整后端流程，非法状态/越权/并发有测试。

### B5：平台管理员和智慧广场前端

- 交付：基于生成 contract 的 queries/mutations、feature state/Jotai、权限导航、i18n 和行为测试。
- 禁止：手写 Console response types、旧 app context、legacy contract loader、硬编码用户文案。
- 完成标准：权限入口、深链、提交/审核/复制、错误/空状态和重复点击均验证。

### B6：1.16 enterprise overlay 与企业镜像

- 交付：最小 Compose overlay、API/Web image/build metadata、WebSocket image 覆盖。
- 禁止：修改官方 Compose；恢复 1.15 Dockerfile；覆盖 Agent depends_on/healthcheck/Landlock/key 关系。
- 完成标准：Compose config 中五个 runtime identity 正确，Agent 新服务完整。

### B7：离线 plugin、镜像包与配置包

- 交付：官方 mirror/signature knob 透传、`Mode=reuse`、完整镜像断言、manifest 和最小配置包。
- 完成标准：包含 Agent backend/local sandbox；绑定验证 image IDs/commit；包内容无 `.env`/secret/volume/cache。

### B8：Dataset/vector/volume 升级与发布验证

- 交付：默认只读的 vector consistency checker、完整 validation evidence、无外网离线 smoke。
- repair：独立任务，需显式批准；不得与只读检查一起默认执行。
- 完成标准：数据库、vector、plugin、Agent、workflow/HITL/WebSocket、auth/RBAC、安全和离线门禁全部通过。

### B9：企业会话管理需求澄清

- 交付：产品契约，不是代码。
- 必答：actor、session 对象、list/revoke/expire 操作、scope、审计、保留时间、验收用例。
- 完成标准：能明确归类为官方 `VERIFY_ONLY` 或新增独立安全设计。

## 5. 任务依赖图

```text
                         ┌──────────────┐
                         │ B1 mode fix  │
                         └──────────────┘
                                ▲
                                │
┌──────────────┐          ┌──────┴───────┐
│ B0 guardrails├─────────>│ B2 migrations│
└──────┬───────┘          └───┬──────┬───┘
       │                       │      │
       ├──────────────────────>│ B3   │
       │                       └──┬───┘
       │                          │
       └──────────────────────> B4 backend
                                  │
                         B3 ───────┴──────> B5 frontend
                                             │
                                             v
                                          B6 overlay
                                             │
                                             v
                                          B7 offline
                                             │
                                             v
                                          B8 release gate

B9 requirement clarification is independent. Any resulting code task must join before B8.
```

## 6. 推荐合并顺序

1. B0 基线/护栏。
2. B1 独立最小回归修复。
3. B2 migration/schema。
4. B3 平台管理员后端。
5. B4 智慧广场后端。
6. B5 前端。
7. B6 overlay/镜像。
8. B7 离线链。
9. B8 完整验证与发布证据。

B3/B4 可在 B2 schema 和授权边界稳定后并行实现，但合并时建议先 B3（B4 审核依赖平台管理员）。B6 不应在业务 contract 未稳定时提前定版镜像；B7 必须在 B6 后；B8 最后且不能跳过。

## 7. 未决问题

1. 目标远端候选分支引用为何未在本地提供；维护者需确认它确实指向官方基线。
2. 平台管理员是纯 email 配置，还是需要数据库角色、审计和 break-glass 流程？email 变更/大小写/禁用账号如何处理？
3. 平台管理员首版是否必须支持密码重置和 workspace 归档？这两项需要高风险操作审计和恢复策略。
4. 智慧广场发布后是不可变 DSL snapshot，还是动态引用 source app？源 app 删除/修改时如何处理？
5. 智慧广场复制目标是否总是 current workspace？复制权限和 plugin/knowledge 依赖缺失如何向用户呈现？
6. 旧企业 `enterprise_marketplace_assets` 是否存在真实生产数据、非标准 schema 或额外 revision？迁移实现前需要只读 inventory。
7. “企业会话管理”精确定义是什么？
8. 离线目标支持哪些 CPU 架构和 vector stores？manifest 是否必须包含多架构 digest？
9. 私有 `.difypkg` 的签名根/可信来源是什么？是否允许任何部署默认关闭签名验证（建议否）？
10. Agent local sandbox 的持久化/清理/retention 企业策略是什么？是否需要独立磁盘配额和审计？
11. `uv flask db heads` 在本工作区因受限网络无法获取锁定 Git 依赖；Builder 依赖环境必须补跑并保存输出。

## 8. Reviewer 精确审查范围

### 基线与范围 Reviewer

- 审查 `git merge-base 1.16.0 HEAD`、每个 Builder diff、无旧目录/volume/cache/真实 env。
- 拒绝混合多个 B 任务的提交或无失败测试的“兼容修复”。

### Backend/API Reviewer

- 仅审查 B2/B3/B4 的 migration、model/domain/service/controller/contract/tests。
- 确认 controller 无 direct SQLAlchemy；service 显式 Session；事务由明确调用者拥有。
- 确认 tenant/owner scope、状态机、幂等、并发、错误映射、无 secret DSL 和审计。
- 对照 `api/AGENTS.md` 与 `api/controllers/API_SCHEMA_GUIDE.md`。

### Frontend Reviewer

- 仅审查 B1/B5 及生成 contract 消费。
- 确认无 `any`、无手写 Console types/fetch、无旧 app context、无硬编码文案。
- 确认 TanStack Query/Jotai ownership、导航权限、loading/error/empty、a11y 和测试。
- 对照 `web/AGENTS.md`、当前生成 contracts 和 TypeScript/Vite+/ESLint 规则。

### Security Reviewer

- 精查平台管理员授权/高风险操作、智慧广场跨 tenant/DSL copy、SSRF/open redirect、RBAC、Agent keys/Landlock/sandbox plan、plugin signature、manifest secret。
- 逐项确认官方 `d9884efaee`（SQLi）、`ae0d6ee214`（SSRF）、`c68e5e5ed3`（redirect）、`38aec8b506`/`7311f1ba6d`（sandbox）、`71709f03c3`（Landlock）未回退。

### Migration/Data Reviewer

- 精查 revision/down_revision 图、历史 IDs、DDL 幂等/兼容、单 head 和四起点测试。
- 对照迁移前后 inventory；禁止 stamp、自动删表/数据或用空库成功代替升级成功。
- 审查 vector checker 默认只读；repair 必须独立审批。

### Docker/Offline Reviewer

- 只审查 B6/B7 的 overlay/build/package/docs；官方 `docker/docker-compose.yaml` 必须无修改。
- 检查五个企业 runtime、Agent 两服务、key 对齐、Landlock、healthcheck、profiles、image ID/commit、`Mode=reuse`。
- 扫描 archive 内容，确认不含 volume、`.env`、secret、cache、源控制元数据。

### Runtime/Release Reviewer

- 按 `VALIDATION_PLAN.md` 复核原始命令/退出码/日志/image IDs/migration inventory/浏览器用例。
- 不接受针对旧容器、不同 image IDs 或联网环境通过后直接声称离线包通过。

## 9. Reviewer 不应审查为“需要保留”的旧代码

- `system_oauth_encryption.py` 重复抽象。
- 旧平台管理员/智慧广场 controller/service/UI 的具体编码形式。
- 旧手写 Web models/hooks、旧 app context 和 1.15 API 兼容调整。
- 旧 Dockerfile/Compose/lockfile 和版本文档。
- 旧 workflow/HITL/plugin/dataset 修复，除非有 1.16 失败测试和独立决策记录。

所有旧内容的唯一价值是需求、历史故障和验收样例；实现评审必须以 1.16 官方代码与本交接的边界为准。

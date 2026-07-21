# Dify Enterprise 1.16.0 Replay Plan

## 1. 唯一基线

- 官方稳定标签：`1.16.0`
- 官方提交：`5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 候选来源名：`codex/enterprise-candidate-1.16.0-20260718`
- 当前架构工作树分支：`ctyun/replay-116-architect`
- 重放实现基线：`5c6372d2f76d240265b92fd27c16bc772ffcb107`

本地没有 `origin/codex/enterprise-candidate-1.16.0-20260718` 跟踪引用，不能用远端引用名复核；但架构分析起点、用户指定基线与本地官方 `1.16.0` 标签完全一致。实施前由维护者确认目标候选分支已从该提交创建。

官方 1.16.0 是实现真相。旧企业分支 `origin/codex/enterprise-candidate-1.15.0-20260626` 只提供需求、历史原因和验证样例，禁止机械 cherry-pick、复制目录或覆盖官方文件树。

## 2. 本轮架构结论

1. 官方已完整提供默认 workspace 自动加入、注册/创建 workspace 开关及测试；企业平行实现删除。
2. 平台管理员和智慧广场仍是企业差距，但旧 controller、手写 Web API、隐式 `db.session` 和旧状态模型不符合 1.16；必须按生成式 Console contract、显式 Session 和 Jotai 边界重实现。
3. 旧 OAuth 专用加密器与官方算法/密文格式等价，删除；生成器 model mode 归一化仍是可证明的最小缺口，保留为独立补丁。
4. Workflow、HITL、Plugin、Dataset、auth/RBAC 和安全修复以官方为准；旧候选无可证明的新差距时只验证，不重放。
5. 1.16 Compose 新增 `agent_backend`/`local_sandbox`。企业 overlay、API/Web 镜像和离线包必须围绕新服务图重写；不得覆盖 Landlock、Agent key、depends_on 或官方安全默认。
6. Release 的 migration 描述不一致：标题说 9、列表/upgrade guide 说 8；标签差异实际新增 5 个文件。升级自官方 1.15 时应执行这 5 个新 revision。
7. 旧企业数据库可能停在 `e2f0a9b7c6d5`。实现必须保留历史 revision 可解析性并新增连接它与官方 `7a1c2d9e4b60` 的 merge；禁止直接 stamp。
8. “企业会话管理”没有足够契约，当前 `DEFER`。若产品确认只指账号多设备 session，则官方已覆盖，转 `VERIFY_ONLY`。
9. 智慧广场推荐采用“发布时生成不可变快照”：已发布内容可审计且不随源应用静默变化，跨 workspace 复制不依赖源权限，源应用删除后资产仍可用。该决定进入 Builder 前的人工 Design Gate；若历史业务事实冲突，必须在 Builder 启动前提出。
10. migration 职责严格拆分：B2 只恢复历史 revision 并创建空 merge，B4 在 merge 后追加最终 schema migration；B2 不猜测 1.16 智慧广场 schema。

详细证据：

- [官方发布分析](docs/enterprise/replay-1.16.0/OFFICIAL_RELEASE_ANALYSIS.md)
- [补丁决策矩阵](docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md)
- [验证计划](docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md)
- [架构交接](docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md)

## 3. 重放原则

1. 从官方标签构建，不以旧企业 commit 为 merge base。
2. 一个 Builder 任务只交付一个可验证能力；混合旧提交必须拆开。
3. 先写失败测试/contract，再实现，再跑最小验证。
4. 后端遵守 controller→service→domain，所有 DB 操作显式 session 和 tenant/owner scope。
5. Console endpoint 使用 Pydantic request/response 并生成 route/type；Web 使用 `consoleQuery`/`consoleClient`。
6. Web server state 用 TanStack Query，feature UI state 用局部 state/Jotai，不恢复 app context。
7. Docker 基础 Compose 保持官方原样；企业 overlay 只覆盖最小字段。
8. 安全修复不可被旧 lockfile、旧网络调用、旧 vector query、旧 auth route 或旧 sandbox 配置回退。
9. migration 以实际代码图为准；空库和升级库必须分别测试。
10. 不访问、复制、修改、提交或打包 `docker/volumes/**`。

## 4. 建议 Builder 工作包

### B0 基线与安全护栏

- 锁定基线、diff allowlist、官方安全回归集合、生成 contract 命令和 Compose 静态检查。
- 输出：CI/Reviewer 可复现的基线证据；不改业务行为。

### B1 生成器 model mode 最小修复

- 先移植需求测试，再按 1.16 TS/i18n 格式实现纯归一化函数和两个调用点。
- 独立于其他企业能力，可最先合并。

### B2 migration 历史兼容与空 merge

- 从旧企业候选恢复 `c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5`，保持 revision ID、`down_revision`、`branch_labels` 和 `upgrade()`/`downgrade()` 历史 DDL 语义；不得重新生成 ID，不得用 `alembic stamp` 伪造状态。
- 新增空 merge revision `a71e16c0de01`（文件 `2026_07_21_1000-a71e16c0de01_merge_1_16_0_enterprise_heads.py`），parents 精确为 `e2f0a9b7c6d5` 和 `7a1c2d9e4b60`，其中不得包含业务 DDL。
- 验证旧企业数据库能定位完整 revision 历史。B2 不定义 1.16 智慧广场新增列、索引、约束或数据迁移。

### B3 平台管理员授权与后端

- 明确平台管理员授权、审计和高风险操作范围。
- 实现 session-injected service、Pydantic DTO、Console endpoints 和 contract tests。
- 密码重置/归档若无审计设计，单独延后，不与列表/邀请能力绑定。

### B4 智慧广场后端

- 以“发布时生成不可变快照”为推荐架构决定，通过人工 Design Gate 后定义 1.16 最终 schema。
- 在 B2 的空 merge 后追加 schema migration `b416e5c4e702`（文件 `2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py`，`down_revision = "a71e16c0de01"`）；它才是最终企业 head，并独占新增列、索引、约束和数据迁移。严禁把这些 DDL 塞入 merge revision。
- 实现 marketplace service/controller、提交/审核/列表/复制状态机、owner scope、官方 SSRF 防护路径、无 secret DSL copy，以及最终 Console OpenAPI contract generation。

### B5 平台管理员与智慧广场前端

- 消费 B3/B4 生成 contracts。
- 使用 `consoleQuery`、feature state/Jotai、权限派生导航和 i18n；补 UI 行为测试。

### B6 1.16 enterprise overlay 与镜像

- 以官方 Compose/Dockerfile 为基线，只覆盖企业 API/Web images、企业安全默认和 `api_websocket`。
- 保留 agent_backend/local_sandbox 的官方依赖、安全和 healthcheck。

### B7 离线插件、离线镜像包与配置包

- 复用官方 plugin mirror/签名配置。
- 从两层 Compose 解析镜像，强制包含 Agent 两镜像；manifest 绑定已验证 image IDs/commit。
- 配置包包含新 env examples，排除 secret/volume/cache。

### B8 Dataset/vector/升级验证工具

- 默认只读地检测关系库与 vector class/collection 一致性。
- repair 作为独立、需审批的后续任务。
- 执行完整升级/runtime/offline 验证，不预设要改官方 Dataset 代码。

### B9 会话管理需求澄清

- 非代码任务。确认 actor/object/actions/audit/expiry/acceptance。
- 若只是官方 account sessions，关闭为 `VERIFY_ONLY`；否则重新做安全/架构设计。

## 5. 依赖与合并顺序

```text
B0 ─┬─> B1
    └─> B2 ─> B3 ─> B4 ─> B5 ─> B6 ─> B7 ─> B8

B9（澄清）必须在 B6 开始前截止；若产生实现任务，追加为 B10，经独立安全/架构评审并在 B8 发布门禁前完成。
```

推荐合并：`B0 → B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8`。同步点强制为 B3 合并后 B4 才开始，B4 完成最终 contract generation 并合并后 B5 才开始；B3、B4 不并行，B5 不自行重新生成 contract。

每个工作包的 Allowed write paths、Read-only reference paths、Forbidden paths、generated artifacts owner、前置任务、合并顺序和验收命令，以及共享文件唯一所有者，见 `ARCHITECT_HANDOFF.md` 的“Builder 文件所有权与重叠矩阵”。未声明文件一旦出现在 Builder diff 中，必须暂停并重新审批范围。

## 6. 明确不重放

- 旧企业源码目录或整个初始提交。
- 旧 OAuth 专用加密器。
- 1.15 Dockerfile、lockfile、Compose service 定义和旧 migration merge head 作为最终 head。
- 旧 install/sign-in/public route 修复、workflow/HITL/plugin/dataset 源码补丁，除非 1.16 失败用例先证明缺口。
- 旧手写 Web Console models/services、app context、legacy contract loader。
- 旧 docs 中的版本、分支、镜像 tag、升级命令。
- `docker/volumes/**`、`.env`、secret、build cache、`.venv`、node_modules、`.next`。

## 7. 发布验收摘要

- 源码：目标测试、type-check、`pnpm check`、OpenAPI generation consistency、`git diff --check`。
- 数据库：单 head；四起点 upgrade；智慧广场数据/tenant/member/dataset 不丢。
- 运行：安装/登录/RBAC、平台管理员、智慧广场、Agent App、workflow/HITL/WebSocket、plugin、dataset/hit testing。
- 安全：SQLi、SSRF、open redirect、sandbox plan、Landlock、secret 和 owner scope。
- 镜像：五个企业 runtime identity 正确，Agent 两服务存在。
- 离线：`Mode=reuse` 复用验证镜像；无外网启动；包内无 volumes/secret。

完整步骤与失败判定见 `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md`。

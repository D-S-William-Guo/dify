# Dify Enterprise 1.16.0 当前状态与新窗口交接

更新时间：2026-08-08（Asia/Shanghai）

本文是新旧 Codex 窗口之间的首要交接入口。它记录当前可信 Git 状态、已通过的门禁、尚未完成的运行验证、下一步顺序，以及 Claude Squad/worktree 的协作规则。

如本文与聊天记录冲突，以 Git、最终复审报告和实际命令输出为准；不要依赖聊天记忆猜测状态。

## 1. 当前可信快照

| 项目 | 当前值 |
| --- | --- |
| 本地仓库 | `/home/ctyun/BigData/GitHub/dify-enterprise-1.16.0` |
| 候选分支 | `codex/enterprise-candidate-1.16.0-20260718` |
| B5 Plan checkpoint | `c0c398f423135dcd118b2dce8be4d6c91562c1a7`（B5 Plan Rereview） |
| B5 Contract checkpoint | `8cd884538bf1d58e92af711e49b72f2cdf061672`（Contract Rereview PASS） |
| B5-E i18n checkpoint | `e319481a7bc1e39ca91200f1b67a6541710c1aa4`（B5-E independent Review PASS） |
| B5-A checkpoint | `11bae180bb8c2786dd89a45f6c062a784b63510a`（B5-A Review PASS） |
| B5-B checkpoint | `0bc4a1e3101ff8109a84a907421b8fa0e3c03c94`（B5-B Review PASS） |
| B5-C checkpoint | `1385ef5dbfce490ef8d224bb2f3a7838646b9046`（B5-C Rereview PASS） |
| B5-D checkpoint | `68822f521507b890ad663ef5a5affb9c2ef91b56`（B5-D Rereview PASS） |
| B5 Final checkpoint | `e7d487538fb1431a3b769a8d3fe9d8354487ceea`（Final Review PASS） |
| B4 产品 checkpoint | `9c4c0356f3f2374c22b383ba96331e1dd92505fd` |
| 交接文档 commit | 使用 `git log -1 --format=%H -- docs/enterprise/replay-1.16.0/CURRENT_STATE.md` 获取，避免文件自引用 commit |
| 远端跟踪 | `origin/codex/enterprise-candidate-1.16.0-20260718` |
| origin | `https://github.com/D-S-William-Guo/dify.git` |
| upstream | `https://github.com/langgenius/dify.git` |
| 官方基线 tag | `1.16.0` |
| 官方基线 commit | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| Alembic 最终 head | `b416e5c4e702`（唯一 head） |
| Skill 源仓库 | `/home/ctyun/BigData/GitHub/codex-personal-skills` |
| Skill 源 commit | `33928a0`（含单控制器、事件驱动清理、下一步 ownership、human-signaled completion、长提示词 human-submit、`cs create` 非交互路径与大契约 temp-file 投递） |
| Claude Squad 定制 commit | `a1e35dc7436454cb53a584b8730166e23055ad4b`（`fix/n-overlay-small-terminal`，含 governed workflow safeguards 与小终端 overlay 修复） |
| 工作区 | 候选在 `e7d487538fb1431a3b769a8d3fe9d8354487ceea` 集成核验时干净；本文件更新期间仅允许本文件 dirty |
| 本地与 origin | 本地已集成 B5 全链并通过 Final Review；origin 已同步（checkpoint push 完成） |
| 当前产品里程碑 | B0～B4 已闭环；B5 全部阶段 PASS（Plan/Contract/B5-E/A/B/C/D/Full Regression/Final Review）；下一阶段 B6 enterprise overlay / 企业镜像 |

禁止向 `upstream/langgenius/dify` 推送企业候选或创建企业 PR。企业分支只推送到用户 fork `origin`。

恢复时先运行：

```bash
cd /home/ctyun/BigData/GitHub/dify-enterprise-1.16.0
git status --short --branch
git rev-parse HEAD
git rev-parse origin/codex/enterprise-candidate-1.16.0-20260718
git merge-base --is-ancestor 9c4c0356f3f2374c22b383ba96331e1dd92505fd HEAD
git merge-base 1.16.0 HEAD
```

预期：

- 本地 HEAD 包含 B5 Final checkpoint `e7d487538fb1431a3b769a8d3fe9d8354487ceea`；状态文档 checkpoint push 完成后，本地 HEAD 与 origin 相同；
- B4 checkpoint `9c4c0356f3f2374c22b383ba96331e1dd92505fd` 是当前 HEAD 的祖先；
- merge-base 为官方 1.16.0 commit；
- 工作区无修改。

任何一项不符时，不得直接启动新 Builder。先诊断分支、worktree 和未提交修改。

## 2. 当前工作顺序

当前已完成 B5 全链：Architect → Plan Reviewer/Fixer/Rereviewer、Contract Fixer/Reviewer/Ruff Fixer/Rereviewer、B5-E i18n Builder/Reviewer、B5-A Builder/Reviewer、B5-B Builder/Reviewer、B5-C Builder/Reviewer/Fixer/Rereviewer、B5-D Builder/Reviewer/Fixer/Rereviewer、full regression 与 Final Reviewer。B5 Final checkpoint 已 fast-forward 到候选分支。下一阶段是 B6 enterprise overlay / 企业镜像，但尚未授权创建实例。

协作基础设施当前状态：

1. 通用 Claude Squad/worktree 协作 Skill：已升级到安全半自动化版并安装；
2. Dify 官方版本企业功能重放 Skill：已创建并安装；
3. 两个 Skill 已通过结构校验；Git 起点核验脚本已通过正向/负向测试；
4. Claude Squad 源 checkpoint 为 `a1e35dc7436454cb53a584b8730166e23055ad4b`，并启用 `"governed_mode": true`；
5. dirty worktree 下 `c`/`p`/`D` 会拒绝危险操作；`D` 会明确提示是否删除本地分支；
6. B5 Plan 与 Contract 角色链实例已清理；B5-A 起至 Final Reviewer 的已完成实例暂时保留，等待 checkpoint 推送后执行事件驱动清理审计；
7. B5 全链已关闭；下一阶段 B6 不得并行启动任何 Builder。

Skill 路径：

```text
源：
/home/ctyun/BigData/GitHub/codex-personal-skills/orchestrate-claude-squad
/home/ctyun/BigData/GitHub/codex-personal-skills/replay-dify-enterprise

Codex 自动发现链接：
/home/ctyun/.codex/skills/orchestrate-claude-squad
/home/ctyun/.codex/skills/replay-dify-enterprise
```

Skill 源仓库当前只有本地 Git commit，尚未配置远端；这不影响本机使用，但未来需要异机同步时应单独配置备份/远端。

产品流水线的下一阶段是：

```text
B5 平台管理员与智慧广场前端
→ B6 enterprise overlay / 企业镜像
→ B7 离线镜像包与配置包
→ B8 数据库、vector、volume 升级和发布验证
```

B9“企业会话管理”仍是产品契约澄清，不是已授权代码任务；最迟在 B6 开始前决定，未决定则保持 `DEFER`。

## 3. 已完成阶段

### Design Gate

已完成官方 release/tag 分析、旧企业补丁决策矩阵、实施拆分、文件所有权和验证计划。

关键原则：

- 官方 1.16 是实现真相；
- 官方已经覆盖或修复的旧企业实现必须舍弃；
- 不把旧候选整体 cherry-pick 到 1.16；
- 旧代码只作为需求和风险证据；
- 每个阶段使用精确 SHA、allowlist、独立 Review 和人工门禁。

主要入口：

- `ARCHITECT_HANDOFF.md`
- `DESIGN_GATE.md`
- `PATCH_DECISION_MATRIX.md`
- `VALIDATION_PLAN.md`
- `OFFICIAL_RELEASE_ANALYSIS.md`

### B0：企业重放护栏

最终 checkpoint：`0c2e573633`

完成：

- 官方基线与 diff scope 检查；
- controller/SQLAlchemy/session 等越界检测；
- 跨 hunk 和 fallback 绕过修复；
- 生成链与禁止路径护栏。

最终报告：`B0_REREVIEW_2.md`。

### B1：Generator model mode 归一化

最终 checkpoint：`bfc122e98e`

完成 automatic/code generator model mode 的归一化、缺失 mode 处理和 focused tests。

最终报告：`B1_REREVIEW.md`。

### B2：只读 inventory 与 migration graph

最终 checkpoint：`578e9c2754`

完成：

- 旧 1.15 运行环境只读 inventory；
- 恢复企业历史 revisions：
  - `c8f3d9d4a1be`
  - `f1a14e1e9b41`
  - `e2f0a9b7c6d5`
- 增加 1.16 空 merge：`a71e16c0de01`；
- 保证 migration graph 可审计。

重要：B2 只恢复历史链，没有执行真实数据库 upgrade/stamp。

主要报告：

- `B2_INVENTORY.md`
- `B2_INVENTORY_REVIEW.md`
- `B2_REVIEW.md`

### B3：平台管理员后端

最终 checkpoint：`925b01e9d2`

完成：

- 平台管理员身份；
- workspace list/detail/rename；
- member list/invite/non-owner role update；
- 精确 7 条 Console route；
- session-injected service；
- RBAC mutation fail-closed；
- contracts 由 B4 统一生成。

明确不包含：

- member DELETE/removal；
- workspace create/delete/archive；
- owner mutation；
- password reset；
- break-glass；
- 新 audit model。

最终报告：`B3_REVIEW.md`。

### B4：智慧广场后端

最终 checkpoint：`9c4c0356f3f2374c22b383ba96331e1dd92505fd`

最终结论：

```text
PASS
P0/P1/P2 open findings = 0/0/0
B4_FINAL_ACCEPTED
CHECKPOINT_PUSH_GATE_RECOMMENDED
398 collected / 398 passed / 0 NOT_RUN
contracts generation deterministic twice
Alembic unique head = b416e5c4e702
```

完成：

- B4-A：最终 marketplace schema/model/migration；
- B4-B：状态机、不可变 snapshot、sanitizer、dependency、copy、backfill CLI；
- B4-C：8 条 marketplace route、权限、DTO、真实 401/domain error contracts；
- 同时生成 B3 7 条和 B4 8 条 Console contracts；
- 修复 first-submit 非空 `expected_row_version` 误创建资产；
- 修复 `approved/unlisted` 与 `approved/unpublished` 无法 resubmit；
- 真实下架、legacy backfill、stale version 路径均有行为测试。

主要报告：

- `B4_IMPLEMENTATION_PLAN.md`
- `B4_A_REREVIEW.md`
- `B4_B_REREVIEW.md`
- `B4_FINAL_REVIEW.md`
- `B4_FINAL_REREVIEW.md`

### B5：企业重放前端全链（B5-E/A/B/C/D + 回归 + Final Review）

当前已接受 B5 Final checkpoint：`e7d487538fb1431a3b769a8d3fe9d8354487ceea`

已完成：

- Architect：`d5b365093ef7272b3cbb36a4ac16ba595f96f2ca`；
- Plan Reviewer：`dfa98c711aee15226e3eabd3b2320d3557aa8e2c`；
- Plan Fixer：`325fb52608890dcfafab72f2dbb3f40069f02f80`；
- Plan Rereviewer：`c0c398f423135dcd118b2dce8be4d6c91562c1a7`，结论 `PASS`、`PLAN_ACCEPTED=yes`。
- Contract Fixer：`7237af7c759f433fac9e2e2c1a1b63d816134a24`；
- Contract Reviewer：`ccc96aef5c38e4605ef927d67f500eb3543e3c8f`，发现并接受 `B5CR-02` targeted Ruff finding；
- Contract Ruff Fixer：`6b6305f2cdeb436c4736978a02240e99ae6c8e5f`；
- Contract Rereviewer：`8cd884538bf1d58e92af711e49b72f2cdf061672`，结论 `PASS`、`CONTRACT_FIX_ACCEPTED=yes`、open findings `0/0/0`。
- B5-E i18n Builder：`f5cf5bee66d924e1bd75b66d01ad635b225a0857`，只修改 23 个 approved locale `common.json`；
- B5-E independent Reviewer：`e319481a7bc1e39ca91200f1b67a6541710c1aa4`，结论 `PASS`、`B5_E_ACCEPTED=yes`、open findings `0/0/0`。
- B5-A Builder：`683f98c8e2d8ca8b207709088fe15299ec499bb0`；Reviewer `11bae180bb8c2786dd89a45f6c062a784b63510a`，结论 `PASS`、`B5_A_ACCEPTED=yes`。
- B5-B Builder：`f912864a1a963a9f89fac46612dc7d85c472e088`；Reviewer `0bc4a1e3101ff8109a84a907421b8fa0e3c03c94`，结论 `PASS`、`B5_B_ACCEPTED=yes`。
- B5-C Builder：`a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b`；Reviewer `80253fcc942121aa662c605b93dc54d340dd00f2` 报 `CHANGES_REQUIRED`（B5CR-01/02）；Fixer `1be688b81ee0f2f0029b84c17b3ca65ca8028d78`；Rereviewer `1385ef5dbfce490ef8d224bb2f3a7838646b9046`，结论 `PASS`。
- B5-D Builder：`06279393ed992f8f2c5d518110b1e595bf6fe43f`；Reviewer `f0d72492f809392c598deb7220e4d87a21cb14f9` 报 `CHANGES_REQUIRED`（B5DR-01/02）；Fixer `35468cd742299d96506e280babd36f068e565fd4`；Rereviewer `68822f521507b890ad663ef5a5affb9c2ef91b56`，结论 `PASS`。
- Full regression：`f1941fc6a5dd312340b96f52bcaab95a9db0e711`，结论 `PASS`；完整 Vitest 295/295、type-check、i18n check PASS；browser/E2E 如实 `NOT_RUN`。
- Final Reviewer：`e7d487538fb1431a3b769a8d3fe9d8354487ceea`，结论 `PASS`、open findings `0/0/0`。

已关闭的计划 findings：

- `B5PR-01`：采用 `MOVE_B5_E_BEFORE_B5_A`，先落盘并独立审查全部 23 locale；
- `B5PR-02`：采用 `B5_C_OWNS_DEDICATED_RESUBMIT_DIALOG`，消除 B5-C 对 B5-D 的前向依赖。

已记录的产品/实施决定：

- `CONTRACT_FIX_REQUIRED`；
- `I18N_OPTION_B_APPROVED`；
- B5-E 是 23 个 locale `common.json` 的唯一 writer；
- 实际串行顺序为 contract 修复门禁 → B5-E → B5-A → B5-B → B5-C → B5-D。

Contract Rereview 已关闭 B5 的 contract 前置阻断；两次官方 generation 均得到与 HEAD
一致的生成内容，已接受的 179 项对称 `DA` 是 generator/index tracking 流程偏差，不是
contracts 内容差异。B5 产品范围与所有阶段门禁均已接受；完整 Vitest 295/295、
type-check、23-locale `i18n:check` 均 PASS；`pnpm check` 仅重现已接受的 5 个 B1
formatting baseline（ESLint `NOT_RUN`）。browser/E2E 因本地环境只有 1.15.0 enterprise
容器、无 B5 生产 artifact 且 integration tests 仅 CI 运行，如实 `NOT_RUN`。
下一阶段是 B6 enterprise overlay / 企业镜像，尚未授权。

主要报告：

- `B5_IMPLEMENTATION_PLAN.md`
- `B5_IMPLEMENTATION_PLAN_REVIEW.md`
- `B5_IMPLEMENTATION_PLAN_REREVIEW.md`
- `B5_CONTRACT_FIX_REVIEW.md`
- `B5_CONTRACT_FIX_REREVIEW.md`
- `B5_E_I18N_REVIEW.md`
- `B5_A_REVIEW.md`
- `B5_B_REVIEW.md`
- `B5_C_REVIEW.md`
- `B5_C_REREVIEW.md`
- `B5_D_REVIEW.md`
- `B5_D_REREVIEW.md`
- `B5_FULL_REGRESSION_REPORT.md`
- `B5_FINAL_REVIEW.md`

## 4. B4 最终契约摘要

### B3 route

精确 7 条：

```text
GET   /console/api/account/platform-admin-status
GET   /console/api/platform-admin/workspaces
GET   /console/api/platform-admin/workspaces/<workspace_id>
PATCH /console/api/platform-admin/workspaces/<workspace_id>
GET   /console/api/platform-admin/workspaces/<workspace_id>/members
POST  /console/api/platform-admin/workspaces/<workspace_id>/members/invitations
PATCH /console/api/platform-admin/workspaces/<workspace_id>/members/<member_id>/role
```

### B4 route

精确 8 条：

```text
POST /console/api/apps/<app_id>/enterprise-marketplace/submissions
GET  /console/api/enterprise-marketplace/submissions
GET  /console/api/enterprise-marketplace/assets
GET  /console/api/enterprise-marketplace/assets/<asset_id>
POST /console/api/enterprise-marketplace/assets/<asset_id>/copies
GET  /console/api/platform-admin/enterprise-marketplace/assets
POST /console/api/platform-admin/enterprise-marketplace/assets/<asset_id>/reviews
POST /console/api/platform-admin/enterprise-marketplace/assets/<asset_id>/unlist
```

没有 marketplace DELETE、platform-admin member DELETE、workspace create/delete/archive、owner/password/break-glass route。

### Contracts

- 401：`UnauthorizedResponse {code, message}`；
- domain errors：`MarketplaceErrorResponse {code, message, status}`；
- B5 只消费 `packages/contracts/generated/api/console/**`；
- B5 不得重新生成或手写 Console response types。

### B5 已关闭的后置 contract completeness findings

以下 findings 不推翻 B3/B4 已接受的后端行为，且已在 B5 消费 contracts 前修复：

1. B3 platform-admin/status generated contracts 缺少与真实可达错误响应对应的 typed
   error unions；`PlatformAdminErrorResponse` 未完整进入 generated contracts。
2. B4 marketplace review 路由实际可达 `422` domain errors，但 OpenAPI 路由声明和
   `PostPlatformAdminEnterpriseMarketplaceAssetsByAssetIdReviewsErrors` 均缺少 `422`。

已接受 checkpoint `8cd884538bf1d58e92af711e49b72f2cdf061672` 包含官方 generator
链修正、行为/契约测试、generated contracts、targeted Ruff 修复和独立 Rereview 报告。
验证结果包括 focused `97 passed`、B3/B4 九文件 `403 passed`、contracts `4 passed`、
type-check PASS、targeted Ruff/format PASS，以及两次 deterministic generation 内容与 HEAD
一致。禁止前端 direct fetch、手写 response/error types 或 legacy loader workaround 的
约束继续有效；B5 只消费已生成 contracts，不得重新生成。

## 5. 仍未完成的运行与升级验证

“代码和 contracts 通过”不等于“生产升级已通过”。

以下仍属于 B6～B8：

- 真实 PostgreSQL 升级/降级演练；
- 旧企业 1.15 数据库副本升级到 1.16；
- 官方 1.15、官方 1.16、空库等 migration 矩阵；
- 真实 PostgreSQL row-lock/deadlock/concurrency；
- marketplace snapshot backfill 的隔离副本演练；
- Weaviate object/index/hit testing；
- Compose overlay、镜像构建、运行容器 image ID；
- Agent backend/local sandbox；
- 旧 volume 的备份、挂载身份、升级和回滚；
- 离线包、无外网 smoke、最终发布证据。

不得在开发工作树或当前运行 volume 上直接执行 migration/repair。真实演练必须使用隔离数据库/volume 副本，并采用 B2 inventory 记录的实际挂载路径。

## 6. 已知限制与风险

### B4 accepted known limitations

以下两项已被明确接受，但不是“已经解决”：

1. 官方 `AppDslService.import_app()` 内部 commit 造成 copy 无法承诺完全原子回滚；
2. DSL 将来新增未知字段时，当前显式 sanitizer 规则可能需要同步扩展。

边界要求：

- 所有企业自有校验必须在 import 前完成；
- 不得声称 import 后仍能完整 rollback；
- B8 必须覆盖失败 reconciliation 和信息泄漏。

### 非阻断技术债

- 测试辅助代码仍有 `datetime.utcnow()` deprecation warning；
- 当前不阻断 B4，但后续可在独立测试清理任务中处理。

### B2/B8 运行风险

只读 inventory 发现：

- 核心 Dify 实际运行版本为 Enterprise 1.15.0；
- Weaviate/Sandbox 的创建和挂载 provenance 来自 1.14.2；
- SSRF Proxy 仍使用 1.14.2 配置，缺少 1.15 private destination 默认拒绝和 allowlist；
- Weaviate class 对应关系已核对，但对象完整性、hit testing 和部分 index 默认配置仍待 B8；
- volume provenance 必须按实际挂载路径验证，不能只相信 Compose 文件。

这些风险不得因为 B4 PASS 而被删除或降级。

## 7. B5 当前门禁与下一任务

B5 全链已完成独立门禁并接受：

```text
B5 Plan Rereview: c0c398f423135dcd118b2dce8be4d6c91562c1a7
B5 Contract Rereview: 8cd884538bf1d58e92af711e49b72f2cdf061672
B5-E Review: e319481a7bc1e39ca91200f1b67a6541710c1aa4
B5-A Review: 11bae180bb8c2786dd89a45f6c062a784b63510a
B5-B Review: 0bc4a1e3101ff8109a84a907421b8fa0e3c03c94
B5-C Rereview: 1385ef5dbfce490ef8d224bb2f3a7838646b9046
B5-D Rereview: 68822f521507b890ad663ef5a5affb9c2ef91b56
Full regression: f1941fc6a5dd312340b96f52bcaab95a9db0e711
Final Review: e7d487538fb1431a3b769a8d3fe9d8354487ceea
```

上述 checkpoint 均包含 B4 产品 checkpoint
`9c4c0356f3f2374c22b383ba96331e1dd92505fd`。交接文档不能自引用其未来 commit；
恢复时以 `git rev-parse HEAD` 取得当前候选精确 SHA，并要求它包含上述 B5 Final
checkpoint。状态文档 checkpoint 推送完成后，还要求本地与 origin 精确一致。

### 已关闭门禁摘要

- B5-E：23 个 locale `common.json` 全量落盘，139 个 approved keys；`i18n:check`、type-check PASS。
- B5-A：8 个 exact files，main-nav 权限 fail-closed、typed error mapping、shared invalidation 唯一 writer；Review PASS。
- B5-B：15 个 exact files，platform-admin workspace/member UI；Review PASS。
- B5-C：23 个 exact files，marketplace browse/detail/submissions/admin review + 专用 resubmit dialog；Review 发现 B5CR-01/02，Fixer 关闭，Rereview PASS。
- B5-D：4 个 exact files，app-card first-submit entry + first-submit dialog；Review 发现 B5DR-01/02，Fixer 关闭，Rereview PASS。
- Full regression：完整 Vitest 295/295、web/e2e type-check、23-locale i18n check PASS；`pnpm check` 仅 5 个 B1 baseline，ESLint `NOT_RUN`；browser/E2E `NOT_RUN`（环境 blocker 已记录）。
- Final Review：全 B5 范围、门禁链、证据均核验；`PASS`、open findings `0/0/0`。

### 下一阶段：B6 enterprise overlay / 企业镜像

B6 尚未授权。恢复时以创建时重新读取的候选完整 40 位 HEAD 为起点；不得重新生成
contracts、不得修改任何 locale/i18n 文件、不得恢复旧 enterprise context/loader。

## 8. Claude Squad / worktree 协作 SOP

### 角色和生命周期

每个实例只承担一个明确角色：

- Architect：分析和任务拆分；
- Builder：实现；
- Reviewer：独立挑战；
- Fixer：只修已确认 finding；
- Rereviewer：关闭 finding 和最终门禁。

一个实例是阶段性 worktree，不是永久 AI 员工。分支已 fast-forward 合并且候选分支已 push 后，该实例即可删除。

### 创建任务

每个 `N` 任务单必须包含：

1. instance name；
2. 角色；
3. 候选 base branch；
4. 完整 40 位精确起点 SHA；
5. 起点 branch/HEAD/clean 三项核验；
6. allowlist；
7. denylist；
8. 必须运行的测试；
9. NOT_RUN 规则；
10. commit/amend/push 权限；
11. 最终报告格式。

禁止使用“从最新 HEAD 开始”等可漂移表述。

### worktree 与候选分支的关系

```text
候选主目录/候选分支
        │
        ├── Claude Squad worktree A / branch A / commit A
        ├── Claude Squad worktree B / branch B / commit B
        └── Claude Squad worktree C / branch C / commit C
```

Agent 在自己的 worktree 内修改并提交。

协调者在候选主目录执行：

```bash
git merge --ff-only ctyun/<instance-branch>
```

这不是重复工作：

- worktree commit 生成独立 Git 对象；
- 候选目录的 `--ff-only` 只是把候选分支指针推进到已审 commit；
- 最终只从候选分支 push；
- instance branch 通常不 push。

### 门禁

- Builder dirty diff 先检查，再授权 commit；
- commit hook 留下新修改时不得忽略，重新测试后 amend；
- Review 报告也先合并，再从“报告合并后的精确 SHA”创建 Fixer；
- Reviewer 不能默认相信 Builder 报告；
- 测试通过不能代替源码/契约审查；
- `CHANGES_REQUIRED` 不允许直接进入下一 Builder；
- generated files 必须有唯一 owner；
- 主目录只做集成、检查和 push，不在那里并行写同一任务实现。

## 9. 新窗口恢复提示词

新窗口可直接使用：

```text
请使用：

- $replay-dify-enterprise
- $orchestrate-claude-squad

先读取：

/home/ctyun/BigData/GitHub/dify-enterprise-1.16.0/docs/enterprise/replay-1.16.0/CURRENT_STATE.md

然后只读恢复并核验：

1. 仓库、分支、HEAD、origin 是否与文档一致；
2. 工作区是否干净；
3. B4_FINAL_REREVIEW.md 是否为 PASS；
4. B5_IMPLEMENTATION_PLAN_REREVIEW.md 是否为 PASS、PLAN_ACCEPTED=yes；
5. B5_CONTRACT_FIX_REREVIEW.md 是否为 PASS、CONTRACT_FIX_ACCEPTED=yes、open findings 0/0/0；
6. B5_E_I18N_REVIEW.md 是否为 PASS、B5_E_ACCEPTED=yes、open findings 0/0/0；
7. B5_A_REVIEW.md、B5_B_REVIEW.md 是否为 PASS；
8. B5_C_REREVIEW.md、B5_D_REREVIEW.md 是否为 PASS；
9. B5_FULL_REGRESSION_REPORT.md、B5_FINAL_REVIEW.md 是否为 PASS；
10. Skill 源 commit 是否包含 33928a0（`cs create` 非交互路径与大契约 temp-file 投递），
   Claude Squad 源 commit 是否包含 a1e35dc7436454cb53a584b8730166e23055ad4b；
11. 只恢复协调状态，不修改业务代码，不创建实例。

核验通过后：

1. 依据 CURRENT_STATE.md 第 7 节确认 B5 全链 PASS；
2. 下一阶段是 B6 enterprise overlay / 企业镜像，仍需人工授权；
3. 使用最新版 $orchestrate-claude-squad 生成 N 表单字段和完整任务契约；
4. 把任务契约交给我人工确认后再创建 Claude Squad 实例；
5. B5 不得重启，不得重新生成 contracts 或修改任何 locale/i18n 文件。

任何事实与文档不符时，先报告差异，不得自动 reset、merge、rebase、migration、Docker 或 volume。
```

## 10. 新窗口建议阅读顺序

不要重新阅读整段旧聊天。按以下顺序：

1. `CURRENT_STATE.md`
2. `B4_FINAL_REREVIEW.md`
3. `ARCHITECT_HANDOFF.md`
4. `PATCH_DECISION_MATRIX.md`
5. `VALIDATION_PLAN.md`
6. 下一任务相关的实施计划和最终 Review

只有发现矛盾或需要追溯设计理由时，才继续读取较早的 Review/Fixer 文档。

## 11. 当前实例状态

B5 Plan 与 Contract 角色链实例已经清理。当前保留 B5-A 至 Final Reviewer 的已完成实例
（以 state.json 为准，共 14 个），其 checkpoint 均已集成到候选分支，状态文档 checkpoint
已提交并推送。当前保留：

- `replay-116-b5-a-builder`、`replay-116-b5-a-reviewer`
- `replay-116-b5-b-builder`、`replay-116-b5-b-reviewer`
- `replay-116-b5-c-builder`、`replay-116-b5-c-reviewer`、`replay-116-b5-c-fixer`、`replay-116-b5-c-rereviewer`
- `replay-116-b5-d-builder`、`replay-116-b5-d-reviewer`、`replay-116-b5-d-fixer`、`replay-116-b5-d-rereviewer`
- `replay-116-b5-regression`
- `replay-116-b5-final-reviewer`

这些实例在 checkpoint push 后按事件驱动清理审计逐项确认：worktree clean、实例 commit
为候选 checkpoint 祖先、无未集成报告，再请求逐个删除授权。

进入 B6 前执行：

```bash
git worktree prune
git worktree list
git status --short --branch
```

预期在获批清理后只保留候选主目录；候选分支与 origin 同步，且包含 B4 checkpoint
`9c4c0356f3f2374c22b383ba96331e1dd92505fd`、B5 Plan Rereview checkpoint
`c0c398f423135dcd118b2dce8be4d6c91562c1a7` 和 B5 Contract Rereview checkpoint
`8cd884538bf1d58e92af711e49b72f2cdf061672`，以及 B5 Final checkpoint
`e7d487538fb1431a3b769a8d3fe9d8354487ceea`。随后以创建时重新读取的候选完整
40 位 HEAD 作为 B6 起点，不得使用移动的“latest HEAD”。

# Dify Enterprise 1.16.0 当前状态与新窗口交接

更新时间：2026-07-31（Asia/Shanghai）

本文是新旧 Codex 窗口之间的首要交接入口。它记录当前可信 Git 状态、已通过的门禁、尚未完成的运行验证、下一步顺序，以及 Claude Squad/worktree 的协作规则。

如本文与聊天记录冲突，以 Git、最终复审报告和实际命令输出为准；不要依赖聊天记忆猜测状态。

## 1. 当前可信快照

| 项目 | 当前值 |
| --- | --- |
| 本地仓库 | `/home/ctyun/BigData/GitHub/dify-enterprise-1.16.0` |
| 候选分支 | `codex/enterprise-candidate-1.16.0-20260718` |
| B4 产品 checkpoint | `9c4c0356f3f2374c22b383ba96331e1dd92505fd` |
| 交接文档 commit | 使用 `git log -1 --format=%H -- docs/enterprise/replay-1.16.0/CURRENT_STATE.md` 获取，避免文件自引用 commit |
| 远端跟踪 | `origin/codex/enterprise-candidate-1.16.0-20260718` |
| origin | `https://github.com/D-S-William-Guo/dify.git` |
| upstream | `https://github.com/langgenius/dify.git` |
| 官方基线 tag | `1.16.0` |
| 官方基线 commit | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| Alembic 最终 head | `b416e5c4e702`（唯一 head） |
| Skill 源仓库 | `/home/ctyun/BigData/GitHub/codex-personal-skills` |
| Skill 源 commit | `2651320`（安全半自动化版） |
| Claude Squad 定制 commit | `3f480f6`（governed workflow safeguards） |
| 工作区 | 干净 |
| 本地与 origin | 已同步 |
| 当前产品里程碑 | B0～B4 已闭环；B4 `B4_FINAL_ACCEPTED` |

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

- 本地 HEAD 与 origin 相同；
- B4 checkpoint `9c4c0356f3f2374c22b383ba96331e1dd92505fd` 是当前 HEAD 的祖先；
- merge-base 为官方 1.16.0 commit；
- 工作区无修改。

任何一项不符时，不得直接启动新 Builder。先诊断分支、worktree 和未提交修改。

## 2. 当前工作顺序

当前已完成新窗口恢复验证和协作 Skill 安全半自动化升级，可以启动 B5 Architect 门禁；尚未授权 B5 Builder。

协作基础设施当前状态：

1. 通用 Claude Squad/worktree 协作 Skill：已升级到安全半自动化版并安装；
2. Dify 官方版本企业功能重放 Skill：已创建并安装；
3. 两个 Skill 已通过结构校验；Git 起点核验脚本已通过正向/负向测试；
4. Claude Squad 已安装 `3f480f6` 构建并启用 `"governed_mode": true`；
5. dirty worktree 下 `c`/`p`/`D` 会拒绝危险操作；`D` 会明确提示是否删除本地分支；
6. 当前无 Claude Squad 实例、B5 分支或额外 worktree；
7. 下一动作是生成并人工创建 B5 Architect，不得直接启动 B5 Builder。

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

## 7. B5 启动边界

B5 启动前必须先由 Architect 基于本 checkpoint 形成精确任务单，并由独立 Reviewer 审查。

产品代码 checkpoint：

```text
9c4c0356f3f2374c22b383ba96331e1dd92505fd
```

实际创建 B5 Architect 时，必须重新读取候选分支当前 40 位 HEAD，并把该值写入任务单。这个 HEAD 必须包含上述 B4 checkpoint，且 B4 后只能多出已审核的治理/交接文档提交；不要把 `9c4c...` 机械填成未来任务的起点。

B5 目标：

- 平台管理员和智慧广场前端；
- generated contract queries/mutations；
- Jotai/feature state；
- 权限入口和导航；
- submit/review/copy/error/empty/loading/retry UI；
- `platformAdmin.*` 和 `enterpriseMarketplace.*` i18n；
- 行为测试、type-check。

B5 禁止：

- 修改 `api/**`；
- 修改 migration/model/service/controller；
- 修改 `docker/**`；
- 修改 `dify-agent/**`；
- 修改或重新生成 `packages/contracts/**`；
- 手写 Console response types；
- 使用旧 app context 或 legacy contract loader；
- 未审批扩大 locale 或共享组件范围。

建议先建立 `B5_IMPLEMENTATION_PLAN.md`，经 Architect → Reviewer → Fixer（如需）→ Rereviewer 门禁后，再拆 Builder。

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
4. 当前是否不存在 B5 分支、额外 worktree 和 Claude Squad 实例；
5. Skill 源 commit 是否包含 2651320，Claude Squad 源 commit 是否包含 3f480f6；
6. 只恢复协调状态，不修改业务代码，不创建实例。

核验通过后：

1. 依据 CURRENT_STATE.md 第 7 节和 B4 最终 contracts，制定 B5 Architect 的精确只读任务；
2. 使用最新版 $orchestrate-claude-squad 生成 N 表单字段和完整任务契约；
3. B5 Architect 只能分析并编写 B5_IMPLEMENTATION_PLAN.md，不得实现前端；
4. 把任务契约交给我人工确认后再创建 Claude Squad 实例；
5. 不得直接启动 B5 Builder。

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

B4 已合并并推送，所有 B4 实例已经清理。当前：

- Claude Squad `instances: []`；
- 无 `ctyun/replay-116-b5-*` 分支；
- 无额外 worktree；
- B5 尚未启动。

开始 B5 前执行：

```bash
git worktree prune
git worktree list
git status --short --branch
```

预期只保留候选主目录；候选分支与 origin 同步，且包含 B4 checkpoint `9c4c0356f3f2374c22b383ba96331e1dd92505fd`。随后以候选分支新的完整 40 位 HEAD 作为 B5 Architect 起点。

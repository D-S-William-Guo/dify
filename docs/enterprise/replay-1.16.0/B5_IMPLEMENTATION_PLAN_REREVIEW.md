# Dify Enterprise 1.16.0 Replay B5 Implementation Plan — Independent Plan Rereview

- **Role**: Independent B5 Plan Rereviewer
- **Branch**: `ctyun/replay-116-b5-plan-rereviewer`
- **HEAD**: `325fb52608890dcfafab72f2dbb3f40069f02f80`
- **Plan Review commit**: `dfa98c711aee15226e3eabd3b2320d3557aa8e2c`
- **Plan Fixer commit under rereview**: `325fb52608890dcfafab72f2dbb3f40069f02f80`
- **B4 product checkpoint**: `9c4c0356f3f2374c22b383ba96331e1dd92505fd`
- **Reviewed artifact**: `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`（Fixer 后的计划）
- **结论**: `PASS`（plan-only；contract 修复仍阻断，Builder 未授权）

本报告是独立 Rereview 证据，不是计划改写。本 Rereviewer 未修改计划、API、
contracts、frontend 或任何 denylist 文件。

---

## 1. RECOVERY

| Check | Expected | Actual | Status |
| --- | --- | --- | --- |
| Branch | `ctyun/replay-116-b5-plan-rereviewer` | `ctyun/replay-116-b5-plan-rereviewer` | PASS |
| HEAD | `325fb52608890dcfafab72f2dbb3f40069f02f80` | `325fb52608890dcfafab72f2dbb3f40069f02f80` | PASS |
| Worktree clean | clean | clean（porcelain 无输出） | PASS |
| HEAD^ | `dfa98c711aee15226e3eabd3b2320d3557aa8e2c` | `dfa98c711aee15226e3eabd3b2320d3557aa8e2c` | PASS |
| B4 checkpoint ancestor | `9c4c0356f3f2374c22b383ba96331e1dd92505fd` 是 HEAD 祖先 | `git merge-base --is-ancestor` exit 0 | PASS |
| verifier | exact branch/SHA, clean | `verify_git_start.sh` exit 0，输出 `OK branch=... head=... clean=true` | PASS |

未执行 merge、rebase、reset、checkout、cherry-pick、commit、amend、push。

## 2. REVIEW_RANGE

- parent（Plan Review commit）: `dfa98c711aee15226e3eabd3b2320d3557aa8e2c`
- reviewed commit（Plan Fixer）: `325fb52608890dcfafab72f2dbb3f40069f02f80`
- exact changed files:
  - `M  docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`（346 insertions / 106 deletions）
- `git diff --name-status`：仅上述 1 个文件。
- `git diff --stat`：`1 file changed, 346 insertions(+), 106 deletions(-)`。
- `git diff --numstat`：`346 106 docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`。
- `git diff --check`（range 与 working tree）均 exit 0，无 whitespace 错误。
- `B5_IMPLEMENTATION_PLAN_REVIEW.md` 在本 range 内未被修改（`git diff ... -- B5_IMPLEMENTATION_PLAN_REVIEW.md` 输出为空）。

## 3. SOURCES_READ

- `docs/enterprise/replay-1.16.0/CURRENT_STATE.md`（逐行）
- `docs/enterprise/replay-1.16.0/B4_FINAL_REREVIEW.md`（逐行）
- `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REVIEW.md`（逐行）
- `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`（逐行，942 行）
- Fixer diff：`git diff dfa98c711..325fb52608 -- docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`
- typed-i18n 只读证据：
  - `web/types/i18n.d.ts`（`enableSelector: 'optimize'`、`keySeparator: false`、`resources: Resources`）
  - `web/i18n-config/resources.ts`（`common: typeof common`，`Resources` 由 `en-US/common.json` type 派生）
  - `web/i18n-config/settings.ts`（`fallbackLng: 'en-US'`、`load: 'currentOnly'`）
  - `.vite-hooks/pre-commit`（web/* 提交运行 `vp staged`）
  - `web/AGENTS.md`（i18n/overlay/client 规则）
  - `web/i18n-config/languages.ts`（`supported: true` 恰 23 个）
  - `web/i18n/<23>/common.json`（23 个均存在、扁平、各 618 keys）
- generated/backend 只读证据：
  - `packages/contracts/generated/api/console/platform-admin/types.gen.ts`
  - `packages/contracts/generated/api/console/account/types.gen.ts`
  - `packages/contracts/generated/api/console/platform-admin/orpc.gen.ts`
  - `api/controllers/console/platform_admin.py`
  - `api/controllers/console/enterprise_marketplace.py`
  - `api/services/enterprise_marketplace_service.py`
  - `api/services/errors/enterprise_marketplace.py`

## 4. B5PR-01 DISPOSITION — CLOSED

原 finding（Review `B5PR-01`）：“i18n key 引入顺序与 typed-i18n/commit 门禁冲突
（B5-A/B/C/D 无法通过 type-check/commit gate）”。Fixer 以
`MOVE_B5_E_BEFORE_B5_A` disposition 关闭。独立证据如下：

### 4.1 `MOVE_B5_E_BEFORE_B5_A` 在 §0/§8/§9/§10/§12/§13/§15/§16/§17 一致表述

| Section | 位置 | 内容 |
| --- | --- | --- |
| §0 | L14-21 | decision 3 记录 disposition；B5-E 门禁先于 B5-A；A/B/C/D 只读消费 typed keys、禁止写 locale/i18n；编号表示 ownership package 不表示执行先后 |
| §8 | §8.4 L305-458 完整 key inventory；§8.5 L460-477 记录 `MOVE_B5_E_BEFORE_B5_A` | §8.4 是完整且已批准的 inventory；B5-E 执行门禁先于 B5-A；缺 key 交独立 i18n Fixer/Review；执行顺序 B5-E → A → B → C → D |
| §9 | L498 | “B5-E 门禁先于 B5-A：§8.4 inventory 全量落盘、23 locale key parity、prefix、无 hardcoded user copy、i18n:check” |
| §10 | L616-622 | “本表 Merge order 即执行顺序：B5-E 门禁先于 B5-A（`MOVE_B5_E_BEFORE_B5_A`），随后 B5-A → B5-B → B5-C → B5-D”；B5-A/B/C/D 均不得写 locale/i18n 文件 |
| §12 | L655-657、L672-674 | 拓扑中 B5-E 排在 contract fast-forward 之后、B5-A 之前；“编号 B5-A..B5-E 表示 ownership package，不表示执行先后，实际执行顺序 B5-E → B5-A → B5-B → B5-C → B5-D” |
| §13 | §13.2 L775-778 | decision 3 复述 disposition；§13.3 L794-795 增加 stop condition（A/B/C/D 需修改 locale/i18n 或需 §8.4 外新 key 即停） |
| §15 | L871-874 | B5-E 门禁先于 B5-A 运行，全 23 locale 落盘 §8.4 inventory，独立 Reviewer 逐 locale 质量 Review，PASS+fast-forward 后 A/B/C/D 才开始 |
| §16 | L905-907 | checklist 记录 disposition：§8.4 是完整且已批准的 inventory；B5-E 门禁先于 B5-A；A/B/C/D 只读消费、禁写 locale/i18n；缺 key 走独立 i18n Fixer/Review |
| §17 | L932-934 | gate：contract PASS fast-forward 后“only then coordinator may authorize B5-E”；“B5-E fast-forwarded；then B5-A → B5-B → B5-C → B5-D” |

无残留旧顺序表述（`rg` 检查 `B5-A → ... → B5-E`、`最后.*B5-E` 等旧拓扑均为 0 匹配）。

### 4.2 §8.4 key inventory 独立计数

用只读脚本从 §8.4 两张表提取并计数：

| 指标 | expected | actual |
| --- | --- | --- |
| `platformAdmin.*` unique keys | 56 | 56 |
| `enterpriseMarketplace.*` unique keys | 83 | 83 |
| total unique | 139 | 139 |
| duplicates | 0 | 0 |
| 前缀正确性 | 全部前缀一致 | 全部 `platformAdmin.*` / `enterpriseMarketplace.*` 各自前缀正确，无 cross-namespace 行 |

§8.4 表内 139 个 key 全部是 B5-E 的“完整且已批准的 key inventory”；§8.1 明确“所有
key 位于 `common.json`，不新增 namespace 文件”。

### 4.3 B5-E 唯一 writer = 精确 23 个 locale `common.json`

- `web/i18n/` 恰 23 个目录；`web/i18n-config/languages.ts` 中 `supported: true` 恰 23 个。
- 23 个 `web/i18n/*/common.json` 全部存在、扁平、各 618 keys；当前均不含
  `platformAdmin`/`enterpriseMarketplace` key（`rg` 0 匹配），与 §8.1 新 key 断言一致。
- §8.3 allowlist、§10 ownership 矩阵、§12 B5-E allowlist 三处均精确列出同样 23 个
  `web/i18n/<locale>/common.json`，无目录通配、无省略、无重复、无额外 locale（脚本
  集合比较确认三个来源 == 实际 23 目录集合）。
- §10/§12/§11：B5-A/B/C/D 对任何 locale/i18n 文件写操作被 deny；B5-E 是唯一 writer
  和翻译质量 owner。

### 4.4 顺序、只读消费、质量 Review、缺 key 升级

- §0/§8.5/§12/§13.2/§15/§17：B5-E 必须在 23 locale 全量落盘 §8.4 inventory、通过
  23-locale `i18n:check`、正确本地化、非英文无英文占位，经独立 B5-E Reviewer /
  i18n Fixer / Rereviewer PASS 且 fast-forward 后，B5-A/B/C/D 才允许开始。
- B5-A/B/C/D 只读消费 §8.4 typed keys；§11、§13.3 明确禁止其写任何 locale/i18n 文件。
- 非英文 locale 禁英文占位/fallback 依赖（§0、§8.3、§8.5、§9、§12、§15、§16），翻译
  质量独立 Review 保持强制。
- 缺 key 升级：Builder 停止并交独立 i18n Fixer/Review 补充 inventory（必要时经
  finding-scoped Plan Fixer 修订 §8.4）与 23 个 locale 文件（§0、§8.5、§12、§13.2、
  §13.3），Builder 不得越权添加。
- 编号与执行顺序：§10 merge order（B5-E=1, A=2, B=3, C=4, D=5）与 §12、§17 串行
  执行顺序（B5-E → A → B → C → D）一致；“编号表示 ownership package，不表示执行
  先后”在所有相关小节一致表述。

## 5. B5PR-02 DISPOSITION — CLOSED

原 finding（Review `B5PR-02`）：“resubmit 流程存在前向依赖 / dialog 文件未分配”。
Fixer 以 `B5_C_OWNS_DEDICATED_RESUBMIT_DIALOG` disposition 关闭。独立证据如下：

### 5.1 文件所有权与依赖

| 文件 | §10 owner | §10 read-only dependency | §10 merge order | §12 allowlist |
| --- | --- | --- | --- | --- |
| `web/features/enterprise-marketplace/resubmit-marketplace-dialog.tsx` | B5-C（唯一） | generated submission mutation/current row_version | 4 | 含于 B5-C（§12 明确“含 `resubmit-marketplace-dialog.tsx`，不含 B5-D 的 `submit-marketplace-dialog.tsx`”） |
| `web/features/enterprise-marketplace/resubmit-action.tsx` | B5-C | **B5-C resubmit-marketplace-dialog**（无任何 B5-D 文件） | 4 | 含于 B5-C |
| `web/features/enterprise-marketplace/submit-marketplace-dialog.tsx` | B5-D（首次提交 only） | generated submit mutation（首次提交） | 5 | B5-D 4 文件之一 |
| `web/app/components/apps/app-card.tsx` | B5-D | B5-D submit-marketplace-dialog（首次提交） | 5 | B5-D |

- §5：`ResubmitMarketplaceDialog` 显式出现在 submissions 组件矩阵；“resubmit 走 B5-C
  专用 dialog，不经 app-card”。
- §10 L619-620：`submit-marketplace-dialog.tsx` 与 `resubmit-marketplace-dialog.tsx`
  互不 import。
- §10 L620-621 / §11 L640-641：B5-C 不得写 `submit-marketplace-dialog.tsx` 或
  `app-card.tsx`；B5-D 不得写任何 `resubmit-*` 文件。
- §13.3 L796-798：stop condition 覆盖“B5-C 依赖 B5-D 文件”、“B5-D 写任何
  `resubmit-*` 文件”、“两个 Builder 文件所有权重叠（含 submit/resubmit dialog 越界
  写）”。

### 5.2 独立 ownership 计数

只读脚本解析 §10 ownership 矩阵：

| Builder | expected | actual |
| --- | --- | --- |
| B5-A | 8 | 8 |
| B5-B | 15 | 15 |
| B5-C | 23 | 23（含 `resubmit-marketplace-dialog.tsx`） |
| B5-D | 4 | 4 |
| B5-E | 23 | 23（locale `common.json`） |
| 跨 owner 重复文件 | 0 | 0 |

### 5.3 409 行为与共享 invalidation

- 409 `stale_asset_version`：保留 draft、invalidate/refetch 当前 row、显示“数据已变更”
  conflict、禁止自动重放 mutation（§3.1 L135-136、§5 L200、§7 L240、§9 L494、§13.2
  L781-782、§16 L908-910）。按 plan §9（L493-496），409 保留 draft/invalidate/refetch/
  conflict/禁止自动重放 由 B5-C submissions + resubmit-marketplace-dialog specs 覆盖
  （L494），stale conflict refetch 不自动重放由 review/resubmit/submissions specs 覆盖
  （L496）；B5-D 行（L493）只覆盖首次提交 version 省略与成功后 invalidate submissions，
  未把 stale 409 行为指派给 B5-D first-submit specs。
- 共享 submission mutation invalidation：唯一 writer = B5-A `web/service/client.ts`
  （§7 L245-246、§10 L617-619），component callbacks 只处理 close/toast/result/
  navigation，不重复 shared invalidation。

## 6. NO_REGRESSION

- **拓扑/顺序**：§12 与 §17 均为
  `contract-owner Fixer → Contract Reviewer → (Fixer?/Rereviewer) → contract PASS
  fast-forward → B5-E → B5-A → B5-B → B5-C → B5-D → 各阶段 Reviewer/Fixer?/Rereviewer
  → full regression/browser gate → Final Reviewer/Fixer?/Final Rereviewer`。无残留旧
  顺序（`rg` 0 匹配）。§10 merge order 与 §12/§17 一致。
- **allowlist/denylist**：B5-A/B/C/D/E allowlist 全部为 exact files，无目录通配；
  §11 denylist 覆盖 `api/**`、`api/migrations/**`、`docker/**`、`docker/volumes/**`、
  `dify-agent/**`、`packages/contracts/**`、`packages/contracts/generated/**`、
  `packages/dify-ui/**`、`packages/iconify-collections/**`、lockfile/依赖/版本文件、
  旧 enterprise service/model、旧 app context/legacy loader、direct fetch、手写
  Console response/error types、§8.3 之外 locale/i18n 文件、A/B/C/D 对 locale/i18n
  写操作、B5-D 写 `resubmit-*`、B5-C 写 `submit-marketplace-dialog.tsx`、真实
  env/secret/DB/Redis/vector/container/volume 写操作。
- **CONTRACT_FIX_REQUIRED 仍为真实未解决前置**（非 relabeled fixed）：
  - `platform-admin/types.gen.ts` 中 B3 7 条 operation 只有 `*Responses`（6 条
    workspaces `*Responses` 计数 + status 在 account），0 条 `*Errors`；全文件仅 3 个
    `*Errors` 类型，均为 B4 admin marketplace operation。
  - `account/types.gen.ts` 无任何 `*Errors` 类型。
  - `PlatformAdminErrorResponse` 在 `api/controllers/console/platform_admin.py:169`
    注册，但 generated 文件中 `rg` 无匹配（未生成）。
  - review route（`enterprise_marketplace.py` `MarketplaceReviewApi.post`）只注册
    400/401/403/404/409，无 `_err_response(422)`；`approve_asset` 经
    `_validate_dsl_no_secrets` / `_extract_and_normalize_dependencies` /
    `_validate_app_metadata` 可抛出 `SnapshotContainsSecret`、`NonportableResourceReference`、
    `PrivatePluginDependency`（`api/services/errors/enterprise_marketplace.py:83-95`
    status_code=422），generated `PostPlatformAdminEnterpriseMarketplaceAssetsByAssetIdReviewsErrors`
    缺 422。
  - §0/§3.2/§12/§13.2/§16/§17 保持该阻断，且明确 B5 不修改 API/generated files、
    不手写 error types、不 direct fetch、不把 contract 修复委托给 B5 Builder。
- **无 frontend workaround**：计划禁止 direct fetch、手写 DTO/error type、legacy
  loader、前端 workaround（§0、§2.3、§3.2、§11、§13.3、§15、§16）。
- **无 contract 再生/无越界扩展**：§15/§16 明确不得运行 `gen-api-contract` 作为 B5
  validation；denylist 覆盖 contracts 与 API/Docker/migration；无 API/Docker/migration
  范围扩大。
- **无提前授权**：§0/§8.3/§12/§17 明确 i18n recorded decision 本身不授权 B5-E；
  contract PASS fast-forward 前整个 B5 链不启动；“only then coordinator may authorize
  B5-E”。
- **`BLOCKED_PENDING_CONTRACT_FIX`**：§0 L5、§13.2 L772、§17 L940 保持显式。
- **`B5_BUILDER_NOT_AUTHORIZED`**：§17 L942 保持显式。
- **B4 accepted known limitations 保留**：§1.2 L57-59 保留 official import internal
  commit 与未来 DSL 字段风险为 `ACCEPTED_KNOWN_LIMITATION`；§13.1 保留 copy 201 后
  import 内部 commit、warnings 展示、不承诺撤销。
- **NOT_RUN 诚实**：§14 记录 frontend Vitest / type-check / `pnpm check` /
  browser/E2E / contract generation / backend tests / database/migration / vector /
  Docker/runtime / offline / volume-upgrade 全部 NOT_RUN，且“源码检查不能替代 browser
  behavior；B4 398/398 不能替代 B5 tests”。

## 7. NEW_FINDINGS

无。未发现新的 P0/P1/P2 finding。Fixer diff 严格限定在计划文档 i18n 顺序、
resubmit dialog ownership、allowlist/denylist/stop-condition/gate 一致性修订，未触及
contract、API、frontend 实现或 denylist 范围外内容。

## 8. COMMANDS

| Command | exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b5-plan-rereviewer` |
| `git rev-parse HEAD` | 0 | `325fb52608890dcfafab72f2dbb3f40069f02f80` |
| `git status --short --branch` | 0 | `## ctyun/replay-116-b5-plan-rereviewer`（无修改） |
| `git status --porcelain=v1` | 0 | 空 |
| `git rev-parse HEAD^` | 0 | `dfa98c711aee15226e3eabd3b2320d3557aa8e2c` |
| `git merge-base --is-ancestor 9c4c0356f3f2374c22b383ba96331e1dd92505fd HEAD` | 0 | ancestor=true |
| `verify_git_start.sh "$(pwd)" ctyun/replay-116-b5-plan-rereviewer 325fb52608890dcfafab72f2dbb3f40069f02f80` | 0 | `OK branch=... head=... clean=true` |
| `git diff --name-status dfa98c711..325fb52608` | 0 | `M docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`（仅此 1 文件） |
| `git diff --stat dfa98c711..325fb52608` | 0 | `1 file changed, 346 insertions(+), 106 deletions(-)` |
| `git diff --numstat dfa98c711..325fb52608` | 0 | `346 106 docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` |
| `git diff --check dfa98c711..325fb52608` | 0 | clean |
| `git diff --check`（working tree） | 0 | clean |
| `git diff dfa98c711..325fb52608 -- B5_IMPLEMENTATION_PLAN_REVIEW.md` | 0 | 空输出（Review 报告未被修改） |
| `rg -n '[ \t]+$' docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REREVIEW.md` | 1 | 无尾随空白匹配（exit 1 = 0 matches）；本报告为 untracked 文件，`git diff --check` 不覆盖 untracked 文件，故以 `rg` 显式检查报告自身 |
| §8.4 key inventory 只读脚本 | 0 | platformAdmin=56, enterpriseMarketplace=83, total=139, unique=139, duplicates=0 |
| §8.3/§10/§12 locale 集合比较脚本 | 0 | 三处均 == 实际 23 目录，无重复/缺失/额外 |
| §10 ownership 解析脚本 | 0 | A=8, B=15, C=23, D=4, E=23；跨 owner 重复 0 |
| `rg -c 'supported: true' web/i18n-config/languages.ts` | 0 | 23 |
| `rg -n 'platformAdmin|enterpriseMarketplace' web/i18n/en-US/common.json` | 1 | 无匹配（新 key 尚不存在，符合计划） |
| `rg -n '^export type.*Errors' .../platform-admin/types.gen.ts` | 0 | 仅 3 个（B4 admin marketplace），B3 0 个 |
| `rg -n '^export type.*Errors' .../account/types.gen.ts` | 1 | 0 个 |
| `rg -rn 'PlatformAdminErrorResponse' packages/contracts/generated/` | 1 | NOT GENERATED |
| review route 422 检查（`rg '_err_response' enterprise_marketplace.py`） | 0 | review route 无 422 注册；仅 copy route 有 422 |
| `rg -n 'BLOCKED_PENDING_CONTRACT_FIX' B5_IMPLEMENTATION_PLAN.md` | 0 | 3 处（§0/§13.2/§17） |
| `rg -n 'B5_BUILDER_NOT_AUTHORIZED' B5_IMPLEMENTATION_PLAN.md` | 0 | §17 显式 |
| `rg -n 'MOVE_B5_E_BEFORE_B5_A' B5_IMPLEMENTATION_PLAN.md` | 0 | §0/§8.5/§10/§12/§13.2/§16/§17 |
| 旧顺序残留检查（`rg 'B5-A → ... → B5-E|最后.*B5-E|merge order.*5.*B5-E'`） | 1 | 0 匹配 |

## 9. NOT_RUN

以下验证未在本 plan-only rereview 中执行（源码/契约只读核验不替代它们）：

- frontend focused Vitest：NOT_RUN
- web type-check：NOT_RUN
- `pnpm check`：NOT_RUN
- browser/E2E：NOT_RUN
- contract generation：NOT_RUN（B5 亦被计划禁止运行；B4 生成物仅只读核验，未重新生成）
- backend/API tests：NOT_RUN
- database/migration：NOT_RUN
- vector：NOT_RUN
- Docker/runtime：NOT_RUN
- offline：NOT_RUN
- volume/upgrade/rollback：NOT_RUN

## 10. GIT

- exact modified files：仅 `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`（Fixer range 内）；本报告为未跟踪新文件
- `git diff --check`：clean（range 与 working tree）
- `git status --short --branch`：`## ctyun/replay-116-b5-plan-rereviewer` + untracked 本报告
- `git status --porcelain=v1`：`?? docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REREVIEW.md`
- commit：**NOT_COMMITTED**
- amend：**NOT_AMENDED**
- push：**NO_PUSH**

## 11. VERDICT

**PASS**

- PLAN_ACCEPTED: **yes**
- B5PR-01: **CLOSED**（§8.4 完整 inventory 56/83/139/0；B5-E 先于 B5-A；23-locale
  唯一 writer；A/B/C/D 只读消费；缺 key 独立 i18n Fixer/Review；§0/8/9/10/12/13/15/16/17
  一致）
- B5PR-02: **CLOSED**（`resubmit-marketplace-dialog.tsx` 唯一 owner=B5-C 且入 B5-C
  allowlist；`resubmit-action.tsx` 只依赖 B5-C dialog；B5-D 仅首次提交；cross-write
  禁止；两 dialog 互不 import；ownership A=8/B=15/C=23/D=4/E=23；409 行为与
  client.ts 单 writer 保持）
- **BLOCKED_PENDING_CONTRACT_FIX**: 保留（B3 platform-admin/status typed error
  unions 与 B4 review reachable 422 仍为真实未解决前置，未 relabeled fixed）
- **B5_BUILDER_NOT_AUTHORIZED**: 保留

说明：

1. Fixer diff 严格限于计划文档，只改动 `B5_IMPLEMENTATION_PLAN.md`（346/106），Review
   报告未修改，无 denylist 越界、无 contract/API/frontend 改动。
2. 两个 P1 finding 均由本 Rereview 以 repo 只读证据独立验证关闭；计划整体
   contract 事实、locale 清单、唯一 writer/allowlist、拓扑顺序一致，质量高。
3. Plan PASS 仅接受 B5 计划本身；contract 修复仍未完成、仍阻断，且不构成任何 B5
   Builder 授权。协调者检查与人工授权是独立后续门禁。

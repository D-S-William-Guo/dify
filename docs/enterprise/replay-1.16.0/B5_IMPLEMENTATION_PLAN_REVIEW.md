# Dify Enterprise 1.16.0 Replay B5 Implementation Plan — Independent Plan Review

- **Role**: Independent B5 Plan Reviewer
- **Branch**: `ctyun/replay-116-b5-plan-reviewer`
- **HEAD**: `d5b365093ef7272b3cbb36a4ac16ba595f96f2ca`
- **Plan parent**: `57b3937e5f7a091fbed646578d1ffbb69aa2f06b`
- **B4 product checkpoint**: `9c4c0356f3f2374c22b383ba96331e1dd92505fd`
- **Reviewed artifact**: `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`
- **结论**: `CHANGES_REQUIRED`

本报告是独立 Review 证据，不是 Architect 计划的改写。本 Reviewer 未修改计划、
API、contracts、frontend 或任何 denylist 文件。

---

## RECOVERY

- expected branch: `ctyun/replay-116-b5-plan-reviewer`
- actual branch: `ctyun/replay-116-b5-plan-reviewer` — PASS
- expected HEAD: `d5b365093ef7272b3cbb36a4ac16ba595f96f2ca`
- actual HEAD: `d5b365093ef7272b3cbb36a4ac16ba595f96f2ca` — PASS
- clean: `true`（porcelain 无输出；`verify_git_start.sh` 输出 `OK ... clean=true`）
- B4 checkpoint ancestor: `true`（`git merge-base --is-ancestor 9c4c0356f3f2374c22b383ba96331e1dd92505fd HEAD` 退出 0）

未执行 merge、rebase、reset、checkout、cherry-pick、commit、amend、push。

## REVIEW_RANGE

- parent: `57b3937e5f7a091fbed646578d1ffbb69aa2f06b`
- reviewed commit: `d5b365093ef7272b3cbb36a4ac16ba595f96f2ca`
- exact changed files:
  - `A  docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`（702 insertions）
- `git diff --check`（parent..reviewed 与 working tree）均 clean。

## SOURCES_READ

- `docs/enterprise/replay-1.16.0/CURRENT_STATE.md`
- `docs/enterprise/replay-1.16.0/B4_FINAL_REREVIEW.md`
- `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md`（逐行）
- `docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md`
- `docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md`
- `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md`
- `docs/enterprise/replay-1.16.0/B4_IMPLEMENTATION_PLAN.md`
- `web/AGENTS.md`
- `web/docs/test.md`
- `web/docs/lint.md`
- `web/docs/overlay.md`
- `packages/dify-ui/README.md`
- `packages/dify-ui/AGENTS.md`
- `web/service/client.ts`（`experimental_defaults` 模式）
- `web/i18n-config/resources.ts`、`web/i18n-config/settings.ts`、`web/types/i18n.d.ts`、`web/scripts/check-i18n.js`
- 生成 contracts：`packages/contracts/generated/api/console/{account,platform-admin,enterprise-marketplace,apps}/{orpc,types,zod}.gen.ts`、`router.gen.ts`
- 后端证据：`api/controllers/console/platform_admin.py`、`api/controllers/console/enterprise_marketplace.py`、`api/libs/platform_admin.py`、`api/services/errors/enterprise_marketplace.py`、`api/services/enterprise_marketplace_service.py`
- 当前 frontend：`web/app/components/main-nav/routes.ts|index.tsx|__tests__/*`、`web/context/{account-state,workspace-state,permission-state}.ts`、`web/app/components/apps/app-card.tsx|__tests__/app-card.spec.tsx`、`web/app/components/explore/{app-list,app-card,sidebar}`、`web/app/components/header/account-setting/members-page/**`、`web/features/`（当前目录）、`web/app/(commonLayout)/` 路由结构、`.vite-hooks/pre-commit`、`web/package.json`、根 `package.json`
- `web/i18n/<23 locales>/common.json`（逐文件 JSON 解析）

## INDEPENDENT_EVIDENCE

以下均来自 repository/generated files 的独立核验，不是 Architect 声明。

### 15-contract verification — 15/15 对象路径真实，input/success/errors/invalidation 基本准确

逐条从 `orpc.gen.ts`/`types.gen.ts` 验证：

| # | 路径 | 实测 | 计划声称 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | `account.platformAdminStatus.get`（`/account/platform-admin-status`，account/orpc.gen.ts:336-343） | 存在；success `PlatformAdminStatusResponse{is_platform_admin,mutation_supported}`（account/types.gen.ts:128-131）；无 `*Errors` | 一致 | ✓ |
| 2 | `platformAdmin.workspaces.get`（`/platform-admin/workspaces`，platform-admin/orpc.gen.ts:195） | query `{keyword,limit,page,status:'all'|'archive'|'normal'}`（types.gen.ts:226-233）；仅 `*Responses` | 一致 | ✓ |
| 3 | `platformAdmin.workspaces.byWorkspaceId.get`（orpc.gen.ts:162） | params workspace_id；无 errors | 一致 | ✓ |
| 4 | `platformAdmin.workspaces.byWorkspaceId.patch`（orpc.gen.ts:173） | body `{name}`（`PlatformAdminWorkspaceRenamePayload`）；无 errors | 一致 | ✓ |
| 5 | `platformAdmin.workspaces.byWorkspaceId.members.get`（orpc.gen.ts:145） | `PlatformAdminMemberListResponse{items,mutation_supported}`（types.gen.ts:78-80）；无 errors | 一致 | ✓ |
| 6 | `platformAdmin.workspaces.byWorkspaceId.members.invitations.post`（orpc.gen.ts:100，successStatus 201） | 逐邮箱 `action`/`email_delivery`（types.gen.ts:130-138）；无 errors | 一致 | ✓ |
| 7 | `platformAdmin.workspaces.byWorkspaceId.members.byMemberId.role.patch`（orpc.gen.ts:121） | body `{role}`；response `{result,workspace_id,member_id}`；无 errors | 一致 | ✓ |
| 8 | `apps.byAppId.enterpriseMarketplace.submissions.post`（apps/orpc.gen.ts:2100-2123，path `/apps/{app_id}/enterprise-marketplace/submissions`） | errors 400/401/403/404/409（apps/types.gen.ts:4756-4762）；201 `MarketplaceAssetResponse` | 一致 | ✓ |
| 9 | `enterpriseMarketplace.submissions.get`（orpc.gen.ts:74） | errors 400 Marketplace / 401 Unauthorized（types.gen.ts:225-231） | 一致 | ✓ |
| 10 | `enterpriseMarketplace.assets.get`（orpc.gen.ts:58） | query page/limit/keyword/category/sort（types.gen.ts:134-140）；errors 400/401 | 一致 | ✓ |
| 11 | `enterpriseMarketplace.assets.byAssetId.get`（orpc.gen.ts:42） | errors 401/404 | 一致 | ✓ |
| 12 | `enterpriseMarketplace.assets.byAssetId.copies.post`（orpc.gen.ts:21，successStatus 201） | body 空 `MarketplaceCopyPayload`（types.gen.ts:57-59）；201 `{app_id,content_sha256,import_status,snapshot_version,warnings}`（types.gen.ts:61-67）；errors 400/401/403/404/409/422/503（types.gen.ts:192-200） | 一致 | ✓ |
| 13 | `platformAdmin.enterpriseMarketplace.assets.get`（orpc.gen.ts:80） | query 含 `status[]/publication_status[]/snapshot_state[]`（types.gen.ts:143-152）；errors 400/401/403，**无 409**（types.gen.ts:156-160） | 一致 | ✓ |
| 14 | `platformAdmin.enterpriseMarketplace.assets.byAssetId.reviews.post`（orpc.gen.ts:35） | errors 400/401/403/404/409，**无 422**（types.gen.ts:181-187）；200 `MarketplaceAssetResponse`（含 row_version） | 一致 | ✓ |
| 15 | `platformAdmin.enterpriseMarketplace.assets.byAssetId.unlist.post`（orpc.gen.ts:55） | errors 400/401/403/404/409（types.gen.ts:208-214） | 一致 | ✓ |

计划 §3 的 request/success/error/invalidation/redirect 描述与 generated files 逐条吻合，无 route-name 猜测、无旧 API shape 假设。

### B3 typed-error verification — 缺失确认

- `platform-admin/types.gen.ts:238-324`：7 条 B3 operation 只有 `*Responses`，无 `*Errors`（0/7）。
- `account/types.gen.ts:434-439`：`GetAccountPlatformAdminStatusResponses` 存在，无 `*Errors`。
- `PlatformAdminErrorResponse` 只在 `api/controllers/console/platform_admin.py:169` 注册，generated 文件中 `rg` 无匹配（未生成）。
- 同文件 3 条 B4 admin marketplace operation 有 typed errors（types.gen.ts:156/181/208），证明生成链支持 typed error union。
- `api/controllers/console/platform_admin.py` 7 条 B3 route（含 status route）均无 `_err_response` decorator；`api/libs/platform_admin.py:83-95` 的 `platform_admin_current_tenant_required` 对全部 admin route 均可抛 409 `current_tenant_required`（实际可达，contract 未含）。
- **结论**：计划 §3.2 "B3 platform-admin/status typed error unions 缺失" 证据真实。

### B4 review-422 verification — reachable 422 缺失确认

- `api/controllers/console/enterprise_marketplace.py:565-601`：review route 只注册 400/401/403/404/409，**无 `_err_response(422)`**。
- `api/services/enterprise_marketplace_service.py:215` `approve_asset` 在 `_validate_dsl_no_secrets`/`_validate_app_metadata`/dependency 校验路径上可抛 `SnapshotContainsSecret`、`NonportableResourceReference`、`PrivatePluginDependency`（`api/services/errors/enterprise_marketplace.py:82-95`，status_code=422）。
- generated `PostPlatformAdminEnterpriseMarketplaceAssetsByAssetIdReviewsErrors`（platform-admin/types.gen.ts:181-187）缺 422。
- **结论**：计划 §3.2 "B4 marketplace review reachable 422 未生成" 证据真实。
- 计划 §3.2/§13.2/§17 明确禁止手写 error type、direct fetch 或其他前端 workaround；contract Fixer repair boundary（补 B3 unions + review 422，重新生成，独立 Reviewer/Rereviewer，fast-forward 后记录 SHA）足够精确。未发现计划把修复委托给 B5 Builder 或绕过 generated contracts。

### Official frontend reuse — 真实，非旧架构

- `web/app/components/main-nav/routes.ts`、`index.tsx`、`__tests__/index.spec.tsx` 存在；route visibility 模型（`MainNavRouteVisibility`/`isMainNavRouteVisible`）与计划 §4 的 main-nav 改造目标吻合。
- `web/context/{account-state,workspace-state,permission-state}.ts` 存在；`permission-state.ts` 已用 `atomWithQuery`（jotai-tanstack-query）模式，计划 §6 的 feature query atom + derived atom 与本仓库一致。
- `web/service/client.ts` 已用 `createTanstackQueryUtils(consoleClient, { experimental_defaults: {...mutationOptions:{onSuccess...}} })`；计划 §7 "shared invalidation 唯一 writer=client.ts" 与本仓库模式一致。
- `web/app/components/apps/app-card.tsx` 存在 `AppCardOperationsMenu`（app-card.tsx:169）；`__tests__/app-card.spec.tsx` 存在。
- `web/app/components/explore/{app-list,app-card,sidebar}` 与 `account-setting/members-page/{invite-modal,member-menu,member-row,role-badges}` 存在，可作只读模式来源。
- `nuqs`（`useQueryState`）与 `keepPreviousData` 在 explore/deployments/agent-v2 当前实现中实际使用。
- 计划 §2.3 disposition 与 `PATCH_DECISION_MATRIX.md` 一致：E05/C11 → REIMPLEMENT_ON_NEW_ARCH（矩阵 E05/C11 KEEP_REQUIREMENT_REIMPLEMENT）；C07 → DROP_UPSTREAMED（矩阵 C07 DROP_UPSTREAMED）；旧 `web/service/use-enterprise-marketplace.ts`/`web/models/enterprise-marketplace.ts` 当前不存在且计划禁止恢复。未发现 cherry-pick 或旧 1.15 API shape 假设。

### Builder ownership — allowlist 精确，唯一 writer 清晰（一处拓扑缺陷见 FINDINGS）

- B5-A 8 个文件、B5-B 15 个文件、B5-C 22 个文件、B5-D 4 个文件、B5-E 23 个文件；逐一与 §10 矩阵计数吻合（B5-B 15、B5-C 22 核对无误）。
- new 文件均显式标注；existing reference 路径（main-nav/routes.ts、index.tsx、client.ts、app-card.tsx、i18n common.json）均真实存在。
- 共享文件唯一 writer：main-nav、client.ts、app-card、feature state、i18n 均唯一；account-setting/explore/context 在 B5 中 read-only（§10:419-421）。
- denylist（§11）覆盖 `api/**`、`api/migrations/**`、`docker/**`、`docker/volumes/**`、`dify-agent/**`、`packages/contracts/**`、`packages/contracts/generated/**`、`packages/dify-ui/**`、lockfile/依赖、旧 enterprise 文件、§8.3 之外 locale/i18n 文件。
- §12 与 §17 执行顺序一致（Plan Review → contract-owner Fixer → Contract Reviewer/Fixer/Rereviewer → contract fast-forward → B5-A→B5-B→B5-C→B5-D→B5-E → final gates）；B5 前全链阻断、contract 修复 fast-forward 前不得授权 B5-A。
- 延期功能（member DELETE、workspace create/delete/archive、owner mutation）未泄漏进 B5（§2.3 DEFER、§11 denylist、§4 mutation_supported fail-closed）。

### Locale inventory — 23 确认

- `web/i18n/` 恰 23 个目录；`web/i18n-config/languages.ts` 中 `supported: true` 恰 23 个。
- 23 个 `web/i18n/*/common.json` 均存在，均为扁平结构、各 618 keys；无 `platformAdmin`/`enterpriseMarketplace` 顶层 key（当前不存在，符合 §8.1 新增断言）。
- 计划 §8.3/§12/§10 B5-E 的 23 个 exact 文件与目录一一对应，无遗漏、重复、额外 locale 或目录通配。

### Command validity — 命令与当前仓库工具一致

- `pnpm --dir web i18n:check --file common --lang <23 locales>`：与 `web/scripts/check-i18n.js` 的 `--file`/`--lang` 空格分隔语法一致；脚本会校验 unsupported language（23 个均有效）；比较粒度为 common.json 扁平 key 全集（`common.<dotted key>`）。
- `pnpm --dir web type-check`：`web/package.json:37` `"type-check": "tsc"`。
- `pnpm check`：根 `package.json:6` `"check": "vp check && pnpm lint:eslint"`。
- `vp test run <dir>...`：`web/docs/test.md` 唯一测试命令来源；`web/package.json:34` `"test": "vp test"`。
- focused spec 路径：`app/components/main-nav/__tests__/index.spec.tsx`、`app/components/apps/__tests__/app-card.spec.tsx` 存在；`features/platform-admin`、`features/enterprise-marketplace` 为计划新增目录（当前 `web/features/` 只有 account-profile/agent-v2/deployments/system-features/tag-management）。
- 计划测试矩阵基于 observable behavior（loading/error/empty/retry/disabled/focus/navigation/copy 文案），不是 source-string/AST 断言。

## FINDINGS

### P0

无。

### P1

#### B5PR-01 — i18n key 引入顺序与 typed-i18n 门禁冲突（B5-A/B/C/D 无法通过 type-check/commit gate）

- **file/line**: `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` §8.1(242-247)、§8.3(280-285)、§9(311-319)、§10(395-417)、§12(449-460)。
- **evidence**:
  - `web/types/i18n.d.ts:6-12`：`CustomTypeOptions.resources = Resources`、`enableSelector: 'optimize'`、`keySeparator: false`。`web/i18n-config/resources.ts:48/136`：`common: typeof common`，`Resources` 由 `web/i18n/en-US/common.json` 的 type 派生。
  - `web/i18n/en-US/common.json` 为扁平 key map（618 keys），当前**不含** `platformAdmin`/`enterpriseMarketplace` key（json 解析确认）。
  - 现有用法 `t(($) => $[route.labelKey])`（main-nav/index.tsx:55）依赖 `MAIN_NAV_ROUTES` `as const` 字面量 union 才能通过类型；新增 `platformAdmin.*`/`enterpriseMarketplace.*` labelKey 字面量在 key 不存在时，selector 访问会触发 TS 错误（`vp check` 启用 `typeAware`+`typeCheck`，见 `web/docs/lint.md:47-55`）。
  - `.vite-hooks/pre-commit:64` 对任何 `web/*` 提交运行 `vp staged`（→ `vp check --fix`，含 TS diagnostics）；`web/AGENTS.md` 与计划 §5/§8.1 禁止 hardcoded 用户文案。
  - 计划 §8.3/§12/§10：`en-US/common.json`（及全部 23 个）是 **B5-E 唯一 writer**，且 B5-E 排在串行链最后；§11 denylist 禁止其他 Builder 写任何 i18n 文件；§9/§15 要求 Builder/最终 Reviewer 运行 `pnpm --dir web type-check` 与 `pnpm check`。
- **violated invariant**: 串行链中每个 Builder 的 gate 必须在其自身 allowlist 内可达成；i18n key 的引入必须早于其消费代码的 type-check/commit gate。B5-A 的 main-nav 改造、B5-B/C/D 的页面均必须消费 `platformAdmin.*`/`enterpriseMarketplace.*` key，但唯一可写这些 key 的 Builder 排最后。
- **impact**: B5-A/B/C/D 无法在不违反 §8.3/§11 allowlist（预写 en-US keys）或 web/AGENTS.md（hardcoded 文案）的前提下通过 `vp check`/`vp staged`/`type-check`。Builder 将被 §11/§13.3 强制停止，或产生未登记/违规 diff。计划未定义 "approved namespace/key set"（§10 B5-E 行）这一产物的具体 artifact 与其引入顺序。
- **required disposition**: 在计划中明确 i18n key 引入顺序。建议：在 B5-A 之前由一个独立小步骤（或 B5-A 前置）将**已批准的 `platformAdmin.*` / `enterpriseMarketplace.*` key 骨架**预置进 `web/i18n/en-US/common.json`（仅 en-US；其余 22 个 locale 的本地化仍由 B5-E 负责并受 i18n:check parity + 独立 Reviewer 门禁），或调整 B5-E 顺序，或显式放宽 B5-A/B/C/D 阶段的门禁定义。
- **smallest repair boundary**: 仅修改 `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` §8/§9/§10/§12 中关于 i18n key 引入顺序与各 Builder type-check 门禁的描述；不改 contract、API、frontend 实现。

#### B5PR-02 — resubmit 流程存在前向依赖 / dialog 文件未分配

- **file/line**: `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` §5(185)、§10(383、393)、§12(453-456)。
- **evidence**:
  - §5(185)：submissions 的 overlay owner 为 "resubmit dialog owns form draft/version"。
  - §10(383)：`web/features/enterprise-marketplace/resubmit-action.tsx` owner=B5-C，read-only dependency="submit dialog"，merge order 3。
  - §10(393)：`web/features/enterprise-marketplace/submit-marketplace-dialog.tsx` owner=B5-D，merge order 4。
  - §12(453-456)：串行顺序 B5-C → B5-D。
  - §9(303)：resubmit 行为（`resubmit includes current expected_row_version`）在 B5-C 的 `submissions` spec 中验证。
  - 全矩阵/allowlist 中不存在 `resubmit-dialog.tsx` 文件。
- **violated invariant**: Builder 只能依赖已 fast-forward 合并的前序产物；串行拓扑中不得存在前向依赖；每个组件文件必须有唯一 owner 且必须在某 Builder allowlist 中。
- **impact**: B5-C 的 `resubmit-action.tsx` 若复用 B5-D 的 `SubmitMarketplaceDialog` 则构成前向依赖（B5-C 先于 B5-D 合并，无法引用）；若自含 dialog，则计划 §5 声称的 "resubmit dialog" 无对应文件，且可能与 B5-D 的 submit dialog 重复。两种读法都使 B5-C 无法按 allowlist 独立完成其 submissions/resubmit 交付，Builder 将被迫停止上报或产生未登记文件。
- **required disposition**: 明确 resubmit dialog 的 owner 与顺序：把 resubmit 流程（含 dialog）并入 B5-D，或把 `resubmit-dialog.tsx` 显式登记进 B5-C allowlist 且不依赖 B5-D 文件。
- **smallest repair boundary**: 仅修改 `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` §5/§10/§12 中 resubmit 的 owner、依赖与顺序描述。

### P2

无。

## RECORDED_DECISIONS

- **CONTRACT_FIX_REQUIRED**: 计划准确、完整、一致地落实该决定（§0:9-11、§3.2:140-150、§13.2:554-557、§17:691-696）。B3 typed-error 缺失与 B4 review 422 缺失均由本 Review 独立证实；计划明确禁止任何前端 workaround，repair 由独立 contract-owner Fixer 执行且 fast-forward 前 B5 全链阻断。无静默改为方案 A 的迹象。
- **I18N_OPTION_B_APPROVED**: 计划准确落实 23 个 supported locale 的 `common.json` allowlist、B5-E 唯一 writer 与翻译质量 owner、非英文 locale 禁英文占位、独立 Reviewer/Fixer/Rereviewer 门禁（§8.2:250-278、§8.3:280-285、§12:458-459）。但该决定与 typed-i18n 门禁的执行顺序存在缺陷（见 B5PR-01）；这是决定落实方式的缺陷，不是对决定本身的挑战，且未改回方案 A。

## NOT_RUN

- frontend focused Vitest: **NOT_RUN**
- web type-check: **NOT_RUN**
- pnpm check: **NOT_RUN**
- browser/E2E: **NOT_RUN**
- contract generation: **NOT_RUN**（计划本身也禁止 B5 运行；B4 已生成物只读核验，未重新生成）
- backend/API tests: **NOT_RUN**
- database/migration: **NOT_RUN**
- vector: **NOT_RUN**
- Docker/runtime: **NOT_RUN**
- offline: **NOT_RUN**
- volume/upgrade/rollback: **NOT_RUN**

以上均未以源码审查、B4 398/398 或 Architect 声明替代。本 Review 只做只读源码/契约/路径核验。

## GIT

- exact modified files: 仅新增 `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REVIEW.md`（本报告；未跟踪）
- git diff --check: clean（parent..reviewed 与 working tree）
- git status --short --branch: `## ctyun/replay-116-b5-plan-reviewer` + untracked 本报告文件
- git status --porcelain=v1: `?? docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REVIEW.md`
- commit: **NOT_COMMITTED**
- amend: **NOT_AMENDED**
- push: **NO_PUSH**

## VERDICT

- **CHANGES_REQUIRED**（存在 2 个 P1 finding：B5PR-01、B5PR-02）
- PLAN_ACCEPTED: **no**（pending findings disposition）
- B5_PHASE_GATE: **BLOCKED_PENDING_CONTRACT_FIX**（plan 自身结论成立；与 findings 相互独立）
- B5_BUILDER_NOT_AUTHORIZED: **yes**

说明：

1. 本 Review 对计划 §3 contract 事实、§3.2 阻断证据、locale 清单、唯一 writer/allowlist、§12/§17 顺序一致性均独立确认，整体质量高。
2. `CHANGES_REQUIRED` 仅针对 B5PR-01（i18n key 引入顺序 vs typed-i18n/commit 门禁）与 B5PR-02（resubmit 前向依赖/未分配文件）两个计划层缺陷；repair boundary 见上，均由独立 Fixer 在 `B5_IMPLEMENTATION_PLAN.md` 内修复，本 Reviewer 未修改计划。
3. Plan PASS 不等于 contract 已修复，也不等于任何 B5 Builder 获授权。

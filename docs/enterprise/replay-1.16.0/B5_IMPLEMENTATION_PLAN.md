# Dify Enterprise 1.16.0 Replay B5 前端实施计划

## 0. 结论

当前结论：**BLOCKED_PENDING_CONTRACT_FIX**。

本文件是可独立 Review 的实施计划，不是 Builder 授权。协调者已记录以下决定：

1. `CONTRACT_FIX_REQUIRED`：B3 的 platform-admin/status typed error unions 和 B4
   marketplace review reachable 422 必须由独立 contract-owner Fixer 修复，并由独立
   Reviewer 验证；修复完成前 B5 保持阻断。
2. `I18N_OPTION_B_APPROVED`：B5 i18n allowlist 扩大到全部 23 个 supported locale 的
   `common.json`；B5-E 是唯一 writer 和翻译质量 owner，且完成后必须独立 Review。
3. `MOVE_B5_E_BEFORE_B5_A`（I18N_EXECUTION_ORDER，B5PR-01 disposition）：B5-E 的执行
   门禁移到 B5-A 之前。B5-E 先创建完整且已批准的 `platformAdmin.*` /
   `enterpriseMarketplace.*` key inventory（§8.4），完成全部 23 个 supported locale
   parity、正确本地化、非英文无英文占位和 `i18n:check`，经独立 B5-E Reviewer /
   i18n Fixer? / Rereviewer PASS 且 fast-forward 后，B5-A/B/C/D 才只读消费 typed
   keys。B5-A/B/C/D 一律禁止修改 locale/i18n 文件。后续 Builder 若发现缺 key，必须
   停止并交独立 i18n Fixer/Review，不得越权添加。编号 B5-A..B5-E 表示 ownership
   package，不表示执行先后。
4. `B5_C_OWNS_DEDICATED_RESUBMIT_DIALOG`（B5PR-02 disposition）：新增计划文件项
   `web/features/enterprise-marketplace/resubmit-marketplace-dialog.tsx`，唯一
   owner=B5-C；`resubmit-action.tsx` 只依赖该 B5-C dialog，不依赖 B5-D 的
   `submit-marketplace-dialog.tsx`。B5-D 继续负责 app-card 首次提交入口、首次提交
   dialog 和 focused tests。409 必须保留 draft、invalidate/refetch、显示 conflict，
   禁止自动重放 mutation。

当前唯一未关闭的前置阻断是 contract 修复。B5 不修改 API 或 generated contracts，
不使用临时 fetch、手写 DTO/error type 或其他前端 workaround；B5-E 不得向非英文
locale 复制英文占位；B5-A/B/C/D 不得向任何 locale/i18n 文件预写或改写 key。

contract 修复经独立 Review、计划经独立 Plan Review 且协调者另行授权后，B5 才可按
本文 §12 的严格串行拓扑执行（contract PASS 后先 B5-E 全 23-locale foundation，再
B5-A → B5-B → B5-C → B5-D）。任何 Builder 仍须从“包含已接受计划、已接受 contract
修复和本文件记录决定”的新 40 位精确 SHA 开始。

## 1. Current-state recovery

### 1.1 强制起点

| 项目 | expected | actual | 结果 |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b5-architect` | `ctyun/replay-116-b5-architect` | PASS |
| HEAD | `57b3937e5f7a091fbed646578d1ffbb69aa2f06b` | `57b3937e5f7a091fbed646578d1ffbb69aa2f06b` | PASS |
| porcelain | empty | empty | PASS |
| B4 ancestor | `9c4c0356f3f2374c22b383ba96331e1dd92505fd` is ancestor | exit 0 | PASS |
| verifier | exact branch/SHA, clean | `OK ... clean=true` | PASS |

未执行 merge、rebase、reset、checkout、cherry-pick、commit、amend 或 push。

### 1.2 已接受产品事实

- B4 checkpoint 是 `9c4c0356f3f2374c22b383ba96331e1dd92505fd`。
- B3/B4 共 15 条 Console route 已生成；B5 只消费
  `packages/contracts/generated/api/console/**`。
- B4 最终 rereview 为 PASS：398 collected / 398 passed；这不能替代 B5 前端验证。
- B4 的 official import internal commit 和未来 DSL 字段风险继续是
  `ACCEPTED_KNOWN_LIMITATION`，B5 只如实展示 copy result/warnings，不宣称原子回滚。

## 2. Official-first findings

### 2.1 可复用的官方 1.16 能力

| 能力 | 官方依据 | B5 用法 |
| --- | --- | --- |
| Generated Console client | `web/service/client.ts` | 使用 `consoleQuery` 的 `queryOptions` / `mutationOptions`；共享 invalidation 写进 `experimental_defaults` |
| Contract router | `packages/contracts/generated/api/console/router.gen.ts` | 使用 `account`、`apps`、`platformAdmin`、`enterpriseMarketplace` 的真实对象路径 |
| Main navigation | `web/app/components/main-nav/routes.ts`、`index.tsx` | 在 route config 增加智慧广场和平台管理员入口；权限由 derived state 决定 |
| Account/workspace state | `web/context/account-state.ts`、`workspace-state.ts`、`permission-state.ts` | 复用当前 account/workspace/permission atoms；不恢复 app context |
| Workspace/member UI | `web/app/components/header/account-setting/members-page/**` | 复用表格、角色、invite result、Form/Dialog 的行为模式，不复用其普通 workspace API |
| App action menu | `web/app/components/apps/app-card.tsx` | 唯一 writer 加入提交入口；Dialog 与 menu 为 sibling surfaces |
| Explore list/detail patterns | `web/app/components/explore/app-list/**`、`app-card/**`、`sidebar/**` | 复用 skeleton、empty、search、card、semantic link 的模式；企业 DTO 不塞进官方 Explore model |
| Dify UI | `packages/dify-ui/README.md`、`web/docs/overlay.md` | 只用 subpath primitives；Dialog/AlertDialog/DropdownMenu/Form/Field/Button；禁止 legacy overlay 与 z-index override |
| Query pagination | apps/explore/deployments 当前实现 | URL/`nuqs` 持有 page/search/sort/filter；`keepPreviousData` 保持分页切换稳定 |
| Frontend tests | `web/docs/test.md` 及相邻 specs | Vitest/RTL 从用户行为验证 loading/error/empty/retry/disabled/focus/navigation |
| i18n sync | `web/i18n-config/README.md`、`languages.ts` | `i18n:check` 可检查 missing/extra keys；自动翻译 workflow 只在 main push 后运行，不能替代当前 Builder 的人工门禁 |

### 2.2 企业差距

- 官方没有平台管理员 workspace/member 页面、身份 bootstrap 或路由。
- 官方没有企业智慧广场 browse/detail/my-submissions/admin-review 页面。
- 官方 app-card 没有 enterprise submit action。
- `consoleQuery` 还没有这些 mutation 的共享 invalidation defaults。
- 当前 main-nav 没有 enterprise route/permission 配置。
- 当前 common i18n 没有 `platformAdmin.*` 或 `enterpriseMarketplace.*` keys。
- B3 generated typed error contracts 不完整；B4 review 422 contract 不完整。

### 2.3 旧企业需求 disposition

| 项目 | disposition | 决定 |
| --- | --- | --- |
| E03 平台管理员前端 | `REIMPLEMENT_ON_NEW_ARCH` | 需求保留；用 generated contracts、Jotai derived permission、TanStack Query 和新 route 实现 |
| E04 智慧广场后端 | `VERIFY_ONLY` | B4 已接受；B5 只验证/消费，不修改 |
| E05 智慧广场前端与导航 | `REIMPLEMENT_ON_NEW_ARCH` | 必须按 1.16 main-nav、route、query、overlay 重实现 |
| C07 旧手写 API 兼容前端 | `DROP_UPSTREAMED` | 整体丢弃；不得恢复旧 service/model/hook/context |
| C11 导航需求 | `REIMPLEMENT_ON_NEW_ARCH` | 需求保留；按 1.16 route/permission state 重实现 |
| 旧 `web/service/use-enterprise-marketplace.ts` | `DROP_UPSTREAMED` | 禁止恢复 |
| 旧 `web/models/enterprise-marketplace.ts` | `DROP_UPSTREAMED` | 禁止恢复；直接消费 generated types |
| 旧 app context / legacy loader | `DROP_UPSTREAMED` | 禁止恢复 |
| B4 contracts | `VERIFY_ONLY` | 只读消费；发现缺陷交回 owner |
| 未批准 member delete/workspace create/delete/archive/owner mutation | `DEFER` | 不得在 UI 暗示或实现 |

## 3. Contract matrix（15/15）

对象路径均来自 generated `orpc.gen.ts`/`router.gen.ts`，不是按 URL 猜测。
`input` 使用 generated detailed shape：`{ params, query?, body? }`。

| # | Route | generated `consoleQuery` / `consoleClient` path | Request | Success | Generated errors | Invalidation / redirect |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | GET `/account/platform-admin-status` | `account.platformAdminStatus.get` | none | `PlatformAdminStatusResponse {is_platform_admin, mutation_supported}` | **缺陷：无 `GetAccountPlatformAdminStatusErrors`**；实际 login guard 可 401 | status atom cache；身份变化时 invalidate；无 redirect |
| 2 | GET `/platform-admin/workspaces` | `platformAdmin.workspaces.get` | query page/limit/keyword/status | `PlatformAdminWorkspacePaginationResponse` | **缺陷：无 typed errors**；实际 400/401/403/409 | query key 含完整 pagination/filter；retry 见 §7 |
| 3 | GET `/platform-admin/workspaces/{workspace_id}` | `platformAdmin.workspaces.byWorkspaceId.get` | params workspace_id | `PlatformAdminWorkspaceResponse` | **缺陷：无 typed errors**；实际 401/403/404/409 | detail key；404 展示 not-found |
| 4 | PATCH same | `platformAdmin.workspaces.byWorkspaceId.patch` | params + `{name}` | updated workspace | **缺陷：无 typed errors**；实际 400/401/403/404/409 | invalidate workspace list + detail；不 optimistic |
| 5 | GET `.../{workspace_id}/members` | `platformAdmin.workspaces.byWorkspaceId.members.get` | params | `PlatformAdminMemberListResponse` | **缺陷：无 typed errors**；实际 401/403/404/409 | members key；读取 list/row `mutation_supported` |
| 6 | POST `.../members/invitations` | `platformAdmin.workspaces.byWorkspaceId.members.invitations.post` | params + emails/language/role | 201 `PlatformAdminMemberInviteResponse` | **缺陷：无 typed errors**；实际 400/401/403/404/409/503 | invalidate members + workspace detail/list；逐邮箱展示 result/action/email_delivery |
| 7 | PATCH `.../members/{member_id}/role` | `platformAdmin.workspaces.byWorkspaceId.members.byMemberId.role.patch` | params workspace_id/member_id + role | success ids | **缺陷：无 typed errors**；实际 400/401/403/404/409/503 | invalidate members；不 optimistic |
| 8 | POST `/apps/{app_id}/enterprise-marketplace/submissions` | `apps.byAppId.enterpriseMarketplace.submissions.post` | params app_id + submission body/optional expected_row_version | 201 `MarketplaceAssetResponse` | 400/401/403/404/409, `MarketplaceErrorResponse` except 401 `UnauthorizedResponse` | invalidate my submissions + admin list; first submit no version; resubmit uses current version |
| 9 | GET `/enterprise-marketplace/submissions` | `enterpriseMarketplace.submissions.get` | page/limit/keyword/category/sort | asset pagination | 400 Marketplace / 401 Unauthorized | complete filter key; retry action |
| 10 | GET `/enterprise-marketplace/assets` | `enterpriseMarketplace.assets.get` | page/limit/keyword/category/sort | snapshot pagination | 400 Marketplace / 401 Unauthorized | public list key; keep previous page data |
| 11 | GET `/enterprise-marketplace/assets/{asset_id}` | `enterpriseMarketplace.assets.byAssetId.get` | params asset_id | snapshot detail | 401 Unauthorized / 404 Marketplace | detail key; 404 not-found, retry for transient only |
| 12 | POST `.../{asset_id}/copies` | `enterpriseMarketplace.assets.byAssetId.copies.post` | params + generated empty body `{}` | 201 `{app_id, import_status, warnings, snapshot_version, content_sha256}` | 400/401/403/404/409/422/503 | invalidate `apps.get` lists; show warnings; then `router.push('/app/'+app_id+'/overview')` |
| 13 | GET `/platform-admin/enterprise-marketplace/assets` | `platformAdmin.enterpriseMarketplace.assets.get` | page/limit/keyword/category/status[]/publication_status[]/snapshot_state[]/sort | asset pagination | 400/401/403 | admin list key；**409 current_tenant_required 未生成** |
| 14 | POST `.../{asset_id}/reviews` | `platformAdmin.enterpriseMarketplace.assets.byAssetId.reviews.post` | params + decision/review_note/expected_row_version | updated asset with new row_version | generated 400/401/403/404/409 | invalidate admin/public/my/detail; **实际 approve 可 422，contract 缺失** |
| 15 | POST `.../{asset_id}/unlist` | `platformAdmin.enterpriseMarketplace.assets.byAssetId.unlist.post` | params + review_note/expected_row_version | updated asset with new row_version | 400/401/403/404/409 | invalidate admin/public/detail; use returned row_version |

### 3.1 Error invariants

- Marketplace errors must be read from generated
  `MarketplaceErrorResponse {code, message, status}`。
- 401 must use generated `UnauthorizedResponse {code, message}` and existing common-layout auth
  refresh behavior；feature 不自行发登录 fetch。
- 禁止把 transport error code 当 domain code；error parser 只接收 generated union 允许的
  body shape/code，未知值落入安全通用文案。
- 409 `stale_asset_version`：保留用户 draft，invalidate/refetch 当前 row，显示“数据已变更”
  conflict；禁止自动重放 mutation。
- review/unlist 成功必须使用 response 的新 `row_version`；列表 invalidate 后以后端为真。
- 503 `rbac_mode_not_supported` / dependency service unavailable：不自动 mutation retry；
  显示可重试或 fail-closed 状态。

### 3.2 Contract blocker evidence

精确证据：

- `packages/contracts/generated/api/console/account/types.gen.ts`：
  `GetAccountPlatformAdminStatusResponses` 存在，`*Errors` 不存在。
- `packages/contracts/generated/api/console/platform-admin/types.gen.ts`：
  7 条 B3 operation 只有 `*Responses`；`PlatformAdminErrorResponse` 也未生成。
- 同文件的 3 条 B4 admin marketplace operation 有 typed errors，证明生成链支持该能力。
- `api/controllers/console/platform_admin.py` 注册了 `PlatformAdminErrorResponse`，但 B3
  route 没有 error response decorators。
- `api/controllers/console/enterprise_marketplace.py` 的 review route 未登记 422；
  `approve_asset` 可抛出三个 status 422 domain errors。

`RECORDED_DECISION — CONTRACT_FIX_REQUIRED`：

- 由独立 contract-owner Fixer 同时补齐 B3 platform-admin/status typed error unions 和
  B4 marketplace review reachable 422，重新生成 contracts。
- 独立 Contract Reviewer 必须核对 exact route/schema evidence、生成物可达 error union、
  deterministic generation 和 contract tests；`CHANGES_REQUIRED` 时只允许
  finding-scoped contract Fixer，随后独立 Rereviewer。
- contract 修复提交 fast-forward 到候选分支并记录其 40 位 exact SHA 前，不得授权
  B5-A 或任何后续 B5 Builder。
- B5 不规定 contract Fixer 的实现 diff，不授权本计划修改 API/generated files，也禁止
  手写 error types、direct fetch 或其他前端 workaround。

## 4. Page / route matrix

| Actor | Route / deep link | Page | Permission | loading / error / empty |
| --- | --- | --- | --- | --- |
| authenticated user | `/enterprise-marketplace` | published asset browse | account initialized | card skeleton；401 global refresh；400 inline retry；zero results empty |
| authenticated user | `/enterprise-marketplace/[assetId]` | immutable snapshot detail/copy | view: authenticated；copy: current workspace editor + `app.create_and_management` | detail skeleton；404 not-found；409/422/503 copy error |
| authenticated editor | `/enterprise-marketplace/submissions` | own submissions/resubmit | view authenticated；submit/edit permission for mutation | table skeleton；empty CTA；409 conflict retains form |
| platform admin | `/platform-admin/workspaces` | workspace search/list | `is_platform_admin` | status + list skeleton；403 fail-closed；empty search；retry |
| platform admin | `/platform-admin/workspaces/[workspaceId]` | detail/rename/member/invite/role | platform admin；mutations also `mutation_supported` | 404；members skeleton；RBAC unavailable banner；503 no side-effect |
| platform admin | `/platform-admin/enterprise-marketplace` | review/reject/unlist queue | platform admin；mutations also `mutation_supported` | filter skeleton；empty；409 stale conflict；422 review validation |
| non-admin deep link | any `/platform-admin/**` | access denied | status false or 403 | never render protected data；no permission flash |

Main-nav：

- `enterprise-marketplace` 对已初始化账号显示，active 覆盖 browse/detail/submissions。
- `platform-admin` 只在 status query 成功且 `is_platform_admin=true` 时显示，active 覆盖
  `/platform-admin/**`。
- status pending 时 admin item 不渲染；status error 时 fail closed、不闪现。
- `mutation_supported=false` 不隐藏只读 admin 页面，但所有 mutation controls disabled，并
  显示 RBAC unavailable 说明。

## 5. Component matrix

| 页面/区域 | 复用官方实现 | 建议新组件 | overlay/form owner |
| --- | --- | --- | --- |
| main nav | `MainNavLink`、route config/visibility | 无 wrapper；增加 route visibility branch | 无 |
| platform workspace list | apps/deployments list header、Skeleton、Pagination | `PlatformAdminWorkspaceListPage`、`WorkspaceTable`、`WorkspaceFilters` | 页面持有 URL filter/query |
| platform workspace detail | account-setting member rows/role labels 的模式 | `WorkspaceDetailPage`、`MemberTable`、`RbacUnavailableBanner` | row 持有 role action |
| rename | current edit-workspace modal 的 field/error/submit behavior | `RenameWorkspaceDialog` | Dialog content 持有 mutation；Form 提交；pending disabled |
| invite | account-setting `invite-modal` recipients/role/result patterns | `InviteMembersDialog`、`InvitationResultList` | Dialog content 持有 draft/mutation；逐邮箱结果不压成单 toast |
| role update | account-setting member menu/role selector pattern | `ChangeMemberRoleDialog` | row/dialog local state；owner/unsupported disabled |
| marketplace browse | Explore card/grid/search/skeleton/empty patterns | `MarketplaceBrowsePage`、`MarketplaceCard`、`MarketplaceFilters` | URL owns filters；query owns server data |
| marketplace detail/copy | Explore detail/app icon/button patterns | `MarketplaceDetailPage`、`CopyAssetAction`、`CopyResultDialog` | copy owner shows warnings before/with navigation |
| submissions | apps list/card patterns | `MySubmissionsPage`、`SubmissionStatus`、`ResubmitAction`、`ResubmitMarketplaceDialog` | B5-C 专用 resubmit dialog 持有 form draft/current `expected_row_version`；409 保留 draft 并 refetch，禁止自动重放 |
| app-card submit | official `AppCardOperationsMenu` | `SubmitMarketplaceDialog`（首次提交 only） | app-card only opens surface；B5-D first-submit dialog owns mutation；resubmit 走 B5-C 专用 dialog，不经 app-card |
| admin marketplace | table/filter/dialog patterns | `MarketplaceReviewPage`、`ReviewDialog`、`UnlistDialog` | row action captures current row_version |

所有新 overlay 只从 `@langgenius/dify-ui/*` 导入。禁止 legacy modal/dialog/drawer、
manual portal、call-site `z-*`。表单必须有 native/Form submit boundary、可见 label、
FieldError，icon-only controls 有 accessible name 和 focus ring。

不修改 account-setting 或 Explore shared files；它们只作只读模式依据。这样避免把企业
DTO 混入官方普通 workspace/explore state。

## 6. State matrix

| State | Owner | 说明 |
| --- | --- | --- |
| dialog open、field draft、selected row/action | local component state | 单 surface 生命周期；close/reset local |
| page/search/sort/filter/category/status/page | Next route + `nuqs` | URL 是唯一来源，支持 deep link/refresh/back-forward |
| platform-admin status query | feature Jotai query atom | main-nav 和多个 admin route guard 共享；导出 field-specific derived atoms |
| `isPlatformAdmin` | derived atom | 从 generated response 派生；pending/error 均 fail closed |
| `platformAdminMutationSupported` | derived atom | status + member response 共同限制 controls；不伪造 RBAC role |
| account/workspace/permission | 现有 context atoms | 复用 `userProfileAtom`、workspace role/ID、permission keys |
| lists/details/mutations | TanStack Query | server/cache state，不复制进 Jotai/local state |
| row_version | query response / dialog submission snapshot | mutation 成功后 invalidate；conflict refetch |
| copy warnings | mutation success result，短生命周期 dialog | 展示后导航；不持久化 |

明确禁止的重复状态：

- 不把 list/detail response、loading/error、pagination cache 复制进 Jotai。
- 不同时在 URL、atom 和 local state 保存同一 filter/page。
- 不用 boolean/ref 手写 mutation in-flight；使用 generated mutation result。
- 不在 app context 增加 platform-admin 或 marketplace state。
- 不复制 generated enum/DTO 为 frontend model。

## 7. Query / mutation matrix

| Owner | Query key / input | pagination/filter | Mutation | optimistic | invalidation | retry/error |
| --- | --- | --- | --- | --- | --- | --- |
| admin status | generated `account.platformAdminStatus.get.key()` | none | none | n/a | auth/profile identity change | 401 no retry；network/503 max 2；else none |
| workspaces | `platformAdmin.workspaces.get` full input | URL page/keyword/status, limit 50 | rename | **No** | all workspace lists + exact detail | queries transient max 2；400/403/404/409 none |
| members | exact workspace ID | none | invite、role | **No** | members；invite also list/detail | mutation never automatic retry；503 explicit retry button only |
| own submissions | full list input | URL page/search/category/sort | submit/resubmit | **No** | submissions + admin assets | 409 conflict refetch, draft retained |
| public assets | full list input | URL page/search/category/sort, limit 24 | copy | **No** | app list after 201 | list transient max 2；copy never auto retry |
| asset detail | exact asset ID | none | copy | **No** | app list; detail unchanged | 404 final；503 retry button |
| admin assets | full filters including arrays | URL page/search/sort/status filters | review、unlist | **No** | admin assets + public assets + exact detail + submissions | 409 refetch current row；422 actionable validation；no auto mutation retry |

`web/service/client.ts` 是所有 B5 mutation shared invalidation 的唯一 writer。
component callbacks 只处理 close/toast/result/navigation，不重复 shared invalidation。

Pagination 切换使用 `keepPreviousData`；搜索 submit/debounce 后 page 重置为 1。服务端 sort
只使用 generated union。未知 string 不 cast 成合法值；URL boundary 先验证。

## 8. i18n matrix and recorded decision

### 8.1 Namespaces

| Prefix | 内容 |
| --- | --- |
| `platformAdmin.*` | nav、workspace list/detail、rename、members、invite results、roles、RBAC unavailable、permission/loading/error/empty/retry |
| `enterpriseMarketplace.*` | nav、browse/detail/submissions、submit/resubmit、review/unlist/copy、warnings、status、conflict、validation/error/empty/retry |

所有 key 位于 `common.json`，不新增 namespace 文件。状态 code 到 key 的映射必须穷尽已生成/
批准 code；后端 `message` 不直接当主要 UI 文案，避免内部/未本地化文本泄漏。

§8.4 是完整且已批准的 key inventory：它是 B5-E 的实现基准（全 23 个 locale 逐 key
落盘），也是 B5-A/B/C/D typed 消费的唯一定义。

### 8.2 当前 locale inventory

仓库有 23 个目录且 `languages.ts` 中 23 个均 `supported: true`：

`ar-TN`、`de-DE`、`en-US`、`es-ES`、`fa-IR`、`fr-FR`、`hi-IN`、`id-ID`、
`it-IT`、`ja-JP`、`ko-KR`、`nl-NL`、`pl-PL`、`pt-BR`、`ro-RO`、`ru-RU`、
`sl-SI`、`th-TH`、`tr-TR`、`uk-UA`、`vi-VN`、`zh-Hans`、`zh-Hant`。

同步机制：

- `pnpm --dir web i18n:check --file common --lang <locales...>` 检查 missing/extra。
- `.github/workflows/translate-i18n-claude.yml` 在 main push 后可生成翻译 PR；它不能让本轮
  dirty Builder diff 自动满足 `web/AGENTS.md`。

### 8.3 RECORDED_DECISION — I18N_OPTION_B_APPROVED

协调者已批准扩大原 Design Gate：B5-E 的 exact allowlist 是全部 23 个 supported
locale 的 `common.json`，不得缩减、扩大或用目录通配替代：

- `web/i18n/ar-TN/common.json`、`web/i18n/de-DE/common.json`、
  `web/i18n/en-US/common.json`、`web/i18n/es-ES/common.json`、
  `web/i18n/fa-IR/common.json`、`web/i18n/fr-FR/common.json`、
  `web/i18n/hi-IN/common.json`、`web/i18n/id-ID/common.json`、
  `web/i18n/it-IT/common.json`、`web/i18n/ja-JP/common.json`、
  `web/i18n/ko-KR/common.json`、`web/i18n/nl-NL/common.json`、
  `web/i18n/pl-PL/common.json`、`web/i18n/pt-BR/common.json`、
  `web/i18n/ro-RO/common.json`、`web/i18n/ru-RU/common.json`、
  `web/i18n/sl-SI/common.json`、`web/i18n/th-TH/common.json`、
  `web/i18n/tr-TR/common.json`、`web/i18n/uk-UA/common.json`、
  `web/i18n/vi-VN/common.json`、`web/i18n/zh-Hans/common.json`、
  `web/i18n/zh-Hant/common.json`。

B5-E 是上述 23 个 shared files 的唯一 writer 和翻译质量 owner。B5-E 必须为每个
非英文 locale 提供正确本地化内容，不得复制 en-US 文案作为占位、不得只依赖 fallback、
不得把 main-push 自动翻译 workflow 当成当前交付。B5-E dirty diff 完成后必须由独立
i18n Reviewer 检查 key parity、命名空间、语义和本地化质量；`CHANGES_REQUIRED` 时仅由
finding-scoped B5-E Fixer 修改上述 allowlist，随后独立 Rereviewer PASS。此决定不解除
contract 阻断，也不构成任何 B5 Builder 授权。

### 8.4 RECORDED_DECISION — 完整且已批准的 key inventory

下表是完整且已批准的 `platformAdmin.*` / `enterpriseMarketplace.*` key inventory，
即 B5PR-01 要求的 "approved namespace/key set" 产物。B5-E 必须把下表每个 key 精确
创建到全部 23 个 `common.json`，不得缩减；B5-A/B/C/D 只能消费下表存在的 typed keys。

#### platformAdmin.* inventory

| Key | 用途 / 消费 surface |
| --- | --- |
| `platformAdmin.nav.label` | main-nav 平台管理员入口标题 |
| `platformAdmin.workspaces.title` | workspace list 页面标题 |
| `platformAdmin.workspaces.searchPlaceholder` | 列表搜索占位 |
| `platformAdmin.workspaces.searchButton` | 搜索按钮 |
| `platformAdmin.workspaces.filterAll` | status 过滤全部 |
| `platformAdmin.workspaces.filterNormal` | status 过滤 normal |
| `platformAdmin.workspaces.filterArchived` | status 过滤 archive |
| `platformAdmin.workspaces.loading` | 列表 loading |
| `platformAdmin.workspaces.empty` | 空结果 |
| `platformAdmin.workspaces.error` | 列表错误文案 |
| `platformAdmin.workspaces.retry` | 重试动作 |
| `platformAdmin.workspaceDetail.title` | workspace detail 页面标题 |
| `platformAdmin.renameWorkspace.title` | 重命名 dialog 标题 |
| `platformAdmin.renameWorkspace.nameLabel` | 名称字段 label |
| `platformAdmin.renameWorkspace.namePlaceholder` | 名称占位 |
| `platformAdmin.renameWorkspace.nameRequired` | 必填校验 |
| `platformAdmin.renameWorkspace.save` | 保存按钮 |
| `platformAdmin.renameWorkspace.cancel` | 取消 |
| `platformAdmin.renameWorkspace.success` | 成功提示 |
| `platformAdmin.renameWorkspace.conflict` | 409 冲突文案 |
| `platformAdmin.members.title` | member list 标题 |
| `platformAdmin.members.loading` | member loading |
| `platformAdmin.members.empty` | member 空结果 |
| `platformAdmin.members.error` | member 错误文案 |
| `platformAdmin.members.retry` | 重试动作 |
| `platformAdmin.members.roleLabel` | 角色列 label |
| `platformAdmin.roles.owner` | 角色 owner |
| `platformAdmin.roles.admin` | 角色 admin |
| `platformAdmin.roles.member` | 角色 member |
| `platformAdmin.ownerBadge` | owner 标记 |
| `platformAdmin.invite.title` | invite dialog 标题 |
| `platformAdmin.invite.recipientsLabel` | 收件人 label |
| `platformAdmin.invite.recipientsPlaceholder` | 收件人占位 |
| `platformAdmin.invite.roleLabel` | 邀请角色 label |
| `platformAdmin.invite.languageLabel` | 邀请语言 label |
| `platformAdmin.invite.send` | 发送按钮 |
| `platformAdmin.invite.cancel` | 取消 |
| `platformAdmin.invite.success` | 整体成功提示 |
| `platformAdmin.invite.resultTitle` | 逐邮箱结果标题 |
| `platformAdmin.invite.status.pending` | 邀请 pending 状态 |
| `platformAdmin.invite.status.activated` | 邀请 activated 状态 |
| `platformAdmin.invite.delivery.sent` | email_delivery sent |
| `platformAdmin.invite.delivery.failed` | email_delivery failed |
| `platformAdmin.changeRole.title` | 角色变更 dialog 标题 |
| `platformAdmin.changeRole.confirmMessage` | 变更确认文案 |
| `platformAdmin.changeRole.save` | 保存 |
| `platformAdmin.changeRole.cancel` | 取消 |
| `platformAdmin.changeRole.success` | 成功提示 |
| `platformAdmin.rbacUnavailable.title` | RBAC unavailable 标题 |
| `platformAdmin.rbacUnavailable.message` | RBAC unavailable 说明 |
| `platformAdmin.errors.unauthorized` | 401 安全通用文案 |
| `platformAdmin.errors.permissionDenied` | 403 fail-closed |
| `platformAdmin.errors.notFound` | 404 |
| `platformAdmin.errors.conflict` | 409 |
| `platformAdmin.errors.serviceUnavailable` | 503 可重试 |
| `platformAdmin.errors.loading` | 通用 loading |

#### enterpriseMarketplace.* inventory

| Key | 用途 / 消费 surface |
| --- | --- |
| `enterpriseMarketplace.nav.label` | main-nav 智慧广场入口标题 |
| `enterpriseMarketplace.browse.title` | browse 页面标题 |
| `enterpriseMarketplace.browse.searchPlaceholder` | 搜索占位 |
| `enterpriseMarketplace.browse.searchButton` | 搜索按钮 |
| `enterpriseMarketplace.browse.categoryAll` | 分类全部 |
| `enterpriseMarketplace.browse.loading` | 列表 loading |
| `enterpriseMarketplace.browse.empty` | 空结果 |
| `enterpriseMarketplace.browse.error` | 列表错误文案 |
| `enterpriseMarketplace.browse.retry` | 重试动作 |
| `enterpriseMarketplace.card.copy` | card 复制按钮 |
| `enterpriseMarketplace.card.viewDetail` | card 查看详情 |
| `enterpriseMarketplace.detail.title` | detail 页面标题 |
| `enterpriseMarketplace.detail.notFound` | 404 |
| `enterpriseMarketplace.detail.error` | 错误文案 |
| `enterpriseMarketplace.detail.retry` | 重试 |
| `enterpriseMarketplace.detail.copy` | 复制按钮 |
| `enterpriseMarketplace.detail.description` | 描述 label |
| `enterpriseMarketplace.detail.category` | 分类 label |
| `enterpriseMarketplace.detail.scenario` | 场景 label |
| `enterpriseMarketplace.detail.tags` | 标签 label |
| `enterpriseMarketplace.copy.confirmTitle` | 复制确认 dialog 标题 |
| `enterpriseMarketplace.copy.confirmMessage` | 复制确认文案 |
| `enterpriseMarketplace.copy.confirm` | 确认按钮 |
| `enterpriseMarketplace.copy.cancel` | 取消 |
| `enterpriseMarketplace.copy.processing` | 复制进行中 |
| `enterpriseMarketplace.copy.success` | 复制成功 |
| `enterpriseMarketplace.copy.warningsTitle` | 警告列表标题 |
| `enterpriseMarketplace.copy.navigateToApp` | 跳转新 app 动作 |
| `enterpriseMarketplace.copy.error.validation` | 422 |
| `enterpriseMarketplace.copy.error.conflict` | 409 |
| `enterpriseMarketplace.copy.error.serviceUnavailable` | 503 |
| `enterpriseMarketplace.copy.error.notFound` | 404 |
| `enterpriseMarketplace.copy.error.permissionDenied` | 403 |
| `enterpriseMarketplace.submissions.title` | submissions 页面标题 |
| `enterpriseMarketplace.submissions.loading` | loading |
| `enterpriseMarketplace.submissions.empty` | 空结果 |
| `enterpriseMarketplace.submissions.emptyCta` | 空结果 CTA |
| `enterpriseMarketplace.submissions.error` | 错误文案 |
| `enterpriseMarketplace.submissions.retry` | 重试 |
| `enterpriseMarketplace.submissions.resubmit` | resubmit 动作 |
| `enterpriseMarketplace.status.pending` | 状态 pending |
| `enterpriseMarketplace.status.approved` | 状态 approved |
| `enterpriseMarketplace.status.rejected` | 状态 rejected |
| `enterpriseMarketplace.status.published` | 状态 published |
| `enterpriseMarketplace.status.unpublished` | 状态 unpublished |
| `enterpriseMarketplace.status.unlisted` | 状态 unlisted |
| `enterpriseMarketplace.status.snapshotError` | 快照异常标记 |
| `enterpriseMarketplace.submitDialog.title` | B5-D 首次提交 dialog 标题 |
| `enterpriseMarketplace.submitDialog.description` | B5-D 首次提交说明 |
| `enterpriseMarketplace.submitDialog.confirm` | B5-D 提交按钮 |
| `enterpriseMarketplace.submitDialog.cancel` | B5-D 取消 |
| `enterpriseMarketplace.submitDialog.success` | B5-D 成功提示 |
| `enterpriseMarketplace.resubmitDialog.title` | B5-C resubmit dialog 标题 |
| `enterpriseMarketplace.resubmitDialog.description` | B5-C resubmit 说明（含当前版本提示） |
| `enterpriseMarketplace.resubmitDialog.confirm` | B5-C 重新提交按钮 |
| `enterpriseMarketplace.resubmitDialog.cancel` | B5-C 取消 |
| `enterpriseMarketplace.resubmitDialog.success` | B5-C 成功提示 |
| `enterpriseMarketplace.resubmitDialog.conflict` | B5-C 409 冲突标题 |
| `enterpriseMarketplace.resubmitDialog.conflictMessage` | B5-C 409 保留 draft/refetch 说明 |
| `enterpriseMarketplace.review.title` | review 页/对话框标题 |
| `enterpriseMarketplace.review.approve` | 批准动作 |
| `enterpriseMarketplace.review.reject` | 拒绝动作 |
| `enterpriseMarketplace.review.reviewNoteLabel` | 审核意见 label |
| `enterpriseMarketplace.review.reviewNotePlaceholder` | 审核意见占位 |
| `enterpriseMarketplace.review.confirm` | 确认按钮 |
| `enterpriseMarketplace.review.cancel` | 取消 |
| `enterpriseMarketplace.review.success` | 成功提示 |
| `enterpriseMarketplace.review.error.validation` | 422 |
| `enterpriseMarketplace.review.error.conflict` | 409 |
| `enterpriseMarketplace.review.error.serviceUnavailable` | 503 |
| `enterpriseMarketplace.unlist.title` | unlist dialog 标题 |
| `enterpriseMarketplace.unlist.confirmMessage` | unlist 确认文案 |
| `enterpriseMarketplace.unlist.confirm` | 确认 |
| `enterpriseMarketplace.unlist.cancel` | 取消 |
| `enterpriseMarketplace.unlist.success` | 成功提示 |
| `enterpriseMarketplace.unlist.error.conflict` | 409 |
| `enterpriseMarketplace.errors.unauthorized` | 401 安全通用文案 |
| `enterpriseMarketplace.errors.permissionDenied` | 403 fail-closed |
| `enterpriseMarketplace.errors.notFound` | 404 |
| `enterpriseMarketplace.errors.conflict` | 409 通用 |
| `enterpriseMarketplace.errors.validation` | 422 通用 |
| `enterpriseMarketplace.errors.serviceUnavailable` | 503 可重试 |
| `enterpriseMarketplace.errors.staleAssetVersion` | stale_asset_version 具体文案 |

### 8.5 RECORDED_DECISION — I18N_EXECUTION_ORDER (MOVE_B5_E_BEFORE_B5_A)

协调者已接受 B5PR-01 的 disposition `MOVE_B5_E_BEFORE_B5_A`：

- §8.4 的 key inventory 是完整且已批准的 `platformAdmin.*` / `enterpriseMarketplace.*`
  key 定义，是 B5-E 的精确实现基准；B5-E 不得缩减、不得依赖 en-US fallback 之外的
  额外 key，也不得向非英文 locale 复制英文占位。
- B5-E 执行门禁排在 B5-A 之前：contract PASS/fast-forward 后第一个执行的 Builder 是
  B5-E。B5-E 必须在 23 个 locale 全部创建 §8.4 inventory、通过 23-locale
  `i18n:check`、提供正确本地化内容，并经独立 B5-E Reviewer / i18n Fixer? / Rereviewer
  PASS 且 fast-forward 后，B5-A/B/C/D 才允许开始。
- B5-A/B/C/D 只读消费 §8.4 typed keys，禁止修改任何 locale/i18n 文件（§11 denylist；
  §8.3 23 个文件唯一 writer=B5-E）。
- 后续 Builder 若发现 §8.4 缺 key：立即停止，交独立 i18n Fixer/Review 补充 inventory
  （必要时经 finding-scoped Plan Fixer 修订 §8.4）与对应 23 个 locale 文件，独立
  Review 后再恢复；Builder 不得越权添加。
- 编号 B5-A..B5-E 表示 ownership package，不表示执行先后；实际执行顺序
  B5-E → B5-A → B5-B → B5-C → B5-D。

## 9. Test matrix

| Observable behavior | Focused Vitest / RTL |
| --- | --- |
| admin nav hidden while status pending/error/false；true 可见；active deep link | main-nav specs + platform state specs |
| non-admin deep link fail closed，无 protected content flash | route guard/page specs |
| workspace pagination/search/status、empty、error retry | platform workspace page spec |
| rename disables duplicate click；success invalidates；409 preserves draft | rename dialog spec |
| RBAC unavailable exposes `role_source=rbac_unavailable` and disables mutations | member page spec |
| invite displays every email/action/email_delivery, including mixed delivery failure | invite dialog spec |
| role mutation respects row/member `mutation_supported` and owner guard | member row spec |
| browse pagination/search/category/sort and empty/retry | marketplace browse spec |
| detail 404 and copy 409/422/503 | detail/copy spec |
| copy button pending cannot activate twice；warnings visible；app_id navigation | copy action spec |
| first submit（B5-D）仅从 app-card 打开、首次提交省略 version；成功后 invalidate submissions | B5-D app-card + submit-marketplace-dialog specs |
| resubmit（B5-C）专用 dialog 携带当前 `expected_row_version`；409 保留 draft、invalidate/refetch、显示 conflict、禁止自动重放 | B5-C submissions + resubmit-marketplace-dialog specs |
| review/unlist send current version；success consumes new version/invalidation | admin marketplace spec |
| stale conflict refetches and does not auto retry | review/resubmit/submissions specs |
| form labels, dialog focus/escape, disabled/loading semantics | owning dialog specs with semantic queries/userEvent |
| B5-E 门禁先于 B5-A：§8.4 inventory 全量落盘、23 locale key parity、prefix、无 hardcoded user copy、`i18n:check` | all-locale i18n check + code review |
| 非英文 locale 是正确本地化内容、无英文占位或 fallback 依赖 | B5-E independent Reviewer 逐 locale 语义 review |

后续 Builder/Reviewer 精确命令：

```bash
pnpm --dir web exec vp test run \
  app/components/main-nav \
  features/platform-admin \
  features/enterprise-marketplace \
  app/components/apps/__tests__/app-card.spec.tsx

pnpm --dir web type-check
pnpm check
```

i18n 命令固定为全部 23 个 supported locale：

```bash
pnpm --dir web i18n:check --file common --lang \
  ar-TN de-DE en-US es-ES fa-IR fr-FR hi-IN id-ID it-IT ja-JP ko-KR \
  nl-NL pl-PL pt-BR ro-RO ru-RU sl-SI th-TH tr-TR uk-UA vi-VN zh-Hans zh-Hant
```

必要浏览器验证（针对本轮 Web build）：

1. admin/non-admin 各登录一次，确认入口、深链刷新、back/forward 和无权限闪烁。
2. A workspace app submit → admin approve → B workspace browse/detail/copy → 跳转新 app overview。
3. reject、unlist、copy warnings、409 stale、422 validation、503 service/RBAC unavailable。
4. keyboard 打开 menu/dialog、Tab focus、Escape close、重复 Enter/click 只发一次 mutation。
5. 1280px desktop 与窄 viewport 检查表格/filters/dialog，无 overlay clipping。

本 Architect 实际未运行上述产品验证；全部见 §14 `NOT_RUN`。

## 10. Exact file ownership matrix

下表是解除 §0 阻断后的建议 ownership。新文件名也是 allowlist，不得用目录通配替代任务单。

| Exact file | Owner | Read-only dependency | Shared conflict | Merge order |
| --- | --- | --- | --- | --- |
| `web/service/client.ts` | B5-A | generated router/types | 全 B5 唯一 writer | 2 |
| `web/app/components/main-nav/routes.ts` | B5-A | current route pattern | main-nav 唯一 writer | 2 |
| `web/app/components/main-nav/index.tsx` | B5-A | platform state | main-nav 唯一 writer | 2 |
| `web/app/components/main-nav/__tests__/index.spec.tsx` | B5-A | test helpers | main-nav 唯一 writer | 2 |
| `web/features/platform-admin/state.ts` | B5-A | account contract/Jotai | feature state 唯一 writer | 2 |
| `web/features/platform-admin/errors.ts` | B5-A | fixed generated B3 error types | blocked until contract fix | 2 |
| `web/features/platform-admin/__tests__/state.spec.tsx` | B5-A | fresh QueryClient | none | 2 |
| `web/features/platform-admin/README.md` | B5-A | skill module boundary | feature README 唯一 writer | 2 |
| `web/app/(commonLayout)/platform-admin/workspaces/page.tsx` | B5-B | B5-A status guard | new | 3 |
| `web/app/(commonLayout)/platform-admin/workspaces/[workspaceId]/page.tsx` | B5-B | B5-A status guard | new | 3 |
| `web/features/platform-admin/workspace-list-page.tsx` | B5-B | generated queries | new | 3 |
| `web/features/platform-admin/workspace-detail-page.tsx` | B5-B | generated queries | new | 3 |
| `web/features/platform-admin/workspace-filters.tsx` | B5-B | nuqs | new | 3 |
| `web/features/platform-admin/workspace-table.tsx` | B5-B | dify-ui | new | 3 |
| `web/features/platform-admin/member-table.tsx` | B5-B | generated response | new | 3 |
| `web/features/platform-admin/rbac-unavailable-banner.tsx` | B5-B | mutation flags | new | 3 |
| `web/features/platform-admin/rename-workspace-dialog.tsx` | B5-B | Form/Dialog/query | new | 3 |
| `web/features/platform-admin/invite-members-dialog.tsx` | B5-B | Form/Dialog/query | new | 3 |
| `web/features/platform-admin/invitation-result-list.tsx` | B5-B | generated result type | new | 3 |
| `web/features/platform-admin/change-member-role-dialog.tsx` | B5-B | generated roles | new | 3 |
| `web/features/platform-admin/__tests__/workspace-list-page.spec.tsx` | B5-B | RTL | new | 3 |
| `web/features/platform-admin/__tests__/workspace-detail-page.spec.tsx` | B5-B | RTL | new | 3 |
| `web/features/platform-admin/__tests__/member-mutations.spec.tsx` | B5-B | RTL | new | 3 |
| `web/app/(commonLayout)/enterprise-marketplace/page.tsx` | B5-C | main-nav route | new | 4 |
| `web/app/(commonLayout)/enterprise-marketplace/[assetId]/page.tsx` | B5-C | route params | new | 4 |
| `web/app/(commonLayout)/enterprise-marketplace/submissions/page.tsx` | B5-C | route | new | 4 |
| `web/app/(commonLayout)/platform-admin/enterprise-marketplace/page.tsx` | B5-C | admin state | new | 4 |
| `web/features/enterprise-marketplace/README.md` | B5-C | module boundary | feature README 唯一 writer | 4 |
| `web/features/enterprise-marketplace/errors.ts` | B5-C | generated marketplace errors | blocked until review 422 fix | 4 |
| `web/features/enterprise-marketplace/marketplace-filters.tsx` | B5-C | nuqs | new | 4 |
| `web/features/enterprise-marketplace/marketplace-card.tsx` | B5-C | AppIcon/card pattern | new | 4 |
| `web/features/enterprise-marketplace/browse-page.tsx` | B5-C | generated public list | new | 4 |
| `web/features/enterprise-marketplace/detail-page.tsx` | B5-C | generated detail | new | 4 |
| `web/features/enterprise-marketplace/copy-asset-action.tsx` | B5-C | copy mutation/router | new | 4 |
| `web/features/enterprise-marketplace/copy-result-dialog.tsx` | B5-C | warnings | new | 4 |
| `web/features/enterprise-marketplace/my-submissions-page.tsx` | B5-C | submissions query | new | 4 |
| `web/features/enterprise-marketplace/submission-status.tsx` | B5-C | generated fields | new | 4 |
| `web/features/enterprise-marketplace/resubmit-action.tsx` | B5-C | B5-C resubmit-marketplace-dialog | new | 4 |
| `web/features/enterprise-marketplace/resubmit-marketplace-dialog.tsx` | B5-C | generated submission mutation/current row_version | new | 4 |
| `web/features/enterprise-marketplace/admin-review-page.tsx` | B5-C | admin query | new | 4 |
| `web/features/enterprise-marketplace/review-dialog.tsx` | B5-C | row_version | new | 4 |
| `web/features/enterprise-marketplace/unlist-dialog.tsx` | B5-C | row_version | new | 4 |
| `web/features/enterprise-marketplace/__tests__/browse-page.spec.tsx` | B5-C | RTL | new | 4 |
| `web/features/enterprise-marketplace/__tests__/detail-copy.spec.tsx` | B5-C | RTL | new | 4 |
| `web/features/enterprise-marketplace/__tests__/submissions.spec.tsx` | B5-C | RTL | new | 4 |
| `web/features/enterprise-marketplace/__tests__/admin-review.spec.tsx` | B5-C | RTL | new | 4 |
| `web/app/components/apps/app-card.tsx` | B5-D | B5-D submit-marketplace-dialog（首次提交） | apps app-card 唯一 writer | 5 |
| `web/app/components/apps/__tests__/app-card.spec.tsx` | B5-D | current app card fixtures | apps test 唯一 writer | 5 |
| `web/features/enterprise-marketplace/submit-marketplace-dialog.tsx` | B5-D | generated submit mutation（首次提交 only） | new | 5 |
| `web/features/enterprise-marketplace/__tests__/submit-marketplace-dialog.spec.tsx` | B5-D | RTL | new | 5 |
| `web/i18n/ar-TN/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/de-DE/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/en-US/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/es-ES/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/fa-IR/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/fr-FR/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/hi-IN/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/id-ID/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/it-IT/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/ja-JP/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/ko-KR/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/nl-NL/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/pl-PL/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/pt-BR/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/ro-RO/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/ru-RU/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/sl-SI/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/th-TH/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/tr-TR/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/uk-UA/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/vi-VN/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/zh-Hans/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |
| `web/i18n/zh-Hant/common.json` | B5-E | §8.4 approved key inventory | i18n 唯一 writer/质量 owner | 1 |

`web/app/components/header/account-setting/**` 和 `web/app/components/explore/**` 在 B5 中
read-only；没有 Builder 可写。`web/context/account-state.ts`、
`workspace-state.ts`、`permission-state.ts` 也保持 read-only。

本表 Merge order 即执行顺序：B5-E 门禁先于 B5-A（`MOVE_B5_E_BEFORE_B5_A`），随后
B5-A → B5-B → B5-C → B5-D。B5-C/B5-D 共享同一个 generated submission mutation
（`apps.byAppId.enterpriseMarketplace.submissions.post`），其 shared invalidation 只由
B5-A 的 `web/service/client.ts` 定义一次；`submit-marketplace-dialog.tsx` 与
`resubmit-marketplace-dialog.tsx` 互不 import。B5-C 不得写 `submit-marketplace-dialog.tsx`
或 `app-card.tsx`；B5-D 不得写任何 `resubmit-*` 文件。B5-A/B/C/D 均不得写任何
locale/i18n 文件（§11、§8.5）。

## 11. Global denylist

所有 B5 Builder 均禁止：

- `api/**`、`api/migrations/**`；
- `docker/**`、`docker/volumes/**`、`dify-agent/**`；
- `packages/contracts/**`、`packages/contracts/generated/**`；
- `packages/dify-ui/**`、`packages/iconify-collections/**`；
- lockfile、dependency、版本文件；
- `web/service/use-enterprise-marketplace.ts`；
- `web/models/enterprise-marketplace.ts`；
- 旧 app context、legacy contract loader、direct
  `fetch('/console/api/...')`、手写 Console response/error types；
- §8.3 精确列出的 23 个文件以外的 locale/i18n 文件；
- B5-A/B/C/D 对任何 locale/i18n 文件的写操作（只读消费 §8.4 typed keys；缺 key 时
  必须停止并交独立 i18n Fixer/Review，不得越权添加）；
- B5-D 写 `web/features/enterprise-marketplace/resubmit-*`、B5-C 写
  `web/features/enterprise-marketplace/submit-marketplace-dialog.tsx`；
- 真实 `.env`、secret、数据库、Redis、vector、container、volume 或外部服务写操作。

若需要 denylist 文件才能实现，Builder 必须停止并报告，不得扩 scope。

## 12. Builder topology and serial gates

严格最小串行链：

```text
independent contract-owner Fixer repairs B3 typed errors + B4 review 422
→ independent Contract Reviewer
→ CHANGES_REQUIRED: finding-scoped Contract Fixer → independent Contract Rereviewer
→ contract PASS fast-forwarded to candidate and exact SHA recorded
→ B5-E all-23-locale foundation: §8.4 approved platformAdmin.*/enterpriseMarketplace.*
  key inventory 全量落盘, 23-locale parity, 正确本地化, 非英文无英文占位, i18n:check
→ independent B5-E Reviewer → i18n Fixer? → independent B5-E Rereviewer
→ B5-A contract/state/client/main-nav（只读消费 §8.4 typed keys）
→ Code Reviewer → Fixer? → Rereviewer
→ B5-B platform-admin UI（只读消费 §8.4 typed keys）
→ Code Reviewer → Fixer? → Rereviewer
→ B5-C marketplace pages + dedicated resubmit dialog（只读消费 §8.4 typed keys）
→ Code Reviewer → Fixer? → Rereviewer
→ B5-D app-card first-submit entry + first-submit dialog（只读消费 §8.4 typed keys）
→ Code Reviewer → Fixer? → Rereviewer
→ full frontend regression/browser gate
→ Final Reviewer → Fixer? → Final Rereviewer
```

后继 Builder 只从前一 Rereviewer PASS 且已 fast-forward 到候选分支的精确 SHA 开始。
不得预填未来 SHA；不得并行启动。`I18N_OPTION_B_APPROVED` 已关闭选择问题；
`MOVE_B5_E_BEFORE_B5_A` 使 B5-E 门禁排在 B5-A 之前——编号 B5-A..B5-E 表示 ownership
package，不表示执行先后，实际执行顺序 B5-E → B5-A → B5-B → B5-C → B5-D；
`CONTRACT_FIX_REQUIRED` 未经独立 Reviewer PASS 前整个 B5 链不启动。

### B5-A allowlist

- `web/service/client.ts`
- `web/app/components/main-nav/routes.ts`
- `web/app/components/main-nav/index.tsx`
- `web/app/components/main-nav/__tests__/index.spec.tsx`
- `web/features/platform-admin/README.md`
- `web/features/platform-admin/state.ts`
- `web/features/platform-admin/errors.ts`
- `web/features/platform-admin/__tests__/state.spec.tsx`

Denylist：除上列外全仓；尤其 account-setting/apps/explore/i18n/contracts/API。B5-A
只读消费 §8.4 approved typed keys；不得向任何 locale/i18n 文件添加或修改 key。

### B5-B allowlist

仅 §10 中 owner=B5-B 的 15 个精确文件。Denylist：B5-A files、marketplace/apps/i18n、
全局 denylist。B5-B 只读消费 §8.4 typed keys；不得写任何 locale/i18n 文件。

### B5-C allowlist

仅 §10 中 owner=B5-C 的 23 个精确文件（含 `resubmit-marketplace-dialog.tsx`，不含
B5-D 的 `submit-marketplace-dialog.tsx`）。Denylist：main-nav/client/platform
workspace files/apps/i18n、全局 denylist。B5-C 只读消费 §8.4 typed keys；不得写任何
locale/i18n 文件，不得依赖 B5-D 的 `submit-marketplace-dialog.tsx`。

### B5-D allowlist

- `web/app/components/apps/app-card.tsx`
- `web/app/components/apps/__tests__/app-card.spec.tsx`
- `web/features/enterprise-marketplace/submit-marketplace-dialog.tsx`
- `web/features/enterprise-marketplace/__tests__/submit-marketplace-dialog.spec.tsx`

Denylist：其余全部；尤其 client/main-nav/explore/account-setting/i18n/contracts、
`resubmit-*`。B5-D 只负责首次提交入口与首次提交 dialog；不得创建/修改任何
`resubmit-*` 文件（B5-C 独占），不得写任何 locale/i18n 文件。

### B5-E allowlist（执行门禁先于 B5-A；编号表示 ownership package，不表示执行先后）

只允许以下 23 个 exact files：

- `web/i18n/ar-TN/common.json`
- `web/i18n/de-DE/common.json`
- `web/i18n/en-US/common.json`
- `web/i18n/es-ES/common.json`
- `web/i18n/fa-IR/common.json`
- `web/i18n/fr-FR/common.json`
- `web/i18n/hi-IN/common.json`
- `web/i18n/id-ID/common.json`
- `web/i18n/it-IT/common.json`
- `web/i18n/ja-JP/common.json`
- `web/i18n/ko-KR/common.json`
- `web/i18n/nl-NL/common.json`
- `web/i18n/pl-PL/common.json`
- `web/i18n/pt-BR/common.json`
- `web/i18n/ro-RO/common.json`
- `web/i18n/ru-RU/common.json`
- `web/i18n/sl-SI/common.json`
- `web/i18n/th-TH/common.json`
- `web/i18n/tr-TR/common.json`
- `web/i18n/uk-UA/common.json`
- `web/i18n/vi-VN/common.json`
- `web/i18n/zh-Hans/common.json`
- `web/i18n/zh-Hant/common.json`

Denylist：所有 TS/TSX、其他 locale/i18n files、contracts/API/Docker。B5-E 是 shared
i18n 唯一 writer 和翻译质量 owner；不得向非英文 locale 复制英文占位。B5-E 按 §8.4
approved key inventory 实现全部 23 个 locale 并通过 23-locale `i18n:check`；PASS 并
fast-forward 后 B5-A/B/C/D 才只读消费 typed keys。B5-E 完成后必须通过独立 B5-E
Reviewer；有 finding 时经 i18n Fixer 和独立 Rereviewer 后才可进入后续 Builder。后续
Builder 发现缺 key 时必须停止并交独立 i18n Fixer/Review，不得越权添加。

每个 Builder：

1. 起点核验 branch/HEAD/clean/B4 ancestor/accepted predecessor ancestor。
2. TDD：先建立可观察失败场景，再最小实现。
3. 只运行自己的 focused specs；Reviewer 独立重跑。
4. dirty diff 交协调者检查；未经另行授权不 commit/amend/push。
5. finding Fixer 只修改 Reviewer 枚举的 exact files；Rereviewer 跑该阶段完整 focused set。

## 13. Risks, decisions and stop conditions

### 13.1 Known limitations

- page-number pagination 在并发更新时可漂移；稳定 sort/id 由后端控制，UI 不假装 snapshot
  pagination。
- copy 201 之后 official import 已可能内部 commit；warnings 必须展示，不能承诺撤销。
- status/role/publication/snapshot fields 多数 generated 为 `string` 而非 enum；UI 只接受已知
  display mapping，未知值显示 safe unknown，不另造可发送的 enum。
- B4 public snapshot nullable 字段必须在 render boundary 处理，不能在 query 层改成空字符串。

### 13.2 RECORDED_DECISION

1. `CONTRACT_FIX_REQUIRED`：独立 contract-owner Fixer 必须同时修复 B3
   platform-admin/status typed error unions 和 B4 marketplace review reachable 422；
   独立 Contract Reviewer/Rereviewer PASS 且修复 fast-forward 到候选分支前，
   `BLOCKED_PENDING_CONTRACT_FIX` 保持有效。B5 禁止任何 frontend workaround。
2. `I18N_OPTION_B_APPROVED`：B5-E 独占 §8.3 的 23 个 exact `common.json`，负责正确
   本地化内容和翻译质量；禁止向非英文 locale 复制英文占位，完成后必须独立 Review。
3. `MOVE_B5_E_BEFORE_B5_A`（B5PR-01 disposition）：§8.4 是完整且已批准的 key
   inventory；B5-E 执行门禁先于 B5-A，全 23 个 locale 落盘并独立 Review PASS 后，
   B5-A/B/C/D 才只读消费 typed keys；B5-A/B/C/D 禁止修改 locale/i18n；缺 key 时
   Builder 停止并交独立 i18n Fixer/Review，不得越权添加。
4. `B5_C_OWNS_DEDICATED_RESUBMIT_DIALOG`（B5PR-02 disposition）：
   `resubmit-marketplace-dialog.tsx` 唯一 owner=B5-C；`resubmit-action.tsx` 只依赖该
   dialog，不依赖 B5-D 的 `submit-marketplace-dialog.tsx`；409 保留 draft、refetch、
   显示 conflict，禁止自动重放 mutation。

上述决定均已关闭决策问题。i18n 选择与执行顺序已关闭；contract 修复决定已形成，但其
修复与独立 Review 尚未完成，因此仍是当前技术门禁。

### 13.3 Stop conditions

- exact branch/SHA/clean/ancestor 不符；
- generated contract 缺陷仍存在；
- Builder 需要 API/contracts/generated 修改；
- contract Fixer/Reviewer 未证明 B3 typed errors 和 B4 review 422 均已修复；
- B5-E 需要写 §8.3 以外 locale/i18n 文件，或无法提供正确本地化内容；
- B5-A/B/C/D 需要修改任何 locale/i18n 文件，或需要 §8.4 inventory 之外的新 key
  （须停止并交独立 i18n Fixer/Review）；
- B5-C 依赖 B5-D 文件（如 `submit-marketplace-dialog.tsx`），或 B5-D 写任何
  `resubmit-*` 文件；
- 两个 Builder 文件所有权重叠（含 submit/resubmit dialog 越界写）；
- 需要恢复旧 1.15 service/model/hooks/context；
- 需要 direct fetch 或手写 response/error type；
- 需要修改 account-setting/explore shared files 而未重新 Review ownership；
- 任一 401/403/404/409/422/503 无可观察 UI；
- 出现 P0/P1 security、tenant、permission 或 deep-link leak；
- 需要数据库、Docker、vector、volume 或外部服务写操作。

## 14. Architect validation record and NOT_RUN

### 14.1 实际执行的只读/文档命令

| Command | exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | exact branch |
| `git rev-parse HEAD` | 0 | exact SHA |
| `git status --short --branch` | 0 | branch only |
| `git status --porcelain=v1` | 0 | empty before edit |
| `git merge-base --is-ancestor 9c4c... HEAD` | 0 | ancestor=true |
| `verify_git_start.sh "$(pwd)" ...` | 0 | `clean=true` |
| ordered `sed` reads of required docs/Web guides/UI README | 0 | sources read |
| `rg`/`sed` generated contract inspection | 0 | 15 operationIds found |
| B3 typed-error search | 0 command; no matches | 0/7 B3 route error unions |
| B4 typed-error search | 0 | 8/8 B4 route error unions, with review 422 omission |
| locale directory count | 0 | 23 |
| `supported: true` count | 0 | 23 |

### 14.2 NOT_RUN

| Area | Status |
| --- | --- |
| frontend focused Vitest | NOT_RUN — Architect plan only |
| web type-check | NOT_RUN |
| `pnpm check` | NOT_RUN |
| browser/E2E | NOT_RUN |
| contract generation | NOT_RUN — explicitly forbidden |
| backend/API tests | NOT_RUN |
| database/migration | NOT_RUN |
| vector | NOT_RUN |
| Docker/runtime | NOT_RUN |
| offline | NOT_RUN |
| volume/upgrade/rollback | NOT_RUN |

源码检查不能替代 browser behavior。B4 398/398 不能替代 B5 tests。

## 15. Exact final validation commands

Architect 交付必须执行：

```bash
git diff --name-status
git diff -- docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md
git diff --check
git status --short --branch
git status --porcelain=v1
```

后续最终 B5 Reviewer 在所有 Builder 合并后执行：

```bash
git diff --name-status <accepted-b5-plan-and-contract-sha>...HEAD
git diff --check

pnpm --dir web exec vp test run \
  app/components/main-nav \
  features/platform-admin \
  features/enterprise-marketplace \
  app/components/apps/__tests__/app-card.spec.tsx

pnpm --dir web type-check
pnpm check
```

B5-E 门禁先于 B5-A 运行：B5-E 全 23 个 locale 落盘 §8.4 inventory 后，先执行 §8 固定
的 all-23-locale i18n 命令，再由独立 B5-E Reviewer 完成逐 locale 翻译质量 Review，
确认非英文 locale 无英文占位或 fallback 依赖；PASS 并 fast-forward 后 B5-A/B/C/D 才
开始。后续各 Builder 阶段 gate 再执行 §9 browser checklist。不得运行
`gen-api-contract` 作为 B5 validation；contracts 的 deterministic generation 属于独立
contract Fixer/Reviewer。

## 16. Plan Reviewer checklist

- [ ] 强制起点与 B4 ancestor 证据真实。
- [ ] 15/15 routes 均映射到真实 generated object path。
- [ ] input/output/error/invalidation/redirect 无 route-name 猜测。
- [ ] B3 typed errors 缺失和 B4 review 422 omission 已按 exact file evidence 阻断。
- [ ] 没有提出手写 fetch/type/legacy loader workaround。
- [ ] E05/C11 为 `REIMPLEMENT_ON_NEW_ARCH`；C07 和旧 hooks/models/context 被丢弃。
- [ ] official main-nav/account-setting/apps/explore/Jotai/Query/dify-ui 优先复用。
- [ ] route permission、深链、loading/error/empty/retry/conflict/duplicate click/a11y 完整。
- [ ] `member.mutation_supported`、`role_source=rbac_unavailable` 和 status
  `mutation_supported` fail closed。
- [ ] invitation 每个 email 的 action/email_delivery 均展示。
- [ ] copy warnings 与 app_id `/app/{id}/overview` navigation 明确。
- [ ] review/unlist 使用 `expected_row_version`，成功后依赖新 version/invalidation。
- [ ] server state 不复制进 Jotai；URL/client/server state ownership 清楚。
- [ ] shared invalidation 只有 `web/service/client.ts` writer。
- [ ] main-nav、apps app-card、feature state、i18n、submit/resubmit dialog 均唯一
  writer（`resubmit-marketplace-dialog.tsx` 只属 B5-C，`submit-marketplace-dialog.tsx`
  只属 B5-D）。
- [ ] account-setting/explore shared files read-only。
- [ ] Builder allowlist 是 exact files，denylist 含 API/Docker/migration/contracts。
- [ ] i18n 23 locale inventory 和自动同步机制真实。
- [ ] `CONTRACT_FIX_REQUIRED` 已记录，B3 typed errors 与 B4 review 422 由独立
  contract-owner Fixer/Reviewer 门禁，不存在 frontend workaround。
- [ ] `I18N_OPTION_B_APPROVED` 已记录，23 个 exact `common.json` 均属于 B5-E，且无
  allowlist 缩减、扩大或目录通配。
- [ ] `MOVE_B5_E_BEFORE_B5_A` 已记录：§8.4 是完整且已批准的 key inventory；B5-E 门禁
  先于 B5-A；A/B/C/D 只读消费 typed keys、禁止修改 locale/i18n；缺 key 走独立 i18n
  Fixer/Review。
- [ ] `B5_C_OWNS_DEDICATED_RESUBMIT_DIALOG` 已记录：`resubmit-action.tsx` 只依赖
  B5-C 的 `resubmit-marketplace-dialog.tsx`，无对 B5-D `submit-marketplace-dialog.tsx`
  的前向依赖；409 保留 draft/refetch/conflict、禁止自动重放。
- [ ] B5-E 是 i18n 唯一 writer/翻译质量 owner；非英文 locale 禁止英文占位，完成后有
  独立 Reviewer/Fixer/Rereviewer 门禁。
- [ ] tests 是可观察 behavior，不是 source-string/implementation assertion。
- [ ] NOT_RUN 诚实，contract generation 明确禁止。
- [ ] Plan Reviewer 和 Contract Reviewer 未 PASS、contract 修复未 fast-forward 时没有
  Builder 授权；i18n recorded decision 本身不授权 B5-E。

## 17. Gate

```text
Architect dirty plan
→ coordinator inspects real diff
→ separately authorizes plan commit
→ fast-forward plan commit into candidate
→ independent Plan Reviewer from exact new SHA
→ CHANGES_REQUIRED: finding-scoped Fixer
→ independent Rereviewer
→ independent contract-owner Fixer closes both §3.2 gaps
→ independent Contract Reviewer
→ CHANGES_REQUIRED: finding-scoped Contract Fixer → independent Contract Rereviewer
→ contract PASS fast-forwarded and exact SHA recorded
→ only then coordinator may authorize B5-E（all-23-locale foundation，§8.4 inventory）
→ independent B5-E Reviewer → i18n Fixer? → independent B5-E Rereviewer
→ B5-E fast-forwarded；then B5-A → B5-B → B5-C → B5-D（每步独立 Reviewer/Fixer?/Rereviewer）
```

`RECORDED_DECISION`：`CONTRACT_FIX_REQUIRED`、`I18N_OPTION_B_APPROVED`、
`MOVE_B5_E_BEFORE_B5_A`、`B5_C_OWNS_DEDICATED_RESUBMIT_DIALOG`。

当前门禁：**BLOCKED_PENDING_CONTRACT_FIX**。

`B5_BUILDER_NOT_AUTHORIZED`。

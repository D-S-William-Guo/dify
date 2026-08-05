# Dify Enterprise 1.16.0 Replay B5-B Platform-Admin Workspace/Member UI — Independent Review

## RECOVERY

- Expected/actual branch: `ctyun/replay-116-b5-b-reviewer` / `ctyun/replay-116-b5-b-reviewer` — PASS.
- Expected/actual HEAD: `f912864a1a963a9f89fac46612dc7d85c472e088` / `f912864a1a963a9f89fac46612dc7d85c472e088` — PASS.
- Start status: `## ctyun/replay-116-b5-b-reviewer`; porcelain empty — clean worktree and index.
- Range: `11bae180bb8c2786dd89a45f6c062a784b63510a..f912864a1a963a9f89fac46612dc7d85c472e088`; commit metadata:
  `commit=f912864a1a963a9f89fac46612dc7d85c472e088`, `parent=11bae180bb8c2786dd89a45f6c062a784b63510a`, `subject=feat: add enterprise B5-B platform-admin workspace/member UI`. Range contains exactly this one commit.
- Recovery preflight completed before any review-source read or report creation. No recovery or repair operation was performed. No commit/amend/push occurred.

## SCOPE

- `git diff --name-status 11bae180bb8c2786dd89a45f6c062a784b63510a..f912864a1a963a9f89fac46612dc7d85c472e088`: exactly 15 `A` paths, the approved B5-B allowlist only (2 app pages, 10 feature files, 3 specs):

```text
A  web/app/(commonLayout)/platform-admin/workspaces/[workspaceId]/page.tsx
A  web/app/(commonLayout)/platform-admin/workspaces/page.tsx
A  web/features/platform-admin/__tests__/member-mutations.spec.tsx
A  web/features/platform-admin/__tests__/workspace-detail-page.spec.tsx
A  web/features/platform-admin/__tests__/workspace-list-page.spec.tsx
A  web/features/platform-admin/change-member-role-dialog.tsx
A  web/features/platform-admin/invitation-result-list.tsx
A  web/features/platform-admin/invite-members-dialog.tsx
A  web/features/platform-admin/member-table.tsx
A  web/features/platform-admin/rbac-unavailable-banner.tsx
A  web/features/platform-admin/rename-workspace-dialog.tsx
A  web/features/platform-admin/workspace-detail-page.tsx
A  web/features/platform-admin/workspace-filters.tsx
A  web/features/platform-admin/workspace-list-page.tsx
A  web/features/platform-admin/workspace-table.tsx
```

- `git diff --stat`: `15 files changed, 2427 insertions(+)`.
- `git diff --check` (range): exit 0, no whitespace errors.
- `git diff --binary ... | sha256sum` = `31698fe18b70f4e0fa0080e86d6e554e16ab335973e0a4e27ac65901d856ecdd`, exactly matching the committed-diff measurement.
- No B5-A/C/D file, no marketplace/apps/account-setting/explore/i18n/contracts/API/Docker/lockfile/manifest path in the range.

### Sources read

1. `docs/enterprise/replay-1.16.0/CURRENT_STATE.md` (complete)
2. `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` (complete, all sections; §8.4 key inventory)
3. `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REVIEW.md`, `B5_IMPLEMENTATION_PLAN_REREVIEW.md`
4. `docs/enterprise/replay-1.16.0/B5_CONTRACT_FIX_REREVIEW.md`
5. `docs/enterprise/replay-1.16.0/B5_E_I18N_REVIEW.md`
6. `docs/enterprise/replay-1.16.0/B5_A_REVIEW.md`
7. `web/AGENTS.md`, `web/docs/test.md`, `web/docs/lint.md`
8. `.agents/skills/frontend-code-review/SKILL.md` and its routed rule packs (accessibility-ui, dify-ui, component-architecture, data-query-contracts, performance, testing, dify-invariants, code-quality), `.agents/skills/frontend-testing/SKILL.md`, `.agents/skills/how-to-write-component/SKILL.md`, `.agents/skills/karpathy-guidelines/SKILL.md`
9. All 15 reviewed files (HEAD) and the exact range diff
10. B5-A foundation owners read-only: `web/features/platform-admin/state.ts`, `errors.ts`, `web/service/client.ts` (B5-B depends on the shared `mutationOptions` defaults: `retry:false` + shared invalidation for rename/invite/role), `web/features/platform-admin/README.md`
11. Generated contracts read completely: `packages/contracts/generated/api/console/platform-admin/types.gen.ts` (workspace list/detail/patch, members list, invitations, role patch data/error/response shapes)
12. Read-only dependency modules: `web/context/i18n.ts` (`useLocale`), `web/app/components/apps/studio-list-header.tsx`, `web/next/link.ts`
13. Dify UI primitives (from the exact-HEAD isolated install): `packages/dify-ui/src/pagination/index.tsx` (`Pagination` clamps out-of-range pages via `clampPage`), `segmented-control/index.tsx` (BaseToggleGroup array-value API), and dialog/field/select/toast/button/input surfaces via type-check
14. B5-E locale keys read-only: `web/i18n/en-US/common.json` (all 54 consumed `platformAdmin.*` keys verified present and matching §8.4 inventory)

## FINDINGS

No P0/P1/P2 findings.

Open P0/P1/P2 counts: `0/0/0`.

### P3 observations (non-gating)

- `web/features/platform-admin/workspace-detail-page.tsx:109-110` computes
  `workspaceMutationSupported = globalMutationSupported && (members?.mutation_supported ?? true)`.
  During the members-loading window and the members-error window, `members` is `undefined`, so the
  `?? true` keeps the header rename/invite buttons enabled (and no RBAC banner) until the members
  query resolves. Once members resolve with `mutation_supported=false`, the controls disable and the
  banner renders. The backend is the authoritative fail-closed RBAC enforcer (the mutation cannot
  succeed without server authorization), so no protected data or unauthorized mutation is reachable;
  this is only a transient UI-affordance nuance. Recorded as a possible future refinement, not a
  finding.
- `web/features/platform-admin/workspace-detail-page.tsx:86-90` maps any non-Response/non-domain
  `unknown` detail-query error to the `platformAdmin.errors.notFound` message. The reachable detail
  errors per contract are 401/403/404/409 (each correctly mapped), so the `notFound` fallback only
  triggers for truly unknown failures (e.g., network rejection), where a retry button is also shown.
  Slightly misleading copy in an edge case; fail-safe and non-blocking.
- `web/features/platform-admin/change-member-role-dialog.tsx:51` initializes the role select to
  `admin`/`normal` only. A member whose `role` is `dataset_operator` or `editor` renders the default
  `normal` selection rather than a current-role display; the user must pick a new role. No sendable
  enum is invented (only the two approved non-owner values are offered), so this is a UX nuance only.

## REVIEW

### A. Scope and architecture — PASS

The range is exactly the approved 15-file B5-B allowlist (2427 insertions, diff SHA-256 `31698fe1...`).
All three mutations consume only the generated `consoleQuery.platformAdmin.*.mutationOptions()` paths
(rename: `platformAdmin.workspaces.byWorkspaceId.patch`; invite:
`platformAdmin.workspaces.byWorkspaceId.members.invitations.post`; role:
`platformAdmin.workspaces.byWorkspaceId.members.byMemberId.role.patch`), verified against
`packages/contracts/generated/api/console/platform-admin/types.gen.ts` operation shapes. B5-B adds no
shared-invalidation writer; the only invalidation lives in B5-A `web/service/client.ts`
(rename → list + exact detail; invite → members + detail + list; role → members), which B5-B inherits
through the default `mutationOptions`. No direct fetch, no handwritten response/error types, no legacy
loader/app-context, no Jotai copies of server data, no locale/contract/API/Docker change.

### B. Fail-closed permission — PASS

`WorkspaceListPage` (workspace-list-page.tsx:38-48) and `WorkspaceDetailPage`
(workspace-detail-page.tsx:29-39) gate on the B5-A status atoms: pending → `errors.loading`,
error or `!isPlatformAdmin` → `errors.permissionDenied`, and only `is_platform_admin === true` renders
the protected content. Because the workspace/member queries are issued only inside the gated content
components, a non-admin never triggers the protected fetches, so there is no permission flash and no
protected data render on pending/error/false. `platformAdminMutationSupportedAtom` and the member
response `mutation_supported` jointly limit mutation controls (see C).

### C. Workspace list — PASS

- URL owns page/search/status through `nuqs` (`workspacePageQueryState` integer default 1,
  `workspaceSearchQueryState` string default `''`, `workspaceStatusQueryState` enum
  `all|normal|archive`), enabling deep link/refresh/back-forward. The detail link href is
  `/platform-admin/workspaces/{id}`.
- `WORKSPACE_PAGE_SIZE = 50` is sent as `limit`; `keepPreviousData` keeps the table stable across page
  changes; `status` is omitted when `'all'` and `keyword` only when non-empty.
- Search submit (`commitSearch`) and status change (`commitStatus`) both call `setPage(1)`, resetting
  to the first page (verified by the URL-update specs asserting `searchParams.has('page') === false`).
- Skeleton (`role="status"`), empty-search, and mapped error states with a retry button are present;
  403/400/404/409/503 map through `mapPlatformAdminError` (`errors.ts`, B5-A). The query retry returns
  `false` for any `Response` (matching the reachable 400/401/403/409 error set, none retried) and
  `failureCount < 2` for transient non-Response failures.
- The dify-ui `Pagination` clamps out-of-range `page` values, so deep links with an invalid page do not
  break pagination.

### D. Workspace detail and dialogs — PASS

- Rename dialog: required validation (`hasError = name.trim().length === 0`, submit disabled),
  `Field`/`FieldLabel`/`FieldError match="valueMissing"`, and a duplicate-submit guard
  (`isPending` early-return in `handleSubmit` plus `disabled`/`loading` button). 409 keeps the dialog
  open, preserves the draft, and shows `renameWorkspace.conflict`; success toasts and closes.
- Member table: change-role is disabled for the owner (`member.role !== 'owner'`), for
  `mutation_supported=false` rows, and for `role_source === 'rbac_unavailable'` rows; the owner badge
  renders only for `role === 'owner'`. The unknown-role display is safe: `memberRoleLabelKey` returns
  `undefined` for roles outside owner/admin/normal and renders no invented label.
- Invite dialog: sends `emails`/`role`/`language` (`useLocale` current locale) and renders
  `InvitationResultList` showing every email with its `action` and `email_delivery` status
  (all five `action` and all three `email_delivery` generated union members are exhaustively mapped),
  including mixed delivery outcomes. A 503 keeps the draft and shows `errors.serviceUnavailable`
  without auto-retry.
- RBAC banner: shows when global or member-level mutation support is off or any row has
  `role_source='rbac_unavailable'`; it does not hide the read-only workspace name or member list.
- 404: unknown/unmapped detail errors and true 404 map to `errors.notFound` with the workspace name
  hidden; 503 member errors render a retryable state with no side effect.

### E. Mutation/query contract — PASS

All three mutations use generated `mutationOptions()` with no `retry`/`onMutate`/`onRollback` override
(shared defaults provide `retry:false` and the exact plan §7 invalidation). Component callbacks handle
only close/toast/result/navigation; no component calls `invalidateQueries`. No optimistic update and no
duplicate shared invalidation. Server/cache state stays in TanStack Query; dialog drafts, the
`roleChangeMember` selection, and open flags are local component state only.

### F. i18n — PASS

All 54 distinct `platformAdmin.*` keys consumed across the 10 feature files and `errors.ts` were
extracted programmatically and cross-checked against `web/i18n/en-US/common.json` and the approved
§8.4 inventory: 0 missing, 0 extra, every key in the approved set. No locale file is written, no
hardcoded user-facing copy exists (member/workspace names, emails, plans, counts are data), and no
sendable enum is invented (only approved `admin`/`normal` role values are offered in both select
surfaces; unknown display values fall back to safe no-label/default-label).

### G. UI primitives and accessibility — PASS

Overlays (Dialog, DialogContent, DialogCloseButton, DialogTitle, DialogDescription, toast) and form
controls (Field/FieldControl/FieldError/FieldLabel, Select*, Input, SegmentedControl, Button,
Pagination) come exclusively from `@langgenius/dify-ui/*`. No legacy modal/portal/call-site `z-*`,
no `@/app/components/base` overlay import. Forms use native `onSubmit`/`type="submit"` boundaries;
visible labels via `FieldLabel`; FieldError present for required fields; icon-only and action controls
carry accessible names (`aria-label`, `aria-labelledby` semantics verified through the specs' role-based
queries); the list link has an explicit `focus-visible:ring-2`; skeleton/banner use `role="status"`.

### H. Tests and evidence quality — PASS

All three specs exercise observable behavior through public boundaries (role/label/URL queries,
`userEvent`, `toast` spies, network-boundary `vi.mock('@/service/client')` that preserves the real
generated query keys and mutation `retry:false`), and cover every required scenario in plan §9 for B5-B:
pending/denied fail-closed deep links, URL-driven filters and page reset, skeleton/empty/403-retry,
rename required/duplicate/409-draft, not-found, members loading/503-retry/no-side-effect, RBAC banner +
disabled controls, invite per-email and mixed-delivery results, 503 draft retention, owner/mutation/
rbac_unavailable role guards, and 409 role-change retention. Coverage split across the three files is
coherent (10 + 9 + 7 = 26 focused tests).

## VALIDATION

All commands ran in an isolated task environment extracted from the exact HEAD via
`git archive f912864a1a963a9f89fac46612dc7d85c472e088` into `/tmp/b5b-review.PLiQL5/source`, with a
frozen offline install (`pnpm install --frozen-lockfile --store-dir /home/ctyun/BigData/.pnpm-store`,
Node 22.22.2 first in PATH, pnpm 11.10.0, task-local XDG/TMPDIR roots). Lockfile hash before/after
install `62f3e0f3639dd80d1d058cae38a3dca53fc5b626fb2e6bec446a0aa397148ee7` (unchanged). The isolated
environment was deleted after validation; no command wrote to the review worktree.

| Exact command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b5-b-reviewer` | PASS |
| `git rev-parse HEAD` | 0 | `f912864a1a963a9f89fac46612dc7d85c472e088` | PASS |
| `git status --short --branch` / `--porcelain=v1` (start) | 0 | branch only, empty | PASS |
| `git diff --name-status 11bae180bb8c2786dd89a45f6c062a784b63510a..f912864a1a963a9f89fac46612dc7d85c472e088` | 0 | exactly the 15 approved `A` paths | PASS |
| `git diff --stat 11bae180bb8c2786dd89a45f6c062a784b63510a..f912864a1a963a9f89fac46612dc7d85c472e088` | 0 | `15 files changed, 2427 insertions(+)` | PASS |
| `git diff --check 11bae180bb8c2786dd89a45f6c062a784b63510a..f912864a1a963a9f89fac46612dc7d85c472e088` | 0 | no output | PASS |
| `git diff --binary 11bae180bb8c2786dd89a45f6c062a784b63510a..f912864a1a963a9f89fac46612dc7d85c472e088 \| sha256sum` | 0 | `31698fe18b70f4e0fa0080e86d6e554e16ab335973e0a4e27ac65901d856ecdd` | PASS (matches accepted measurement) |
| `pnpm --dir web exec vp test run 'app/(commonLayout)/platform-admin/workspaces' 'features/platform-admin/__tests__/workspace-list-page.spec.tsx' 'features/platform-admin/__tests__/workspace-detail-page.spec.tsx' 'features/platform-admin/__tests__/member-mutations.spec.tsx'` | 0 | `Test Files 3 passed (3); Tests 26 passed (26)` | PASS |
| `pnpm --dir web exec vp test run features/platform-admin` | 0 | `Test Files 4 passed (4); Tests 49 passed (49)` | PASS |
| `pnpm exec vp check <15 exact paths>` | 1 | `error: Cannot find binary path for command 'node'` | FAIL — literal command fails solely with the known pnpm-shim/node-shadow resolution error; direct binary fallback run and reported separately |
| `./node_modules/.bin/vp check <15 exact paths>` | 0 | `pass: All 15 files are correctly formatted`; `pass: Found no warnings, lint errors, or type errors in 15 files` | PASS |
| `pnpm --dir web type-check` | 0 | `tsc` no diagnostics | PASS |
| `pnpm check` | 1 | `vp check` reports formatting issues in exactly the five accepted B1 files; `pnpm lint:eslint` short-circuited | ACCEPTED_LIMITATION (B1 baseline) |
| `git diff --check` (working tree) | 0 | clean at start | PASS |
| `git diff --name-status` / `git diff --stat` (working tree) | 0 | empty at start | PASS |
| `git status --short --branch` / `git status --porcelain=v1` | 0 | branch only at start; after report, branch plus the sole report entry | see GIT |

### git diff --check

Range and working-tree `git diff --check` both exit 0 with no output. Final status after writing this
report: `?? docs/enterprise/replay-1.16.0/B5_B_REVIEW.md` only.

## NOT_RUN

- Full ESLint: NOT_RUN — short-circuited inside `pnpm check` by the exact accepted five-file `vp check` B1 baseline, matching the established repository limitation.
- Browser/E2E: NOT_RUN — B5-B is a client-rendered feature stage; plan §9 browser checklist belongs to the later full-frontend regression gate.
- Contract generation: NOT_RUN — prohibited.
- Backend/API tests: NOT_RUN — no backend change in this range.
- Database/migration: NOT_RUN.
- Redis: NOT_RUN.
- Vector: NOT_RUN.
- Docker/runtime/container/image: NOT_RUN.
- Offline validation: NOT_RUN.
- Volume/upgrade/rollback: NOT_RUN.
- External services: NOT_RUN — prohibited.
- Dependency installation in the original review worktree: NOT_RUN — prohibited; the frozen offline install occurred only in the deleted exact-HEAD `/tmp` snapshot.

## GIT

- Final worktree/index status: only `?? docs/enterprise/replay-1.16.0/B5_B_REVIEW.md` (this report) is dirty. All 15 reviewed product/test files and every denylisted path are untouched.
- `git diff --check`: exit 0, no output.
- Commit: **NOT_COMMITTED**.
- Amend: **NOT_AMENDED**.
- Push: **NO_PUSH**.
- No Fixer, Rereviewer, Builder, PR, or other Agent created. `B5_B_FIXER_NOT_STARTED`.

## GATE

```text
PASS
B5_B_ACCEPTED=yes
open P0/P1/P2 findings = 0/0/0
B5_B_FIXER_NOT_STARTED
```

- Scope is exactly the approved 15 files (2427 insertions, diff SHA-256 `31698fe1...`).
- All B5-B behavior and type evidence is complete: focused Vitest 26/26, `features/platform-admin` 49/49, direct `./node_modules/.bin/vp check` PASS on all 15 files, `pnpm --dir web type-check` PASS, and `pnpm check` reproduces only the accepted five-file B1 baseline (ESLint short-circuited → NOT_RUN). The literal `pnpm exec vp check` node-shim failure is recorded separately and is the accepted baseline limitation.
- No unauthorized write or external-state action was performed. Only this report is preserved dirty for coordinator inspection.

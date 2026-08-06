# Dify Enterprise 1.16.0 Replay B5-C Enterprise Marketplace Pages — Independent Review

## RECOVERY

- Expected/actual branch: `ctyun/replay-116-b5-c-reviewer` / `ctyun/replay-116-b5-c-reviewer` — PASS.
- Expected/actual HEAD: `a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b` / `a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b` — PASS.
- Start status: `## ctyun/replay-116-b5-c-reviewer`; `git status --porcelain=v1` empty — clean worktree and index.
- Range: `0bc4a1e3101ff8109a84a907421b8fa0e3c03c94..a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b`; commit metadata: `commit=a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b`, `parent=0bc4a1e3101ff8109a84a907421b8fa0e3c03c94`, `subject=feat: add enterprise B5-C enterprise-marketplace pages`. Range contains exactly this one commit.
- Recovery preflight completed before any review-source read or report creation. No recovery or repair operation was performed. No commit/amend/push occurred.

## SCOPE

- `git diff --name-status 0bc4a1e3101ff8109a84a907421b8fa0e3c03c94..a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b`: exactly 23 `A` paths, the approved B5-C allowlist only (4 app pages, 14 feature files, 4 specs, README):

```text
A  web/app/(commonLayout)/enterprise-marketplace/[assetId]/page.tsx
A  web/app/(commonLayout)/enterprise-marketplace/page.tsx
A  web/app/(commonLayout)/enterprise-marketplace/submissions/page.tsx
A  web/app/(commonLayout)/platform-admin/enterprise-marketplace/page.tsx
A  web/features/enterprise-marketplace/README.md
A  web/features/enterprise-marketplace/__tests__/admin-review.spec.tsx
A  web/features/enterprise-marketplace/__tests__/browse-page.spec.tsx
A  web/features/enterprise-marketplace/__tests__/detail-copy.spec.tsx
A  web/features/enterprise-marketplace/__tests__/submissions.spec.tsx
A  web/features/enterprise-marketplace/admin-review-page.tsx
A  web/features/enterprise-marketplace/browse-page.tsx
A  web/features/enterprise-marketplace/copy-asset-action.tsx
A  web/features/enterprise-marketplace/copy-result-dialog.tsx
A  web/features/enterprise-marketplace/detail-page.tsx
A  web/features/enterprise-marketplace/errors.ts
A  web/features/enterprise-marketplace/marketplace-card.tsx
A  web/features/enterprise-marketplace/marketplace-filters.tsx
A  web/features/enterprise-marketplace/my-submissions-page.tsx
A  web/features/enterprise-marketplace/resubmit-action.tsx
A  web/features/enterprise-marketplace/resubmit-marketplace-dialog.tsx
A  web/features/enterprise-marketplace/review-dialog.tsx
A  web/features/enterprise-marketplace/submission-status.tsx
A  web/features/enterprise-marketplace/unlist-dialog.tsx
```

- `git diff --stat`: `23 files changed, 3389 insertions(+)`.
- `git diff --numstat`: 3389 insertions / 0 deletions.
- `git diff --check` (range): exit 0, no whitespace errors.
- `git diff --binary ... | sha256sum` = `f103d71504fcd58d56bbe382a7b1eb2e6deafea06aa1d4c08e3684e38358b51d`, exactly matching the known committed-diff measurement.
- No B5-A/C/D-adjacent write, no `submit-marketplace-dialog.tsx`, no `app-card.tsx`, no client/main-nav/i18n/contracts/API/Docker/lockfile/manifest path in the range.

### Sources read

1. `docs/enterprise/replay-1.16.0/CURRENT_STATE.md` (complete)
2. `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` (complete; §3.1 error invariants, §4 page/permission matrix, §5 component matrix, §7 query/mutation matrix, §8.4 key inventory, §9 test matrix, §10 ownership, §12 serial gates, §13 stop conditions)
3. `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REVIEW.md`, `B5_IMPLEMENTATION_PLAN_REREVIEW.md`, `B5_CONTRACT_FIX_REREVIEW.md`, `B5_E_I18N_REVIEW.md`, `B5_A_REVIEW.md`, `B5_B_REVIEW.md`
4. `web/AGENTS.md`, `web/docs/test.md`, `web/docs/lint.md`
5. `.agents/skills/frontend-code-review/SKILL.md` and its routed rule packs (accessibility-ui, dify-ui, component-architecture, data-query-contracts, performance, testing, dify-invariants, code-quality), `.agents/skills/frontend-testing/SKILL.md`, `.agents/skills/how-to-write-component/SKILL.md`, `.agents/skills/karpathy-guidelines/SKILL.md`
6. All 23 reviewed files (HEAD) and the exact range diff
7. B5-A foundation owners read-only: `web/features/platform-admin/state.ts` (four status atoms), `web/service/client.ts` (shared `mutationOptions` defaults for submit/resubmit/copy/review/unlist: `retry:false` + the plan §7 invalidation breadth), `web/features/platform-admin/README.md`
8. Generated contracts read completely: `packages/contracts/generated/api/console/{enterprise-marketplace,platform-admin,apps}/types.gen.ts` (all six marketplace operation error unions, `MarketplaceAssetResponse`/`MarketplaceSnapshotResponse`/`MarketplaceSnapshotDetailResponse`, `MarketplaceSubmissionPayload`/`MarketplaceReviewPayload`/`MarketplaceUnlistPayload`/`MarketplaceCopyPayload`, list query shapes incl. `sort` unions and filter arrays), plus the `orpc.gen.ts`/`zod.gen.ts` operation registrations
9. Official layout/overlay owners read-only: `web/app/components/apps/studio-list-header.tsx`, `web/app/components/explore/app-list/explore-app-list-header.tsx`, `web/app/components/header/account-setting/index.tsx`, `web/next/navigation.ts`/`link.ts`, `packages/dify-ui/src/field/index.tsx`, `packages/dify-ui/src/select/index.tsx`, `packages/dify-ui/src/toast/index.tsx`
10. Base UI 1.6.0 Select runtime from the exact-HEAD isolated install: `select/root/SelectRoot.mjs` (`setValue` fires `onValueChange(nextValue, …)` unconditionally before any change guard), `select/item/SelectItem.mjs` (`commitSelection` → `setValue(itemValue, …)` on item press with `itemValue` defaulting to `null` but honoring the explicit `value=""`), and `SelectRoot.d.ts` (`onValueChange?: (value: string | null, …)`)
11. B5-B RBAC precedent read-only: `web/features/platform-admin/workspace-detail-page.tsx` (`platformAdminMutationSupportedAtom`, `RbacUnavailableBanner`, disabled mutation controls) and `rbac-unavailable-banner.tsx`
12. B5-E locale keys read-only: `web/i18n/en-US/common.json` (all consumed `enterpriseMarketplace.*` keys verified present and matching the §8.4 inventory)

## FINDINGS

Open P0/P1/P2 counts: `1/1/0` (one P1, one P2).

### [P1] Browse category "All" option cannot be selected — filter can never be reset to All

File: `web/features/enterprise-marketplace/marketplace-filters.tsx:84-86`

```tsx
onValueChange={(nextCategory) => {
  if (nextCategory) commitCategory(nextCategory)
}}
```

The "All" item is `<SelectItem value="">` (marketplace-filters.tsx:92). Base UI Select 1.6.0 (the exact pinned runtime) fires `onValueChange` with the pressed item's raw value on every item press with no empty-string guard: `SelectItem.mjs` `commitSelection` → `setValue(itemValue, …)` (line 121), `SelectRoot.mjs` `setValue` → `onValueChange?.(nextValue, …)` (lines 260-266). Clicking "All" therefore calls `onValueChange("")`, and the consumer's truthiness guard drops it, so `commitCategory` is never reached and `setCategory(null)` never runs.

Reproduction: render the browse page, select any category (URL gains `?category=…`), open the category Select again and pick "All". The dropdown closes and the URL/category filter is unchanged; the user cannot return to the unfiltered browse view through the UI. The admin page's equivalent control handles the empty case correctly (`admin-review-page.tsx:311-314`, `selectCategory(value === '' ? null : value)`), and `commitCategory` in the same file is written to accept `''` (`nextCategory === '' ? null : nextCategory`), confirming the intent. The `browse-page.spec.tsx` only feeds category through `searchParams` and never exercises the Select, so the defect is untested.

Violated contract: plan §4/§7 URL-driven filters — the URL is the single source of truth for `category`, and the reset path is dead. Finding-scoped repair boundary: `marketplace-filters.tsx` only (remove the truthiness guard, e.g. `onValueChange={(nextCategory) => commitCategory(nextCategory)}`). Blocks acceptance: YES.

### [P2] Admin review queue does not fail-closed on `mutation_supported=false`

File: `web/features/enterprise-marketplace/admin-review-page.tsx:64-73` (gate) and 187-210 (approve/reject/unlist buttons)

`AdminReviewPage` gates only on the identity atoms (`platformAdminStatusPendingAtom`, `platformAdminStatusErrorAtom`, `isPlatformAdminAtom`). It never reads `platformAdminMutationSupportedAtom` (B5-A `state.ts`), the approve/reject/unlist buttons are never disabled for `mutation_supported=false`, and no RBAC-unavailable notice is rendered.

Violated contract: plan §4 ("review/reject/unlist queue | platform admin; mutations also `mutation_supported`"; and the general rule "`mutation_supported=false` 不隐藏只读 admin 页面，但所有 mutation controls disabled，并显示 RBAC unavailable 说明") and §7 mutation matrix. The B5-B precedent implements exactly this (`workspace-detail-page.tsx:57,110,137` consumes `platformAdminMutationSupportedAtom`, gates controls, renders `RbacUnavailableBanner`); B5-C omits it. Impact: in RBAC-unavailable deployments the queue offers enabled mutations that fail server-side with 503 (`rbac_mode_not_supported`, mapped to `review.error.serviceUnavailable`); the server remains the authoritative enforcer, so there is no auth/tenant leak — this is a plan-conformance and affordance gap, not a security hole. Finding-scoped repair boundary: `admin-review-page.tsx` (consume `platformAdminMutationSupportedAtom`, disable mutation controls and show an RBAC note when false). Blocks acceptance: YES (open P2).

### P3 observations (non-gating)

- `web/features/enterprise-marketplace/copy-asset-action.tsx:55-57`, `resubmit-marketplace-dialog.tsx:91-93`, `review-dialog.tsx:82-84`, `unlist-dialog.tsx:66-68`: an unknown-kind mutation error (including the reachable generated `400` on copy/submit/review/unlist) sets `submissionError` to `null`, leaving the dialog open with no visible message. Plan §3.1 requires unknown values to fall to a safe generic message; the list surfaces do (`browse.error`/`submissions.error`), but the mutation dialogs cannot because §8.4 contains no generic mutation-error key and B5-C may not add keys. Plan-vs-inventory tension; fail-safe (dialog stays open, no auto-replay), non-gating.
- `web/features/enterprise-marketplace/browse-page.tsx:65`, `my-submissions-page.tsx:63`, `admin-review-page.tsx:134`: three `sticky top-0 z-10` headers are literal call-site `z-*` under plan §5's wording. Honest classification: they are layout sticky-header stacking (not overlay layering) that replicates verbatim the official 1.16 list-header idiom the plan directs B5-C to reuse (`web/app/components/apps/studio-list-header.tsx:10` and `web/app/components/explore/app-list/explore-app-list-header.tsx:25` carry the identical class string `sticky top-0 z-10 … bg-background-body px-8 pt-4 pb-2`; account-setting also uses `z-20` sticky headers). `z-10` stays below the dify-ui overlay `z-50`/`z-60` stack, so no overlay/focus/a11y defect results. Literal plan-text deviation worth a coordinator note (possible plan amendment), non-gating.
- `web/features/enterprise-marketplace/detail-page.tsx:78`: `CopyAssetAction` renders unconditionally; plan §4 lists the copy permission as "current workspace editor + `app.create_and_management`" but the UI does not gate the button on workspace role. A non-editor sees the button and only learns on submit via the mapped 403 (`copy.error.permissionDenied`), which is observable and server-authoritative. Non-gating.

## REVIEW

### A. Scope and architecture — PASS

The range is exactly the approved 23-file B5-C allowlist (3389 insertions / 0 deletions, diff SHA-256 `f103d715…`). All four mutation surfaces consume only generated `consoleQuery.*.mutationOptions()` (submit/resubmit: `apps.byAppId.enterpriseMarketplace.submissions.post`; copy: `enterpriseMarketplace.assets.byAssetId.copies.post`; review: `platformAdmin.enterpriseMarketplace.assets.byAssetId.reviews.post`; unlist: `…unlist.post`), verified against the generated `orpc.gen.ts` routers and the operation error unions in `types.gen.ts`. `errors.ts` is a status-driven guard over the generated `UnauthorizedResponse`/`MarketplaceErrorResponse` and the generated operation-error unions — no handwritten DTO/error re-declaration. No direct `fetch`, no legacy app-context/contract loader, no Jotai copies of server data, no locale/contract/API/Docker write. No dependency on B5-D `submit-marketplace-dialog.tsx` or `app-card.tsx` (`resubmit-action.tsx` imports only the B5-C `resubmit-marketplace-dialog.tsx`). Shared success invalidation remains solely in B5-A `web/service/client.ts`; the only component-side `invalidateQueries` calls are the three 409-conflict-path refetches (resubmit/review/unlist dialogs).

### B. Browse — PASS (one P1 on the category reset, see FINDINGS)

URL owns page/search/category/sort via nuqs (`parseAsInteger`/`parseAsString`/`parseAsStringEnum` over the exact generated `sort` union); `MARKETPLACE_PAGE_SIZE = 24`; `placeholderData: keepPreviousData`; card grid skeleton (`role="status"`), empty state, inline error with retry; `resolveListErrorMessage` maps 400 and other unknown statuses to `browse.error` and 503 to `errors.serviceUnavailable`; retry returns `false` for any `Response` and max-2 for transient failures; safe rendering of non-nullable snapshot display fields (title/category/description/tags) with unknown `publication_status`/`status` values rendered via no label rather than a crash. All confirmed by `browse-page.spec.tsx` (9 tests).

### C. Detail and copy — PASS

Immutable snapshot render from the generated `MarketplaceSnapshotDetailResponse`; 404 → `detail.notFound` with no retry, other errors → `detail.error` with retry (transient-only). Copy 409/422/503 map to the approved `copy.error.conflict/validation/serviceUnavailable` keys; 403/404 also map to approved keys; warnings render from the generated `MarketplaceCopyResponse.warnings`; success navigates to `/app/{result.app_id}/overview` via the official `@/next/navigation` shim; `startCopy` guards `isPending` and the confirm button is `disabled`+`loading`, so a pending copy cannot activate twice. All confirmed by `detail-copy.spec.tsx` (8 tests).

### D. Submissions and resubmit — PASS

Table skeleton, empty state with CTA to `/apps`, per-row `SubmissionStatus` (pending/approved/rejected + publication status + snapshot-error marker; unknown values render no label). `ResubmitAction` opens only the B5-C `ResubmitMarketplaceDialog`; the dialog submits via the shared generated mutation with `expected_row_version: asset.row_version` and current draft fields (trimmed; optional fields omitted when empty); `isPending`+`hasError` guard double submit; a 409 keeps the dialog open with the draft intact, shows `resubmitDialog.conflict`/`conflictMessage`, invalidates the submissions list key (the row lives in that list — the "current row refetch"), and never auto-replays (mutation `retry:false` via shared defaults). Confirmed by `submissions.spec.tsx` (7 tests). No dependency on B5-D's first-submit dialog.

### E. Admin review — PASS except the P2 in FINDINGS

Fail-closed gate on the B5-A status atoms: pending → loading, error or `!isPlatformAdmin` → `permissionDenied`, and the admin query is issued only inside the gated content component (no permission flash, no protected data on pending/error/false). URL-driven filters: page/search/category/sort plus `status[]`, `publication_status[]`, `snapshot_state[]` arrays via `parseAsArrayOf(parseAsString)`; toggles reset page to 1. Approve/reject/unlist all send `expected_row_version: asset.row_version`; 409 refetches the admin list and does not auto-replay; 422 maps to `review.error.validation`; 503 to `review.error.serviceUnavailable`. Confirmed by `admin-review.spec.tsx` (13 tests). The `mutation_supported=false` fail-closed affordance required by plan §4 is missing (open P2).

### F. Mutations — PASS

All four mutations consume generated `mutationOptions()` with no component override of `retry` (shared defaults provide `retry:false`); no `onMutate`/`onRollback`/optimistic update anywhere; success invalidation lives only in B5-A `web/service/client.ts` (submissions → submissions+admin assets; copy → `apps.get`; review → admin+public+submissions+exact detail; unlist → admin+public+exact detail); the three component `invalidateQueries` are exclusively the required 409-conflict-path refetches. Server/cache state stays in TanStack Query; dialog drafts/targets/open flags are local component state.

### G. i18n — PASS

All 75 literal `enterpriseMarketplace.*` keys consumed across the 14 production feature files were extracted programmatically and cross-checked against `web/i18n/en-US/common.json` and the approved §8.4 inventory: 0 missing, 0 extra, every key in the approved set (the only other string matches are `consoleQuery.enterpriseMarketplace.*` contract object paths, not i18n keys). No locale file written, no hardcoded user-facing copy (titles, categories, tags, warnings, notes are data). Unknown status/publication/snapshot values use a safe no-label fallback (`submission-status.tsx`), and no sendable enum is invented (`review` sends only the generated `'approved' | 'rejected'` union; `sort` only the generated three-value union).

### H. UI primitives and accessibility — PASS

All overlays (Dialog/DialogContent/DialogCloseButton/DialogTitle/DialogDescription, toast) come from `@langgenius/dify-ui/*`; forms use native `onSubmit`/`type="submit"` boundaries (search, resubmit, review, unlist); visible `FieldLabel`s and `FieldError match="valueMissing"` on the required resubmit fields; `aria-label`/`aria-labelledby` on icon-ambiguous and filter controls (search input, category trigger/select, filter checkboxes with label text); `focus-visible:ring-2` on links and controls; skeleton/empty states use `role="status"`; no legacy modal/portal. The three `sticky top-0 z-10` headers are evaluated in FINDINGS (P3). The category reset defect (P1) is a browse-flow functional regression but is not an overlay/a11y issue.

### I. Tests and evidence quality — PASS (with coverage note)

All four specs exercise observable behavior through public boundaries (role/label/URL queries, `userEvent`, network-boundary `vi.mock('@/service/client')` preserving the real generated query keys and `retry:false`, `NuqsTestingAdapter`, fresh QueryClient per test, `QueryClientAtomHydrator` for the Jotai status query). Coverage matches plan §9: 9 browse + 8 detail-copy + 7 submissions + 13 admin-review = 37 tests, all focused on the required behaviors (browse filters/page/skeleton/empty/400/503/unknown, 404 no-retry, copy 409/422/503/duplicate-guard/navigation/warnings, resubmit row-version + 409 draft retention + no-auto-replay, admin fail-closed deep-link + filter arrays + row versions + 409/422/503). Coverage note: the category Select interaction is not covered by any spec, which is exactly why the P1 reset defect shipped untested.

### J. Feature README — PASS

`web/features/enterprise-marketplace/README.md` provides the module name (`enterprise-marketplace`), a one-sentence boundary ("Frontend surfaces for browsing, copying, submitting, and reviewing the enterprise marketplace."), `Internal Modules` (the 14 feature files), and `External Modules` (`features/platform-admin/state`). The remaining imports are the whitelisted plumbing (`@/service/client`, `@/next/link`, `@/next/navigation`) and npm/workspace packages (`@langgenius/dify-ui/*`, `@tanstack/react-query`, `nuqs`, `jotai`, `react-i18next`, `@dify/contracts/*`), which the repository whitelist rules say to omit — consistent with the B5-A/B precedent.

## VALIDATION

All commands ran in an isolated task environment extracted from the exact HEAD via `git archive a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b` under `/home/ctyun/BigData/.system-data/tmp/opencode/b5c-review/source`, with a frozen offline install (`pnpm install --frozen-lockfile --store-dir /home/ctyun/BigData/.pnpm-store`, Node 22.22.2 first in PATH, pnpm 11.10.0). Lockfile hash before/after install `62f3e0f3639dd80d1d058cae38a3dca53fc5b626fb2e6bec446a0aa397148ee7` (unchanged). The isolated environment was deleted after validation; no command wrote to the review worktree.

| Exact command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b5-c-reviewer` | PASS |
| `git rev-parse HEAD` | 0 | `a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b` | PASS |
| `git status --short --branch` / `--porcelain=v1` (start) | 0 | branch only, empty | PASS |
| `git diff --name-status 0bc4a1e3101ff8109a84a907421b8fa0e3c03c94..a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b` | 0 | exactly the 23 approved `A` paths | PASS |
| `git diff --stat 0bc4a1e3101ff8109a84a907421b8fa0e3c03c94..a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b` | 0 | `23 files changed, 3389 insertions(+)` | PASS |
| `git diff --check 0bc4a1e3101ff8109a84a907421b8fa0e3c03c94..a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b` | 0 | no output | PASS |
| `git diff --binary 0bc4a1e3101ff8109a84a907421b8fa0e3c03c94..a5c1e2a336c95ed71c6dea0961c985f0f7fdc40b \| sha256sum` | 0 | `f103d71504fcd58d56bbe382a7b1eb2e6deafea06aa1d4c08e3684e38358b51d` | PASS (matches the known committed-diff measurement) |
| `pnpm --dir web exec vp test run 'app/(commonLayout)/enterprise-marketplace' 'app/(commonLayout)/platform-admin/enterprise-marketplace' 'features/enterprise-marketplace'` | 0 | `Test Files 4 passed (4); Tests 37 passed (37)` | PASS (matches Builder's 37/37) |
| `pnpm exec vp check <23 exact paths>` | 1 | `error: Cannot find binary path for command 'node'` | FAIL — literal command fails solely with the known pnpm-shim/node-shadow resolution error; direct binary fallback run and reported separately (matches the accepted baseline limitation) |
| `./node_modules/.bin/vp check <23 exact paths>` | 0 | `pass: All 23 files are correctly formatted`; `pass: Found no warnings, lint errors, or type errors in 22 files` (README.md excluded from type scope) | PASS |
| `pnpm --dir web type-check` | 0 | `tsc` no diagnostics | PASS |
| `pnpm check` | 1 | `vp check` reports formatting issues in exactly the five accepted B1 files; `pnpm lint:eslint` short-circuited | ACCEPTED_LIMITATION (B1 baseline); ESLint NOT_RUN |
| `git diff --check` (working tree) | 0 | clean at start | PASS |
| `git diff --name-status` / `git diff --stat` (working tree) | 0 | empty at start | PASS |
| `git status --short --branch` / `git status --porcelain=v1` | 0 | branch only at start; after report, branch plus the sole report entry | see GIT |

### git diff --check

Range and working-tree `git diff --check` both exit 0 with no output. Final status after writing this report: `?? docs/enterprise/replay-1.16.0/B5_C_REVIEW.md` only.

## NOT_RUN

- Full ESLint: NOT_RUN — short-circuited inside `pnpm check` by the exact accepted five-file `vp check` B1 baseline, matching the established repository limitation.
- Browser/E2E: NOT_RUN — B5-C is a client-rendered feature stage; plan §9 browser checklist belongs to the later full-frontend regression gate.
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

- Final worktree/index status: only `?? docs/enterprise/replay-1.16.0/B5_C_REVIEW.md` (this report) is dirty. All 23 reviewed product/test files and every denylisted path are untouched.
- `git diff --check`: exit 0, no output.
- Commit: **NOT_COMMITTED**.
- Amend: **NOT_AMENDED**.
- Push: **NO_PUSH**.
- No Fixer, Rereviewer, Builder, PR, or other Agent created. `B5_C_FIXER_NOT_STARTED`.

## GATE

```text
CHANGES_REQUIRED
open P0/P1/P2 findings = 0/1/1
B5_C_FIXER_NOT_STARTED
```

- Scope is exactly the approved 23 files (3389 insertions, diff SHA-256 `f103d715…`), and all behavior/type evidence is complete: focused Vitest 37/37, direct `./node_modules/.bin/vp check` PASS on all 23 files, `pnpm --dir web type-check` PASS, and `pnpm check` reproduces only the accepted five-file B1 baseline (ESLint short-circuited → NOT_RUN). The literal `pnpm exec vp check` node-shim failure is the accepted baseline limitation, recorded separately.
- Two open findings block acceptance:
  - **B5CR-01 (P1)** — `marketplace-filters.tsx:84-86`: the browse category "All" option is dead because `onValueChange` guards on truthy `nextCategory` and Base UI fires `""` for the `value=""` item; the category filter cannot be reset to All from the UI. Finding-scoped repair boundary: `marketplace-filters.tsx` only.
  - **B5CR-02 (P2)** — `admin-review-page.tsx`: no `platformAdminMutationSupportedAtom` consumption; approve/reject/unlist stay enabled and no RBAC notice renders when `mutation_supported=false`, contrary to plan §4/§7 and the B5-B precedent. Finding-scoped repair boundary: `admin-review-page.tsx` only.
- No unauthorized write or external-state action was performed. Only this report is preserved dirty for coordinator inspection. A finding-scoped Fixer may be authorized for the two files above, followed by an independent Rereviewer running the full B5-C focused set.

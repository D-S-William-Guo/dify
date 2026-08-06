# Dify Enterprise 1.16.0 Replay B5-D App-Card First-Submit Entry + Dialog — Independent Review

## RECOVERY

- Expected/actual branch: `ctyun/replay-116-b5-d-reviewer` / `ctyun/replay-116-b5-d-reviewer` — PASS.
- Expected/actual HEAD: `06279393ed992f8f2c5d518110b1e595bf6fe43f` / `06279393ed992f8f2c5d518110b1e595bf6fe43f` — PASS.
- Start status: `## ctyun/replay-116-b5-d-reviewer`; porcelain empty — clean worktree and index.
- Range contains exactly one commit: `git rev-list --count 1385ef5d..06279393` = 1; `06279393` has sole parent `1385ef5dbfce490ef8d224bb2f3a7838646b9046`; subject `feat: add enterprise B5-D app-card first-submit entry`.
- No recovery or repair operation was performed.

## SCOPE

- Exact range: `1385ef5dbfce490ef8d224bb2f3a7838646b9046..06279393ed992f8f2c5d518110b1e595bf6fe43f`.
- `git diff --name-status`: exactly 4 paths, the approved B5-D allowlist only:

```text
M  web/app/components/apps/__tests__/app-card.spec.tsx
M  web/app/components/apps/app-card.tsx
A  web/features/enterprise-marketplace/__tests__/submit-marketplace-dialog.spec.tsx
A  web/features/enterprise-marketplace/submit-marketplace-dialog.tsx
```

- `git diff --stat`: `4 files changed, 604 insertions(+), 1 deletion(-)`.
- `git diff --check` (range): exit 0, no whitespace errors.
- Diff SHA-256: `git diff --binary ... | sha256sum` = `bf30dda58420e3ba6d7515770199628b6d8f1b29f44fe43074d089783b55bacb`, exactly matching the accepted committed-diff measurement.
- No path outside the allowlist; no B5-C `resubmit-*` write, no client/main-nav/explore/account-setting/i18n/contract/API/Docker/lockfile/manifest change.

### Sources read

1. `docs/enterprise/replay-1.16.0/CURRENT_STATE.md` (complete)
2. `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` (complete, all sections; §4/§5/§6/§8.4/§9/§10/§11/§12)
3. `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN_REVIEW.md`, `B5_IMPLEMENTATION_PLAN_REREVIEW.md`, `B5_CONTRACT_FIX_REREVIEW.md`, `B5_E_I18N_REVIEW.md`, `B5_A_REVIEW.md`, `B5_B_REVIEW.md`, `B5_C_REVIEW.md`, `B5_C_REREVIEW.md`
4. `web/AGENTS.md`, `web/docs/test.md`, `web/docs/lint.md`
5. `.agents/skills/frontend-code-review/SKILL.md` and its rule packs (`dify-ui.md`, `component-architecture.md`, `data-query-contracts.md`, `testing.md`, `accessibility-ui.md`, `dify-invariants.md`, `code-quality.md`, `performance.md`)
6. `.agents/skills/frontend-testing/SKILL.md`, `.agents/skills/how-to-write-component/SKILL.md`, `.agents/skills/karpathy-guidelines/SKILL.md`
7. All 4 reviewed files (HEAD) plus the range diff; the B5-C `resubmit-marketplace-dialog.tsx` / `resubmit-action.tsx` / `errors.ts` siblings for pattern comparison
8. Generated contracts: `packages/contracts/generated/api/console/apps/types.gen.ts` (`MarketplaceSubmissionPayload`, `MarketplaceAssetResponse`)
9. `web/service/client.ts` shared `enterpriseMarketplace.submissions.post.mutationOptions` (B5-A owner, git-blame `683f98c8e2d`)
10. `api/controllers/console/enterprise_marketplace.py` (POST submissions route) and `api/controllers/console/wraps.py` (`edit_permission_required`)
11. `web/utils/permission.ts`, `web/test/i18n-mock.ts`, `web/vitest.setup.ts`, `packages/dify-ui/src/field/index.tsx`, `packages/dify-ui/src/button/index.tsx`
12. `web/i18n/en-US/common.json` (read-only) — all consumed keys verified present and matching §8.4

## FINDINGS

### B5DR-01 — P2 — App-card first-submit entry is not gated on the submit/edit permission the mutation enforces

- File/lines: `web/app/components/apps/app-card.tsx:617` (`AppCardActionBar`) and `:1104` (`AppCard`): `const shouldShowSubmitMarketplaceOption = true`; consequential `shouldShowOperationsMenu` addition at `:618-626` / `:1105-1113`.
- Evidence:
  - The mutation this entry triggers is `POST /apps/{app_id}/enterprise-marketplace/submissions`, decorated `@edit_permission_required` (`api/controllers/console/enterprise_marketplace.py:394`). In non-RBAC deployments that decorator rejects any account without edit permission (`api/controllers/console/wraps.py:416-430`, `current_user.has_edit_permission` → `Forbidden`).
  - The frontend already derives the exact matching signal: `appACLCapabilities.canEdit` (app-card.tsx:606 / 1094).
  - The Builder's own test asserts the over-exposure: `web/app/components/apps/__tests__/app-card.spec.tsx:2339-2356` renders an app with `permission_keys: [AppACLPermission.ViewLayout]` and asserts "Submit to Marketplace" is shown even though that user holds no edit permission. For such users `shouldShowOperationsMenu` now renders the "more" menu on cards where it previously did not (all `shouldShow*Option` were false before this change).
- Violated invariant: plan §4 ties the same submit mutation to "submit/edit permission for mutation"; the task checklist requires `shouldShowSubmitMarketplaceOption=true` to be evaluated against §4/§9 and honestly classified. Honest classification: this is **not a security leak** — the server is authoritative, a 403 is mapped to `enterpriseMarketplace.errors.permissionDenied` in the dialog, and in RBAC mode the backend decorator is a no-op, so `= true` matches the RBAC-mode backend. It is a permission-visibility mismatch: in non-RBAC deployments view-only users are offered a guaranteed-403 action and the card chrome gains a menu they cannot use. Server-authoritative gating therefore does not by itself make the unconditional entry PASS.
- Repair boundary: gate the entry on the same signal the mutation requires, e.g. `shouldShowSubmitMarketplaceOption = appACLCapabilities.canEdit` in both `AppCardActionBar` and `AppCard`, and keep server-side enforcement unchanged. Files in scope: `app-card.tsx` (and the two app-card tests that assert the ungated behavior).

### B5DR-02 — P2 — First-submit dialog retains stale draft and error state across open/close cycles

- File/lines: `web/features/enterprise-marketplace/submit-marketplace-dialog.tsx:32-37` (five `useState` drafts + `submissionError`) with the always-mounted, key-less dialog at `web/app/components/apps/app-card.tsx:840-844` and `:1503-1507`.
- Evidence: `onOpenChange(false)` only flips `open`; nothing resets `title/category/description/scenario/tags/submissionError` on close or on reopen. After a successful submit, a cancel, or a failed submit the previous draft and any `submissionError` reappear the next time the dialog opens. The accepted B5-C resubmit dialog avoids exactly this with a keyed remount at its caller (`web/features/enterprise-marketplace/resubmit-action.tsx:28-33`, `key={String(open)}`), and plan §6 state matrix requires `close/reset local` for "dialog open、field draft".
- Violated invariant: plan §6 ("单 surface 生命周期；close/reset local"); stale-draft-on-reopen footgun (a user reopening after a successful or cancelled submit sees the old content as if the form were fresh, and may resubmit stale copy).
- Repair boundary: reset the five draft fields and `submissionError` when `open` transitions false→true (keyed remount at the app-card call sites, matching the B5-C pattern, or an internal `open` transition reset). Both `submit-marketplace-dialog.tsx` and `app-card.tsx` are B5-D-owned files, so the fix is in scope.

### P3 observations (non-gating)

- `submit-marketplace-dialog.tsx:71-76`: an unknown-kind mutation error (including the reachable generated `400`) sets `submissionError` to `null`, leaving the dialog open with no visible message. This is the same plan-vs-inventory tension the B5-C reviewer already recorded as non-gating (`B5_C_REVIEW.md:92`): §8.4 contains no generic mutation-error key and B5-D may not add keys. Fail-safe (dialog stays open, no auto-replay), non-gating.
- `app-card.tsx:242-243`: the menu item reuses `enterpriseMarketplace.submitDialog.title` ("Submit to Marketplace") as its label; §8.4 has no dedicated menu-item key and B5-D may not add one. Consistent with the approved inventory; accepted.
- `app-card.tsx:194`: `hasSubmitGroup = shouldShowSubmitMarketplaceOption` is a redundant alias; harmless and consistent with the existing `hasEditGroup` style.

## REVIEW

### A. Scope and architecture — PASS

Exactly the approved 4-file allowlist (604 insertions / 1 deletion, diff SHA-256 `bf30dda5...`). No B5-C `resubmit-*` write or dependency: the app-card imports only `submit-marketplace-dialog.tsx`, and `resubmit-action.tsx`/`resubmit-marketplace-dialog.tsx` are untouched. No direct `fetch`, no handwritten DTO/error type (the dialog reuses the B5-C `mapMarketplaceError` guard over the generated `UnauthorizedResponse`/`MarketplaceErrorResponse`/operation-error unions), no legacy app-context/contract loader, no duplicate shared invalidation, and no locale/contract/API/Docker change.

### B. App-card entry — mixed

- The entry opens only `SubmitMarketplaceDialog`; no resubmit is offered from the app-card (verified by `app-card.spec.tsx:2358-2375` asserting both `resubmitDialog.title` and `submissions.resubmit` are absent).
- The menu handler follows the existing close-then-microtask pattern (`handleShowSubmitMarketplace`, app-card.tsx:466-471 / 957-962), matching `handleShowEditModal` etc.
- Separator logic is correct for every combination: `(hasSubmitGroup || hasEditGroup)` places the separator after the Submit/Edit group only when a following group exists; a lone Submit item renders without a trailing separator.
- Both branches (`AppCardOperationsMenuContent` webapp_auth path and `AppCardOperationsMenu` non-auth path) receive the new props and render through the same `AppCardOperationsMenu`, so no path misses the entry.
- **Exception:** `shouldShowSubmitMarketplaceOption = true` is unconditional — B5DR-01.

### C. Submit dialog — PASS (behavior)

- First-submit only: body omits `expected_row_version` (generated `MarketplaceSubmissionPayload.expected_row_version?: number | null`, `apps/types.gen.ts:556`); the spec asserts `expect(submitCall.body).not.toHaveProperty('expected_row_version')`.
- Consumes only the generated `consoleQuery.apps.byAppId.enterpriseMarketplace.submissions.post.mutationOptions()` (submit-marketplace-dialog.tsx:39-41).
- No optimistic update (`onMutate`/`onRollback` absent); `retry: false` comes from the shared B5-A defaults.
- No component-side invalidation: success invalidation remains solely in B5-A `web/service/client.ts:462-480` (`enterpriseMarketplace.submissions.get` + `platformAdmin.enterpriseMarketplace.assets.get`), git-blame `683f98c8e2` (B5-A). The dialog's `onSuccess` only toasts and closes.
- Unknown/400 errors keep the dialog open with no invented message and no auto-replay (`mapped.kind === 'unknown' ? null : ...`), matching the accepted B5-C dialogs.

### D. Form/UI — PASS

- Required `title`/`category` carry visible `FieldLabel` + `FieldError match="valueMissing"`; the confirm button is disabled via `hasError` and `isPending` (`isPending || hasError`), with a matching guard at the top of `handleSubmit` (duplicate-submit protection, verified by the pending spec).
- All overlays/controls come from `@langgenius/dify-ui/*` (`dialog`, `field`, `button`, `toast`); native `<form onSubmit>` boundary; `Dialog` + `DialogContent backdropProps={{ forceRender: true }}` match the accepted B5-C dialog; no legacy modal/portal/call-site `z-*`.
- Accessible names come from `FieldLabel` → Base UI `Field.Control` textboxes; `Button` provides standard `focus-visible` rings and the Base UI `aria-disabled` during `loading` (verified in `packages/dify-ui/src/button/index.tsx:125-126`).
- B5DR-02 is the one form-state defect (stale state across reopen).

### E. i18n — PASS

All consumed keys are in the approved §8.4 inventory and exist in `web/i18n/en-US/common.json` (verified read-only): `enterpriseMarketplace.submitDialog.{title,description,cancel,confirm,success}`, `enterpriseMarketplace.detail.{title,category,description,scenario,tags}`, and `enterpriseMarketplace.errors.conflict` (via `errors.ts`). The test-only `resubmitDialog.title` and `submissions.resubmit` keys also exist and are only asserted for absence. No locale write; no hardcoded user copy (all user-facing strings go through `t`).

### F. Tests — PASS

- app-card spec (4 new tests): first-submit entry visible, opens the dialog (`findByRole('dialog')`), visible when no other operation is permitted, and no resubmit offered. Uses semantic queries only.
- submit dialog spec (6 new tests): first-submit version omission, required-field disabled/enabled, success invalidation **through real generated query keys** (`consoleQuery.enterpriseMarketplace.submissions.get.key()` / `consoleQuery.platformAdmin.enterpriseMarketplace.assets.get.key()` with `getQueryState().isInvalidated`, a public TanStack API) exercising the real B5-A `onSuccess` spread through the client mock, duplicate-submit guard (`aria-disabled` + single call), 409 conflict error retention (dialog open, mapped `errors.conflict` shown), and unknown-400 no-message/no-auto-replay with a manual retry.
- The client mock is scoped to the exact `apps.byAppId.enterpriseMarketplace.submissions.post.mutationOptions` shape the dialog consumes and preserves the real `onSuccess` defaults; no source-string/AST/private-state/snapshot assertions.

### Accepted process deviations and residual risks

- `pnpm check` reproduces only the five accepted B1 formatting files and short-circuits before ESLint (ESLint NOT_RUN), matching the established repository baseline.
- The literal `pnpm exec vp check` fails solely with the known node-shim/path error (`error: Cannot find binary path for command 'node'`); the direct `./node_modules/.bin/vp check` run is recorded separately and passes.
- Browser/E2E remains NOT_RUN for this stage (plan §9 browser checklist).
- Residual risk from B5DR-01: in RBAC mode the backend `edit_permission_required` is a no-op, so the unconditional entry does not contradict the RBAC-mode backend; the finding is scoped to the non-RBAC permission mismatch and the viewer card-chrome change.

## VALIDATION

All commands were run in this review worktree with the repository's existing node/pnpm toolchain. No command wrote to the reviewed files.

| Exact command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b5-d-reviewer` | PASS |
| `git rev-parse HEAD` | 0 | `06279393ed992f8f2c5d518110b1e595bf6fe43f` | PASS |
| `git status --short --branch` | 0 | clean, branch only | PASS |
| `git diff --name-status 1385ef5d..06279393` | 0 | exactly the 4 approved paths | PASS |
| `git diff --stat 1385ef5d..06279393` | 0 | `4 files changed, 604 insertions(+), 1 deletion(-)` | PASS |
| `git diff --check 1385ef5d..06279393` | 0 | no output | PASS |
| `git diff --binary 1385ef5d..06279393 \| sha256sum` | 0 | `bf30dda58420e3ba6d7515770199628b6d8f1b29f44fe43074d089783b55bacb` | PASS (matches accepted measurement) |
| `git rev-list --count 1385ef5d..06279393` | 0 | `1` (single commit, sole parent `1385ef5d`) | PASS |
| `pnpm --dir web exec vp test run 'app/components/apps/__tests__/app-card.spec.tsx' 'features/enterprise-marketplace/__tests__/submit-marketplace-dialog.spec.tsx'` | 0 | `Test Files 2 passed (2); Tests 119 passed (119)` | PASS (matches Builder 119/119) |
| `pnpm --dir web exec vp test run 'app/components/apps' 'features/enterprise-marketplace'` | 0 | `Test Files 13 passed (13); Tests 265 passed (265)` | PASS (matches Builder 265/265) |
| `pnpm exec vp check <4 exact paths>` | 1 | `error: Cannot find binary path for command 'node'` | FAIL — literal command fails solely with the known pnpm-shim/node-shadow error; direct binary fallback recorded separately |
| `./node_modules/.bin/vp check <4 exact paths>` | 0 | `pass: All 4 files are correctly formatted`; `pass: Found no warnings, lint errors, or type errors in 4 files` | PASS |
| `pnpm --dir web type-check` | 0 | `tsc` no diagnostics | PASS |
| `pnpm check` | 1 | `vp check` formatting issues only in the five accepted B1 files (get-automatic-res spec/component/normalizer + get-code-generator-res spec/component); `pnpm lint:eslint` short-circuited | ACCEPTED_LIMITATION (B1 baseline); ESLint NOT_RUN |
| `git diff --check` (working tree) | 0 | clean | PASS |
| `git diff --name-status` / `git diff --stat` (working tree) | 0 | empty | PASS |
| `git status --porcelain=v1` / `git status --short --branch` | 0 | clean until this report | PASS |

### git diff --check

`git diff --check` (range and working tree) exits 0 with no output. Final status after writing this report: `?? docs/enterprise/replay-1.16.0/B5_D_REVIEW.md` only. The report file is not staged.

## NOT_RUN

- Full ESLint: NOT_RUN — short-circuited inside `pnpm check` by the exact accepted five-file `vp check` B1 baseline, matching the established repository limitation.
- Browser/E2E: NOT_RUN — plan §9 browser checklist belongs to the later full-frontend regression/browser gate; B5-D is a component-level surface.
- Contract generation: NOT_RUN — prohibited.
- Backend/API tests: NOT_RUN — no backend change in this range.
- Database/migration/Redis/vector/Docker/runtime/offline/volume/upgrade/rollback: NOT_RUN.
- External systems, containers, volumes, remotes, production state: not modified.

## GIT

- Final worktree/index status: only `?? docs/enterprise/replay-1.16.0/B5_D_REVIEW.md` (this report) is dirty. All 4 reviewed product/test files and every denylisted path are untouched.
- Staged content: none (`git diff --cached --name-status` empty).
- `git diff --check`: exit 0, no output, including the report's worktree content.
- Commit: **NOT_COMMITTED**.
- Amend: **NOT_AMENDED**.
- Push: **NO_PUSH**.
- No Fixer, Rereviewer, Builder, PR, or other Agent created. `B5_D_FIXER_NOT_STARTED`.

## GATE

```text
CHANGES_REQUIRED
open P0/P1/P2 findings = 0/0/2   (B5DR-01, B5DR-02)
B5_D_FIXER_NOT_STARTED
```

- Scope is exactly the approved 4 files (604/1, diff SHA-256 `bf30dda5...`), single reviewed commit `06279393` with sole parent `1385ef5d`.
- All behavioral, i18n, contract, and test evidence is complete: focused Vitest 119/119, related 265/265, direct `./node_modules/.bin/vp check` PASS, `pnpm --dir web type-check` PASS, and `pnpm check` reproduces only the accepted five-file B1 baseline (ESLint NOT_RUN).
- Two P2 findings require a finding-scoped Fixer before re-review: B5DR-01 (unconditional submit entry not gated on the mutation's edit permission; server-authoritative gating is safe but not a PASS on its own) and B5DR-02 (first-submit dialog retains stale draft/error across reopen, contradicting plan §6 and the B5-C reset pattern).
- No unauthorized write or external-state action was performed. Only this report is preserved dirty for coordinator inspection.

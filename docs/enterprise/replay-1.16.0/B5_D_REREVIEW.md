# Dify Enterprise 1.16.0 Replay B5-D App-Card First-Submit Entry + Dialog — Independent Rereview

## RECOVERY

- Expected/actual branch: `ctyun/replay-116-b5-d-rereviewer` / `ctyun/replay-116-b5-d-rereviewer` — PASS.
- Expected/actual HEAD: `35468cd742299d96506e280babd36f068e565fd4` / `35468cd742299d96506e280babd36f068e565fd4` — PASS.
- Start status: `## ctyun/replay-116-b5-d-rereviewer`; `git status --porcelain=v1` empty — clean worktree and index.
- Fixer range: `f0d72492f809392c598deb7220e4d87a21cb14f9..35468cd742299d96506e280babd36f068e565fd4`; commit metadata: `commit=35468cd742299d96506e280babd36f068e565fd4`, `parent=f0d72492f809392c598deb7220e4d87a21cb14f9`, `subject=fix: resolve B5-D review findings`. Range contains exactly this one commit (`git rev-list --count f0d72492..35468cd` = 1).
- Chain: `1385ef5d` (B5-C rereview) → `06279393` (B5-D builder) → `f0d72492` (B5-D review report) → `35468cd` (B5-D fixer).
- Recovery preflight completed before any review-source read or report creation. No recovery or repair operation was performed. No commit/amend/push occurred.

## SCOPE

- `git diff --name-status f0d72492f809392c598deb7220e4d87a21cb14f9..35468cd742299d96506e280babd36f068e565fd4`: exactly 2 `M` paths, both within the finding-scoped repair boundaries:

```text
M  web/app/components/apps/__tests__/app-card.spec.tsx   (5 insertions / 8 deletions)
M  web/app/components/apps/app-card.tsx                  (4 insertions / 2 deletions)
```

- `git diff --stat`: `2 files changed, 9 insertions(+), 10 deletions(-)` — exactly the required 9 insertions and 10 deletions.
- `git diff --numstat`: `5 8 web/app/components/apps/__tests__/app-card.spec.tsx`; `4 2 web/app/components/apps/app-card.tsx`.
- `git diff --check` (range): exit 0, no whitespace errors.
- `git diff --binary ... | sha256sum` = `2dd512fcc5054eeaaed28e53f1060ec5db1ed2e684d9b109464591612852426c`, exactly matching the known Fixer diff measurement.
- `git diff --name-status 1385ef5dbfce490ef8d224bb2f3a7838646b9046..35468cd742299d96506e280babd36f068e565fd4` (base → HEAD): exactly the 4 approved B5-D allowlist paths plus `docs/enterprise/replay-1.16.0/B5_D_REVIEW.md` (5 total); no denylisted path (no i18n/locale/contract/API/Docker/lockfile/resubmit-* change).
- Known evidence independently re-derived: builder diff SHA `bf30dda58420e3ba6d7515770199628b6d8f1b29f44fe43074d089783b55bacb` (1385ef5d..06279393) — matches; review report SHA `ba39b055db10a3eb387e26280588b0fc3ca49db46dd44ab0a041aa20fd684657` (`git show f0d72492:docs/enterprise/replay-1.16.0/B5_D_REVIEW.md | sha256sum`) — matches; fixer diff SHA `2dd512fc...` — matches.

### Sources read

1. `docs/enterprise/replay-1.16.0/B5_D_REVIEW.md` (complete — the original review with findings B5DR-01 and B5DR-02)
2. `docs/enterprise/replay-1.16.0/B5_IMPLEMENTATION_PLAN.md` (complete; §4 page/permission matrix, §5 component matrix, §6 state matrix, §7 query/mutation matrix, §8.4 key inventory, §9 test matrix, §10 ownership, §12 serial gates, §13 stop conditions)
3. `docs/enterprise/replay-1.16.0/B5_C_REVIEW.md`, `docs/enterprise/replay-1.16.0/B5_C_REREVIEW.md` (B5-C precedent for finding disposition, keyed-remount reset pattern, and Rereview report format)
4. `web/AGENTS.md`, `web/docs/test.md`, `web/docs/lint.md`
5. `.agents/skills/frontend-code-review/SKILL.md` (and its data-query-contracts/testing/component-architecture rule packs), `.agents/skills/frontend-testing/SKILL.md`, `.agents/skills/how-to-write-component/SKILL.md`, `.agents/skills/karpathy-guidelines/SKILL.md`
6. The exact Fixer diff and the two modified files (HEAD)
7. `web/features/enterprise-marketplace/submit-marketplace-dialog.tsx` (unchanged) and `web/features/enterprise-marketplace/resubmit-action.tsx` (B5-C keyed-remount precedent, `key={String(open)}` at line 29)
8. `web/utils/permission.ts` (`getAppACLCapabilities` derivation of `canEdit`)
9. B5-D specs (read-only, unchanged except the single disposition test): `app-card.spec.tsx`, `submit-marketplace-dialog.spec.tsx`

## FINDINGS

Open P0/P1/P2 counts: `0/0/0`.

No P0/P1/P2 findings. The two original findings are independently verified disposed:

### B5DR-01 DISPOSITION — CLOSED

- Original finding (P2): `shouldShowSubmitMarketplaceOption = true` in both `AppCardActionBar` and `AppCard` offered a guaranteed-403 submit action to view-only users in non-RBAC deployments, and added a `shouldShowOperationsMenu` "more" menu on cards that previously had none; the mutation is `@edit_permission_required`. Repair boundary: gate on `appACLCapabilities.canEdit` in both components, keep server-side enforcement unchanged.
- Fixer change (HEAD):
  - `app-card.tsx:617` (`AppCardActionBar`): `const shouldShowSubmitMarketplaceOption = appACLCapabilities.canEdit`.
  - `app-card.tsx:1105` (`AppCard`): `const shouldShowSubmitMarketplaceOption = appACLCapabilities.canEdit`.
  - `app-card.tsx:606/1095` `shouldShowEditOption` already uses the same `canEdit` signal, so the submit entry is now exactly aligned with the edit group and the mutation's edit-permission requirement.
  - `app-card.spec.tsx:2339-2353`: the ViewLayout-only test was rewritten from "should show the submit option when no other operations are permitted" (which asserted over-exposure) to "should not show the submit option for a viewer without edit permission", and now asserts the submit entry AND the operations menu are absent: `expect(screen.queryByTestId('dropdown-menu-trigger')).not.toBeInTheDocument()` (operations menu absent) and `expect(screen.queryByText('common.enterpriseMarketplace.submitDialog.title')).not.toBeInTheDocument()` (submit entry absent), plus the pre-existing `app.editApp` absence assertion. The test renders an app owned by `another-user` with `permission_keys: [AppACLPermission.ViewLayout]` and `workspacePermissionKeys = []`, which exercises the non-maintainer, non-editor path (verified against `web/utils/permission.ts:117-139`: `canEdit` = `hasResourcePermission(keys, Edit, hasMaintainerPermissions=false)` = false for ViewLayout-only, and the viewer is not the maintainer).
  - The `dropdown-menu-trigger` testid is applied by the spec's DropdownMenu mock to the trigger (`app-card.spec.tsx:413`), which is rendered only inside `{shouldShowOperationsMenu && <DropdownMenu>}` (`app-card.tsx:665` and `:1316`), so the absence assertion is a direct check that `shouldShowOperationsMenu` collapsed for the viewer.
  - Both `AppCardOperationsMenu` branches (`systemFeatures.webapp_auth.enabled` → `AppCardOperationsMenuContent` wrapper, and the direct non-auth `AppCardOperationsMenu`) receive the gated flag unchanged and render it through the shared `hasSubmitGroup` (`app-card.tsx:194`).
- Server-side enforcement unchanged: the Fixer range contains no `api/**` path; `@edit_permission_required` on `POST /apps/{app_id}/enterprise-marketplace/submissions` is untouched.
- Reading scope: the fix is contained to `app-card.tsx` and `app-card.spec.tsx` as the repair boundary required. **DISPOSED.**

### B5DR-02 DISPOSITION — CLOSED

- Original finding (P2): `SubmitMarketplaceDialog` retained stale draft/error state across open/close cycles because the five `useState` drafts + `submissionError` were only reset by unmount, but the dialog was always mounted with a key-less call site. Repair boundary: keyed remount at both app-card call sites matching the B5-C pattern, or an equivalent internal open-transition reset.
- Fixer change (HEAD): both call sites now remount the dialog on each open via `key={String(showSubmitMarketplace)}`:
  - `app-card.tsx:840-841` (`AppCardActionBar`): `<SubmitMarketplaceDialog key={String(showSubmitMarketplace)} ... />`.
  - `app-card.tsx:1504-1505` (`AppCard`): `<SubmitMarketplaceDialog key={String(showSubmitMarketplace)} ... />`.
- This matches the accepted B5-C reset pattern exactly (`resubmit-action.tsx:28-33`, `key={String(open)}`): when `showSubmitMarketplace` transitions false→true the key changes, forcing a fresh mount in which all `useState` initializers (`title/category/description/scenario/tags/submissionError`) run at their initial values. Closing (true→false) also remounts, so a subsequent open starts clean. No draft, error, or result can leak across cycles.
- `submit-marketplace-dialog.tsx` remains byte-identical (not in the Fixer range), which is explicitly permitted because the keyed remount is present at both call sites. **DISPOSED.**

## REVIEW

### A. Scope and architecture — PASS

The Fixer range is exactly the two finding-scoped files with the exact required magnitude (9 insertions / 10 deletions, diff SHA-256 `2dd512fc...`). No scope expansion: no i18n key added, no locale/i18n/contract/API/Docker/lockfile/test-file-with-new-tests change, and no other B5-C/B5-A/B5-D path was touched. `git diff --name-status 1385ef5d..35468cd` shows exactly the 4 approved B5-D allowlist paths plus the original review report — no denylisted path. The existing `submit-marketplace-dialog.spec.tsx` (314 lines, unchanged) still passes; the only spec modification is the B5DR-01 disposition test.

### B. B5DR-01 disposition — PASS

The submit entry is now gated on `appACLCapabilities.canEdit` in both `AppCardActionBar` and `AppCard`, matching the `@edit_permission_required`-enforced mutation and the existing `shouldShowEditOption` signal. For a ViewLayout-only, non-maintainer viewer, `canEdit=false` collapses `shouldShowOperationsMenu` entirely (no other option is available for such a user), so both the "more" menu and the submit entry disappear — verified by the rewritten test asserting `dropdown-menu-trigger` and `submitDialog.title` absence. Editors (`AppACLPermission.Edit`, or maintainer/creator) still see the entry (the existing "should show the first-submit marketplace option in the operations menu" and "should open the first-submit marketplace dialog" tests use the default `mockApp` and pass). Server-authoritative enforcement is unchanged; the frontend signal now matches the backend gate. No regression.

### C. B5DR-02 disposition — PASS

The `key={String(showSubmitMarketplace)}` remount at both call sites reproduces the accepted B5-C reset pattern. The dialog component is unchanged, which is allowed only because the keyed remount is present at both call sites (verified at `app-card.tsx:840-841` and `:1504-1505`). Stale draft/error cannot survive an open/close cycle. The unchanged `submit-marketplace-dialog.spec.tsx` (success invalidation, required-field disabled, duplicate-submit guard, 409 retention, unknown-400 no-message) passes unmodified, confirming no behavior regression inside the dialog.

### D. Regression and conformance — PASS

- All 119 focused B5-D tests pass on the fixer HEAD (see VALIDATION), including the rewritten viewer test and the 4 submit-entry tests.
- The related 265-test set (13 files) passes, confirming no regression across the `app/components/apps` and `features/enterprise-marketplace` suites.
- Type-check passes, confirming `appACLCapabilities.canEdit` and the `key` prop type-check against unchanged sources.
- vp check passes on all 4 B5-D files (direct binary).
- The three original P3 observations from B5_D_REVIEW (unknown-kind mutation error → `null` message, menu-item label reuse of `submitDialog.title`, redundant `hasSubmitGroup` alias) are outside the fixer scope and remain non-gating; the Fixer did not regress them.

### E. Tests and evidence quality — PASS

The Fixer modified exactly the one test that asserted the ungated behavior, converting it into the required absence regression test (operations menu absent + submit entry absent for a ViewLayout-only viewer). The other app-card tests and the entire submit-marketplace-dialog spec are untouched and pass. Coverage notes (non-gating): the keyed-remount reset is verified by code inspection and the B5-C precedent rather than a dedicated reopen test; the B5DR-01 absence behavior is now directly asserted.

## VALIDATION

All commands ran in an isolated task environment extracted from the exact HEAD via `git archive 35468cd742299d96506e280babd36f068e565fd4` under `/home/ctyun/BigData/.system-data/tmp/opencode/b5d-rereview/source`, with a frozen offline install (`pnpm install --frozen-lockfile --store-dir /home/ctyun/BigData/.pnpm-store`, Node 22.22.2 first in PATH via `/home/ctyun/BigData/.nvm/versions/node/v22.22.2/bin`, pnpm 11.10.0). Lockfile hash before/after install `62f3e0f3639dd80d1d058cae38a3dca53fc5b626fb2e6bec446a0aa397148ee7` (unchanged). The isolated environment will be deleted after validation; no command wrote to the review worktree.

| Exact command | Exit | Result | Classification |
| --- | ---: | --- | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b5-d-rereviewer` | PASS |
| `git rev-parse HEAD` | 0 | `35468cd742299d96506e280babd36f068e565fd4` | PASS |
| `git status --short --branch` / `--porcelain=v1` (start) | 0 | branch only, empty | PASS |
| `git diff --name-status f0d72492..35468cd` | 0 | exactly the 2 approved `M` paths | PASS |
| `git diff --stat f0d72492..35468cd` | 0 | `2 files changed, 9 insertions(+), 10 deletions(-)` | PASS |
| `git diff --check f0d72492..35468cd` | 0 | no output | PASS |
| `git diff --binary f0d72492..35468cd \| sha256sum` | 0 | `2dd512fcc5054eeaaed28e53f1060ec5db1ed2e684d9b109464591612852426c` | PASS (matches the known Fixer diff measurement) |
| `git diff --name-status 1385ef5d..35468cd` | 0 | 4 approved B5-D `A`/`M` paths + `B5_D_REVIEW.md`; no denylisted path | PASS |
| `git rev-list --count f0d72492..35468cd` | 0 | `1` (single commit, sole parent `f0d72492`) | PASS |
| `pnpm --dir web exec vp test run 'app/components/apps/__tests__/app-card.spec.tsx' 'features/enterprise-marketplace/__tests__/submit-marketplace-dialog.spec.tsx'` | 0 | `Test Files 2 passed (2); Tests 119 passed (119)` | PASS (matches Builder 119/119) |
| `pnpm --dir web exec vp test run 'app/components/apps' 'features/enterprise-marketplace'` | 0 | `Test Files 13 passed (13); Tests 265 passed (265)` | PASS (matches Builder 265/265) |
| `pnpm --dir web exec vp check <4 exact paths>` | 2 | `Formatting could not start … Expected at least one target file. All matched files may have been excluded by ignore rules.` | FAIL — literal command fails with the known path-resolution error under `--dir web` with `web/`-prefixed args; direct binary run recorded separately (accepted baseline limitation) |
| `./node_modules/.bin/vp check <4 exact paths>` (from exact-HEAD source root, same `web/`-prefixed args) | 0 | `pass: All 4 files are correctly formatted`; `pass: Found no warnings, lint errors, or type errors in 4 files` | PASS |
| `pnpm --dir web type-check` | 0 | `tsc` no diagnostics | PASS |
| `pnpm check` | 1 | `vp check` reports formatting issues in exactly the five accepted B1 files (get-automatic-res spec/component/normalize-generator-model + get-code-generator-res spec/component); `pnpm lint:eslint` short-circuited | ACCEPTED_LIMITATION (B1 baseline); ESLint NOT_RUN |
| `git diff --check` (working tree) | 0 | clean at start | PASS |
| `git diff --name-status` / `git diff --stat` (working tree) | 0 | empty at start | PASS |
| `git status --short --branch` / `git status --porcelain=v1` | 0 | branch only at start; after report, branch plus the sole report entry | see GIT |

### git diff --check

Fixer range and working-tree `git diff --check` both exit 0 with no output. Final status after writing this report: `?? docs/enterprise/replay-1.16.0/B5_D_REREVIEW.md` only.

## NOT_RUN

- Full ESLint: NOT_RUN — short-circuited inside `pnpm check` by the exact accepted five-file `vp check` B1 baseline, matching the established repository limitation.
- Browser/E2E: NOT_RUN — B5-D is a component-level surface; plan §9 browser checklist belongs to the later full-frontend regression gate.
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
- New regression tests for the two fixes beyond the single rewritten disposition test: NOT_RUN — additional test-file changes are not required by the disposition and would exceed the minimal fixer scope.

## GIT

- Final worktree/index status: only `?? docs/enterprise/replay-1.16.0/B5_D_REREVIEW.md` (this report) is dirty. All 4 reviewed product/test files and every denylisted path are untouched.
- `git diff --check`: exit 0, no output.
- Commit: **NOT_COMMITTED**.
- Amend: **NOT_AMENDED**.
- Push: **NO_PUSH**.
- No Fixer, Rereviewer, Builder, PR, or other Agent created.

## GATE

```text
PASS
B5_D_FIXER_ACCEPTED=yes
open P0/P1/P2 findings = 0/0/0
```

- The Fixer range is exactly the two finding-scoped files (9 insertions / 10 deletions, diff SHA-256 `2dd512fc...`), single commit `35468cd` with sole parent `f0d72492`, with no scope expansion and no denylisted path.
- B5DR-01 is disposed: `shouldShowSubmitMarketplaceOption = appACLCapabilities.canEdit` in both `AppCardActionBar` (`app-card.tsx:617`) and `AppCard` (`app-card.tsx:1105`), server enforcement unchanged, and the ViewLayout-only test now asserts both the operations menu (`dropdown-menu-trigger` absent) and the submit entry (`submitDialog.title` absent) for a non-maintainer viewer.
- B5DR-02 is disposed: `key={String(showSubmitMarketplace)}` at both `SubmitMarketplaceDialog` call sites (`app-card.tsx:840-841` and `:1504-1505`), matching the accepted B5-C `key={String(open)}` reset pattern; `submit-marketplace-dialog.tsx` is unchanged as permitted.
- Full focused evidence is complete: Vitest 119/119, related 265/265, direct `./node_modules/.bin/vp check` PASS on all 4 B5-D files, `pnpm --dir web type-check` PASS, and `pnpm check` reproduces only the accepted five-file B1 baseline (ESLint short-circuited → NOT_RUN). The literal `pnpm --dir web exec vp check` failure is the accepted literal-command baseline limitation, recorded separately from the passing direct binary run.
- No unauthorized write or external-state action was performed. Only this report is preserved dirty for coordinator inspection. No commit/amend/push occurred.

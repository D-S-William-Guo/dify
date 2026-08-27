# Marketplace Replay P2 Rereview — 2026-08-27

## Immutable target

| Item | Value |
| --- | --- |
| Candidate branch | `codex/enterprise-candidate-1.16.0-20260718` |
| Reviewed range | `066de763913ddc2189b42e5324145c46964ee58e..62bd85f5fc0a2bed4f43faf18427458dc15ab293` |
| Rereviewer | `replay-116-p2-rereview-20260826` (`codex-sol`) |
| Verdict | **PASS** |

The rereviewer made no repository, container, database, remote, production, or gray-environment change.

## Finding dispositions

| Finding | Invariant and evidence | Disposition |
| --- | --- | --- |
| P2-A | Submit (`:627`), approve (`:668`), and reject (`:707`) controller tests assert expected public `asset_id` and absence of persistence key `id`. | **CLOSED — PASS** |
| P2-B | Main-navigation test (`web/app/components/main-nav/__tests__/index.spec.tsx:724`) covers non-admin absence, platform-admin link to `/platform-admin/enterprise-marketplace`, review-route active state, and workspace-admin mutual exclusion. | **CLOSED — PASS** |

Only these two test files changed in the reviewed range. No production API, route, navigation implementation, i18n, docs, or generated contract changed.

## Verification

| Check | Result |
| --- | --- |
| `git diff 066de...62bd --check` | PASS |
| Marketplace runtime pytest (`-k 'not openapi'`) | `69 passed, 7 deselected, 0 failed` |
| Full main-navigation suite on an identical clean checkout at the same SHA | `53 passed, 0 failed` |
| P2-B test isolated by name | `1 passed, 52 skipped` |
| Rereviewer worktree final status | clean |

The exact frontend command in the isolated rereview worktree was **NOT_RUN** before Vitest because pnpm could not create its unavailable home-store path. The identical clean checkout had matching relevant file blobs and ran the full suite successfully with the native Vite config loader; this supplies the behavioral evidence without modifying the rereview worktree.

The previously observed spacing-test variation did not reproduce in rereview and is not attributed to the Fixer.

## Accepted limitations

- Seven OpenAPI checks remain **NOT_RUN** because the ignored generated fixture `packages/contracts/openapi/console-openapi.json` is absent. It was not generated.
- Browser/screenshot verification was **NOT_RUN** for this test-only rereview. Existing browser acceptance evidence remains in `UPGRADE_REHEARSAL_VALIDATION_2026-08-18.md`; this change does not alter runtime UI behavior.

## Gate

The P2 test-evidence repair is closed locally at `62bd85f5fc0a2bed4f43faf18427458dc15ab293`. A future push, deployment, production/gray connection, or Claude Squad instance cleanup requires separate explicit approval.

# Marketplace Replay Review — 2026-08-26

## Immutable review target

| Item | Value |
| --- | --- |
| Candidate branch | `codex/enterprise-candidate-1.16.0-20260718` |
| Reviewed HEAD | `4466f439015e894b622025391b307c42b80212be` |
| Reviewed implementation range | `261ba37959..82b48543c0` |
| Reviewer instance | `replay-116-review-20260825` (`codex-sol`) |
| Verdict | **CHANGES_REQUIRED** |

The reviewer made no repository, remote, container, database, or production changes.

## Accepted release-preparation findings

### P2-A — response tests must protect the public DTO contract

- **Location:** `api/tests/unit_tests/controllers/console/test_enterprise_marketplace.py:596`
- **Invariant:** marketplace responses expose `asset_id`, never persistence field `id`.
- **Evidence:** test fixtures now model the entity's real `id`, but submit, approve, and reject tests discard their response payloads. A future serialization regression would therefore pass those tests.
- **Required repair boundary:** assert the expected `asset_id` and absence of `id` in each affected public response. Do not change API behavior.

### P2-B — admin review navigation needs behavioral coverage

- **Location:** `web/app/components/main-nav/routes.ts:108`
- **Invariant:** `审核应用` is visible and clickable only for platform administrators, points to `/platform-admin/enterprise-marketplace`, and is active only for that route; workspace administration must not be active there.
- **Evidence:** the existing 52-test main-navigation suite did not cover the new review item. Source inspection confirmed the implementation, but its intended visibility, target, and mutually-exclusive active state lack a durable automated test.
- **Required repair boundary:** add one focused main-navigation test. Do not change navigation behavior or route definitions.

## Confirmed implementation behavior

- `MarketplaceAssetResponse.asset_id` validates from entity `id`; the shared mapper serves submit, resubmit, approve, reject, unlist, and list responses.
- `我的提交` is a visible link below `智慧广场`; `审核应用` is restricted to platform administrators and does not overlap the workspace-administration active matcher.
- `.dockerignore` excludes only local `.env` material and `docker/` from the generic build context. API/web Dockerfile-specific ignore files and the offline archive workflow retain their required inputs.

## Independent verification evidence

| Check | Result |
| --- | --- |
| Review worktree preflight at reviewed SHA | PASS |
| `git diff 261ba37959..82b48543c0 --check` | PASS |
| Targeted Ruff check | PASS |
| Marketplace runtime pytest (`-k 'not openapi'`) | `69 passed, 7 deselected` |
| OpenAPI-only pytest | `7` setup errors, all blocked before assertions by missing generated `packages/contracts/openapi/console-openapi.json`; **NOT_RUN**, not an implementation failure |
| Marketplace browse frontend test with absolute `COREPACK_HOME` | `9 passed` |
| Main-navigation focused suite | `52 passed` |

The supplied frontend command using relative `COREPACK_HOME=.corepack` was **NOT_RUN** because Corepack resolved its cache beneath `web/`; the absolute-cache rerun above isolates that harness issue from product behavior.

Browser screenshot inspection was **NOT_RUN** in the isolated review worktree because ignored evidence artifacts are intentionally absent there. The reviewer did not re-run browser or external runtime validation.

## Next gate

P2-A and P2-B are accepted required release-preparation work. A finding-scoped Fixer must start from the commit containing this report, edit only the two test files, and receive separate creation authorization. No push, deployment, or production/gray connection is authorized.

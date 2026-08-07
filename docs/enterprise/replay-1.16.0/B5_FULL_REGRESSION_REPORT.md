# B5 Full Frontend Regression / Browser Gate Report

Role: code-reviewer · Instance: replay-116-b5-regression

## 0. Verdict

**PASS** — all required focused/type/i18n evidence is complete, no open P0/P1/P2 findings,
no fabricated browser results (browser/E2E honestly NOT_RUN with exact blockers), and no
unauthorized writes. The pre-existing dynamic webApps Vitest flake did NOT reproduce this run.

## 1. Candidate start verification

- Branch: `ctyun/replay-116-b5-regression`
- HEAD: `68822f521507b890ad663ef5a5affb9c2ef91b56`
- `git status --short --branch`: `## ctyun/replay-116-b5-regression` (clean)
- Base integration branch `codex/enterprise-candidate-1.16.0-20260718` resolves to the same
  SHA `68822f5215` and is an ancestor of HEAD.
- The candidate contains the accepted B5 stages and their review/rereview reports:
  - B5-E i18n foundation: `b4801a1ada` advance → `f5cf5bee66` feat → `e319481a7b` review
    (`B5_E_I18N_REVIEW.md`)
  - B5-A: `cae1b00b0c` advance → `683f98c8e2` feat → `11bae180bb` review (`B5_A_REVIEW.md`)
  - B5-B: `f912864a1a` feat → `0bc4a1e310` review (`B5_B_REVIEW.md`)
  - B5-C: `a5c1e2a336` feat → `80253fcc94` review → `1be688b81e` fix → `1385ef5dbf` rereview
    (`B5_C_REVIEW.md`, `B5_C_REREVIEW.md`)
  - B5-D: `06279393ed` feat → `f0d72492f8` review → `35468cd742` fix → `68822f5215` rereview
    (`B5_D_REVIEW.md`, `B5_D_REREVIEW.md`)
- All source-of-truth docs listed in the contract exist under `docs/enterprise/replay-1.16.0/`.

## 2. Git verification

| Command | Result |
| --- | --- |
| `git status --porcelain=v1` | 0 lines (clean) |
| `git rev-parse HEAD` | `68822f521507b890ad663ef5a5affb9c2ef91b56` |
| `git diff --name-status 80253fcc942121aa662c605b93dc54d340dd00f2..HEAD` | 3 added docs + 5 web files (B5-C rereview / B5-D scope, all allowed) |
| `git diff --check 80253fcc942121aa662c605b93dc54d340dd00f2..HEAD` | exit 0 |
| `git diff --check` (worktree) | exit 0 |
| Full B5 range `b4801a1ada^..HEAD` | Only `web/**` B5-allowlist files, the 23 `web/i18n/*/common.json`, and `docs/enterprise/replay-1.16.0/**` — no api/docker/packages/lockfile/manifest/contract/i18n-tooling/product change |

No commit, amend, or push occurred during this validation.

## 3. Vitest regression set (plan §15 exact command)

Command:

```bash
pnpm --dir web exec vp test run app/components/main-nav features/platform-admin features/enterprise-marketplace app/components/apps/__tests__/app-card.spec.tsx
```

Result:

```
 Test Files  14 passed (14)
      Tests  295 passed (295)
```

Exit 0. Exact counts: **14/14 files passed, 295/295 tests passed, 0 failed**.

The pre-existing dynamic webApps flake (`index.spec.tsx:458 explore.sidebar.webApps`) did NOT
reproduce on this run; the full set passed. Therefore no ACCEPTED_LIMITATION classification
was needed and there is no failure finding.

## 4. Type check

| Command | Result |
| --- | --- |
| `pnpm --dir web type-check` | exit 0, no output (tsc clean) |
| `pnpm --dir e2e type-check` | exit 0, no output (tsc clean) |

## 5. pnpm check

Command: `pnpm check` (root script `vp check && pnpm lint:eslint`)

Result: `vp check` failed with formatting issues in exactly the accepted five-file B1 baseline:

1. `web/app/components/app/configuration/config/automatic/__tests__/get-automatic-res.spec.tsx`
2. `web/app/components/app/configuration/config/automatic/get-automatic-res.tsx`
3. `web/app/components/app/configuration/config/automatic/normalize-generator-model.ts`
4. `web/app/components/app/configuration/config/code-generator/__tests__/get-code-generator-res.spec.tsx`
5. `web/app/components/app/configuration/config/code-generator/get-code-generator-res.tsx`

Because `vp check` exited non-zero, `pnpm lint:eslint` was short-circuited by `&&` →
**ESLint NOT_RUN** (accepted baseline). This matches the recorded B1 formatting baseline and
all prior B5 stage reports.

## 6. i18n parity (plan §8 fixed all-23-locale command)

Command:

```bash
pnpm --dir web i18n:check --file common --lang ar-TN de-DE en-US es-ES fa-IR fr-FR hi-IN id-ID it-IT ja-JP ko-KR nl-NL pl-PL pt-BR ro-RO ru-RU sl-SI th-TH tr-TR uk-UA vi-VN zh-Hans zh-Hant
```

Result: **PASS**, exit 0.

- All 23 locale difference counts are `0` (ar-TN … zh-Hant).
- All 23 "Missing keys in <locale>: []" lists are empty.
- Final line: `✅ All i18n files are in sync`.

## 7. Browser / E2E gate

### 7.1 E2E suite — NOT_RUN (exact blockers)

`pnpm --dir e2e e2e` was NOT run. Per `e2e/AGENTS.md` the suite is a CI-oriented integration
gate that tests backend-from-source, frontend-from-production-artifact, and Docker middleware.
Exact blockers observed:

1. The running Docker stack is the **1.15.0 enterprise images**, not B5 source:
   - `docker-web-1` → `dify-web-enterprise:1.15.0-enterprise` (image `sha256:ed1b6cc1…`)
   - `docker-api-1` → `dify-api-enterprise:1.15.0-enterprise`
2. The frontend production artifact is absent: `web/.next/BUILD_ID` does not exist, so the
   runner would build the web artifact into `web/.next` — a forbidden write path (`web/**`).
3. The runner writes to forbidden paths under `e2e/**` (`e2e/.logs`, `e2e/cucumber-report`,
   `e2e/.auth`) and starts the backend from source plus Celery against the live middleware
   stack, bootstrapping auth via `/install` — this mutates running containers/DB state, which
   is forbidden for a validation-only role.
4. `web/AGENTS.md` and root `AGENTS.md:18` record that integration tests are CI-only and are
   not expected to run in the local environment.

### 7.2 Plan §9 browser checklist (items 1–5) — NOT_RUN (same blockers)

| # | Checklist item | Result |
| --- | --- | --- |
| 1 | admin/non-admin login, entry, deep-link refresh, back/forward, no permission flash | NOT_RUN |
| 2 | workspace A submit → admin approve → workspace B browse/detail/copy → new app overview | NOT_RUN |
| 3 | reject, unlist, copy warnings, 409 stale, 422 validation, 503 service/RBAC unavailable | NOT_RUN |
| 4 | keyboard open menu/dialog, Tab focus, Escape close, duplicate Enter/click single mutation | NOT_RUN |
| 5 | 1280px desktop + narrow viewport table/filters/dialog, no overlay clipping | NOT_RUN |

All five items require a live B5 web build, a backend running the B5/1.16 contracts, and a
browser session against that stack. The environment provides neither a B5 artifact nor B5
services (only 1.15.0 enterprise containers), and producing them requires writes forbidden by
this role. No browser result is fabricated.

## 8. Findings

### Accepted baselines (no findings)

- Pre-existing dynamic webApps Vitest flake: **did not reproduce** this run (295/295 pass);
  no ACCEPTED_LIMITATION needed.
- Five-file B1 `vp check` formatting baseline: reproduced exactly.
- ESLint: **NOT_RUN** (short-circuited by `&&` after `vp check` exit 1).
- Literal `pnpm --dir web exec vp check` node-shim/path failure: not re-triggered in this run
  because `vp test`/`vp check` resolved via `./node_modules/.bin` paths without issue; the
  prior accepted baseline record remains unchanged.

### Open findings

None. No B5FR-XX findings; no open P0/P1/P2.

### P3 observations

None.

## 9. Final state confirmation

- `git status --short --branch`: `## ctyun/replay-116-b5-regression` (clean)
- `git status --porcelain=v1`: 0 lines
- `git rev-parse HEAD`: `68822f521507b890ad663ef5a5affb9c2ef91b56`
- `git diff --check`: exit 0
- No commit / amend / push occurred. No product, lockfile, manifest, contract, API, Docker,
  i18n, or `e2e/**` file was modified. The only write is this report under
  `docs/enterprise/replay-1.16.0/B5_FULL_REGRESSION_REPORT.md`.

# Enterprise Replay Plan

Base: `upstream/main` at `da00de668886`

Candidate branch: `codex/enterprise-candidate-20260424`

Status: current best enterprise candidate. This branch has been rebuilt from a clean upstream base and has passed the core manual runtime flows listed below.

## Goal

Rebuild the enterprise branch from a clean upstream base, replaying only the patches required to preserve enterprise workspace and 智慧广场 behavior while keeping upstream's safer and newer implementation as the default.

## Branch Truth

- `main`: official upstream baseline; do not add enterprise features here.
- `codex/enterprise-candidate-20260424`: current candidate and active work surface.
- `enterprise/main`: previous dirty enterprise branch until the candidate is promoted; use only as a historical reference.
- `codex/protect-enterprise-main-20260424-103050`: protected snapshot of the previous dirty branch.

Agents must not use the old dirty branch as an implementation source of truth. Copy only a named patch group or a change that has been re-proven by current-source tests, rebuilt enterprise images, browser clicks, and logs.

## Replay Principles

- Start from upstream and add enterprise behavior surgically.
- Prefer upstream implementation unless an enterprise capability would break.
- Re-apply enterprise patches by capability area, not by copying the old dirty tree.
- After each replay group, run the closest build/test/runtime check before moving on.
- Do not import local runtime artifacts, build caches, `node_modules`, Docker volumes, or old test-only drift.
- Treat old route-2 performance work as optional historical guidance, not mandatory enterprise behavior.
- Prefer deleting stale assumptions over adapting the new candidate to old dirty-branch quirks.

## Current Verified Runtime Flows

The current candidate has been manually validated for these production-critical paths:

- Platform admin can create workspaces, rejects duplicate workspace names, invites members, changes roles, removes members, and deletes non-current workspaces.
- New accounts can join additional spaces and can also be added to the default space.
- Apps can be submitted to 智慧广场, reviewed by a platform admin, listed publicly, and copied by another account into a different workspace.
- Plugin installation works for a new account and does not keep asking to install the same Tongyi plugin after success.
- Knowledge base usage works in the verified local environment.

These flows are the minimum behavior to preserve when promoting this candidate or syncing a future official version.

## Must Replay Patch Groups

### 1. Enterprise Workspace Baseline

Purpose: preserve enterprise workspace behavior, default workspace joining, workspace/account compatibility, and platform-admin entry points.

Candidate sources to review:

- `api/services/account_service.py`
- `api/controllers/console/workspace/account.py`
- `api/controllers/console/workspace/__init__.py`
- `api/models/account.py`
- `web/context/workspace-context.ts`
- `web/app/components/header/account-setting/platform-admin-page/`
- `web/app/components/header/account-dropdown/workplace-selector/`

Validation:

- Fresh install creates account correctly.
- First login reaches official language/timezone completion when required.
- `/apps?action=showSettings&tab=provider` does not hit the Next error boundary.
- Workspace selector and account settings render without runtime errors.

### 2. 智慧广场 / Enterprise Marketplace

Purpose: preserve enterprise marketplace app submission, admin review/listing, explore marketplace navigation, and related backend APIs.

Candidate sources to review:

- `api/controllers/console/enterprise_marketplace.py`
- `api/services/enterprise_marketplace_service.py`
- `api/migrations/versions/2026_04_01_2100-c8f3d9d4a1be_add_enterprise_marketplace_assets.py`
- `web/app/(commonLayout)/explore/marketplace/page.tsx`
- `web/app/components/explore/enterprise-marketplace/`
- `web/app/components/apps/submit-enterprise-marketplace-modal.tsx`
- `web/app/components/header/enterprise-marketplace-nav/`
- `web/service/use-enterprise-marketplace.ts`

Validation:

- Explore marketplace tests pass.
- Marketplace API routes load.
- Enterprise app submission and admin entry render.

### 3. Docker / Offline Enterprise Packaging

Purpose: preserve only deployment-safe enterprise packaging, especially for remote offline Linux. Do not carry machine-specific runtime hacks.

Candidate sources to review:

- `docker/docker-compose.enterprise.yaml`
- `docker/README.enterprise.md`
- `docker/scripts/build-enterprise-web.ps1`
- `scripts/build-enterprise-offline.ps1`
- `scripts/build-enterprise-offline.sh`
- `.dockerignore`
- `web/Dockerfile`
- `web/Dockerfile.dockerignore`

Validation:

- Enterprise API image builds from current source.
- Enterprise web image builds from current source.
- Compose services start without migration multiple-head errors.
- No local `docker/volumes/**` runtime data is required for a fresh deployment except documented config files.

### 4. Install / Sign-In / Public Route Regression Fixes

Purpose: keep the fixes that are proven by runtime verification, without masking official setup flow behavior.

Candidate sources to review:

- `web/app/install/installForm.tsx`
- `web/app/signin/normal-form.tsx`
- `web/app/signin/one-more-step.tsx`
- `web/context/global-public-context.tsx`
- `web/service/base.ts`
- `web/service/fetch.ts`
- `web/service/system-features.ts`
- `web/service/use-common.ts`
- `api/services/account_service.py`

Validation:

- `/install` works on a clean database.
- Setup/login flow reaches the correct next step.
- `/apps` loads after initialization.
- Direct public/session-sensitive routes do not show blank/error pages.

### 5. User-Flagged Critical Regressions

Purpose: explicitly re-check the two areas the user called out from the previous image.

Candidate sources to review:

- `api/services/app_dsl_service.py`
- `web/app/components/app/configuration/hooks/use-configuration-utils.ts`

Validation:

- DSL import/export representative tests pass.
- Creating beginner apps such as text generation, agent, and chat assistant works.
- Configuration hook tests pass against current upstream behavior.

### 6. Workflow / Plugin / Dataset / Tool Compatibility

Purpose: carry only enterprise-required compatibility patches after upstream behavior is understood.

Candidate sources to review:

- `api/controllers/console/app/workflow_draft_variable.py`
- `api/controllers/console/datasets/data_source.py`
- `api/services/dataset_service.py`
- `api/services/tools/*_tools_manage_service.py`
- `api/core/workflow/`
- `web/app/components/workflow/`
- `web/app/components/plugins/`
- `web/app/components/datasets/`
- `web/app/components/tools/`

Validation:

- Representative workflow, dataset, plugin, and tool flow tests pass.
- Runtime clicks for dataset creation, plugin marketplace, tool provider detail, and workflow block selection work.

## Explicit Exclusions Unless Re-Proven Necessary

- `docker/.build/`
- `docker/volumes/**` runtime data
- `docker/volumes/sandbox/dependencies/`
- `packages/*/node_modules/`
- `web/.eslintcache`
- Broad UI-library migration edits that are not required by enterprise behavior or current upstream build
- Old tests that only assert pre-upstream APIs
- Local Windows-only runtime workarounds that would not apply to remote offline Linux deployment

## First Implementation Order

1. Replay documentation and Docker/offline packaging scaffolding that is source-safe.
2. Replay enterprise marketplace backend migration/service/controller.
3. Replay enterprise marketplace frontend navigation and pages.
4. Replay enterprise workspace/account behavior.
5. Re-check install/sign-in/public route behavior against clean upstream first, then patch only proven regressions.
6. Re-check `app_dsl_service.py` and `use-configuration-utils.ts` before carrying any old hotfix.
7. Validate dataset/plugin/tool/workflow flows last, because these are broad upstream-moving areas.

## Promotion Checklist

Before this candidate becomes the new `enterprise/main`:

1. Remove local runtime-data deletions and other machine artifacts from the Git diff.
2. Commit only source, config, documentation, tests, migrations, and release scripts.
3. Rebuild enterprise `api` and `web` images from the candidate source.
4. Force recreate `api`, `worker`, `worker_beat`, `web`, and `nginx`.
5. Repeat the verified runtime flows above and inspect logs for new 500s, tracebacks, and Next error boundaries.
6. Protect the previous `enterprise/main` and promote this candidate by PR, merge, or an explicitly approved branch reset.

# Dify Enterprise 1.16.0 Replay B6 — Implementation Plan Review

Role: plan-reviewer · Instance: replay-116-b6-plan-reviewer

## 0. Verdict

**PASS** — exact scope, no open P0/P1/P2 findings, complete evidence with only accepted
NOT_RUN, no unauthorized writes. The B6 implementation plan
(`docs/enterprise/replay-1.16.0/B6_IMPLEMENTATION_PLAN.md`) is internally consistent with
all sources of truth and is sufficient to launch the B6 Builder unambiguously.

## 1. Start verification

| Item | Expected | Actual | Result |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b6-plan-reviewer` | `ctyun/replay-116-b6-plan-reviewer` | PASS |
| HEAD | `d7e4f41971d7dc1812b2c5197cb25cbe30b4243d` | `d7e4f41971d7dc1812b2c5197cb25cbe30b4243d` | PASS |
| `git status --short --branch` | clean | `## ctyun/replay-116-b6-plan-reviewer` | PASS |
| `git status --porcelain=v1` | empty | empty | PASS |

No merge, rebase, reset, checkout, cherry-pick, commit, amend or push was performed.

## 2. Exact range and scope

- Reviewed commit: `d7e4f41971` "docs: plan enterprise replay B6 overlay".
- `git diff --name-status 757806e3698dfe673be5e46d164b4942edb282a0..HEAD`:
  exactly `A docs/enterprise/replay-1.16.0/B6_IMPLEMENTATION_PLAN.md`.
- The range contains exactly the one plan file and nothing else (no product file).
- `git diff --check 757806e3698dfe673be5e46d164b4942edb282a0..HEAD` → exit 0 (clean).
- The plan file records its own authoring start state (branch
  `ctyun/replay-116-b6-architect`, HEAD `757806e369…`), which is the exact range base;
  internally consistent with the plan commit being a child of that base.

## 3. Checklist verification with evidence

### 3.1 Recovery and gate evidence (checklist 1) — PASS

- B5 ancestor: `git merge-base --is-ancestor e7d487538fb1431a3b769a8d3fe9d8354487ceea HEAD`
  → exit 0. Matches plan §1.1.
- Official compose/template consistency: `diff docker/docker-compose.yaml
  docker/docker-compose-template.yaml` shows only the 6-line auto-generated header
  (`1,6d0`), exit 0; last modification of both is official baseline `5c6372d2f7` via
  `git log`. Matches plan §1.1 and §2.1.
- B9 decision file absent: `docs/enterprise/replay-1.16.0/session-management-product-decision.md`
  does not exist (verified). Matches plan §0.1 / §1.3.
- Start clean: porcelain empty; `docker/.env` absent, no stray artifact left after the
  architect's temporary `.env` runs.

### 3.2 Allowlist / denylist (checklist 2) — PASS

- Plan §0.2, §3.1, §7 make `docker/docker-compose.enterprise.yaml` the sole default product
  file. No new Dockerfile/build metadata is default-authorized; any addition requires an
  explicit stop-and-request (plan §0.2, §3.1, §7, §8, §10.3).
- Plan §8 global denylist covers `docker/docker-compose.yaml`,
  `docker/docker-compose-template.yaml`, `docker/volumes/**`, `docker/envs/**`,
  `docker/.env*`, `nginx/**`, `ssrf_proxy/**`, `certbot/**`, `generate_docker_compose`,
  remaining `docker/**`, `api/**`, `web/**`, `dify-agent/**`, `packages/**`, `scripts/**`,
  all lockfiles, and all other `docs/enterprise/replay-1.16.0/**` docs. Matches the
  ARCHITECT_HANDOFF §5 B6 row and the task contract.

### 3.3 Overlay contract (checklist 3) — PASS

Verified against the actual official `docker/docker-compose.yaml`:

- Official four API runtimes all `image: langgenius/dify-api:1.16.0`
  (`api:229`, `api_websocket:279`, `worker:305`, `worker_beat:354`); `web` is
  `langgenius/dify-web:1.16.0` (`web:387`). Plan §3.1 requires the overlay to resolve all
  four API runtimes to the same enterprise API tag and web to the enterprise Web tag,
  default `1.16.0-enterprise`. Consistent.
- `agent_backend` (`agent_backend:645`) and `local_sandbox` (`local_sandbox:540`) stay
  official 1.16 images; plan §3.2 excludes both service blocks from the overlay.
- depends_on: `api:261`/`worker:334` → `agent_backend` (`service_started`);
  `agent_backend:671-677` → `redis`/`plugin_daemon`/`local_sandbox`. Plan §2.1, §3.1,
  §6.2 preserve and assert these.
- collaboration profile: `api_websocket.profiles: [collaboration]` (`api_websocket:280-281`);
  plan §3.1 requires the overlay to re-declare `profiles: [collaboration]` explicitly and
  Phase E asserts via `--profile collaboration config --services`. Addresses
  ARCHITECT_REVIEW P2-4 / FIX-14 / E14.
- Compose merge semantics (mapping merge, list append) correctly described in §3.1;
  official `env_file`, `depends_on`, `healthcheck`, `volumes`, `networks` are preserved
  because the overlay only appends `environment` keys and adds `image`/`build`.

### 3.4 Security / identity (checklist 4) — PASS

- `CAN_REPLACE_LOGO`: official source default `false` at
  `api/configs/enterprise/__init__.py:17`; plan requires overlay literal `true` (§2.1, §4,
  §5 S-1) and separately asserts official vs overlay expanded values. Matches E08 /
  FIX-18 / ARCHITECT_REVIEW §8.2.
- No volume/network/healthcheck/security-variable override: §3.3 and §5 S-2/S-3; verified
  official `volumes`, `networks`, `healthcheck` present and overlay set excludes them.
- No permanent `local_sandbox` volume: official `local_sandbox` has none
  (`local_sandbox:539-554`); plan §3.2/§3.3/S-3 forbid adding one.
- No dev agent secret in overlay: plan §3.3/S-8 forbid writing the official dev default
  `DIFY_AGENT_SERVER_SECRET_KEY` value (`docker-compose.yaml:668`).
- Key equality: official fallback chain gives
  `api.INNER_API_KEY_FOR_PLUGIN` (`api:239`) ==
  `agent_backend.DIFY_AGENT_INNER_API_KEY` (`agent_backend:661`) via
  `${PLUGIN_DIFY_INNER_API_KEY:-…}`; plan §5 S-5 asserts equality on expanded values with a
  0600 temp file and YAML parser, printing only `equal=true/false`. Matches FIX-06 /
  VALIDATION_PLAN Phase E.
- Retention: official `DIFY_AGENT_RUN_RETENTION_SECONDS:-259200` (`agent_backend:670`);
  plan §4/S-4 assert 259200.
- Redis database numbers: verified non-conflicting — main cache/session default `/0`,
  Celery broker `/1` (`shared.env.example:24`), agent `/2` (`docker-compose.yaml:656`).
  Plan §5 S-6 requires parsing database numbers, not URL prefixes. Matches FIX-14.
- Landlock: `SHELLCTL_ENABLE_PATH_ISOLATION=true` in `local-sandbox.env.example:6`;
  plan §4/S-7 keeps it untouched and asserts it in expanded config.
- Security-regression commits listed in §5 S-9 (`d9884efaee` SQLi, `ae0d6ee214` SSRF,
  `c68e5e5ed3` redirect, `38aec8b506`/`7311f1ba6d` sandbox, `71709f03c3`/`8a33161080`
  Landlock) all exist in the repo and match the ARCHITECT_REVIEW security reviewer scope.

### 3.5 Phase E only / honest NOT_RUN (checklist 5) — PASS

- §6.2 Phase E static commands mirror VALIDATION_PLAN §Phase E exactly:
  `config -q`, `config --images | sort -u`, `--profile collaboration config --services`,
  with `DIFY_ENTERPRISE_VERSION` and `COMPOSE_PROFILES` exports.
- §6.3 Phase F (build/recreate/`docker inspect .Image`) is explicitly NOT_RUN pending
  separate coordinator authorization; §11.2 declares NOT_RUN honestly for build/up/inspect/
  browser/E2E/Phase G/Phase H/Phase D/contract tests/`docker/volumes` access.
- §11.1 records only read-only commands actually run by the Architect; the note about
  compose v5 requiring a temporary `docker/.env` copy is accurate (reproduced: exit 1
  without `.env`, exit 0 with `.env.example` copy, removed afterward, porcelain empty).
  No fabricated runtime evidence.

### 3.6 Old 1.15 dispositions (checklist 6) — PASS

- `HOME: ${HOME_OVERRIDE:-/tmp}` → DROP_UPSTREAMED. Verified 1.16 has zero
  `HOME_OVERRIDE`/`DIFY_INTERNAL_API_URL` references (`grep` across `docker/`, `api/`,
  `web/docker/` → none).
- `web` `DIFY_INTERNAL_API_URL` → DROP_UPSTREAMED (C07 deprecated old-API compatibility).
- `plugin_daemon` `PIP_MIRROR_URL`/`PIP_INDEX_URL`/`UV_INDEX_URL`/
  `PLUGIN_MAX_EXECUTION_TIMEOUT` → DROP_FROM_B6, deferred to B7 (E11); verified official
  `plugin_daemon` is not in the B6 overlay service set.
- `api_websocket` enterprise image → KEEP_MINIMAL_PATCH with `profiles: [collaboration]`
  retained (E14).
- Enterprise image naming `dify-api-enterprise`/`dify-web-enterprise`, tag
  `1.16.0-enterprise` → KEEP; overlay reuses official Dockerfiles (E08/E09), verified both
  `api/Dockerfile:119-120` and `web/Dockerfile:84-85` declare `ARG/ENV COMMIT_SHA`.
- Web frontend env mapping `ALLOW_REGISTER`→`NEXT_PUBLIC_ALLOW_REGISTER` /
  `ALLOW_CREATE_WORKSPACE`→`NEXT_PUBLIC_ALLOW_CREATE_WORKSPACE` verified at
  `web/docker/entrypoint.sh:38-39`; plan §2.1/E02 requires overlay injection on `web`.

### 3.7 Plan quality (checklist 7) — PASS

- Exact ownership matrix (§7) matches ARCHITECT_HANDOFF §5 shared-path table
  (`docker/docker-compose.enterprise.yaml` sole writer = B6; B7 read-only consumer).
- Env matrix (§4), security matrix (§5), validation plan (§6), risks/decisions/stop
  conditions (§10), and Plan Reviewer checklist (§13) are present, complete, and internally
  consistent; all cited decision IDs (E02/E08/E09/E11/E14/E18, FIX-06/08/10/14,
  DG-03, C07) resolve to the PATCH_DECISION_MATRIX / ARCHITECT_REVIEW / VALIDATION_PLAN /
  ARCHITECT_HANDOFF sources.
- Gate chain (§9, §14) matches the established Architect → Reviewer → Fixer → Rereviewer →
  Builder → Code Reviewer → coordinator-authorized-commit flow.

## 4. Findings

No P0/P1/P2 findings.

### P3 observations (non-blocking)

- **B6PR-01 (P3)**: Plan §3.1 sets the `COMMIT_SHA` build arg to
  `${DIFY_ENTERPRISE_VERSION:-1.16.0-enterprise}`, i.e. the version tag rather than an
  actual git commit SHA. This mirrors the old 1.15 overlay and is consistent with
  E08/E09/C08, so it is acceptable; the builder should record in the Phase F image-ID
  evidence that `COMMIT_SHA` holds the enterprise version tag, not a commit hash.
- **B6PR-02 (P3)**: Plan §6.1 uses a `<B6 起始 base SHA>` placeholder; the concrete base is
  the accepted-plan SHA (this review's HEAD `d7e4f41971…`). The builder must resolve the
  placeholder to the exact accepted-plan SHA before running the §6.1 commands.
- **B6PR-03 (P3)**: Plan §5 S-9 lists code-level security-regression commits
  (`d9884efaee`, `ae0d6ee214`, …) which a compose-only overlay cannot reintroduce by
  construction; the assertion is harmless and guards against copying insecure old YAML, and
  the real enforcement is B7 package scanning. No change required.

## 5. Verification command log

| Command | Exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b6-plan-reviewer` |
| `git rev-parse HEAD` | 0 | `d7e4f41971d7dc1812b2c5197cb25cbe30b4243d` |
| `git status --short --branch` | 0 | clean |
| `git status --porcelain=v1` | 0 | empty |
| `git merge-base --is-ancestor e7d4875… HEAD` | 0 | ancestor=true |
| `git diff --name-status 757806e…..HEAD` | 0 | exactly `A docs/enterprise/replay-1.16.0/B6_IMPLEMENTATION_PLAN.md` |
| `git diff --check 757806e…..HEAD` | 0 | clean |
| `docker compose -f docker/docker-compose.yaml --profile collaboration config --services` (with temp `.env`) | 0 | 13 services incl. `api_websocket` |
| `docker compose -f docker/docker-compose.yaml config --images \| sort -u` | 0 | 12 images incl. `dify-agent-backend:1.16.0`, `dify-agent-local-sandbox:1.16.0`, `dify-api:1.16.0`, `dify-web:1.16.0` |
| `docker compose -f …/dify-enterprise-1.15.0/…/docker-compose.yaml -f …/docker-compose.enterprise.yaml config -q` | 0 | old 1.15 overlay statically valid (read-only evidence) |
| `docker/docker-compose.enterprise.yaml` existence | — | absent (B6 pending) |
| `docs/enterprise/replay-1.16.0/session-management-product-decision.md` existence | — | absent (B9 keeps DEFER) |
| `diff docker/docker-compose.yaml docker/docker-compose-template.yaml` | 0 | identical except 6-line generated header |
| `grep` HOME_OVERRIDE / DIFY_INTERNAL_API_URL in `docker/ api/ web/docker/` | 1 (no match) | legacy vars absent in 1.16 |
| `grep` ALLOW_REGISTER / ALLOW_CREATE_WORKSPACE in `web/docker/entrypoint.sh` | 0 | `NEXT_PUBLIC_ALLOW_REGISTER`/`NEXT_PUBLIC_ALLOW_CREATE_WORKSPACE` mapping present |
| `git cat-file -e` on §5 S-9 commit IDs | 0 | all 7 referenced commits exist |

Pass/Fail/NOT_RUN: **13 PASS / 0 FAIL / 0 NOT_RUN** among the commands this reviewer ran
(all required verification commands executed and passed; no fabrication). The NOT_RUN areas
are exclusively the plan's accepted Phase F/runtime gates, which this review does not execute.

`git diff --check` result: **clean (exit 0)** for the reviewed range.

Current `git status`: clean (`## ctyun/replay-116-b6-plan-reviewer`, porcelain empty).

## 6. Declaration

- No commit, amend, push, merge, rebase, reset, or cherry-pick occurred during this review.
- The only intended write is this report at
  `docs/enterprise/replay-1.16.0/B6_IMPLEMENTATION_PLAN_REVIEW.md`.
- No external system, database, container, volume, remote, or production state was modified.

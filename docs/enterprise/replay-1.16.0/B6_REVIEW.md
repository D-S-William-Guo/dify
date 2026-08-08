# Dify Enterprise 1.16.0 Replay B6 — Code Review

Role: code-reviewer · Instance: replay-116-b6-reviewer

## 0. Verdict

**PASS** — exact scope, no open P0/P1/P2 findings, complete Phase E evidence with only
accepted NOT_RUN, no unauthorized writes. The B6 enterprise Compose overlay
(`docker/docker-compose.enterprise.yaml`) satisfies the overlay contract, environment
matrix, and security/identity invariants of B6_IMPLEMENTATION_PLAN.md §3–§5 and
VALIDATION_PLAN.md Phase E.

## 1. Start verification

| Item | Expected | Actual | Result |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b6-reviewer` | `ctyun/replay-116-b6-reviewer` | PASS |
| HEAD | `d218e48f282fee2f9c662d187be0f3508912396e` | `d218e48f282fee2f9c662d187be0f3508912396e` | PASS |
| `git status --short --branch` | clean | `## ctyun/replay-116-b6-reviewer` | PASS |
| `git status --porcelain=v1` | empty | empty | PASS |

No merge, rebase, reset, checkout, cherry-pick, commit, amend or push was performed.

## 2. Exact range and scope

- Reviewed commit: `d218e48f28` "feat: add enterprise B6 compose overlay" (HEAD).
- Range: `68a052f8be6ac2a87e98938a1fb1d65daeb8be1b..HEAD`.
- `git diff --name-status`: exactly `A docker/docker-compose.enterprise.yaml` (74 lines).
- `git diff --stat`: `1 file changed, 74 insertions(+)`.
- `git diff --binary | sha256sum`: `55ad33d39149f6137ad034408e01b98913c59c4d86540698437204904ad6519e` (matches required).
- No changes to official `docker/docker-compose.yaml`, `docker/docker-compose-template.yaml`,
  `docker/.env.example`, `docker/volumes/**`, `docker/envs/**`, `api/**`, `web/**`,
  agent/local sandbox; no new Dockerfile/build metadata. Targeted diff of the official
  compose files, `.env.example`, `api/`, `web/` across the range is empty.

## 3. Checklist verification with evidence

### 3.1 Overlay contract (checklist 2) — PASS

- Only services declared: `api`, `worker`, `worker_beat`, `api_websocket`, `web`
  (`docker/docker-compose.enterprise.yaml:6-74`).
- All four API runtimes resolve to the same enterprise API image/tag
  `dify-api-enterprise:1.16.0-enterprise` (asserted on expanded `config`: set of four
  images == `{'dify-api-enterprise:1.16.0-enterprise'}`).
- `web` resolves to `dify-web-enterprise:1.16.0-enterprise`.
- `build.context: ..`, `build.dockerfile: api/Dockerfile` / `web/Dockerfile`,
  `build.args.COMMIT_SHA` present for all five runtimes; both official Dockerfiles declare
  `ARG COMMIT_SHA`/`ENV COMMIT_SHA` (`api/Dockerfile:119-120`, `web/Dockerfile:84-85`).
- `api_websocket` keeps `profiles: [collaboration]` (`docker-compose.enterprise.yaml:23-24`);
  confirmed in expanded config.
- Compose merge preserves official `env_file`, `volumes`, `networks`, `healthcheck`,
  `depends_on` (mapping merge / list append); expanded `api`/`worker`/`worker_beat` retain
  healthcheck/volumes/networks as in official, `api_websocket` retains official shape.

### 3.2 Environment (checklist 3) — PASS

- Four API runtimes get `ENTERPRISE_ENABLED=false`, `CAN_REPLACE_LOGO` literal `true`,
  `PLATFORM_ADMIN_EMAILS=` (empty), `ALLOW_REGISTER=false`, `ALLOW_CREATE_WORKSPACE=false`
  (asserted on expanded config values).
- `web` gets `ALLOW_REGISTER=false` and `ALLOW_CREATE_WORKSPACE=false` only
  (`docker-compose.enterprise.yaml:72-74`); `web/docker/entrypoint.sh:38-39` maps these to
  `NEXT_PUBLIC_ALLOW_REGISTER`/`NEXT_PUBLIC_ALLOW_CREATE_WORKSPACE`.
- No other official env overridden: overlay only appends these keys; official keys
  (`MODE`, `INNER_API_KEY_FOR_PLUGIN`, `AGENT_BACKEND_*`, `SERVER_WORKER_*`, etc.) are all
  present unchanged in the expanded config.

### 3.3 Security / identity (checklist 4, plan §5 S-1..S-9) — PASS

- S-1 `CAN_REPLACE_LOGO`: official single-file config contains 0 occurrences (source default
  `false` at `api/configs/enterprise/__init__.py:17`); overlay expanded value == `true`. PASS.
- S-2 No volume/network/healthcheck/security-variable override: overlay diff contains no
  `volumes:`/`networks:`/`healthcheck:`/`depends_on:`/`security` keys (grep over
  `git show HEAD:docker/docker-compose.enterprise.yaml` → no matches). PASS.
- S-3 `local_sandbox` has no volumes in expanded config; overlay declares no `local_sandbox`
  block. PASS.
- S-4 `DIFY_AGENT_RUN_RETENTION_SECONDS` == `259200` (expanded `agent_backend`). PASS.
- S-5 Key equality after fallback expansion:
  `agent_backend.DIFY_AGENT_INNER_API_KEY == api.INNER_API_KEY_FOR_PLUGIN` == true (0600 temp
  file + YAML parser; only the boolean is reported). PASS.
- S-6 Redis database numbers parsed from URLs: main cache/session `0`, Celery broker `1`,
  agent backend `2`; mutually distinct. PASS.
- S-7 Landlock untouched: expanded `local_sandbox` environment does not set
  `SHELLCTL_ENABLE_PATH_ISOLATION`. PASS.
- S-8 No dev agent secret in overlay: no `DIFY_AGENT_SERVER_SECRET_KEY` occurrence in the
  overlay file/diff. PASS.
- S-9 No security-regression content: overlay contains none of the S-9 commit refs or
  corresponding code/config (compose-only file; grep no matches). PASS.

### 3.4 depends_on / profile preservation — PASS

- `api` and `worker` `depends_on` still include `agent_backend` (`service_started`).
- `agent_backend` `depends_on` still includes `redis`, `plugin_daemon`, `local_sandbox`.
- Official profile set preserved: `--profile collaboration config --services` (official
  single file) == same with overlay (diff identical, sorted).

### 3.5 Phase E static compose (plan §6.2) — PASS

Commands executed with a temporary `docker/.env` (copy of `docker/.env.example`), then
deleted; `git status --porcelain=v1` empty afterward.

| Command | Exit | Result |
| --- | ---: | --- |
| `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q` | 0 | static validity |
| `docker compose ... config --images \| sort -u` | 0 | 12 images incl. `dify-api-enterprise:1.16.0-enterprise`, `dify-web-enterprise:1.16.0-enterprise`, `langgenius/dify-agent-backend:1.16.0`, `langgenius/dify-agent-local-sandbox:1.16.0` |
| `docker compose ... --profile collaboration config --services` | 0 | 13 services incl. `api_websocket` |
| Expanded-config S-1..S-7 assertion script (0600 temp file) | 0 | all `equal=true` / expected values |
| Official vs overlay service-set diff | 0 | identical |

### 3.6 Phase F — NOT_RUN (accepted)

- `docker compose build` (enterprise API/Web images): NOT_RUN.
- `docker compose up -d` / recreate / container runtime: NOT_RUN.
- `docker inspect ... .Image` five-runtime image-ID equality (FIX-10): NOT_RUN.
- browser/E2E / Phase G runtime acceptance: NOT_RUN.

Static image-tag equality does not substitute for image-ID equality; this remains the
accepted Phase F deferral per plan §6.3 / §10.1.

## 4. Findings

No P0/P1/P2 findings.

### P3 observations (non-blocking)

- **B6R-01 (P3)**: As in the plan (and the accepted plan-reviewer observation B6PR-01),
  `COMMIT_SHA` carries the enterprise version tag (`1.16.0-enterprise`), not a commit hash.
  Consistent with plan §3.1; the Phase F evidence should record that `COMMIT_SHA` holds the
  tag, not a commit hash.
- **B6R-02 (P3)**: `CAN_REPLACE_LOGO` is written as a quoted YAML string `"true"`. Compose
  normalizes all environment values to strings, so the expanded value is `true` (string) as
  required; the app parses it per the pydantic `bool` config. No change required.
- **B6R-03 (P3)**: The overlay relies on compose mapping-merge to preserve official fields
  (no explicit re-declaration). This is correct for the compose version used (v5.0.2) and is
  asserted statically; it cannot be fully proven without Phase F runtime merge behavior.

## 5. Verification command log

| Command | Exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b6-reviewer` |
| `git rev-parse HEAD` | 0 | `d218e48f282fee2f9c662d187be0f3508912396e` |
| `git status --short --branch` | 0 | clean |
| `git status --porcelain=v1` | 0 | empty |
| `git diff --name-status 68a052f8…..HEAD` | 0 | exactly `A docker/docker-compose.enterprise.yaml` |
| `git diff --stat 68a052f8…..HEAD` | 0 | 74 insertions, 1 file |
| `git diff --check 68a052f8…..HEAD` | 0 | clean |
| `git diff --binary 68a052f8…..HEAD \| sha256sum` | 0 | `55ad33d39149f6137ad034408e01b98913c59c4d86540698437204904ad6519e` |
| `git merge-base --is-ancestor e7d4875… HEAD` | 0 | B5 ancestor holds |
| `docker compose … config -q` (temp `.env`) | 0 | valid |
| `docker compose … config --images \| sort -u` | 0 | enterprise API/Web + official agent images |
| `docker compose … --profile collaboration config --services` | 0 | includes `api_websocket` |
| S-1..S-7 expanded-config assertions | 0 | all pass |
| official vs overlay service-set diff | 0 | identical |
| official single-file `CAN_REPLACE_LOGO` grep | 1 | 0 occurrences (default `false` holds) |
| overlay-diff security/override grep | 1 | no forbidden keys |
| `git diff --check` (worktree) | 0 | clean |
| `git status --short --branch` (final) | 0 | clean |

Pass/Fail/NOT_RUN: **17 PASS / 0 FAIL / 3 NOT_RUN** among the commands this reviewer ran
(3 NOT_RUN are the accepted Phase F gates: build, recreate/runtime, `docker inspect`
image-ID; no static result is presented as runtime evidence).

`git diff --check` result: **clean (exit 0)** for the reviewed range and the worktree.

Current `git status`: clean (`## ctyun/replay-116-b6-reviewer`, porcelain empty; temp
`docker/.env` and 0600 expanded-config temp files removed after use).

## 6. Declaration

- No commit, amend, push, merge, rebase, reset, or cherry-pick occurred during this review.
- The only intended write is this report at `docs/enterprise/replay-1.16.0/B6_REVIEW.md`.
- No external system, database, container, volume, remote, or production state was modified;
  no `docker/volumes/**` was accessed or copied.

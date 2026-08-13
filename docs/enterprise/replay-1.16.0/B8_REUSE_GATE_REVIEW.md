# B8 Reuse-Gate Review — stale same-tag image hardening

Reviewer: `replay-116-b8-reuse-gate-reviewer`
Branch: `ctyun/replay-116-b8-reuse-gate-reviewer`
Reviewed commit: `437c59ab8b85599daa54ac8cd6f55617e1c63e3e`
Fixer range: `94e65cdb59e43ff1cc5b80a94fc7925a9d86c648..437c59ab8b85599daa54ac8cd6f55617e1c63e3e`
Date: 2026-08-13

## Verdict: PASS

No P0/P1/P2. Exact scope (+179/-3, 5 files, diff SHA-256
`1fa8bfdbb2dbb68071bdad84bffc77a92bb5d95b120e4eb6d115edfc76521c0a`). Tests
24/24 pass (exit 0). Real pre-fix image rejected (exit 1, migration-set diff).
The B7 gate would have rejected the Phase H stale image.

## Scope verification

`git diff --name-status 94e65cdb..HEAD`:

- M `docs/enterprise/replay-1.16.0/DECISION_RISK_LEDGER.md`
- M `scripts/build-enterprise-offline.ps1`
- M `scripts/build-enterprise-offline.sh`
- M `scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker`
- M `scripts/ci/check-enterprise-offline-tests.sh`

`git diff --stat`: 5 files, +179/-3. `git diff --check` clean. No forbidden
path changed (`check-enterprise-offline.sh`,
`build-enterprise-config-package.{sh,ps1}`, `docker`, `api`, `web`,
`dify-agent`, `packages`, evidence dir all byte-identical).

## Per-item findings

### 1. Content gate logic (.sh) — PASS

- `verify_enterprise_image_content` (build-enterprise-offline.sh:122) is wired
  into `ensure_enterprise_image` (line 150/155/163) and invoked for the API
  image only (line 215, `verify_content=true`); runs on reuse, smart-reuse,
  and `-CheckOnly` paths. Web image intentionally ungated (Phase G was
  backend-only; ledger records this).
- Read-only: uses only `docker run --rm --entrypoint sh` (ls + grep). No
  build/pull/save/compose up. Verified in fake-docker.log (`^docker run `),
  no `build|pull` in reuse run.
- Fail-closed: any mismatch (migration set, missing `_align_snapshot_to_composition`)
  prints a clear stderr message and `exit 1`.
- `check-enterprise-offline.sh` CLI contract unchanged (file not in diff).

### 2. Migration set + marker comparison — PASS

- Both sides sorted before comparison (`find ... -printf '%f\n' | sort` and
  `ls ... | sed | sort`); exact-string compare of newline-joined names.
- Empty set: missing `/app/api/migrations/versions` → `ls` glob fails →
  empty `image_migrations` → mismatch → reject (fail-closed).
- `docker run` failure: swallowed by `|| true`, yields empty list → reject.
  Fail-closed preserved (see B8RGR-01 for the diagnostic caveat).
- Image path assumptions `/app/api/...` confirmed against the real image
  (grep inside `dify-api-enterprise:1.16.0-enterprise` runs fine).
- Marker: repo `api/clients/agent_backend/request_builder.py` contains
  `_align_snapshot_to_composition` (3 occurrences); migration
  `2026_08_12_0000-e7c0a9d2b8f3_*.py` present in repo.

### 3. fake-docker run branch + fixture tests — PASS

- fake-docker `run` branch (fake-docker:120) parses the exact gate invocation
  form `run --rm --entrypoint sh IMAGE -c SCRIPT`, returns
  `FAKE_DOCKER_MIGRATIONS` (default = repo list under `$PWD`) and honors
  `FAKE_DOCKER_MISSING_FUNCTION`. `bash -n` clean.
- Tests: `scripts/ci/check-enterprise-offline-tests.sh` → 24/24 pass, exit 0.
  New cases: content-gate-must-run assertion (tests:124), stale-migration
  reject (tests:195), stale-function reject (tests:206).

### 4. Real stale-image reproduction — PASS

Pre-fix image `dify-api-enterprise:1.16.0-enterprise`
(`sha256:cb4d99a45ac1...`, matches Phase H README `cb4d99a45ac1`) has
`COMMIT_SHA=1.16.0-enterprise` (old gate would accept), is missing migration
`e7c0a9d2b8f3` AND the marker. Real run in isolated fixture (real docker):

```
exit=1
Image dify-api-enterprise:1.16.0-enterprise is not reusable: image migration
file set differs from the repository api/migrations/versions at current HEAD.
125d124
< 2026_08_12_0000-e7c0a9d2b8f3_align_marketplace_uuid_columns.py
```

The gate would have rejected the Phase H stale image.

### 5. .ps1 mirror — PASS (NOT_RUN honestly recorded)

`Test-EnterpriseImageContent` (build-enterprise-offline.ps1:98) mirrors the
.sh gate for the API image reuse/smart/CheckOnly paths; `throw` fail-closed.
Runtime NOT_RUN — no pwsh in this environment; ledger explicitly records this.

### 6. Forbidden paths — PASS

None touched (see scope verification).

## Findings

- **B8RGR-01 (P3, informational):** `.sh` gate suppresses docker stderr
  (`2>/dev/null`, `|| true`); if `docker run` fails for an unrelated reason
  (daemon error, missing `sh` entrypoint) the reported diagnostic is the
  misleading "migration file set differs" instead of the real docker error.
  Safety preserved (empty output → mismatch → reject). Disposition: surface
  docker stderr when output is empty; non-blocking. Same applies to `.ps1`
  (`2>$null`, no `$LASTEXITCODE` check on the first run).
- **B8RGR-02 (P3, informational):** gate compares migration *filenames* plus a
  single grep marker, not content hashes; a same-tag image with identical
  filenames but drifted migration content would pass. Documented scope
  (GPH-01 file-set + GPH-02 marker), consistent with ledger decision. Upgrade
  path: per-file content hash or build-from-HEAD proof. Non-blocking.

## Commands run

| Check | Result |
| --- | --- |
| `git branch --show-current` | `ctyun/replay-116-b8-reuse-gate-reviewer` |
| `git rev-parse HEAD` | `437c59ab8b85599daa54ac8cd6f55617e1c63e3e` |
| `git status --short --branch` | clean at start |
| `git diff --name-status/--stat range..HEAD` | 5 files, +179/-3 |
| `git diff --check range..HEAD` | clean |
| `git diff --binary range..HEAD \| sha256sum` | `1fa8bfdb...` |
| `bash -n build-enterprise-offline.sh tests.sh` | clean |
| `scripts/ci/check-enterprise-offline-tests.sh` | 24/24 PASS, exit 0 |
| `docker image inspect dify-api-enterprise:1.16.0-enterprise` | `sha256:cb4d99a45ac1...` |
| real reuse run vs pre-fix image | exit 1, migration-set diff |
| pwsh | NOT_RUN (not installed) |

No commit/amend/push performed. Current worktree: this file is the only
addition (untracked review artifact).

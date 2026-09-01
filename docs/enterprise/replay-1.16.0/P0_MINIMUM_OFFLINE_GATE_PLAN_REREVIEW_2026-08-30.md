# Enterprise 1.16.0 minimum offline artifact gate plan rereview

Date: 2026-08-31 (Asia/Shanghai)

Role: independent Plan Rereviewer

Environment: Development / isolated rehearsal

## Verdict: PASS

The Plan Fixer fully and accurately repaired accepted findings P1-01, P1-02, P1-03, P1-04,
P2-01, and P2-02 without changing their severities. No blocking or new finding remains. The
repaired plan preserves the accepted minimum policy: exact construction inputs, auditable
first-party contexts, clean exact-candidate rebuild provenance, metadata and identity binding,
and synthetic/public canaries replace normal protected-pattern processing and layer-content
scanning.

The plan is accepted for a future narrowly allowlisted Builder stage. This is plan acceptance
only: implementation, real image/runtime evidence, PowerShell parity, protected audit, isolated
upgrade rehearsal, and deployment remain unexecuted. No Builder may be created unless the human
separately authorizes it.

## Immutable start preflight

The required commands ran before any write:

```text
git branch --show-current
  ctyun/replay-116-minimum-offline-gate-plan-rereviewer-20260830
git rev-parse HEAD
  120092cdaafd80cd185060d51c93ca7516bfe2eb
git status --short --branch
  ## ctyun/replay-116-minimum-offline-gate-plan-rereviewer-20260830
git diff --check
  exit 0; no output
```

The branch, exact start SHA, cleanliness, and initial whitespace check all matched the task
contract. No reset, rebase, merge, cherry-pick, stash, checkout, or repair was needed or used.

## Fixer diff inspected

The complete diff from `9f12d168a4ba5f43ecc48ad909765fa6254f24bb` to
`120092cdaafd80cd185060d51c93ca7516bfe2eb` changes only:

```text
docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md
```

Diff size: 131 insertions and 43 deletions. The changes add explicit dispositions, ownership,
acceptance rows, compatibility rules, boundary statements, limitations, and a Plan Fixer
verification addendum for all six accepted findings. No implementation or test file changed in
the Fixer diff.

## Six accepted findings

### P1-01 — complete disposition

- Current-source evidence: `scripts/build-enterprise-offline.sh:105-117` trusts a caller-controlled
  `COMMIT_SHA`; `:143-175` permits label-based `reuse`/`smart`; `:196-216` independently handles
  Web and currently passes the version string to both builds; `:280-323` records HEAD and mutable
  image metadata later. Those paths confirm the original provenance gap.
- Repaired-plan evidence: the selected solution A is explicit at
  `P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:115-121`; normal controls require both images
  to be rebuilt from a clean exact candidate at `:172-179`; ownership is assigned at `:222-225`;
  P01/P02 require explicit `-Mode rebuild` and reject `reuse`/`smart`, dirty, or mismatched
  candidates at `:272-273`; compatibility repeats that only rebuild can emit normal release
  provenance at `:293-296`.
- Result: both API and Web must traverse their audited contexts under explicit rebuild before
  normal release validation. Matching mutable labels cannot substitute. The plan expressly avoids
  a rebuild-record format, attestation framework, scanner, dependency, helper, Dockerfile, or
  Docker-ignore expansion (`:115-121`, `:227`). P1-01 is fully repaired.

### P1-02 — complete disposition

- Current-source evidence: `scripts/build-enterprise-config-package.sh:39-57` uses working-tree
  `find` plus two recursive directory operands; `:75-95` passes those recursive operands to `tar`.
  The checker also discovers the working tree at `scripts/ci/check-enterprise-offline.sh:328-339`.
- Candidate-tree evidence at the exact start SHA: `git ls-tree -r --name-only` yields 37 tracked
  `docker/envs/**/*.env.example` files, nine tracked nginx/SSRF files, and three fixed Docker files.
  With two version-matched generated members, the exact regular-file total is 51.
- Repaired-plan evidence: `P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:240-255` requires the
  exact 49 candidate-tracked source paths plus the two generated paths, reads the tracked set from
  the candidate tree, replaces recursive directory expansion, and fails on changed membership,
  untracked extras, unsafe paths, or non-regular members. C01/C02/C07/C08 at `:261-268` cover the
  exact count, a rogue untracked `*.env.example`, other extras, duplicates, unsafe paths, and wrong
  types.
- Result: working-tree discovery cannot define or expand the package input set, recursive directory
  operands are removed, and missing/extra/wrong-type evidence fails. P1-02 is fully repaired.

### P1-03 — complete disposition

- Current-source evidence: `scripts/build-enterprise-offline.sh:196-212` recursively copies the
  Web roots but prunes only dependency/generated directories. `web/Dockerfile.dockerignore:20-21`
  excludes only root `web/.env` and `web/.env.*`; `web/Dockerfile:37-45` then executes `COPY . .`.
- Repaired-plan evidence: the root cause and minimal producer-side prune are stated at
  `P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:93-107`; the disposition forbids Dockerfile or
  ignore-file edits at `:200`; W01 at `:271` places nested `.env` and `.env.*` canaries across the
  copied roots and proves every canary absent from the temporary context before `docker build`.
- Result: the production source allowlist stays unchanged while the temporary context is pruned and
  tested before build. No unnecessary Dockerfile or Docker-ignore change is introduced. P1-03 is
  fully repaired.

### P1-04 — complete disposition

- Current-source evidence: the public development default and warning markers are defined at
  `scripts/ci/check-enterprise-offline.sh:51-55`; the bounded rule is implemented at `:171-184`
  and currently exercised during config scanning at `:341-373`. The existing missing-warning
  regression is at `scripts/ci/check-enterprise-offline-tests.sh:364-378`.
- Repaired-plan evidence: the distinct safeguard is retained through bounded, non-extracting reads
  at `P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:147-162` and `:198`; R01 at `:282` requires
  both missing-warning failure and warned success. The Development boundary allows only this
  bounded public-default check while deleting normal `-SecretsPattern` and all first-/third-party
  layer-content scanning at `:306-312`.
- Result: the public development-default-with-warning safeguard remains without reviving generic
  protected-pattern handling or layer scanning. P1-04 is fully repaired.

### P2-01 — complete disposition

- Current-source evidence: `scripts/ci/check-enterprise-offline.sh:377-390` presently distinguishes
  an absent bundle as `NOT_RUN` from an observed malformed archive/layout as failure, while
  `:463-476` shows the old coverage aggregation ambiguity.
- Repaired-plan evidence: M05 and M07 at
  `P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:278-280` classify observed missing/malformed
  required identity or metadata as `FAIL` with nonzero exit. The general rule at `:286-289`
  reserves `NOT_RUN` for genuinely unexecuted environment prerequisites.
- Result: executed validation fails closed; missing required normal-gate evidence cannot become
  PASS or `NOT_RUN`. P2-01 is fully repaired.

### P2-02 — complete disposition

- Current-source evidence: `scripts/build-enterprise-offline.sh:313-320` records
  `{{index .RepoDigests 0}}` without matching that digest's repository to the image-list name.
- Repaired-plan evidence: normalized repository matching and the image-ID-only fallback are defined
  at `P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:137-145`; manifest ownership retains the
  rule at `:204-205`; M04 tests multiple/matching and mismatched-only RepoDigests at `:277`; the
  Development claim is limited to repository-matched provenance when claimed at `:314-320`; the
  limitation is preserved at `:330-331`.
- Result: a mismatched digest is never falsely attributed. With no repository match, the manifest
  records no registry-origin digest and retains only immutable image-ID bundle identity. P2-02 is
  fully repaired.

## Remaining required review questions

### Executability and baseline honesty

The future Builder has a narrow three-file production allowlist and two-file test allowlist at
`P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:210-238`. Ownership is explicit at `:222-225`.
C01-C08, A01-A02, W01, P01-P02, M01-M07, D01, and R01 define synthetic setup, expected result,
and nonzero failure behavior at `:257-289`. Builder and Reviewer commands and exact-result
reporting are specified at `:381-394`.

The existing 24 cases are described strictly as baseline at `:366-379`: the plan says they do not
prove that revised Builder behavior or synthetic cases exist. The required new suite must report
its newly observed total (`:284`). This is executable enough for a future Builder and independent
Code Reviewer without treating plan text or baseline tests as implementation evidence.

### Smallest allowlists and prohibitions

The production allowlist remains exactly:

```text
scripts/build-enterprise-offline.sh
scripts/build-enterprise-config-package.sh
scripts/ci/check-enterprise-offline.sh
```

The test allowlist remains exactly:

```text
scripts/ci/check-enterprise-offline-tests.sh
scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker
```

`fake-git` remains unchanged. The plan excludes new helpers, dependencies, Dockerfiles,
Docker-ignore files, Compose, application code, PowerShell, and scanner frameworks at
`P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:181-189`, `:210-238`. Development may use only
repository source, fake commands, standard-library metadata parsing, bounded exact-member reads,
and synthetic/public canaries (`:302-312`). It forbids Docker, network, built release artifact
contents, protected patterns, real credentials, production/gray/Plan B values, target
configuration, runtime volumes, and target connections.

Historical protected-audit hits remain redacted and unclassified (`:322-326`). A Protected release
audit remains separate and requires explicit authorization for its runner and named artifacts; it
authorizes no target access, deployment, secret rotation, or rewrite. The repaired plan therefore
preserves both the smallest allowlists and every stated environment/secret prohibition.

## Findings

P0: none.

P1: none remaining. P1-01, P1-02, P1-03, and P1-04 retain their accepted P1 severity and are fully
disposed.

P2: none remaining. P2-01 and P2-02 retain their accepted P2 severity and are fully disposed.

P3: none.

No new finding was introduced.

## Commands and evidence with PASS/FAIL/NOT_RUN counts

| Command/evidence | PASS | FAIL | NOT_RUN | Result |
| --- | ---: | ---: | ---: | --- |
| Required branch/SHA/clean/initial-diff preflight | 4 | 0 | 0 | Exact branch and SHA, clean status, `git diff --check` exit 0. |
| Fixer diff name/scope inspection | 1 | 0 | 0 | One Architect plan file; 131 insertions, 43 deletions. |
| Exact candidate-tree configuration inventory | 3 groups | 0 | 0 | 37 env examples + 9 nginx/SSRF + 3 fixed Docker source files; plus 2 generated = 51. |
| `bash -n` over the four authorized offline shell scripts | 4 files | 0 | 0 | Exit 0; no output. |
| Initial combined focused-suite observation | 21 observed | 0 observed | 1 completion status | The tool yielded after 21 visible `ok` rows; not used as acceptance evidence. |
| Authoritative standalone `bash scripts/ci/check-enterprise-offline-tests.sh` | 24 cases | 0 | 0 | Exit 0; `all 24 enterprise offline tests passed`. Baseline only. |
| Final index-state evidence | 1 | 0 | 0 | `git status` reports ` A`; the index contains only the empty intent-to-add blob, so no report content is staged. |
| Final tracked and new-file whitespace checks | 2 | 0 | 0 | Recorded after the report write below. |
| Real Docker build/save/load/run/inspect and artifact runtime validation | 0 | 0 | 1 | `NOT_RUN`: forbidden in this Development plan rereview. |
| Docker-ignore runtime evaluation | 0 | 0 | 1 | `NOT_RUN`: no Docker daemon use authorized. |
| PowerShell parity/runtime | 0 | 0 | 1 | `NOT_RUN`: outside the plan and unavailable evidence. |
| Protected release audit and historical-hit classification | 0 | 0 | 1 | `NOT_RUN`: separate explicit authorization and secure runner required. |
| Isolated upgrade rehearsal and true offline-host boot | 0 | 0 | 1 | `NOT_RUN`: not authorized by this plan-quality review. |
| Browser, network, target, signing, deployment, database, vector, container, and volume actions | 0 | 0 | 1 | `NOT_RUN`: forbidden and unnecessary for this review. |

The 24-case baseline proves only the current fake-Docker regression suite. It is not proof of any
unimplemented P1/P2 repair, real Docker behavior, release artifact, or runtime environment.

## Planned versus actual changes

| Item | Planned | Actual | Deviation |
| --- | --- | --- | --- |
| Write scope | New rereview report only | New rereview report only | The report remains in Git's empty intent-to-add state; no report content is staged. |
| Architect/source/test changes | None | None | None. |
| Review evidence | Fixer diff, plan/review/current state, named shell/Docker-ignore/fake-Docker sources | Inspected read-only | None. |
| Authorized checks | Preflight, four-file syntax, baseline suite, diff/status | Completed with results above | The first suite observation yielded; a standalone authoritative rerun completed 24/24. |
| Runtime/external actions | None | None | None. |

## Final whitespace and status evidence

Final `git diff --check`: PASS (exit 0, no output).

Because the report content exists only in the working tree while the index holds an empty
intent-to-add marker, `git diff --no-index --check /dev/null
docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_PLAN_REREVIEW_2026-08-30.md` was also used;
it reported no whitespace errors. Its expected status 1 means only that the file differs from
`/dev/null`.

Final exact modified-file list:

```text
docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_PLAN_REREVIEW_2026-08-30.md
```

Final status:

```text
## ctyun/replay-116-minimum-offline-gate-plan-rereviewer-20260830
 A docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_PLAN_REREVIEW_2026-08-30.md
```

## Commit ID: none

No report content is staged: Git's index entry is the empty intent-to-add blob and the complete
report remains a working-tree change. No index-changing command was run during this bounded
correction. No commit, amend, push, merge, rebase, cherry-pick, tag, working-tree deletion, Docker
action, network action, protected-data access, target action, or other external-state change
occurred.

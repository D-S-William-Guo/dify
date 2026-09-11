# P1-OFFLINE-01 Docker-save order rereview

Date: 2026-09-11 (Asia/Shanghai)

Role: independent Rereviewer (`codex-sol`)

Environment: Development / isolated rehearsal

## Verdict: PASS

The accepted fix in
`acee5da413d573f09074ed238158021e90114058..8a042ce262ad849feb13b04f77ba3b7812907dd4`
correctly treats Docker-save manifest record order as non-contractual while preserving exact,
duplicate-free tag membership and the tag-to-Config-to-release-manifest image-ID binding. The
focused synthetic suite passed all 65 cases. No P0, P1, or P2 finding remains.

## Immutable start

The required preflight ran before inspection or writes:

```text
git branch --show-current
  ctyun/replay-116-docker-save-order-rereviewer-20260911
git rev-parse HEAD
  8a042ce262ad849feb13b04f77ba3b7812907dd4
git status --short --branch
  ## ctyun/replay-116-docker-save-order-rereviewer-20260911
```

The branch and exact SHA matched the contract, and the worktree was clean. No repair, checkout,
merge, rebase, reset, or cherry-pick was performed.

## Exact reviewed change

The range contains one commit, `8a042ce262 fix(offline): validate save tag sets`, and exactly two
modified files:

| File | Insertions | Deletions |
| --- | ---: | ---: |
| `scripts/ci/check-enterprise-offline-tests.sh` | 54 | 0 |
| `scripts/ci/check-enterprise-offline.sh` | 3 | 3 |

No production behavior outside the Docker-save final tag comparison changed. The test-only change
adds a standard-library tar/JSON mutation helper and four focused cases. No code, test, or document
outside this exact range was part of the accepted fix.

## Behavior and evidence

| Required invariant | Evidence | Result |
| --- | --- | --- |
| Reordered legal Docker-save records pass | `scripts/ci/check-enterprise-offline.sh:297-318` validates records independently, then compares a duplicate-free tag set instead of list order. `scripts/ci/check-enterprise-offline-tests.sh:477-486` reverses all records without changing their data. The focused run printed `ok - P1-OFFLINE-01 reordered Docker-save records pass`. | PASS |
| Missing tags fail closed | The exact-set comparison at `scripts/ci/check-enterprise-offline.sh:316-317` rejects the reduced tag set. The mutation at `scripts/ci/check-enterprise-offline-tests.sh:203` removes one record; the focused run printed the expected-failure case as `ok`. | PASS |
| Duplicate tags fail closed | `scripts/ci/check-enterprise-offline.sh:316` compares list length with set length. The mutation at `scripts/ci/check-enterprise-offline-tests.sh:204` repeats an existing tag; the expected-failure case passed. | PASS |
| Extra tags fail closed | Each tag must exist in `manifest_images` at `scripts/ci/check-enterprise-offline.sh:312-315`, and final set equality is also required at `:316-317`. The unknown-tag mutation at `scripts/ci/check-enterprise-offline-tests.sh:205` failed as required. | PASS |
| Every unique tag remains bound through Config digest to release-manifest image ID | Config paths are canonicalized and restricted to the accepted legacy/Docker-29 digest forms at `scripts/ci/check-enterprise-offline.sh:301-305`; exactly one regular Config member is required at `:306-308`; each tag's release-manifest ID must equal that Config digest at `:312-315` before the tag can enter the accepted set. | PASS |
| Image-list and release-manifest ordering checks remain unchanged | `scripts/ci/check-enterprise-offline.sh:121-127` still requires sorted unique image-list entries, and `:167-169` still requires release-manifest names to exactly match image-list order. The accepted diff does not touch either check; the retained M02 reorder expected-failure case passed. | PASS |
| No scope expansion | `git diff --name-only` reports only the checker and its focused test script; the range is 57 insertions and 3 deletions. No dependency, CLI, artifact format, runtime, layer scan, or external-system behavior changed. | PASS |

## Findings

### P0

None.

### P1

None. P1-OFFLINE-01 is closed by the accepted fix.

### P2

None.

There is no violated invariant, failing reproduction, or repair boundary to prescribe. The repair
boundary is none.

## Verification commands and counts

| Exact command | PASS | FAIL | NOT_RUN | Evidence/result |
| --- | ---: | ---: | ---: | --- |
| `git branch --show-current`; `git rev-parse HEAD`; `git status --short --branch` | 3 | 0 | 0 | Expected branch, exact HEAD, and clean start. |
| `bash -n scripts/ci/check-enterprise-offline.sh scripts/ci/check-enterprise-offline-tests.sh` | 2 files | 0 | 0 | Exit 0; no output. |
| `env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C bash scripts/ci/check-enterprise-offline-tests.sh` | 65 cases | 0 | 0 | Authoritative captured run exited 0 with `all 65 enterprise offline tests passed`. An earlier identical invocation exceeded its 30-second output-capture window after 16 printed cases; it was not used as completion evidence, and the fully captured rerun supplies the result. |
| `git diff --check acee5da413d573f09074ed238158021e90114058..8a042ce262ad849feb13b04f77ba3b7812907dd4` | 1 | 0 | 0 | Exit 0; no output. |
| `git diff --check` | 1 | 0 | 0 | Exit 0; no output after writing this report. |
| `git status --short --branch` | 1 | 0 | 0 | Final status shown below; only this authorized report has an intent-to-add index entry and working-tree content. |
| Real Docker daemon/build/save/load/run and true offline-host validation | 0 | 0 | 1 | NOT_RUN: expressly forbidden; the repository suite used fake Docker only. |
| Real `dist/offline/rehearsal-acee5da4` or `/tmp/replay-116-config-acee5da4` artifact execution/modification | 0 | 0 | 1 | NOT_RUN: not needed for the smallest focused verification; both paths remained untouched. |
| PowerShell parity, protected audit, browser, network, services, databases, vectors, volumes, deployment, gray/production targets, and real secret/pattern/proxy handling | 0 | 0 | 1 | NOT_RUN: outside scope or forbidden and not substitutable with synthetic tests. |

## Final repository state

`git diff --check` exited 0 with no output.

Final `git status --short --branch`:

```text
## ctyun/replay-116-docker-save-order-rereviewer-20260911
 A docs/enterprise/replay-1.16.0/P0_DOCKER_SAVE_ORDER_REREVIEW_2026-09-11.md
```

`git ls-files --stage` reports mode `100644` and the empty-blob object
`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` for the report. `git diff --cached --name-only`
and `git diff --cached --stat` both produce no output: the intent-to-add entry exists, but no
report content is staged.

Exact modified file: only
`docs/enterprise/replay-1.16.0/P0_DOCKER_SAVE_ORDER_REREVIEW_2026-09-11.md`.

No report content was staged. No commit, amend, push, pull, fetch, PR, merge, rebase, reset,
checkout, cherry-pick, Docker, service, database, volume, deployment, external-system, or deletion
action occurred.

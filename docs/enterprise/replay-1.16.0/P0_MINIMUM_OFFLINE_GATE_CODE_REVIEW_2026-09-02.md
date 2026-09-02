# Enterprise 1.16.0 minimum offline artifact gate code review

Date: 2026-09-02 (Asia/Shanghai)

Role: independent Code Reviewer (`codex-sol`)

Environment: Development / isolated rehearsal

## Verdict: PASS

The exact Builder change from `9a55680ec449d75e17e7cd9f10e8761e5393be2f` to
`60bd4df96c46c6a218eb7f5758fd53469dd812ed` implements the accepted minimum
offline gate. Source inspection and the focused synthetic suite found no P0,
P1, or P2 defect.

This verdict covers only the normal Development gate: candidate-bound
construction inputs, first-party context boundaries, rebuild provenance,
configuration/archive metadata, immutable image identity, Docker-save metadata,
and the bounded public-default warning. It does not claim real Docker, real
artifact, PowerShell, protected-audit, offline-host, or target runtime evidence.

## Immutable preflight

The required preflight ran before any write:

```text
git branch --show-current
  ctyun/replay-116-minimum-offline-gate-code-reviewer-20260902
git rev-parse HEAD
  60bd4df96c46c6a218eb7f5758fd53469dd812ed
git status --short
  no output; clean
git diff --stat
  no output
git diff --cached --stat
  no output
```

Branch, exact HEAD, clean start, unstaged diff, and staged diff all matched the
review contract. No repair, reset, checkout, merge, rebase, commit, stage, push,
Docker, network, browser, artifact, credential, secret-pattern, target,
deployment, migration, volume, or deletion action was used.

## Exact reviewed change

The range contains one commit and exactly five changed files:

```text
M  scripts/build-enterprise-config-package.sh
M  scripts/build-enterprise-offline.sh
M  scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker
M  scripts/ci/check-enterprise-offline-tests.sh
M  scripts/ci/check-enterprise-offline.sh
```

Range size: 827 insertions, 915 deletions.

Per-file range counts:

| File | Insertions | Deletions |
| --- | ---: | ---: |
| `scripts/build-enterprise-config-package.sh` | 67 | 34 |
| `scripts/build-enterprise-offline.sh` | 76 | 58 |
| `scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker` | 78 | 53 |
| `scripts/ci/check-enterprise-offline-tests.sh` | 311 | 316 |
| `scripts/ci/check-enterprise-offline.sh` | 295 | 454 |

No file outside the accepted three-file production and two-file test allowlists
changed.

## Accepted requirements

| Requirement | Source and behavior inspected | Result |
| --- | --- | --- |
| Rebuild-only release provenance | `scripts/build-enterprise-offline.sh:47-75` rejects non-check-only `reuse`/`smart`, binds the run to a clean 40-hex HEAD, and `:142-206` rebuilds API and Web with that SHA then re-inspects both labels. `:330-340` records `mode=rebuild` and `release_gate=true` only for the non-check-only rebuild. Synthetic P01/P02 and M03 cover explicit rebuild, convenience-mode rejection, dirty input, and label mismatch. | PASS |
| Exact candidate config membership | `scripts/build-enterprise-config-package.sh:60-106` uses the candidate tree for the 37 env examples, fixes the nine nginx/SSRF members, checks all 49 tracked source files and their working-tree equality, and rejects root expansion. `:108-127` adds only the two version-matched generated regular files. The checker independently derives and enforces exactly 51 members at `scripts/ci/check-enterprise-offline.sh:195-258`. C01-C08 exercise the exact set, canaries, missing/extra members, unsafe paths, duplicates, and wrong types. Candidate inventory observed 37 env examples + 9 nginx/SSRF files + 3 fixed Docker files + 2 generated files = 51. | PASS |
| API root context | `scripts/build-enterprise-offline.sh:198` uses `api/Dockerfile` with repository root as the final build context. The existing `api/Dockerfile.dockerignore:1-37` remains deny-by-default and admits only API plus required `dify-agent` inputs while excluding environment/runtime paths. A01/A02 verify the call and ignore contract. | PASS |
| Web nested-env boundary | `scripts/build-enterprise-offline.sh:178-195` retains the narrow temporary source roots and removes every nested `.env`/`.env.*` file, directory, or link before the build call. W01 places synthetic nested canaries and inspects the captured context. | PASS |
| Bounded public-default warning | `scripts/ci/check-enterprise-offline.sh:49-50,224-272` reads only bounded, exact regular config members without extraction and rejects the known public default unless a retained warning marker is in the same member. R01 proves the missing-warning failure and warned success. | PASS |
| Normal pattern/layer scans removed | The checker CLI at `scripts/ci/check-enterprise-offline.sh:10-29` accepts only the four normal artifacts. No `SecretsPattern`, `layer.tar`, `docker run/load/export`, archive extraction, or layer-content path remains in the production producer/checker. D01 confirms the suite uses only the shim and observes no retired call or scan path. | PASS |
| Immutable IDs and RepoDigest provenance | `scripts/build-enterprise-offline.sh:280-327` requires a `sha256:` image ID for every image, parses RepoDigests fail-closed, records only a digest whose repository matches the image-list repository, and otherwise warns while retaining image-ID identity. `scripts/ci/check-enterprise-offline.sh:131-193` revalidates candidate, ordering, IDs, and any claimed RepoDigest. M01-M05 cover the valid graph, mismatch/absence/reordering, candidate mismatch, malformed IDs, matching multiple digests, and mismatched-only fallback. | PASS |
| Docker-save metadata fail-closed | `scripts/ci/check-enterprise-offline.sh:276-320` bounds archive headers, requires one regular top-level `manifest.json`, validates size/JSON/shape, accepts legacy and Docker 29 Config paths, requires one regular Config member, and binds ordered RepoTags and Config digests to the release manifest without reading layers. M06 covers both Config layouts; all six M07 missing/duplicate/nonregular/malformed/oversized/inconsistent cases fail nonzero. | PASS |
| Synthetic suite scope | `scripts/ci/check-enterprise-offline-tests.sh` uses local shared clones, generated canaries/archives, the fake Docker shim, and standard tools. It neither calls a real daemon nor reads protected values. The suite reports its observed total rather than the historical total. | PASS, 51/51 |

## Findings

### P0

None.

### P1

None.

### P2

None.

There is therefore no violated invariant, failing reproduction, or repair to
prescribe. The smallest repair is none.

## Commands and counts

| Command/evidence | PASS | FAIL | NOT_RUN | Result |
| --- | ---: | ---: | ---: | --- |
| Branch/HEAD/status/unstaged-diff/staged-diff preflight | 5 | 0 | 0 | Exact branch and SHA; clean start; both diffs empty. |
| `git rev-list --count 9a55680e..60bd4df9` | 1 commit | 0 | 0 | One Builder commit. |
| `git diff --name-status`, `--stat`, and `--numstat` over the exact range | 5 files | 0 | 0 | Only the accepted allowlists; 827 insertions, 915 deletions. |
| Candidate config inventory (`git ls-tree`) | 49 source files | 0 | 0 | 37 env examples + 9 nginx/SSRF + 3 fixed Docker files; two generated files make 51. |
| Retired-path search over the production producer/checker | 1 search | 0 matches | 0 | No normal protected-pattern, layer, run/load/export path. |
| `bash -n` over all five changed shell/fixture files | 5 files | 0 | 0 | Exit 0; no output. |
| `bash scripts/ci/check-enterprise-offline-tests.sh` | 51 cases | 0 | 0 | Exit 0; `all 51 enterprise offline tests passed`. |
| Range whitespace check | 1 | 0 | 0 | `git diff --check 9a55680e..60bd4df9` exited 0 with no output. |
| Real Docker build/save/load/run/inspect and Docker-ignore runtime evaluation | 0 | 0 | 1 | NOT_RUN: forbidden in this Development review. |
| Real release artifact inspection or runtime | 0 | 0 | 1 | NOT_RUN: no real artifact was authorized. |
| PowerShell parity/runtime | 0 | 0 | 1 | NOT_RUN: outside the Builder range and no runtime authorized. |
| Protected release audit and historical-hit classification | 0 | 0 | 1 | NOT_RUN: requires separate authorization and a secure runner. |
| True offline-host boot, browser, network, target, signing, deployment, database, vector, container, migration, and volume actions | 0 | 0 | 1 | NOT_RUN: forbidden and not substitutable with synthetic tests. |

## Planned versus actual

| Item | Planned | Actual | Deviation |
| --- | --- | --- | --- |
| Production scope | Three accepted shell files | Exactly those three files | None. |
| Test scope | Test script plus fake Docker shim | Exactly those two files | None. |
| Normal release provenance | Clean exact-candidate rebuild of API and Web | Implemented and synthetically verified | None. |
| Config construction | Exact 49 candidate sources plus two generated members | Implemented and synthetically verified at 51 members | None. |
| Context controls | API root context; nested Web env prune | Implemented and synthetically verified | None. |
| Normal scanning | Remove protected-pattern and first-/third-party layer scans; retain bounded public-default warning | Implemented and synthetically verified | None. |
| Identity and save metadata | Fail closed on malformed/missing evidence; repository-match RepoDigests | Implemented and synthetically verified | None. |
| Reviewer write scope | This review report only | This review report only | None. |
| Runtime/external actions | None | None | None. |

## Final repository state

Final `git status --short` reports only:

```text
 A docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_CODE_REVIEW_2026-09-02.md
```

This is an intent-to-add index entry for the empty blob
`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`, with index flags `20004000`.
The report body itself is not staged: `git diff --cached` and `git diff
--cached --stat` remain empty, while the working-tree diff contains the report
body. Read-only working-tree, cached, and new-file whitespace checks report no
whitespace error. No Builder file, test, or other documentation was modified.

Commit ID: none.

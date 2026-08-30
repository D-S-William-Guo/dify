# Enterprise 1.16.0 minimum offline artifact gate plan review

Date: 2026-08-30 (Asia/Shanghai)

Role: Plan Reviewer

Environment: Development / isolated rehearsal

## Verdict: CHANGES_REQUIRED

The accepted direction is correct: exact construction inputs, auditable first-party contexts,
candidate and immutable-image identity, bounded Docker-save metadata checks, and synthetic
canaries can replace normal `-SecretsPattern` processing and layer-content scanning. The plan
does not yet preserve that policy end to end. Four P1 gaps permit non-candidate or local content
to pass the proposed construction gate, or remove the existing public development-default
safeguard without a replacement. Two P2 gaps make dependency provenance and result reporting
ambiguous.

No full third-party or first-party layer scanner, protected-pattern path, new dependency,
Dockerfile, Docker-ignore, Compose, application, PowerShell, or helper file is justified.

## Start branch and SHA

- Expected branch: `ctyun/replay-116-minimum-offline-gate-plan-reviewer-20260830`
- Verified branch: `ctyun/replay-116-minimum-offline-gate-plan-reviewer-20260830`
- Expected HEAD: `8f5a5d6c973006e5127f8912849968d02f4a1457`
- Verified HEAD: `8f5a5d6c973006e5127f8912849968d02f4a1457`
- Initial status: clean

The required preflight ran before source inspection:

```text
git branch --show-current
  ctyun/replay-116-minimum-offline-gate-plan-reviewer-20260830
git rev-parse HEAD
  8f5a5d6c973006e5127f8912849968d02f4a1457
git status --short --branch
  ## ctyun/replay-116-minimum-offline-gate-plan-reviewer-20260830
```

## Exact modified files

```text
docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_PLAN_REVIEW_2026-08-30.md
```

No Architect plan, source, test, fixture, Docker, API, Web, Agent, or deployment file was
modified.

## Independent evidence and commands with exact PASS/FAIL/NOT_RUN counts

The review derived its claims from the named repository source and tests, plus the directly
referenced API/Web Dockerfiles, Dockerfile-specific ignore files, Compose context declaration,
and existing fake command fixtures. It did not use Architect assertions as proof.

| Command/evidence | PASS | FAIL | NOT_RUN | Result |
| --- | ---: | ---: | ---: | --- |
| Required branch/SHA/clean preflight | 3 | 0 | 0 | Exact branch and SHA; clean status. |
| `bash -n scripts/build-enterprise-offline.sh scripts/build-enterprise-config-package.sh scripts/ci/check-enterprise-offline.sh scripts/ci/check-enterprise-offline-tests.sh` | 4 | 0 | 0 | Exit 0; no output. |
| Authoritative `bash scripts/ci/check-enterprise-offline-tests.sh` rerun | 24 | 0 | 0 | Exit 0; `all 24 enterprise offline tests passed`. |
| Initial focused-suite invocation | 22 observed | 0 observed | 1 completion status | The command yielded at 30 seconds after 22 visible `ok` rows; it is not counted as acceptance evidence. The standalone rerun above completed. |
| Real Docker build/save/load/run and real artifact inspection | 0 | 0 | 1 | `NOT_RUN`: forbidden in this Development review. |
| Docker-ignore runtime evaluation | 0 | 0 | 1 | `NOT_RUN`: no Docker daemon use authorized; source semantics reviewed. |
| PowerShell runtime/parity | 0 | 0 | 1 | `NOT_RUN`: outside this plan and runtime unavailable. |
| Protected release audit | 0 | 0 | 1 | `NOT_RUN`: separately authorized secure runner required. |
| Browser, network, target, database, container, and volume checks | 0 | 0 | 1 | `NOT_RUN`: forbidden and unnecessary for this plan review. |

The 24/24 result proves only the current implementation's fake-Docker regressions. It cannot
prove that the proposed replacement tests or controls are sufficient.

Useful source-verification commands:

```bash
nl -ba scripts/build-enterprise-offline.sh | sed -n '105,216p'
nl -ba scripts/build-enterprise-config-package.sh | sed -n '39,95p'
nl -ba scripts/ci/check-enterprise-offline.sh | sed -n '94,190p;225,483p'
nl -ba scripts/ci/check-enterprise-offline-tests.sh | sed -n '99,215p;245,393p'
nl -ba api/Dockerfile.dockerignore
nl -ba web/Dockerfile.dockerignore
nl -ba web/Dockerfile | sed -n '24,45p;77,85p'
find docker/envs -type f -name '*.env.example' -printf '%p\n' | sort
find docker/nginx docker/ssrf_proxy -type f -printf '%p\n' | sort
```

At this SHA the final two commands show 37 env examples and nine fixed nginx/SSRF files, so the
intended 51 regular-member total is arithmetically correct: 3 fixed Docker files + 2 generated
files + 37 env examples + 9 nginx/SSRF files.

## P0/P1/P2/P3 findings

### P0 findings

None.

### P1 findings

#### P1-01 — A `COMMIT_SHA` label does not prove a reused image was built from that commit

- Evidence: `scripts/build-enterprise-offline.sh:105-117` accepts caller-controlled image
  metadata as the reuse decision. The current narrow content checks at lines 119-141 are the
  only independent same-label stale-content guard, and the accepted plan at
  `P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md:176-177` deletes them. Proposed rows P01/P02
  at lines 236-237 again test only the label. The proposed Docker-save parser at line 126 reads
  only `manifest.json`; it binds config IDs but does not establish how the labeled image was
  built.
- Violated invariant: both first-party images must be bound to the exact candidate SHA, not
  merely carry a matching mutable metadata string.
- Verification command:

  ```bash
  sed -n '105,141p' scripts/build-enterprise-offline.sh
  sed -n '118,126p;176,183p;233,244p' \
    docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md
  sed -n '195,215p' scripts/ci/check-enterprise-offline-tests.sh
  ```

- Exact repair boundary: P01 must reject label-only reuse. Either force both first-party images
  through the audited build contexts for the accepted candidate, or require an already accepted
  rebuild record that binds the candidate SHA to the exact API/Web image IDs and verify those IDs
  before reuse and against Docker-save metadata. Retain the current narrow probes until that
  provenance exists. Do not add a layer scanner, attestation framework, dependency, or Dockerfile
  change.

#### P1-02 — The configuration input set remains working-tree-discovered, not candidate-exact

- Evidence: `scripts/build-enterprise-config-package.sh:47-52` includes every working-tree file
  matching `docker/envs/**/*.env.example`. The plan at lines 149 and 212-219 requires an exact
  candidate set, but line 170 retains a “deterministic env-example set” without defining tracked
  provenance. C02 at lines 225-226 does not add a rogue `.env.example` canary, and the current
  test at `scripts/ci/check-enterprise-offline-tests.sh:278-282` verifies only that the observed
  count is 37. Once content scanning is removed, an untracked allowed-suffix file is packaged
  without another normal safeguard.
- Violated invariant: configuration-package inputs and regular members must equal the accepted
  candidate's explicit allowlist; local working-tree discovery must not expand it.
- Reproduction command for a disposable synthetic clone only:

  ```bash
  fixture=$(mktemp -d)
  git clone --quiet --shared --no-tags . "$fixture/repo"
  mkdir -p "$fixture/repo/dist/offline" "$fixture/repo/docker/envs/review-canary"
  : > "$fixture/repo/dist/offline/manifest-1.16.0-enterprise.json"
  : > "$fixture/repo/dist/offline/images-1.16.0-enterprise.txt"
  printf 'SYNTHETIC_ONLY=1\n' > "$fixture/repo/docker/envs/review-canary/rogue.env.example"
  "$fixture/repo/scripts/build-enterprise-config-package.sh"
  tar tzf "$fixture/repo/dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz" \
    | grep -F 'docker/envs/review-canary/rogue.env.example'
  ```

- Exact repair boundary: derive the 37 env examples from candidate-tracked paths (or enumerate
  them explicitly), fail if the set differs, and package only that set plus the nine named fixed
  files and five other approved files. Extend C02/C08 with an untracked
  `rogue.env.example` canary. No new manifest format or helper is needed.

#### P1-03 — The Web context can copy nested local environment files despite the claimed boundary

- Evidence: `scripts/build-enterprise-offline.sh:201-206` recursively copies `web`, then prunes
  dependency/generated directories but no environment files. `web/Dockerfile.dockerignore:20-21`
  excludes only `web/.env` and `web/.env.*`, not nested `web/**/.env*` paths. The builder stage's
  `COPY . .` at `web/Dockerfile:40` receives every remaining admitted Web path. The plan claims at
  lines 90-96 and W01 at line 235 that the existing ignore contract excludes environment paths,
  but W01 only inspects the presence of patterns and does not exercise this nested-path case.
- Violated invariant: the first-party Web context must be structurally unable to send local
  environment/runtime inputs and must remain auditable before content scanning is removed.
- Verification command:

  ```bash
  sed -n '196,212p' scripts/build-enterprise-offline.sh
  sed -n '1,36p' web/Dockerfile.dockerignore
  sed -n '36,45p' web/Dockerfile
  ```

- Exact repair boundary: keep the production allowlist unchanged. In
  `scripts/build-enterprise-offline.sh`, construct the temporary context from candidate-tracked
  source or prune all nested `.env`/`.env.*` paths before `docker build`. Extend W01 and the
  existing fake-Docker fixture to place nested synthetic env canaries and assert they are absent
  from the build context. A Docker-ignore edit is unnecessary if the context producer enforces
  the boundary.

#### P1-04 — Deleting generic content scanning also deletes a distinct public development-default safeguard

- Evidence: `scripts/ci/check-enterprise-offline.sh:171-184` rejects the known public development
  default when it lacks a warning; lines 346-373 apply that rule to config members. The current
  regression at `scripts/ci/check-enterprise-offline-tests.sh:364-378` proves the behavior without
  any protected pattern. The plan drops config content scanning at line 173 and the layer/pattern
  machinery at lines 181-182, but its acceptance matrix has no explicit replacement; R01 at line
  246 only says “retained” regressions and does not decide whether this test is retained.
- Violated invariant: dropping normal protected-pattern and broad layer scans must not silently
  remove a separate, synthetic/public development-default safeguard.
- Verification command:

  ```bash
  sed -n '155,190p;341,375p' scripts/ci/check-enterprise-offline.sh
  sed -n '364,378p' scripts/ci/check-enterprise-offline-tests.sh
  sed -n '168,183p;221,248p' \
    docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md
  ```

- Exact repair boundary: explicitly retain the known public-default-with-warning rule and its
  synthetic canary, reading only bounded exact regular config members with Python `tarfile` and
  no extraction. Remove `-SecretsPattern`, protected input handling, and all layer content scans
  as planned. Do not generalize this into a scanner framework.

### P2 findings

#### P2-01 — M05 and M07 misclassify observed validation failures as `NOT_RUN`

- Evidence: plan rows M05 and M07 at lines 242 and 244 classify malformed/missing immutable
  identities and malformed/missing Docker-save metadata as `NOT_RUN`, although the checker ran,
  observed invalid input, and must exit nonzero.
- Violated invariant: `FAIL` means an executed check rejected evidence; `NOT_RUN` is reserved for
  an unexecuted environment-dependent check. Gate evidence must remain auditable and fail closed.
- Verification command:

  ```bash
  sed -n '238,246p' \
    docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md
  sed -n '79,92p;478,483p' scripts/ci/check-enterprise-offline.sh
  ```

- Exact repair boundary: change M05 and M07 to `FAIL` plus nonzero. Use `NOT_RUN` only when an
  authorized artifact/runtime prerequisite was not executed or supplied; do not allow a missing
  required normal-gate artifact to reach PASS.

#### P2-02 — A syntactically valid first RepoDigest is not repository provenance

- Evidence: `scripts/build-enterprise-offline.sh:313-320` records `index .RepoDigests 0` for each
  image. An image may have multiple repository digests, and the first need not correspond to the
  repository named by that image-list entry. Plan row M04 at line 241 requires only a valid
  RepoDigest or image ID, while lines 121 and 282 distinguish registry-origin provenance from
  bundle identity.
- Violated invariant: dependency provenance must not attribute a digest from one repository to a
  differently named dependency. Image ID may pin bundled content but does not prove registry
  origin.
- Verification command:

  ```bash
  sed -n '292,320p' scripts/build-enterprise-offline.sh
  sed -n '118,126p;238,244p;279,286p' \
    docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md
  ```

- Exact repair boundary: select and validate a RepoDigest whose normalized repository matches the
  image-list name's repository. If none matches, record no registry-origin digest and rely only on
  the valid image ID for immutable bundle identity, preserving provenance as an explicit
  limitation. Add one multiple/mismatched-RepoDigest fake case; no registry call or new dependency.

### P3 findings

None.

## Acceptance conditions and smallest Builder/test allowlists

The plan can pass after all six findings are repaired in the plan and behavioral matrix. The
smallest implementation allowlists remain:

Production Builder:

```text
scripts/build-enterprise-offline.sh
scripts/build-enterprise-config-package.sh
scripts/ci/check-enterprise-offline.sh
```

Tests/fixture:

```text
scripts/ci/check-enterprise-offline-tests.sh
scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker
```

No change to `fake-git` is needed. No new file, package, scanner, Dockerfile, Docker-ignore,
Compose, API, Web, Agent, PowerShell, or documentation production change is accepted.

Required behavioral repairs:

| Row | Acceptance condition |
| --- | --- |
| C01/C08 | The candidate-tracked 51-member regular-file set is exact; missing, extra, duplicate, unsafe, or wrong-type members fail. |
| C02 | Add a rogue untracked `*.env.example` canary and prove it is not packaged, in addition to env/volume/key/certificate/credential canaries. |
| A01/A02 | Keep root API context plus the existing deny-by-default Dockerfile-specific ignore contract; no API Dockerfile/ignore edit. |
| W01 | Prove nested synthetic `.env`/`.env.*` files cannot enter the temporary Web context; source-pattern presence alone is insufficient. |
| P01/P02 | Label-only reuse fails; reuse requires accepted candidate-to-image-ID provenance, or first-party rebuild is required. |
| M01/M03 | Bind candidate provenance, release manifest IDs, image list, and Docker-save config IDs for both first-party images. |
| M04 | Match RepoDigest repository provenance to the named dependency; otherwise use image ID only and retain the limitation. |
| M05/M07 | Invalid or missing required identity/metadata is `FAIL`, never `NOT_RUN`, and overall exit is nonzero. |
| R01 | Explicitly retain the public development-default warning regression without protected patterns or broad scanning. |
| D01 | Confirm no real Docker daemon, protected value/pattern, layer extraction, or layer content scan. |

All other accepted rows remain necessary. The suite must report its newly observed exact total;
the current 24/24 count is baseline evidence only.

## Development-versus-Protected-release boundary

This review accepts removal of normal `-SecretsPattern` handling and all first-/third-party layer
content scanning only after the construction findings above are closed. The Development gate may
use repository source, candidate-tracked paths, fake commands, Python standard-library metadata
parsing, and synthetic/public canaries only.

It must not read, hash, scan, request, or process real production/gray/Plan B values, protected
patterns, target configuration, runtime volumes, or built release artifact content. It may not
use Docker, network, browser, target connections, or external state.

Historical protected-audit hits remain redacted and unclassified. This review does not call them
clean, false positives, resolved, safe, or attributable. A separately authorized Protected
release audit on a designated secure runner and named unchanged artifacts remains required for
release guidance; it authorizes no target access, deployment, secret rotation, or artifact rewrite.

## Known limitations and actions still unauthorized

- Real first-party build and Docker-ignore runtime behavior remain `NOT_RUN`.
- Real Docker-save/load/boot and true no-network-host verification remain `NOT_RUN`.
- Dependency image ID pins bundled content but does not establish registry origin when no matching
  RepoDigest exists.
- Publisher signatures, SBOM attestation, and formal artifact signing remain `NOT_RUN`.
- PowerShell parity/runtime remains `NOT_RUN` and is not claimed.
- Protected audit, historical-hit classification, production/gray access, target configuration,
  deployment, migration, database/vector/volume work, container changes, browser checks, network
  calls, and external-state actions remain unauthorized.
- No old broad-scan Plan Fixer worktree or diff was read, changed, classified, merged, or recommended
  for merge.

## Planned versus actual changes

| Item | Planned | Actual | Deviation |
| --- | --- | --- | --- |
| Write scope | Review report only | Review report only | None. |
| Implementation | None | None | None. |
| Source/test changes | None | None | None. |
| Focused checks | Preflight, four-file syntax, fake-Docker suite, diff/status | Completed; authoritative suite 24/24 PASS | Initial combined suite observation yielded before completion; a standalone authoritative rerun completed exit 0. |
| Runtime/external actions | None | None | None. |

## git diff --check

`PASS`: final `git diff --check` exited 0 with no output. Because the report is untracked,
`git diff --no-index --check /dev/null
docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_PLAN_REVIEW_2026-08-30.md` also emitted no
whitespace error; its expected status 1 means only that the new file differs from `/dev/null`.

## git status

Final expected status, to be verified after the final report write:

```text
## ctyun/replay-116-minimum-offline-gate-plan-reviewer-20260830
?? docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_PLAN_REVIEW_2026-08-30.md
```

## Commit ID: none

No commit or amend occurred or was authorized.

## No-push/external-action confirmation

No merge, rebase, reset, checkout, cherry-pick, commit, amend, push, PR, remote modification,
Docker action, real artifact inspection, browser action, network call, protected-pattern access,
real-secret handling, target connection, database/container/vector/volume action, or
production/gray action occurred.

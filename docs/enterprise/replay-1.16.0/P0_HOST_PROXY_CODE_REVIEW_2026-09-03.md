# Enterprise 1.16.0 explicit host-proxy mode code review

Date: 2026-09-03 (Asia/Shanghai)

Role: independent Code Reviewer (`codex-sol`)

Environment: Development / isolated rehearsal

## Verdict: CHANGES_REQUIRED

The exact one-commit range
`b10c34fd6afe1821857715a6830e5218855d9570..8909ad41ce3f7d58f9469573ff14a93a9d0b24b3`
correctly keeps host-proxy behavior default-off, applies the opt-in arguments to
both API and Web builds, forwards only set standard proxy variable names, and
keeps synthetic proxy values out of argv captures and generated files. It does
not, however, reject an exported-but-empty primary proxy variable. One P1
finding therefore blocks release-gate acceptance.

The repository synthetic suite passed 59/59 with fake Docker. Real Docker and
real image/artifact validation were forbidden and remain `NOT_RUN`.

## Immutable preflight

The required preflight ran before any write:

```text
git branch --show-current
  ctyun/replay-116-host-proxy-code-reviewer-20260903
git rev-parse HEAD
  8909ad41ce3f7d58f9469573ff14a93a9d0b24b3
git status --short --branch
  ## ctyun/replay-116-host-proxy-code-reviewer-20260903
```

The branch, exact HEAD, and clean starting status matched the contract. No
repair, checkout, merge, rebase, reset, cherry-pick, commit, amend, push, PR,
network, container, volume, deployment, database, production, gray-system, or
real-Docker action occurred. Proxy-sensitive execution used only an empty
environment, generated synthetic canaries, and the repository fake Docker.

## Exact reviewed change

The range contains one commit and exactly two modified files:

```text
M  scripts/build-enterprise-offline.sh
M  scripts/ci/check-enterprise-offline-tests.sh
```

Range size: 85 insertions, 1 deletion.

| File | Insertions | Deletions |
| --- | ---: | ---: |
| `scripts/build-enterprise-offline.sh` | 23 | 1 |
| `scripts/ci/check-enterprise-offline-tests.sh` | 62 | 0 |

No implementation, test, dependency, lock, Dockerfile, Compose, API, Web,
Docker, or documentation file outside this review report was changed by the
Reviewer.

## Behavior assessment

| Requirement | Evidence and judgment | Result |
| --- | --- | --- |
| Default-off compatibility | `scripts/build-enterprise-offline.sh:9,57-70` leaves the array empty unless `-UseHostProxy` is parsed. The quoted empty-array expansion at `:182,216` adds no argument under `set -u`. H01 at `scripts/ci/check-enterprise-offline-tests.sh:237-247` observes neither host networking nor proxy build arguments. | PASS |
| Consistent API/Web opt-in | One shared array is inserted before the final build context in both Docker commands at `scripts/build-enterprise-offline.sh:177-183,203-217`. `--network=host` and every build option precede the one positional context, which is valid Docker CLI placement. H02 observes exactly two builds and two host-network arguments at `scripts/ci/check-enterprise-offline-tests.sh:249-272`. | PASS |
| Standard set names only | The fixed allowlist at `scripts/build-enterprise-offline.sh:65` contains only uppercase/lowercase `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY`; `-v` at `:66` omits unset names. H02/H03 at `scripts/ci/check-enterprise-offline-tests.sh:249-283` cover all allowlisted names and omission of unset names. | PASS |
| No value handling or persistence | `scripts/build-enterprise-offline.sh:57-70` checks variable existence and constructs name-only `--build-arg NAME` argv entries; it does not expand, print, store, or content-match a proxy value. H02 uses only a generated synthetic canary and checks both the fake-Docker argv log and `dist` at `scripts/ci/check-enterprise-offline-tests.sh:251-271`. No API/Web Dockerfile declares a proxy `ARG` or `ENV`. Real image history/layer validation remains `NOT_RUN`. | PASS within source and synthetic boundary |
| NO_PROXY-only fail-fast | The primary-variable guard excludes both `NO_PROXY` spellings at `scripts/build-enterprise-offline.sh:58-62`, before repository resolution, artifact creation, or either build. H04 at `scripts/ci/check-enterprise-offline-tests.sh:285-295` verifies the diagnostic and absence of a fake Docker build. | PASS |
| Empty primary proxy | Bash `[[ -v HTTP_PROXY ]]` is true when `HTTP_PROXY` is exported as an empty string, so `scripts/build-enterprise-offline.sh:59` accepts an unusable configuration and `:64-68` enables host networking plus `--build-arg HTTP_PROXY`. The independent complete fake-Docker fixture exited 0 and recorded two builds, two host-network arguments, and two name-only `HTTP_PROXY` arguments. | **FAIL — P1** |
| `set -euo pipefail` behavior | The array is always declared, `-v` does not dereference unset values, the loop variable is assigned, and the optional `.nvmrc` test remains the non-final command of an `&&` list. No new unbound-variable or unintended errexit path was found. Both shell syntax checks and the suite passed under a scrubbed environment. | PASS, subject to empty-value logic finding |
| Check-only behavior | Without opt-in, the existing check-only path remains unchanged and H01/R01 emits no build/pull/save/run. With opt-in, validation still runs, but both image functions return before the two Docker build sites, so proxy build options cannot be issued. Treating an explicitly invalid opt-in as invalid even in check-only mode is consistent with fail-fast parsing. | PASS |
| Synthetic test strength | The suite scrubs all eight proxy names at `scripts/ci/check-enterprise-offline-tests.sh:50-61`, uses the repository fake Docker, and strongly covers default-off, both builds, all allowlisted names, unset-name omission, canary non-persistence, and NO_PROXY-only fail-fast. It does not cover an empty primary value despite naming H04 “without a usable proxy.” | FAIL — missing focused edge case |

`docs/enterprise/replay-1.16.0/CURRENT_STATE.md:15-19` explicitly keeps real
Docker, real artifacts, protected audit, offline-host, and target validation
outside this Development gate. This review preserved that boundary.

## Findings

### P0

None.

### P1

#### P1-1: Exported-but-empty primary proxy bypasses the configured/usable guard

Evidence: `scripts/build-enterprise-offline.sh:58-68` and
`scripts/ci/check-enterprise-offline-tests.sh:285-295`.

Reasoning/reproduction: Bash `-v` tests whether a variable is set, not whether
its value is non-empty. In a complete isolated fixture using the repository
fake Docker, `env HTTP_PROXY= ... -UseHostProxy` exited 0 and reached both API
and Web builds; the fake argv log contained two `--network=host` entries and
two name-only `--build-arg HTTP_PROXY` entries. No real or non-synthetic proxy
value was read or processed.

Violated invariant: explicit host-proxy mode must fail before a build unless at
least one primary uppercase/lowercase HTTP, HTTPS, or ALL proxy variable is
configured and usable. An empty variable is neither usable nor equivalent to
the required fail-fast behavior. It can enable host networking and permit a
release build to proceed when inputs happen to be cached, masking the invalid
operator configuration.

Bounded repair: at `scripts/build-enterprise-offline.sh:58-62`, require at least
one set primary proxy variable to have non-zero length while continuing to pass
only its name to Docker; do not log, persist, capture, or content-match the
value. Add one focused H04 regression at
`scripts/ci/check-enterprise-offline-tests.sh:285-295` that exports an empty
uppercase or lowercase primary variable, expects the existing diagnostic, and
asserts that no fake Docker build occurred. No abstraction or wider refactor is
needed.

### P2

None.

## Planned versus actual

| Item | Planned/reported invariant | Actual | Deviation |
| --- | --- | --- | --- |
| Scope | Offline build script plus focused synthetic test script | Exactly those two files changed | None |
| Default mode | No host network or proxy build arguments | Implemented and synthetically verified | None |
| Explicit mode | Same host network and set, name-only standard proxy arguments for API and Web | Implemented and synthetically verified | None |
| Value boundary | No proxy value printed, persisted, compared, captured, or placed in generated output | Source uses names only; synthetic canary absent from argv capture and `dist`; real image validation `NOT_RUN` | None within authorized boundary |
| Missing usable proxy | NO_PROXY-only and otherwise unusable primary input fail before build | NO_PROXY-only fails, but exported-empty primary input succeeds and builds | **Silent deviation: P1-1** |
| H04 test claim | “without a usable proxy fails before build” | Exercises only absent primary variables with NO_PROXY/no_proxy set; omits empty primary variables | **Silent coverage deviation: P1-1** |
| Current-state report | Historical 2026-09-02 gate state remains the source for Development/real-Docker boundaries | Builder range did not change it or claim current 59-test evidence there | No silent modification; current change is not recorded there |
| Reviewer scope | This report only | This report only | None |

The one-commit range contains no separate Builder report file. Accordingly,
the auditable planned-versus-actual comparison above uses the stated contract,
source, test labels, exact diff, and command evidence rather than unavailable
Builder prose. The empty-value behavior is the only observed implementation or
coverage deviation.

## Verification commands and accounting

All proxy-sensitive commands below ran under `env -i` with only synthetic or
empty proxy input.

| Command/evidence | PASS | FAIL | NOT_RUN | Result |
| --- | ---: | ---: | ---: | --- |
| Required branch/HEAD/status preflight | 3 | 0 | 0 | Exact branch and SHA; clean start |
| Exact range commit/file/count inspection | 1 commit, 2 files | 0 | 0 | 85 insertions, 1 deletion |
| `env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C bash -n scripts/build-enterprise-offline.sh` | 1 | 0 | 0 | Exit 0; no output |
| `env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C bash -n scripts/ci/check-enterprise-offline-tests.sh` | 1 | 0 | 0 | Exit 0; no output |
| `env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C bash scripts/ci/check-enterprise-offline-tests.sh` | 59 cases | 0 | 0 | Exit 0; `all 59 enterprise offline tests passed` |
| `git diff 8909ad41ce3f7d58f9469573ff14a93a9d0b24b3^ 8909ad41ce3f7d58f9469573ff14a93a9d0b24b3 --check` | 1 | 0 | 0 | Exit 0; no output |
| Complete synthetic `HTTP_PROXY=` fake-Docker reproducer | 0 | 1 invariant | 0 | Script exited 0 and reached both builds; expected fail-fast did not occur |
| `git diff --check` after report creation | 1 | 0 | 0 | Exit 0; no output |
| Real Docker build/save/load/run/inspect and real image history/layer validation | 0 | 0 | 1 | `NOT_RUN`: forbidden in this review |
| Real release artifact construction/inspection | 0 | 0 | 1 | `NOT_RUN`: forbidden; synthetic artifacts only |
| Protected audit, offline-host/runtime, network, target, signing, deployment, database, migration, and volume actions | 0 | 0 | 1 | `NOT_RUN`: forbidden/outside scope |

An earlier empty-proxy reproducer used an intentionally minimal compose list
and exited at the unrelated required-image assertion; it was setup-invalid and
is not counted as a product PASS or FAIL. The complete fixture above isolated
and reproduced P1-1. An earlier identical suite invocation yielded only partial
output at the tool boundary; the fully captured exit-0 run is the counted run.

## Final repository state

Final `git diff --check` exited 0 with no output. The report itself was also
checked independently for whitespace errors. Final `git status --short
--branch` reports only this allowed report:

```text
## ctyun/replay-116-host-proxy-code-reviewer-20260903
 A docs/enterprise/replay-1.16.0/P0_HOST_PROXY_CODE_REVIEW_2026-09-03.md
```

The report has only an intent-to-add index entry for the empty blob
`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`; `git diff --cached` and its stat
are empty, so no report content is staged. No implementation or test file was
modified. No commit, amend, push, PR, merge, rebase, reset, checkout, or
cherry-pick occurred.

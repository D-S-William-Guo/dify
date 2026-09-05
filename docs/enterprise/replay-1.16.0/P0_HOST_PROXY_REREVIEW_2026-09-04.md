# Enterprise 1.16.0 explicit host-proxy mode rereview

Date: 2026-09-04 (Asia/Shanghai)

Role: independent Rereviewer (`codex-sol`)

Environment: Development / isolated rehearsal

## Final gate: PASS

P1-1 is **CLOSED**. The exact Fixer commit rejects the all-unset/all-empty
state across all six primary proxy names before either build, retains the
explicit host-network path when any primary proxy is non-empty, and preserves
name-only forwarding. The new H05 is a behavioral fake-Docker regression using
only an exported-empty synthetic input, the existing diagnostic, and an
explicit assertion that no fake Docker build occurred.

Open findings: P0/P1/P2 = **0/0/0**.

Real Docker and real image/artifact validation were forbidden and remain
**NOT_RUN**.

## Immutable start

The required preflight ran before any repository read or write:

```text
git branch --show-current
  ctyun/replay-116-host-proxy-rereviewer-20260904
git rev-parse HEAD
  393a229f62bb1cd1505c2d590d2f242a59d7ba7f
git status --short --branch
  ## ctyun/replay-116-host-proxy-rereviewer-20260904
```

Branch, exact HEAD, and clean status matched the task contract. No repair,
checkout, merge, rebase, reset, or cherry-pick was performed.

The local official tag and merge base both resolve to
`5c6372d2f76d240265b92fd27c16bc772ffcb107`, consistent with the repository
state document's official 1.16.0 checkpoint. No remote access was performed.

## Exact ranges and modified files

### Fixer range

`72ae1451880e3ca86e3dc1a485a2e36458db72ed..393a229f62bb1cd1505c2d590d2f242a59d7ba7f`
contains exactly one commit:

```text
393a229f62bb1cd1505c2d590d2f242a59d7ba7f fix: reject empty host proxy settings
parent: 72ae1451880e3ca86e3dc1a485a2e36458db72ed
```

Exactly two files changed, totaling 13 insertions and 2 deletions:

```text
M  scripts/build-enterprise-offline.sh                    +1  -1
M  scripts/ci/check-enterprise-offline-tests.sh          +12  -1
```

### Cumulative implementation range

`b10c34fd6afe1821857715a6830e5218855d9570..393a229f62bb1cd1505c2d590d2f242a59d7ba7f`
contains the Builder, Code Review, and Fixer commits. Exactly three files
changed, totaling 274 insertions and 1 deletion:

```text
A  docs/enterprise/replay-1.16.0/P0_HOST_PROXY_CODE_REVIEW_2026-09-03.md  +178  -0
M  scripts/build-enterprise-offline.sh                                    +23  -1
M  scripts/ci/check-enterprise-offline-tests.sh                           +73  -0
```

No API, Web, Dockerfile, Compose, dependency, lock-file, or other documentation
path changed in either implementation scope. This rereview modifies only this
allowed report.

## P1-1 disposition and cumulative behavior

| Invariant | Evidence | Result |
| --- | --- | --- |
| All six primary names unset or empty fail before build | `scripts/build-enterprise-offline.sh:57-62` initializes the array and gates opt-in with non-empty checks for `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `http_proxy`, `https_proxy`, and `all_proxy`. The guard precedes repository resolution, output creation, and both build functions. H04 proves the no-primary/NO_PROXY-only case; H05 proves exported-empty input; an independent six-name empty matrix passed 6/6 with no fake build. | PASS |
| Any non-empty primary preserves explicit behavior | `scripts/build-enterprise-offline.sh:64-69` adds `--network=host` and only allowlisted set variable names. H02 covers all upper/lower primary and NO_PROXY names on two builds; H03 covers a single non-empty primary. | PASS |
| API/Web consistency | The same `HOST_PROXY_BUILD_ARGS` array is expanded at `scripts/build-enterprise-offline.sh:182` and `:216`, before each build context. H02 observes exactly two builds and two host-network arguments. | PASS |
| Default remains off | `USE_HOST_PROXY=false` at `scripts/build-enterprise-offline.sh:9`; the array remains empty without the flag. H01 observes no host-network or proxy build arguments. | PASS |
| NO_PROXY alone cannot enable the mode | The six-name guard excludes both NO_PROXY spellings. H04 at `scripts/ci/check-enterprise-offline-tests.sh:285-295` supplies only synthetic `NO_PROXY`/`no_proxy`, finds the existing diagnostic, and proves no fake build occurred. | PASS |
| Unset names are omitted | The fixed eight-name allowlist uses Bash `-v` at `scripts/build-enterprise-offline.sh:65-68`; H03 at `scripts/ci/check-enterprise-offline-tests.sh:274-283` proves all unset names are absent from both build captures. | PASS |
| Proxy values stay out of argv captures/artifacts | Only `--build-arg NAME` is constructed. H02 at `scripts/ci/check-enterprise-offline-tests.sh:249-272` uses a generated synthetic canary and proves it is absent from the fake-Docker argv log and generated `dist` tree. Real image/layer evidence is NOT_RUN. | PASS within the authorized boundary |
| Bash `set -euo pipefail` behavior | `${name:-}` safely handles unset variables in the guard; the optional array is always declared; `-v "$proxy_variable"` checks existence without dereferencing; the empty quoted array expansion adds no argument. Both syntax checks and the full scrubbed suite pass. | PASS |

### H05 quality

H05 at `scripts/ci/check-enterprise-offline-tests.sh:297-306`:

- calls the real offline script through the repository fake-Docker harness;
- supplies only `HTTP_PROXY=` after `fake_defaults` scrubbed all eight names;
- expects the existing `requires a configured` diagnostic;
- fails if the fake-Docker log contains a `docker build` call; and
- increments the suite count only after both behavioral assertions succeed.

It does not use a non-empty proxy value, mock the guard, or inspect a real
Docker daemon. This closes the exact coverage gap identified by P1-1.

## Fixer planned versus actual

The task contract supplies the Fixer plan/report claim; no separate durable
Fixer plan or Fixer report file exists in the reviewed repository range.

| Claimed item | Actual evidence | Deviation |
| --- | --- | --- |
| Change exactly the two allowed scripts | Fixer range changes exactly those two scripts. | None |
| Replace existence-only guard with a non-empty guard | One-line `-v` to six-name `-n ${name:-}` replacement at `scripts/build-enterprise-offline.sh:59`. | None |
| Add one exported-empty fake-Docker regression | H05 adds one fixture and one `HTTP_PROXY=` behavioral case, checks the existing diagnostic, and asserts no fake build. | None |
| Preserve default-off, explicit host networking, and name-only forwarding | H01-H03 and source inspection confirm all three. | None |
| `61/61` synthetic checks under `env -i` | Independently reproduced: exit 0, `all 61 enterprise offline tests passed`. | None |
| No real Docker | The suite prepends its fake Docker shim; D01 passes and no real Docker command was invoked or inspected. | None |
| Only the later authorized Fixer commit after Review | `git rev-list --count` for the Fixer range is 1; HEAD has the Review commit as its sole parent. | None |

No silent planned-versus-actual deviation was found. The absence of a separate
repository Fixer plan/report artifact is explicitly recorded above; the
contract-supplied claim, real diff, commit graph, accepted finding, and
independent evidence agree.

## Verification and accounting

All proxy-sensitive execution used only unset, empty, or generated synthetic
inputs under a scrubbed environment. No real proxy value or secret was read,
expanded, printed, compared, or recorded.

| Command/evidence | PASS | FAIL | NOT_RUN | Result |
| --- | ---: | ---: | ---: | --- |
| Required branch/HEAD/status preflight | 3 | 0 | 0 | Exact branch and SHA; clean start |
| Fixer commit/parent/file/count inspection | 1 range | 0 | 0 | One commit; two files; +13/-2 |
| Cumulative commit/file/count inspection | 1 range | 0 | 0 | Three commits; three files; +274/-1 |
| `bash -n scripts/build-enterprise-offline.sh` | 1 | 0 | 0 | Exit 0; no output |
| `bash -n scripts/ci/check-enterprise-offline-tests.sh` | 1 | 0 | 0 | Exit 0; no output |
| `env -i PATH=/usr/local/bin:/usr/bin:/bin LANG=C bash scripts/ci/check-enterprise-offline-tests.sh` | 61 cases | 0 | 0 | Exit 0; all 61 passed |
| Independent `env -i` six-name exported-empty fake-Docker matrix | 6 cases | 0 | 0 | Every primary name emitted the diagnostic before a fake build |
| `git diff 72ae1451880e3ca86e3dc1a485a2e36458db72ed..393a229f62bb1cd1505c2d590d2f242a59d7ba7f --check` | 1 | 0 | 0 | Exit 0; no output |
| `git diff b10c34fd6afe1821857715a6830e5218855d9570..393a229f62bb1cd1505c2d590d2f242a59d7ba7f --check` | 1 | 0 | 0 | Exit 0; no output |
| Working-tree `git diff --check` | 1 | 0 | 0 | Exit 0; no output |
| Real Docker build/save/load/run/inspect and real image/layer validation | 0 | 0 | 1 | NOT_RUN: explicitly forbidden |
| Real release artifacts, protected audit, offline host/runtime, network, target, signing, deployment, database, migration, and volume actions | 0 | 0 | 1 | NOT_RUN: forbidden or outside scope |

One preliminary invocation of the same scrubbed 61-case suite produced partial
streamed output before its session handle was lost by the command wrapper. It
is not counted as PASS or FAIL; no process remained afterward. The immediately
repeated, fully captured invocation above is the authoritative result.

## Final repository state

`git diff --check` exits 0 with no output and checks the report content because
the new file has intent-to-add state. An explicit no-index check also emitted
no whitespace diagnostic (its exit 1 records the expected file difference).

Final status:

```text
## ctyun/replay-116-host-proxy-rereviewer-20260904
 A docs/enterprise/replay-1.16.0/P0_HOST_PROXY_REREVIEW_2026-09-04.md
```

The report has only an intent-to-add index entry for the empty blob
`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`; `git diff --cached` is empty, so
no report content is staged.

This Rereviewer made no implementation or test change and performed no commit,
amend, push, PR, merge, rebase, reset, checkout, or cherry-pick. The historical
authorized Fixer commit `393a229f62bb1cd1505c2d590d2f242a59d7ba7f`
was only inspected.

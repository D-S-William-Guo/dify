# P0 protected-secret scan plan review

Verdict: CHANGES_REQUIRED

Date: 2026-08-28 (Asia/Shanghai)

Role: Plan Reviewer

## Start branch and SHA

- Branch: `ctyun/replay-116-p0-secret-plan-reviewer-20260828`
- HEAD: `eff38e1078a8d9f5e5e06b0d842534086a076b66`
- Required start verifier: PASS; branch and HEAD matched and the worktree was clean.

## Exact modified files

- `docs/enterprise/replay-1.16.0/P0_SECRET_SCAN_PLAN_REVIEW_2026-08-28.md`

No scanner, test, fixture, artifact, pattern source, or other file was modified.

## Independent evidence and commands with exact counts

The review derived the control-flow findings from checked-in source, not the Architect's claims:

- `scripts/ci/check-enterprise-offline.sh:155-168` passes each active literal to `grep` as an argument and counts once per matching pattern. Lines 218-222 and 269-273 scan the top-level image list and release manifest. Lines 341-370 extract and scan config members. Lines 405-451 discover only `*/layer.tar` and decode the inner tar as gzip. Lines 453-459 have no zero-candidate result. Lines 463-475 aggregate only config/layer counters and accept at least one config member plus at least one layer pass. Lines 478-484 ignore `NOT_RUN` when choosing the exit status.
- `scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker:99-118` emits a gzip-compressed `ab12cd34/layer.tar`, while `scripts/ci/check-enterprise-offline-tests.sh:315-344` treats that fixture as the positive real-bundle case. This proves neither raw legacy layers nor Docker 29 manifest-referenced blob layers.
- `docs/enterprise/replay-1.16.0/evidence/phase-h/README.md:27-28,98-107` records synthetic-only scanning and the Docker 29 layer-layout `NOT_RUN`. `docs/enterprise/replay-1.16.0/FINAL_VALIDATION_SUMMARY.md:59-75` and `docs/enterprise/replay-1.16.0/CURRENT_STATE.md:416-432` retain layer scanning and the protected-pattern audit as release limitations.
- The checked-in redacted production-preflight log was counted by status/target labels only. An `awk` label counter produced exactly `11 PASS / 128 FAIL / 0 NOT_RUN`: 2 top-level image-list events (`prod-secret-scan.log:3-4`), 2 top-level manifest events (`:6-7`), 123 config-member events across 27 unique target labels (`:12-134`), and 1 aggregate S-8 event (`:139`). The partition is `2 + 2 + 123 + 1 = 128`; `other_fail=0`. The summary at line 141 independently reports `11 PASS / 128 FAIL / 0 NOT_RUN`.
- Source-stability checks with `git show <sha>{,^}:<path> | sha256sum` produced identical before/after hashes for both scanner source (`fb59a45...`) and tests (`a7c3f942...`), confirming the reviewed plan commit changed neither implementation nor tests.
- No protected value or matching payload was read, requested, hashed, copied, printed, inferred, or passed to a command. Only redacted labels and aggregate counts were processed.

Commands used for this evidence were read-only `nl`/`sed`/`rg` source inspection, status-label-only `awk` counts, `sha256sum` of public source text, and the required Git start checks. No artifact-content command, protected scan, Docker command, network call, or runtime test was run.

## Findings

Open finding counts: **P0 1 / P1 2 / P2 1 / P3 0**.

### P0-01 — Archive link safety does not cover the config archive

- **Evidence:** The current scanner extracts the entire config archive with `tar xzf` and then follows archive-created paths through `[[ -f ... ]]` and `grep` (`scripts/ci/check-enterprise-offline.sh:341-370`). The plan's safe `tarfile` helper is scoped to manifest-selected outer layer members and inner layer tar streams (`P0_SECRET_SCAN_ARCHITECT_2026-08-28.md:134-144`); its only safety case explicitly says “Inner tar” (`:189`). A config-archive symlink can therefore redirect the content scan to a regular file outside the artifact even after the proposed layer repair.
- **Violated invariant:** The protected scanner must never extract through attacker-controlled paths, follow archive links into runner files, or scan bytes that are not regular-file content owned by the artifact. Every required regular config member must still be covered.
- **Reproduction/command:** NOT_RUN in this review because execution was forbidden. The Builder regression must create only a synthetic config archive containing absolute/traversal names and safe/escaping symlink and hardlink cases, invoke `bash scripts/ci/check-enterprise-offline-tests.sh`, and prove no path outside the fixture scratch root is read or written. Output must contain no canary.
- **Exact repair boundary:** In `scripts/ci/check-enterprise-offline.sh`, use the same embedded standard-library archive reader for config members and image-bundle outer/inner members. Inspect member metadata without `extractall`/`tar x*`; reject ambiguous duplicate names and absolute/`..` paths; never dereference symlinks on the filesystem; require each manifest-selected layer payload to be an unambiguous regular outer member; handle inner hardlinks only by safe in-archive resolution or mark coverage `NOT_RUN`. Copy/stream regular bytes only to opaque mode-`0600` scratch targets. Extend only the existing test script and fake Docker fixture.

### P1-01 — Pattern normalization can still drop an active literal without a regression

- **Evidence:** The plan requires exact active-line literals and an unreadable/empty source to fail (`P0_SECRET_SCAN_ARCHITECT_2026-08-28.md:113-124`), but the implementation shape only says to create a normalized file and call `grep -Fq -f` (`:134-139`). Its pattern cases cover clean, empty, target hits, multiple matches, and a weak literal (`:173-180`), but not a final active line without a newline, unreadable/non-regular input, or literal metacharacter/leading-dash preservation. The current `while read` loop (`scripts/ci/check-enterprise-offline.sh:161-168`) drops an unterminated final record.
- **Violated invariant:** No active literal, including a weak/common one, may be silently removed or reinterpreted; protected plaintext must not appear in process arguments, logs, or diagnostics.
- **Reproduction/command:** NOT_RUN. Add a synthetic pattern source with one absent newline-terminated literal followed by a matching final literal with no trailing newline; the repaired checker must fail redacted and nonzero. Add missing, unreadable/non-regular, blank/comment-only, leading-dash, backslash, and surrounding-space cases using synthetic values only.
- **Exact repair boundary:** Specify byte-preserving line normalization including the unterminated last record; validate the source as readable and regular; set `umask 077` and mode `0600`; reject zero active lines; and invoke `grep -Fq -f "$normalized" -- "$target"`. Review captured output and the command construction to prove literals are absent from argv/output. Do not add a dependency or protected fixture.

### P1-02 — The acceptance matrix does not prove the full manifest graph or FAIL-plus-NOT_RUN aggregation

- **Evidence:** The plan correctly requires every unique layer from every Docker-save `manifest.json` entry and requires incomplete surfaces to remain `NOT_RUN` even when another surface hits (`P0_SECRET_SCAN_ARCHITECT_2026-08-28.md:121-132,138-143`). Its tests exercise one Docker 29 blob, zero/missing/partial layers, and hits separately (`:181-190`), but no case has multiple image entries with shared and unique layers, and no case combines a protected hit with a missing/corrupt layer. A Builder could read only the first manifest entry, double-count a shared layer, or suppress `NOT_RUN` after a hit while passing every listed case.
- **Violated invariant:** Coverage is complete only when the deduplicated expected graph from all image entries equals the scanned graph; a hit must never erase an incomplete-surface `NOT_RUN`, and either condition must exit nonzero.
- **Reproduction/command:** NOT_RUN. Add one synthetic Docker 29 manifest with at least two image entries, one shared layer and one unique layer per entry, mixing raw and gzip tar streams; assert exact expected/scanned unique counts. Add one combined metadata hit plus corrupt/missing second layer; assert a redacted `FAIL`, an explicit `NOT_RUN`, the exact summary counts, no S-8 `PASS`, and nonzero exit. Add malformed/duplicate outer `manifest.json` and layer-member cases as `NOT_RUN` plus nonzero.
- **Exact repair boundary:** Tests and counters only within the three accepted files. Parse exactly one unambiguous regular top-level Docker-save `manifest.json`; validate JSON shape and every `Layers` value/path; deduplicate exact safe member names; compare expected, scanned, hit, and unreadable counts before S-8 aggregation.

### P2-01 — Bounded scratch/resource failure is requested but not specified or tested

- **Evidence:** The plan says not to load whole members into memory but still copies regular streams to scratch (`P0_SECRET_SCAN_ARCHITECT_2026-08-28.md:141`). It later calls archive resource exhaustion a residual risk and says review should require bounded scratch/error handling (`:223`), yet no implementation rule or acceptance case defines the bound or the required status.
- **Violated invariant:** Oversized, truncated, or write-failing archive members must not exhaust the secure runner or turn partial scanning into success; the result must be redacted `NOT_RUN` and nonzero.
- **Reproduction/command:** NOT_RUN. Add a small synthetic test-only byte budget and a member whose declared/copied bytes exceed it; the focused suite must prove bounded cleanup, explicit `NOT_RUN`, and nonzero exit without printing content.
- **Exact repair boundary:** Stream members where practical; otherwise copy one member at a time under an explicit byte budget, unlink immediately after scanning, and convert size/copy/disk errors into coverage `NOT_RUN`. Keep the helper embedded and standard-library-only; add no service, daemon, or dependency.

## Acceptance conditions and smallest Builder/test allowlists

The plan may pass after all four findings are incorporated as explicit implementation rules and synthetic acceptance rows, with no relaxation by length, frequency, commonness, path, file class, example/template status, or metadata status.

Minimum fail-closed acceptance:

1. Pattern input is readable, regular, nonempty after exact active-line normalization, preserves an unterminated last record, remains absent from argv/output, and uses `grep -Fq -f ... -- target` or an equivalently private fixed-string mechanism.
2. Top-level image list, top-level release manifest, every regular config member, and every unique safe layer referenced by every Docker-save manifest image entry have explicit expected/scanned state.
3. Raw and gzip inner layer tar streams pass through format autodetection. Zero, missing, corrupt, unsafe, duplicated/ambiguous, oversized, or partially covered required members produce redacted `NOT_RUN` and nonzero exit.
4. Any literal hit produces `FAIL` and nonzero exit. A simultaneous hit and coverage gap reports both `FAIL` and `NOT_RUN`; no hit or gap may be hidden by aggregation.
5. Existing no-pattern behavior and the full existing fixture suite remain green; the Builder reports the new exact test count rather than reusing the historical checked-in `21/21` count from `CURRENT_STATE.md:315-321`.

Smallest production Builder allowlist:

- `scripts/ci/check-enterprise-offline.sh`

Smallest test allowlist:

- `scripts/ci/check-enterprise-offline-tests.sh`
- `scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker`

No new file, package, dependency, service, Docker action, artifact rewrite, application source change, PowerShell expansion, or generalized scanner framework is justified.

## Development-versus-release boundary check

PASS. The reviewed plan keeps development validation synthetic-only (`P0_SECRET_SCAN_ARCHITECT_2026-08-28.md:169-203`) and keeps the protected real-pattern audit separate and explicitly authorized (`:225-250`). This agrees with `CURRENT_STATE.md:110-121,416-432` and `FINAL_VALIDATION_SUMMARY.md:59-75`: local Builder/reviewer work may use only generated canaries, while a later protected release audit must name the secure runner and unchanged artifact set, keep protected values out of arguments/logs/evidence, emit only redacted boolean/count evidence, and authorize no deployment.

The protected-pattern owner may separately classify or remove a protected literal through its audited process. Builder code must not infer that a frequent, short, example-file, or metadata match is safe.

## Known limitations and actions still unauthorized

- The checked-in protected audit remains `FAIL`; its image-layer portion is unverified despite `0 NOT_RUN`. Synthetic repair tests cannot close that release gate.
- A protected real-pattern rescan, true no-network Docker-host load/boot, image signing/audit, independent deployment rehearsal, PowerShell runtime, migrated production-vector validation, plugin remote debug, and inline-agent UI validation remain `NOT_RUN` or separately gated as recorded in current-state evidence.
- No protected-pattern file/value, production or gray credential, Plan B value, artifact content, Docker daemon, build/load/run/restart, network, production/gray connection, deployment, browser, artifact rewrite, secret rotation, or external-state action was authorized or performed.
- No merge, rebase, reset, cherry-pick, commit, amend, push, branch/worktree deletion, or instance lifecycle action was authorized or performed.

## git diff --check and git status

- `bash -n scripts/ci/check-enterprise-offline.sh scripts/ci/check-enterprise-offline-tests.sh scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker`: PASS (exit 0, no output).
- `git diff --check`: PASS (exit 0, no output).
- `git status --short --branch`: PASS; exact output was:

```text
## ctyun/replay-116-p0-secret-plan-reviewer-20260828
?? docs/enterprise/replay-1.16.0/P0_SECRET_SCAN_PLAN_REVIEW_2026-08-28.md
```

Commit ID: none (not authorized)

Confirmation: no push or external-state action occurred.

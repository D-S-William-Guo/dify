# Enterprise 1.16.0 P0 protected-secret scan architecture gate

Date: 2026-08-28 (Asia/Shanghai)

Role: Architect

Start worktree branch: `ctyun/replay-116-p0-secret-architect-20260828`

Start HEAD: `198ee103deac60d1d5be008aeb671c90c93eca62`

Candidate verified by the required start script: `codex/enterprise-candidate-1.16.0-20260718` at the same SHA, clean.

## 1. Scope, plan, and guardrails

This is a one-file, documentation-only architecture gate. Runtime plan mode was skipped for that reason; this section is the required plan of record. No scanner, fixture, artifact, pattern file, container, or external system is to be changed by this task.

### Planned file

- Write only `docs/enterprise/replay-1.16.0/P0_SECRET_SCAN_ARCHITECT_2026-08-28.md`.

### Planned analysis

1. Verify the assigned worktree branch, exact HEAD, clean state, and candidate start SHA; stop on mismatch.
2. Trace `scripts/ci/check-enterprise-offline.sh` end to end, including protected-pattern matching, images/manifest/config coverage, layer discovery, archive decoding, S-8 aggregation, counters, and exit status.
3. Read `scripts/ci/check-enterprise-offline-tests.sh` and its two existing fake-command fixtures to identify what current tests prove and conceal.
4. Classify the production-preflight `11 PASS / 128 FAIL / 0 NOT_RUN` result only by redacted status labels and deterministic packaged-file classes. Do not inspect, print, copy, or derive any protected pattern or matching content.
5. Reconcile the production result with Phase H evidence, `CURRENT_STATE.md`, and `FINAL_VALIDATION_SUMMARY.md`.
6. Define the smallest fail-closed repair, Builder/test ownership, exact synthetic acceptance cases, review gates, remaining `NOT_RUN`, risks, rejected alternatives, and human decisions.

### Planned verification

```bash
git diff --check
git status --short --branch
```

Builder commands are proposed in section 8 but are not authorized or run by this Architect task.

### Planned risks

- Protected-pattern confidentiality: no protected value, file content, raw matching line, token, password, or payload may enter this report or command output.
- Evidence ambiguity: a redacted literal hit proves a match, but not whether the matched pattern is an active credential, a weak credential, or a non-secret value mistakenly placed in the protected source.
- False assurance: a lower failure count must never be achieved by ignoring weak/common patterns, skipping file classes, or treating partial layer coverage as success.
- Archive safety: layer support must not introduce path traversal, symlink extraction, unbounded in-memory reads, or accidental content logging.
- Scope drift: this gate does not authorize artifact rewriting, Docker execution, a protected rescan, secret rotation, or production access.

## 2. Executive decision

**P0 verdict: release remains blocked.** The real-pattern run contains protected-pattern hits, including the top-level image list and manifest, while the same run leaves image-layer content unverified without reporting `NOT_RUN`. The 128 failures cannot be relabeled as false positives from the authorized evidence.

Recommended minimum repair:

1. keep literal matching fail-closed on every current surface;
2. emit at most one redacted protected-pattern failure per target, without suppressing any matching pattern;
3. derive layer members from Docker-save `manifest.json` instead of filename shape;
4. scan both raw and compressed layer tar streams using the Python standard library already required by the script;
5. make zero, corrupt, missing, or partially scanned layers an explicit `NOT_RUN` and a nonzero protected-scan outcome;
6. prove the behavior with synthetic fixtures only.

This is `KEEP_MINIMAL_PATCH` in the existing B7 checker and tests. No new dependency, script, service, artifact format, or generalized scanning framework is warranted.

## 3. Current scanner control flow and evidence

All line references are to start SHA `198ee103deac60d1d5be008aeb671c90c93eca62`.

| Flow | Repository evidence | Consequence |
| --- | --- | --- |
| Arguments and protected-pattern input | `check-enterprise-offline.sh:11-39` parses `-SecretsPattern`; lines 41-46 require the four artifact paths but not the optional pattern. | S-8 is optional by design outside protected preflight. When supplied, its completeness must be judged separately from ordinary artifact checks. |
| Redacted literal matching | Lines 155-190 implement `scan_content_secrets`. Lines 161-168 read each active line and run fixed-string `grep` once per pattern per target; every matching pattern increments `fail_count`. | Failure count is a count of pattern-target hit events, not leaked values, distinct secrets, or even distinct files. Pattern plaintext is also passed as a process argument to `grep`; the repair should use protected file-based matching instead. |
| Image list | Lines 196-223 validate existence/required images, then scan the complete image-list file at lines 218-222. | Image names/tags are intentionally in scope. A redacted hit cannot be ignored merely because this is metadata. |
| Manifest | Lines 225-274 validate schema/name consistency, then scan the complete manifest at lines 269-273. | Manifest metadata is intentionally in scope and can carry a genuine secret. |
| Config archive | Lines 276-340 list and validate paths. Lines 341-370 extract and scan each regular member. | Packaged copies of the image list and manifest are scanned again. This is two artifact surfaces, not proof that duplicate diagnostics are false. |
| Development default | Lines 171-184 handle the known development default. Config lines 351-364 also perform a separate warning check before calling the shared scanner at line 365. | This is independent of protected patterns. The production 128-event classification below contains only real-pattern diagnostics, not development-default failures. |
| Bundle assumptions | Lines 377-403 require/list the outer Docker-save archive. Lines 405-406 and 451 select only names ending in `*/layer.tar`. | Docker 29 blob paths are never selected, so the loop can execute zero times. |
| Inner archive decoding | Lines 415 and 428 use `tar tzf` and `tar xzf`. | Legacy Docker `layer.tar` is a raw tar, while `-z` requires gzip. A selected real raw layer therefore becomes `NOT_RUN`. |
| Silent zero-layer path | Lines 453-459 report only when a hit, pass, or prior layer `NOT_RUN` flag exists. A zero-candidate loop leaves all three unset. | The production result can show `0 NOT_RUN` although no layer was examined. |
| Incomplete S-8 aggregation | Lines 463-475 aggregate only config/layer counters. Images/manifest protected hits have no S-8 state. Line 469 needs only one clean config member and one passing layer; it does not require every layer to pass. | S-8 can be semantically inconsistent with direct metadata failures, and partial layer coverage can be reported as S-8 `PASS`. |
| Exit status | Lines 478-483 exit nonzero only when `fail_count > 0`. | An incomplete protected scan represented solely by `NOT_RUN` can still exit zero. |

Phase H independently confirms the layout gap: `evidence/phase-h/secret-scan.log:13-17` and `evidence/phase-h-rerun/secret-scan.log:17-22` state that Docker 29 emitted `blobs/sha256/*`, which the `*/layer.tar` selection did not match. Both offline scan logs show `13 PASS / 0 FAIL / 1 NOT_RUN` at lines 14-16. `CURRENT_STATE.md:416-428` and `FINAL_VALIDATION_SUMMARY.md:59-71` retain image-layer scanning and the real protected-pattern run as release limitations.

The existing fake Docker fixture masks the second archive bug: `check-enterprise-offline-fixtures/bin/fake-docker:99-118` creates `ab12cd34/layer.tar` with `tar czf`, i.e. gzip content under a `.tar` name. The positive test at `check-enterprise-offline-tests.sh:315-344` therefore matches both the filename filter and the incorrect `-z` decoder instead of modeling a real raw Docker layer.

## 4. Classification of the 128 failures

The authorized redacted log contains exactly `11 PASS / 128 FAIL / 0 NOT_RUN`. Its 128 failure diagnostics partition deterministically as follows:

| Redacted target class | Hit events | What is proved | What is not proved |
| --- | ---: | --- | --- |
| Top-level image list | 2 | Two active literal patterns matched that target during its direct scan. | Whether either pattern is a live credential, weak credential, or non-secret protected-source error. |
| Top-level manifest | 2 | Two active literal patterns matched that target during its direct scan. | Same distinction; metadata is not automatically safe. |
| Config archive members | 123 | 123 pattern-target hit events occurred across 27 unique packaged members. | 123 distinct secrets or 123 distinct files. |
| Aggregate S-8 failure | 1 | At least one config/layer hit counter was nonzero. | Complete layer coverage. |
| **Total** | **128** | Exact reconciliation with the summary. | Any basis for “false positive.” |

The 123 config-member events further partition without reading content:

| Deterministic packaged-file group | Hit events |
| --- | ---: |
| `docker/envs/**.env.example` | 85 |
| root `docker/.env.example` | 15 |
| the two Compose YAML files | 18 |
| packaged image list plus manifest | 4 |
| nginx configuration template | 1 |
| **Total** | **123** |

The 27 unique config members are 22 env-example files, two YAML files, one JSON file, one text file, and one nginx template. Their hit multiplicities range from one to fifteen because the current loop emits once per matching pattern. Direct image/manifest scans plus packaged copies explain why those logical metadata files each contribute on two artifact surfaces.

`0 NOT_RUN` does **not** prove layer coverage. The absence of both a layer-scan `PASS` and a layer `NOT_RUN`, combined with the zero-candidate control flow and Phase H's Docker 29 evidence, proves the layer loop did not establish coverage. In this run, the aggregate S-8 failure from config hits suppresses the otherwise incomplete layer state.

No failure in this report is called a false positive. That distinction is impossible without an authorized protected-pattern owner determining whether each pattern still represents protected credential material. A ubiquitous or weak literal may be noisy and still be the genuine secret; frequency is not exculpatory.

## 5. Fail-closed protected-pattern policy

The repaired contract must be:

1. The protected source remains one exact fixed-string pattern per active non-comment, non-empty line. It is owner-controlled, readable only by the protected runner, never logged, and never passed as plaintext in process arguments.
2. Suppression based on length, frequency, “commonness,” filename, extension, example/template status, image metadata, or warning text is forbidden. A genuine weak or ubiquitous secret must still make every matching target fail.
3. One target produces one redacted protected-hit diagnostic even if several patterns match it. This changes only diagnostic cardinality; it does not change the boolean release decision or skip any pattern.
4. An empty active pattern set, unreadable protected file, or invalid protected-file setup is a configuration failure, not a clean scan.
5. Required surfaces are the top-level image list, top-level manifest, every regular config-archive member, and every unique layer referenced by every Docker-save `manifest.json` image entry. Packaged copies remain independently scanned.
6. Layer success requires a nonzero expected layer count and `scanned == expected`, with every layer structurally readable and every regular member content-scanned. Shared layers may be byte-scanned once after exact member-path deduplication.
7. Any hit is `FAIL`. Any missing/corrupt/unsupported/partially scanned required surface is explicit `NOT_RUN`; with `-SecretsPattern` supplied, either state returns nonzero. Only complete coverage with zero hits is S-8 `PASS`.
8. Output contains target identity and boolean status only. It must never contain a pattern, matching line, member payload, credential value, or content-derived excerpt.

Decision table:

| Protected hit | Complete required coverage | S-8 result | Exit |
| --- | --- | --- | --- |
| yes | yes or no | `FAIL`; also report incomplete surfaces as `NOT_RUN` | nonzero |
| no | no | `NOT_RUN` | nonzero |
| no | yes | `PASS` | zero, assuming other artifact checks pass |

## 6. Minimum safe implementation shape

Keep Bash orchestration and the existing fixed-string scan contract. Make one production-file change:

1. At protected-pattern initialization, set restrictive temporary-file permissions and create a normalized, non-logged pattern file containing only active lines. Refuse an empty active set. Use `grep -Fq -f <normalized-file> <target>` once per target. Maintain a dedicated global protected-hit flag/count, separate from the development-default warning logic.
2. Track explicit coverage for images, manifest, config members, expected layers, scanned layers, and unreadable layers. Do not infer completeness from “at least one pass.”
3. Read exact layer paths from the outer Docker-save `manifest.json` `Layers` arrays. Do not discover layers by `*/layer.tar` or scan every blob indiscriminately.
4. Use an embedded Python standard-library `tarfile` helper (`r:*`/streaming equivalent) for raw or compressed inner tar detection. It should open exact outer members, enumerate every inner member for forbidden-path checks, and copy only regular-file streams to opaque `0600` scratch names for the existing scanner. It must not use `extractall`, trust archive paths as filesystem paths, follow symlinks, load whole large members into memory, or emit content.
5. Report zero expected layers, missing manifest references, corrupt layers, and partial completion explicitly. Preserve `NOT_RUN` counts even when another surface already has a hit, and make protected-scan incompleteness nonzero.

This fixes both real defects once in the shared checker. Merely replacing `tzf/xzf` with `tf/xf` is insufficient because Docker 29 blob paths still bypass the filename filter; merely adding a blob glob is insufficient because not every blob is a layer.

## 7. Ownership and gates

### Builder allowlist (production)

- `scripts/ci/check-enterprise-offline.sh`

No build script, PowerShell script, artifact, manifest, image list, Compose file, application source, dependency file, or documentation file belongs in the Builder production allowlist.

### Test allowlist

- `scripts/ci/check-enterprise-offline-tests.sh`
- `scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker`

Prefer extending the existing fake Docker switches rather than adding fixture files. `fake-git` needs no change.

### Roles

- **Builder: required.** One owner changes the shared checker and its synthetic fixtures from the exact accepted SHA.
- **Independent Code Reviewer: required.** This is a P0 release/security boundary. Review must challenge pattern disclosure, boolean preservation, all-surface coverage, archive traversal/symlink handling, compression/layout support, failure/`NOT_RUN` exit semantics, and allowlist compliance.
- **Fixer and Rereviewer: conditional but mandatory after any finding.** If review is a clean `PASS` and the reviewed SHA does not change, a rereview has no delta. If any code/test/report change follows review, an independent Rereviewer must rerun the full focused suite and close every enumerated finding before integration.

No commit, merge, push, or candidate integration is authorized by this report. Those need a separate human gate.

## 8. Exact synthetic acceptance cases and commands

All new cases use generated canaries under the existing temporary test root. Test output must be asserted not to contain the canary.

| Case | Fixture/action | Required result |
| --- | --- | --- |
| P1 clean protected set | One active synthetic pattern absent from all complete surfaces. | S-8 `PASS`, exit zero. |
| P2 empty protected set | Only blank/comment lines. | Configuration `FAIL`, exit nonzero. |
| P3 image-list hit | Add a synthetic canary to a schema-valid image-list/manifest pair. | Redacted image target `FAIL`, aggregate S-8 `FAIL`, exit nonzero, canary absent from output. |
| P4 manifest hit | Put a synthetic canary in a non-structural manifest field while retaining schema consistency. | Redacted manifest target `FAIL`, aggregate S-8 `FAIL`, exit nonzero, canary absent from output. |
| P5 multiple-pattern same target | Two synthetic active patterns match one target. | Exactly one protected-hit diagnostic for that target; release still fails. |
| P6 weak/ubiquitous pattern | Use a deliberately short synthetic pattern that matches packaged metadata. | Hit remains blocking; no length/frequency suppression. |
| L1 legacy raw clean layer | Fake Docker emits a real raw `layer.tar` with no canary. | Expected/scanned layer counts match; layer and S-8 pass. |
| L2 legacy raw hit | Raw `layer.tar` contains a synthetic canary in a regular member. | Redacted layer-member `FAIL`, exit nonzero, canary absent from output. |
| L3 compressed clean layer | Manifest references a gzip-compressed tar layer. | Complete layer scan passes, proving compression autodetection remains supported. |
| L4 Docker 29 blob clean | Manifest `Layers` references `blobs/sha256/*`; blob is a clean layer tar stream. | Blob is discovered from manifest and scanned; complete S-8 passes. |
| L5 Docker 29 blob hit | Same layout with a synthetic canary. | Redacted layer-member `FAIL`, exit nonzero. |
| L6 zero referenced layers | Valid outer files but no referenced layer. | Explicit layer `NOT_RUN`, protected scan exits nonzero. |
| L7 missing/corrupt layer | Manifest references an absent or unreadable layer. | Explicit `NOT_RUN`, protected scan exits nonzero. |
| L8 partial coverage | Two referenced layers: one clean, one unreadable. | No layer/S-8 pass; explicit `NOT_RUN`, protected scan exits nonzero. |
| L9 archive-path safety | Inner tar includes traversal, absolute, symlink, and non-regular entries. | No write escapes scratch root; forbidden names fail where policy applies; only regular bytes are scanned. |
| R1 existing regressions | Run every existing offline fixture case unchanged. | Full suite passes; ordinary no-pattern behavior remains compatible. |

Builder verification:

```bash
bash -n scripts/ci/check-enterprise-offline.sh \
  scripts/ci/check-enterprise-offline-tests.sh \
  scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker
bash scripts/ci/check-enterprise-offline-tests.sh
git diff --check
git status --short --branch
```

Reviewer/Rereviewer run the same commands from the exact submitted SHA. They must inspect captured synthetic output for value absence. They must not use a real secret value, protected pattern file, real artifact rewrite, Docker daemon, network, or production host.

The historical baseline is 21/21 fixture tests (`CURRENT_STATE.md:315-321` and `FINAL_VALIDATION_SUMMARY.md:17-29`). The Builder must report the new exact test count rather than preserving or guessing 21.

## 9. Risks and rejected alternatives

| Alternative | Decision and reason |
| --- | --- |
| Remove/ignore short or common patterns | Rejected: a weak/common value can be the genuine credential. Frequency cannot weaken a release gate. |
| Call the 128 events false positives | Rejected: redacted evidence cannot establish that. |
| Skip images, manifest, examples, templates, or Compose | Rejected: current evidence proves those packaged bytes match protected literals; file class does not prove safety. |
| Allowlist current target paths | Rejected: path allowlisting would suppress future genuine leakage and make artifact copies inconsistent. |
| Stop after diagnostic deduplication | Rejected: it improves counts but leaves real layer bytes unverified. |
| Change only `tar tzf/xzf` to `tar tf/xf` | Rejected: fixes raw legacy layers but not Docker 29 manifest-referenced blob paths or extraction safety. |
| Scan every `blobs/sha256/*` as a layer | Rejected: Docker-save blobs can include non-layer objects; use the manifest's exact layer graph. |
| Treat any one scanned layer as complete | Rejected: partial coverage is not release evidence. |
| Keep `NOT_RUN` exit zero with a protected pattern | Rejected: orchestration could publish after an incomplete security gate. |
| Add a dependency or new scanner service | Rejected: Bash plus the already-required Python standard library is sufficient. |
| Modify artifacts until the count falls | Rejected: this gate diagnoses; it does not authorize hiding, rotating, or rewriting protected material. |

Residual risks after the code repair are archive resource exhaustion and platform-specific tar edge cases. The Reviewer should require bounded scratch use/error handling and synthetic malformed archives, but no generalized archive framework or Docker invocation.

## 10. Human decisions and recommended default

Human decisions required:

1. The protected-pattern owner must decide, outside this report and without disclosing values, whether each active literal still represents protected credential material. If yes, every matching artifact remains a genuine release blocker and the credential/content must be remediated through a separately authorized security process. If no, only that owner may remove the non-secret literal from the protected source with an audit record.
2. Authorize or reject the narrow Builder and test allowlists above from an exact candidate SHA.
3. After accepted code review, authorize a protected-environment rescan of unchanged release artifacts. The runner must retain only redacted boolean/count evidence.
4. Separately authorize any secret rotation, artifact rebuild, candidate integration, signing, offline-host validation, or deployment. None follows automatically from this architecture report.

**Recommended default:** keep the release blocked; retain all current patterns and all target classes; implement only the shared checker plus synthetic tests; require independent review; then rerun the protected scan in the authorized environment. Do not set a target failure count. Acceptance is complete coverage and zero protected hits, not “fewer than 128.”

## 11. Remaining `NOT_RUN`

The scanner repair can close local synthetic coverage of raw/gzip and manifest-referenced blob layers, but it cannot close the following release evidence in this task:

- protected-pattern scan over every real release-artifact surface, including real image layers: requires the protected runner and protected source;
- true no-network Docker-host load and boot: prior Phase H was same-daemon simulation (`FINAL_VALIDATION_SUMMARY.md:59-63`);
- formal image signing/audit and independent-environment deployment rehearsal: separate release authorization (`FINAL_VALIDATION_SUMMARY.md:73-75`);
- migrated production-dataset vector-class alignment: production Weaviate data is outside authorized paths (`CURRENT_STATE.md:416-428`);
- plugin remote-debug runtime validation: prerequisite/environment remains unavailable in current evidence;
- PowerShell checker runtime: no `pwsh`; it needs a separate owner and is outside this allowlist;
- inline-agent UI path validation: the API-only attempt does not close the UI route;
- completeness scripts: explicitly unauthorized, with manual audit only;
- seven OpenAPI contract cases recorded at `CURRENT_STATE.md:20`: missing generated owner artifact; they need a separate contract-owned phase and are unrelated to this scanner repair.

The current real-pattern run itself is `FAIL`, not `NOT_RUN`. Its layer portion is unverified despite the misleading zero `NOT_RUN` count. No local synthetic success may substitute for the later protected real-artifact run.

## 12. Planned versus actual Architect work

| Item | Planned | Actual | Deviation |
| --- | --- | --- | --- |
| Writes | This report only | This report only | None. |
| Scanner/test analysis | Read both scripts and existing fixtures | Completed with line-level control-flow trace | None. |
| Production evidence | Redacted statuses/classes only | Reconciled 11/128/0 and 128-event partition without protected content | None. |
| Layer evidence | Source plus Phase H evidence; archive metadata/member names only if needed | Source and checked-in Phase H evidence were sufficient; no offline archive content or member dump was needed | Optional metadata step omitted to minimize handling. |
| Runtime/external actions | None | None | None. |
| Tests | Propose only | No Builder tests run | None; analysis-only gate. |
| Verification | `git diff --check`, Git status | First diff check found Markdown trailing spaces; they were removed and required verification was rerun | Corrective report-only edit; no scope expansion. |
| Report application | One report write | First patch syntax validation rejected the patch before any write; corrected patch then created the report | No filesystem deviation or extra file resulted. |

## 13. Architect command evidence

Start checks:

```text
git branch --show-current
  ctyun/replay-116-p0-secret-architect-20260828
git rev-parse HEAD
  198ee103deac60d1d5be008aeb671c90c93eca62
git status --short --branch
  ## ctyun/replay-116-p0-secret-architect-20260828
verify_git_start.sh ...
  OK branch=codex/enterprise-candidate-1.16.0-20260718 head=198ee103deac60d1d5be008aeb671c90c93eca62 clean=true
```

Evidence counts derived without reading pattern content or matching payloads:

```text
production protected-pattern evidence: 11 PASS / 128 FAIL / 0 NOT_RUN
failure partition: 2 image-list + 2 manifest + 123 config-member + 1 aggregate S-8
config partition: 27 unique members / 123 pattern-target hit events
Phase H synthetic evidence: 13 PASS / 0 FAIL / 1 NOT_RUN
Phase H rerun synthetic evidence: 13 PASS / 0 FAIL / 1 NOT_RUN
Builder tests: NOT_RUN (analysis-only; no implementation)
```

Final Git verification after correcting the report-only whitespace finding:

```text
git diff --check
  PASS (exit 0, no output)
git status --short --branch
  ## ctyun/replay-116-p0-secret-architect-20260828
   A docs/enterprise/replay-1.16.0/P0_SECRET_SCAN_ARCHITECT_2026-08-28.md
```

Exact modified files: `docs/enterprise/replay-1.16.0/P0_SECRET_SCAN_ARCHITECT_2026-08-28.md` only.

Commit ID: none (not authorized). No commit, amend, push, merge, rebase, reset, cherry-pick, Docker action, network call, browser use, protected-pattern read, or external-state action occurred.

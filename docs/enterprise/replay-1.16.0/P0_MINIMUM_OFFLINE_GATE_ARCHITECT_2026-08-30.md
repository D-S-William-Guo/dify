# Enterprise 1.16.0 minimum offline artifact gate architecture

Date: 2026-08-30 (Asia/Shanghai)

Role: Architect

Environment: Development / isolated rehearsal

Plan Fixer revision: incorporates accepted findings P1-01, P1-02, P1-03, P1-04, P2-01,
and P2-02 without changing their severities.

## Verdict

`KEEP_MINIMAL_PATCH`, with deletion of the superseded normal layer scanner.

The minimum gate can prove that actual deployment values cannot enter the offline artifacts by controlling construction inputs and verifying immutable artifact identity. A normal first-party image-content scan is not necessary after both first-party images are rebuilt from the clean exact candidate through those controlled contexts. A normal third-party layer scan is expressly out of scope.

The smallest missing controls are:

1. derive the configuration archive's exact regular-file member set from candidate-tracked paths instead of working-tree discovery or recursive directory operands;
2. use the repository root as the API Docker build context so the existing `api/Dockerfile.dockerignore` allowlist matches `api/Dockerfile`'s `COPY api/...` and `COPY dify-agent/...` instructions;
3. prune nested `.env` and `.env.*` paths from the temporary Web context and prove the boundary with a synthetic canary;
4. require the normal release package to rebuild both first-party images with explicit `-Mode rebuild` from a clean exact candidate SHA before validation;
5. validate release-manifest image identity, repository-matched dependency RepoDigests, and Docker-save metadata without reading layer contents;
6. retain the public development-default-with-warning safeguard over bounded exact regular config members; and
7. replace broad layer/content-scan fixtures with focused synthetic path, archive-metadata, context, identity, and public-default regressions.

No application, Docker Compose, Dockerfile, or Docker-ignore change is needed. The existing ignore
contracts, the corrected API root context, and the minimal Web temporary-context prune together
express the required first-party context boundaries.

## Start branch and SHA

- Expected branch: `ctyun/replay-116-minimum-offline-gate-architect-20260830`
- Verified branch: `ctyun/replay-116-minimum-offline-gate-architect-20260830`
- Expected HEAD: `352abde0339685c0c7b4402ac2d646019483f200`
- Verified HEAD: `352abde0339685c0c7b4402ac2d646019483f200`
- Initial worktree: clean
- Runtime planning mode: skipped because this is a one-file, documentation-only design task. This document is the plan of record.

The initial commands were:

```text
git branch --show-current
  ctyun/replay-116-minimum-offline-gate-architect-20260830
git rev-parse HEAD
  352abde0339685c0c7b4402ac2d646019483f200
git status --short --branch
  ## ctyun/replay-116-minimum-offline-gate-architect-20260830
```

## Repository evidence

### Configuration-package inputs

`scripts/build-enterprise-config-package.sh:39-57` currently constructs the package from:

- three fixed source files: `docker/docker-compose.yaml`, `docker/docker-compose.enterprise.yaml`, and `docker/.env.example`;
- the generated `manifest-<version>.json` and `images-<version>.txt`;
- every working-tree `docker/envs/**/*.env.example` file found by `find` (37 files at this SHA); and
- the complete recursive working-tree contents of `docker/nginx` and `docker/ssrf_proxy`.

At this SHA the two recursive directories contain nine regular files:

```text
docker/nginx/conf.d/default.conf.template
docker/nginx/docker-entrypoint.sh
docker/nginx/https.conf.template
docker/nginx/nginx.conf.template
docker/nginx/proxy.conf.template
docker/nginx/ssl/.gitkeep
docker/ssrf_proxy/docker-entrypoint.sh
docker/ssrf_proxy/squid.conf.template
docker/ssrf_proxy/test_ssrf_proxy_config.sh
```

The producer's `tar` exclusions at lines 80-93 exclude common `.env`, volume, Git, cache, dependency, virtual-environment, and build-output paths. They do not turn the two recursive directory operands into an allowlist and do not reject all certificate or credential-bearing names. An unexpected file beneath either recursive directory can therefore become an input before the checker sees it.

`scripts/ci/check-enterprise-offline.sh:94-153` already has the useful shared path policy: it rejects real `.env` forms, `docker/volumes`, secret directories, common private-key/credential basenames, caches, and generated output. Lines 276-340 check required package entries. This is `VERIFY_ONLY` evidence for the rejection model, but it is not an exact package allowlist. Lines 341-370 extract every config member to scan content, which is unnecessary for the accepted construction policy and retains the archive-link risk recorded by `P0_SECRET_SCAN_PLAN_REVIEW_2026-08-28.md:38-43`.

### First-party API build context

`scripts/build-enterprise-offline.sh:215` passes `$REPO_ROOT/api` as the API build context. That does not match `api/Dockerfile:25-28,113-116`, whose sources are rooted as `api/...` and `dify-agent/...`. The repository's Compose build uses the correct root context at `docker/docker-compose.enterprise.yaml:9-11`.

The intended root-context allowlist already exists in `api/Dockerfile.dockerignore`:

- lines 1-9 deny everything, then admit `api/**` and only the required `dify-agent` files/source;
- lines 11-20 exclude environment files, Python caches, and virtual environments; and
- lines 26-37 exclude API storage/runtime data, logs, tests, and editor state.

`api/Dockerfile` copies only the admitted dependency/source paths into build stages and copies only the application/entrypoint into the production stage. No Dockerfile or ignore-file edit is required. The caller must use `$REPO_ROOT` so those existing rules can operate on the paths the Dockerfile names.

### First-party Web build context

`scripts/build-enterprise-offline.sh:196-212` creates a temporary context containing only root package metadata plus `web`, `e2e`, `packages`, and `sdks`, then removes dependency, generated-build, coverage, and package-store directories before `docker build`.

The copied `web/Dockerfile.dockerignore` is a deny-by-default Dockerfile-specific allowlist:

- it admits root package metadata, `web/**`, `e2e/package.json`, package manifests, and the Node SDK manifest;
- it explicitly excludes `web/.env`, `web/.env.*`, logs, dependency directories, and generated outputs; and
- `web/Dockerfile:77-82` copies only compiled public/standalone outputs and the entrypoint into the production stage.

The producer does not currently prune nested `.env` or `.env.*` paths. The two root-only ignore
patterns therefore do not prevent a nested synthetic environment file from reaching the builder
stage's `COPY . .`. The temporary context remains the right producer, but it requires a minimal
prune of all nested `.env`/`.env.*` paths before `docker build` plus a synthetic context canary.
No separate Web context builder, Dockerfile/Docker-ignore edit, or scanner is justified.

### Candidate and first-party image provenance

`scripts/build-enterprise-offline.sh:105-117` decides reuse from image `COMMIT_SHA`, but lines 215-216 pass `$VERSION`, not the Git commit. The manifest later records `git rev-parse HEAD` at lines 280-323. The image provenance field and release manifest can therefore disagree semantically even when both contain nonempty strings.

The two narrow API content probes at lines 119-141 compare migration filenames and one function name. They neither cover Web nor prove the full candidate source. A caller-controlled label cannot prove how a reused image was built, so label-only `reuse` cannot satisfy normal release provenance.

The accepted solution is A: a normal offline release-gate package must start from a clean exact
candidate SHA and explicitly use `-Mode rebuild` for both first-party API and Web images before
package validation. Their audited contexts and candidate-SHA labels then bind the resulting image
IDs and Docker-save metadata to that build. `reuse` and `smart` may remain fail-closed local
convenience/check-only modes, but cannot produce a normal release-gate package. The two narrow API
content probes may be deleted after this rebuild-only release path applies to both images. No
rebuild-record format, attestation framework, dependency, or helper is needed.

### Image-list and manifest provenance

`scripts/build-enterprise-offline.sh:218-259` derives the image list from `docker compose ... config --images`, sorts it uniquely, requires the enterprise API tag in four services, the enterprise Web tag once, and the two 1.16 Agent images. The selected dependency set remains profile-dependent on the build environment; no target `.env` content belongs in the output.

Lines 282-323 write:

- the official baseline tag and commit;
- the enterprise repository commit;
- each resolved image name;
- Docker image ID; and
- the first RepoDigest when available.

The generator permits empty identity fields. The checker at lines 225-267 validates field presence and name-set equality but not uniqueness, order, identity syntax, candidate binding, or bundle-to-manifest correspondence. The current fake test asserts only that its fake values are nonempty.

For the minimum gate, immutable identity means:

- first-party: exact expected name, candidate commit in both image `COMMIT_SHA` and release manifest, plus a content-addressed `sha256:` image ID;
- dependency: exact resolved name plus a content-addressed image ID for bundle identity, and registry-origin provenance only when a RepoDigest's normalized repository matches the image-list entry's normalized repository; and
- bundle binding: Docker-save `manifest.json` RepoTags equal the image list and each Config digest corresponds to the release manifest image ID.

A mutable tag such as `latest` is not provenance by itself. It is acceptable in the image list only when the bundle and release manifest pin the saved content by immutable ID. Re-resolving that tag later is not equivalent to using the accepted bundle. If no repository-matched RepoDigest exists, record no registry-origin digest, retain only the image ID, and report the registry-origin provenance limitation explicitly.

The Docker-save metadata can be checked with Python standard-library `tarfile` and `json`: read only the single bounded, regular top-level `manifest.json`; do not open or scan any layer member. Support both legacy `<digest>.json` and Docker 29 `blobs/sha256/<digest>` Config names.

### Current checker and test coverage

The checker currently proves:

- required image names and release-manifest field presence/name equality;
- config archive listability, a required subset, all repository env examples, and broad forbidden path classes;
- Docker-save archive listability and a superficial top-level layout; and
- a known public development-default diagnostic plus optional protected-pattern content matching.

It does not prove exact config membership or immutable image identity. Its bounded known public
development-default diagnostic is a distinct safeguard that must remain: it reads only exact
regular config members with Python `tarfile`, without extraction, and requires the warning when
the public default is present. Its layer loop at lines 405-451 only selects `*/layer.tar`, treats
inner layers as gzip, scans any matching dependency layer, and can see zero layers without
recording `NOT_RUN`. The final S-8 logic at lines 463-483 can conflate incomplete coverage with
success. Those are reasons to delete the normal layer scanner, not reasons to repair it.

`scripts/ci/check-enterprise-offline-tests.sh` currently covers reuse/version matching, the two partial API probes, dry-run side effects, required image names, manifest field presence, config required members, `.env`, volume and public-development-default canaries, and a fake gzip `*/layer.tar`. It lacks exact member, key/certificate/credential path, archive type/path, API root-context, candidate-SHA, malformed identity, missing provenance, and bundle-metadata binding cases.

## Accepted policy and non-goals

The normal release invariant is:

> Actual deployment values exist only in the target deployment directory's `.env` and runtime mounts. They never enter the offline image bundle or configuration package.

Accepted normal Development controls:

1. exact candidate-tracked configuration-package member allowlisting;
2. fail-closed rejection of real environment files, runtime volumes, private keys, certificates, credential-bearing paths, unsafe archive paths, non-regular allowed members, duplicates, and unexpected members;
3. deny-by-default first-party API/Web Docker contexts, including nested Web environment-path pruning, followed by an explicit clean exact-candidate `rebuild` of both images for every normal release-gate package;
4. exact first-party image-name checks and immutable identity for every manifest entry;
5. Docker-save metadata-to-release-manifest binding without layer reads; and
6. a bounded public development-default-with-warning check over exact regular config members, plus synthetic canaries only.

Non-goals:

- no normal content scan of third-party dependency layers;
- no normal first-party layer content scan after construction evidence passes;
- no protected pattern source or real production/gray/Plan B value;
- no classification or remediation of historical protected-audit hits;
- no Docker daemon, artifact load/run/export, browser, network, target connection, secret rotation, signing, deployment, or runtime-volume action in this task;
- no new script, package, dependency, service, scanner framework, or application change; and
- no modification, merge, or recommendation to merge the retained uncommitted broad-scan Plan Fixer worktree.

## Current-control disposition

| Current control | Disposition | Minimum action |
| --- | --- | --- |
| Config producer fixed files and 37 `*.env.example` inputs | `KEEP_MINIMAL_PATCH` | Derive the 37 env examples from the exact candidate tree, require the 49 tracked source paths plus the two version-matched generated members, and replace recursive directory operands with the exact nine fixed tracked paths. Reject untracked or changed membership before packaging. |
| Config producer broad `tar --exclude` list | `DROP_REDUNDANT` after exact inputs | Exact inputs become the construction boundary. Retain only harmless defense-in-depth exclusions if they do not imply recursion is acceptable. |
| Checker `forbidden_path` policy | `KEEP_MINIMAL_PATCH` | Reuse it for explicit diagnostics; add certificate and credential-directory cases and exact member-set/type validation. |
| Config archive extraction/content scan | `KEEP_MINIMAL_PATCH` | Remove extraction and generic content scanning; retain only bounded reads of exact regular config members for the public development-default-with-warning rule. |
| API root-context Docker ignore | `VERIFY_ONLY` | Existing `api/Dockerfile.dockerignore` is sufficient after fixing the caller context. |
| Web temporary context and Docker ignore | `KEEP_MINIMAL_PATCH` | Retain the production source allowlist; prune nested `.env`/`.env.*` paths in the temporary-context producer and prove absence with a synthetic canary. Do not edit the Dockerfile or Docker-ignore file. |
| Image `COMMIT_SHA=$VERSION` | `KEEP_MINIMAL_PATCH` | Move `git rev-parse HEAD` before image validation/build and use that SHA for API and Web. |
| First-party release provenance and two partial API `docker run` probes | `KEEP_MINIMAL_PATCH` | Require explicit `-Mode rebuild` of API and Web from the clean exact candidate for a normal release-gate package, then delete the probes. Keep `reuse`/`smart` only as non-release convenience/check-only modes. |
| Required first-party image counts/names | `VERIFY_ONLY` | Retain exact API/Web and Agent assertions. |
| Release-manifest field/name validation | `KEEP_MINIMAL_PATCH` | Require unique exact ordering, valid candidate commit, valid immutable identities, and repository-matched RepoDigest provenance when recorded. |
| Docker-save top-level name check | `KEEP_MINIMAL_PATCH` | Replace substring presence with bounded parsing of the single regular top-level `manifest.json` and bind tags/config IDs. |
| Normal `*/layer.tar` path/content scan and S-8 aggregation | `DROP_SUPERSEDED` | Delete; do not repair raw/gzip/blob traversal. |
| Normal checker `-SecretsPattern` path | `DROP_FROM_NORMAL_GATE` | Remove protected-pattern input and all layer-content scanning from this Development gate while retaining the bounded public-default warning rule. A future Protected release audit needs separate authorization and reviewed tooling. |
| Fake gzip layer fixture and broad-scan plan findings | `DROP_SUPERSEDED` | Replace only with metadata/context/identity/path canaries. Do not implement the old layer parser. |

## Smallest Builder/test allowlists

### Builder production allowlist

Only these files may contain production changes:

```text
scripts/build-enterprise-offline.sh
scripts/build-enterprise-config-package.sh
scripts/ci/check-enterprise-offline.sh
```

Within that allowlist, the offline producer owns clean exact-candidate rebuild enforcement, Web
context pruning, and image/manifest generation; the config producer owns the candidate-tracked
member set; and the checker owns exact archive metadata, the bounded public-default rule, and
identity/bundle validation.

No Dockerfile, Docker-ignore, Compose, API, Web, Agent, PowerShell, documentation, dependency, or new helper file is needed.

### Test allowlist

Only these files may contain test-fixture changes:

```text
scripts/ci/check-enterprise-offline-tests.sh
scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker
```

`fake-git` already returns a deterministic 40-character commit and should remain unchanged. The fake Docker IDs/digests must become syntactically valid deterministic SHA-256 identities. No fixture may call a real Docker daemon.

### Exact configuration member allowlist

The package's regular files must equal, not merely contain, the accepted set derived from the
exact candidate: 49 candidate-tracked source paths plus two version-matched generated paths.
The tracked path set is read from the candidate tree rather than discovered from the working tree:

- the three fixed Docker source files;
- the two generated version-matched manifest/image-list files;
- the sorted 37-file candidate-tracked set under `docker/envs` whose names end exactly in `.env.example`; and
- the nine fixed nginx/SSRF files listed in Repository evidence.

At this SHA the expected total is 51 regular files. The producer must fail if candidate-tracked
membership is missing or changed and must never expand it from working-tree discovery. An
untracked `*.env.example`, unexpected member, duplicate, unsafe path, or non-regular member is a
failure. Directory headers may be omitted. If retained for compatibility, they must be safe
parents of an allowed regular member and must not expand membership.

## Behavioral acceptance matrix

| ID | Synthetic setup/action | Expected result |
| --- | --- | --- |
| C01 | Build the config package from the unchanged fixture repository. | Exactly the 49 candidate-tracked source members plus two version-matched generated members; 51 regular files total, no extras; PASS. |
| C02 | Add an untracked `docker/envs/.../rogue.env.example` plus `.env`, volume, key, certificate, and credential-path canaries beneath plausible Docker paths before packaging. | The rogue `*.env.example` and every other unexpected input are rejected, no such member is packaged, and the producer exits nonzero. |
| C03 | Present a synthetic config archive with `docker/.env`. | Redacted real-environment diagnostic; FAIL and nonzero. |
| C04 | Present a synthetic config archive with `docker/volumes/...`. | Redacted runtime-volume diagnostic; FAIL and nonzero. |
| C05 | Present synthetic `*.key`/private-key and `*.crt`/certificate members. | Redacted key/certificate diagnostics; FAIL and nonzero. |
| C06 | Present a synthetic member under `.secrets`, `secrets`, or `credentials`. | Redacted credential-path diagnostic; FAIL and nonzero. |
| C07 | Present duplicate, absolute, `..`, symlink, hardlink, device, or FIFO members, including an allowed name with the wrong type. | Metadata-only rejection; no extraction or dereference; FAIL and nonzero. |
| C08 | Omit a candidate-tracked member, add an unexpected or duplicate member, or present an allowed name with an unsafe/non-regular type. | Exact-set/type mismatch identifies only the path; FAIL and nonzero. |
| A01 | Run fake `rebuild` and capture the API build call. | Dockerfile is `api/Dockerfile`; final context argument is repository root; PASS. |
| A02 | Inspect the existing API Dockerfile-specific ignore contract in the focused test. | Deny-by-default admits only `api/**` and required `dify-agent` source; env/runtime exclusions present; PASS. |
| W01 | Place nested synthetic `.env` and `.env.*` canaries throughout the copied Web-context source roots, capture the fake Web build, and inspect its temporary context plus the existing Dockerfile-specific ignore contract. | The named source roots remain; every nested environment canary is absent before `docker build`; runtime/generated exclusions remain; PASS without Dockerfile/Docker-ignore changes. |
| P01 | From a clean exact candidate SHA, create a normal release-gate package with explicit `-Mode rebuild`. | Both API and Web build through the audited contexts with that candidate SHA before package validation; their image IDs bind to manifest and bundle metadata; PASS. |
| P02 | Attempt a normal release-gate package through `reuse`/`smart`, including images carrying caller-controlled matching `COMMIT_SHA` labels, or rebuild from a dirty/mismatched candidate. | Reject candidate provenance; FAIL and nonzero. `reuse`/`smart` remain non-release local convenience/check-only modes only. |
| M01 | Validate a well-formed image list/release manifest/fake Docker-save metadata graph. | Unique ordered names match; expected first-party images exist; IDs/config digests bind; PASS. |
| M02 | Duplicate, omit, reorder, or rename an image between the image list and release manifest. | FAIL and nonzero. |
| M03 | Make the release manifest candidate commit differ from the first-party build commit. | FAIL and nonzero. |
| M04 | Give a dependency multiple RepoDigests including one whose normalized repository matches its image-list name; then give only mismatched RepoDigests with a valid image ID. | Select and validate the matching RepoDigest in the first case. In the second, record no registry-origin digest, retain image-ID bundle identity, PASS with the explicit provenance limitation, and never attribute a mismatched repository digest. |
| M05 | Remove or malform required immutable identity for a dependency or either first-party image. | Executed identity validation is `FAIL`; overall exit is nonzero. |
| M06 | Use Docker 29 `blobs/sha256/<config>` and legacy `<config>.json` Config names in synthetic Docker-save metadata. | Both bind to release-manifest `sha256:<config>` IDs; PASS. |
| M07 | Make required top-level `manifest.json` absent, duplicate, non-regular, malformed, oversized, or inconsistent. | Executed metadata validation is `FAIL`; overall exit is nonzero; no layer opened. |
| D01 | Search fake-Docker calls during the full suite. | No real daemon; no layer extraction/content scan; no protected value/pattern; PASS. |
| R01 | Run all retained no-pattern offline regressions, including the known public development default once without and once with its required warning. | The missing-warning case fails and the warned case passes using bounded reads of exact regular config members; existing CLI/output paths, non-release reuse/check-only behavior, config extraction usefulness, and required image assertions remain compatible. |

The suite must report its newly observed exact total; it must not copy the historical `21/21` claim.

An executed normal-gate check that observes missing or malformed required identity, metadata, or
artifact evidence is `FAIL` and exits nonzero. `NOT_RUN` is reserved for a genuinely unexecuted
environment prerequisite, such as real Docker runtime validation, PowerShell parity, or the
separately authorized Protected release audit.

### Compatibility expectations

- Keep `.sh` producer CLI arguments and output filenames unchanged.
- A normal release-gate package always requires explicit `-Mode rebuild` of both first-party images from the clean exact candidate before validation. `reuse` and `smart` may remain fail-closed non-release local convenience/check-only modes and cannot satisfy or emit normal release-gate provenance.
- Keep `-CheckOnly` free of build, pull, and save operations; it cannot create missing release provenance.
- Existing same-tag first-party images, even with a caller-controlled matching `COMMIT_SHA`, cannot satisfy normal release provenance and require the explicit rebuild path.
- Config package extraction yields the same 51 useful regular files; directory-header omission is acceptable because archive extraction creates parents.
- The normal checker's `-SecretsPattern` compatibility is intentionally removed. It is not a supported substitute for a Protected release audit.
- The public development-default-with-warning safeguard remains compatible without protected-pattern input or general content scanning.
- PowerShell parity is not changed or claimed. The `.ps1` paths and runtime remain `NOT_RUN` until a separately owned parity phase is authorized.

## Development-versus-Protected-release boundary

### Development / isolated rehearsal

The Builder, Reviewer, and Rereviewer may use only repository source, fake commands,
standard-library `tarfile`/`json` metadata parsing, bounded reads of the exact regular config
members for the public-default warning rule, and generated synthetic canaries. They must not use
Docker, network access, built release artifact contents, a browser, protected patterns, real
credentials, production/gray/Plan B values, target configuration, runtime volumes, or target
connections. Normal `-SecretsPattern` input and every first-/third-party layer-content scan are
deleted, not repaired or replaced.

The Development gate answers only:

- were the configuration inputs exactly allowlisted;
- were first-party contexts structurally unable to send local environment/runtime paths;
- were both first-party images explicitly rebuilt from the clean exact candidate before normal package validation;
- did image-list, release-manifest, and Docker-save metadata agree; and
- did every bundled dependency have immutable bundle identity and repository-matched registry provenance when claimed.

### Protected release audit

A Protected release audit is separately authorized, uses a designated secure runner and named unchanged artifacts, and may test only whether protected values are absent. It must keep values out of commands, arguments, logs, reports, screenshots, commits, and prompts and retain only redacted boolean/count evidence. It authorizes no target access, secret rotation, deployment, or artifact rewrite.

The historical redacted hits remain unclassified. This plan does not call them clean, false positives, resolved, or safe. Deleting the broken normal broad scanner does not change their status. Only the protected-pattern owner and a separately authorized audit can classify or close them.

## Known limitations

- No first-party Docker build, Docker-ignore runtime evaluation, Docker-save, load, or boot is performed in this Architect/Plan Fixer task. Those environment prerequisites are genuinely `NOT_RUN`; the future normal release gate must perform the explicit API/Web rebuild before validation.
- A Docker image ID pins the bundled content but does not prove its registry origin. When no RepoDigest repository matches the named dependency, the manifest records no registry-origin digest and retains only image-ID bundle identity; registry-origin provenance remains an explicit limitation and the accepted bundle must not be reconstructed by mutable tag.
- The normal metadata gate does not attest publisher signatures or SBOMs. Formal signing/audit remains separately authorized.
- True no-network host load/boot, PowerShell runtime/parity, independent deployment rehearsal, and target deployment are `NOT_RUN`.
- The current checker's protected-pattern and layer-scan defects are not repaired. That machinery is removed from the normal gate; only the bounded public development-default warning safeguard remains. A future Protected release audit needs its own reviewed design.
- Existing historical protected-audit hits remain redacted and unclassified.
- This plan relies on the stage contract's exact clean start SHA for source provenance. Builder/Reviewer commands must record exact branch, HEAD, and status; a dirty or mismatched start stops the stage.

## Commands with PASS/FAIL/NOT_RUN counts

### Architect commands

No Docker, real artifact-content, browser, network, or protected-pattern command was permitted or run.

```bash
bash -n scripts/build-enterprise-offline.sh \
  scripts/build-enterprise-config-package.sh \
  scripts/ci/check-enterprise-offline.sh \
  scripts/ci/check-enterprise-offline-tests.sh
bash scripts/ci/check-enterprise-offline-tests.sh
git diff --check
git status --short --branch
```

Observed command results:

| Command | PASS | FAIL | NOT_RUN | Result |
| --- | ---: | ---: | ---: | --- |
| Required `bash -n` | 4 files | 0 | 0 | Exit 0, no output. |
| Existing focused fake-Docker fixture suite | 24 cases | 0 | 0 | Exit 0; `all 24 enterprise offline tests passed`. |
| Real Docker/image/artifact runtime verification | 0 | 0 | 1 | `NOT_RUN`: forbidden in this architecture task. |
| PowerShell runtime/parity | 0 | 0 | 1 | `NOT_RUN`: outside the allowlist and no authorized runtime. |
| Protected release audit | 0 | 0 | 1 | `NOT_RUN`: separate authorization and secure runner required. |

The focused suite used only its fake Docker shim and synthetic temporary archives. Its labels mentioning a “real image bundle” describe the fixture's tar shape, not a Docker-produced or release artifact. No historical count was substituted.

### Plan Fixer verification addendum

The Plan Fixer changed only this document. The existing suite is baseline evidence; it does not
claim that the revised Builder behaviors or synthetic cases already exist.

| Command | PASS | FAIL | NOT_RUN | Result |
| --- | ---: | ---: | ---: | --- |
| Required branch/SHA/clean preflight | 3 | 0 | 0 | Exact branch and SHA; clean initial status. |
| Required `bash -n` | 4 files | 0 | 0 | Exit 0, no output. |
| Existing focused fake-Docker fixture suite | 24 cases | 0 | 0 | Authoritative standalone rerun exited 0; `all 24 enterprise offline tests passed`. |
| Real Docker/image/artifact runtime verification | 0 | 0 | 1 | `NOT_RUN`: forbidden in this Plan Fixer task. |
| PowerShell runtime/parity | 0 | 0 | 1 | `NOT_RUN`: outside the allowlist and no authorized runtime. |
| Protected release audit | 0 | 0 | 1 | `NOT_RUN`: separate authorization and secure runner required. |
| Browser, network, target, database, container, and volume checks | 0 | 0 | 1 | `NOT_RUN`: forbidden and unnecessary for this docs-only repair. |

### Future Builder/Reviewer commands

```bash
bash -n scripts/build-enterprise-offline.sh \
  scripts/build-enterprise-config-package.sh \
  scripts/ci/check-enterprise-offline.sh \
  scripts/ci/check-enterprise-offline-tests.sh \
  scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker
bash scripts/ci/check-enterprise-offline-tests.sh
git diff --check
git status --short --branch
```

Builder and independent Reviewer must run the same focused suite from their exact submitted SHA and report its actual PASS/FAIL/NOT_RUN totals. Docker, PowerShell, real artifact, protected-pattern, browser, network, and target checks remain `NOT_RUN` in Development.

## Planned versus actual changes

| Item | Planned | Actual | Deviation |
| --- | --- | --- | --- |
| Write scope | This architecture document only | This architecture document only | None. |
| Repository evidence | Seven named sources plus directly selected Dockerfiles/ignore files, Compose build declarations, and fake command fixtures | Completed without reading `.env`, artifacts, protected data, or external state | Direct supporting sources were needed to trace the named build contexts; no scope expansion into runtime data. |
| Implementation | None | None | None |
| Runtime/external actions | None | None | None |
| Focused checks | Required shell syntax, synthetic fake-Docker suite if safe, diff check, status | Syntax PASS for 4/4 files; focused suite PASS 24/24; final diff/status recorded below | None. |

### Plan Fixer addendum

| Item | Planned | Actual | Deviation |
| --- | --- | --- | --- |
| Write scope | Architect plan only | Architect plan only | None. |
| Accepted findings | Repair P1-01, P1-02, P1-03, P1-04, P2-01, and P2-02 without severity changes or omitted conditions | All six are explicit in the plan, dispositions, matrix, compatibility, boundaries, limitations, and verification ownership | None. |
| Implementation | No code or test changes | No code or test changes | None. |
| Source evidence | The Architect plan and accepted Plan Review | Both sources remained authoritative; `CURRENT_STATE.md` was additionally read as required replay context and did not override them | Additional read-only context; no write or decision-scope expansion. |
| Focused checks | Preflight, four-file syntax, focused suite, diff check, status | Preflight 3/3, syntax 4/4, and authoritative suite 24/24 PASS; final diff/status recorded below | An initial parallel suite observation yielded after 23 visible PASS rows; the required standalone rerun completed 24/24 with exit 0. |
| Runtime/external actions | None | None | None. |

## git diff --check

Architect historical result: PASS (exit 0, no output) after the original report update. Because
the only changed file was then untracked, `git diff --no-index --check /dev/null <report>` was also
run: it emitted no whitespace error (its expected status 1 only denotes that the new file differs
from `/dev/null`).

Plan Fixer addendum: final `git diff --check` for the tracked one-file repair exited 0 with no
output.

## git status

Architect historical final status:

```text
## ctyun/replay-116-minimum-offline-gate-architect-20260830
?? docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md
```

Exact modified files: `docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md` only.

Plan Fixer final status:

```text
## ctyun/replay-116-minimum-offline-gate-plan-fixer-20260830
 M docs/enterprise/replay-1.16.0/P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md
```

## Commit ID: none

No commit or amend is authorized.

## No-push/external-action confirmation

No merge, rebase, reset, checkout, cherry-pick, commit, amend, push, PR, remote modification, Docker action, artifact inspection, browser action, network call, protected-pattern access, secret handling, target connection, database/container/volume action, or production/gray action is authorized by this plan.

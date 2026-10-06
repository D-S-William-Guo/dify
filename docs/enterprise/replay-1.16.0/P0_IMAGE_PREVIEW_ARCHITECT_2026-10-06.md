# P0 embedded-image preview: Architect plan — 2026-10-06

## 1. Scope, immutable start, and investigation plan

**Result: source investigation and proposed implementation/validation only. Image preview remains release-blocking; no behavior was implemented or runtime result newly accepted.**

- Verified branch: `ctyun/replay-116-image-preview-architect-20261006`.
- Verified starting and final HEAD: `fb0928bfff62bcdbbd954712573213971f8e3949`.
- Base integration branch: `codex/enterprise-candidate-1.16.0-20260718`.
- Official `1.16.0`: `5c6372d2f76d240265b92fd27c16bc772ffcb107`, verified from the local tag object.
- Environment: **Development / historical-data rehearsal**. Historical local data does not authorize access to its live source, production, or gray environments.
- Initial `git status --short --branch`: only `## ctyun/replay-116-image-preview-architect-20261006`; clean index/worktree.
- Only permitted write, and the exact file added: `docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md`. Current observed state is **intent-to-add**, with **no report content staged**: status is ` A` (leading space), the cached diff is empty, and the working-tree diff lists the report. The index holds the empty blob with intent-to-add flags; its origin is not established.

Before investigating, the agent stated this plan, report path, verification method, and risks in commentary: verify immutable start; read required skills and applicable AGENTS; trace authorization → retrieval serialization → response normalization/contract → Markdown → preview validation; compare official local Git objects; propose the minimum shared repair and synthetic checks; write only this report and verify Git/whitespace. Runtime planning mode is unavailable in this session; the explicit written plan substitutes for that UI mode.

Read instructions: root, `api/AGENTS.md`, `web/AGENTS.md`; installed `/home/ctyun/.codex/skills/replay-dify-enterprise/SKILL.md` and its official-first reference; `/home/ctyun/.codex/skills/orchestrate-claude-squad/SKILL.md`. Role is Architect. Existing accepted contract supplies this stage's authorization; it does not authorize instance/controller operations, implementation, commits, or later gates.

Primary risks identified before reporting: historical observations are not a current reproduction; a signer reused without checking query boundaries can corrupt refreshed links; a shared signer correction affects additional callers; runtime route/configuration and expiry behavior require later acceptance. No real secret, provider credential, proxy value, sensitive response payload, or live signed URL is included here.

## 2. Sources and acceptance status

`CURRENT_STATE.md:9–18`, especially the **2026-10-04 override**, is authoritative over older PASS summaries. Its prior candidate checkpoint `18a3658e65fd2678c19d35a44d5c2c2c6403285d` is an ancestor of this task HEAD, not a requirement that the worktree use that older SHA. Local origin still names that earlier checkpoint; no remote was contacted or updated.

Read-only historical evidence: `/home/ctyun/BigData/GitHub/dify-enterprise-1.16.0/output/playwright/replay-116-regression-20260930.md:12–13,24–34`. Relevant observations were extracted with URLs redacted; no historical payload was copied into the report.

| Evidence class | Finding and limit |
| --- | --- |
| Historical browser evidence | Line 12 reports embedded file-preview requests missing signature parameters and HTTP 400; text recall works. It also reports the symptom in 2026-09-24 logs, preceding the 9/30 image switch. This stage did not open those logs or reproduce the browser action. |
| Independent accepted behavior | Line 13 reports DOCX original download PASS. The 10/04 state override accepts Agent, text generation, and file workflow PASS. These remain separate accepted results; none closes image preview. |
| Current source facts | The conversion chain below omits signing and explicitly defaults the response field to null. Both preview routes require signature query fields. |
| Inference requiring later validation | Populating signed response content should eliminate the reported missing-parameter failure for embedded images; successful rendering, routing, file existence, storage access, and expiry handling remain NOT_RUN. |

Retain existing valid runtime connection configuration. Default-password rotation is an independently deferred hardening item, not a prerequisite or blocker for this repair. Do not change model/provider bindings, including those separately accepted historical application migrations.

## 3. Complete source flow and missing-signature boundary

Line references below describe the unchanged task-start source.

| Step | Source evidence | Observed source contract |
| --- | --- | --- |
| Console authorization | `api/controllers/console/datasets/hit_testing.py:30–62` | POST `/console/api/datasets/<dataset_id>/hit-testing`; setup/login/account, billing, tenant/user, `DATASET_PIPELINE_TEST` RBAC, session; validate dataset before retrieval. |
| Dataset permission | `api/controllers/console/datasets/hit_testing_base.py:84–100`; `api/services/dataset_service.py:1361–1380` | Check actor tenant matches dataset tenant, then only-me/partial-team access with owner behavior preserved. Missing dataset is 404; permission error becomes 403. |
| Service API authorization | `api/controllers/service_api/dataset/hit_testing.py:17–68`; `api/controllers/service_api/wraps.py:285–349,389–392` | Same controller supports `/v1/datasets/<dataset_id>/hit-testing` and `/v1/datasets/<dataset_id>/retrieve`. Dataset token validates tenant-scoped dataset and `enable_api`, installs its tenant owner account, then shared validation/retrieval runs. The handler's implicit account fallback is intentional existing behavior, not authorization to bypass the wrapper. |
| Shared retrieval | `hit_testing_base.py:113–139`; `api/services/hit_testing_service.py:104–188,235–245` | Both controllers call `perform_hit_testing` → `HitTestingService.retrieve` → `compact_retrieve_response` → `_dump_retrieval_records`. Retrieval uses the already authorized dataset ID. Existing query-history recording/commit is unrelated and must remain intact. |
| Retrieval segments | `api/core/rag/datasource/retrieval_service.py:488–507,744–791`; `api/core/rag/embedding/retrieval.py:26–34` | Formatter constructs `RetrievalSegments` holding a `DocumentSegment`, child chunks, files, score, summary. It does not populate signed text. |
| Serialization boundary — root cause | `api/services/hit_testing_service.py:59–101`, especially `68,80,89–93` | `record.model_dump()` serializes the segment's dataclass fields; `sign_content` is a property rather than a mapped/dataclass field (`api/models/dataset.py:905–943,1006–1010`; `api/models/base.py:19`). Conversion adds `created_at` and document metadata but never evaluates or inserts `segment.sign_content`. All three dump branches lack that step. |
| Normalization makes omission visible | `hit_testing_base.py:51–81`, especially `65` | `setdefault("sign_content", None)` fills the omitted property with null. It normalizes keywords/child_chunks/files to lists and defaults tsne/summary. It is not the place where signing was attempted and failed. |
| Response validation | `api/fields/hit_testing_fields.py:27–50,79–90` | `HitTestingResponse` retains raw `content` and nullable `sign_content`, plus document, timestamps and collection fields. `dump_response` on both controllers validates this shape; null is legal, so schema validation does not catch the rendering bug. |
| Console consumption | `web/service/knowledge/use-hit-testing.ts:12–19`; `web/app/components/datasets/hit-testing/components/result-item.tsx:25–29,50–69`; `components/chunk-detail-modal.tsx:27–30,99–106` | Hook posts hit-testing; result card and ordinary chunk-detail Markdown both render `sign_content || content`. Null selects unsigned historical content. Q&A detail uses separate plain question/answer rendering (`chunk-detail-modal.tsx:108–120`); do not claim this Markdown repair changes that branch. |
| Image request | `web/app/components/base/markdown/streamdown-wrapper.tsx:214–218,243`; `markdown/markdown-utils.ts:61–81`; `markdown-blocks/img.tsx:9–14`; `image-gallery/index.tsx:38–53` | Markdown passes the allowed source through `Img`/ImageGallery to `img src`, with optional enlarged preview. No component signs URLs. |
| Signature-required endpoint | `api/controllers/files/image_preview.py:19–26,32–71,74–106`; `api/services/file_service.py:197–231` | Both image-preview and file-preview require timestamp/nonce/sign. Missing fields fail request-model validation (historically HTTP 400); provided signatures are verified before file load. Verification failure is 404 in FileService. Never turn a missing-signature fix into unsigned public file access. |

`api/core/rag/extractor/word_extractor.py:162,190` creates unsigned Markdown file-preview references when extracting images. Durable unsigned references are expected: signing belongs to response presentation, not indexing or stored content. `DocumentSegment.sign_content` delegates to existing `get_sign_content()`; that method generates endpoint-specific HMAC parameters without a database query or content mutation (`dataset.py:1010–1073`).

### Caller coverage and exclusions

Repository-wide caller search found the sole production caller of `_dump_retrieval_records` at `compact_retrieve_response:245`. That function is reached by normal retrieval at `188` and the empty metadata-filter result at `146`. The sole production caller of `HitTestingService.retrieve` is shared `perform_hit_testing:122`; both controller classes above use it. Fixing only Console or frontend would leave Service API response content broken.

External knowledge hit-testing calls the separate `external_retrieve` / `compact_external_retrieve_response` (`hit_testing_service.py:191–264`, frontend hook `use-hit-testing.ts:22–28`). Its records contain content/title/metadata, not `DocumentSegment`; it bypasses the proposed repair. Separately signed `files[].source_url` attachment rendering is not the embedded `segment.content` boundary. DOCX original download and accepted application behavior have separate paths/status.

If the existing signer changes, related callers also include:

- `api/core/rag/retrieval/dataset_retrieval.py:325,328,502,504` (retrieval node/context, including question-answer formatting).
- `api/core/tools/utils/dataset_retriever/dataset_retriever_tool.py:178,180`.
- `api/core/tools/utils/dataset_retriever/dataset_multi_retriever_tool.py:108,110`.
- `DocumentSegment.sign_content` itself and segment-response consumers declaring that field (`api/fields/segment_fields.py:37–43`).

These are existing signer users; they are not proven to share the missing-property omission. Signer compatibility must be checked, without rewriting those callers.

## 4. Official-first comparison and patch disposition

Local `git diff 1.16.0 HEAD` is **empty** for the service, base normalizer, retrieval entity, dataset model, hit-testing DTO, both hit-testing controllers and preview controller. The accepted symptom therefore exists in source matching the official target, not in a demonstrated surviving enterprise change.

Relevant official history already present **inside** the baseline:

- `2afa39cdcbb31e6cdaae6012386a9a6167141576`, “fix: knowledge hit-testing render failed. (#36106)”: introduced document-enriching dump conversion, but did not insert signed content.
- `f720a3bed2b23da49cca81e05473090ab2b69692`, “fix: Image rendering in the knowledge base failed. (#35914)”: adjusts attachment/signature URL handling; it does not repair this omitted hit-testing property. Both commits are verified ancestors of `1.16.0`, not newer fixes to apply.

The local official main snapshot is `c2428361c442eb4bfcc658e2fd3c0328e40902d7` (2026-04-03); the target tag is dated 2026-07-17. No later official release tag is available locally. `git log 1.16.0..origin/main` yields no changes in the affected service/model/normalizer. `git rev-list --all --not 1.16.0` for those files returns only `ba94e890c0c56c56641087a99d36899e033e6897` and `91666df708ac383bdfc1d61962a83b311d4f5dbe`: enterprise merge/performance history; inspected changes are document enrichment / prefetched dataset counters, not a newer official signature fix. Candidate path history after the baseline is empty, and final blobs match the baseline.

**Disposition: KEEP_MINIMAL_PATCH for the remaining release requirement**, implemented on official 1.16.0's current shared service boundary. This means a new narrowly scoped candidate repair; it does not assert that an old enterprise signing patch exists to replay. Do not classify the HTTP 400 as an enterprise-patch regression solely because replay exposed it. No fetch, ref update, dependency update, or invented upstream commit is justified. A newer official fix outside local objects is unknown.

## 5. Surface-to-contract row

| Actor / permission | Backend contract | Route / visible navigation / active state | Result and later headed acceptance |
| --- | --- | --- | --- |
| Existing authorized dataset actor in the migrated local workspace; dataset access plus retrieval-recall capability, and backend `DATASET_PIPELINE_TEST` RBAC when enabled. Service consumer uses a dataset token for the owning tenant with API access enabled. | Console POST `/console/api/datasets/<datasetId>/hit-testing`; Service API POST `/v1/datasets/<datasetId>/hit-testing` and `/retrieve`. Preserve `query.content`, records, raw `segment.content`, signed `segment.sign_content`, document/timestamp/score and normalized list fields. | UI `/datasets/<datasetId>/hitTesting`; click visible **Knowledge Base → existing dataset → Recall Test** (en-US source labels “Knowledge” / “Retrieval Testing”, `common.json:142,382`). Sidebar entry uses that route and permission/pipeline publish gating (`app-sidebar/dataset-detail-section.tsx:70–86`). Direct unauthorized route redirects using existing ACL (`layout-main.tsx:85–107`). Verify sidebar selection on actual navigation in the browser; source inspection is not active-state acceptance. | Submit a non-sensitive query recalling an existing image-bearing historical chunk. Confirm recall response 200 and non-null signed content, visible card image and detail-modal image, preview request 200 and decoded image (`complete` and `naturalWidth > 0`), then enlarged preview if exposed. Capture only redacted status/parameter-name/boolean evidence, never signed URLs. Recheck text and original-download outcomes separately. |

No new route, permission, frontend contract, navigation item, feature flag, or generated schema is needed. Do not test success only by hand-entering the route; visible navigation and direct-route denial are later acceptance requirements.

## 6. Minimal proposed Builder scope and alternatives

### Primary change

In `_dump_retrieval_records`, populate each returned valid segment dictionary's `sign_content` from its source `DocumentSegment.get_sign_content()` (or existing property), while leaving `content` unchanged. Keep serialization/signing together at this shared response boundary, covering the no-document-ID early return and invalid/absent-ID fallback as well as normal document enrichment. Serialize/sign once per record; preserve missing-document skip/warning behavior, created-at injection, record ordering, and collection normalization. Do not add a global Pydantic serializer or a new signing service.

### Required narrow signer compatibility correction

Source inspection exposes two risks in the reusable signer that the requested regressions must address:

1. `dataset.py:1015,1032` uses an optional query with lazy `.*?`. It can consume the question mark with zero query characters, retaining the old query after the new signature. A signed input can consequently produce a contaminated signature. Replace only those query suffix patterns with bounded consumption through the current URL boundary, following the existing tools branch's whitespace/parenthesis/quote boundary convention (`1050`). Preserve the host/prefix and surrounding Markdown. This is a source-derived defect prediction, **not a test executed in this stage**.
2. Matches are gathered by endpoint family (`1014–1065`) and applied with a cumulative offset in insertion order (`1067–1071`). Mixed-family URLs appearing in a different textual order invalidate offsets. Order replacements by their original start position (retain the existing offset algorithm), or apply them from right to left without offsets; choose one small correction, not both.

These method-only corrections support required refreshed and multiple/adjacent historical image cases. They do not authorize rewriting model definitions, persistence, or URL-security policy. Builder must first demonstrate the failures with synthetic tests; if the failures differ or require a broader parser/host/security redesign, stop for scope review.

### Proposed exact write allowlist (future authorization only)

| File | Bounded purpose |
| --- | --- |
| `api/services/hit_testing_service.py` | Only shared record serialization/sign-content population and necessary intent note. |
| `api/models/dataset.py` | Only `DocumentSegment.get_sign_content` query-boundary and replacement-order corrections; leave HMAC/domain/config and model definitions intact. |
| `api/tests/unit_tests/services/test_hit_testing_service.py` | Add synthetic real-segment/real-RetrievalSegments conversion and preservation cases; mock session document lookup, no real data. |
| `api/tests/unit_tests/models/test_dataset_models.py` | Add small parameterized signer behavior regressions for both preview routes and replacement boundaries/order. |
| `api/tests/unit_tests/controllers/console/datasets/test_hit_testing_base.py` | Exercise signed conversion through real shared normalization and `HitTestingResponse`, not a hardcoded signed return fixture. |

Existing Console and Service API controller suites are read-only related checks; no controller edit is proposed. Test shared conversion/DTO preservation in the allowlisted base suite, then run both existing caller suites. If an existing controller suite needs a necessary new behavioral assertion beyond this arrangement, obtain an enumerated allowlist amendment first. Any later Builder evidence report path must be separately named in its contract; this Architect report is not automatically writable by Builder.

Explicit denylist: every other path; all frontend, DTO/contract/generated files, controllers/auth/RBAC/preview verification, model definitions outside the named method, extractors/indexing/vector code, provider configuration, migrations, identifiers, historical stored content, tests outside the allowlist, existing docs, Skills, configuration/env/secrets/proxy/pattern files, generated artifacts. No new dependency, reindexing, runtime operations, container/build/deploy, external access, Git staging/commit/amend/integration/push/PR, or lifecycle operation is granted by this report.

| Alternative | Reason not recommended |
| --- | --- |
| Frontend signs or asks a new endpoint to sign | Secrets cannot move to frontend; adds an API/request path and leaves Service API content wrong. |
| Sign in `_prepare_hit_testing_records` | It has serialized dictionaries, not the source segment property; encourages a second signer or object reconstruction. Existing list normalization should retain its responsibility. |
| Add signing to `RetrievalSegments` global serialization | Wider effect on formatter callers and all model dumps; unnecessary for the shared hit-testing response. |
| Persist signed text / extractor or vector changes | Expiring credentials become durable data; requires historical mutation/reindexing and does not solve refresh correctly. Forbidden. |
| Relax preview signature validation | Removes a file-access security boundary. Forbidden. |
| Only insert one line in the normal document branch | Misses existing dump fallbacks and signer query/order requirements; insufficient coverage. |

Risks: signature lifetime limits a long-lived modal; renewed retrieval should refresh credentials, while proactive frontend refresh is not proposed. Existing signer accepts historical embedded references under its current policy; do not broaden accepted hosts/paths or introduce a new signing oracle. Tenant/dataset checks must execute before response conversion. Signing must not trigger new SQL or persist values; tests must assert source-content and input-dictionary preservation. The scoped signer correction also affects tool/context and segment-response users, so related checks below are required.

## 7. Synthetic behavioral regressions

All proposed tests use synthetic UUIDs, `https://docs.example.test` or relative paths, a monkeypatched **synthetic** signing key, controlled clock/nonce, and mocked sessions. Assert parsed URLs and an independently recomputed stdlib HMAC, never source-string/AST assertions or live URL snapshots. No provider/network/storage/database/vector dependency is needed beyond existing disposable unit fixtures.

| Required regression | Observable assertion |
| --- | --- |
| Unsigned preview link in real retrieval conversion | Real `DocumentSegment` + `RetrievalSegments` + dump + base normalization + DTO emits signed `sign_content`; `content` and source object stay byte-identical; correct domain-specific signature verifies synthetically. |
| Existing signature refresh, both endpoints | Old synthetic timestamp/nonce/sign are replaced, each signature key appears once, exactly one URL query delimiter remains, no old suffix; fresh credentials pass independent expected-HMAC comparison. Repeated conversion refreshes without stacking parameters or mutating storage. |
| Historical image-preview and file-preview | Parameterize both routes, relative and synthetic absolute prefixes. Path/ID/prefix remain intact; endpoint's signing domain matches; Markdown delimiters remain intact. |
| Multiple/adjacent Markdown images | Same-family and mixed-family links in both orders, adjacent images, repeated IDs; every destination independently has valid parameters; image count, labels, order and surrounding text remain unchanged. |
| Plain text / no images / empty text | Signed content equals original text; no unrelated text/URL changes or persistence. |
| Empty records and missing IDs/documents | Empty input returns []; absent/empty document-ID fallback still preserves dump/signing behavior; missing document records retain existing skip/warning semantics; lookup remains batched and not per image. Nullable segment fallback uses a narrow test double if needed: the real entity's segment type is not optional, so do not relax it to manufacture that fixture. |
| Collection normalization and DTO | Existing keywords/child_chunks/files null → []; score, tsne/summary defaults, timestamps and document fields preserved; valid signed string survives normalization, and caller input dictionaries are not mutated. Invalid record container/member still fails as before. |
| Shared Console / Service API callers | Exercise real shared service dump/base/DTO chain, then existing Console and Service API handler suites. Verify both use the same result contract and the Service controller registers both hit-testing/retrieve route aliases (read-only source/route check; do not mistake direct undecorated handler tests for token/RBAC validation). |
| Authorization and signature boundaries | Existing permission-denied/cross-tenant/disabled-API cases stay denied before retrieval/signing. Both query models still reject missing fields. Existing FileService rejects invalid signatures before storage; no unsigned-success path. Existing auth/preview suites are related evidence, not proof of historical runtime acceptance. |
| Related shared-signer compatibility | Tool-format references remain intact, including a mixed tools/preview ordering case because the replacement loop is shared. Existing dataset-retrieval/tool/signature suites remain green. |

Optional cases, outside the minimum release fix: uppercase/noncanonical IDs, arbitrary external-host policy, arbitrary query option preservation, fragments, exotic escaped/angle-bracket Markdown and nested-parenthesis destinations, proactive expiry refresh, child-chunk/summary/Q&A inline-image signing. Do not silently expand into these behaviors. A tools-only link is a required compatibility control when the shared replacement loop changes, not a new feature. If any optional format occurs in the later accepted historical chunk and prevents acceptance, return to the coordinator with evidence and a bounded scope proposal.

## 8. Exact future focused commands — NOT_RUN here

Run from repository root in an independently authorized Builder checkout, using its prepared synthetic unit environment; never load rehearsal/production connection values to make unit checks run. TDD: run the smallest new failing cases first, implement, then run these full focused files. Root pytest hooks only start middleware/vector stacks when explicit flags are passed (`api/conftest.py:64–82`); do not use those flags. Existing unit fixtures mock Redis and use disposable in-memory SQLite; they do not authorize historical DB operations.

Required focused unit command:

```bash
uv run --project api --dev pytest -o addopts='' -p no:cacheprovider -p no:benchmark \
  api/tests/unit_tests/services/test_hit_testing_service.py \
  api/tests/unit_tests/models/test_dataset_models.py \
  api/tests/unit_tests/controllers/console/datasets/test_hit_testing_base.py \
  api/tests/unit_tests/controllers/console/datasets/test_hit_testing.py \
  api/tests/unit_tests/controllers/service_api/dataset/test_hit_testing.py
```

Risk-proportionate related regression command:

```bash
uv run --project api --dev pytest -o addopts='' -p no:cacheprovider -p no:benchmark \
  api/tests/unit_tests/core/tools/test_signature.py \
  api/tests/unit_tests/core/tools/test_dataset_retriever_tool.py \
  api/tests/unit_tests/core/rag/retrieval/test_dataset_retrieval.py \
  api/tests/unit_tests/controllers/console/datasets/test_wraps.py \
  api/tests/unit_tests/controllers/service_api/test_wraps.py \
  api/tests/unit_tests/controllers/files/test_image_preview.py \
  api/tests/unit_tests/services/test_file_service.py
```

Focused non-mutating quality commands, also future NOT_RUN:

```bash
uv run --project api --dev ruff check \
  api/services/hit_testing_service.py api/models/dataset.py \
  api/tests/unit_tests/services/test_hit_testing_service.py \
  api/tests/unit_tests/models/test_dataset_models.py \
  api/tests/unit_tests/controllers/console/datasets/test_hit_testing_base.py
uv run --project api --dev ruff format --check \
  api/services/hit_testing_service.py api/models/dataset.py \
  api/tests/unit_tests/services/test_hit_testing_service.py \
  api/tests/unit_tests/models/test_dataset_models.py \
  api/tests/unit_tests/controllers/console/datasets/test_hit_testing_base.py
git diff --check
```

No broad make/test-all or integration/container test invocation is proposed. No functional tests, test collection, code import, browser, Docker, DB, vector, builds, offline checker, deployment, protected audit, or production/gray connection were run during this Architect stage.

## 9. Subsequent gates and human decisions

Sequence, with separate authorization at each action gate:

1. **Independent Plan Review** of this report against immutable source/evidence, especially bounded signer edits, caller coverage, allowlist, tests and upstream disposition.
2. **Authorized Builder**, from the coordinator's accepted exact SHA, with enumerated file ownership and synthetic red → green evidence only.
3. **Independent Code Review**, including real diff, tests, authorization/signature preservation and planned-versus-actual report. Fixer/rereview only for enumerated accepted findings if needed. Commit/amend only after coordinator inspects the dirty diff and explicitly authorizes it.
4. **Authorized local image rebuild/switch**, preserving current connection configuration and mounts. Inspect actual gateway upstream-resolution behavior within that future authorized scope; include nginx reload/restart when needed to avoid stale container-IP resolution, then probe real API/Web through the gateway. This report grants no runtime inspection or switch permission.
5. **Authorized headed Playwright historical-image verification** using existing local migrated actor/dataset/chunk and the visible surface-to-contract navigation. Check card/detail image response and decoded pixels, absence of missing-signature 400, and separate text/download acceptance; do not persist signed response text or replace models/data. Capture redacted evidence tied to accepted source SHA and actual running image IDs.
6. **Authorized offline rebuild/checker**, bind new artifacts to accepted source/image identities and normal allowlist/synthetic-canary gates. Old offline PASS is not acceptance of the repaired artifacts. Load/boot/protected release audit or production guidance remains separately gated as applicable.

**Material open product/human decisions: none** within the accepted image-preview objective; current configuration retention, separate historical PASS statuses and independent password hardening are already decided. Recommendation: accept the bounded plan only after independent Plan Review; do not authorize Builder, runtime actions, or release from this Architect result. Proposed signer corrections are technical recommendations awaiting that review, not expanded runtime authorization.

Next recommended role: Plan Reviewer, source/evidence/report inspection only. Suggested coordinator authorization sentence: “Authorize independent Plan Review of P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md against fb0928bfff62bcdbbd954712573213971f8e3949; no implementation or runtime operations.” This sentence is a handoff recommendation, not a request to create an instance here.

## 10. Planned versus actual work and verification

| Planned | Actual / deviation |
| --- | --- |
| Exact branch/HEAD/clean preflight before work | Matched; no environment repair. |
| Read required instructions and authoritative evidence | Completed. Historical evidence read with URL-redacted relevant observations. |
| Trace every shared conversion caller and official baseline | Completed, including Console, both Service aliases, empty/fallback branches, external exclusion and signer users. |
| Reuse existing signing at minimum shared boundary | Recommended service population plus two method-local signer compatibility corrections because source inspection predicts failures for explicitly required refresh/mixed-image regressions. This is a justified refinement, not implemented code or unrelated URL-policy work. |
| Runtime planning mode where supported | Not available; explicit commentary plan used. |
| Functional/runtime tests remain NOT_RUN | Preserved; only read-only source/Git and report checks performed. |
| Named report only; preserve index; no commit | Only the report was edited. Coordinator correction and read-only recheck establish intent-to-add with no report content staged. Earlier untracked/empty-working-diff claims are superseded. The entry's creator and creation time are unknown; the correction preserves the index exactly. |

Discovery diagnostics: `python` was unavailable; retried historical evidence extraction with `python3`. Initial `rg`/`nl` probes guessed several nonexistent paths (including `api/core/file/helpers.py` and older frontend layouts); corrected by `rg --files` and actual imports. These are recovered discovery errors, not test failures, and are excluded from verification-gate counts. No missing required source/evidence or permission/runtime blocker remains. No prohibited access was used to resolve them.

The coordinator observed intent-to-add rather than an untracked report. Read-only recheck confirms that state. Earlier command captures and the agent's visible action history do not establish who created the index entry or when; they must not be used to deny the current index metadata. The report now distinguishes the observed final state from actions recorded in the session. The substantive implementation and validation plan is unchanged.

### Executed verification records

The earlier official-source parity, baseline and ancestry checks remain the source evidence in sections 1 and 4; they were not rerun during this report-only correction. Earlier final-state labels claiming an untracked report and an empty working-tree diff are withdrawn.

**9 PASS / 0 FAIL** final read-only rechecks (rows below). They check the corrected report and actual Git state, not runtime behavior. Git subprocesses use `GIT_OPTIONAL_LOCKS=0` to avoid optional index refresh writes. Whitespace and final Git checks were repeated after editing.

| Gate | Exact command / check | Result |
| --- | --- | --- |
| Final HEAD | `git rev-parse HEAD` | PASS: exit 0; exact starting SHA below. |
| Exact worktree status | `git status --porcelain=v1` | PASS: exit 0; ` A` report (leading space), intent-to-add. |
| Staged content scope | `git diff --cached --name-only` | PASS: exit 0; empty, no report content staged. |
| Working-tree diff scope | `git diff --name-only` | PASS: exit 0; only the report. |
| Index entry metadata | `git ls-files --stage --debug -- docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md` | PASS: exit 0; mode 100644, stage 0, empty blob, flags 20004000. |
| Working-tree report whitespace | `git diff --check` | PASS: exit 0; no output. Intent-to-add makes the report part of this working-tree diff. |
| Independent report whitespace comparison | `git diff --no-index --check /dev/null docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md` | PASS: exit 1 (added-file difference); no whitespace diagnostics. |
| Final branch/status | `git status --short --branch` | PASS: exit 0; exact output below. |
| Index preserved byte-for-byte | `git rev-parse --git-path index`; `python3` stdlib `hashlib.sha256(Path(index_path).read_bytes()).hexdigest()` before and after correction | PASS: identical SHA-256 `a64f70a8e7ee2338b4f151bf6633b6d28ae864291b97076c8a84e9ff85d7c6d3`. |

The no-index command returns **1 with no diagnostics** because the report differs from `/dev/null`; this is an added-file comparison outcome, not a whitespace error. The original stage's first verification harness incorrectly expected exit 0 and stopped before appending anything; that recovered harness error remains disclosed separately. No functional test failed or ran.

### Unexecuted validation counts

**0 PASS / 0 FAIL / 9 NOT_RUN** validation categories: (1) focused synthetic unit tests, (2) related unit regressions, (3) Ruff code checks, (4) Docker/container/service/gateway operations, (5) headed browser checks, (6) historical DB operations, (7) vector/reindex checks, (8) image/offline build and checker, (9) deployment/production/gray/protected audit. These counts are categories, not claimed pytest case counts; all future unit cases remain unexecuted. No CI-only integration tests ran. This correction performs no code/test or runtime validation.

### Exact final outputs

`git rev-parse HEAD` (exit 0):

```text
fb0928bfff62bcdbbd954712573213971f8e3949
```

`git status --porcelain=v1` (exit 0; first character of the report line is a space):

```text
 A docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md
```

`git diff --cached --name-only` (exit 0): no output.

`git diff --name-only` (exit 0):

```text
docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md
```

`git ls-files --stage --debug -- docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md` (exit 0; the first line separates stage and path with a tab):

```text
100644 e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 0	docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md
  ctime: 0:0
  mtime: 0:0
  dev: 0	ino: 0
  uid: 0	gid: 0
  size: 0	flags: 20004000
```

The empty-blob object ID plus intent-to-add flags explain the empty cached diff and nonempty working-tree diff. **No report content is staged; the report has an index entry and is not untracked.** These facts do not identify who created that entry.

`git diff --check`: exit 0, no output. `git diff --no-index --check /dev/null docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md`: exit 1, no output or whitespace diagnostics.

`git status --short --branch` (exit 0; the report line begins with a space):

```text
## ctyun/replay-116-image-preview-architect-20261006
 A docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md
```

### Observed state versus action history

The visible agent command history contains no `git add -N`, other `git add`, or reset command; that is an action-history observation, not proof that intent-to-add is absent or evidence of the entry's origin. During this correction the index was preserved byte-for-byte and no index-mutating command ran. No commit, amend, push, code/test change, Docker/browser/data/network/deployment/instance/controller operation or production/gray access ran during the correction. No commit/amend/push appears in the original agent action history either. HEAD remains the exact starting SHA. Only this report was edited; the substantive plan remains unchanged. Independent Plan Review remains the next recommended gate; image preview is not closed.

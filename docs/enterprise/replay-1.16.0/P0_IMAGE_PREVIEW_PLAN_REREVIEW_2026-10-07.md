# Embedded-image preview PLAN Rereview — 2026-10-07

**Recommendation: PASS (plan only).** The revision completely assigns the accepted IPPR-01 and IPPR-02 acceptance requirements to implementable future synthetic cases within the unchanged five-file allowlist. Open mandatory plan findings: **P0/P1/P2 = 0/0/0**. No behavior was implemented, no application code was imported, and no test was collected or executed. Image preview remains unfixed and unaccepted at runtime. IPPR-03 remains optional, not an accepted mandatory finding or additional release gate.

## Immutable start, method and revision comparison

- Role: rereviewer; instance/profile: `replay-116-image-preview-plan-rereviewer-20261007` / `codex-sol`.
- Verified start branch: `ctyun/replay-116-image-preview-plan-rereviewer-20261007`.
- Verified start and final HEAD: `525736583b520ec77f97a94dec68de35c337eb81`.
- Parent: `4c2a48e192bc5e05b846e76a913f80e3fd786073`.
- Initial status contained only `## ctyun/replay-116-image-preview-plan-rereviewer-20261007`; clean. The three required commands ran before other work and each exited 0.
- Environment: **Development / historical-data rehearsal**. No historical runtime evidence was reproduced or reopened. The task's exact branch/SHA supersedes older stage checkpoints in `CURRENT_STATE.md` and the Architect/Review history; those records do not describe this worktree's current state.
- Sole authorized write and sole actual changed file: `docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md`.

Investigation plan stated before reads: verify immutable clean start; read required skills/references/AGENTS; compare revision and original Review; trace each accepted criterion through imports, constructors, call signatures, patch ownership, real logic, synthetic I/O, query predicates and spies; audit unchanged paths/commands; write this report and inspect actual Git/whitespace evidence. Actual work followed that plan. No scope deviation, implementation or follow-on agent.

Read `orchestrate-claude-squad` with task-contract and worktree-lifecycle references, `replay-dify-enterprise` with official-first and replay-gates references, and root/API/Web AGENTS. The explicit contract overrides general skill suggestions to fetch, execute regression tests or operate instances. This is PLAN Rereview, not Code Review or a security-policy redesign.

`git diff --stat HEAD^ HEAD` reports **one file, 143 insertions / 4 deletions**: the Architect document. The revision adds its stage preface, changes the existing base-test ownership description and unsupported coverage claims, adds sections 7.1/7.2 and the two-class first-run command/registration checks, and appends Plan Fixer evidence. The original Review and all API source/tests are unchanged across the revision. Its accepted P2 criteria are at Review lines 20–44. The five allowlisted paths are identical to the parent; section 10's historical evidence is preserved verbatim. All existing section 8 bash command blocks remain present unchanged, with no new pytest file path. The new class selectors target the already allowed base suite.

The eight affected source blobs still match local official `1.16.0`. This independently supports the existing **KEEP_MINIMAL_PATCH** disposition: a new bounded repair on the official shared response boundary, not proof of an old enterprise signing patch. The original Review's upstream-history discussion is supporting historical evidence; no fetch or search outside local Git objects occurred.

## Unchanged future Builder ownership

| Exact write path | Authorized future purpose |
| --- | --- |
| `api/services/hit_testing_service.py` | Populate presentation signing at shared record dumping; preserve enrichment, skip/warning, batching, order and raw content. |
| `api/models/dataset.py` | Only `DocumentSegment.get_sign_content` query consumption and replacement order; preserve HMAC/domains and model definitions. |
| `api/tests/unit_tests/services/test_hit_testing_service.py` | Real segment/retrieval conversion and preservation tests with synthetic document lookup. |
| `api/tests/unit_tests/models/test_dataset_models.py` | Signer refresh, URL-boundary and mixed/repeated/adjacent ordering regressions. |
| `api/tests/unit_tests/controllers/console/datasets/test_hit_testing_base.py` | Real dump/normalization/DTO proof and both new security classes. |

One future Builder owns these files and test-local fixtures. No conftest/helper, controller, preview/auth implementation, DTO/generated contract, frontend, extractor, persisted content, vector, migration, configuration or dependency write is added. The existing controller/preview/FileService/wraps and supporting runtime suites remain read-only. A future Builder evidence-report path needs its own contract authorization; it is not implicitly added to these five paths.

## IPPR-01 acceptance matrix

All rows below have **plan disposition: addressed / source-feasible; execution: NOT_RUN**. Owner is `TestUploadPreviewSecurity` in the allowed base test file (Architect lines 155–170), plus the retained signer/conversion matrix at lines 138–151. These are planned assertions, not observed test PASS results.

| Accepted criterion / named future case | Independent source evidence and executable boundary |
| --- | --- |
| Both query models reject each missing field before FileService — `test_each_missing_preview_field_stops_before_file_service` | `image_preview.py:19–26` makes timestamp/nonce/sign required; actual bound handlers validate at `:56,98`, before construction/call at `:62,101`. Six variants can call `ImagePreviewApi().get(UUID(...))` / `FilePreviewApi().get(UUID(...))` under a minimal Flask request context, omit one field, inspect the real Pydantic missing error, and assert the module's FileService spy has zero calls. No unwrapping or canned validation outcome. This proves validation/order, not an executed HTTP 400 response. |
| Generated parameters accepted by real verifier in both domains — `test_generated_preview_parameters_pass_real_verifier` | Real signer at `dataset.py:1010–1046` generates the image/file payload; `file_runtime.py:116–129` independently recalculates it. Both relative and synthetic absolute prefixes are preserved because replacement targets the `/files/…` substring. Parse parameters, assert one of each key, and independently recompute stdlib HMAC; call real `verify_preview_signature(preview_kind=kind, file_id=id, timestamp=..., nonce=..., sign=...)`. Fresh and age-60 success align with the inclusive timeout check. |
| Wrong ID/domain, tampering and expiry rejected — `test_generated_preview_parameters_reject_wrong_id_domain_tampering_and_expiry` | Changing ID, domain, sign, nonce or numeric timestamp without recomputing the signature fails real HMAC comparison (`file_runtime.py:125–128`). Keeping original credentials and moving verification time to generation + 61 fails the real timeout (`:129`). Both domains are assigned; expiry/domain rejection is not inferred from HMAC equality alone. |
| Invalid verification yields 404 with zero SQL/storage — `test_invalid_preview_verification_stops_before_sql_and_storage` | `FileService.get_image_preview:197–214` and `get_file_generator_by_file_id:218–229` verify before constructing a session or calling storage. Forwarding adapters patch the helpers where FileService looks them up, translate `upload_file_id` to `file_id`, fix the method's domain and delegate every field to the real runtime verifier. Invalid variants assert real NotFound code 404 and zero maker/scalar/execute/storage calls. Fresh credentials must reach the maker/scalar lookup; a synthetic absent file can then give 404. Reset spies between negative and positive cases. |
| Real conversion and raw-content preservation; no unsigned fallback | Retained matrix at Architect `:142–151` assigns a real `DocumentSegment` inside real `RetrievalSegments`, real dumping and normalization, and `HitTestingResponse` validation. `RetrievalSegments.segment` is nonoptional (`embedding/retrieval.py:26–34`); signer is an ordinary property/method (`dataset.py:1006–1010`), currently omitted by all dump branches (`hit_testing_service.py:59–101`). Normalization currently inserts null (`hit_testing_base.py:61–68`). Future tests must fail that omission while retaining source content, timestamps, document fields, batching/skip behavior and fresh signatures. |

Imports resolve from source: the four preview classes/models are defined in `controllers.files.image_preview`; the runtime is in `core.app.workflow.file_runtime`; `core.app.file_access/__init__.py` exports `DatabaseFileAccessController` from its `controller.py`; FileService and DocumentSegment are in their stated modules. `core.app.file_access` is a package, not a `file_access.py` file.

Constructor and patch constraints are compatible. Use **`DifyWorkflowFileRuntime(file_access_controller=DatabaseFileAccessController())`**: its argument is keyword-only (`file_runtime.py:39`); the access controller has a default scope-getter (`file_access/controller.py:28–33`), and verification never uses it. Use `FileService(session_factory=MagicMock(spec=sessionmaker))`, supported by its match at `file_service.py:40–47` and the existing fixture at `test_file_service.py:20–34`. No runtime binding or access-controller SQL is needed.

Replace each module's `dify_config` reference with the synthetic namespace, rather than reading or saving a real key. `models.dataset.time` and `file_runtime.time` refer to the same stdlib module: finish generation at 1,700,000,000 before advancing the shared clock; do not assume two independent clock patches. Nonce bytes and timeout are controlled and patches restored per case (Architect `:161`). `_secret_key`, HMAC and verifier stay real. The FileService adapter deliberately isolates graphon's dispatch: it proves real repository verification and FileService order, **not** real dependency runtime-dispatch integration. Existing preview tests mock FileService and existing service tests mock verifier booleans (`test_image_preview.py:34–108`; `test_file_service.py:272–330`); they remain compatibility checks rather than replacement proof.

## IPPR-02 acceptance matrix

All rows have **plan disposition: addressed / source-feasible; execution: NOT_RUN**. Owner is `TestDatasetAuthorizationSecurity` in the same allowed base suite (Architect lines 172–198). The seven named functions have explicit synthetic actors, I/O boundaries, denial spies and reachable success controls.

| Accepted criterion / named future case | Independent source evidence and executable boundary |
| --- | --- |
| Dataset ID and token tenant both constrain lookup; mismatch/absence 404 — `test_dataset_token_binds_dataset_and_token_tenant` | Real decorator at `wraps.py:295–322` validates token then constructs a Select with both `Dataset.id == dataset_id` and `Dataset.tenant_id == api_token.tenant_id`. Always pass a nonempty UUID to the decorated continuation. Capture actual WHERE expression nodes/operators and values; assert both predicates for matching, wrong-tenant, None-tenant and absent-dataset variants. The fake scalar evaluates these predicates against synthetic rows, so missing tenant scoping cannot be disguised by canned None. A None tenant generates `IS NULL`, with a SQL NULL node rather than a tenant bind value; inspect that operator explicitly. Matching row proceeds; exclusions raise 404 before owner lookup/continuation/retrieval/signing. |
| Dataset API disabled 403 — `test_api_disabled_dataset_stops_before_retrieval_and_signing` | Enabled/disabled is checked at `wraps.py:321–322` after a matching row and before owner lookup. Set `Dataset.enable_api=False` explicitly, keep token/tenant/ID valid, and assert Forbidden code 403 with no owner lookup/continuation/retrieval/dump/signer. This exercises dataset-token logic, not app-token disabling. |
| Missing/invalid token 401 — `test_missing_or_invalid_dataset_token_stops_before_retrieval_and_signing` | No header, a no-space malformed header, and a non-Bearer scheme follow `wraps.py:365–373`. Invalid Bearer follows the real cache miss at `:375–386`, forwarding only the single-flight I/O boundary to real `api_token_service.query_token_from_db:282–294`. Capture the actual `ApiToken.token` and `.type == 'dataset'` query, return no row and let real code raise Unauthorized; no dataset/owner lookup or continuation/retrieval/dump/signer. This need not enumerate every malformed-header edge or alter auth behavior. |
| Missing tenant-owner join / Account 401 — `test_missing_tenant_owner_or_account_retains_unauthorized` | After enabled matching dataset, real owner join and Account lookup are at `wraps.py:324–342`. Synthetic execute-result or get returns None at the respective I/O boundary; real code raises 401 before continuation. This is distinct from a missing token tenant rejected by the preceding dataset lookup with 404. |
| Real cross-tenant/private/partial denial 403 — `test_real_dataset_permissions_deny_before_retrieval_and_signing` | Direct shared continuation uses real `get_and_validate_dataset:84–100` and `DatasetService.get_dataset:549–551`; real permission checks at `dataset_service.py:1361–1380` reject tenant mismatch before checking OWNER, reject same-tenant ONLY_ME nonmaintainer/nonowner, and query PARTIAL_TEAM membership for a nonmaintainer/nonowner. Assert both real `DatasetPermission.dataset_id` / `.account_id` predicates and no membership. Real NoPermissionError becomes Forbidden code 403; retrieve/dump/sign stay at zero. Cross-tenant OWNER also denies without membership query. These explicit-actor cases must reach shared validation directly; the token fixture's owner does not manufacture nonowner denials. |
| Shared missing dataset 404 — `test_missing_dataset_stops_before_retrieval_and_signing` | Inject session.get returning None, leave `DatasetService.get_dataset` real, call real shared validation and assert NotFound code 404 (`hit_testing_base.py:91–93`) before retrieve/dump/sign. This tests the shared lookup independently of the decorator's earlier missing-row control. |
| Authorized owner behavior and reachable signing — `test_authorized_owner_reaches_real_signed_conversion` | Tenant check precedes owner bypass (`dataset_service.py:1363–1380`). Same-tenant real Account OWNER succeeds for ONLY_ME and PARTIAL_TEAM even with another maintainer/no membership; no partial-member lookup is needed. Real shared perform calls the retrieve spy (`hit_testing_base.py:120–138`); its provider-isolating side effect invokes real dump over a real segment/retrieval entity, with synthetic document lookup. Delegating dump/sign spies must fire and a signed field survive real normalization/DTO without changing raw content. The matching decorated-token continuation also reaches this success chain. A canned signed return is insufficient. |

Patch ownership is correct: `wraps.py:32` imports ApiTokenCache, record_token_usage and fetch_token_with_single_flight; patch these references in `controllers.service_api.wraps`. On invalid-token cache miss, the forwarded function uses `services.api_token_service.Session` and `db`, so patch those references and its ApiTokenCache.set; real no-row code raises before usage recording. A synthetic Session context manager must yield the session with scalar; no engine or Redis service is used. Cache success can use a synthetic cached object with explicit tenant/scope; if using the existing `CachedApiToken` DTO, supply its required id/app_id/tenant_id/type/token/last_used_at/created_at fields (`api_token_service.py:30–44`). Assert exact Bearer value and `'dataset'` cache scope, not a high-level validation mock.

`@validate_dataset_token` on `def protected(tenant_id, dataset_id)` is feasible: call `protected(dataset_id=<uuid>)` (or one positional UUID), with no supplied tenant argument; the real decorator injects token tenant as the first argument (`wraps.py:285–291,344–349`). Its owner-resolution fake session must support scalar, execute-result `.one_or_none()`, `.get(Account, id)` and **callable `db.session()`** for `:336`. Patch the account's tenant setter to assign `_current_tenant`/role only, and the minimal Flask app login-manager update and signal send as stated. These are session/context boundaries, not permission decisions.

Real Account construction requires name/email and Tenant requires name; assign synthetic IDs after construction because their ID fields are init=False (`account.py:89–121,260–279`). `_current_tenant` and role supply real current_tenant_id/current_role properties (`:159–183`). Dataset is the ordinary mapped Base constructor: explicitly set id/tenant/name/created_by/maintainer/permission/enable_api rather than relying on unflushed database defaults (`dataset.py:166–212`). The shared signatures accept `(session, dataset_id, account, tenant_id)` and `(session, dataset, args, account, tenant_id)` (`hit_testing_base.py:84–89,113–119`). Supplying both actor and tenant keeps real `resolve_account_fallback` on its explicit-actor branch (`libs/login.py:65–83`); this does not prove the production Service handler's implicit login fallback.

To make positive controls reach DTO validation, construct DocumentSegment with tenant_id/dataset_id/document_id/position/content/word_count/tokens/created_by (`dataset.py:919–927`), set its init=False created_at to a synthetic datetime, and construct `RetrievalSegments(segment=segment, score=...)`. Synthetic document rows must supply id/data_source_type/name/doc_type/doc_metadata; the real dump uses `session.scalars(...).all()` and injects created_at/document (`hit_testing_service.py:49–93`). Feed the normalized response to real `HitTestingResponse` validation; perform_hit_testing alone returns a dict and does not invoke the DTO (`hit_testing_base.py:136–139`; `hit_testing_fields.py:27–50,79–90`). All required fields can be supplied locally without model/DTO edits. Nullable/absent-document fallbacks are dump compatibility fixtures, not successful full DTO records.

Spies must remain installed across authorization and the continuation, delegate to originals with correct method binding, and reset per case. Both dumping and retrieve are classmethods, while get_sign_content is an instance method (`hit_testing_service.py:58–59,103–104`; `dataset.py:1010`). Save bound originals or use binding-aware side effects; the plan does not require an incompatible mock signature. Positive controls exercise these same spies, making zero counts on rejected paths meaningful. The shared permission error must be caught around get_and_validate_dataset; it precedes perform_hit_testing's generic exception translation.

## Registration evidence, security scope and remaining acceptance

Read-only alias checks confirm `HitTestingApi(DatasetApiResource, DatasetsHitTestingBase)` registers both paths at `service_api/dataset/hit_testing.py:17–18`; DatasetApiResource inherits its real token decorator at `wraps.py:389–392`. The Service handler uses real shared validation and dumps the same DTO (`hit_testing.py:58–68`). These are **registration/inheritance/source facts**. Planned real decorator/continuation cases prove shared synthetic authorization behavior once executed. Existing unwrapped handlers prove caller/response compatibility. None constitutes authenticated HTTP proof for either alias, Console setup/login/RBAC, or real request-context fallback; those remain separate later acceptance.

No security behavior change is proposed: preserve signed bearer capabilities, mandatory query fields, endpoint HMAC domains, timeout and verifier-before-I/O; preserve tenant predicates, 401/403/404 order, real permissions and owner behavior. Do not add an unsigned fallback, ownership-policy redesign, host policy, auth fix or broader parser. The query-consumption/order correction stays inside the existing signer method. Related callers found in dataset retrieval and both retriever tools retain their existing contracts; the related signer suites and real matrix remain required future controls.

Residual risks remain visible: no execution/dependency-dispatch/authenticated HTTP proof; import/collection readiness depends on the already stated synthetic-only prepared environment; source-defined guards are not demonstrated tests. IPPR-03's concrete environment-preparation suggestion remains optional. Global pytest preparation runs before tests (`api/conftest.py:29–31`; `tests/pytest_dify.py:42–60`), so future authorized execution must honor synthetic provenance and disposable storage without loading real rehearsal/production values. No new fixture/config file or mandatory release gate is introduced here.

Future implementation must still prove red → green for omitted signed conversion and signer refresh/order; existing security checks may already pass and must not be weakened to manufacture red. No broader URL formats, proactive refresh, child-chunk/summary/Q&A signing or password rotation is added. Default-password rotation remains deferred independent hardening. Later image rebuild/switch, gateway checks, **headed** browser historical card/detail rendering, offline artifacts and release acceptance need their separately authorized evidence tied to accepted source and actual image identities. A plan PASS does not fix current image preview or authorize those actions.

## Commands and NOT_RUN accounting

Exact future executable commands remain Architect section 8, lines 207–209 (new classes), 222–227 (five focused files), 233–240 (seven related files), and 246–255 (Ruff check and format --check over the five allowed paths). Flags remain `uv run --project api --dev pytest -o addopts='' -p no:cacheprovider -p no:benchmark`; no middleware/vector startup flags. All 12 unique pytest paths exist; supporting runtime test is an additional read-only citation, not a thirteenth command path. The 11 new named functions are future selectors/parameterized cases, not an executed test count. Existing dev dependencies include pytest and Ruff (`pyproject.toml:125–135`).

**Functional validation: 0 PASS / 0 FAIL / 9 NOT_RUN categories:** focused synthetic units (including the two new classes); related units; Ruff check/format; Docker/services/gateway; headed browser; historical database; vector/reindex; image/offline build/checker; deployment/production/gray/protected audit. No pytest collection, application import, or feasibility demonstration by execution occurred. Source reads (`nl`, `sed`, `rg`, `cat`) are evidence inspection, not test execution.

The read-only audit command below ran before report creation (exit 0); it uses stdlib text/path/Git operations only. It printed five unchanged allowed files, 12 unchanged pytest paths, preserved original bash blocks/history, the sole Architect revision path, report absent before creation, and index SHA-256 `7b4caaa3a4dbf917c48c5a0e2481bbbbcf00687b81b7277e5dc6e7ade6bba8ce`.

```bash
GIT_OPTIONAL_LOCKS=0 python3 - <<'PY'
import hashlib
import re
import subprocess
from pathlib import Path
p = 'docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md'
old = subprocess.check_output(['git', 'show', 'HEAD^:' + p], text=True)
new = Path(p).read_text()
def allowlist(text):
    block = text.split('### Proposed exact write allowlist (future authorization only)', 1)[1].split('Existing Console and Service API controller suites', 1)[0]
    return re.findall(r'^\| `(api/[^`]+)`', block, re.M)
assert allowlist(old) == allowlist(new) and len(allowlist(new)) == 5
assert all(Path(path).is_file() for path in allowlist(new))
commands = new.split('## 8. Exact future focused commands', 1)[1].split('## 9.', 1)[0]
old_commands = old.split('## 8. Exact future focused commands', 1)[1].split('## 9.', 1)[0]
paths = set(re.findall(r'api/tests/unit_tests/[\w/]+\.py', commands))
assert len(paths) == 12 and paths == set(re.findall(r'api/tests/unit_tests/[\w/]+\.py', old_commands))
assert all(Path(path).is_file() for path in paths)
assert all(block in new for block in re.findall(r'```bash\n(.*?)```', old_commands, re.S))
history = new.split('## 10. Planned versus actual work and verification', 1)[1].split('## 11.', 1)[0]
assert history.rstrip() == old.split('## 10. Planned versus actual work and verification', 1)[1].rstrip()
assert subprocess.check_output(['git', 'diff', '--name-only', 'HEAD^', 'HEAD'], text=True).splitlines() == [p]
assert Path('docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md').exists() is False
print('PASS path/scope audit: five unchanged allowed files; 12 unchanged pytest paths; old bash commands preserved; historical section 10 unchanged; sole revision path Architect; report absent before creation')
index = Path(subprocess.check_output(['git', 'rev-parse', '--git-path', 'index'], text=True).strip())
print('index_sha256=' + hashlib.sha256(index.read_bytes()).hexdigest())
PY
```

One recovered discovery diagnostic: `nl -ba api/core/app/file_access.py` reported a nonexistent file. `rg --files api/core/app/file_access` and its package exports established the actual package/controller location. No application import or test was used to resolve it; this is not a functional failure. Long source/diff output was reread in narrower ranges where necessary.

## Final read-only evidence and actual Git state

### Earlier snapshots versus current observation

The earlier turn recorded **20 PASS / 0 FAIL evidence gates**: three original start checks, one source/path/command audit, fifteen command checks and one index-snapshot equality check. At those recorded snapshots, status was `??`, both cached and tracked working diffs were empty, report index metadata was empty, and the pre-write/end snapshots both hashed to `7b4caaa3a4dbf917c48c5a0e2481bbbbcf00687b81b7277e5dc6e7ade6bba8ce`. Those observations describe the earlier captures only. Their labels as the report's final/current Git state are superseded by the correction below; the index equality at those snapshots does **not** establish preservation across the whole stage.

The coordinator subsequently observed an intent-to-add entry. This correction independently confirms it: status ` A` (leading space), empty cached diff, working diff containing this report, and empty-blob stage-0 index metadata with flags `20004000`. The current pre-correction index hash is `db534012e3f6403385435b42eede5a1635a47e6e7f5b9ef779a347410927ac0d`, which differs from the earlier hash. The entry's creator and creation time are unknown; no attribution is made. No index repair, staging or removal was attempted.

Original source/path/alias/baseline checks above remain earlier inspection evidence; they were not rerun for this Git-reporting-only correction. The substantive review, recommendation, acceptance matrices and all text before this final-evidence section are unchanged. The preserved prefix hashes to SHA-256 `11169bc57320ee34199b14d7f1ecdf8a2e69535d0ab7af6f28304f875347229c` before and after correction.

### Current correction checks

**13 PASS / 0 FAIL correction evidence gates**: eleven final commands below, one before/after correction index equality check and one substantive-prefix equality check. These are document/Git evidence, not functional tests or a cumulative rerun of the earlier 20 gates. Expected no-index exit 1 is a successful whitespace inspection, not an exit-0 command. Checks were repeated after completing this section. All correction Git commands use `GIT_OPTIONAL_LOCKS=0` to suppress optional index refresh writes. Functional validation remains **0 PASS / 0 FAIL / 9 NOT_RUN categories**, unchanged.

| Count | Exact command/check | Actual result |
| --- | --- | --- |
| 1 | `git branch --show-current` | Exit 0, expected Rereviewer branch. |
| 1 | `git rev-parse HEAD` | Exit 0, exact start SHA. |
| 1 | `git diff --cached --name-only` | Exit 0, empty; no staged paths. |
| 1 | `git diff --cached` | Exit 0, empty; no staged content. |
| 1 | `git diff --name-only` | Exit 0, only this Rereview report. |
| 1 | `git diff --stat` | Exit 0, only this report as an added file; full report content is in the working diff. |
| 1 | `git diff` | Exit 0, added-file diff for this report only; no code/test/data or other path change. |
| 1 | `git ls-files --stage --debug -- docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md` | Exit 0; empty blob `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`, stage 0, flags `20004000`; exact metadata below. |
| 1 | `git diff --check` | Exit 0, no output or whitespace diagnostics; the intent-to-add report is included in this working diff. |
| 1 | `git diff --no-index --check /dev/null docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md` | Exit 1, empty stdout/stderr, no whitespace diagnostics; expected added-file difference. |
| 1 | `git status --short --branch` | Exit 0; exact output below, report intent-to-add with no content staged. |
| 1 | `git rev-parse --git-path index`, then stdlib `hashlib.sha256(Path(index_path).read_bytes()).hexdigest()` compared to the pre-correction snapshot | Exit 0; identical SHA-256 `db534012e3f6403385435b42eede5a1635a47e6e7f5b9ef779a347410927ac0d` across the correction snapshots only. |
| 1 | Stdlib SHA-256 of `Path(report).read_text().split('## Final read-only evidence and actual Git state', 1)[0].encode()` | Exit 0; prefix equals the pre-correction hash above, preserving the substantive review and matrices. |

Exact earlier alias commands (not rerun during this correction):

```bash
rg -n 'service_api_ns.route|class HitTestingApi' api/controllers/service_api/dataset/hit_testing.py
rg -n 'class DatasetApiResource|method_decorators = \[validate_dataset_token\]' api/controllers/service_api/wraps.py
```

Actual final status (report line begins with a space):

```text
## ctyun/replay-116-image-preview-plan-rereviewer-20261007
 A docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md
```

Exact final index metadata (first line has a tab between stage and path):

```text
100644 e69de29bb2d1d6434b8b29ae775ad8c2e48c5391 0	docs/enterprise/replay-1.16.0/P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md
  ctime: 0:0
  mtime: 0:0
  dev: 0	ino: 0
  uid: 0	gid: 0
  size: 0	flags: 20004000
```

The cached diff is empty: **no report content is staged**. The working diff lists and contains the full added report because the index has an empty-blob intent-to-add entry. The report is **intent-to-add, not currently untracked**. Earlier Architect/Review intent-to-add observations remain historical and are separate from this current entry. Current metadata and differing earlier/current hashes do not establish who created it or when. Index preservation is established only across the matched pre-correction/final-correction snapshots, not the whole stage.

No git add (including -N), index-mutating command, commit, amend, push, merge, rebase, reset, checkout, cherry-pick, PR, follow-on agent, lifecycle/instance/controller action, network, Docker, browser, database/service, config/secret or production/gray operation occurred. Stop after this report and final evidence. Coordinator disposition/authorization remains outside this instance.

# Dify Enterprise 1.16.0 Replay B5 Contract Fix — Independent Rereview

## RECOVERY

- Branch/HEAD: `ctyun/replay-116-b5-contract-rereviewer` / `6b6305f2cdeb436c4736978a02240e99ae6c8e5f`; exact match.
- Initial status/porcelain: clean; all four ancestor checks exit 0.
- Verifier: `OK branch=ctyun/replay-116-b5-contract-rereviewer head=6b6305f2cdeb436c4736978a02240e99ae6c8e5f clean=true`.
- Initial lock hashes: `api/uv.lock` `2903bfd7fb58511054a0d7111717eb8be92eac627f80862517f09fe69eeffed2`; `pnpm-lock.yaml` `62f3e0f3639dd80d1d058cae38a3dca53fc5b626fb2e6bec446a0aa397148ee7`.
- Initial index hash: `257b24b71a7e4f4a41f8a497b22c6440f4d70056d690952af3605abc322cc944`.
- Human gate accepted the sole report's temporary intent-to-add state; execution baseline was `d935f2316bfd85a4f6bc7c13903d7755d5690be17980b89103c1db3fa5fbea3d`.

## SOURCES_READ

Read completely in required order: `CURRENT_STATE.md`, `B5_IMPLEMENTATION_PLAN.md`, `B5_IMPLEMENTATION_PLAN_REREVIEW.md`, `B4_FINAL_REREVIEW.md`, `B5_CONTRACT_FIX_REVIEW.md`, `api/AGENTS.md`, and `api/controllers/API_SCHEMA_GUIDE.md`. Independently inspected the final controllers/tests/generated contracts, exact diffs/history, OpenAPI, auth/error helpers, platform-admin service reachability, marketplace service/domain errors, official generator configuration, router nesting, and generated TypeScript/Zod.

## REVIEW_RANGES

- Implementation `55cfe8ec165f3799543fabbe2d777d332cf1de0e..7237af7c759f433fac9e2e2c1a1b63d816134a24`: exact eight files; `255 insertions(+), 0 deletions`.
- Review report `7237af7c759f433fac9e2e2c1a1b63d816134a24..ccc96aef5c38e4605ef927d67f500eb3543e3c8f`: only `B5_CONTRACT_FIX_REVIEW.md`, 237 insertions.
- Ruff Fix `ccc96aef5c38e4605ef927d67f500eb3543e3c8f..6b6305f2cdeb436c4736978a02240e99ae6c8e5f`: exact three files; `162 insertions(+), 83 deletions(-)`.
- Integrated range: eight product/contract files plus Review report; `649 insertions(+), 78 deletions(-)`.
- Name-status, stat, numstat, full-diff inspection, and diff-check completed; diff-check exit 0 for every range.

## SCOPE

- Product/code scope is exactly the eight-file allowlist.
- Review report was added only by `ccc96aef5c38e4605ef927d67f500eb3543e3c8f` and not modified by Ruff Fix.
- Ruff Fix parent, subject, exact three files, and expected stat all match.
- `api/controllers/console/platform_admin.py` has an empty Ruff-Fix range diff.
- No Web, service/state-machine, schema/model, migration, dependency, manifest, lockfile, handwritten response type, direct fetch, or frontend workaround change exists.

## B3_CONTRACT_EVIDENCE

OpenAPI operation IDs/methods/paths/success/error matrices independently match:

1. status: 200; 401.
2. workspace list: 200; 400/401/403/409.
3. workspace detail: 200; 401/403/404/409.
4. workspace patch: 200; 400/401/403/404/409.
5. members: 200; 401/403/404/409.
6. invitations: 201; 400/401/403/404/409/503.
7. role patch: 200; 400/401/403/404/409/503.

`UnauthorizedResponse` requires exactly `code,message`; `PlatformAdminErrorResponse` requires exactly `code,message,status`. Generated TypeScript error maps exactly match every row. Generated Zod defines the same two-field unauthorized and three-field domain shapes. Controller decorators, login unauthorized handler, validation, platform-admin/current-tenant guards, workspace/member lookups, conflicts, and RBAC fail-closed paths establish real reachability. Router operation nesting and success types did not regress.

## B4_422_EVIDENCE

`MarketplaceReviewApi.post` calls `approve_asset`; approval reaches `_validate_dsl_no_secrets`, `_extract_and_normalize_dependencies`, metadata/icon portability checks, and can raise `SnapshotContainsSecret`, `NonportableResourceReference`, or `PrivatePluginDependency`, each status 422. Review OpenAPI and generated TypeScript expose exactly `400/401/403/404/409/422`; 503 is absent. Review 401 uses `UnauthorizedResponse`; every domain status uses `MarketplaceErrorResponse {code,message,status}`. Zod schemas match those body shapes.

## B5CR_02_DISPOSITION

- Exact four-file Ruff check: exit 0, `All checks passed!`.
- Exact four-file Ruff format check: exit 0, `4 files already formatted`.
- All eight prior diagnostics and three formatter findings are closed.
- Ruff Fix touches only the expected three files; platform-admin controller is unchanged.
- Full diff inspection and regression confirm formatting/semantics-preserving lint repair only; no service, state-machine, exception, schema, migration, frontend, or generated-contract behavior changed.

## PROCESS_DEVIATIONS

1. Original 179 generated empty-blob/intent-to-add entries: attribution remains unproven; final generated content and index are clean after the explicitly authorized normalization workflow.
2. Test history retained accurately: first pre-generation run `86 passed, 11 setup errors, 2 warnings`; later runs `97 passed, 2 warnings`; this rereview ran generation first and then `97 passed, 2 warnings`.
3. Hook deviation retained accurately: prohibited full-API Ruff changed five out-of-allowlist files; those were restored and none is in Ruff Fix.
4. Sole report temporary intent-to-add state was explicitly accepted; cached report content remained empty.
5. Each official generator pass produced exactly 179 symmetric `DA` entries with identical cached/unstaged path sets and `git diff HEAD --quiet -- packages/contracts/generated/api` exit 0. The coordinator pre-authorized exact `git restore --staged packages/contracts/generated/api`; each normalization changed no worktree content. This is accepted as an index-tracking process deviation, not a contracts content difference.
6. First normalization briefly encountered sandbox/index-lock failures; the exact authorized command succeeded on retry after the transient lock was absent. No lock was manually removed.

## GENERATION

- Pass 1: official proxy-cleared, isolated-UV-cache, Node-22 command exit 0. Exactly 179 symmetric `DA` paths; HEAD-content exit 0. Authorized normalization succeeded. Post-normalization cached/unstaged generated counts 0/0; new index hash `480889b52591baae3f1f16e119943950b872ae8a65ac1f1609e42aff161813fe`.
- Pass 2: same command exit 0. Exactly 179 symmetric `DA` paths; cached and unstaged sorted path-set SHA-256 both `ec7ea65bc06c4a4292b485d0afa5be06a47fba207b0a49d4b7be01df47e2afc1`; HEAD-content exit 0. Authorized normalization succeeded. Post-normalization cached/unstaged generated diffs empty; index baseline `054fa61c6b51b858e20603a18d03fa96cecddeefe6bc7867a8b02c4f1bde7f91`.
- Deterministic generated content: PASS.

## COMMANDS

- Frozen Python sync: first sandbox attempt exit 1 on network; exact approved retry exit 0, 513 locked packages.
- Frozen filtered pnpm install: first sandbox attempt exit 1 on network; exact approved retry exit 0, resolution skipped, 507 packages.
- Generator commands: exit 0 twice.
- Targeted Ruff check/format: exit 0/0.
- Focused pytest: exit 0.
- Nine-file pytest: exit 0.
- Contracts test/type-check: exit 0/0.
- OpenAPI `jq`, generated TypeScript/Zod `rg/sed`, service/error/auth reachability, scope, and Git evidence commands: exit 0 except one malformed exploratory `jq` query (exit 5), immediately replaced by a correct query that exited 0.

## VALIDATION

- Focused controllers/contracts: `97 passed, 2 warnings in 9.72s`.
- Nine-file B3/B4 regression: `403 passed, 165 warnings in 32.98s`.
- Contracts: one test file, four tests passed.
- Contracts type-check: `tsc` exit 0.
- Targeted Ruff and format: PASS.
- Two-generation content determinism: PASS with accepted symmetric index normalization.

## FINDINGS

Open P0/P1/P2 findings: `0/0/0`.

`B5CRR-01` is withdrawn as a finding and recorded as the explicitly accepted generation/index-tracking process deviation. There is no generated contracts content difference.

## NOT_RUN

Frontend unit/browser/E2E, database upgrade/downgrade/stamp/runtime, PostgreSQL concurrency, vector, Docker/container/image/volume, offline, production upgrade/rollback, and B5 runtime validation remain NOT_RUN and outside this gate. Full-API Ruff, Ruff auto-fix, commit, amend, push, and B5 Builder were not run.

## AUDIT_EVIDENCE

- Lockfiles unchanged.
- Authorized temporary UV/pnpm roots and `api/.venv` removed; cleanup exit 0.
- No external audit log retained.
- Only this report is retained as the permitted write.

## GIT

- Final lock hashes equal initial hashes.
- Final index baseline after pass-2 normalization: `054fa61c6b51b858e20603a18d03fa96cecddeefe6bc7867a8b02c4f1bde7f91`.
- Generated cached/unstaged diffs empty; generated content equals HEAD.
- Final expected status: branch plus sole report ` A`; report cached content empty.
- Commit: NOT_COMMITTED. Amend: NOT_AMENDED. Push: NO_PUSH.

## GATE

```text
PASS
CONTRACT_FIX_ACCEPTED=yes
B5_CONTRACT_GATE_CLOSED_PENDING_REPORT_INTEGRATION
B5_BUILDER_NOT_AUTHORIZED
```

B5 remains unauthorized until coordinator review, report integration, and fast-forward.

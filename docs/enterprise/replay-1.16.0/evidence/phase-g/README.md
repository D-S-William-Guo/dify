# Phase G Evidence — Runtime Acceptance Matrix

Validator: `replay-116-b8-phase-g-validator`
Head: `8e088188a2b685b86cb776bdc978f2f5f2ead0e9`
Base: `codex/enterprise-candidate-1.16.0-20260718`
Date: 2026-08-12 (Asia/Shanghai)
Stack: isolated project `dify-b8-phase-g`, port `127.0.0.1:18080` only.

## Decision sheet options (confirmed 2026-08-12)

- G1 = A full Phase G | G2 = A migrated production copy as primary DB + empty-DB `/install`
  quick check | G3 = A Aliyun/Tongyi carried by migrated DB; **user supplied OpenRouter key**
  (migrated Tongyi creds undecryptable — tenant RSA keys live in forbidden production storage) |
  G4 = A Playwright | G5 = A synthetic pattern | G7 = A single instance.

## Summary

| Area | Result |
| --- | --- |
| Identity/env checks | PASS (branch/HEAD/clean; images; config -q; port) |
| DB: dump/restore/upgrade | PASS (head `b416e5c4e702`, counts match production baseline) |
| Install/login/activation/invite/public | PASS (upgrade DB no /install; login; register 403; invite+activate) |
| Platform-admin 7 routes + boundaries | PASS (7 routes; non-admin 403 all; no header bypass; owner 409; RBAC 503) |
| Marketplace | **FAIL** — release-blocking schema/type mismatch (varchar vs uuid) |
| Agent App Beta (roster/skills/files/publish/chat) | PASS (OpenRouter LLM end-to-end) |
| Agent App Beta (knowledge) | **FAIL** — release-blocking compositor layer mismatch |
| Agent agent_backend stop | PASS w/ minor deviation (400 not 503; no crash; recovery OK) |
| Agent Landlock | PASS (out-of-workspace write + /etc/passwd read denied) |
| Agent dual-secret tokens | PASS (cross-deployment JWE decode rejected) |
| Agent timeout/cancel | PASS (stop 200; terminated; retry OK) |
| Workflow | PASS (create/sync/run start→end succeeded) |
| WebSocket/socket.io | PASS (handshake + websocket upgrade via api_websocket) |
| Plugin/Dataset/Vector + hit-testing | PASS (bge-m3 embed, Weaviate class, hit score 0.7067) |
| Secret runtime scan | PASS (real key no-hit; dev defaults only in compose config) |
| Browser/E2E 5 groups | PASS (login/nav, roster, error-state, keyboard focus, responsive) |
| Empty-DB /install | PASS (auto-migrate → /install → setup admin → finished) |

## Release-blocking findings

1. **Marketplace schema/type mismatch** (`marketplace.log`): B4 migration created
   `enterprise_marketplace_assets` / `_snapshots` ID/FK columns as `VARCHAR(36)` but the ORM
   model uses `StringUUID` (PG `uuid`). Every query filtering on those columns fails
   `operator does not exist: character varying = uuid`. Breaks submit/review/copy/unlist on
   both upgraded and fresh PostgreSQL. Model: `api/models/model.py:2847-2848`; migration:
   `api/migrations/versions/2026_07_21_1400-b416e5c4e702...` lines 60-71.
2. **Agent knowledge binding breaks conversation** (`agent-knowledge.log`): binding a
   knowledge set to a roster Agent then chatting fails with
   `CompositorSessionSnapshot layer names must match ... [.., llm, knowledge], got [.., llm]`.
   Same chat without knowledge succeeds. Release-blocking for VALIDATION_PLAN Agent knowledge
   scenario.

## Deviations from plan

1. Migrated Aliyun/Tongyi provider creds could not be decrypted (tenant RSA private keys live
   in `docker/volumes/**`, forbidden). Per G3 stop-condition, user supplied an OpenRouter key;
   openrouter plugin `0.1.3` and ollama `1.0.0` installed fresh from marketplace
   (0.1.2/0.2.9 runtime files were in forbidden production plugin storage).
2. Plugin daemon `0.6.3-local` returns 400/404 for `/plugin/current/...` model-schema paths
   (UUID parse of sentinel `current`) and for `validate_provider_credentials` when a stale
   installation (0.1.2) has no runtime; removed stale installs, installed 0.1.3.
3. agent_backend stop returns 400 `completion_request_error` with raw transport message
   instead of stable 503 (no secrets leaked; API/Web did not crash; recovery verified).
4. Inline-agent-in-workflow via API-only was NOT_RUN (composer node binding requires the UI
   authoring path); roster binding + composer save verified at the Agent level.
5. Migrated dataset vector class alignment NOT_RUN (production Weaviate data is in forbidden
   `docker/volumes/**`); new dataset alignment + hit-testing PASS.
6. plugin_daemon remote-debugging host port (5003) removed per "only port 18080" guardrail;
   plugin remote-debug install NOT_RUN.

## Environment notes

- OpenRouter LLM: `openrouter/auto` (default), validated + 2 agent conversations (exact
  answers). Embedding: local Ollama `bge-m3` (1024-dim). Reranker: not configured (per user).
- Full stack: db_postgres(empty, unused), redis, weaviate, sandbox, plugin_daemon,
  agent_backend, local_sandbox, ssrf_proxy, api, worker, worker_beat, api_websocket, web, nginx.
- Primary DB at `b416e5c4e702`; counts matched production baseline before runtime tests.

## Evidence files

- `PLAN.md`, `README.md` (this), `setup.log` (DB prep; see below)
- `install-login.log`, `platform-admin.log`, `marketplace.log`
- `agent-conversation.log`, `agent-knowledge.log`, `agent-backend-stop.log`,
  `agent-landlock.log`, `agent-dual-secret.log`, `agent-timeout-cancel.log`
- `workflow-hitl-websocket.log`
- `plugin-dataset-vector.log`
- `secret-scan.log`
- `browser-e2e.log` + `browser-screenshots/**`
- `empty-db-install.log`
- `teardown.log`

## Required-verification commands (all PASS)

- `git branch --show-current` / `git rev-parse HEAD` / `git status --short --branch`
- `git merge-base --is-ancestor b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4 HEAD`
- `docker exec docker-db_postgres-1 pg_dump --version` -> 15.17
- `docker compose -p dify-b8-phase-g ... config -q` -> exit 0
- `git diff --check` -> clean
- `ss -ltn | rg :18080` -> listening (isolated)

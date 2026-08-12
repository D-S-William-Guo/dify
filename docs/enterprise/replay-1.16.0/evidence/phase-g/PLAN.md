# Phase G Execution Plan (Option G-A: full runtime acceptance)

Validator: `replay-116-b8-phase-g-validator`
Start head: `8e088188a2b685b86cb776bdc978f2f5f2ead0e9`
Base: `codex/enterprise-candidate-1.16.0-20260718`
Date: 2026-08-12 (Asia/Shanghai)

Decision sheet: `/tmp/replay-116-phase-g-decision-sheet.md`:
- G1 = A full Phase G (all scenarios + browser 5 groups)
- G2 = A migrated production copy as primary DB + one empty-DB `/install` quick check
- G3 = A reuse Aliyun/Tongyi provider carried by migrated DB; OpenRouter key only if
  user supplies it after quota/credential failure (STOP + ask, never invent)
- G4 = A Playwright browser automation
- G5 = A synthetic secret-pattern scan (0600 pattern file under /tmp, boolean output only)
- G7 = A single instance
- Port: 18080 only

## Guardrails

- Never touch the running 1.15 stack (`docker-*` project, 12 containers) or its volumes.
- Never access/modify `docker/volumes/**` in this repo or
  `/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/docker/volumes/**`.
- Host port bindings: ONLY `127.0.0.1:18080`. Ports 80/443/5003 in use by the 1.15 stack
  must never be bound by this project (plugin_daemon debug port 5003 also removed).
- No modifications to compose/source under `docker/`, `api/`, `web/`, `dify-agent/`,
  `packages/`. Only `docs/enterprise/replay-1.16.0/evidence/phase-g/**` and
  `DECISION_RISK_LEDGER.md` are written.
- No commit/amend/push.
- Never print provider keys, secrets, endpoints, emails, or plaintext business IDs.
- If Aliyun/Tongyi provider fails (quota/credential), STOP and ask user for OpenRouter key.

## Stack / images

- Project `dify-b8-phase-g`; workdir `<repo>/docker`.
- Config files: `docker/docker-compose.yaml`, `docker/docker-compose.enterprise.yaml`,
  `/tmp/dify-b8-phase-g.override.yaml` (never committed).
- Images: `dify-api-enterprise:1.16.0-enterprise` = `sha256:cb4d99a45ac1...`,
  `dify-web-enterprise:1.16.0-enterprise` = `sha256:0ae50b4527b8...`,
  official `langgenius/dify-agent-backend:1.16.0`, `langgenius/dify-agent-local-sandbox:1.16.0`,
  plus base images already present (postgres:15-alpine, redis:6-alpine,
  weaviate:1.27.0, dify-sandbox:0.2.15, dify-plugin-daemon:0.6.3-local, ubuntu/squid, nginx:latest).
- Temp `docker/.env` = copy of `docker/.env.example` (gitignored), removed after teardown.
- Override maps every `./volumes/**` bind to a temp named volume `dify-b8-phase-g-*`;
  nginx ports overridden to `127.0.0.1:18080:80` only; plugin_daemon host port removed;
  sandbox `/conf` + `/dependencies` binds replaced with temp bind dirs / named volume
  (sandbox image ships a default `/conf/config.yaml`, so a temp config dir under /tmp works).

## Databases

### Primary DB (migrated production copy)
1. Online read-only `pg_dump` of `docker-db_postgres-1` → `/tmp/replay-116-phase-g/prod-pg15.dump`.
   - `docker exec docker-db_postgres-1 pg_dump -U postgres -d dify --format=custom --no-owner --no-acl --lock-wait-timeout=10`
2. Restore into isolated PG15 container `dify-b8-phase-g-db-primary` (named volume
   `dify-b8-phase-g-db-primary`, host port 127.0.0.1:15432 only, for the migration step).
3. Upgrade to enterprise head `b416e5c4e702` with `MODE=migration` one-shot
   `dify-api-enterprise:1.16.0-enterprise` container (`flask upgrade-db`), env `DB_HOST=127.0.0.1
   DB_PORT=15432 DB_USERNAME=postgres DB_PASSWORD=<isolated> DB_DATABASE=dify MIGRATION_ENABLED=true`.
4. Verify `alembic_version = b416e5c4e702` and counts match production baseline
   (accounts/tenants/tenant_account_joins/apps/workflows/datasets/documents/segments/conversations/marketplace).
5. api/worker/etc point at this DB via override env (`DB_HOST=127.0.0.1`, `DB_PORT=15432`) —
   no compose `db_postgres` service needed for the primary stack (its bind `./volumes/db/data`
   would be forbidden).

### Secondary empty PG15 DB
- Isolated PG15 container `dify-b8-phase-g-db-empty` (named volume `dify-b8-phase-g-db-empty`,
  host port 127.0.0.1:15433 only). Empty. Run `/install` flow once against a small api/web
  stack pointed at this DB, capture evidence, teardown.

## Scenario order

1. Environment + identity checks (branch/HEAD/clean, images, config -q, port 18080 free).
2. Primary DB dump + restore + upgrade + count verification.
3. Full stack up (primary DB): api, worker, worker_beat, api_websocket, web, nginx,
   agent_backend, local_sandbox, plugin_daemon, sandbox, ssrf_proxy, redis, weaviate.
4. Install/login/activation/invite/public routes (upgrade DB must NOT show /install).
5. Platform-admin 7 routes + permission boundaries (non-admin 403).
6. Marketplace submit/review/copy/unlist + secret-free snapshot.
7. Agent App Beta 12 scenarios (roster/skills/files/knowledge/tools/publish/conversation/
   workflow-ref/inline/agent_backend-stop/timeout-reconnect-cancel/Landlock/dual-secret).
8. Workflow/HITL/WebSocket collaboration.
9. Plugin/Dataset/Vector + hit testing.
10. Secret runtime scan (synthetic 0600 pattern; boolean output only).
11. Browser/E2E 5 groups with Playwright screenshots.
12. Empty-DB `/install` quick check (secondary DB, mini stack).
13. Teardown (`docker compose -p dify-b8-phase-g down -v`, remove /tmp files, verify no leftovers).
14. Evidence write-up + `DECISION_RISK_LEDGER.md` update.

## Evidence files

- `PLAN.md` (this), `README.md` (matrix results)
- `setup.log` (env checks + DB dump/restore/upgrade + counts)
- `install-login.log`, `platform-admin.log`, `marketplace.log`
- `agent-*.log` + `agent-screenshots/**`
- `workflow-hitl-websocket.log`
- `plugin-dataset-vector.log`
- `secret-scan.log` (redacted boolean results)
- `browser-e2e.log` + `browser-screenshots/**`
- `empty-db-install.log` + screenshots
- `teardown.log`

## NOT_RUN (honest, anticipated)

- Anything requiring a second host port (remote plugin debugging 5003) — recorded as NOT_RUN.
- MySQL rows — out of scope for local release blocker.
- Agent scenarios needing a live external model if Aliyun/Tongyi quota fails — STOP + ask user.

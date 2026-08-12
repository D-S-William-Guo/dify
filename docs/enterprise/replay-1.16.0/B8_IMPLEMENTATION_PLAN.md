# Dify Enterprise 1.16.0 Replay B8 实施计划

## 0. 结论

当前结论：**PLAN_READY**（本文件是供独立 Review 的实施计划，不是 Builder 授权）。

B8 是 B7 之后的最终发布验证门禁（ARCHITECT_HANDOFF §4 B8、§7 第 9 条）。本计划只定义：
默认只读的 vector consistency checker 及其 fixtures/tests、只读执行与 no-repair 边界；
`docs/enterprise/replay-1.16.0/evidence/**` 批准证据布局；validation evidence completeness
check；B8 Builder 的精确 allowlist/denylist、验证命令、串行门禁与报告 schema。

已确认的关键决定：

1. `B8_READONLY_DEFAULT`：vector checker 默认且唯一只读。绝不包含 `--repair`/修复路径；
   repair 只作为需要协调者单独审批的独立任务描述（PATCH_DECISION_MATRIX E13
   “先实现 read-only 检查；repair 必须单独审批/任务”；ARCHITECT_HANDOFF §4 B8
   “repair：独立任务，需显式批准；不得与只读检查一起默认执行”）。本计划不设计 repair
   实现，只写边界。
2. `B8_CHECKER_NO_PS1`：vector checker 只交付 `scripts/check-enterprise-vector-indexes.sh`。
   旧 1.15 链对应脚本只有 `.sh`（`dify-enterprise-1.15.0/scripts/check-enterprise-vector-indexes.sh`，
   只读证据，无 `.ps1` 对照），因此 Windows parity 不成立，默认不新增 `.ps1`。若后续运维
   必须维护 Windows 路径，Builder 必须停下请求扩展 allowlist，不得默认省掉后声称等价。
3. `B8_EVIDENCE_BUILDER_ONLY`：`docs/enterprise/replay-1.16.0/evidence/**` 只允许在后续
   协调者授权的 B8 Builder/Validator 写入；本 Architect 不写。缺失证据一律记 `NOT_RUN`，
   不得以 PASS 冒充。
4. `B8_MISSING_EVIDENCE_IS_NOT_RUN`：任何门禁缺失必需证据即 `NOT_RUN`（VALIDATION_PLAN §5
   “不得用口头‘已验证’替代可复现证据”），仅当证据完整且通过才给 PASS。
5. `B8_PHASE_DFGH_NOT_RUN`：Phase D（migration/数据库升级矩阵）、Phase F（构建/容器身份）、
   Phase G（运行验收）、Phase H（离线目标 smoke）的真实运行操作默认 `NOT_RUN` for B8
   Builder，必须由协调者逐项另行授权（VALIDATION_PLAN Phase D/F/G/H；B7 同款门禁
   `B7_PHASE_FG_NOT_RUN`）。静态/只读替代证据不得冒充运行证据。
6. `B8_COMPLETENESS_CHECK`：evidence completeness check 是**条件性/描述性交付**。脚本
   `scripts/ci/check-enterprise-validation-evidence.sh`/`-tests.sh` **当前未被授权**：不在
   ARCHITECT_HANDOFF §5 B8 allowlist（§5 B8 允许写路径仅为
   `scripts/check-enterprise-vector-indexes.*`、对应 fixtures/tests、经批准的
   `docs/enterprise/replay-1.16.0/evidence/**`）。“数据库/runtime/offline evidence completeness
   check”只是 §5 验收命令（验收标准），不是写权限授权。B8 Builder 写出这两个脚本前必须获得
   协调者**显式 allowlist 扩展审批**；本计划不假定审批已存在。

当前门禁：

```text
B8_BUILDER_NOT_AUTHORIZED
B8_PHASE_DFGH_NOT_AUTHORIZED（Phase D/F/G/H 需协调者逐项另行批准）
```

## 1. Current-state recovery

### 1.1 强制起点

| 项目 | expected | actual | 结果 |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b8-architect` | `ctyun/replay-116-b8-architect` | PASS |
| HEAD | `b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4` | `b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4` | PASS |
| porcelain | empty | empty | PASS |
| B7 链已合并 | `b8dd2b3e3c`（B7 Rereview，HEAD）、`93ab820b48`（B7 Code Review）、`bb86a5e8aa`（B7 Fixer）、`28f9f72e7d`（B7 code feat）均在 HEAD | `git log` 确认 | PASS |
| B6 overlay 存在 | `docker/docker-compose.enterprise.yaml` 74 行 | 74 行 | PASS |
| 旧 1.15 vector checker | 只读证据 `dify-enterprise-1.15.0/scripts/check-enterprise-vector-indexes.sh` | 存在，189 行，含 `--repair` | PASS（仅证据；repair 不移植） |
| 本仓库 vector checker | `scripts/check-enterprise-vector-indexes.*` 不存在 | `ls` 输出 no-such-file | PASS（B8 待创建） |
| evidence 目录 | `docs/enterprise/replay-1.16.0/evidence` 不存在 | 不存在 | PASS（B8 Builder 才写） |
| 迁移头文件 | `b416e5c4e702`/`a71e16c0de01`/三个历史 revision 文件存在 | 5 个文件均存在 | PASS |
| B7 离线链 | 4 脚本 + check/check-tests + fixtures 存在 | `scripts/`、`scripts/ci/` 核验 | PASS |

未执行 merge、rebase、reset、checkout、cherry-pick、commit、amend 或 push。

### 1.2 已接受产品事实

- B0→B1→B2→B3→B4→B5→B6→B7 全链已合并到候选分支；B7 最终 Rereview `b8dd2b3e3c`
  结论 `PASS`、`21/21` fixture PASS（B7_REREVIEW §VERDICT）。
- B6 overlay `docker/docker-compose.enterprise.yaml`（74 行）是唯一 enterprise Compose
  覆盖文件；五个企业 runtime 覆盖企业 API/Web image/tag，`agent_backend`/`local_sandbox`
  保持官方 1.16 镜像（B6_REVIEW §3.1）。
- B7 离线链交付 4 个 product 脚本 +
  `scripts/ci/check-enterprise-offline.sh`/`-tests.sh`/`-fixtures/**`（B7_REVIEW §REVIEW_RANGE），
  manifest schema 已固化 `baseline=1.16.0/5c6372d2f7…`、`enterprise_commit`、逐镜像 id/digest
  （B7_REVIEW §4）。
- 官方基线 tag `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`；Alembic 唯一企业 head
  `e7c0a9d2b8f3`（Phase G fixer revision，parent `b416e5c4e702`；CURRENT_STATE §1，`api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py`
  等测试已在仓）。
- 只读 B2 inventory 事实：PostgreSQL `15.17`、实际旧企业 head `e2f0a9b7c6d5`；
  `high_quality`+有 `class_prefix` 的 dataset 1 个、`index_struct.type=weaviate`；
  Weaviate `1.27.0` 认证 GET `/v1/schema` 返回 1 个 class，与 PostgreSQL 预期 class
  哈希集合完全匹配（缺失 0、额外 0）；Weaviate 响应未显式提供 `vectorizer`/
  `vectorIndexType`/`vectorIndexConfig`，均为 `UNKNOWN`，不得解释为没有向量索引
  （B2_INVENTORY §5.4–§5.5、§6、§6.1、§8）。
- 官方 `api/configs/middleware/vdb/weaviate_config.py` 暴露 `WEAVIATE_ENDPOINT`/
  `WEAVIATE_API_KEY`/`WEAVIATE_GRPC_ENDPOINT`/`WEAVIATE_BATCH_SIZE`/
  `WEAVIATE_TOKENIZATION`（仅 `WEAVIATE_ENDPOINT`/`WEAVIATE_API_KEY` 允许 None）；
  `docker/envs/vectorstores/weaviate.env.example` 是官方 Weaviate 配置示例。
- 官方 compose `weaviate` 服务 image `semitechnologies/weaviate:1.27.0`、
  bind `./volumes/weaviate:/var/lib/weaviate`、`VECTOR_STORE: ${VECTOR_STORE:-}`
  interpolation（`docker/docker-compose.yaml:773-798,1196`）。
- 当前发布阻断组合固定为 **PostgreSQL + Weaviate**（VALIDATION_PLAN 硬门禁 7）；
  离线范围固定为 Linux amd64 + PostgreSQL + Weaviate + Compose（ARCHITECT_HANDOFF §8 第 7 条）。

### 1.3 B8 交付物范围依据

ARCHITECT_HANDOFF §5 B8 行 + §4 B8 + VALIDATION_PLAN Phase A–H + PATCH_DECISION_MATRIX
E13/E15/E12：B8 独占最终验证报告和 read-only vector checker；允许写
`scripts/check-enterprise-vector-indexes.*`、对应 fixtures/tests、经批准的
`docs/enterprise/replay-1.16.0/evidence/**`；禁止业务源码、Compose/overlay、migration、
contracts、`docker/volumes/**`；repair 实现未经另批不得写。

## 2. Official-first findings

### 2.1 可复用/必须保持的官方 1.16 能力

| 能力 | 官方/仓库依据 | B8 用法 |
| --- | --- | --- |
| Weaviate 服务身份 | `docker/docker-compose.yaml:773-798`，image `semitechnologies/weaviate:1.27.0`；`docker/envs/vectorstores/weaviate.env.example` | checker 的 provider 身份与只读 GET 目标 |
| Weaviate 配置字段 | `api/configs/middleware/vdb/weaviate_config.py:10-33`（`WEAVIATE_ENDPOINT`/`WEAVIATE_API_KEY`） | checker 输入变量名对齐（`WEAVIATE_ENDPOINT`/`WEAVIATE_API_KEY` 或 `-WeaviateEndpoint`+env key），不读 `.env` |
| `VECTOR_STORE` 选择 | `docker/docker-compose.yaml:1196` `VECTOR_STORE: ${VECTOR_STORE:-}` | 非 `weaviate` 一律 `NOT_RUN`（发布阻断组合外不冒充） |
| 只读查询方法论 | B2_INVENTORY §2（`PGOPTIONS=-c default_transaction_read_only=on`、仅 SELECT/SHOW、Weaviate 仅 GET、脱敏哈希） | checker 默认执行边界；PG 只读会话 + Weaviate GET `/v1/schema`（含按 class GET） |
| class_prefix 判定 | B2_INVENTORY §5.5（`index_struct.vector_store.class_prefix`）；旧 1.15 脚本 `collection_name_for()`（fallback `Dataset.gen_collection_name_by_id`） | checker 按同一语义从 PG `index_struct` 提取预期 class；缺失时 fallback 到官方命名 |
| 只读检查语义 | PATCH_DECISION_MATRIX E13 单元测试清单（缺 class、空 dataset、低质量 dataset、provider error、read-only 不写） | fixture 用例集合 |
| PASS/FAIL/NOT_RUN 三态输出 | B7 `scripts/ci/check-enterprise-offline.sh:70-92`（pass/fail/notrun 计数 + 汇总行） | checker 与 completeness check 沿用同一输出约定 |
| fixture/dry-run 测试模式 | B7 `scripts/ci/check-enterprise-offline-tests.sh`（fake-docker/fake-git shim + `git clone --shared` fixture 工作树） | checker 用 fake psql/curl shim + fixture 数据 |
| 迁移图测试 | `api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py`、`test_enterprise_1_16_marketplace_migration.py` | Phase D 静态门禁证据来源（已合并，不需重跑） |

### 2.2 企业差距（B8 必须覆盖，仍待 B8）

- `scripts/check-enterprise-vector-indexes.sh` 在本仓库不存在；旧 1.15 版本含 `--repair`
  写路径（旧脚本 line 41-47、163-188），必须整体丢弃 repair，只移植只读检查语义。
- Weaviate 对象/向量数量、document segment 完整性、hit testing、部分 index 默认配置
  仍未验证（B2_INVENTORY §8“没有证明”；CURRENT_STATE §6.3）。这些属于 Phase D/G 运行
  门禁（另行授权），checker 只证明 class 级一致性，不得声称对象级证据。
- SSRF Proxy 当前容器挂 1.14.2 entrypoint/template，未采用 1.15 private destination
  默认拒绝/allowlist（B2_INVENTORY §4.5、CURRENT_STATE §6.3）。B8 只记录/验证，不修复。
- 真实 PostgreSQL 升级/回滚矩阵、PG18 空库/应用升级、备份恢复演练均未运行
  （CURRENT_STATE §5；VALIDATION_PLAN Phase D）。

## 3. Vector consistency checker 契约

### 3.1 文件与 allowlist 位置

- 唯一 product 文件：`scripts/check-enterprise-vector-indexes.sh`。
- 对应 fixture 测试与 fixtures（§7.3）：
  - `scripts/ci/check-enterprise-vector-indexes-tests.sh`
  - `scripts/ci/check-enterprise-vector-indexes-fixtures/**`
- `.ps1`：**默认不交付**（`B8_CHECKER_NO_PS1`，§0.2）。Builder 若必须维护 Windows
  运维路径，停下请求扩展 allowlist。

### 3.2 输入契约

checker 不接受数据库/vector 连接串作为命令行参数（防 secret 入日志）。输入分两类：

1. **Compose/环境输入**（默认，面向运行中的升级副本）：
   - `VECTOR_STORE`（必须为 `weaviate`，否则全量 `NOT_RUN` 并退出 0）；
   - `WEAVIATE_ENDPOINT`、`WEAVIATE_API_KEY`（与官方配置字段同名；key 只从环境读，不打印）；
   - `DIFY_ENTERPRISE_VERSION`（默认 `1.16.0-enterprise`，仅作报告身份记录）、
     `COMPOSE_PROFILES`（默认 `weaviate,postgresql,collaboration`，仅作报告身份记录）。
2. **显式只读连接输入**（面向隔离升级副本/演练环境）：
   - `-Postgres` 只读会话由 `PGHOST`/`PGPORT`/`PGDATABASE`/`PGUSER`/`PGPASSWORD`（均从环境）构成，
     且必须携带 `PGOPTIONS='-c default_transaction_read_only=on'`；
   - `-WeaviateEndpoint <url>`（key 仍从 `WEAVIATE_API_KEY` 环境读取）。

身份/只读约束：checker 启动即断言 `VECTOR_STORE=weaviate`、PG 会话 `SHOW
transaction_read_only` 为 `on`；任一不满足即以 `FAIL`/`NOT_RUN` 记录并拒绝继续。未执行
`docker compose up/build/pull/save`、未启动容器、未读 `.env`（B2_INVENTORY §2 同款边界）。

### 3.3 检查逻辑（只读，两级）

1. **PostgreSQL 只读预期集合**（仅 SELECT/SHOW）：
   - 查询 `indexing_technique='high_quality'` 且存在已 completed/enabled 文档与
     completed/enabled segment 的 dataset（对齐 B2_INVENTORY §5.5 与旧 1.15 脚本
     `load_statuses()` 语义：`IndexingStatus.COMPLETED`、`enabled`、非 archived、
     `SegmentStatus.COMPLETED`）。
   - 对每个 dataset 从 `index_struct` JSON 提取 `vector_store.class_prefix`；缺失时
     fallback 到 `Dataset.gen_collection_name_by_id(dataset_id)`（旧脚本 `collection_name_for()`）。
   - 同时读取全部 documents 计数、segments 计数（仅作报告）。
2. **Weaviate 只读 schema 核对**（仅 GET）：
   - 认证 `GET {WEAVIATE_ENDPOINT}/v1/schema` 得实际 class 集合；
   - 对每个预期 class 认证 `GET {WEAVIATE_ENDPOINT}/v1/schema/{class}`；
   - 双向集合比对：预期缺失（`MISSING`）、存在（`PRESENT`）、额外 class（`EXTRA`，报告不阻断）。
   - 不查询对象正文、不导出对象、不写任何 vector 数据（B2_INVENTORY §2 同款边界）。

### 3.4 输出 schema（PASS/FAIL/NOT_RUN，目标脱敏）

逐 dataset 一行（dataset/class 用 SHA-256 前 12 位 hex 脱敏，复用 B2_INVENTORY 脱敏惯例），
末尾汇总行。示例：

```text
# vector consistency check, VECTOR_STORE=weaviate, DIFY_ENTERPRISE_VERSION=1.16.0-enterprise
PASS    dataset=sha256:61372cc983f1  class=sha256:abcd1234ef56  documents=2  segments=63  weaviate_schema_class=present
FAIL    dataset=sha256:61372cc983f1  class=sha256:deadbeef0000  documents=2  segments=63  weaviate_schema_class=missing
NOT_RUN unsupported vector provider: VECTOR_STORE=qdrant (release blocker set is PostgreSQL + Weaviate)
NOT_RUN weaviate schema unavailable (GET /v1/schema returned 403/404/5xx); runtime Phase D/G gate required
summary: 1 PASS / 1 FAIL / 1 NOT_RUN
```

- 任何 `MISSING` → 该行 `FAIL`，脚本 exit 1（对齐 B2_INVENTORY §6.1 结论与 E13 检测目标）。
- `EXTRA` class 仅 `NOT_RUN`/INFO 报告，不阻断（可能为其他 tenant/历史 class，B2 未证明归属）。
- 任何目标（dataset ID、class 名、endpoint、key）绝不打印明文；只输出脱敏别名与布尔/计数。
- 汇总行格式固定 `summary: <n> PASS / <n> FAIL / <n> NOT_RUN`，供 completeness check 解析。

### 3.5 只读强制（read-only enforcement）

- 脚本源码内**不存在** `--repair`、`INSERT`/`UPDATE`/`DELETE`/`ALTER`/`DROP`/`CREATE`/
  `VACUUM`/`docker compose up`/`docker build`/`docker pull`/`docker save` 任一写操作。
- 所有 psql 调用带 `PGOPTIONS=-c default_transaction_read_only=on`；启动断言
  `SHOW transaction_read_only` = `on`。
- Weaviate 仅 `GET`；无 `POST`/`PUT`/`DELETE` 请求。
- 负向 fixture 断言：运行 checker 不产生任何文件写入、不调用 psql 写命令、不调用
  weaviate 写接口（§7.3）。

### 3.6 显式 no-repair 边界

- 本脚本**永不**包含修复逻辑（重建 class、`add_document_to_index_task` 等）。旧 1.15 脚本的
  `--repair` 路径（旧脚本 line 41-47、163-188）是需求证据，不移植。
- Repair 只能作为**独立任务**，由协调者另行批准后另行设计（含幂等、限流、审计、源数据
  只读复核、失败恢复；PATCH_DECISION_MATRIX E13 实施任务要求）。B8 计划只写边界，不设计
  repair 实现。
- 若某个 `MISSING` 需要修复，checker 输出 `FAIL` + 提示“repair is a separately authorized
  task; not performed by this read-only check”，exit 1，不做任何补救动作。

### 3.7 支持的 provider/configuration

- 支持：`VECTOR_STORE=weaviate` + `WEAVIATE_ENDPOINT`/`WEAVIATE_API_KEY`。
- 其他官方 VDB provider（`api/configs/middleware/vdb/` 全部 30 个配置，如 qdrant、
  pgvector、milvus、myscale、elasticsearch、opensearch、chroma 等）在本次发布阻断集合外
  （VALIDATION_PLAN 硬门禁 7、E15），一律 `NOT_RUN`，不假装支持、不猜 provider 结构。
- `WEAVIATE_ENDPOINT` 未配置时按 `VECTOR_STORE` 判定：`weaviate` 且无 endpoint → `NOT_RUN`
  （环境不全），不 `FAIL`、不 `PASS`。

## 4. 证据布局：docs/enterprise/replay-1.16.0/evidence/**

### 4.1 规则

- `docs/enterprise/replay-1.16.0/evidence/**` 只允许**后续被协调者授权的 B8 Builder/Validator**
  写入（`B8_EVIDENCE_BUILDER_ONLY`）。本 Architect 与本计划不创建任何证据文件。
- 每个门禁产物必须是**可复现证据文件**：记录命令、exit code、精确 SHA/时间戳、产出内容；
  只写“已验证”而无证据 = `NOT_RUN`（VALIDATION_PLAN §5）。
- **缺失证据一律 `NOT_RUN`，不是 PASS**（`B8_MISSING_EVIDENCE_IS_NOT_RUN`）。
- 证据内禁真实 secret、真实 `.env` 值、完整 endpoint/key、明文业务 ID/邮箱/姓名/DSL。
  目标一律脱敏（B2_INVENTORY §2 脱敏边界）。
- `evidence/README.md` 是证据索引（每个产物一行：阶段、文件、状态 PASS/FAIL/NOT_RUN、
  command、exit、SHA、日期）；该索引是 completeness check 的输入。

### 4.2 批准布局（按 VALIDATION_PLAN 阶段）

| 路径 | 内容 | 阶段 |
| --- | --- | --- |
| `evidence/phase-a/scope.txt` | `git rev-parse HEAD`、`git merge-base 1.16.0 HEAD`、`git diff --name-status 1.16.0...HEAD`、`git diff --check`、`git grep` scope 输出 | Phase A |
| `evidence/phase-b/focused-backend.log` | `uv run --project api pytest <enterprise focused set>` 最小集合；含 vector checker 相关（Phase B 第 55 行） | Phase B |
| `evidence/phase-b/focused-frontend.log` | `pnpm --dir web vitest run <specs>`、`pnpm --dir web type-check`、`pnpm check`（如环境允许） | Phase B |
| `evidence/phase-b/notrun.txt` | 明确 NOT_RUN 的测试/工具 | Phase B |
| `evidence/phase-c/contracts.log` | B4 唯一 generation 记录（含 deterministic 校验）；或 NOT_RUN | Phase C |
| `evidence/phase-d/heads.txt`、`history.txt` | `flask db heads`/`history` 输出；迁移图测试报告（已合并） | Phase D（静态） |
| `evidence/phase-d/db-matrix/*.md` | 每条“必须运行/条件运行”行的 inventory 前后与结果；真实 DB 操作未授权则 NOT_RUN 并留占位 | Phase D（运行=另行授权） |
| `evidence/phase-e/compose-*.log` | 两层 Compose `config -q`、`config --images \| sort -u`、`--profile collaboration config --services`、S-1…S-9 断言布尔（0600 临时文件） | Phase E（静态） |
| `evidence/phase-f/image-ids-*.log` | `docker inspect` 五 runtime `.Image` ID 与本轮 build 记录；未授权则 NOT_RUN | Phase F（运行=另行授权） |
| `evidence/phase-g/**` | 每场景截图+日志+请求 ID（Agent App Beta 12 场景、Workflow/HITL/WebSocket、plugin/dataset、secret 扫描、auth/RBAC）；未授权则 NOT_RUN | Phase G（运行=另行授权） |
| `evidence/phase-h/**` | manifest/images/config 包扫描、`Mode=reuse` reuse 门禁、`--pull never` 离线 smoke、Phase G 重复 secret 扫描；未授权则 NOT_RUN | Phase H（运行=另行授权） |
| `evidence/vector-checker/checker-*.txt` | checker 实际运行输出（PASS/FAIL/NOT_RUN 汇总）+ 只读断言结果 | B8 checker |
| `evidence/README.md` | 证据索引（§4.1） | 全部 |

## 5. Validation completeness matrix（Phase A–H → owner artifact）

每个门禁的最终状态只有 PASS/FAIL/NOT_RUN；evidence 缺失即 NOT_RUN（§4.1）。Phase D/F/G/H
真实运行操作默认 NOT_RUN，除非协调者逐项另行授权（`B8_PHASE_DFGH_NOT_RUN`）。

| 门禁 | VALIDATION_PLAN 章节 | 必需 owner artifact | B8 Builder 默认 | 另行授权后 |
| --- | --- | --- | --- | --- |
| Phase A 静态范围与基线 | Phase A（line 25-37） | `evidence/phase-a/scope.txt` | 执行（只读 git） | — |
| Phase B 聚焦测试 | Phase B（line 39-65） | `evidence/phase-b/focused-*.log`、`notrun.txt` | 执行最小集（pytest/vitest 若环境允许） | 完整集 |
| Phase C 契约 | Phase C（line 67-74） | `evidence/phase-c/contracts.log` | 只读复核 B4 已生成 contracts + 引用；不再生成 | 必要时重生成（B4 唯一 writer） |
| Phase D migration 图/数据库矩阵 | Phase D（line 76-111） | `evidence/phase-d/heads.txt`/`history.txt`/`db-matrix/*.md` | 静态：引用已合并迁移图测试 + `flask db heads/history`（如 uv 依赖可用）；真实 DB 升级矩阵 **NOT_RUN** | 隔离副本升级/回滚演练（需协调者批准） |
| Phase E Compose 静态验证 | Phase E（line 113-148） | `evidence/phase-e/compose-*.log` | 执行静态（两层 config + S-1…S-9 断言） | 真实 `docker/.env` 展开复核 |
| Phase F 镜像构建与容器身份 | Phase F（line 150-167） | `evidence/phase-f/image-ids-*.log` | **NOT_RUN** | build/recreate/`docker inspect`（FIX-10） |
| Phase G 运行验收 | Phase G（line 169-247） | `evidence/phase-g/**` | **NOT_RUN** | 运行验收含 secret 运行扫描 |
| Phase H 离线包验证 | Phase H（line 249-261） | `evidence/phase-h/**` | 静态扫描 B7 产物（check-enterprise-offline.sh 可在已有产物上跑）；`--pull never` smoke **NOT_RUN** | 离线目标 smoke（`docker load` + `up --pull never`） |
| Secret 扫描 | Phase G “Secret 扫描”（line 243-247）、Phase H §8（line 260） | `evidence/phase-g/secret-scan.log`、`evidence/phase-h/secret-scan.log` | 在受保护 pattern 文件可用时对静态产物跑；否则 NOT_RUN | 运行输出扫描 |
| 回滚协议 | VALIDATION_PLAN §3（line 263-297） | `evidence/phase-d/rollback-drill/*.md` | **NOT_RUN** | 隔离演练（FIX-19） |
| Vector/Weaviate | Phase G “Plugin、Dataset 与向量索引”（line 233-241）、B2_INVENTORY §6 | `evidence/vector-checker/checker-*.txt` | 执行 checker（只读） | hit testing 运行验证 |
| Plugin/Agent/Workflow/HITL/WebSocket | Phase G 各节 | `evidence/phase-g/**` | **NOT_RUN** | 运行验收 |
| auth/RBAC/安全 | Phase G、安全回归清单（line 299-308） | `evidence/phase-g/auth-rbac-security.log` | 静态引用 B3/B4 已合并测试；运行 **NOT_RUN** | 运行验收 |
| 离线包/镜像一致性 | Phase H、B7 manifest | `evidence/phase-h/offline-*.log` | 静态扫描 B7 产物 | 离线目标 smoke |

### 5.1 completeness check（`scripts/ci/check-enterprise-validation-evidence.sh`；条件性/描述性交付，见 §0.6 决定 6）

- 输入：`-Evidence <docs/enterprise/replay-1.16.0/evidence>`（必填）。
- 读 `evidence/README.md` 索引，对上表每个门禁：缺 artifact → `NOT_RUN`；artifact 存在但
  缺 command/exit/SHA/时间戳元数据 → `NOT_RUN`；artifact 存在且元数据完整 → 按内容
  PASS/FAIL/NOT_RUN。
- 规则：任何门禁不能因“无证据”而 PASS；静态证据不能标成运行 PASS（Phase F/G/H 只有
  运行证据可 PASS）。
- 输出沿用 §3.4 三态汇总行：`summary: <n> PASS / <n> FAIL / <n> NOT_RUN`；任一 `FAIL` exit 1。
- 校验证据目录不越界：evidence 目录内任何文件路径必须位于 `docs/enterprise/replay-1.16.0/evidence/` 下。
- 对 checker 产物校验输出行格式（§3.4）与 `summary:` 行一致。

## 6. B8 Builder allowlist / denylist

### 6.1 精确 allowlist（B8 Builder 唯一可写集合）

| 精确文件 | 说明 |
| --- | --- |
| `scripts/check-enterprise-vector-indexes.sh` | 默认只读 vector consistency checker（§3） |
| `scripts/ci/check-enterprise-vector-indexes-tests.sh` | checker fixture/dry-run 测试 |
| `scripts/ci/check-enterprise-vector-indexes-fixtures/**` | checker fixtures（fake psql/curl shim、fixture inventory、canary） |
| `scripts/ci/check-enterprise-validation-evidence.sh` | evidence completeness check（§5.1）；**当前未授权**：不在 ARCHITECT_HANDOFF §5 B8 allowlist，需协调者显式 allowlist 扩展审批后方可写 |
| `scripts/ci/check-enterprise-validation-evidence-tests.sh` | completeness check fixture 测试（含缺证据=NOT_RUN、越界路径、坏格式负例）；**当前未授权**：同上，需协调者显式 allowlist 扩展审批后方可写 |
| `docs/enterprise/replay-1.16.0/evidence/**` | 只允许**后续授权**的 B8 Builder/Validator 写（§4） |

说明：

- `.ps1` 默认不交付（`B8_CHECKER_NO_PS1`）。
- `scripts/ci/check-enterprise-validation-evidence.sh`/`-tests.sh` **当前未被授权**：
  ARCHITECT_HANDOFF §5 B8 行允许写路径仅 `scripts/check-enterprise-vector-indexes.*`、对应
  fixtures/tests、经批准的 evidence/**，不含 `scripts/ci/check-enterprise-validation-*`；
  §5 验收命令“数据库/runtime/offline evidence completeness check”只是验收标准，不是写权限授权。
  completeness check 仅作为条件性/描述性交付保留；B8 Builder 写出这两个脚本前必须获得协调者
  显式 allowlist 扩展审批，本计划不假定审批已存在。
- 除上述文件外任何新文件（含新 docs、新 `.env.example`、新 Dockerfile）默认非法；
  Builder 必须停下请求扩展 allowlist。
- `dist/offline/**` 是 B7 生成产物（gitignored），B8 只读取。
- 本计划本身由本 Architect 唯一写入，B8 Builder 不修改。

### 6.2 只读 reference paths

- 全部已合并实现：`api/**`、`web/**`、`dify-agent/**`、`packages/contracts/generated/api/console/**`（只读）
- B6/B7 artifacts：`docker/docker-compose.enterprise.yaml`、`scripts/build-enterprise-offline.sh`/`.ps1`、
  `scripts/build-enterprise-config-package.sh`/`.ps1`、`scripts/ci/check-enterprise-offline.sh`/`-tests.sh`/`-fixtures/**`
- 隔离升级环境 inventory（B2_INVENTORY.md）
- 官方 Weaviate 配置：`docker/envs/vectorstores/weaviate.env.example`、`docker/docker-compose.yaml`
- 旧 1.15 只读证据：`dify-enterprise-1.15.0/scripts/check-enterprise-vector-indexes.sh`
- `docs/enterprise/replay-1.16.0/` 全部（只读 sources of truth，除 evidence 写路径）

### 6.3 Global denylist

所有 B8 Builder 禁止：

- `docker/**`（官方 compose、overlay、env 示例、nginx/ssrf_proxy、volumes）逐字节不变；
  `docker/volumes/**` 禁止访问/复制/修改
- `api/**`、`web/**`、`dify-agent/**`、`packages/**`（含 contracts）、`api/migrations/**`
- `scripts/**` 除 §6.1 allowlist
- `**/pnpm-lock.yaml`、`**/yarn.lock`、`**/package-lock.json`、`**/package.json`、`**/uv.lock`
- `docker/.env`、任何层级真实 `.env`/secret
- 真实 `.env` 值、endpoint/key、业务明文进证据
- 数据库、Redis、vector、container、volume、外部服务任何写操作；`docker compose up/build/pull/save`
- 任何 repair 实现（含重建 class、重新索引、`add_document_to_index_task` 调用）
- 旧 1.15 源码/Dockerfile/Compose/lockfile/版本文档恢复

若需要 denylist 内文件才能实现，Builder 必须停止并报告，不得扩 scope。

## 7. B8 Builder 验证计划

### 7.1 起点与范围（必跑）

```bash
git branch --show-current
git rev-parse HEAD
git status --short --branch
git merge-base --is-ancestor b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4 HEAD
git diff --check
git diff --name-status <B8 起始 base SHA>...HEAD   # 期望仅 §6.1 allowlist 文件
git diff <base>...HEAD -- docker/   # 期望空
git status --porcelain=v1
```

### 7.2 checker fixture/dry-run 测试（必跑）

```bash
scripts/ci/check-enterprise-vector-indexes-tests.sh
```

fixture 断言（fake psql + fake curl/wget shim + fixture inventory 数据）：

| 用例 | 期望 |
| --- | --- |
| 无 high_quality dataset | 全 PASS（0 FAIL），`summary: n PASS / 0 FAIL / 0 NOT_RUN`，exit 0 |
| high_quality dataset 且 Weaviate class 存在 | 该行 PASS，exit 0 |
| high_quality dataset 但 class 缺失（canary） | 该行 FAIL，`weaviate_schema_class=missing`，exit 1 |
| `VECTOR_STORE=qdrant`（阻断集合外） | 全量 NOT_RUN，exit 0，不冒充 |
| `VECTOR_STORE=weaviate` 但无 `WEAVIATE_ENDPOINT` | NOT_RUN，exit 0 |
| Weaviate GET /v1/schema 403/404/5xx | 对应行 NOT_RUN（运行门禁兜底），不 PASS |
| PG 会话非只读（`PGOPTIONS` 未设） | FAIL 并拒绝继续，exit 1 |
| read-only 不写（负向） | shim 日志断言：无 psql 写命令、无 weaviate POST/PUT/DELETE、无文件写入 |
| 额外 class（EXTRA） | 报告不阻断，exit 0 |
| 输出脱敏 | 输出中不含明文 dataset ID/class/endpoint/key 的 fixture 值 |

### 7.3 completeness check fixture/dry-run（条件性，非必跑）

§7.3 仅在协调者显式 allowlist 扩展审批获得后执行；未授权则如实 NOT_RUN/跳过。

```bash
scripts/ci/check-enterprise-validation-evidence-tests.sh
```

| 用例 | 期望 |
| --- | --- |
| 空 evidence 目录 | 全部 NOT_RUN，`summary` 无 PASS 冒充；exit 0 |
| 缺元数据的 artifact | 该门禁 NOT_RUN |
| 完整 PASS artifact | 门禁 PASS |
| 越界路径（evidence 外文件） | FAIL，exit 1 |
| Phase F/G/H 用静态证据标 PASS | 拒绝（必须运行证据或 NOT_RUN），FAIL |
| 坏 checker 输出行格式 | FAIL |

### 7.4 Phase D/E 静态执行（环境允许时）

```bash
UV_CACHE_DIR=.uv-cache uv run --project api flask db heads    # 网络受限则如实 NOT_RUN（Design Gate §8 第 10 条）
UV_CACHE_DIR=.uv-cache uv run --project api flask db history  # 同上
export DIFY_ENTERPRISE_VERSION=1.16.0-enterprise
export COMPOSE_PROFILES=weaviate,postgresql,collaboration
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config --images | sort -u
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml --profile collaboration config --services
```

静态结果写入 `evidence/phase-d/`、`evidence/phase-e/`；任一命令因环境不可运行 → 如实 NOT_RUN。

### 7.5 Phase D/F/G/H 真实运行——NOT_RUN，另行授权

- Phase D 数据库升级矩阵（空库/官方 1.15/旧企业 1.15/官方 1.16/PG18/uuidv7/回滚）
- Phase F build/recreate/`docker inspect` 五 runtime image ID
- Phase G 运行验收（含 Agent App Beta 12 场景、secret 运行扫描、浏览器/E2E）
- Phase H 离线目标 `docker load` + `up --pull never` + 最小 smoke

`NOT_RUN` 必须在 B8 报告如实声明；静态/checker 结果不替代运行证据（B6_REVIEW §3.6、
B7_REVIEW §7 同款纪律）。

## 8. Exact file ownership matrix

| Exact file | Owner | 依赖（只读） | 共享冲突 | Merge order |
| --- | --- | --- | --- | --- |
| `scripts/check-enterprise-vector-indexes.sh` | B8 独占 | B2_INVENTORY 方法论、旧 1.15 checker（证据）、`api/configs/middleware/vdb/weaviate_config.py`、官方 weaviate env example、B7 check 脚本输出约定 | 无 | B7 之后 |
| `scripts/ci/check-enterprise-vector-indexes-tests.sh`、`-fixtures/**` | B8 独占 | 同 checker；B7 tests.sh fixture 模式 | `scripts/ci/` 目录已有 B0/B7 文件，B8 只新增独立文件 | 同 B8 |
| `scripts/ci/check-enterprise-validation-evidence.sh`/`-tests.sh` | B8 独占（**当前未授权**：需协调者显式 allowlist 扩展审批后方可写/跑；未授权则 NOT_RUN/跳过） | §5.1 矩阵、evidence 布局 | 同 B8 | 同 B8 |
| `docs/enterprise/replay-1.16.0/evidence/**` | 后续授权 B8 Builder/Validator | 全部已合并实现、B6/B7 artifacts | 唯一写者=B8 Builder/Validator；本 Architect 不写 | 随 B8 |
| `docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN.md` | 本 Architect | 全部 sources of truth | 唯一 writer=本计划 | 随 B8 计划门禁 |

共享路径唯一所有者重申（ARCHITECT_HANDOFF §5）：`docker/docker-compose.enterprise.yaml`
唯一写者 = B6；`scripts/**` 企业 B 任务新增文件按任务分区，B8 只新增 §6.1 独立文件，不修改
B0/B7 文件。

## 9. Builder topology and serial gates

```text
B8 Architect（本计划）
→ 独立 Plan Reviewer
→ CHANGES_REQUIRED: finding-scoped Plan Fixer → 独立 Plan Rereviewer
→ 协调者检查 dirty diff 后另行授权 plan commit
→ fast-forward 到候选分支
→ B8 Builder（只写 §6.1 allowlist：checker + fixtures/tests；evidence completeness check 为
   条件性/描述性交付，仅协调者显式 allowlist 扩展审批后写与跑，未授权则 NOT_RUN/跳过；Phase A/B/E
   静态 + §7.2/§7.3 fixture/dry-run（§7.3 需审批）+ §7.4 静态；证据目录初始化只放 README 索引）
→ Code Reviewer（Migration/Data + Docker/Offline + Runtime/Release 视角）
→ Fixer? → Rereviewer
→ 协调者检查 dirty diff 后另行授权 commit
→ fast-forward 到候选分支，记录精确 SHA
→ 协调者逐项另行授权 Phase D/F/G/H 运行门禁（每项独立授权，静态不得冒充）
→ Validator 收集全部授权门禁证据 → completeness check 全绿 → 最终发布门禁
```

- B8 不并行启动其他 Builder；B8 是最终发布门禁，不可跳过（ARCHITECT_HANDOFF §7 第 9 条）。
- Phase D/F/G/H 授权只能由协调者逐项另行发出；未授权时 B8 Builder 结束于静态/只读验证。

## 10. Risks, decisions and stop conditions

### 10.1 Known limitations（保持可见，不得删除/降级）

B7R-03..06（已承认 P3，B7_REREVIEW §REMAINING FINDINGS / B7_REVIEW FINDINGS）：

- `B7R-03`：B7 check 脚本 dev-default WARNING 校验为“同文件”而非“相邻”（`check-enterprise-offline.sh:332-351`）。
- `B7R-04`：B7 check 脚本硬编码 `1.16.0-enterprise`（`check-enterprise-offline.sh:56-61`）。
- `B7R-05`：B7 `.ps1` UTF-8 BOM 风险（Windows PowerShell 5.1；`.ps1` 运行 NOT_RUN）。
- `B7R-06`：B7 `forbidden_path` 不拦裸 `docker/volumes` 目录项（`check-enterprise-offline.sh:89-117`）。

B4 accepted known limitations（CURRENT_STATE §6.1）：

- 官方 `AppDslService.import_app()` 内部 commit 造成 copy 无法承诺完全原子回滚；
- DSL 未来新增未知字段时，显式 sanitizer 规则可能需要同步扩展；
- 边界：企业校验必须在 import 前完成；B8 必须覆盖失败 reconciliation 和信息泄漏。

B2/B8 运行风险（CURRENT_STATE §6.3、B2_INVENTORY §4/§8）：

- 核心应用实际运行 Enterprise 1.15.0；Weaviate/Sandbox 创建与挂载 provenance 来自 1.14.2；
- SSRF Proxy 仍用 1.14.2 配置，缺 1.15 private destination 默认拒绝和 allowlist；
- Weaviate class 对应已核对，但对象完整性、hit testing、部分 index 默认配置仍待 B8 运行门禁；
- volume provenance 必须按实际挂载路径验证，不能只相信 Compose 文件；
- Weaviate `vectorizer`/`vectorIndexType`/`vectorIndexConfig` 为 `UNKNOWN`；
- `--pull never` 离线 smoke、PG 升级/回滚矩阵、备份恢复演练未运行（CURRENT_STATE §5）。

本计划不声称已解决上述任何一项；B8 只保证 checker 只读检测 + 证据完整性 + 未授权项如实
NOT_RUN。

### 10.2 RECORDED_DECISION

1. `B8_READONLY_DEFAULT`：checker 默认且唯一只读；无 repair 路径；repair 独立任务+协调者批准。
2. `B8_CHECKER_NO_PS1`：只交付 `.sh`；Windows parity 不成立，不默认新增 `.ps1`。
3. `B8_EVIDENCE_BUILDER_ONLY`：evidence/** 只允许后续授权 B8 Builder/Validator 写。
4. `B8_MISSING_EVIDENCE_IS_NOT_RUN`：缺证据 = NOT_RUN，不是 PASS。
5. `B8_PHASE_DFGH_NOT_RUN`：Phase D/F/G/H 真实运行默认 NOT_RUN，逐项协调者授权。
6. `B8_COMPLETENESS_CHECK`：evidence completeness check 为**条件性/描述性交付**；脚本当前未授权，需协调者显式 allowlist 扩展审批后方可写出/运行，未授权则 NOT_RUN（同 §0.6）。

### 10.3 Stop conditions

- exact branch/SHA/clean/B7 ancestor 起点不符；
- 修改了 `docker/**`、`api/**`、`web/**`、`dify-agent/**`、`packages/**`、`api/migrations/**`
  或任何 denylist 文件，或需要 §6.1 之外新文件而未获批准；
- checker 出现任何写路径（repair/重建 class/重新索引/psql 写/weaviate 写/compose up）；
- checker 输出含明文 dataset/class/endpoint/key；PG 会话非只读仍继续执行；
- 缺失证据被标为 PASS，或 Phase F/G/H 用静态证据冒充运行 PASS；
- evidence 目录出现越界路径或真实 secret；
- Phase D/F/G/H 被擅自执行；`docker/volumes/**` 被访问/复制；
- 出现 P0/P1 security、secret、数据完整或 volume 泄漏。

## 11. Architect validation record and NOT_RUN

### 11.1 实际执行的只读命令

| Command | exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b8-architect` |
| `git rev-parse HEAD` | 0 | `b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4` |
| `git status --short --branch` | 0 | clean |
| `git status --porcelain=v1` | 0 | empty |
| `git diff --check` | 0 | clean |
| `git log --oneline -15` | 0 | HEAD 为 B7 Rereview `b8dd2b3e3c`；含 B7 Code Review `93ab820b48`、B7 Fixer `bb86a5e8aa`、B7 code feat `28f9f72e7d` |
| `git show d218e48f28:docker/docker-compose.enterprise.yaml \| wc -l` | 0 | 74 |
| `ls scripts/check-enterprise-vector-indexes.*` | 1 | no-such-file（B8 待创建） |
| `ls docs/enterprise/replay-1.16.0/evidence` | 1 | no-such-dir（B8 Builder 才写） |
| `ls api/migrations/versions/` | 0 | 三个历史 revision + `a71e16c0de01` + `b416e5c4e702` 均存在 |
| `git merge-base 1.16.0 HEAD` | 0 | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| 读取 sources of truth 六份 + B2_INVENTORY + B6/B7 计划与 Review | — | 全部读取 |
| 旧 1.15 vector checker（只读证据） | — | `dify-enterprise-1.15.0/scripts/check-enterprise-vector-indexes.sh` 189 行，含 `--repair`（不移植） |
| 官方配置/Compose 事实 | — | `api/configs/middleware/vdb/weaviate_config.py`、`docker/envs/vectorstores/weaviate.env.example`、`docker/docker-compose.yaml` weaviate 段与 `VECTOR_STORE` |

### 11.2 NOT_RUN（如实声明）

| Area | Status |
| --- | --- |
| `flask db heads/history` | NOT_RUN（本工作区受限网络无法获取锁定 Git 依赖，Design Gate §8 第 10 条；已引用已合并迁移图测试） |
| `docker compose config`（两层） | NOT_RUN（无 `docker/.env`；B6 已验；B8 Builder 按 §7.4 补跑） |
| Phase D 数据库升级矩阵 / 回滚演练 | NOT_RUN（另行授权） |
| Phase F 构建/容器身份 | NOT_RUN（另行授权） |
| Phase G 运行验收 / browser / E2E | NOT_RUN（另行授权） |
| Phase H 离线目标 `--pull never` smoke | NOT_RUN（另行授权） |
| checker 运行 | NOT_RUN（B8 Builder 实现后） |
| `docker/volumes/**` 访问或复制 | NOT_RUN（禁止） |

## 12. Exact final validation commands

Architect 交付必须执行：

```bash
git diff --name-status
git diff -- docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN.md
git diff --check
git status --short --branch
git status --porcelain=v1
```

后续 B8 Builder 必须执行（§7）；最终 B8 Reviewer 在所有 Builder 合并后执行：

```bash
git diff --name-status <accepted-b8-plan-sha>...HEAD
git diff --check
# §7.2 checker fixture、§7.3 completeness fixture（条件性，见 §7.3）、§7.4 Phase D/E 静态；Phase F/G/H 按协调者授权
scripts/ci/check-enterprise-vector-indexes-tests.sh
# 以下 completeness check 两命令需先获 §0.6/§6.1 所述 allowlist 扩展审批；未授权则 NOT_RUN
scripts/ci/check-enterprise-validation-evidence-tests.sh
scripts/ci/check-enterprise-validation-evidence.sh -Evidence docs/enterprise/replay-1.16.0/evidence
```

不得把 `docker compose build`、容器运行、数据库升级或离线目标 smoke 作为 B8 静态 validation；
Phase D/F/G/H 属于逐项另行授权阶段。

## 13. Plan Reviewer checklist

- [ ] 强制起点与 B7 ancestor 事实真实（§1.1）：branch/HEAD/clean、`b8dd2b3e3c`（B7 Rereview）在 HEAD、B6 overlay 74 行、vector checker 与 evidence 均不存在。
- [ ] checker 只读契约完整（§3）：输入（环境/显式只读连接）、`VECTOR_STORE=weaviate` 门禁、PG 只读断言、Weaviate 仅 GET、输出三态与脱敏、负向“read-only 不写”。
- [ ] 无 repair 路径；repair 只作为独立任务+协调者批准描述（E13），本计划未设计 repair 实现。
- [ ] `.ps1` 默认不交付且理由（旧链无 `.ps1` 对照）明确。
- [ ] evidence 布局（§4）与缺失证据=NOT_RUN 规则明确；Phase A–H 每门禁有 owner artifact。
- [ ] completeness matrix（§5）覆盖 Phase A-H、B6 overlay、B7 离线链、DB/migration 矩阵、vector/Weaviate、plugin/Agent/workflow/HITL/WebSocket、auth/RBAC/安全、secret 扫描、`--pull never` smoke、回滚协议。
- [ ] Phase D/F/G/H 默认 NOT_RUN 且逐项协调者授权；无静态冒充运行。
- [ ] allowlist 精确（§6.1）；denylist 覆盖 docker/volumes/业务源码/migration/contracts/repair/真实 env。
- [ ] 已知限制保持可见（B7R-03..06、B4 limitations、B2/B8 运行风险、Weaviate UNKNOWN、SSRF 1.14.2、volume provenance）。
- [ ] 验证命令与报告 schema（三态汇总、脱敏、证据索引）可执行可复核。
- [ ] 风险、决定、stop conditions 完整；无未声明的文件所有权。

## 14. Gate

```text
Architect dirty plan
→ coordinator inspects real diff
→ separately authorizes plan commit
→ fast-forward plan commit into candidate
→ independent Plan Reviewer from exact new SHA
→ CHANGES_REQUIRED: finding-scoped Fixer
→ independent Rereviewer
→ only then coordinator may authorize B8 Builder（只写 §6.1 allowlist；静态 + fixture/dry-run）
→ Code Reviewer → Fixer? → Rereviewer
→ B8 fast-forward 并记录精确 SHA
→ coordinator 逐项授权 Phase D/F/G/H 运行门禁
→ Validator 收集证据 → completeness check 全绿 → 最终发布门禁
```

`RECORDED_DECISION`：`B8_READONLY_DEFAULT`、`B8_CHECKER_NO_PS1`、
`B8_EVIDENCE_BUILDER_ONLY`、`B8_MISSING_EVIDENCE_IS_NOT_RUN`、
`B8_PHASE_DFGH_NOT_RUN`、`B8_COMPLETENESS_CHECK`。

当前门禁：**PLAN_READY**；`B8_BUILDER_NOT_AUTHORIZED`；Phase D/F/G/H 需协调者逐项另行授权。

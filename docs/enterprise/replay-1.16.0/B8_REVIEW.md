# Dify Enterprise 1.16.0 Replay B8 Vector Consistency Checker — Independent Code Review

- **Role**: Code Reviewer（B8 Builder 独立审查）
- **Instance**: `replay-116-b8-reviewer`
- **Branch**: `ctyun/replay-116-b8-reviewer`
- **HEAD**: `79d8252121d392c0c1157d2313651873e21d9b69`
- **Reviewed range**: `ce316ce2169a77ec3f6106a4cbe3ddd4caa03f7a..79d8252121d392c0c1157d2313651873e21d9b69`
- **Reviewed commit**: `79d8252121` "feat: add enterprise B8 vector consistency checker and evidence"
- **结论**: `PASS`（无 P0/P1/P2；P3 观察项 3 条，不阻断）

本报告是独立 Review 证据。本 Reviewer 未修改任何 product/denylist/evidence 文件；唯一写入
文件是本报告 `docs/enterprise/replay-1.16.0/B8_REVIEW.md`。未执行 commit、amend、push、
merge、rebase、reset、checkout 或 cherry-pick。

---

## RECOVERY

| item | expected | actual | result |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b8-reviewer` | `ctyun/replay-116-b8-reviewer` | PASS |
| HEAD | `79d8252121d392c0c1157d2313651873e21d9b69` | `79d8252121d392c0c1157d2313651873e21d9b69` | PASS |
| `git status --short --branch` | clean | `## ctyun/replay-116-b8-reviewer` | PASS |
| range 唯一 commit | `79d8252121` | `git log ce316ce..HEAD` 唯一 commit `79d8252121` | PASS |

## REVIEW_RANGE

- `git diff --name-status ce316ce..HEAD`：**恰好 19 个路径**，全部落在四个允许路径：

```text
A  docs/enterprise/replay-1.16.0/evidence/README.md
A  docs/enterprise/replay-1.16.0/evidence/phase-a/scope.txt
A  docs/enterprise/replay-1.16.0/evidence/phase-b/checker-fixture-tests.log
A  docs/enterprise/replay-1.16.0/evidence/phase-b/focused-backend.log
A  docs/enterprise/replay-1.16.0/evidence/phase-b/notrun.txt
A  docs/enterprise/replay-1.16.0/evidence/phase-c/contracts.log
A  docs/enterprise/replay-1.16.0/evidence/phase-d/db-matrix/notrun.md
A  docs/enterprise/replay-1.16.0/evidence/phase-d/flask-db.log
A  docs/enterprise/replay-1.16.0/evidence/phase-d/migration-graph-tests.log
A  docs/enterprise/replay-1.16.0/evidence/phase-e/compose-config.log
A  docs/enterprise/replay-1.16.0/evidence/vector-checker/checker-notrun.txt
A  scripts/check-enterprise-vector-indexes.sh
A  scripts/ci/check-enterprise-vector-indexes-fixtures/bin/fake-curl
A  scripts/ci/check-enterprise-vector-indexes-fixtures/bin/fake-psql
A  scripts/ci/check-enterprise-vector-indexes-fixtures/data/schema-empty.json
A  scripts/ci/check-enterprise-vector-indexes-fixtures/data/schema-extra.json
A  scripts/ci/check-enterprise-vector-indexes-fixtures/data/schema-fallback.json
A  scripts/ci/check-enterprise-vector-indexes-fixtures/data/schema-present.json
A  scripts/ci/check-enterprise-vector-indexes-tests.sh
```

- `git diff --stat`：`19 files changed, 1125 insertions(+)`，与契约 **+1125/-0** 一致。
- `git diff --binary | sha256sum`：`bd3de9497bebb901989bacfe82763528fdcf7b86267cbec65fd0bda2c8419f7a`，与契约一致。
- `git diff --check ce316ce..HEAD`：clean（exit 0）。
- 无 completeness 脚本（`check-enterprise-validation-evidence*`）、无 B8_IMPLEMENTATION_PLAN*/CURRENT_STATE 修改、
  无 docker/api/web/dify-agent/packages/migration/contract 触碰。

## SOURCES_READ

- `docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN.md`（§2/§3/§4/§5/§6/§7.2）
- `docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN_REREVIEW2.md`
- `docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md`、`VALIDATION_PLAN.md`、`B2_INVENTORY.md`
- 提交的全部 19 个文件（逐行）
- 仓库事实核对：
  - `api/models/dataset.py:485-487` `Dataset.gen_collection_name_by_id`（`Vector_index_<normalized>_Node`，前缀取自 `dify_config.VECTOR_INDEX_NAME_PREFIX` 默认 `Vector_index`）
  - `api/models/dataset.py:588-597` Document（`indexing_status`/`enabled`/`archived`）、`:905-939` DocumentSegment（`status`/`enabled`）
  - `api/providers/vdb/vdb-weaviate/src/dify_vdb_weaviate/weaviate_vector.py:173-186` `get_collection_name`
  - `api/commands/vector.py:153-164`（Weaviate ∈ upper_collection_vector_types，`gen_collection_name_by_id` 结果含 `_Node` 写入 class_prefix）

## CHECKLIST VERIFICATION

### 1. Range and scope — PASS

19 文件、+1125/-0、diff SHA-256 逐字节匹配；`git diff --check` clean；无 completeness 脚本，
无 evidence 之外 docs 改动，无 product 代码。`git diff ce316ce..HEAD --name-only | rg
'check-enterprise-validation-evidence'` 无命中。

### 2. Read-only enforcement — PASS

`scripts/check-enterprise-vector-indexes.sh`：

- 源码内 **无** `--repair`、`INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/VACUUM/TRUNCATE`、
  `docker compose up/build/pull/save`（`rg` 无命中）。
- PostgreSQL：仅两条 psql 调用（line 97 `SHOW transaction_read_only`、line 144 `-c "<SELECT-only SQL>"`），
  均 `-X -v ON_ERROR_STOP=1` 只读参数；启动断言 `PGOPTIONS` 含 `default_transaction_read_only=on`
  （line 91-94）并 `SHOW transaction_read_only`=`on`（line 103-106），任一不满足即 FAIL 并 `finish` 拒绝继续。
- Weaviate：`weaviate_get()`（line 165-193）仅 `curl --output --write-out '%{http_code}'`（GET）
  或 wget 读取；无 POST/PUT/DELETE；无对象正文查询。
- 负向 fixture（case 08）断言 shim 日志无 psql 写命令、无非 GET weaviate 请求、run 目录零文件写入。
- 无 docker/容器/volume 操作，不读 `.env`。

### 3. Checker logic — PASS

- `VECTOR_STORE=weaviate` 门禁（line 80-83）：非 weaviate 全量 NOT_RUN、exit 0。
- 预期 class SQL（line 113-137）对齐 B2_INVENTORY §5.5 与计划 §3.3：`indexing_technique='high_quality'`
  AND EXISTS(completed/enabled/**非 archived** documents) AND EXISTS(completed/enabled segments)；
  column 名逐一对齐 `api/models/dataset.py`（`indexing_status`/`enabled`/`archived`、
  `status`/`enabled`），枚举值 `completed` 对齐 `api/models/enums.py`。
- `class_prefix` 从 `index_struct::jsonb #>> '{vector_store,class_prefix}'` 提取，缺失时 fallback
  `Vector_index_<id 中 - → _>_Node`，与 `Dataset.gen_collection_name_by_id` 默认前缀语义一致
  （B8R-02 观察自定义前缀）。
- 逐 class GET `/v1/schema/{class}`：200=PASS、404=FAIL + "repair is a separately authorized task..."
  独立提示、其余非 200=NOT_RUN；额外 class 仅 NOT_RUN 报告不阻断（case 09 证明 exit 0）。
- 脱敏：所有 dataset/class 目标经 `redact()`（sha256 前 12 位 hex）；endpoint/key 不打印；报告仅
  布尔/计数。header 只含 VECTOR_STORE/DIFY_ENTERPRISE_VERSION/COMPOSE_PROFILES 身份值。

### 4. Fixture suite — PASS

`scripts/ci/check-enterprise-vector-indexes-tests.sh` 独立重跑：**47/47 ok，exit 0**，输出与
`evidence/phase-b/checker-fixture-tests.log` 逐行一致（证据真实可复现）。计划 §7.2 全部 10 行用例
均被覆盖：

| §7.2 用例 | 覆盖 |
| --- | --- |
| 无 high_quality dataset 全 PASS | case 01 |
| class 存在 PASS | case 02 |
| class 缺失 FAIL + repair 提示 + exit 1 | case 03 |
| `VECTOR_STORE=qdrant` 全量 NOT_RUN exit 0 | case 04 |
| weaviate 无 `WEAVIATE_ENDPOINT` NOT_RUN exit 0 | case 05 |
| GET /v1/schema 403/404/5xx → NOT_RUN 不 PASS | case 06（403；checker 对全部非 200 统一处理） |
| PGOPTIONS 未设 → FAIL + 拒绝继续 exit 1 | case 07 |
| read-only 不写（负向 shim 日志 + 零文件写入） | case 08 |
| 额外 class 报告不阻断 exit 0 | case 09 |
| 输出脱敏（无明文 dataset/class/endpoint/key） | case 10 |

额外 case 11（PG 连接失败 NOT_RUN）、12（显式 `-WeaviateEndpoint`）、13（class_prefix fallback）。
`bash -n` 两个脚本均 clean。

### 5. Evidence — PASS

- `git ls-files docs/enterprise/replay-1.16.0/evidence` = **11**（README + 10 artifact）。
- README 索引的 10 个 artifact 全部存在且 tracked；六个 `*.log` 虽命中 `.gitignore:63 (*.log)`
  （无目录内 negate），仍 tracked（`git add -f` 语义，符合契约描述）。
- 证据真实性抽查（可复现项全部命中）：
  - `checker-fixture-tests.log`：重跑 47/47 逐行一致；
  - `vector-checker/checker-notrun.txt`：重跑两个 NOT_RUN demo，输出/exit 逐行一致；
  - `phase-a/scope.txt`：`git merge-base 1.16.0 HEAD` 复现 `5c6372d2...`；`git diff --check` exit 0；
  - `phase-b/focused-backend.log`、`phase-d/migration-graph-tests.log` 引用的 4 个 pytest 文件
    均存在于仓库；断言计数与日志一致（reviewer 沙箱无 `api/.venv`，未独立重跑，见 NOT_RUN）。
- Phase D/F/G/H 与 completeness 脚本均 NOT_RUN/absent，无冒充 PASS。
- secret 扫描（endpoint/key/token/password/bearer/邮件/业务 UUID 正则）无明文命中；
  `compose-config.log` 仅含 sandbox 工作树路径，非 secret。

### 6. No unauthorized writes — PASS

range 仅触碰 `scripts/check-enterprise-vector-indexes.sh`、
`scripts/ci/check-enterprise-vector-indexes-tests.sh`、
`scripts/ci/check-enterprise-vector-indexes-fixtures/**`、
`docs/enterprise/replay-1.16.0/evidence/**` 四类路径；无 docker/api/web/dify-agent/packages/
plan/review/migration/contract 改动。

## COMMANDS & COUNTS

| command | result |
| --- | --- |
| `git branch --show-current` | `ctyun/replay-116-b8-reviewer` PASS |
| `git rev-parse HEAD` | `79d8252121d392c0c1157d2313651873e21d9b69` PASS |
| `git status --short --branch`（起/终） | clean PASS |
| `git diff --name-status ce316ce..HEAD` | 19 files PASS |
| `git diff --stat ce316ce..HEAD` | +1125/-0 PASS |
| `git diff --check ce316ce..HEAD` | clean PASS |
| `git diff --binary ce316ce..HEAD \| sha256sum` | `bd3de9497b...` PASS |
| `bash -n`（checker + tests） | clean PASS |
| `scripts/ci/check-enterprise-vector-indexes-tests.sh` | 47/47 PASS，exit 0 |
| `git ls-files docs/enterprise/replay-1.16.0/evidence \| wc -l` | 11 PASS |
| `rg -n -- '--repair\|INSERT\|...\|docker compose (up\|build\|pull\|save)' scripts/check-enterprise-vector-indexes.sh` | 0 hit PASS |
| `git diff ce316ce..HEAD --name-only \| rg 'check-enterprise-validation-evidence'` | 0 hit PASS |
| `git diff --check`（全树） | clean PASS |
| checker NOT_RUN demo 复现（2 runs） | 逐行一致 PASS |

Pass count：19（上表）。NOT_RUN（诚实未独立重跑）：backend 聚焦 pytest（focused-backend /
migration-graph 两组，沙箱无 `api/.venv`）；weaviate wget fallback 分支 fixture 未覆盖。
无 FAIL。

## FINDINGS

### B8R-01 (P3, 观察/不阻断) — class_prefix 逐字使用 vs Weaviate provider `_Node` 补全分支

- 位置：`scripts/check-enterprise-vector-indexes.sh:232-239`；对照
  `api/providers/vdb/vdb-weaviate/src/dify_vdb_weaviate/weaviate_vector.py:180-183`。
- 内容：provider `get_collection_name` 对缺失 `_Node` 后缀的 class_prefix 会追加 `_Node`；checker
  逐字使用 class_prefix。若某 dataset 的 class_prefix 无 `_Node` 后缀，checker 将得到假 FAIL。
- 违反不变量：无。计划 §3.3 与 B2_INVENTORY §5.5 均规定逐字 class_prefix 语义；B2 实测唯一
  high_quality dataset 的 class_prefix 与 Weaviate class 完全匹配（含后缀），且 `commands/vector.py`
  写入 class_prefix 时已含 `_Node`。
- 处置：接受。仅遗留 class_prefix 无 `_Node` 的数据会有偏差；如 future repair 授权时可按
  provider 语义对齐。

### B8R-02 (P3, 观察/不阻断) — fallback 硬编码默认前缀 `Vector_index`

- 位置：`scripts/check-enterprise-vector-indexes.sh:236-237`；对照
  `api/models/dataset.py:486-487`（前缀来自 `dify_config.VECTOR_INDEX_NAME_PREFIX`）。
- 内容：自定义 `VECTOR_INDEX_NAME_PREFIX` 的部署下，缺失 class_prefix 的 dataset 会按默认前缀
  生成预期 class，导致假 FAIL。
- 违反不变量：无（默认配置下与官方命名一致；B2 实测缺失 class_prefix=0）。
- 处置：接受。如需支持自定义前缀，可增加 env 输入（计划未要求）。

### B8R-03 (P3, 观察/不阻断) — wget fallback 分支未覆盖且状态解析与 curl 有偏差

- 位置：`scripts/check-enterprise-vector-indexes.sh:178-188`。
- 内容：fixture 只 fake curl，wget 分支零测试；wget 对 HTTP 错误（如 404）默认非零退出，会被
  `if ! code=$(...)` 归为连接失败 → NOT_RUN，而 curl 分支会如实区分 404=FAIL。
- 违反不变量：无（计划 §3.4/§7.2 以 curl/wget shim 为要求，主路径 curl 覆盖完整）。
- 处置：接受。curl 存在时优先走 curl；如需 wget-only 环境可补 fixture。

## VERDICT

**PASS**。范围精确（19 文件 / +1125 / diff SHA 匹配）、只读语义完整、checker 逻辑对齐
B2_INVENTORY 与计划 §3，fixture 47/47 且独立复现，证据 honest 且全部 tracked，无 P0/P1/P2。
P3 观察项 B8R-01/02/03 不阻断。

本 Reviewer 未执行任何 commit、amend、push、merge、rebase、reset、checkout 或 cherry-pick；
`git status --short --branch` 最终仍 clean（本报告文件尚未提交）。

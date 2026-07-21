# Dify Enterprise 1.16.0 Architect Re-Review

## 1. 复审日期

2026-07-21

## 2. 官方基线

- 官方标签：`1.16.0`
- 官方提交：`5c6372d2f76d240265b92fd27c16bc772ffcb107`

## 3. 原始审查 commit

`caedca07e4938e8460c755b9ba37293d59417c8c` (branch: `ctyun/replay-116-reviewer`)

## 4. 整改 commit

`2af616e7e2de1939431b51b4521e6bf2b580be47` (subject: `docs: address enterprise 1.16.0 replay review`)

## 5. 复审分支

`ctyun/replay-116-reviewer2`

HEAD == `2af616e7e2` ✓

## 6. 文件范围检查

### 6.1 整改修改文件 (5 files)

| 文件 | 状态 |
| --- | --- |
| `ENTERPRISE_REPLAY_PLAN.md` | 已修改 ✓ |
| `docs/enterprise/replay-1.16.0/OFFICIAL_RELEASE_ANALYSIS.md` | 已修改 ✓ |
| `docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md` | 已修改 ✓ |
| `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md` | 已修改 ✓ |
| `docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md` | 已修改 ✓ |

### 6.2 逐字未变文件确认

| 文件 | 状态 |
| --- | --- |
| `docs/enterprise/replay-1.16.0/ARCHITECT_REVIEW.md` | 未修改 ✓ (`git diff caedca07e4..2af616e7e2 -- ARCHITECT_REVIEW.md` 输出为空) |

### 6.3 禁止修改目录确认

| 目录 | 状态 |
| --- | --- |
| `api/` | 未修改 ✓ |
| `web/` | 未修改 ✓ |
| `docker/` | 未修改 ✓ |
| `packages/` | 未修改 ✓ |
| `dify-agent/` | 未修改 ✓ |
| `docker/volumes/` | 未修改 ✓ |
| 依赖和锁文件 | 未修改 ✓ |
| migration 实现 | 未修改 ✓ |

### 6.4 整改范围结论

整改提交严格只修改了 5 个允许的文档文件，原始 `ARCHITECT_REVIEW.md` 逐字未变。业务代码、Docker、migration、依赖、version 号和 `docker/volumes` 均未涉及。通过。

---

## 7. FIX-01 ~ FIX-19 逐项结果

### P0 复审

#### FIX-01: B2/B4 循环依赖

**原始问题**: B2 需产出“最终智慧广场 schema”并创建 merge migration，但 schema 设计信息要到 B4 才知道。

**整改内容**:
- `ENTERPRISE_REPLAY_PLAN.md:62-65`: B2 只恢复 3 个历史 revision 并创建空 merge；B4 在 merge 后追加最终 schema migration。
- `ARCHITECT_HANDOFF.md:54-58, 66-70`: B2/B4 职责明确拆分。
- `PATCH_DECISION_MATRIX.md:65-66`: 不可变快照决策设为人工 Design Gate。

**逐项验证**:

1. B2 只恢复历史 revision `c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5` — ✓
2. B2 创建空 merge `a71e16c0de01` — ✓
3. 空 merge parents 精确为 `e2f0a9b7c6d5` 和 `7a1c2d9e4b60` — ✓
4. 空 merge 不包含业务 DDL — ✓
5. B4 在空 merge 后创建 `b416e5c4e702` — ✓
6. `b416e5c4e702` 的 `down_revision` 为 `a71e16c0de01` — ✓
7. B4 独占最终智慧广场 schema、DDL、model、service、controller 和 contracts — ✓
8. 顺序强制为 `B2 → B3 → B4 → B5` — ✓
9. B3 与 B4 不允许并行 — ✓（多次声明 `B3/B4 不并行`）

**不可变发布快照 Design Gate 检查**:

- `PATCH_DECISION_MATRIX.md E04`: "推荐采用发布时生成不可变快照...该方向是 Builder 前人工 Design Gate；历史业务事实若冲突必须在启动前提出" — ✓
- `ENTERPRISE_REPLAY_PLAN.md §4 B4`: "以'发布时生成不可变快照'为推荐架构决定，通过人工 Design Gate 后定义 1.16 最终 schema" — ✓
- `ARCHITECT_HANDOFF.md §8`: "该项是 Builder 前 Design Gate" — ✓

该决定明确标记为人工 Design Gate，Builder 无需猜测。通过。

**结果**: **VERIFIED_CLOSED**

---

#### FIX-02: 缺少 Builder 任务文件范围与重叠矩阵

**原始问题**: 无 Builder 文件所有权表；`api/controllers/console/__init__.py`、`api/models/__init__.py`、`api/migrations/versions/`、`packages/contracts/`、`web/i18n/` 存在跨 B 任务冲突。

**整改内容**: `ARCHITECT_HANDOFF.md §5` 增加完整的 Builder 文件所有权与重叠矩阵。

**逐项验证**:

| 共享路径 | 所有者 | 验证 |
| --- | --- | --- |
| `api/controllers/console/__init__.py` | B4 独占 | B3 forbidden paths 包含该文件；B4 负责统一注册 B3+B4 endpoint — ✓ |
| `api/models/__init__.py`、`api/models/model.py` | B4 独占 | B2 只恢复 migration（不创建/注册 model）；B4 定义最终模型 — ✓ |
| `api/migrations/versions/` | 按文件分区（B2 历史+空 merge，B4 最终 schema） | B2/B4 不改对方文件 — ✓ |
| `packages/contracts/` | B4 独占生成者 | B3 不生成；B5 只消费 — ✓ |
| `web/i18n/en-US/common.json`、`web/i18n/zh-Hans/common.json` | B5 独占 | 后端 Builder 不预写 — ✓ |
| `docker/docker-compose.enterprise.yaml` | B6 独占 | B7 只读取展开结果 — ✓ |

**关键设计挑战验证**:

- B3 不修改 controller 注册文件，B4 后续统一注册 B3+B4 endpoint — ✓ (`api/controllers/console/__init__.py` 仅 B4 写入)
- B3 不生成 contracts，B4 在 B3 合并后统一生成 — ✓ (B4 负责把 B3+B4 endpoint 一次性生成)
- B5 只消费 contracts，禁止自行重新生成 — ✓ (B5 forbidden: `packages/contracts/**`)
- B2 与 B4 只写各自指定的 migration 文件 — ✓ (按文件分区)
- 未声明文件出现时必须暂停任务 — ✓ (§5 首段明确)

**隐藏共享文件检查**:

每个 B 任务拥有独立的 Allowed write / Read-only reference / Forbidden paths。以下路径在原始 Review 中未明确提出，但在整改矩阵中已有分配：

- `api/configs/feature/__init__.py` — B3 allowed ✓
- `api/libs/platform_admin.py` — B3 exclusive ✓
- `api/services/platform_admin_service.py` — B3 exclusive ✓
- `api/controllers/console/platform_admin.py` — B3 exclusive ✓
- `api/controllers/console/enterprise_marketplace.py` — B4 exclusive ✓
- `api/services/enterprise_marketplace_service.py` — B4 exclusive ✓

未发现未分配所有者的共享文件。

**结果**: **VERIFIED_CLOSED**

---

#### FIX-03: 缺少最终 enterprise Alembic head 的 revision ID

**原始问题**: 计划多处提到 merge revision 但未指定 ID 和文件名。

**整改内容**: `OFFICIAL_RELEASE_ANALYSIS.md §4` 预分配两个 revision ID，并附唯一性证据。

**Git 对象唯一性独立验证**:

```bash
# 官方 1.16.0 标签
$ git grep -n -e a71e16c0de01 -e b416e5c4e702 1.16.0 --
EXIT:1   # 无匹配 ✓

# 旧企业候选分支
$ git grep -n -e a71e16c0de01 -e b416e5c4e702 origin/codex/enterprise-candidate-1.15.0-20260626 --
EXIT:1   # 无匹配 ✓

# 1.16.0 中全部已有 migration 文件名
$ git show 1.16.0:api/migrations/versions/ | grep -E 'a71e16c0de01|b416e5c4e702'
(无匹配) ✓
```

**格式验证**:

| 项目 | 值 | 符合约定？ |
| --- | --- | --- |
| Merge revision ID | `a71e16c0de01` | 12 位 hex，与 Dify 一致 ✓ |
| Final head ID | `b416e5c4e702` | 12 位 hex，与 Dify 一致 ✓ |
| Merge 文件名 | `2026_07_21_1000-a71e16c0de01_merge_1_16_0_enterprise_heads.py` | 格式 `YYYY_MM_DD_HHMM-ID_desc.py` ✓ |
| Final schema 文件名 | `2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py` | 同上格式 ✓ |

**职责验证**:

- 空 merge `a71e16c0de01` — 仅连接历史分支，无 DDL ✓
- 最终 head `b416e5c4e702` — 独占 1.16 智慧广场列/索引/约束/数据迁移 ✓
- 当前阶段只预分配，不创建 migration 文件 — ✓

**注意**: 在当前 refs (`ctyun/replay-116-architect`、`ctyun/replay-116-reviewer2`、`codex/enterprise-candidate-1.16.0-20260718`) 中 grep 会匹配到——因为这些 ref 包含整改文档本身。这是预期行为，不影响唯一性：在官方 `1.16.0` 标签和旧企业候选 `origin/codex/enterprise-candidate-1.15.0-20260626` 中均无匹配。

**结果**: **VERIFIED_CLOSED**

---

### P1 复审

#### FIX-04: B2 重建旧 revision 的方法未明确

**原始问题**: 三种实现方式（复制/重写/stamp），文档未指明用哪种。

**整改内容**: 在三个文档中明确方法为复制并保持原始属性不变。

- `ENTERPRISE_REPLAY_PLAN.md:62`: "从旧企业候选恢复...保持 revision ID、down_revision、branch_labels 和 upgrade()/downgrade() 历史 DDL 语义；不得重新生成 ID，不得用 alembic stamp 伪造状态"
- `PATCH_DECISION_MATRIX.md E15`: "B2 从旧候选恢复历史文件，保持 revision、down_revision、branch_labels 和 upgrade()/downgrade() 历史 DDL 语义...不得重建新 ID、修改历史语义或用 alembic stamp 伪造状态"
- `VALIDATION_PLAN.md Phase D`: "文件从旧企业候选恢复并保持 revision ID、down_revision、branch_labels、upgrade()/downgrade() 历史 DDL 语义。不得重新生成 ID，不得使用 alembic stamp 伪造升级状态"

**结果**: **VERIFIED_CLOSED**

---

#### FIX-05: PostgreSQL 18 migration 兼容性验证

**原始问题**: uuidv7 migration `1c9ba48be8e4` 在 1.16 修改以兼容 PG18，验证矩阵未覆盖。

**整改内容**: `VALIDATION_PLAN.md Phase D` 新增完整 PG18 矩阵。

**验证**:

| 级别 | 场景 | 状态 |
| --- | --- | --- |
| 必须运行 | PostgreSQL 18 空库 | 包含 `SELECT uuidv7()` 且 UUID version 为 7 ✓ |
| 必须运行 | PostgreSQL 18 应用升级 | PG18 兼容路径有效 ✓ |
| 条件运行 | PG 大版本升级 + Dify 升级同窗口 | 独立高风险场景，不得用分开升级代替 ✓ |

- 默认拆分 DB 大版本升级与 Dify 应用升级 — ✓
- `OFFICIAL_RELEASE_ANALYSIS.md:56` 明确提及 `1c9ba48be8e4` 修改事实 — ✓
- 矩阵显式标注“必须运行”与“条件运行”，不会混淆“计划”与“已执行” — ✓
- 文档首段 ("本计划用于后续 Builder...当前架构任务不修改代码、不启动 Docker") — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-06: DIFY_AGENT_INNER_API_KEY == INNER_API_KEY_FOR_PLUGIN 显式断言

**原始问题**: 缺少 Compose config 展开后的显式相等断言。

**整改内容**: `VALIDATION_PLAN.md Phase E` 写入详细验证步骤。

**验证**:

- 使用 `docker compose config` 最终展开结果 — ✓
- 写入权限 `0600` 的临时文件 — ✓
- 用 YAML parser 读取并按字段路径作显式相等断言 — ✓
- 比较的是 fallback 展开后的最终值，不是变量名/模板文本 — ✓
- 输出只记录 `equal=true/false`，不打印值 — ✓
- Phase G 必须证明 agent backend 调用 Dify inner API 成功 — ✓
- 临时文件安全清理，不进日志/CI artifact/manifest/仓库 — ✓

安全防护措施充分，无 secret 暴露风险。

**结果**: **VERIFIED_CLOSED**

---

#### FIX-07: Agent App 具体测试场景

**原始问题**: 验证计划 Agent App 只有 5 条高层面描述，缺少复现步骤和失败判定。

**整改内容**: `VALIDATION_PLAN.md Phase G` 将 Agent App Beta 验证扩展为 12 场景统一表格。

**场景覆盖验证**:

| 场景 | 前置数据 | UI/API | HTTP/字段 | 页面 | 失败 | 截图/日志 |
| --- | --- | --- | --- | --- | --- | --- |
| roster Agent | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Skills | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 文件 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Knowledge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tools | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 发布 Web App | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 最终用户对话 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Workflow roster Agent | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| inline Agent | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| agent_backend 停止 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 超时/重连/取消/清理 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Landlock 边界 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 两套 secret token 隔离 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**API 路径警告验证**:

文档明确标注：
> "HTTP 路径以本提交生成的 Console OpenAPI 为准；下表列出的 /console/api 路径必须与生成 contract 对齐，若路径或响应 schema 漂移必须更新本表后再执行，不能临场猜测。"

路径被标记为需要与生成 OpenAPI 对齐，不是绝对事实。通过。

**结果**: **VERIFIED_CLOSED**

---

#### FIX-08: 离线包缺少 DIFY_AGENT_SERVER_SECRET_KEY 非默认检查

**原始问题**: 开发默认 key 可能进入可运行生产配置。

**整改内容**: `VALIDATION_PLAN.md Phase H` 建立三层防护。

**验证**:

1. 真实 secret 禁入包 — ✓ (明确声明)
2. 开发默认值只能出现在 example，带显眼 `WARNING: DEVELOPMENT ONLY, REPLACE IN PRODUCTION` — ✓
3. 默认 key 无 WARNING 或进入可运行配置时阻断发布 — ✓
4. 生产安装生成全新随机 secret，写入不打包、不记录日志的 secret store — ✓
5. 安装脚本证据只记录布尔结果和指纹，不记录 secret — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-09: Secret 扫描覆盖范围与方法

**原始问题**: "key 不进日志"是一条规则但缺验证方法。

**整改内容**: `VALIDATION_PLAN.md` 新增独立 "Secret 扫描" 节。

**扫描范围验证**:

| 目标 | 覆盖？ |
| --- | --- |
| API stdout/stderr | ✓ |
| worker stdout/stderr | ✓ |
| api_websocket stdout/stderr | ✓ |
| plugin daemon stdout/stderr | ✓ |
| agent backend stdout/stderr | ✓ |
| local sandbox stdout/stderr | ✓ |
| Web 可访问日志 | ✓ |
| Compose 最终展开结果 | ✓ |
| 离线包 manifest | ✓ |
| 安装脚本 stdout/stderr | ✓ |

**安全方法验证**:

- Pattern 文件构造来源：从受保护运行环境读取，`0700` 临时目录 — ✓
- 文件权限：`0600` — ✓
- CLI/日志暴露：禁止 secret 进入命令参数、shell trace、日志、仓库、CI artifact — ✓
- 输出脱敏：只输出 "目标 + 是否命中"，命中内容脱敏 — ✓
- 安全清理：pattern、Compose 展开结果和中间日志扫描后全部清理 — ✓
- 开发默认 pattern 扫描：报告位置和分类，不记录生产值 — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-10: 五个 runtime image ID 显式检查

**原始问题**: Phase F 未显式枚举 `api_websocket`，tag 相同可能掩盖 ID 不同。

**整改内容**: `VALIDATION_PLAN.md Phase F` 显式枚举五个容器。

**验证**:

```text
api, worker, worker_beat, api_websocket -> same enterprise API image ID
web -> current enterprise Web image ID
```

- 使用 `docker inspect` 读取不可变 `.Image` ID — ✓
- 断言 `api == worker == worker_beat == api_websocket` — ✓
- Web 等于企业 Web image ID（不要求等于 API image ID）— ✓
- "tag 文本相同不能代替 image ID 相等" — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-19: Volume 升级回滚步骤与 retention/sandbox 持久化

**原始问题**: 回滚步骤未定义；Agent run retention 和 sandbox 持久化未明确。

**整改内容**: `VALIDATION_PLAN.md §3` 新增 "唯一受支持的回滚方法"。

**回滚步骤验证**:

1. 停止 1.16 服务并阻止写入 — ✓
2. 隔离已迁移的数据库、storage、Redis、plugin、vector volume — ✓
3. 从完整一致性备份恢复到新目标 — ✓
4. 恢复 1.15 配置与镜像 — ✓
5. 启动 1.15 并验证数据 — ✓
6. 对照 inventory/抽样哈希确认恢复完整 — ✓

**禁止项验证**:

- 禁止 Alembic downgrade — ✓
- 禁止在已迁移 volume 上启动 1.15 — ✓
- 禁止默认回灌 1.16 新数据到 1.15 — ✓

**Agent retention/sandbox 验证**:

- Agent run retention 默认 3 天（259200 秒），允许部署覆盖 — ✓
- local sandbox 默认不持久化，企业 overlay 禁止增加永久共享 volume — ✓
- Redis DB 编号冲突检查 — ✓

**恢复对象完整性**: 账户、workspace/member、应用、工作流、知识库、插件、上传文件、向量数据 — ✓

**结果**: **VERIFIED_CLOSED**

---

### P2 复审

#### FIX-11: uuidv7 migration 是第 4 个 modified migration

**验证**: `OFFICIAL_RELEASE_ANALYSIS.md:56` 和 `VALIDATION_PLAN.md Phase D` 均明确 5A+4M 且提及 `1c9ba48be8e4` 为第 4 修改。

**结果**: **VERIFIED_CLOSED**

---

#### FIX-12: Agent App checklist 结构化

**验证**: `VALIDATION_PLAN.md Phase G` 已有 12 场景统一表格，每场景包含全部 7 列。每条路径要求与生成 contract 对齐。

**结果**: **VERIFIED_CLOSED**

---

#### FIX-13: B3→B4→B5 串行

**验证**:
- `ARCHITECT_HANDOFF.md §6`: "B3/B4 不并行：B3 合并形成平台管理员鉴权基础后，B4 才开始" — ✓
- `ENTERPRISE_REPLAY_PLAN.md §5`: "B3、B4 不并行，B5 不自行重新生成 contract" — ✓
- contracts 唯一生成者 B4 — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-14: Collaboration profile 保留 api_websocket + Redis DB 编号

**验证**:
- `VALIDATION_PLAN.md Phase E`: `--profile collaboration config --services` + api_websocket 存在检查 — ✓
- 解析所有 Redis URL database 编号并断言 agent backend 不冲突 — ✓
- `ARCHITECT_HANDOFF.md B6 ownership`: 包含 profile/Redis 静态断言 — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-15: i18n 使用 platformAdmin.* 和 enterpriseMarketplace.*

**验证**:
- `ARCHITECT_HANDOFF.md B5`: "i18n 唯一命名空间：平台管理员使用 platformAdmin.*，智慧广场使用 enterpriseMarketplace.*" — ✓
- B5 独占两份 common.json，后端 Builder 不预写 — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-16: B9 截止 B6 开始前

**验证**:
- `ENTERPRISE_REPLAY_PLAN.md §5`: "B9（澄清）必须在 B6 开始前截止" — ✓
- `PATCH_DECISION_MATRIX.md E06`: "产品契约最迟在 B6 开始前给出" — ✓
- `ARCHITECT_HANDOFF.md B9`: "最迟 B6 开始前结论" — ✓
- 若产生实现，B10 经独立安全/架构评审，B8 前完成 — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-17: MySQL marketplace DDL 真实数据库验证

**验证**:
- `VALIDATION_PLAN.md Phase D`: MySQL 空库与企业升级均为 必须运行 — ✓
- `SHOW CREATE TABLE` 验证 JSON 列、created_at/updated_at 默认值、索引、约束 — ✓
- DDL 验证列入证据要求 — ✓

**结果**: **VERIFIED_CLOSED**

---

#### FIX-18: CAN_REPLACE_LOGO 官方默认 false；OpenAI Responses API；SSRF

**验证**:
- CAN_REPLACE_LOGO: `OFFICIAL_RELEASE_ANALYSIS.md §3` 说明修正 + `VALIDATION_PLAN.md Phase E` 检查最终值 — ✓
- OpenAI Responses API: `VALIDATION_PLAN.md Plugin` 节检查升级后的 API type 并验证模型调用 — ✓
- 智慧广场 SSRF: `PATCH_DECISION_MATRIX.md E04` + `VALIDATION_PLAN.md` 均要求走官方 SSRF proxy/helper，含 loopback/link-local/私网 fixture — ✓

**结果**: **VERIFIED_CLOSED**

---

## 8. P0 remaining

**0**

FIX-01、FIX-02、FIX-03 均已 VERIFIED_CLOSED。

## 9. P1 remaining

**0**

FIX-04、FIX-05、FIX-06、FIX-07、FIX-08、FIX-09、FIX-10、FIX-19 均已 VERIFIED_CLOSED。

## 10. P2 remaining

**0**

FIX-11～FIX-18 均已 VERIFIED_CLOSED。

## 11. 新增发现

以下为独立审查中识别的新问题，未出现在原始 Review 的 19 个 FIX 项中：

### 11.1 B3 若需要新增 Model 将受限于 Forbidden Paths (LOW)

**描述**: B3 的 Forbidden paths 包括 `api/models/__init__.py` 和 `api/models/model.py`。如果平台管理员首版需要审计日志表或额外 model，B3 无法自建。

**影响**: 当前计划假设 B3 仅使用现有 Account/Tenant 等 model 完成授权逻辑。若产品需求要求审计表，需在 B3 开始前或通过 B4 协调扩展 allowlist。

**建议**: 在 B3 开始前确认平台管理员不需要新建 model。若需要，改为 B4 定义 model（或 B3 追加独立 audit model 文件并经 B4 注册）。

**级别**: P2

---

### 11.2 Agent App Beta 表格中的 API 路径未标注为示例/猜测 (LOW)

**描述**: `VALIDATION_PLAN.md Phase G` 的 Agent App Beta 表格中列出了 13 个具体 API 路径（如 `/console/api/agent`、`/console/api/agent/{agent_id}/config/skills/upload` 等）。文档已注明"必须与生成 contract 对齐，...不能临场猜测"——但表格本身未在每行路径旁标注它们仅是预期路径模板。

**影响**: Builder 或验证者可能误以为这些路径已是最终事实。当前警告在表格前，足够明确；但每个路径行缺少 `[EXPECTED - verify with OpenAPI]` 标记。

**建议**: 在表格中每个路径后追加 `（与生成 OpenAPI 对齐后确认）`，或将路径列标题改为 `期望路径 (须与 OpenAPI 对齐)`。

**级别**: P2

---

### 11.3 api/configs/enterprise/__init__.py 未分配所有者 (LOW)

**描述**: `api/configs/enterprise/__init__.py` 是 Dify 中控制企业特性启用的配置文件。在 1.15 企业候选中使用过，但当前所有权矩阵未覆盖。B3 的 allowlist 包含 `api/configs/feature/__init__.py`（用于 PLATFORM_ADMIN_EMAILS），但不包含 `api/configs/enterprise/__init__.py`。B6 的允许范围是 Docker overlay，不含 API 配置。

**影响**: 如果 1.16 的企业特性启用需要后端代码调整（如 `ENTERPRISE_ENABLED`），缺少明确所有者可能导致该文件被跳过或由非预期 Builder 修改。

**建议**: 明确该文件的读写策略——若无需修改则记录为 Read-only；若需修改则指定所有者。

**级别**: P2

---

### 11.4 B4 如何发现 B3 路由以统一注册 (MEDIUM)

**描述**: B4 负责统一注册 B3 和 B4 的 Console endpoint 到 `api/controllers/console/__init__.py`，并统一生成 OpenAPI contracts。但 B3 的 allowed write paths 中不包括 controller 注册文件。B4 需要能够 introspect B3 的 route definitions（位于 `api/controllers/console/platform_admin.py`）来正确注册并纳入 contract generation。

**影响**: 如果 Dify 的 Console OpenAPI 生成依赖于 `__init__.py` 中的显式 import/registration，B4 需要知道 B3 定义了哪些 routes 和 schemas。当前 handoff 说 B3 "向 B4 提交 route/schema generation 需求"——但这个 handoff 是文档化的还是代码级的，未明确。

**当前缓解**: 因为 B3 在 B4 开始前已合并，B4 可以直接读取 B3 的源码文件。在 Dify 的架构中，route 定义文件独立于 `__init__.py` 的 blueprint 注册。B4 只需 import B3 的 controller 并注册 blueprint。可行。

**建议**: 不需要代码更改，但建议在 handoff 中明确 B4 对 B3 controller 的 import 模式。

**级别**: P2

---

## 12. Design Gate 仍需人工确认的事项

以下事项在整改中已明确标注为 Builder 前 Design Gate，不属于 Reviewer-2 可关闭：

| 编号 | 事项 | 当前状态 | 阻止 Builder 启动？ |
| --- | --- | --- | --- |
| DG-01 | 智慧广场发布时不可变快照 vs 动态引用：产品/历史业务事实是否冲突 | Architect 推荐不可变快照；设为人工 Design Gate | 是 |
| DG-02 | 平台管理员首版是否必须支持密码重置和 workspace 归档 | 高风险操作延后（无审计不交付）；需产品确认 | 否（密码重置/归档可延后） |
| DG-03 | 企业会话管理精确定义 | DEFER；产品契约截止 B6 开始前 | 否（B6 才截止） |
| DG-04 | 目标远端候选分支引用确认 | 维护者确认它指向官方基线 | 是 |
| DG-05 | 旧企业 `enterprise_marketplace_assets` 是否存在生产数据/非标准 schema | 迁移前需只读 inventory | 否（B2/B4 迁移前即可完成） |
| DG-06 | Agent run retention 产品是否要求不同于官方 3 天 | 默认官方 3 天；B6 前明确 | 否（有默认值，B6 前确认） |
| DG-07 | `CAN_REPLACE_LOGO` 企业产品预期 | 官方默认 `false`；若需 `true` 则显式配置 | 否（有默认值） |

## 13. 最终 Verdict

**PASS**

### PASS 条件逐一验证

| 条件 | 状态 |
| --- | --- |
| P0 remaining = 0 | ✓ |
| P1 remaining = 0 | ✓ |
| P2 均已关闭或有可接受 disposition | ✓ (FIX-11～FIX-18 全部 VERIFIED_CLOSED) |
| 没有新增 P0/P1 | ✓ (新增发现均为 P2) |
| 原始 Review 未修改 | ✓ (ARCHITECT_REVIEW.md 逐字未变) |
| 整改只涉及允许文档 | ✓ (仅 5 个允许文档) |
| Builder 文件所有权和顺序可执行 | ✓ |
| volume 升级/回滚计划可执行 | ✓ |
| 不存在安全回退 | ✓ (官方安全修复未回退) |
| 不存在把未执行测试写成已通过 | ✓ (所有验证均为计划步骤，使用将来时态) |

## 14. 是否允许进入人工 Design Gate

**允许**。3 个 P0、8 个 P1、8 个 P2 均已 VERIFIED_CLOSED。剩余 7 个 Design Gate 事项已明确列出，其中 DG-01 和 DG-04 必须在 Builder 启动前确认。

## 15. 是否允许启动 Builder

**不允许自动授权**。即使 Verdict 为 PASS，仍必须经过人工 Design Gate（尤其是 DG-01 智慧广场不可变快照决定和 DG-04 候选分支确认）后才能启动 Builder。本轮复审结论为 PASS 意味着计划在技术上无歧义、无矛盾，但产品事实确认仍是 Builder 启动的前置条件。

---

## 附录 A: 复审方法

1. `git branch --show-current && git rev-parse HEAD && git status --short && git log -4 --oneline --decorate` — 确认分支和 HEAD
2. `git diff caedca07e4..2af616e7e2 --stat` — 确认修改文件范围
3. `git diff caedca07e4..2af616e7e2` — 逐行审查所有整改变更
4. `git diff caedca07e4..2af616e7e2 -- ARCHITECT_REVIEW.md` — 确认原始 Review 未修改
5. `git grep -e a71e16c0de01 -e b416e5c4e702 1.16.0 --` — 验证 revision ID 在官方标签中唯一
6. `git grep -e a71e16c0de01 -e b416e5c4e702 origin/codex/enterprise-candidate-1.15.0-20260626 --` — 验证在旧企业候选中的唯一性
7. 全文阅读 5 份整改文档及原始 ARCHITECT_REVIEW.md，交叉引用比对
8. 独立分析 Builder 任务所有权矩阵的可执行性
9. 独立审查 volume 升级/回滚计划的完整性

**复审完整性声明**: 未修改任何业务代码、Docker、migration、依赖、版本号或 `docker/volumes`。未启动 Docker。未访问、复制或修改运行数据。

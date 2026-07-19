# Dify Enterprise 1.16.0 Architect Review

## 1. 审查对象

| 项目 | 值 |
| --- | --- |
| 审查日期 | 2026-07-19 |
| 审查基线 commit | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| 审查目标 commit | `4fa0d53d49b9a77123e0c152e55a2c9262189c15` |
| 审查分支 | `ctyun/replay-116-reviewer` |
| 待审查文档 | `ENTERPRISE_REPLAY_PLAN.md`, `OFFICIAL_RELEASE_ANALYSIS.md`, `PATCH_DECISION_MATRIX.md`, `VALIDATION_PLAN.md`, `ARCHITECT_HANDOFF.md` |
| 旧企业基线 | `origin/codex/enterprise-candidate-1.15.0-20260626` (`b3af6ec907`) |

## 2. 审查结论

| Verdict | 说明 |
| --- | --- |
| **CHANGES_REQUIRED** | 架构方向正确，PATCH_DECISION_MATRIX 分类基本准确，但存在 2 个 P0 阻断项和 7 个 P1 整改项。P0 解决前不能进入 Builder 阶段。 |

### 发现数量

| 级别 | 数量 |
| --- | --- |
| P0 阻断 | 3 |
| P1 必须整改 | 7 |
| P2 建议优化 | 7 |

## 3. P0 阻断项

### P0-1: B2/B4 循环依赖 — migration schema 定义与实现时序倒置

- **严重级别**: P0 — 阻塞 Builder 启动
- **文档位置**: `ENTERPRISE_REPLAY_PLAN.md:62-65`, `ARCHITECT_HANDOFF.md:54-58, 66-70`
- **代码/提交依据**:
  - B2 任务描述：`审计重建 c8f3d9d4a1be、f1a14e1e9b41、e2f0a9b7c6d5 的历史可解析性。定义最终智慧广场 schema；新增连接旧企业 head 与官方 7a1c2d9e4b60 的 merge。`
  - B4 任务描述：`提交/审核/发布/下架/复制状态机、生成 contract...先决决策：发布时生成不可变快照`
  - 依赖图：`B0 → B2 → B4`
- **问题**:
  B2 必须产出"最终智慧广场 schema"并创建 merge migration，但那个 schema 的最终设计信息要等 B4 完成才知道。
  如果 B4 为了支持"不可变快照 vs 动态引用"的设计决策需要新增列（如 `snapshot_dsl`、`snapshot_version` 或 `source_app_frozen_at`），
  B2 提供的 migration 就会过期，必须重新生成。这会迫使 B2 要么猜一个 schema（导致返工），要么等 B4 完成（打破依赖图）。

  当前旧企业的 `enterprise_marketplace_assets` 表（migration `c8f3d9d4a1be`）只有基础字段，不包含快照支持。B4 的设计必然后影响 schema。
- **整改要求**:
  - B2 只负责：重建旧 revision（`c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5`）的可解析性，并新增一个空 merge revision 连接 `e2f0a9b7c6d5` 与官方 `7a1c2d9e4b60`。
  - B4 负责：定义 marketplace 完整 schema（含任何新列/索引），并在其自身 migration 文件中完成 DDL。
  - 或者反转顺序：先确认 B4 schema 设计决策（对齐产品方"快照 vs 引用"问题），再做 B2。两种方案必须二选一，不得猜 schema。
- **验证方式**: 检查 B2 migration 中除了 merge 和旧表重建之外的 DDL 是否归 B4 所有。

### P0-2: 缺少 Builder 任务文件范围与重叠矩阵

- **严重级别**: P0 — 阻塞 Builder 分配
- **文档位置**: `ENTERPRISE_REPLAY_PLAN.md:46-111`, `ARCHITECT_HANDOFF.md:39-100`
- **问题**:
  计划未为每个 Builder 任务列出具体允许修改的文件/目录范围。以下文件存在跨 B 任务重叠风险：

  | 文件 | 潜在冲突 B 任务 | 冲突类型 |
  | --- | --- | --- |
  | `api/controllers/console/__init__.py` | B3 + B4 | 都需要注册 blueprint/route |
  | `api/models/model.py` | B2 + B3 + B4 | B2 需注册 marketplace model；B3 可能需审计 model；B4 需 marketplace model |
  | `api/models/__init__.py` | B2 + B4 | model 导入注册 |
  | `web/app/components/header/account-setting/` | B5 | B5 内部可能多个子组件 |
  | `web/app/components/main-nav/` | B5 | B5 内部多个子组件 |
  | `docker/docker-compose.enterprise.yaml` | B6 + B7 | B6 定义 overlay；B7 基于 overlay 做离线脚本 |
  | `api/configs/feature/__init__.py` | B3 | 需新增 `PLATFORM_ADMIN_EMAILS` 配置 |
  | `packages/contracts/` | B3 + B4 + B5 | B3/B4 生成 contract；B5 消费 |
  | `web/i18n/en-US/common.json` | B5 | 集中式 i18n 文件易冲突 |
  | `web/i18n/zh-Hans/common.json` | B5 | 同上 |

- **整改要求**:
  为每个 B 任务列出明确的允许文件/目录清单。对重叠文件：
  - `api/controllers/console/__init__.py`: 只允许 B3 或 B4 之一修改，另一任务向其提交接口需求；或拆为串行 B3→B4。
  - `api/models/__init__.py` 和 `api/models/model.py`: B2 先建立 model + 历史 migration；B4 在 B2 合并后在其基础上新增。
  - `packages/contracts/`: 必须是 build artifact，由最后执行的 B 任务统一 regenerate。
  - `web/i18n/`: B5 内部按功能模块拆 key range（如 `platformAdmin.*`, `enterpriseMarketplace.*`），或用独立 i18n namespace 文件；禁止两个开发者同时编辑同一 JSON 文件。
  - 在上述重叠矩阵基础上，额外审查 B3 与 B4 的 contract 消费关系：B4 的审核依赖平台管理员鉴权，该鉴权 helper/service 应归 B3 独有，B4 只 import。
- **验证方式**: 为每个 B 任务维护 `ALLOWED_FILES.txt` 或 CI diff owner check；未声明的文件不得出现在该 B 任务 diff 中。

### P0-3: 缺少最终 enterprise Alembic head 的 revision ID

- **严重级别**: P0 — 阻塞 migration 实现
- **文档位置**: `OFFICIAL_RELEASE_ANALYSIS.md:57-59`, `PATCH_DECISION_MATRIX.md:213-223 (E15)`, `VALIDATION_PLAN.md:73-97`
- **问题**:
  计划多处提到要"新增一个连接 `e2f0a9b7c6d5` 和 `7a1c2d9e4b60` 的 merge revision"，但未指定新 revision 的 ID 和文件名。
  Alembic revision ID 必须唯一且在全历史链中可引用。若不预先分配，B2、B4、E15 的验证和测试代码无法编写断言。
- **整改要求**:
  在计划中预分配一个唯一的 revision ID，格式遵从 Dify 约定（如 `2026_07_20_1000-a1b2c3d4e5f6_merge_1_16_0_enterprise_heads.py`）。
  同时确认：
  - 这个 merge 的两个 parent 分别是 `e2f0a9b7c6d5`（旧企业 head）和 `7a1c2d9e4b60`（官方 1.16 head）。
  - 该 merge 是否为最终企业 head。如果 B4 需要新增 migration 修改 schema，必须在 merge 之后追加独立 revision，不得修改 merge 本身。
- **验证方式**: `uv run --project api flask db heads` 输出唯一 head 且 revision ID 匹配。

## 4. P1 必须整改项

### P1-1: B2 重建旧 revision 的方法未明确

- **严重级别**: P1
- **文档位置**: `PATCH_DECISION_MATRIX.md:213-223 (E15)`, `ARCHITECT_HANDOFF.md:54-58 (B2)`
- **代码/提交依据**:
  - 旧 `c8f3d9d4a1be` 创建 `enterprise_marketplace_assets` 表（含 18 列、3 索引）。
  - 旧 `f1a14e1e9b41` 空 merge（parent: `a4f2d8c9b731`, `c8f3d9d4a1be`）。
  - 旧 `e2f0a9b7c6d5` 空 merge（parent: `f1a14e1e9b41`, `d9e8f7a6b5c4`）。
- **问题**:
  E15 说"审计重建历史 revision 可解析性"但没说 HOW。三种实现方式后果不同：
  - (a) 复制旧文件并只更新 import paths → 保持 revision ID 不变，旧库可升级。
  - (b) 重写为新 migration → revision ID 变化，旧库的 `alembic_version` 找不到 `e2f0a9b7c6d5` → 崩溃。
  - (c) 用 stamp 手动标记 → 禁止操作，风险极高。
  当前 B2 实施者会误选 (b)，导致旧企业数据库无法升级。
- **整改要求**:
  明确 B2 必须使用方式 (a)：复制旧文件到新工作树，保持 revision ID、`down_revision` 和 `branch_labels` 不变。
  仅允许：
  - 更新文件中的 import（如 `import models` → `import models as models` 或保持原样）。
  - 保持 `upgrade()`/`downgrade()` 内容不变。
  三者关系必须在迁移链测试中验证：`c8f3d9d4a1be ← f1a14e1e9b41 ← e2f0a9b7c6d5`。
- **验证方式**: `uv run --project api flask db history` 包含 `e2f0a9b7c6d5 -> 7a1c2d9e4b60 (mergehead)` 路径，且旧企业升级不报 "Can't locate revision"。

### P1-2: 验证计划缺少 PostgreSQL 18 migration 兼容性检查

- **严重级别**: P1
- **文档位置**: `VALIDATION_PLAN.md:73-97 (Phase D)`, `OFFICIAL_RELEASE_ANALYSIS.md:47-55`
- **代码/提交依据**:
  - `1c9ba48be8e4` (uuidv7 function) 在 1.16 中修改为兼容 PostgreSQL 18 原生 uuidv7()。
  - `git diff 1.15.0..1.16.0 -- api/migrations/versions/2025_07_02_2332-1c9ba48be8e4_add_uuidv7_function_in_sql.py` 返回 `M`（已修改）。
  - 该 migration 不在 Release 的 8 项列表中，但属于 1.15.0→1.16.0 的实际差异。
  - OFFICIAL_RELEASE_ANALYSIS.md:47 只提到 "PostgreSQL 18 还要保留官方 uuidv7 migration 测试" 但未在验证矩阵中展开。
- **问题**:
  如果旧企业数据库在 PostgreSQL < 18 升级后切换到 PostgreSQL 18，uuidv7 函数可能不存在或签名不兼容。
  企业 migration 验证矩阵（空库/官方 1.15/企业 1.15/官方 1.16）未覆盖"PG 版本变化"这一维度。
- **整改要求**:
  在 Phase D 验证矩阵中增加：对旧企业升级路径，验证 PG <18 → PG 18 和 PG 18 原地升级两条子路径。
  至少在一个路径确认 uuidv7 函数存在且被使用。
- **验证方式**: 升级后执行 `SELECT uuidv7()` 不报错，且在 PG 18 上返回 native uuidv7 结果。

### P1-3: DIFY_AGENT_INNER_API_KEY 与 INNER_API_KEY_FOR_PLUGIN 一致性缺少显式断言

- **严重级别**: P1
- **文档位置**: `OFFICIAL_RELEASE_ANALYSIS.md:21-22`, `VALIDATION_PLAN.md:122`
- **代码/提交依据**:
  官方 Compose:
  ```
  INNER_API_KEY_FOR_PLUGIN: ${PLUGIN_DIFY_INNER_API_KEY:-QaHbTe77CtuXmsfyhR7+vRjI/+XbV1AaFy691iy+kGDv2Jvy0/eAh8Y1}
  DIFY_AGENT_INNER_API_KEY: ${DIFY_AGENT_INNER_API_KEY:-${PLUGIN_DIFY_INNER_API_KEY:-QaHbTe77CtuXmsfyhR7+vRjI/+XbV1AaFy691iy+kGDv2Jvy0/eAh8Y1}}
  ```
  两者最终都源自 `PLUGIN_DIFY_INNER_API_KEY`，但 `DIFY_AGENT_INNER_API_KEY` 可被单独覆盖。
- **问题**:
  VALIDATION_PLAN.md:122 说"DIFY_AGENT_INNER_API_KEY 来源与 INNER_API_KEY_FOR_PLUGIN 一致"但缺少 Compose config 后的显式 assert。
  如果企业 overlay 或运维单独设置了 `DIFY_AGENT_INNER_API_KEY` 为不同值（如误用 `INNER_API_KEY`），Agent backend 的 inner API 调用会失败，但服务仍健康启动。
- **整改要求**:
  在 Phase E Compose 静态验证中增加：执行 `docker compose config` 并断言 `agent_backend` 的 `DIFY_AGENT_INNER_API_KEY` 值与 `api` 的 `INNER_API_KEY_FOR_PLUGIN` 值相同（包括 fallback 链解析）。
  在 Phase G 集成验证中增加：Agent backend 调用 Dify inner API 的 success case。
- **验证方式**: Compose config 输出中两变量值一致；运行时 Agent Smoketest 通过。

### P1-4: 验证计划未覆盖 Agent App 的具体测试场景

- **严重级别**: P1
- **文档位置**: `VALIDATION_PLAN.md:169-175 (Agent App Beta)`
- **问题**:
  VALIDATION_PLAN.md 的 Agent App 验证只有 5 条高层面描述：
  - 新建 roster Agent，配置 model/Skills/files/tools/knowledge，发布为 Web App 并对话。
  - 工作流引用 roster Agent；创建 inline Agent；输出传递正确。
  - shell 命令和文件操作在 Landlock 边界内；越界读取/写入失败。
  - Agent backend 断线/超时/重连/取消/失败清理可观测。
  - `DIFY_AGENT_SERVER_SECRET_KEY` 非默认，stub token 可用且不能跨部署复用。

  这些描述缺少可复现的操作步骤、期望结果和失败判定标准。例如：
  - "断线/超时/重连" 如何模拟和观察？
  - stub token 如何验证"不能跨部署复用"？
  - Skill 安装失败时 Agent 的状态如何？

- **整改要求**:
  对每类 Agent App 场景补充：
  - roster Agent 创建流程（model 选择、Skills 安装、file 上传、knowledge 接入、Web App publish、end-user conversation）。
  - inline Agent 在工作流中的输入/输出 schema 验证。
  - Landlock：验证 Shell 命令在当前目录文件可读，`/etc/passwd` 不可读。
  - Failure 路径：停止 agent_backend 容器后，API 返回正确错误码且不 crash。
  - `DIFY_AGENT_SERVER_SECRET_KEY` 跨部署：用两套不同 key 的部署验证 stub token 互不可用。

- **验证方式**: 每个场景输出 pass/fail + 截图/日志摘录。

### P1-5: 离线包验证缺少 DIFY_AGENT_SERVER_SECRET_KEY 的非默认检查

- **严重级别**: P1
- **文档位置**: `VALIDATION_PLAN.md:192-201 (Phase H)`, `OFFICIAL_RELEASE_ANALYSIS.md:22`
- **代码/提交依据**:
  官方 Compose 中 `DIFY_AGENT_SERVER_SECRET_KEY` 默认值为 `MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY`（硬编码开发默认）。
  Release 明确要求生产替换：`python -c 'import secrets; print(secrets.token_urlsafe(32))'`
- **问题**:
  Phase H 离线包验证只有配置包内容扫描（"排除 `.env`、secret"），但未检查包内的 `.env.example` 文件是否仍含有开发默认 key。
  如果配置包提供 `dify-agent.env.example` 包含 `DIFY_AGENT_SERVER_SECRET_KEY=MDEyM...`，运维可能误以为该值可直接生产使用。
- **整改要求**:
  在 Phase H 中增加检查：
  - 搜索所有 `.env.example` 文件中是否包含 `MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY`（Agent server secret 开发默认）。
  - 搜索结果若非空，检查是否在注释中明确标注"DEVELOPMENT ONLY, REPLACE IN PRODUCTION"。
  - 如果 key 值未被替换且无标注，阻断发布。
- **验证方式**: `grep -r "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY" docker/envs/` 返回空或仅出现在有明确 WARNING 注释的上下文。

### P1-6: 日志输出要求不明确 — Agent key/Plugin key 不能进日志但未给出防止措施

- **严重级别**: P1
- **文档位置**: `VALIDATION_PLAN.md:231`
- **问题**:
  "Agent key/Plugin key 不进日志/manifest"是一条规则，但缺少验证方法。
  `DIFY_AGENT_INNER_API_KEY` 和 `PLUGIN_DAEMON_KEY` 可能在启动日志、错误日志或 plugin daemon stdout 中出现。
- **整改要求**:
  在 Phase G 运行验收中增加：
  - 启动后 grep 所有 service log 的 stdout/stderr，搜索已知 key 值（开发默认的 base64 pattern）。
  - 对 manifest 文件做同样的内容扫描。
  - 如果任一服务在 INFO 级别以上打印了这些 key，阻断。
- **验证方式**: `docker compose logs 2>&1 | grep -f known-keys-patterns.txt` 无匹配。

### P1-7: 验证计划未覆盖企业 WebSocket 使用企业镜像的运行时断言

- **严重级别**: P1
- **文档位置**: `VALIDATION_PLAN.md:99-114 (Phase E)`, `PATCH_DECISION_MATRIX.md:197-209 (E14)`
- **问题**:
  Phase E Compose 静态验证只检查 `api_websocket` 的 image tag 指向企业 API。但运行时可能存在容器使用旧镜像的情况（tag 重打但 ID 不同）。
  Phase F 有 image ID 检查但未显式列出 `api_websocket` 在 five-runtime 列表中。
- **整改要求**:
  Phase F 镜像构建与容器身份检查中，显式包含 `api_websocket` 在"五个 runtime 使用同一 image ID"的断言中。
  当前列表为 "api, worker, worker_beat, api_websocket, web(#137)"，但没有把 `api_websocket` 明确枚举。
- **验证方式**: `docker inspect <api_websocket_container> | jq '.[0].Image'` 与 api container 的 Image 字段一致。

## 5. P2 建议优化项

### P2-1: OFFICIAL_RELEASE_ANALYSIS.md 中 migration 修改文件数的表述可能引起歧义

- **严重级别**: P2
- **文档位置**: `OFFICIAL_RELEASE_ANALYSIS.md:53`
- **原文**: `三个在 1.15 已存在但 1.16 修改的 Agent migrations`
- **问题**: 实际 `1.15.0..1.16.0` 中有 4 个 M（Modified）文件：3 个 Agent 相关 + 1 个 uuidv7 (`1c9ba48be8e4`)。虽然此处只是说"Release 列表中前三个"，读者可能误以为总共只有 3 个修改。建议补上对 uuidv7 修改的说明。
- **整改**: 将第 53 行改为 `Release 列表中前三个 migration...已存在于 1.15.0`，并在同段或下一段说明 `此外 uuidv7 函数 migration 1c9ba48be8e4 也在 1.16 被修改以支持 PostgreSQL 18`。
- **验证**: 文档 grep 能找到 `1c9ba48be8e4` 的提及。

### P2-2: 验证计划应指定 Agent App E2E 的具体浏览器路径和 HTTP API 验证

- **严重级别**: P2
- **文档位置**: `VALIDATION_PLAN.md:169-175`
- **问题**: 缺少具体的 URL 路径、期望 HTTP 状态码、UI 元素选择器。后续验证者可能用不同理解执行测试。
- **整改**: 补充类似以下的结构化 checklist：
  ```
  1. POST /console/api/apps {mode: "agent"} → 201
  2. GET /console/api/apps/{id}/agent/roster → 200, agents[]
  3. POST /console/api/apps/{id}/agent/roster → 201
  4. PUT /console/api/apps/{id}/agent/roster/{agent_id} → 200
  5. GET /console/api/apps/{id}/agent/webapp → 200, agent_config
  6. Browser: /app/{id} → 加载 Web App → 发送消息 → 收到 agent 回复
  ```
- **验证**: 每个路径记录实际 HTTP 状态码和响应 schema。

### P2-3: Builder 合并顺序中 B3/B4 并行建议缺少同步点

- **严重级别**: P2
- **文档位置**: `ENTERPRISE_REPLAY_PLAN.md:113`, `ARCHITECT_HANDOFF.md:143-144`
- **问题**: B3 和 B4 被允许在 B2 后并行开发，但两者共享一些基础设施文件（如 controller blueprint 注册、model 导入）。缺少两者完成后的同步点（如 "B4 contract 发布后 B3 才能 merge" 或 "B3 先 merge，B4 在其上 rebase"）。
- **整改**: 在依赖说明中增加：B3 先 merge 到候选分支，B4 基于 merged result 开发 contract，或明确两者的 merge 顺序和 rebase 策略。
- **验证**: 检查 git log 中 B3 和 B4 的合并顺序与依赖说明一致。

### P2-4: 缺少企业 overlay profile 的保持验证

- **严重级别**: P2
- **文档位置**: `VALIDATION_PLAN.md:99-114 (Phase E)`, `PATCH_DECISION_MATRIX.md:113-126 (E08)`
- **问题**: 官方 Compose 使用 `profiles` 控制 collaboration 等可选服务。E08 要求"只覆盖最小字段"，但未提到保留官方 profile 定义。如果企业 overlay 重新声明了 `api_websocket` 的完整 service 块而不包含 `profiles: [collaboration]`，协作功能可能在 `docker compose up` 时不被启动。
- **整改**: 在 Phase E Compose 静态验证中增加：`docker compose config --profiles collaboration` 的输出中 `api_websocket` 服务仍然存在。
- **验证**: 带 collaboration profile 的 compose config 包含 `api_websocket`。

### P2-5: B5 前端任务未拆分 i18n key 命名空间

- **严重级别**: P2
- **文档位置**: `ARCHITECT_HANDOFF.md:72-77 (B5)`
- **问题**: B5 描述为"平台管理员和智慧广场前端"合并任务，两者共享 `web/i18n/*/common.json`。两个开发者可能编辑同一 JSON key 区间导致 merge conflict。
- **整改**: 明确 i18n key 命名空间：
  - 平台管理员: `platformAdmin.*`
  - 智慧广场: `enterpriseMarketplace.*`
  或者预先在 `common.json` 中预留 key 区间。
- **验证**: `git diff` 中 i18n 文件 diff 不包含同一行的冲突修改。

### P2-6: E06（会话管理）的 DEFER 状态缺少时间限制或升级条件

- **严重级别**: P2
- **文档位置**: `PATCH_DECISION_MATRIX.md:85-98 (E06)`, `ARCHITECT_HANDOFF.md:95-99 (B9)`
- **问题**: E06 被 DEFER 但无时间约束。如果产品方在 B8 发布前给出需求，架构审查需要重新评估。当前计划只说"B9 不阻塞 1.16 升级"，但未说如果 B9 产生新实现任务时如何融入已完成的任务链。
- **整改**: 增加时间约束：B9 的产品契约必须在 B6 开始前交付。如果 B9 产生实现任务，必须在 B8 发布门禁前完成独立安全审查并作为 B10 追加。
- **验证**: 检查 B9 澄清文档是否在 B6 开始前存在，及其结论。

### P2-7: MySQL 兼容性验证中缺少 marketplace migration 的具体 DDL 检查

- **严重级别**: P2
- **文档位置**: `VALIDATION_PLAN.md:96`
- **问题**: `c8f3d9d4a1be` 使用 `server_default=sa.text("CURRENT_TIMESTAMP")`，这在 PostgreSQL 中正常工作，但 MySQL 中 `CURRENT_TIMESTAMP` 只能用于一个 TIMESTAMP 列的默认值（除非指定 `DEFAULT CURRENT_TIMESTAMP` 且列类型为 `TIMESTAMP`）。该 migration 在两列（`created_at`, `updated_at`）上使用了此默认值，MySQL 上可能报错。
  此外，`sa.JSON()` 列在 MySQL 中等价于 `JSON` 类型（需要 MySQL 5.7.8+），旧 MySQL 版本可能回退到 `LONGTEXT`。
- **整改**: 在 Phase D 数据库矩阵的 MySQL 空库升级路径中，显式检查 `enterprise_marketplace_assets` 表 DDL 是否执行成功、列类型是否正确。
- **验证**: MySQL 空库升级后 `SHOW CREATE TABLE enterprise_marketplace_assets` 显示 `JSON` 类型和正确的默认值。

## 6. PATCH_DECISION_MATRIX KEEP 项抽查证据

### E01 — 企业默认工作区自动加入 → DROP_UPSTREAMED

| 检查项 | 结果 |
| --- | --- |
| 官方 1.16 是否有 `try_join_default_workspace` | **是**。`api/services/enterprise/enterprise_service.py:94`（1.16.0 版本） |
| 官方 1.16 是否有 `DefaultWorkspaceJoinResult` | **是**。同文件 `:73` |
| 官方实现是否包含 soft-fail | **是**。`try_join_default_workspace` 捕获异常并记录 warning |
| 结论 | **DROP 正确**。官方已完整覆盖 |

### E02 — 注册和创建工作区策略 → KEEP_MINIMAL_PATCH

| 检查项 | 结果 |
| --- | --- |
| 官方 1.16 是否有 `ALLOW_REGISTER` | **是**。`api/configs/feature/__init__.py` 中 `LoginConfig`，`default=False` |
| 官方 1.16 是否有 `ALLOW_CREATE_WORKSPACE` | **是**。同文件，`default=False` |
| 官方 1.16 是否有 `NEXT_PUBLIC_ALLOW_*` 前端配置 | **是**。`web/features/system-features/config.ts` |
| 旧企业补丁做了什么 | 在 `docker/docker-compose.enterprise.yaml` 中设置 `ALLOW_REGISTER: ${ALLOW_REGISTER:-false}` |
| 结论 | **KEEP_MINIMAL_PATCH 正确**。官方已有完整功能，企业只需 overlay 默认值。 |
| 风险提示 | Architect 提到的"仅设置后端或仅设置前端"不一致风险真实存在，必须在验证中覆盖 |

### E03 — 平台管理员 → KEEP_REQUIREMENT_REIMPLEMENT

| 检查项 | 结果 |
| --- | --- |
| 官方 1.16 是否有 `platform-admin` endpoint | **否**。`git grep -n 'platform.admin\|platform_admin' 1.16.0 -- api/` 无匹配 |
| 官方 1.16 是否有 `PLATFORM_ADMIN_EMAILS` 配置 | **否**。`git grep PLATFORM_ADMIN_EMAILS 1.16.0 -- api/` 无匹配 |
| 旧企业补丁内容 | 8 组 endpoint、`platform_admin_service.py`、`platform_admin.py` helper、前端页面 |
| 结论 | **KEEP_REQUIREMENT_REIMPLEMENT 正确**。需求在官方不存在，必须重实现 |

### E04 — 智慧广场后端 → KEEP_REQUIREMENT_REIMPLEMENT

| 检查项 | 结果 |
| --- | --- |
| 官方 1.16 是否有 `enterprise_marketplace` endpoint | **否**。`git grep enterprise_marketplace 1.16.0 -- api/` 无匹配 |
| 官方 1.16 是否有 marketplace 审核模型 | **否**。无 `enterprise_marketplace_assets` model 或 migration |
| 旧企业补丁内容 | controller、service、model (`EnterpriseMarketplaceAsset`)、migration |
| 结论 | **KEEP_REQUIREMENT_REIMPLEMENT 正确**。需求在官方不存在 |

### E16 — OAuth 专用加密器 → DROP_UPSTREAMED

| 检查项 | 结果 |
| --- | --- |
| 官方 `SystemEncrypter` 算法 | SHA-256 key derivation → AES-CBC → random 16-byte IV → PKCS padding → JSON(TypeAdapter) → base64(iv + ciphertext) |
| 旧企业 `SystemOAuthEncrypter` 算法 | SHA-256 key derivation → AES-CBC → random 16-byte IV → PKCS padding → JSON(TypeAdapter) → base64(iv + ciphertext) |
| 密文格式是否兼容 | **是**。两者都是 `base64(iv + ciphertext)` |
| 1.16 官方是否已使用 `system_encryption` | **是**。`builtin_tools_manage_service.py` 和 `trigger_provider_service.py` 均从 `system_encryption` 导入 |
| 结论 | **DROP 正确**。旧实现是官方实现的别名，功能等价 |

### E17 — 生成器 model mode 归一化 → KEEP_MINIMAL_PATCH

| 检查项 | 结果 |
| --- | --- |
| 1.16 是否存在 `normalize-generator-model.ts` | **否**。`git show 1.16.0:web/app/components/app/configuration/config/normalize-generator-model.ts` 返回 "Not found" |
| 1.16 `get-automatic-res.tsx` 如何处理 mode | `mode as unknown as ModelModeType` — 直接 cast，无归一化 |
| 旧企业补丁做了什么 | `normalizeGeneratorModel` 将 `agent-chat` / completion → `ModelModeType.chat` / `completion` |
| 结论 | **KEEP_MINIMAL_PATCH 正确**。gap 可证明，官方未修复 |

### E08 — Docker enterprise overlay → KEEP_REQUIREMENT_REIMPLEMENT

| 检查项 | 结果 |
| --- | --- |
| 官方 1.16 Compose 是否有 `agent_backend` | **是**。`docker/docker-compose.yaml` line with `agent_backend:` |
| 官方 1.16 Compose 是否有 `local_sandbox` | **是**。同文件 `local_sandbox:` |
| 旧企业 overlay 是否有 Agent 服务 | **否**。基于 1.15，无 Agent 相关 service 定义 |
| 结论 | **KEEP_REQUIREMENT_REIMPLEMENT 正确**。1.16 Compose 服务图已变，旧 overlay 不适用 |

### E15 — 升级检查与 migration head → KEEP_REQUIREMENT_REIMPLEMENT

| 检查项 | 结果 |
| --- | --- |
| 官方 1.16 head | `7a1c2d9e4b60`，`down_revision = "c3d4e5f6a7b8"` |
| 官方 1.15 head | `d9e8f7a6b5c4`，`down_revision = "c8f4a6b2d3e1"` |
| 1.15→1.16 实际新增 5 个 revision | **确认**。`a6f1c9d2e8b4`, `e4f5a6b7c8d9`, `a2b3c4d5e6f7`, `c3d4e5f6a7b8`, `7a1c2d9e4b60` |
| 1.15→1.16 修改 4 个已有 revision | **确认**。`1c9ba48be8e4`, `97e2e1a644e8`, `0b2f2c8a9d1e`, `b2515f9d4c2a` |
| 旧企业 head | `e2f0a9b7c6d5` (merge `f1a14e1e9b41` + `d9e8f7a6b5c4`) |
| 旧企业历史 revision | `c8f3d9d4a1be` → `f1a14e1e9b41` → `e2f0a9b7c6d5` |
| Release 迁移数量不一致 | 标题"9"，列表 8，upgrade guide "8"。实际 git diff: 5A + 4M = 9 |
| 结论 | **KEEP_REQUIREMENT_REIMPLEMENT 正确**。官方无企业 migration 兼容方案 |

## 7. 官方已覆盖但被误保留的补丁

经过代码检查，未发现 Architect 将官方已覆盖的能力错误标为 KEEP。全部 KEEP 项经过抽查均有明确证据支持。

### E01 不属于"误保留"但需注意

E01（默认工作区）被标为 `DROP_UPSTREAMED`，处理正确。但 Architect 在 `ENTERPRISE_REPLAY_PLAN.md:17` 说"企业平行实现删除"——经检查，旧企业候选中的 E01 代码位于 `api/services/enterprise/enterprise_service.py` 中，该文件原本来自官方 1.15 基线（在 `d70f1c3bbd` 提交中属于编辑而非新增）。1.16 官方继续演化该文件。Architect 的分析正确。

### E16 官方实现被正确识别

旧企业 `system_oauth_encryption.py` 与官方 `system_encryption.py` 的对比确认两者算法等价。Architect 的 `DROP_UPSTREAMED` 正确且给出了密文格式兼容性依据。

## 8. 被 Architect 漏掉的官方变化

### 8.1 Migration 修改文件的计数误差

- **位置**: `OFFICIAL_RELEASE_ANALYSIS.md:53`
- **遗漏**: 未提及 `1c9ba48be8e4`（uuidv7 函数 migration）在 1.16 中被修改。
- **影响**: 低。不影响 5 个新增 revision 的结论，但 PostgreSQL 18 的升级兼容性缺少明确跟踪。
- **已在 P1-2 中要求整改。**

### 8.2 `CAN_REPLACE_LOGO` 默认值修复

- **位置**: Release 的 Bug Fixes 列表和 PR #38126
- **遗漏**: Architect 引用了 `CAN_REPLACE_LOGO` 作为 enterprise 配置项（`api/configs/enterprise/__init__.py`）但未提及官方在 1.16 中将其默认从 `true` 修正为 `false` 的修复。
- **影响**: 如果企业 overlay 不设置该变量，企业部署会继承 `default=False`，与旧行为不同。应在验证计划中覆盖。
- **整改**: 在 Phase E 或 G 中检查 `CAN_REPLACE_LOGO` 的企业预期行为。

### 8.3 OpenAI Responses API 默认变更

- **位置**: Release 的 "Action Required" 部分
- **遗漏**: 1.16 将 OpenAI plugin 默认 API 类型从 Chat Completions 改为 Responses API。这影响使用自定义 OpenAI API key 的企业用户。
- **影响**: 使用 GPT-5.6+ 的企业用户如果从 1.15 升级且保留了自定义 key，可能遇到 API 兼容错误。企业验证计划应覆盖此变更。
- **整改**: 在 Phase G 的 plugin 验证中增加：检查 OpenAI provider 的 API type 设置。

## 9. Builder 文件重叠矩阵

以下矩阵标记了并行或相邻 Builder 任务之间的预期文件冲突点。

| 文件路径 | B0 | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | 冲突等级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `api/configs/feature/__init__.py` | - | - | - | W | - | - | - | - | - | 低 |
| `api/controllers/console/__init__.py` | - | - | - | W | W | - | - | - | - | **高** |
| `api/models/__init__.py` | - | - | W | - | W | - | - | - | - | **高** |
| `api/models/model.py` | - | - | W | - | W | - | - | - | - | 中 |
| `api/models/account.py` | - | - | - | R | - | - | - | - | - | 低 |
| `api/migrations/versions/*.py` | - | - | W | - | W | - | - | - | - | **高** |
| `api/services/platform_admin_service.py` | - | - | - | W | - | - | - | - | - | 独占 |
| `api/services/enterprise_marketplace_service.py` | - | - | - | - | W | - | - | - | - | 独占 |
| `api/controllers/console/platform_admin.py` | - | - | - | W | - | - | - | - | - | 独占 |
| `api/controllers/console/enterprise_marketplace.py` | - | - | - | - | W | - | - | - | - | 独占 |
| `api/libs/platform_admin.py` | - | - | - | W | - | - | - | - | - | 独占 |
| `packages/contracts/generated/api/console/*` | - | - | - | G | G | C | - | - | - | **高** |
| `web/app/components/main-nav/routes.ts` | - | - | - | - | - | W | - | - | - | 独占 |
| `web/app/components/header/account-setting/` | - | - | - | - | - | W | - | - | - | 独占 |
| `web/app/components/explore/` | - | - | - | - | - | W | - | - | - | 独占 |
| `web/app/components/apps/` | - | - | - | - | - | W | - | - | - | 独占 |
| `web/features/` | - | - | - | - | - | W | - | - | - | 独占 |
| `web/i18n/en-US/common.json` | - | - | - | - | - | W | - | - | - | 中 |
| `web/i18n/zh-Hans/common.json` | - | - | - | - | - | W | - | - | - | 中 |
| `web/app/components/app/configuration/config/automatic/` | - | W | - | - | - | - | - | - | - | 独占 |
| `web/app/components/app/configuration/config/code-generator/` | - | W | - | - | - | - | - | - | - | 独占 |
| `docker/docker-compose.enterprise.yaml` | - | - | - | - | - | - | W | R | - | 中 |
| `docker/envs/core-services/plugin-daemon.env.example` | - | - | - | - | - | - | R | W | - | 低 |
| `scripts/check-enterprise-vector-indexes.*` | - | - | - | - | - | - | - | - | W | 独占 |

图例: W = Write, R = Read, G = Generate, C = Consume, - = No touch

**需要串行化的冲突**:

1. **`api/controllers/console/__init__.py`** (B3 vs B4): 都需要注册 blueprint。要求 B3 先合并→B4 rebase，或 B4 向 B3 提交接口需求。
2. **`api/models/__init__.py` + `api/models/model.py`** (B2 vs B4): B2 建旧 model 和 migration，B4 在 B2 合并后新增/修改 model。串行 B2→B4。
3. **`api/migrations/versions/`** (B2 vs B4): B2 建旧 revision + merge。B4 在其后追加新 migration。串行 B2→B4（已在 P0-1 中要求）。
4. **`packages/contracts/`** (B3/B4 生成, B5 消费): B3 和 B4 各自生成后会产生冲突。要求 B3→B4→B5 串行，或 B3 与 B4 生成后由 B5 统一 regenerate。

**B3 与 B4 的并行风险**: 上述分析表明 B3 和 B4 不能真正并行——它们共享 controller 注册、model 导入和 contract 生成产物。建议强制串行 B3→B4，或在两者完成后增加 "contract 对齐" 的串行同步点。

## 10. Volume 升级与回滚缺口

### 10.1 回滚步骤未定义

- **严重级别**: P1（已在 P0-3 和 P1-1 中部分覆盖）
- **文档位置**: `VALIDATION_PLAN.md:203-222`
- **问题**:
  Volume 升级协议（Phase 3）描述了"成功后才制定生产窗口；生产升级仍需独立备份和回滚点"，但回滚到旧 1.15 步骤未定义：
  - 回滚是否需要反向 migration（downgrade）？`e2f0a9b7c6d5` 的 `downgrade()` 是空函数。
  - 如果 Agent App 的 conversation/session 数据在 1.16 中存在，回退到 1.15 后如何访问？
  - 如果企业 marketplace 表在 1.16 中新增了列（B4 新增），回退到旧 schema 是否需要手动 DROP COLUMN？
- **整改要求**: 增加回滚节：明确回滚时是使用备份完全恢复还是执行 downgrade + 数据迁移。建议只有"完全从备份恢复"作为受支持回滚方式。

### 10.2 Agent backend/local sandbox 数据持久化未定义

- **严重级别**: P1
- **文档位置**: `VALIDATION_PLAN.md:222`, `ARCHITECT_HANDOFF.md:157-158`
- **问题**:
  ARCHITECT_HANDOFF.md:157 提问 "Agent local sandbox 的持久化/清理/retention 企业策略是什么？"但未在验证计划中列为必答项。
  1.16 官方 Compose 中 `agent_backend` 和 `local_sandbox` 没有显式 volume mount（agent backend 的 agent run records 存储在 Redis 中，sandbox 是临时文件系统）。
  如果企业 overlay 为 sandbox 添加 volume，可能引入持久化数据不一致。
- **整改要求**: 在 B6 overlay 实施前明确：
  - Agent backend 的 run retention 策略（`DIFY_AGENT_RUN_RETENTION_SECONDS` 默认 3 天）。
  - Sandbox 是否持久化（建议否，sandbox 应是临时环境）。
  - 上述决策纳入验证计划。

### 10.3 Redis 数据库编号冲突未检查

- **严重级别**: P2
- **文档位置**: 未在现有文档中说明
- **问题**:
  官方 Compose 中 `agent_backend` 使用 Redis database `/2`（`DIFY_AGENT_REDIS_URL: redis://...@redis:6379/2`）。
  Dify 主服务可能使用 `/0` 或 `/1`。如果企业 overlay 修改了 Redis URL，可能导致 database 编号冲突。
- **整改**: 在 Phase E 中增加 Redis database 编号不冲突的检查。

## 11. 安全回退风险

逐一检查了官方安全修复，确认 Architect 没有将其错误归类为需要企业覆盖。

| 官方安全提交 | 提交 SHA | Architect 处理 | 覆盖风险 |
| --- | --- | --- | --- |
| SQL 注入修复 | `d9884efaee` | 列入不可回退清单（行 135） | 低。旧企业候选不涉及 MyScale metadata key |
| SSRF 修复 | `ae0d6ee214` | 列入不可回退清单（行 136） | 低。智慧广场新实现若包含外部 URL fetch 必须走 SSRF helper。**已在 OFFICIAL_RELEASE_ANALYSIS.md:136-137 预警** |
| 开放重定向修复 | `c68e5e5ed3` | 列入不可回退清单（行 137） | 低。E07 VERIFY_ONLY 保留测试 |
| Sandbox plan 检查 | `38aec8b506`, `7311f1ba6d` | 列入不可回退清单（行 138） | 低。未涉及旧 sandbox 代码回退 |
| Landlock 保护 | `71709f03c3`, `8a33161080` | 列入不可回退清单（行 139） | 低。overlay 要求保持默认开启 |
| CVE 依赖升级 | 多个（行 140） | 列入不可回退清单 | 低。明确不恢复 1.15 lockfile/Docker 层 |
| RBAC owner scope | `62cb5b5865` | 列入不可回退清单（行 141） | 低。智慧广场新实现必须显式 scope |

**新增风险**: 智慧广场的"复制到 workspace B"功能如果使用 `httpx.get` 获取 source app 的 icon 或外部 URL，可能引入 SSRF。Architect 在 OFFICIAL_RELEASE_ANALYSIS.md:136 提了 "API tool schema fetch 走 SSRF helper" 但未明确智慧广场复制/导入的 URL fetch 也必须走 SSRF proxy。
- **已在 PATCH_DECISION_MATRIX.md:64-65 部分覆盖**（"source app 跨租户泄漏""依赖泄漏"）。

**Agent key 泄露风险**: 官方 Compose 中 `DIFY_AGENT_SERVER_SECRET_KEY` 硬编码在 YAML 中。如果企业 overlay 复制了官方 service 块但未修改 key，该默认值将进入企业配置包。
- **已在 P1-5 中要求整改。**

## 12. 精确整改清单

| ID | 优先级 | 描述 | 负责方 | 阻断后续？ |
| --- | --- | --- | --- | --- |
| FIX-01 | P0 | B2 只做历史 revision 兼容，schema 最终化归 B4；或反转 B2/B4 顺序，先确认 schema 再做 migration | Architect | 是（B2/B4 不能并行开始） |
| FIX-02 | P0 | 为每个 Builder 任务产出 `ALLOWED_FILES.txt` 和文件重叠矩阵，对冲突文件指定唯一所有者 | Architect | 是（Builder 不能独立开发） |
| FIX-03 | P0 | 预分配企业 1.16 head 的 revision ID（格式 `YYYY_MM_DD_HHMM-XXXXXXXXXXXXXXXX_merge_1_16_0_enterprise_heads.py`） | Architect | 是（B2 无法完成 migration） |
| FIX-04 | P1 | B2 实施方法明确为方式 (a) 复制旧文件保持 revision ID 不变 | Architect | 否（但 E15 验证缺正确前提） |
| FIX-05 | P1 | 验证计划 Phase D 增加 PostgreSQL 18 兼容性子路径 | Architect | 否 |
| FIX-06 | P1 | 验证计划 Phase E 增加 `DIFY_AGENT_INNER_API_KEY` == `INNER_API_KEY_FOR_PLUGIN` 显式断言 | Architect | 否 |
| FIX-07 | P1 | 验证计划 Phase G 补充 Agent App 具体操作步骤和期望结果 | Architect | 否（但验证不可复现） |
| FIX-08 | P1 | 验证计划 Phase H 增加 `DIFY_AGENT_SERVER_SECRET_KEY` 非默认检查 | Architect | 否 |
| FIX-09 | P1 | 验证计划 Phase G 增加 log grep 扫描已知 security key | Architect | 否 |
| FIX-10 | P1 | 验证计划 Phase F 显式包含 `api_websocket` 在五 runtime image ID 检查中 | Architect | 否 |
| FIX-11 | P2 | OFFICIAL_RELEASE_ANALYSIS.md:53 补充 uuidv7 migration 修改说明 | Architect | 否 |
| FIX-12 | P2 | 验证计划补充 Agent App 的结构化 checklist | Architect | 否 |
| FIX-13 | P2 | 合并顺序中 B3/B4 并行明确同步点 | Architect | 否 |
| FIX-14 | P2 | 验证计划 Phase E 增加 profile 保持和 Redis database 编号检查 | Architect | 否 |
| FIX-15 | P2 | B5 任务拆分 i18n key 命名空间 | Architect | 否 |
| FIX-16 | P2 | E06/B9 增加时间约束 | Architect | 否 |
| FIX-17 | P2 | 验证计划 Phase D MySQL 路径增加 marketplace DDL 兼容性检查 | Architect | 否 |
| FIX-18 | P2 | 验证计划增加 `CAN_REPLACE_LOGO` 和 OpenAI Responses API 变更覆盖 | Architect | 否 |
| FIX-19 | P1 | Volume 验证协议增加回滚步骤定义（完全从备份恢复） | Architect | 否 |

## 13. 复审时必须验证的项目

以下项目必须在 Builder 阶段开始前由再次审查确认：

1. **P0 全部关闭**: FIX-01, FIX-02, FIX-03 已在更新后的计划中体现。
2. **P1 全部关闭**: FIX-04 至 FIX-10 已在更新后的验证计划中体现。
3. **B2 的 3 个旧 migration 文件**经过 `git show` 验证 revision ID、`down_revision` 和 DDL 与原文件一致。
4. **企业 head revision ID** 出现在 `uv run --project api flask db heads` 输出中且唯一。
5. **每个 B 任务的文件清单**已发布，且 CI 有 diff owner check 能阻止未声明文件的变更。
6. **OpenAI Responses API 变更**已在升级验证中覆盖。
7. **`CAN_REPLACE_LOGO` 行为**已在验证中确认与企业预期一致。

---

## 附录 A: 审查方法

1. 对所有 5 份文档进行全文阅读和交叉引用。
2. 使用 `git show 1.16.0:<path>` 验证官方代码中存在/不存在。
3. 使用 `git diff 1.15.0..1.16.0 --stat` 和 `--name-status` 验证 migration 差异。
4. 使用 `git show origin/codex/enterprise-candidate-1.15.0-20260626:<path>` 验证旧企业补丁。
5. 使用 `webfetch` 抓取 GitHub Release 页面，交叉验证迁移数量、env 变量和安全修复描述。
6. 对每个 KEEP 项进行独立的代码存在性检查和算法对比（OAuth encryption）。
7. 人工分析文件重叠矩阵。

**审查完整性声明**: 本审查基于 Git 对象 (`1.16.0` tag, `1.15.0` tag, `origin/codex/enterprise-candidate-1.15.0-20260626`) 和 GitHub Release 页面完成。所有代码引用均可通过 `git show` 复现。未访问 `docker/volumes`，未修改任何业务代码，未启动 Docker。

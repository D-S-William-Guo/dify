# Dify Enterprise 1.16.0 Architect Handoff

## 1. 工作树与提交身份

- 当前工作树分支：`ctyun/replay-116-architect`
- 用户指定候选来源：`codex/enterprise-candidate-1.16.0-20260718`
- 官方基线标签：`1.16.0`
- 基线提交：`5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 架构工作开始时 HEAD：`5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 原架构提交主题：`docs: plan enterprise replay for 1.16.0`。独立审查提交为 `caedca07e4938e8460c755b9ba37293d59417c8c`；本轮整改提交主题为 `docs: address enterprise 1.16.0 replay review`，最终 hash 在交付报告给出（Git 对象不能在自身内容中稳定自引用其最终 hash）。

本地仓库未提供 `origin/codex/enterprise-candidate-1.16.0-20260718` 跟踪引用，因此只能证明架构工作起点与用户指定提交及官方标签完全一致，不能用远端引用名再次证明候选分支来源。当前文档分支已在该基线上追加架构、Reviewer 原始记录和本轮整改提交；Builder 开始前由维护者确认/创建目标候选分支，不要改变实现基线。

## 2. 本次交付范围

本提交只应包含：

1. `ENTERPRISE_REPLAY_PLAN.md`
2. `docs/enterprise/replay-1.16.0/OFFICIAL_RELEASE_ANALYSIS.md`
3. `docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md`
4. `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md`
5. `docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md`

未修改业务代码、Docker 配置、migration、版本号或运行数据；未启动 Docker；未访问、复制或修改 `docker/volumes`。

## 3. 主要结论

1. 官方 1.16 是不可妥协的实现真相。`1.15.0..1.16.0` 变更达 8,708 文件，Agent、契约、session、状态与工具链都已换代，旧候选不能 cherry-pick。
2. 官方已经实现企业默认 workspace 自动加入和注册/workspace 创建开关，删除平行实现，只保留配置与验证。
3. 平台管理员、智慧广场、企业 overlay/镜像、离线包、vector 升级检查和旧企业 migration 兼容仍需企业交付。
4. 平台管理员/智慧广场必须使用 1.16 的 Pydantic Console contracts、生成 routes/types、`consoleQuery`、显式 SQLAlchemy `Session`、tenant/owner scope 和 Jotai/bootstrap；旧 controller/service/Web hooks 全部只作需求证据。
5. 旧 OAuth 专用加密器与官方实现密文兼容且行为重复，`DROP_UPSTREAMED`。生成器 model mode 归一化仍未上游覆盖，`KEEP_MINIMAL_PATCH`。
6. Workflow、HITL、Plugin、Dataset、install/sign-in/public routes 和旧 session bug 大多 `VERIFY_ONLY`；只有失败测试先证明 1.16 差距后才能新增补丁。
7. 1.16 新增 `agent_backend` 和 `local_sandbox`。overlay 不得覆盖其安全边界；离线包必须包含两镜像，生产必须替换 Agent server secret，Landlock 默认开启。
8. migration 文案不一致已按代码澄清：Release 标题说 9、实际列 8、升级说明说 8；从官方 1.15 到 1.16 实际新增 5 个 revision。官方 1.16 静态 head 是 `7a1c2d9e4b60`。
9. 旧企业库可能记录 `e2f0a9b7c6d5`。必须保留旧 revision 可解析并新增 1.16 merge；直接删除旧 migration 或 stamp 都会破坏升级可审计性。
10. “企业会话管理”范围不明，当前 `DEFER`。不得擅自把 account sessions、conversation 或 Agent shell session 中任一种当成完整需求。

## 4. Builder 任务拆分

### B0：基线、生成链和安全护栏

- 交付：基线/diff allowlist、OpenAPI generation 命令、官方安全回归集合、Compose 静态断言。
- 允许文件：测试/CI/开发脚本的最小范围，需 Reviewer 预先确认。
- 完成标准：能阻止旧 contract、controller SQLAlchemy、旧镜像/volume 文件进入 diff。

### B1：生成器 mode 归一化

- 交付：纯函数、automatic/code generator 接入和聚焦测试。
- 旧证据：`normalize-generator-model.ts` 及两个旧 spec。
- 1.16 边界：使用当前 TypeScript/Vite+/i18n/test mocks，不复制旧格式。
- 完成标准：`chat`、`completion`、`agent-chat`、stale localStorage 的 API payload 合法。

### B2：历史 migration 图和空 merge

- 交付：原样恢复 `c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5` 的 revision ID、`down_revision`、`branch_labels` 和历史 DDL 语义；增加空 merge `a71e16c0de01`。
- 关键图：merge parents 为旧企业 `e2f0a9b7c6d5` 与官方 `7a1c2d9e4b60`；merge 不含业务 DDL。不得新生成历史 ID或使用 `alembic stamp`。
- 完成标准：旧企业数据库可定位完整 history；B2 不设计 1.16 智慧广场新增字段。

### B3：平台管理员后端

- 交付：授权/审计设计、session-injected service、DTO/controller、生成 contract、后端测试。
- 先决决策：密码重置、workspace 归档是否首版交付；无审计则延后高风险操作。
- 完成标准：admin/non-admin、跨 tenant scope、owner/last workspace/seat limit、rollback 全覆盖。

### B4：智慧广场后端

- 交付：在 merge 后通过 `b416e5c4e702` 定义最终 schema，完成列/索引/约束/数据迁移、service/controller、提交/审核/发布/下架/复制状态机、最终 contract generation 和无 secret DSL copy。
- 先决决策：推荐“发布时生成不可变快照”，因为它保证审计、发布后稳定、跨 workspace 权限独立和源 app 删除后可用；必须通过人工 Design Gate。外部 URL 一律走官方 SSRF 防护路径。
- 完成标准：A 提交→admin 审核→B 复制的完整后端流程，非法状态/越权/并发有测试。

### B5：平台管理员和智慧广场前端

- 交付：基于生成 contract 的 queries/mutations、feature state/Jotai、权限导航、i18n 和行为测试。
- 禁止：手写 Console response types、旧 app context、legacy contract loader、硬编码用户文案。
- i18n 唯一命名空间：平台管理员使用 `platformAdmin.*`，智慧广场使用 `enterpriseMarketplace.*`；B5 独占两份 `common.json` 修改。
- 完成标准：权限入口、深链、提交/审核/复制、错误/空状态和重复点击均验证。

### B6：1.16 enterprise overlay 与企业镜像

- 交付：最小 Compose overlay、API/Web image/build metadata、WebSocket image 覆盖。
- 禁止：修改官方 Compose；恢复 1.15 Dockerfile；覆盖 Agent depends_on/healthcheck/Landlock/key 关系。
- 完成标准：Compose config 中五个 runtime identity 正确，Agent 新服务完整。

### B7：离线 plugin、镜像包与配置包

- 交付：官方 mirror/signature knob 透传、`Mode=reuse`、完整镜像断言、manifest 和最小配置包。
- 完成标准：包含 Agent backend/local sandbox；绑定验证 image IDs/commit；包内容无 `.env`/secret/volume/cache。

### B8：Dataset/vector/volume 升级与发布验证

- 交付：默认只读的 vector consistency checker、完整 validation evidence、无外网离线 smoke。
- repair：独立任务，需显式批准；不得与只读检查一起默认执行。
- 完成标准：数据库、vector、plugin、Agent、workflow/HITL/WebSocket、auth/RBAC、安全和离线门禁全部通过。

### B9：企业会话管理需求澄清

- 交付：产品契约，不是代码。
- 必答：actor、session 对象、list/revoke/expire 操作、scope、审计、保留时间、验收用例。
- 完成标准：能明确归类为官方 `VERIFY_ONLY` 或新增独立安全设计。

## 5. Builder 文件所有权与重叠矩阵

本表是规范化 allowlist；不要求当前在业务目录创建 `ALLOWED_FILES.txt`。每个 Builder 开始前把基线 commit 固定到任务单，结束时按 Allowed write paths 审核 diff。任何未声明文件一旦出现，立即暂停合并并重新审批范围；“顺手修复”、格式化波及和跨任务生成都不例外。是否增加自动 diff-owner 检查由 B0 在 Builder 开始前形成独立工具决策，但没有自动检查不降低人工门禁。

| 任务 | Allowed write paths | Read-only reference paths | Forbidden paths | Generated artifacts owner | 前置任务 / 合并顺序 | 验收命令 |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | `.github/workflows/enterprise-replay-*`、`scripts/ci/check-enterprise-replay-*`、经 Reviewer 批准的 guardrail tests | 全仓库、五份架构文档 | `api/**`、`web/**`、`docker/**`、`dify-agent/**`、`packages/**`、`docker/volumes/**` | B0 独占 scope-check 报告/CI 定义；不生成 contracts | 首个合并 | `git diff --check 1.16.0...HEAD`；`scripts/ci/check-enterprise-replay-scope.sh 1.16.0 HEAD`；OpenAPI/Compose 命令只做 dry-run |
| B1 | `web/app/components/app/configuration/config/automatic/**`、`web/app/components/app/configuration/config/code-generator/**` 及同目录 focused specs | 当前 generator/types/i18n/test helpers | `api/**`、`docker/**`、`packages/contracts/**`、`web/i18n/**` | 无 | B0 后，可在 B2 前合并 | `pnpm --dir web vitest run app/components/app/configuration/config/automatic app/components/app/configuration/config/code-generator`；`pnpm --dir web type-check` |
| B2 | 仅历史文件 `2026_04_30_2100-c8f3d9d4a1be_add_enterprise_marketplace_assets.py`、`2026_05_19_2000-f1a14e1e9b41_merge_1_14_2_enterprise_heads.py`、`2026_06_27_1145-e2f0a9b7c6d5_merge_1_15_0_enterprise_heads.py`、空 merge `2026_07_21_1000-a71e16c0de01_merge_1_16_0_enterprise_heads.py`，及 migration graph tests | 旧企业候选 migration、官方 migrations、models | 除上述文件外的 `api/**`；尤其 `api/models/**`、controller/service、contracts；全部 Web/Docker | B2 独占三个历史 revision 与空 merge | B0/B1 后；必须先于 B3、B4 | `uv run --project api flask db history`；`uv run --project api flask db heads`；历史文件语义 diff；四起点 graph tests |
| B3 | `api/configs/feature/__init__.py`、`api/libs/platform_admin.py`、`api/services/platform_admin_service.py`、`api/controllers/console/platform_admin.py`、对应 unit/contract source tests | account/tenant/RBAC、Console schema guide、B2 graph | `api/controllers/console/__init__.py`、`api/models/__init__.py`、`api/models/model.py`、`api/migrations/versions/**`、`packages/contracts/**`、Web/Docker | 不生成/提交 `packages/contracts/**`；向 B4 提交 route/schema generation 需求 | B2 合并后开始并合并；B4 才开始 | `uv run --project api pytest api/tests/unit_tests/services/test_platform_admin_service.py api/tests/unit_tests/controllers/console/test_platform_admin.py`；diff-owner check |
| B4 | `api/controllers/console/__init__.py`、`api/models/__init__.py`、`api/models/model.py`、`api/controllers/console/enterprise_marketplace.py`、`api/services/enterprise_marketplace_service.py`、相关 domain/DTO/tests、`2026_07_21_1400-b416e5c4e702_finalize_enterprise_marketplace_schema.py`、`packages/contracts/generated/api/console/**` | B3 platform-admin API/auth、官方 DSL/SSRF helpers、B2 migrations、Web contract consumers | B2 四个 migration 文件、平台管理员独占实现文件、`web/**`、`docker/**` | B4 是最终 Console OpenAPI/contracts 唯一生成者，负责把 B3+B4 endpoint 一次性生成并提交 | B3 已合并后开始；B4 合并后才允许 B5 | `uv run --project api pytest api/tests/unit_tests/services/test_enterprise_marketplace_service.py api/tests/unit_tests/controllers/console/test_enterprise_marketplace.py`；`pnpm --dir packages/contracts gen-api-contract`；`uv run --project api flask db heads` 输出唯一 `b416e5c4e702` |
| B5 | 企业前端组件/queries/tests：`web/app/components/header/account-setting/**`、`web/app/components/main-nav/**`、`web/app/components/explore/**`、`web/app/components/apps/**`、经批准的 `web/features/platform-admin/**`/`enterprise-marketplace/**`；`web/i18n/en-US/common.json`、`web/i18n/zh-Hans/common.json` | `packages/contracts/generated/api/console/**`、B3/B4 OpenAPI、现有 Jotai/query patterns | `api/**`、`docker/**`、`dify-agent/**`、`packages/contracts/**`；其他 locale 未批准范围 | B5 独占企业前端与两份 i18n；只消费、不重新生成 contracts | B4 最终 contracts 合并后开始 | `pnpm --dir web vitest run app/components/header/account-setting app/components/main-nav app/components/explore app/components/apps`；`pnpm --dir web type-check`；`pnpm check`；i18n namespace check |
| B6 | `docker/docker-compose.enterprise.yaml`、经批准的新 enterprise API/Web Dockerfile/构建元数据文件 | 官方 `docker/docker-compose.yaml`、env examples、B3/B4 配置、B5 build | 官方 `docker/docker-compose.yaml`、`docker/volumes/**`、业务源码、offline/package scripts | B6 独占 enterprise compose overlay；Compose 展开结果仅作临时证据 | B5 后；B9 截止点；B7 必须等待 B6 | 两层 `docker compose config -q`、`config --images`、`--profile collaboration config --services`；key/Redis/profile 静态断言 |
| B7 | `scripts/build-enterprise-offline.*`、`scripts/*enterprise*config*`、离线 fixture/tests、必要的 `docker/envs/**.env.example` | B6 overlay、官方 Compose、image metadata、plugin mirror/signature配置 | `docker/docker-compose.enterprise.yaml`、业务源码、`packages/contracts/**`、`docker/volumes/**`、真实 `.env`/secret | B7 独占离线 image list、manifest、config archive 生成逻辑；只读取 B6 overlay | B6 合并后 | offline dry-run/fixture tests；`Mode=reuse`；archive/secret/default-key/volume scan；`--pull never` smoke |
| B8 | `scripts/check-enterprise-vector-indexes.*`、对应 fixtures/tests、经批准的 `docs/enterprise/replay-1.16.0/evidence/**` | 全部已合并实现、B6/B7 artifacts、隔离升级环境 inventory | 业务源码、Compose/overlay、migration、contracts、`docker/volumes/**`；repair 实现未经另批不得写 | B8 独占最终验证报告和 read-only vector checker；不重新生成产品 artifact | B7 后，最终发布门禁 | 完整 `VALIDATION_PLAN.md`；checker read-only tests；数据库/runtime/offline evidence completeness check |
| B9 | `docs/enterprise/replay-1.16.0/session-management-product-decision.md`（仅在产品方要求留档时） | 官方 account/Agent/conversation session 实现与本计划 | 所有业务代码、migration、Compose、contracts、volume | B9 仅产出产品契约，无 generated code | 最迟 B6 开始前结论；新实现只能成为另审 B10 | 文档包含 actor/object/actions/scope/audit/expiry/acceptance；架构签字 |

共享路径唯一所有者与交接规则：

| 共享路径 | 唯一写入者 | 规则 |
| --- | --- | --- |
| `api/controllers/console/__init__.py` | B4 | B3 不写；B4 在 B3 合并后一次性注册平台管理员与智慧广场需求 |
| `api/models/__init__.py`、`api/models/model.py` | B4 | B2 只恢复 migration，不创建/注册 model；B4 定义最终模型 |
| `api/migrations/versions/` | 按文件分区：B2 历史+空 merge，B4 仅最终 schema | B2/B4 不改对方文件；目录内任何第三个企业 migration 需重新审批 |
| `packages/contracts/` | B4 | B3 只交付 schema source；B4 在 B3 合并后完成唯一一次最终 generation；B5 只消费 |
| `web/i18n/en-US/common.json`、`web/i18n/zh-Hans/common.json` | B5 | 只使用 `platformAdmin.*`、`enterpriseMarketplace.*`，不得由后端 Builder 预写 |
| `docker/docker-compose.enterprise.yaml` | B6 | B7 只读取展开结果，不修改 overlay |

## 6. 任务依赖图

```text
B0 ─┬─> B1
    └─> B2 ─> B3 ─> B4 ─> B5 ─> B6 ─> B7 ─> B8

B9 的产品契约截止于 B6 开始前；若产生实现任务，新增 B10，完成独立安全/架构评审并在 B8 前合并。
```

## 7. 推荐合并顺序

1. B0 基线/护栏。
2. B1 独立最小回归修复。
3. B2 历史 migration 与空 merge。
4. B3 平台管理员后端。
5. B4 智慧广场后端。
6. B5 前端。
7. B6 overlay/镜像。
8. B7 离线链。
9. B8 完整验证与发布证据。

B3/B4 不并行：B3 合并形成平台管理员鉴权基础后，B4 才开始并在其上实现审核、schema 和最终 contract generation；B4 合并后 B5 才消费 generated contracts。B6 不应在业务 contract 未稳定时提前定版镜像；B7 必须在 B6 后；B8 最后且不能跳过。

## 8. 未决问题

1. 目标远端候选分支引用为何未在本地提供；维护者需确认它确实指向官方基线。
2. 平台管理员是纯 email 配置，还是需要数据库角色、审计和 break-glass 流程？email 变更/大小写/禁用账号如何处理？
3. 平台管理员首版是否必须支持密码重置和 workspace 归档？这两项需要高风险操作审计和恢复策略。
4. 智慧广场推荐发布时形成不可变 DSL snapshot；产品/历史业务事实是否与此冲突？该项是 Builder 前 Design Gate。
5. 智慧广场复制目标是否总是 current workspace？复制权限和 plugin/knowledge 依赖缺失如何向用户呈现？
6. 旧企业 `enterprise_marketplace_assets` 是否存在真实生产数据、非标准 schema 或额外 revision？迁移实现前需要只读 inventory。
7. “企业会话管理”精确定义是什么？产品契约截止到 B6 开始前；超时保持 DEFER，不进入本次代码范围。
8. 离线目标支持哪些 CPU 架构和 vector stores？manifest 是否必须包含多架构 digest？
9. 私有 `.difypkg` 的签名根/可信来源是什么？是否允许任何部署默认关闭签名验证（建议否）？
10. Agent run retention 默认官方 3 天且可配置覆盖；local sandbox 默认不持久化且 overlay 不增加永久共享 volume。产品是否要求不同 retention（需在 B6 前明确）？
11. `uv flask db heads` 在本工作区因受限网络无法获取锁定 Git 依赖；Builder 依赖环境必须补跑并保存输出。

## 9. Review Disposition

Reviewer 结论段“2 个 P0”与发现数量/P0 章节/整改清单不一致；本台账按实际 **3 个 P0** 处理。以下状态仅使用批准枚举；所有 P0/P1 都已有文档闭环，没有以 `NEEDS_HUMAN_DECISION` 放行 Builder。Design Gate 是已接受方案的产品事实核验，不会把未决实现交给 Builder。

| Review ID | 严重级别 | 处理状态 | 是否接受 | 整改文档位置 | 采用的决定 | 证据 | 复审方法 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FIX-01 | P0 | ADDRESSED_WITH_REFINEMENT | 接受 | Replay Plan §4–5；Decision Matrix E04/E15；本文件 B2/B4 | B2 只恢复历史+空 merge；B4 在 B3 后负责最终 schema/DDL/service/controller/contracts；推荐不可变快照并设 Design Gate | 明确 `a71e16c0de01` 无 DDL，`b416e5c4e702` 位于其后；依赖 `B2→B3→B4→B5` | 检查两个 migration 内容/parents/head；检查 B4 schema 与快照决定；确认 Builder 前 Gate 结论 |
| FIX-02 | P0 | ADDRESSED_WITH_REFINEMENT | 接受 | 本文件 §5 | B0–B9 全量规范化 allowlist/readonly/forbidden/owner/dependency/order/command；文档矩阵代替当前创建 `ALLOWED_FILES.txt`，自动检查由 B0 单独决定 | 共享 controller/model/migrations/contracts/i18n/overlay 均有唯一写入者或精确文件分区；未声明 diff 强制暂停 | Reviewer 按 Builder diff 逐行对表；检查 B0 工具决定，不以工具缺失绕过人工门禁 |
| FIX-03 | P0 | ADDRESSED_WITH_REFINEMENT | 接受 | Release Analysis §4；Replay Plan B2/B4；Validation Phase D | 同时预分配空 merge `a71e16c0de01` 与最终 schema/head `b416e5c4e702`，消除“merge 已知但最终 head 未知” | 2026-07-21 `git grep` 覆盖 `1.16.0`、全部本地/`origin` refs、旧企业候选均 CLEAR；文件名/parents 固化 | 重跑同一 refs 集合 grep；检查 merge 双 parent、无 DDL、B4 parent 和唯一 head |
| FIX-04 | P1 | ADDRESSED | 接受 | Replay Plan B2；Decision Matrix E15；Validation Phase D | 复制旧文件，保持 revision/down_revision/branch_labels/历史 DDL 语义；禁新 ID、禁 stamp | 三个历史 ID 和语义对比均列为门禁 | `git show` 旧候选逐文件对比；`flask db history`；旧库实际升级 |
| FIX-05 | P1 | ADDRESSED_WITH_REFINEMENT | 接受 | Release Analysis §4；Validation Phase D | 增加当前生产 PG、PG18 空库、PG18 应用升级；默认拆分 DB 大版本与应用升级，同窗列为独立高风险条件场景 | 明确 `1c9ba48be8e4` 修改事实、`SELECT uuidv7()` 和支持级别矩阵 | 审核每个“必须运行”证据；确认条件场景未冒充执行；检查 uuid version 7 |
| FIX-06 | P1 | ADDRESSED | 接受 | Validation Phase E/G | 比较 Compose fallback 展开后的最终值，且运行 Agent inner API success case | 明确字段路径、0600 临时文件、只输出相等布尔值 | 用 YAML parser 重跑相等断言；运行 success smoke；检查无值泄漏 |
| FIX-07 | P1 | ADDRESSED_WITH_REFINEMENT | 接受 | Validation Phase G “Agent App Beta” | 用统一表格定义前置数据、UI/API、状态码/响应、页面、失败、截图/日志，覆盖 12 类场景 | roster、Skills、文件、Knowledge、Tools、发布、对话、roster Workflow、inline、停服、timeout/reconnect/cancel/cleanup、Landlock、双 secret 均覆盖 | 对照生成 OpenAPI 固化唯一状态码；逐行复跑并核对截图与 service 日志 |
| FIX-08 | P1 | ADDRESSED | 接受 | Validation Phase H | 真实 secret 禁入包；开发默认只允许 WARNING example；生产安装生成新 secret；违规阻断 | example、可运行配置、安装流程分别设门禁 | 解包扫描；检查 WARNING 上下文；全新安装验证生成/注入且输出不泄漏 |
| FIX-09 | P1 | ADDRESSED_WITH_REFINEMENT | 接受 | Validation Phase G “Secret 扫描”、Phase H | pattern 从受保护环境构造，禁 CLI/日志/仓库暴露，0600 使用后清理；覆盖服务、Compose、manifest、安装输出 | 扫描范围显式含 API/worker/WebSocket/plugin/agent/sandbox/Web/Compose/manifest/installer | 在隔离环境植入 canary 验证扫描能失败；检查实际运行输出与临时文件清理 |
| FIX-10 | P1 | ADDRESSED | 接受 | Validation Phase F | 显式 inspect 五个容器；四个 API runtime image ID 全等，Web 等于企业 Web ID，tag 不作替代 | `api/worker/worker_beat/api_websocket/web` 全枚举 | 保存每个 `.Image`/RepoDigest；比较不可变 ID 与本轮 build 记录 |
| FIX-11 | P2 | ADDRESSED | 接受 | Release Analysis §4；Validation Phase D | 补充 uuidv7 `1c9ba48be8e4` 是第 4 个修改 migration | 明确 5A+4M 及 PG18 原因 | grep 文档和 `git diff 1.15.0..1.16.0` 复核 |
| FIX-12 | P2 | ADDRESSED_WITH_REFINEMENT | 接受 | Validation Phase G “Agent App Beta” | 结构化 UI/API checklist，并要求由生成 contract 固化最终路径/状态/schema | 每个场景都有状态/字段/页面/证据 | Reviewer 检查最终记录无候选码、每行均有实际 API 与截图 |
| FIX-13 | P2 | ADDRESSED | 接受 | Replay Plan §5；本文件 §6–7 | 强制 B3 合并→B4 开始/生成→B5 消费，不再并行 | contracts 唯一 owner B4，B5 禁生成 | 检查 git log/任务基线和 B3/B4/B5 diff 顺序 |
| FIX-14 | P2 | ADDRESSED | 接受 | Validation Phase E；本文件 B6 ownership | collaboration profile 必须保留 `api_websocket`；解析 Redis DB 并断言不冲突 | profile 命令、service 检查和 Redis 规则已明确 | 展开 Compose profiles；枚举所有 Redis URL database 编号 |
| FIX-15 | P2 | ADDRESSED | 接受 | 本文件 B5/§5 | B5 独占 i18n，固定 `platformAdmin.*` 与 `enterpriseMarketplace.*` | 两份 common.json 只有 B5 可写 | diff key-prefix check；确认无第二 Builder 编辑 |
| FIX-16 | P2 | ADDRESSED | 接受 | Decision Matrix E06；Replay Plan §5；本文件 B9 | B9 产品契约截止 B6 开始前；新实现为 B10，须安全/架构评审并在 B8 前完成 | 超时则 DEFER 且禁止代码的升级条件明确 | 查 B6 启动时间前的产品决定；若有 B10 查独立评审与 B8 门禁 |
| FIX-17 | P2 | ADDRESSED | 接受 | Validation Phase D | MySQL 空库与企业升级均必须运行，检查 marketplace JSON、时间默认、索引/约束 | `SHOW CREATE TABLE` 明确列入证据 | 在声明支持的 MySQL 版本执行两路径并保存 DDL |
| FIX-18 | P2 | ADDRESSED | 接受 | Release Analysis §3；Validation Phase E/G | 验证 `CAN_REPLACE_LOGO=false` 官方默认；升级自定义 OpenAI key 时检查 Responses API | Compose 展开值和 provider 实际请求均列门禁 | 配置默认/显式覆盖测试；升级 fixture 执行模型调用 |
| FIX-19 | P1 | ADDRESSED | 接受 | Validation §3 “唯一受支持的回滚方法”及 retention 条款 | 只支持停止 1.16、隔离 migrated volume、完整备份恢复、1.15 配置/镜像重启验证；1.16 数据不自动回灌；run retention 3 天、sandbox 不持久化 | 明确禁 Alembic downgrade/原地复用，列出恢复对象和业务验证 | 在隔离演练恢复；核对账户/应用/workflow/knowledge/plugin/vector；检查 overlay/Redis/retention |

## 10. Reviewer-2 精确复审范围

### 基线与范围 Reviewer

- 审查 `git merge-base 1.16.0 HEAD`、每个 Builder diff、无旧目录/volume/cache/真实 env。
- 拒绝混合多个 B 任务的提交或无失败测试的“兼容修复”。

### Backend/API Reviewer

- 仅审查 B2/B3/B4 的 migration、model/domain/service/controller/contract/tests。
- 确认 controller 无 direct SQLAlchemy；service 显式 Session；事务由明确调用者拥有。
- 确认 tenant/owner scope、状态机、幂等、并发、错误映射、无 secret DSL 和审计。
- 对照 `api/AGENTS.md` 与 `api/controllers/API_SCHEMA_GUIDE.md`。

### Frontend Reviewer

- 仅审查 B1/B5 及生成 contract 消费。
- 确认无 `any`、无手写 Console types/fetch、无旧 app context、无硬编码文案。
- 确认 TanStack Query/Jotai ownership、导航权限、loading/error/empty、a11y 和测试。
- 对照 `web/AGENTS.md`、当前生成 contracts 和 TypeScript/Vite+/ESLint 规则。

### Security Reviewer

- 精查平台管理员授权/高风险操作、智慧广场跨 tenant/DSL copy、SSRF/open redirect、RBAC、Agent keys/Landlock/sandbox plan、plugin signature、manifest secret。
- 逐项确认官方 `d9884efaee`（SQLi）、`ae0d6ee214`（SSRF）、`c68e5e5ed3`（redirect）、`38aec8b506`/`7311f1ba6d`（sandbox）、`71709f03c3`（Landlock）未回退。

### Migration/Data Reviewer

- 精查 revision/down_revision 图、历史 IDs、DDL 幂等/兼容、单 head 和四起点测试。
- 对照迁移前后 inventory；禁止 stamp、自动删表/数据或用空库成功代替升级成功。
- 审查 vector checker 默认只读；repair 必须独立审批。

### Docker/Offline Reviewer

- 只审查 B6/B7 的 overlay/build/package/docs；官方 `docker/docker-compose.yaml` 必须无修改。
- 检查五个企业 runtime、Agent 两服务、key 对齐、Landlock、healthcheck、profiles、image ID/commit、`Mode=reuse`。
- 扫描 archive 内容，确认不含 volume、`.env`、secret、cache、源控制元数据。

### Runtime/Release Reviewer

- 按 `VALIDATION_PLAN.md` 复核原始命令/退出码/日志/image IDs/migration inventory/浏览器用例。
- 不接受针对旧容器、不同 image IDs 或联网环境通过后直接声称离线包通过。

Reviewer-2 必须精确复审：FIX-01～FIX-19 disposition 与引用位置；3 个 P0 的 migration 职责/ID/ownership/串行链；7 个 P1 的历史语义、PG18、key equality、Agent 场景、离线默认 secret、secret 扫描、image ID；FIX-19 回滚/retention/sandbox；P2 的 uuidv7、profile/Redis、i18n、B9 deadline、MySQL、logo/OpenAI/SSRF。复审只针对本轮五份允许修改文档和未修改的原始 `ARCHITECT_REVIEW.md`，不要求业务实现已经存在；但必须判断计划是否足以无歧义地启动 Builder。

## 11. Reviewer 不应审查为“需要保留”的旧代码

- `system_oauth_encryption.py` 重复抽象。
- 旧平台管理员/智慧广场 controller/service/UI 的具体编码形式。
- 旧手写 Web models/hooks、旧 app context 和 1.15 API 兼容调整。
- 旧 Dockerfile/Compose/lockfile 和版本文档。
- 旧 workflow/HITL/plugin/dataset 修复，除非有 1.16 失败测试和独立决策记录。

所有旧内容的唯一价值是需求、历史故障和验收样例；实现评审必须以 1.16 官方代码与本交接的边界为准。

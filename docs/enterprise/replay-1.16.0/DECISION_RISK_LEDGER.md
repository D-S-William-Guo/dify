# Dify Enterprise 1.16.0 重放 B0–B8 决策/风险台账（详细版）

更新时间：2026-08-14（Asia/Shanghai，Phase F Rebuild Validator 回填）

本文件是人工判断的对照物，不是 AI 的结论。每项都尽量给出：决策点、选项、选择、影响范围、优缺点、数据证据、验证状态、待判断问题。

## 状态图例

- ✅ 已定 + 已验证：有静态/单元/fixture/契约证据。
- ⚠️ 已定 + 未运行验证：真实数据库/容器/浏览器/离线运行未验证；编译或运行可能暴露问题。
- ❓ 未定：需要你拍板；本文件只列选项与利弊。

## 数据来源

- `ARCHITECT_HANDOFF.md`
- `PATCH_DECISION_MATRIX.md`
- `VALIDATION_PLAN.md`
- `DESIGN_GATE.md`、`OFFICIAL_RELEASE_ANALYSIS.md`
- B0–B8 各阶段 Review/Rereview/报告
- `B8_IMPLEMENTATION_PLAN.md`、`B8_REVIEW.md`

## 当前快照

| 项 | 值 |
| --- | --- |
| 候选分支 | `codex/enterprise-candidate-1.16.0-20260718` |
| 候选 HEAD | `b0f84651099ab25208b7a177d505505bf7c57324` |
| origin | `b0f84651099ab25208b7a177d505505bf7c57324`（已 push） |
| 官方基线 | `1.16.0` = `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| Alembic 唯一 head | `e7c0a9d2b8f3`（parent `b416e5c4e702`；Phase G 修复后） |
| B8 Reviewer | PASS；B8R-01/02/03 已接受为不阻断 P3 |
| 已接受决策 | A 跳过 Rereviewer；B completeness 暂不扩；C repair 暂不开；D 完整运行验证顺序 D→F→G→H；E push 已完成；F 本台账入库；G P3 保持接受 |

## 全局运行验证矩阵（最重要的一张表）

| 阶段 | 验证内容 | 当前状态 | 需要环境 | 失败会暴露什么 | 预估工作量 |
| --- | --- | --- | --- | --- | --- |
| Phase A | 静态范围与基线 | ✅ 已做（B0/B8 evidence） | git | 越界文件、非官方基线 | 已完成 |
| Phase B | 聚焦单元测试 | ✅ 部分（B4 398、B5 295、B7 21、B8 47+158+61） | Python/Node 环境 | 逻辑回归 | 已完成大部分 |
| Phase C | OpenAPI/contracts 生成 | ✅ B4 两次 deterministic | pnpm | 契约漂移、手写类型 | 已完成 |
| Phase D | migration 图 + 真库升级矩阵 | ✅ 真库 6 行全 PASS（隔离副本） | 隔离 PostgreSQL/备份副本 | 升级失败、数据丢失、uuidv7、双 head | 已完成（6/6 PASS，evidence/phase-d） |
| Phase E | Compose 静态验证 | ✅ B6/B8 静态 | docker compose config | overlay 丢失依赖/安全变量 | 已完成 |
| Phase F | 镜像构建 + 容器身份 | ✅ 已做（`replay-116-b8-phase-f-validator`，PASS，`evidence/phase-f/**`）→ 因 Phase H 发现缺 Phase G 修复，已于 2026-08-14 重建（`replay-116-b8-phase-f-rebuild`，PASS，`evidence/phase-f-rebuild/**`） | Docker build/daemon | image ID 不一致、构建缺文件 | 中 |
| Phase G | 运行验收（browser/API/Agent） | ✅ 已做（`replay-116-b8-phase-g-validator`，`evidence/phase-g/**`；2 个 release-blocking finding，见下） | 完整运行栈 + 浏览器 | 登录/权限/marketplace/Agent/WebSocket/secret | 高 |
| Phase H | 离线包 load + `--pull never` smoke | ⚠️ 已跑（`replay-116-b8-phase-h-validator`，`evidence/phase-h/**`；链机制全 PASS，但当时离线镜像缺 Phase G 修复，见下）。Phase F Rebuild 已重建镜像（新 API image `566bdf4c88cf` 含 `e7c0a9d2b8f3` + `_align_snapshot_to_composition`，B7 reuse gate `-CheckOnly` exit 0）；离线链复跑（load + `--pull never` smoke）未做，仍待运行 | 同一 daemon 模拟（无独立无外网 Docker 目标） | 离线包不可用、含 secret、缺镜像 | 中 |
| 回滚 | 备份/恢复演练 | ✅ 真库演练 PASS（DB 级） | 隔离卷/备份 | 回滚失败、数据回灌问题 | 已完成（evidence/phase-d/rollback-drill） |

## 已接受决策（2026-08-11）

1. A：B8 不再跑 Rereviewer。
2. B：completeness 两脚本暂不扩 scope。
3. C：vector repair 暂不开独立任务。
4. D：运行验证按 Phase D→F→G→H 完整顺序执行（每项仍需单独授权实例/环境）。
5. E：B7/B8 checkpoint 已 push 到 origin（`b0f8465109`）。
6. F：本台账入库；后续每阶段回填状态。
7. G：B8R-01/02/03 保持接受，运行验证发现问题再修。

---

## B0 企业重放护栏

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| 越界检查方式 | 人工 review / 自动 guardrail | 自动 guardrail | 所有后续 Builder | 自动可复现；需维护 |
| AST 范围 | 全文件 / 只查新增修改行 | 完整文件 AST + 新增行区间 | 误报控制 | 防跨 hunk 绕过；不漏历史 |
| 失败模式 | 放行 / fail-closed | fail-closed | 任何解析失败即拒绝 | 安全优先；可能卡住正常提交 |

### 影响范围

`.github/workflows/enterprise-replay-*`、`scripts/ci/check-enterprise-replay-*`、全仓 scope 检查。

### 数据证据

- ✅ 43 个 enterprise replay scope tests PASS。
- ✅ scope check PASS。
- ✅ B0_REREVIEW_2：PASS；跨 hunk 绕过修复后复验。

### 已知限制

- guardrail 只查代码仓库，不查运行时/DB/容器行为。

### 待判断

- 无。已闭环。

---

## B1 Generator model mode 归一化

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| 未知 mode 默认值 | 报错 / `completion` / `chat` | `chat` | 生成器 payload | 兼容旧数据；掩盖未知 mode |
| 旧 localStorage | 迁移 / 读取时归一化 | 读取时归一化 | 老用户 | 不改用户数据；逻辑集中 |
| 测试方式 | 只组件测试 / 纯函数+组件 | 纯函数+组件 | 回归成本 | 8 种输入全覆盖 |

### 影响范围

`web/app/components/app/configuration/config/automatic/**`、`code-generator/**`。

### 数据证据

- ✅ 纯函数测试 + 两组件集成测试 PASS。
- ✅ B1_REREVIEW：P1-1 关闭，PASS。

### 已知限制

- ⚠️ 5 个文件 formatting baseline（`vp check` exit 1）。
- ⚠️ ESLint NOT_RUN（已接受）。
- 未知 mode 静默转 `chat`，未来官方新增 mode 时需重审。

### 待判断

- 是否在发布前清 5 文件 formatting + 跑 ESLint？之前接受为 baseline。

---

## B2 Migration 历史恢复 + 只读 inventory

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| 旧 revision | 删除重建 / 保留原 ID 原语义 | 保留原 ID | 旧企业库升级 | 不破坏历史链；维护面大 |
| 1.16 合并点 | merge 带 DDL / 空 merge | 空 merge `a71e16c0de01` | 升级可审计 | 历史与 schema 分离 |
| stamp | 允许 / 禁止 | 禁止 | 数据完整性 | 逼真升级；慢 |
| inventory | 不查 / 只读先查 | 必须 | B2 启动 | 提供真实基线 |

### 影响范围

四个升级起点：旧企业 1.15、官方 1.15、官方 1.16、空库；B3/B4 schema 依赖。

### 数据证据（B2_INVENTORY）

- PostgreSQL 15.17；旧企业 head `e2f0a9b7c6d5`。
- Weaviate 1.27.0；schema class 与 PostgreSQL 预期完全匹配（缺失 0、额外 0）。
- 1 个 high_quality dataset（class_prefix 存在）。
- ✅ B2_REVIEW：PASS；16 个 migration graph 测试通过。
- ✅ 真库升级矩阵 6/6 PASS（Phase D Validator，隔离副本）：生产 PG15 企业 1.15→1.16、官方 1.15→1.16、PG18 空库、PG18 企业 1.15 应用升级、官方 1.16→1.16、备份/恢复回滚演练。证据：`docs/enterprise/replay-1.16.0/evidence/phase-d/`。

### 已知限制

- ⚠️ MySQL 条件验证未做。
- Weaviate `vectorizer`/`vectorIndexType`/`vectorIndexConfig` 为 UNKNOWN。

### 待判断

- Phase D 真库矩阵已全部 PASS（6/6）；应用级验收仍属 Phase G。

---

## B3 平台管理员后端

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| 首版范围 | 全量管理 / 7 条 route | 7 条 route | API 面 | 可控；能力缺口明确 |
| 授权 | 官方 RBAC / `PLATFORM_ADMIN_EMAILS` | 企业授权 helper | 跨租户安全 | 需求满足；需小心越权 |
| session | 隐式 db.session / 显式 Session | 显式 Session | 事务回滚 | 可测试；改动多 |
| 邀请容量 | 只查不锁 / reservation | 只查不锁 | 并发接受 | 简单；可能超限 |

### 影响范围

platform-admin API、member 数据、B4 contracts、前端导航。

### 数据证据

- ✅ 8 个文件 + service/controller 测试 PASS。
- ✅ B3_REVIEW：PASS，`B3_CODE_ACCEPTED`。
- ✅ 7 条 route 精确，无 member DELETE/owner mutation。

### 已知限制

- ⚠️ 邀请 capacity 不是 reservation；延迟/并发接受可能突破 member limit（ACCEPTED_KNOWN_LIMITATION）。
- member removal、workspace create/delete/archive、owner mutation、密码重置、break-glass 全部 DEFER。

### 待判断

- 这些 DEFER 能力是否在 1.16 发布前补？若需要，应作为独立任务，不能塞进现有链。

---

## B4 智慧广场后端 + schema + contracts

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| 发布快照 | 动态引用 / 提交时复制 / 审核后不可变快照 | 不可变无 secret 快照 | 复制与源解耦 | 稳定；存量大 |
| 复制源 | 任意 DSL / 仅已审核快照 | 仅已审核快照 | 安全 | 防 secret 泄漏 |
| schema 位置 | merge 内 / 独立 revision | `b416e5c4e702` 独立 | 升级路径 | 审计清晰 |
| contracts | 各阶段自己生成 / B4 唯一 | B4 唯一 | 全链类型 | 防漂移；B5 只消费 |
| 回填 | schema 内一次做 / 独立可重试任务 | 独立可重试 | 旧数据 | 可控；复杂 |

### 影响范围

8 条 marketplace route、状态机、数据迁移、Console contracts、B5 前端。

### 数据证据

- ✅ 398 collected / 398 passed。
- ✅ contracts 两次生成 deterministic。
- ✅ 唯一 head `b416e5c4e702`。
- ✅ B4_FINAL_REREVIEW：PASS，0/0/0。

### 已知限制

- ⚠️ `AppDslService.import_app()` 内部 commit → copy 无法承诺完全原子回滚（ACCEPTED）。
- DSL 未来新增字段时 sanitizer 需扩展（ACCEPTED）。
- 真实回填/失败 reconciliation 未运行。

### 待判断

- B8 已计划覆盖“失败 reconciliation 和信息泄漏”，但只是计划；Phase D/G 才能验证。

---

## B5 企业前端全链

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| locale 写入者 | 分散 / B5-E 独占 | B5-E 独占 23 个 locale | i18n 一致性 | 可审；串行 |
| API 调用 | direct fetch / 生成 contracts | 只消费 contracts | 类型安全 | 防漂移；禁手写 |
| 提交交互 | 单 dialog / 专用 resubmit | 专用 resubmit | 用户体验 | 复杂；清晰 |
| first-submit 入口 | 前置依赖 / 独立 | B5-D 独立 | 并行风险 | 解耦 |

### 影响范围

platform-admin 页面、marketplace 浏览/提交/审核/复制、main nav、23 locale。

### 数据证据

- ✅ 14/14 测试文件、295/295 tests PASS。
- ✅ type-check、i18n check PASS。
- ✅ B5_FINAL_REVIEW：PASS，0/0/0。

### 已知限制

- ⚠️ browser/E2E NOT_RUN（5 组浏览器场景全部未跑）。
- ⚠️ `pnpm check` 5 文件 formatting baseline；ESLint NOT_RUN。

### 待判断

- 发布前补真实浏览器回归？范围 5 组，需 Phase G 环境。

---

## B6 Enterprise Compose overlay

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| Compose 策略 | 改官方 / overlay | 官方不动 + overlay | 升级兼容 | 安全；需重审官方变化 |
| 覆盖 service | 全部 / 最小五个 | api/worker/beat/websocket/web | 镜像身份 | 可控 |
| Agent 服务 | 覆盖 / 保持官方 | 保持官方 | Agent 链路 | 官方安全配置保留 |
| logo | 官方改默认 / overlay 展开 | 官方 false + overlay true | 品牌 | 双配置需验证 |
| Redis DB | 只查前缀 / 解析编号 | 解析编号断言不冲突 | 运行隔离 | 更准 |

### 影响范围

企业镜像 tag、五个 runtime、collaboration profile、Agent 依赖。

### 数据证据

- ✅ overlay 74 行。
- ✅ B6_REVIEW：PASS；Phase E 静态断言 S-1..S-9 PASS。
- ✅ `CAN_REPLACE_LOGO` 普通 false / overlay true；Agent key 相等；Redis DB 不冲突。

### 已知限制

- ✅ Phase F build/recreate/image ID 已运行验证：`replay-116-b8-phase-f-validator`（2026-08-11），
  5 runtime 容器 image ID 断言 PASS，`evidence/phase-f/**`。
- ⚠️ Phase G 运行 NOT_RUN。

### 待判断

- Phase F 环境：本地 Docker 还是隔离构建机？

---

## B7 离线 artifact chain

### 决策点

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| 打包模式 | rebuild/smart/reuse | 发布只允许 reuse | 镜像一致性 | 可追溯；限制灵活 |
| dry-run | 允许 build/pull/save | `-CheckOnly` 禁止 | 安全 | 防误操作 |
| 配置包 | 含 1.15 文件 / 只 1.16 | 只 1.16 + 37 env example | 包内容 | 干净；缺旧工具 |
| 插件源 | 平行 mirror / 官方 knob | 官方 knob 透传 | 离线安装 | 不重复造轮子 |
| secret 扫描 | 只查 images/manifest / 全内容 | 全内容三态 | 发布安全 | 更稳；更慢 |

### 影响范围

离线镜像 list、manifest、config archive、插件离线安装、离线目标 smoke。

### 数据证据

- ✅ 21/21 fixture PASS。
- ✅ S-8 独立 clean/hit 行为验证。
- ✅ B7_REREVIEW：PASS。

### 已知限制

- ⚠️ Phase F/G/H NOT_RUN；`.ps1` 运行时 NOT_RUN。
- P3：B7R-03（WARNING 同文件非相邻）、B7R-04（硬编码版本）、B7R-05（ps1 BOM）、B7R-06（裸 volumes 不拦）。

### 待判断

- Phase H 离线目标 smoke 环境：无外网 Docker 目标机/副本。

---

## B8 Vector checker + 发布验证准备

### 已定决策

1. checker 只读，无 repair。
2. 只做 `.sh`，不做 `.ps1`。
3. evidence 缺 = NOT_RUN。
4. Phase D/F/G/H 默认 NOT_RUN，逐项授权。
5. completeness 两脚本当前未授权。
6. evidence/** 只允许授权 Builder/Validator 写。

### Builder 交付

| 文件 | 行数/说明 |
| --- | --- |
| `scripts/check-enterprise-vector-indexes.sh` | 276 行只读 checker |
| `scripts/ci/check-enterprise-vector-indexes-tests.sh` | 47 项断言 |
| `scripts/ci/check-enterprise-vector-indexes-fixtures/**` | fake psql/curl + 4 schema fixture |
| `docs/enterprise/replay-1.16.0/evidence/**` | 11 文件（6 个 force-add `.log`） |

### 数据证据

- ✅ 47/47 checker fixture（独立复跑 exit 0）。
- ✅ backend focused 158 passed、migration graph 61 passed（Builder 环境）。
- ✅ B8_REVIEW：PASS；0 P0/P1/P2。

### 已接受 P3

| ID | 内容 | 影响 | 处置 |
| --- | --- | --- | --- |
| B8R-01 | class_prefix 无 `_Node` 时 checker 假 FAIL | 历史数据若含后缀则无影响 | 接受 |
| B8R-02 | fallback 硬编码 `Vector_index` | 自定义前缀部署假 FAIL | 接受 |
| B8R-03 | wget fallback 未测试且错误解析偏差 | curl 主路径已覆盖 | 接受 |

### ❓ 后续运行验证待办

按已接受决策 D：

1. ~~Phase D：隔离副本真库升级矩阵（PG 15.17 企业 1.15→1.16、官方 1.15→1.16、PG18 空库/应用升级、回滚）~~ ✅ 已完成（`replay-116-b8-phase-d-validator`，6/6 PASS，`evidence/phase-d/**`）。
2. ~~Phase F：build + 五容器 image ID 断言~~ ✅ 已完成（`replay-116-b8-phase-f-validator`，PASS，`evidence/phase-f/**`）。
3. Phase G：完整运行验收（platform-admin/marketplace/Agent 12 场景/Workflow/HITL/WebSocket/browser/E2E/secret）。
4. ~~Phase H：离线 `docker load` + `up --pull never` + smoke + 重复 secret 扫描~~ ⚠️ 已跑（`replay-116-b8-phase-h-validator`，2026-08-12，`evidence/phase-h/**`），结果 FAIL：链机制全 PASS，但发现离线镜像缺 Phase G 修复（见下），须重建镜像后复跑。

---

## 跨阶段风险清单（按暴露点排序）

| 风险 | 暴露阶段 | 当前状态 | 决策 |
| --- | --- | --- | --- |
| migration 升级失败/数据丢失 | Phase D | ✅ 已验（6/6 PASS，隔离副本） | 隔离副本 |
| uuidv7/PG18 不兼容 | Phase D | ✅ 已验（PG18 uuidv7 版本 7；`1c9ba48be8e4` 不重跑） | 必跑 |
| image ID 不一致 | Phase F | ✅ 已验（api==worker==worker_beat==api_websocket，web 为企业 Web image；PASS）；2026-08-14 重建后 API `566bdf4c88cf` != 旧 `cb4d99a45ac1` | 五容器 inspect |
| 浏览器/交互回归 | Phase G | ✅ 已验（E2E 5 组 Playwright 截图 PASS） | E2E 5 组 |
| Agent/WebSocket 故障 | Phase G | ✅ 已验（12 场景；knowledge 绑定已修，见 Phase G 修复；stop 400 非阻断偏差） | 12 场景 |
| secret 泄漏到运行日志/包 | Phase G/H | ✅ 运行扫描已做（真实 key 0 命中；仅 compose 配置含 dev default） | 受保护 pattern |
| 离线包不可用 | Phase H | ⚠️ 链机制跑通但当时 FAIL：Phase F 镜像缺 Phase G 修复 → 2026-08-14 Phase F Rebuild 已重建镜像并通过 B7 reuse gate（exit 0）；离线链复跑待做 | load + `--pull never`；已重 build，复跑后闭环 |
| capacity 非 reservation | 并发邀请 | 已知限制 | 接受/未来修 |
| copy 非原子 | 复制失败 | 已知限制 | 接受/未来修 |
| check 脚本 P3 | 特殊部署 | 已接受 | 运行发现再修 |
| completeness 门禁缺失 | 发布审计 | 未授权 | 人工兜底 |

## Phase G 运行发现（2026-08-12 Validator 回填）

运行验收在隔离栈 `dify-b8-phase-g`（端口 18080）完成。总体：install/login/platform-admin/
Workflow/WebSocket/plugin-dataset-vector/secret/浏览器/E2E 均 PASS；Agent 12 场景大部分 PASS
（chat/Landlock/dual-secret/publish/stop-recovery）。发现 **2 个 release-blocking 运行 bug**：

1. **Marketplace schema 类型不匹配**（`evidence/phase-g/marketplace.log`）
   - B4 migration `b416e5c4e702` 把 `enterprise_marketplace_assets` 和
     `enterprise_marketplace_asset_snapshots` 的 ID/FK 列建成 `VARCHAR(36)`，但 ORM model
     （`api/models/model.py:2847-2848`）用 `StringUUID`（PG `uuid`）。
   - 所有按这些列过滤的查询在 PostgreSQL 上抛 `operator does not exist: character varying = uuid`。
   - 影响：submit/review/copy/unlist 全部 500；升级库和空库都受影响。阻断发布。
2. **Agent 绑定 Knowledge 后对话失败**（`evidence/phase-g/agent-knowledge.log`）
   - roster Agent 的 `agent_soul.knowledge.sets` 绑定数据集后，chat 报
     `CompositorSessionSnapshot layer names must match ... knowledge`（agent_backend
     `agenton/compositor/core.py:314`）。
   - 同一 Agent 去掉 knowledge 后 chat 正常（OpenRouter 实测 PhaseG-OK）。阻断发布。

其余偏差（非阻断）：
- 迁移的 Aliyun/Tongyi 凭据因租户 RSA 私钥在生产 storage（禁止路径）而无法解密；按 G3
  stop-condition，用户提供 OpenRouter key，openrouter 0.1.3 + ollama 1.0.0 从 marketplace 新装。
- agent_backend 停止时 chat 返回 400（含 raw transport message）而非计划中的稳定 503；API/Web
  未 crash，重启后恢复（`agent-backend-stop.log`）。
- 迁移 dataset 的向量 class 对齐 NOT_RUN（生产 Weaviate 数据在禁止路径）；新 dataset 对齐+hit-testing PASS。
- inline agent（workflow agent-composer 节点）仅 API 未跑通（binding 需 UI 路径），记为 NOT_RUN。

## Phase G 修复（Fixer，2026-08-12）

两个 release-blocking finding 已修复（`replay-116-b8-phase-g-fixer`，分支
`ctyun/replay-116-b8-phase-g-fixer`）：

### GPH-01：Marketplace schema 类型不匹配 → 新 migration

- 修复：新增 1 个 Alembic revision（`e7c0a9d2b8f3`，parent `b416e5c4e702`），在
  PostgreSQL 上把 `enterprise_marketplace_assets` 与
  `enterprise_marketplace_asset_snapshots` 的所有 ID/FK 列
  （id、source_app_id、source_tenant_id、submitter_account_id、
  reviewer_account_id、published_snapshot_id、asset_id）由 `VARCHAR(36)` 改为
  `uuid`，使用数据保留的 `ALTER TYPE ... USING col::uuid`；索引/唯一约束/CHECK
  由 PostgreSQL 在列类型重写中保留。其他方言为 no-op（`StringUUID` 已映射为
  `CHAR(36)`）。
- 决策：**不修改** `b416e5c4e702`，只在它之后追加新 revision。
- ⚠️ **企业修复 / 上游对账（upstream reconciliation）**：`e7c0a9d2b8f3` 是
  企业特有修复，官方 Dify 任何版本均不含。未来官方 release 若自行修复或上游化
  这些列，升级前必须把该 revision 与新版官方 migration graph 对账，待官方 schema
  已声明为 `uuid` 后删除本 revision。该说明已写入新 migration 的 docstring。
- 验证：migration graph + marketplace 迁移测试更新为以 `e7c0a9d2b8f3` 为唯一
  head；新增 PG（mock 绑定）下全部 12 列 `ALTER TYPE uuid USING col::uuid` 断言、
  非 PG no-op、downgrade 反转断言。

### GPH-02：Agent 绑定 Knowledge 后对话失败 → 运行时快照对齐

- 修复：`api/clients/agent_backend/request_builder.py` 的
  `build_for_agent_app` / `build_for_workflow_node` 在
  `agent_soul.knowledge.sets` 非空时，若存储的 `session_snapshot` 缺
  `knowledge` 层，则按 composition 层序注入 fresh knowledge 快照条目
  （NEW lifecycle、空 runtime state）；若 snapshot 携带已删除的 knowledge 层则
  丢弃；snapshot 与 composition 已一致时原样透传（knowledge-absent 路径字节级
  兼容）。
- 影响：仅改 API 侧请求构建路径，不触碰 dify-agent/agenton。
- 验证：knowledge-present / knowledge-absent 单测（clients request_builder、
  agent_app runtime_request_builder、workflow agent_v2 runtime_request_builder）。

### 未触碰（非阻断偏差，按任务约束不动）

- agent_backend stop 400、inline-agent NOT_RUN、迁移 vector 对齐 NOT_RUN、
  plugin debug NOT_RUN。

## Phase H 运行发现（2026-08-12 Validator 回填）

离线链机制全部跑通：`build-enterprise-offline.sh -Mode reuse`（复用 Phase F
镜像，exit 0，7.8G tar + manifest + images）→ `build-enterprise-config-package.sh`
（exit 0）→ `check-enterprise-offline.sh`（13 PASS / 0 FAIL / 1 NOT_RUN，synthetic
0600 pattern，只输出布尔）→ `docker load`（12 镜像）→ 隔离 project
`dify-b8-phase-h` `up --pull never`（db_postgres/redis/api/web/nginx，`./volumes/**`
全部重映射到 `dify-b8-phase-h-*` named volumes）→ smoke（nginx 18080 HTTP 200、
api `/health` 200、web `/webpage/signin` 200、`/` 307→/install）→ teardown
`down -v` 后无残留、`docker/volumes/**` 与 1.15 栈均未变。证据：
`evidence/phase-h/**`。

**Release-blocking 发现：Phase F 构建的 API 镜像缺 Phase G 修复。**

- `dify-api-enterprise:1.16.0-enterprise`（`cb4d99a45ac1`，2026-08-11 构建）不含
  Phase G 修复提交 `85b445c0e1`（2026-08-12 合并）。
- 镜像内验证：`migrations/versions/` 无 `e7c0a9d2b8f3`；fresh PostgreSQL 15
  升级到该镜像 head 后 `alembic_version = b416e5c4e702`（不是唯一企业 head
  `e7c0a9d2b8f3`）→ marketplace ID/FK 列保持 `VARCHAR(36)`，GPH-01 500 bug 在
  全新离线安装仍会复现。`request_builder.py` 无 `_align_snapshot_to_composition`
  （GPH-02）→ agent 绑定 knowledge 的 bug 同样未修复。
- 根因：B7 reuse 门禁只比较 `COMMIT_SHA`（携带 version tag，B6R-01），无法区分
  同 tag 的两次构建；Phase H 用镜像内容 vs 候选 HEAD 交叉核对发现漂移。
- 处置（超出 Phase H scope，待协调者）：从候选 HEAD 重建企业 API 镜像（Phase F
  重跑）→ 复跑 Phase H，确认镜像 migration head 为 `e7c0a9d2b8f3` 且
  `request_builder.py` 含修复，离线包才可视为 release-ready。

## Phase F Rebuild（Validator，2026-08-14）

Phase H 处置的第一步已完成：从候选 HEAD 重建企业 API 与 Web 镜像
（`replay-116-b8-phase-f-rebuild`，隔离 project `dify-b8-phase-f-rebuild`，
build only，无 up/容器/端口/卷）。证据：`evidence/phase-f-rebuild/**`。

- 命令：
  `DIFY_ENTERPRISE_VERSION=1.16.0-enterprise COMPOSE_PROFILES=weaviate,postgresql,collaboration
  docker compose -p dify-b8-phase-f-rebuild -f docker/docker-compose.yaml -f
  docker/docker-compose.enterprise.yaml -f /tmp/dify-b8-phase-f-rebuild.override.yaml
  build api web`（exit 0；temp override 复用 Phase F 环境适配：
  `build.network: host` + proxy build-args）。
- 新镜像 ID：API `sha256:566bdf4c88cf1bf3be5f7f6c7c39b338d5f1973ebe10f115050d9ac527930680`
  （!= 旧 `cb4d99a45ac1`）；Web `sha256:b76919e99830040e603d6c5c1e189b839e816f9829b43cb0e44584fe9e5dd725`。
- 镜像内容核对（`docker run --rm` 只读）：`e7c0a9d2b8f3` migration
  `2026_08_12_0000-e7c0a9d2b8f3_align_marketplace_uuid_columns.py` PRESENT；
  `request_builder.py` 含 `_align_snapshot_to_composition` PRESENT；镜像
  migration 文件集 == 仓库 HEAD 文件集（206 文件）。
- B7 reuse gate（加固后）：`scripts/build-enterprise-offline.sh -CheckOnly
  -Version 1.16.0-enterprise -Mode reuse -OutputDir /tmp/b8-phase-f-rebuild-check`
  → exit **0**（ACCEPTS 新 API 镜像）；manifest `enterprise_commit =
  a7dd727ddfad1dce75be6a52ea8d7da18dfb4cb8`（候选 HEAD）；temp 输出目录已删。
- 偏差（诚实记录）：脚本 `OUTPUT_PATH="$REPO_ROOT/$OUTPUT_DIR"`（第 62 行）会
  把绝对 `-OutputDir /tmp/...` 拼接成 `<repo>/tmp/...`；为保持输出在 /tmp，
  临时建了未跟踪符号链接 `<repo>/tmp -> /tmp`，跑完即删（未触碰任何跟踪路径）。
- 未做（NOT_RUN，诚实）：Phase H 离线链复跑（load + `--pull never` boot +
  smoke）；Web 镜像内容核对（Phase G 修复仅后端）。

## B7 reuse gate 加固（Fixer，2026-08-13）

Phase H 根因修复的自动化部分：加固 B7 离线 reuse 门禁，使其不能接受同 tag 的
过期企业镜像。

### 决策

| 决策 | 选项 | 选择 | 影响 | 利弊 |
| --- | --- | --- | --- | --- |
| 内容核对方式 | 比较 COMMIT_SHA 之外再加镜像内容 | `docker run --rm --entrypoint sh` 只读读取 `/app/api/...` | 门禁成本 | 只读不落盘；可 fixture 模拟 |
| 核对内容 | 只 migration / migration + 函数 | migration 文件集 + `request_builder.py` 含 `_align_snapshot_to_composition` | 覆盖 GPH-01 + GPH-02 | 两个 release-blocking finding 都拦 |
| 失败模式 | 放行 / fail-closed | 任一不匹配 exit 1 + 明确诊断 | 构建门禁 | 安全优先 |
| .ps1 | 不镜像 / 镜像 | 镜像相同门禁 | 双平台一致 | 本环境无 pwsh，仅镜像未运行（NOT_RUN，诚实记录） |

### 变更

- `scripts/build-enterprise-offline.sh`：新增只读内容核对
  `verify_enterprise_image_content`（`docker run --rm --entrypoint sh IMAGE -c`），
  在 API 镜像 reuse/smart/`-CheckOnly` 复用路径上强制执行：
  1. 镜像 `/app/api/migrations/versions/*.py` 文件集 == 仓库 `api/migrations/versions`
     当前 HEAD 文件集（缺 `e7c0a9d2b8f3` 即拒绝）；
  2. 镜像 `/app/api/clients/agent_backend/request_builder.py` 必须含
     `_align_snapshot_to_composition`（缺 GPH-02 即拒绝）。
  任一不匹配：stderr 打印差异/缺失说明并 exit 1。参数契约与
  `check-enterprise-offline.sh` 输出不变。
- `scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker`：新增 `run` 分支 +
  `FAKE_DOCKER_MIGRATIONS` / `FAKE_DOCKER_MISSING_FUNCTION`（默认=匹配仓库）。
- `scripts/ci/check-enterprise-offline-tests.sh`：新增 fixture 用例
  （stale 缺 migration、stale 缺函数、匹配镜像 PASS 且必须发生 `docker run` 内容核对）。
- `scripts/build-enterprise-offline.ps1`：镜像 `Test-EnterpriseImageContent`
  （API 镜像 reuse/smart/CheckOnly 路径），与 .sh 行为一致。

### 验证状态

- ✅ `scripts/ci/check-enterprise-offline-tests.sh` 全 PASS（含 3 个新用例）。
- ⚠️ `.ps1` 镜像门禁：NOT_RUN（本环境无 pwsh/Windows）；.sh 为权威实现。
- ❓ 真实 Docker daemon 上对过期镜像的实测拒绝：未做（无旧镜像；fixture 已覆盖逻辑）。

### 不变量保持

- `scripts/ci/check-enterprise-offline.sh` 字节级未动；CLI 契约未动。
- 内容核对只读：`docker run`（create/run/cp/inspect 允许），无 compose up/build/pull/save。
- Web 镜像不做内容核对（Phase G 修复仅涉及后端）。

## 回填规则

每完成一项运行验证：

1. 在对应阶段把 ⚠️ 改为 ✅，附命令、exit、证据文件路径。
2. 在 `docs/enterprise/replay-1.16.0/evidence/**` 写入 artifact（先获得该项授权）。
3. 更新本台账“当前快照”和“跨阶段风险清单”。
4. 若发现新限制，加行并标 ❓，不自动接受。

## 下一步

1. 清理审计已显示 B7/B8 共 16 个实例 git_ready=true、checkpoint 已在远端；删除仍需你逐个/批量授权。
2. 准备 Phase D 运行验证决策单与实例契约（环境、隔离副本、备份、命令、证据）。
3. Phase D 通过后按 D→F→G→H 顺序推进。

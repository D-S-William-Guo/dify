# Dify Enterprise 1.16.0 验证计划

## 1. 目标与硬门禁

本计划用于后续 Builder 和 Reviewer。当前状态为 `DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`；Gate Reviewer 通过前不启动 Builder，通过后也仅授权 B0/B1，B2～B9 暂不授权。本文所有测试均为计划项，不代表已经运行通过。当前任务不修改代码、不启动 Docker、不访问或复制 `docker/volumes`。

发布必须同时证明四件事：源码正确、迁移可升级、运行容器确实包含本轮源码、离线包复用同一批已验证镜像。任一层通过都不能替代下一层。

硬门禁：

1. 基线保持官方 `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`，企业提交可清晰审计。
2. `git diff 1.16.0...HEAD` 不得包含旧源码树、`docker/volumes/**`、真实 `.env`、secret、cache、node_modules 或构建产物。
3. 官方安全修复的回归测试全部保留。
4. Alembic 只有一个最终企业 head `b416e5c4e702`，且空库、官方 1.15、旧企业 1.15 和官方 1.16 路径均按支持矩阵升级。
5. API、worker、worker_beat、api_websocket 使用同一企业 API image ID；Web 使用本轮企业 Web image ID。
6. 离线 manifest 包含 Agent backend/local sandbox，并与通过 runtime 验证的 image IDs/digests 一致。
7. 当前发布阻断组合为 PostgreSQL + Weaviate；MySQL 仅条件验证，不是本轮本地发布阻断项。

### B2 启动前只读 inventory

B2 启动前，必须对旧 1.15 数据库和 volume 完成只读 inventory，记录实际 Alembic head；`enterprise_marketplace_assets` 表结构、行数、状态分布和 `source_app_id`；源应用正常/删除/异常数量；tenant/member/app/workflow/dataset/document/plugin 计数；PostgreSQL 版本；Weaviate class/index；运行镜像和 Compose 配置身份。该步骤不授权 migration、修复或修改 volume；证据不完整时 B2 不得启动。

## 2. 验证阶段

### Phase A：静态范围与基线

执行：

```bash
git rev-parse HEAD
git merge-base 1.16.0 HEAD
git diff --name-status 1.16.0...HEAD
git diff --check
git grep -n 'PLATFORM_ADMIN_EMAILS\|enterprise_marketplace' 1.16.0 -- api web docker
```

期望：merge-base 为官方提交；变更仅为已批准 Builder 任务；未引入 `docker/volumes`；无旧 `console_ns.schema_model`、手写 Console models/service、旧 app context 或 controller 直接 SQLAlchemy。

### Phase B：聚焦单元测试

后端命令统一通过 `uv run --project api`，先跑最小集合：

```bash
UV_CACHE_DIR=.uv-cache uv run --project api pytest \
  api/tests/unit_tests/services/enterprise/test_enterprise_service.py \
  api/tests/unit_tests/services/test_account_service.py
```

Builder 应按实际新文件补以下集合：

- 平台管理员授权/service/controller/contract tests。
- 智慧广场 model/service/controller/contract tests。
- migration graph 和 upgrade tests。
- dataset/hit testing、SSRF parser、MyScale metadata key、auth redirect、member permissions 的官方回归测试。
- vector index checker 的 shell/fixture tests。

前端最小集合：

```bash
pnpm --dir web vitest run <enterprise-focused-specs>
pnpm --dir web type-check
pnpm check
```

包括：生成器 mode 归一化、平台管理员/智慧广场 queries/mutations、main nav 权限、redirect、install/sign-in、i18n 和 generated contract type 使用。

### Phase C：OpenAPI 与生成契约

1. 由 B4 作为唯一生成者运行 `pnpm --dir packages/contracts gen-api-contract`；B3 不提交中间 generated diff，B5 只消费结果。
2. 检查后端 request/response DTO 均出现在 spec。
3. 重新生成 `packages/contracts/generated/api/console/**`。
4. `git diff` 中生成变化必须能追溯到企业 endpoints；禁止手改 generated files。
5. Web 不得新增 `fetch('/console/api/...')`、手写 response type 或 legacy contract loader。
6. 对 400/401/403/404/409 等业务错误做 schema/客户端解析测试。

### Phase D：migration 图与数据库升级

在依赖完整环境执行：

```bash
UV_CACHE_DIR=.uv-cache uv run --project api flask db heads
UV_CACHE_DIR=.uv-cache uv run --project api flask db history
```

要求：

- 单一最终企业 head `b416e5c4e702`。
- 历史 revision `c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5` 均可解析；文件从旧企业候选恢复并保持 revision ID、`down_revision`、`branch_labels`、`upgrade()`/`downgrade()` 历史 DDL 语义。不得重新生成 ID，不得使用 `alembic stamp` 伪造升级状态。
- 空 merge `a71e16c0de01` 的 parents 精确为 `e2f0a9b7c6d5` 与官方 `7a1c2d9e4b60`，其 `upgrade()`/`downgrade()` 为空且不含业务 DDL。
- B4 schema revision `b416e5c4e702` 位于 merge 后，`down_revision = "a71e16c0de01"`；所有 1.16 智慧广场新增列、索引、约束和数据迁移只在此 revision，不能塞进 merge。
- 从官方 1.15 head 升级会执行官方实际新增的 5 个 revision，再收敛到企业 head。
- Release 列表中三个在 1.15 已存在但 1.16 修改的 Agent migrations，以及同样被修改的 uuidv7 migration `1c9ba48be8e4`，不得被错误地当作升级时会重跑。

数据库兼容矩阵（以下均为待执行计划；“必须运行”才可作为本次发布通过证据，“条件运行”不得冒充已执行）：

| 级别 | 数据库/场景 | 起点与操作 | 必验结果 |
| --- | --- | --- | --- |
| 必须运行 | 当前生产 PostgreSQL 版本，企业升级 | 企业 1.15 `e2f0a9b7c6d5` → 1.16 | 官方新链→空 merge→B4；历史资产行/状态、tenant/member/dataset 不丢；最终 head `b416e5c4e702` |
| 必须运行 | 当前生产 PostgreSQL 版本，官方升级 | 官方 1.15 `d9e8f7a6b5c4` → 1.16 | 执行 5 个官方新增 revision、企业历史分支、空 merge、B4，无重复建表 |
| 必须运行 | PostgreSQL 18 空库 | 无表 → 1.16 | 完整 history 成功；`SELECT uuidv7()` 成功且 UUID version 为 7；智慧广场最终表/索引/约束正确 |
| 必须运行 | PostgreSQL 18 应用升级 | 在 PG18 上预置企业 1.15 副本后升级 Dify 1.16 | `1c9ba48be8e4` 的 PG18 兼容路径有效；`SELECT uuidv7()` 成功；数据与最终 head 正确 |
| 必须运行 | PostgreSQL 当前生产版本，官方 1.16 | `7a1c2d9e4b60` → 企业 1.16 | 恢复企业历史分支、执行空 merge 和 B4；无重复建表 |
| 条件运行 | MySQL 空库 | 未来对外交付声明支持 MySQL 时：无表 → 1.16 | `enterprise_marketplace_assets` DDL 成功；`SHOW CREATE TABLE` 验证 JSON 列、`created_at`/`updated_at` 默认值、索引和约束符合设计 |
| 条件运行 | MySQL 企业升级 | 未来对外交付声明支持 MySQL 时：企业 1.15 `e2f0a9b7c6d5` → 1.16 | 历史 DDL 与 B4 migration 均成功；资产数据保留；最终单 head |
| 条件运行 | PostgreSQL 大版本升级与 Dify 升级组合窗口 | 仅当运维坚持同窗：生产 PG 版本副本升级到 PG18，并在同一演练中升级 Dify | 作为独立高风险场景完整重跑备份恢复、uuidv7、数据和业务验收，不得用分开升级结果代替 |
| 条件运行 | 其他官方支持的 PostgreSQL/MySQL 小版本与 vector provider | 该组合进入本次生产支持声明时 | 重跑对应空库、升级和 vector 一致性场景 |
| 不在本次支持范围 | SQLite、MariaDB、低于官方最低版本或未声明数据库 | 任意 | 不声称兼容，不以本地 mock/SQLite 结果替代真实数据库 |

默认并且推荐把“数据库大版本升级”和“Dify 应用升级”放在不同维护窗口：先独立完成数据库升级、稳定与备份，再升级 Dify，以减少同时变化的变量。若必须组合，只有上表的独立高风险演练通过后才能批准。

当前本地发布阻断组合固定为 PostgreSQL + Weaviate，必须覆盖旧企业 PostgreSQL 数据升级、单一 migration head、智慧广场数据和快照回填、用户/workspace/应用/工作流/知识库/插件、Weaviate class/index、hit testing 与完整备份恢复回滚。不得声称本轮已经完成 MySQL 兼容验证。

### Phase E：Compose 静态验证

在启动任何服务前：

```bash
export DIFY_ENTERPRISE_VERSION=1.16.0-enterprise
export COMPOSE_PROFILES=weaviate,postgresql,collaboration
docker compose \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  config -q
docker compose \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  config --images | sort -u
docker compose \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  --profile collaboration config --services
```

检查：

- `api`、`worker`、`worker_beat`、`api_websocket` 指向同一企业 API tag。
- `web` 指向企业 Web tag。
- 包含 `dify-agent-backend:1.16.0`、`dify-agent-local-sandbox:1.16.0`。
- `api`/`worker` 仍依赖 `agent_backend`；agent backend 仍依赖 Redis/plugin daemon/local sandbox。
- collaboration profile 展开后的 service 列表仍包含 `api_websocket`；overlay 不得丢失官方 profile。
- 把 `docker compose config` 的最终展开结果写入权限为 `0600` 的临时文件，用 YAML parser 读取值并作显式相等断言：`services.agent_backend.environment.DIFY_AGENT_INNER_API_KEY == services.api.environment.INNER_API_KEY_FOR_PLUGIN`。比较的是 fallback 展开后的最终值，不是变量名/模板文本；输出只记录 `equal=true/false`，不得打印值。Phase G 还必须证明 agent backend 调用 Dify inner API 成功。
- Landlock 默认开启；Agent server secret 不使用发布环境的开发默认值。
- `DIFY_AGENT_RUN_RETENTION_SECONDS` 未覆盖时等于官方 3 天（259200 秒），允许部署配置显式覆盖并记录；`local_sandbox` 默认无永久持久化，企业 overlay 禁止擅自增加永久共享 volume。
- 解析所有 Redis URL 的 database 编号并断言 agent backend 的编号不与 API 主缓存/session 及 Celery broker/result backend 使用的编号冲突；禁止只比较 URL 字符串前缀。
- 普通官方配置的 `CAN_REPLACE_LOGO` 必须保持官方 1.16 默认 `false`；企业 overlay 必须显式设置并展开为 `true`。不得修改官方源码默认。
- 企业 overlay 没有覆盖官方 volume、network、healthcheck 和安全变量。

上述临时 Compose 展开文件属于 secret-bearing artifact：仅在受保护临时目录存在，验证完成后安全清理，不进入日志、CI artifact、manifest 或仓库。

### Phase F：镜像构建与容器身份

仅在 Phase A–E 通过后构建：

1. 构建企业 API 和 Web image，版本均为 `1.16.0-enterprise`。
2. recreate API 相关服务与 Web；包含 collaboration profile 和 Agent 新服务。
3. 记录 image ID、RepoDigest、`COMMIT_SHA`、启动时间和 Compose project/workdir。
4. 检查所有 bind mount 指向当前 1.16 部署目录，无旧工作树路径。
5. 分别用 `docker inspect` 读取 `api`、`worker`、`worker_beat`、`api_websocket`、`web` 容器的不可变 `.Image` ID；断言 `api == worker == worker_beat == api_websocket`，且该 ID 是本轮企业 API image ID。`web` 必须等于本轮企业 Web image ID。tag 文本相同不能代替 image ID 相等。

示例检查目标：

```text
api, worker, worker_beat, api_websocket -> same enterprise API image ID
web                                     -> current enterprise Web image ID
agent_backend                           -> official 1.16 Agent backend image
local_sandbox                           -> official 1.16 local sandbox image
```

### Phase G：运行验收

#### 安装、登录和权限

- 空库 `/install` 完成初始化，首次登录按官方流程完成语言/时区。
- 升级库不显示 install。
- `ALLOW_REGISTER=false` 与 `ALLOW_CREATE_WORKSPACE=false` 在 UI/API 一致。
- 邀请/激活、OAuth/SSO 回跳保持当前部署；外部绝对 URL、协议相对 URL 和编码绕过被拒绝。
- editor 可查看允许的日志，但不能管理成员或修改 trace config。

#### 默认 workspace 与平台管理员

- Enterprise enabled：新账号 best-effort 加入默认 workspace；API 故障不阻断注册。
- 非平台管理员所有 `/platform-admin/**` 均 403，不能通过伪造 tenant/header 绕过。
- 首版只验平台管理员身份、workspace list/detail/rename、member list/invite/non-owner role update，共
  7 条 route；验证 tenant scope、owner mutation 拒绝、邀请时 capacity 和允许操作的日志。
- 负向验证必须确认没有 member DELETE route；member removal 不验成功，current/last workspace 删除 guard
  不属于本轮必须通过项。owner mutation、workspace create/delete/archive、密码重置、需新审计表的高风险
  操作与 break-glass 均不存在；B3 不新增 audit model。
- `RBAC_ENABLED=true` 时 invite/role mutation 必须 503 fail-closed，且无 DB/token/task 副作用。
- ACTIVE 未加入的 invitation token 必须 `requires_setup=false`，接受时不得错误触发 PENDING setup；
  新建或既有 PENDING invitation token 必须 `requires_setup=true`，并在隔离 integration 中证明官方
  `/activate` 收集 setup fields 后将 Account 激活为 ACTIVE。
- unit 验证邀请时精确 capacity guard。官方 `/activate` 不复查 capacity，B3 也不修改它；ACTIVE 邀请无
  reservation，B3 Redis 锁不覆盖接受路径，延迟/并发接受可能突破 workspace member limit。此结果必须标记
  `KNOWN_LIMITATION`，不得声称最终 workspace limit 不会被突破。

#### 智慧广场

- Workspace A editor/owner 提交，普通成员按产品权限被允许或拒绝。
- Admin 审核批准/拒绝/下架；状态机拒绝非法转换。
- Workspace B 只能看到已批准资产，复制到 B 后 source secret 不泄漏。
- 发布时保存无 secret DSL、版本、内容哈希、冻结时间和来源；复制只使用已审核快照。源 app 删除后仍可复制，修改不影响已发布版本；更新必须重新提交/审核/版本化。旧来源存在时回填无密钥快照，丢失/异常时标记待处理或下架且不得猜测；复杂回填通过独立、可重试、有 inventory 和失败恢复的数据迁移执行。
- 重复提交/重复复制有幂等或明确冲突结果。

#### Agent App Beta

执行前固定两个隔离部署 A/B（不同 `DIFY_AGENT_SERVER_SECRET_KEY`）、测试 workspace、可用模型、测试 Knowledge、无敏感内容的文件和可控 Tool。下表的具体 API 路径全部是期望路径，须与生成 OpenAPI 对齐，并非已经实现的事实；若路径或响应 schema 漂移必须先更新并复审本表，不能临场猜测。每行必须保存请求 ID、实际状态、响应 schema 校验、页面截图和对应 service 日志时间窗。

| 场景 | 前置数据 | UI / 期望 API 路径（须与生成 OpenAPI 对齐） | 期望 HTTP / 响应字段 | 期望页面状态 | 失败判定 | 截图与日志证据 |
| --- | --- | --- | --- | --- | --- | --- |
| roster Agent | 空 roster、可用 model | UI 创建；期望 `POST /console/api/agent` 后 `GET /console/api/agent/{agent_id}`（须与生成 OpenAPI 对齐） | 创建 201；读取 200；含 `id`、`app_id`、`role`、配置状态 | roster 出现唯一 Agent，可进入编辑页 | 状态码/schema 不符、重复项、刷新丢失 | roster/编辑页截图；API 与 agent backend 日志 |
| Skills | 已创建 Agent、受控 Skill 包 | 上传/安装；期望 `/console/api/agent/{agent_id}/config/skills/upload`（须与生成 OpenAPI 对齐），并读取 skills 列表/inspect | 上传 200；返回 skill 标识/状态；inspect 200 且文件清单符合包 | Skill 显示已安装并可选；失败包显示可操作错误 | 安装假成功、越权文件、错误被吞、重启后无状态 | Skill 状态截图；API/plugin/agent backend 日志 |
| 文件 | 小文本文件与超限/非法文件 fixture | UI 上传；期望 `POST /console/api/agent/{agent_id}/config/files`（须与生成 OpenAPI 对齐），再 preview/download | 合法文件 200，含文件名/size；非法输入为 contract 定义的 4xx | 文件可预览/删除，错误提示明确 | 内容错、跨 Agent 可读、非法文件 2xx | 文件页截图；API/agent backend/local sandbox 日志 |
| Knowledge | 已索引测试 Knowledge，含唯一答案 | 在 Agent 配置绑定 Knowledge 后保存并调试提问 | 保存 200；调试消息 200/stream success；响应含引用/答案字段 | 配置显示数据集；回答显示预期引用 | 未检索、引用跨 tenant、错误静默降级 | 配置与回答截图；API/worker/vector 日志 |
| Tools | 成功 Tool 和确定失败 Tool | 绑定 Tool，分别执行成功/失败输入 | 保存 200；成功调用返回 tool output；失败调用返回结构化错误而非 500 crash | tool 状态、调用步骤和错误可见 | 参数泄漏、失败挂起、后台未清理 | Tool trace 截图；API/plugin daemon/agent backend 日志 |
| 发布 Web App | roster 配置完整且未发布 | 期望 `POST /console/api/agent/{agent_id}/publish`（须与生成 OpenAPI 对齐），再读取 Web App/public 配置 | publish 200；含 published/version 状态；公开读取 200 且无 secret | Published 状态和公开 URL 可见 | 未发布即可访问、响应含 secret、版本不固定 | 发布页与公开页截图；API/agent backend 日志 |
| 最终用户对话 | 已发布 Agent Web App | 匿名/授权用户打开公开 URL，发送唯一 prompt，随后取消一次长响应 | 页面请求 200；消息 stream 成功；取消 endpoint 200；响应含 message/task id | 能看到 Agent 回复、引用和已取消状态 | 500、无限 loading、取消后仍继续执行 | 对话前后截图；web/API/agent backend 日志 |
| Workflow 引用 roster Agent | 已发布 roster Agent、空 Workflow | 在 Agent v2 节点选择 roster；运行固定输入 | composer/save 200；workflow run 200/stream；输出 schema 含预期字段 | 节点显示 roster binding，run panel 输出正确 | binding 变 inline、输出丢字段、跨 workspace 引用 | 节点与 run detail 截图；API/worker/agent backend 日志 |
| inline Agent | Workflow Agent v2 节点 | 期望 `PUT /console/api/apps/{app_id}/workflows/draft/nodes/{node_id}/agent-composer`（须与生成 OpenAPI 对齐）保存 inline 配置，validate 后运行 | save/validate 200；`binding_type=inline_agent`；运行输出匹配 schema | inline 编辑器保留配置，刷新后不变 | 偷存 roster、校验与运行不一致、输出类型错 | composer 与输出截图；API/worker/agent backend 日志 |
| agent_backend 停止 | 有可运行 Agent；记录健康基线 | 停止 agent_backend，发起调试/Workflow run，再恢复服务 | 新请求 503，响应含稳定错误 `code`/`message` 且不含内部 secret；API/Web 不 crash；恢复后同请求 200 | 明确“服务不可用/可重试”；恢复后页面可继续 | 非 503、假成功、API crash、永久脏 running 状态 | 错误与恢复截图；API/worker/agent backend 容器事件日志 |
| 超时/重连/取消/清理 | 可控慢 Tool、可断开的浏览器网络 | 触发超时；中断 stream 后重连；调用 stop/cancel；等待 retention/cleanup job | 同步超时请求 504 或异步 stream 以结构化 `run_failed` 终止（按对应接口固定）；重连 200 且不重复消息；取消 200；最终 terminal 状态 | timeout/cancel 状态明确，可重试；无幽灵输出 | 状态/事件不符、无限 running、重复消息、取消无效、临时文件/run 未清理 | 四阶段截图；API/worker/WebSocket/agent backend/sandbox 日志及清理 inventory |
| Landlock 边界 | sandbox 当前工作目录含测试文件 | Shell 读取当前目录文件；尝试读 `/etc/passwd`、写工作目录外路径 | 允许路径成功；越界操作为权限拒绝/结构化 tool error，不返回目标内容 | 成功与拒绝结果清楚，Landlock 仍 enabled | 能读取 `/etc/passwd`、越界写成功、overlay 关闭隔离 | 结果截图；agent backend/local sandbox 审计日志 |
| 两套 secret token 隔离 | A/B 使用不同非默认 server secret | A 生成 stub token：A 内调用成功；同 token 调 B；反向重复 | 同部署 2xx；跨部署 401/403 且无解密细节；响应不回显 token | 合法会话可用，跨部署访问被拒 | token 跨部署可用、500、日志泄漏 token/key | A/B 结果截图；两边 agent backend/API 脱敏日志 |

所有预期状态码在执行前必须与生成 OpenAPI 对齐；若实现 contract 与本表冲突，Builder 必须先提出设计变更并更新/复审本表，不能在执行记录中临场替换。任一场景缺截图或缺对应日志证据视为未执行。

#### Workflow、HITL 与 WebSocket

- workflow create/run/import/export、失败 settlement、retry details。
- HITL pause→表单→resume，刷新后状态恢复；并行 human input 和 timeout。
- 两浏览器 workflow collaboration，多 worker、断线重连、顺序一致。
- API websocket 容器确实使用企业 API image ID。

#### Plugin、Dataset 与向量索引

- marketplace plugin callback、权限、cache；本地 `.difypkg` 安装与签名失败。
- 离线镜像源下 plugin 依赖安装。
- 对从 1.15 升级且使用自定义 OpenAI API key 的 provider，读取升级后的 API type；验证官方默认已转为 Responses API，并分别用目标模型执行一次成功请求。若自定义兼容端点只支持 Chat Completions，必须显式保留兼容配置或阻断升级，不能静默套用新默认。
- dataset create/upload/index/hit testing；索引异常必须在 UI/API 显示。
- 非法 MyScale metadata key 被拒绝；API tool schema URL 走 SSRF helper。
- 智慧广场图标、内容、依赖或导入流程若处理外部 URL，必须通过官方 SSRF proxy/helper，并用 loopback、link-local、私网、重定向到私网等 fixture 验证拒绝；禁止直接网络 client 获取。
- 迁移 dataset 的关系库计数与向量 class/collection 对齐，hit testing 有可见结果。

#### Secret 扫描

从受保护的运行环境读取本次部署的 Agent server/inner key、Plugin daemon key 及其他批准扫描项，在权限为 `0700` 的临时目录内生成 `0600` pattern 文件。不得把真实 secret 放入命令参数、shell trace、日志、仓库或 CI artifact；扫描命令只输出“目标 + 是否命中”，命中内容本身必须脱敏。扫描后安全清理 pattern、Compose 展开结果和中间日志。

扫描范围必须包括：API、worker、api_websocket、plugin daemon、agent backend、local sandbox 的 stdout/stderr；Web 可访问日志；Compose 最终展开结果；离线包 manifest；安装脚本 stdout/stderr。任何真实 key/token 命中均阻断发布。开发默认 pattern 也要扫描，但仅报告文件/服务位置和分类，禁止把真实生产值写进证据。

### Phase H：离线包验证

在 Phase F/G 完成后用 `Mode=reuse`：

1. 脚本拒绝 COMMIT_SHA 不一致或缺失的企业镜像。
2. `images-*.txt` 与 Compose `config --images` 集合一致。
3. manifest 记录版本、基线、企业 commit、image tag、ID/digest。
4. tar 内容扫描排除 `.env`、secret、`docker/volumes/**`、`.git`、cache、node_modules、`.venv`、`.next`。
5. 配置包包含所有 `docker/envs/**/*.env.example`，特别是 dify-agent/local-sandbox。
6. 扫描所有 env example 和可运行配置中的官方开发默认 `DIFY_AGENT_SERVER_SECRET_KEY`。真实 secret 绝不允许入包；开发默认值只能出现在 example，且相邻位置必须有显眼的 `WARNING: DEVELOPMENT ONLY, REPLACE IN PRODUCTION`。默认 key 无 WARNING 或进入可运行配置时阻断发布。
7. 生产安装流程必须在受保护环境为 `DIFY_AGENT_SERVER_SECRET_KEY` 生成全新随机 secret，写入不打包、不记录日志的部署 secret store；禁止复制 example 默认值。安装脚本证据只记录已生成/已注入的布尔结果和指纹，不记录 secret。
8. 对 manifest、安装脚本输出与解包后的配置重复 Phase G 的 secret 扫描；临时 pattern 文件使用后安全清理。
9. 在无外网目标 `docker load`，用 `--pull never` 启动并重复最小 G 阶段 smoke。

## 3. volume 升级验证协议

本节是对后续运维/验证人员的要求，不授权当前任务或 Builder 脚本自动访问 volume。

1. 旧环境停止写入，由运维创建数据库、storage、Redis、plugin 和 vector store 的可恢复备份。
2. 建立隔离升级副本；源 volume 只读且不被新 Compose 直接挂载。
3. 记录升级前 inventory：Alembic head、核心表行数、智慧广场状态分布、tenant/member join、apps/workflows/datasets/documents/segments、plugin 列表、vector classes/collections。
4. 在副本运行 migration；不得 `stamp` 跳过 revision，不得使用旧工作树启动服务。
5. 记录升级后同一 inventory 和异常；允许新增官方/企业 schema，不允许无说明的数据减少。
6. 对智慧广场、dataset/vector、Agent runtime/session 做抽样业务验证。
7. 失败时停止，不自动删除/recreate volume；用备份恢复到新的隔离目标并复现。
8. 成功后才制定生产窗口；生产升级仍需独立备份和回滚点。

### 唯一受支持的回滚方法

不支持依赖 Alembic `downgrade` 的原地回滚，也不支持在已迁移 volume 上直接启动 1.15。唯一受支持的方法是：

1. 停止全部 1.16 服务并阻止新的写入。
2. 隔离已经迁移的数据库、storage、Redis、plugin 和 vector volume，不删除、不复用给 1.15。
3. 从升级前的完整一致性备份恢复到新的恢复目标。
4. 恢复经归档的 1.15 配置与镜像，确认 image IDs/配置版本均属于 1.15。
5. 启动 1.15，并验证账户、workspace/member、应用、工作流、知识库、插件、上传文件和向量数据。
6. 对照升级前 inventory/抽样哈希确认恢复完整，再决定是否重新开放写入。

1.16 运行期间产生的数据默认不会自动回灌到 1.15。若业务要求回灌，必须另行设计、评审和演练数据迁移；它不属于普通回滚，也不能在事故现场临时执行。

特别断言：

- `alembic_version` 从 `e2f0a9b7c6d5` 或官方 head 收敛到唯一企业 head。
- `enterprise_marketplace_assets` 行数和状态不因 merge migration 改变。
- Postgres 有 completed documents 时，目标 vector store 必须存在对应 class/collection；只看 UI 列表不算通过。
- plugin 数据、上传 storage 和 Redis 丢失不能被“应用能打开”掩盖。
- 不复制旧 sandbox dependencies 到离线发布包；Agent/local sandbox 依赖由 1.16 镜像和明确持久化策略提供。
- Agent run retention 默认采用官方 3 天（259200 秒）作为初始值，允许部署配置覆盖并记录；local sandbox 默认不持久化，企业 overlay 禁止增加永久共享 volume。
- agent backend Redis database 编号不得与主服务缓存/session、Celery broker 或 result backend 使用的编号冲突；升级前后均记录实际展开编号。

## 4. 安全回归清单

- SQL 注入：MyScale metadata key allowlist/validation。
- SSRF：API tool schema、智慧广场图标/内容（若有外链）全部通过 SSRF proxy/helper。
- Open redirect：登录、SSO、OAuth、邀请、公开 Web App。
- RBAC：editor/member/admin/platform-admin 边界，tenant scope，trial/recommended app。
- Sandbox：workflow_id/plan 检查、special workflow 禁止、Landlock。
- Secret：DSL copy 无 secret，Agent key/Plugin key 不进日志/manifest，真实 `.env` 不打包。
- Dependency：不恢复 1.15 lockfile；CVE 升级版本保持。

## 5. 失败判定与证据留存

下列任一项直接阻断合并/发布：

- 非唯一 migration head 或任一路径无法升级。
- 旧企业 revision 无法解析、智慧广场数据丢失。
- 企业 endpoint 未进入生成 contract，或 Web 使用手写 API 类型。
- controller 新增 direct SQLAlchemy、service 隐式 `db.session` 事务。
- API runtime image IDs 不一致，或离线包与验证镜像不一致。
- 漏掉 Agent backend/local sandbox，或安全 secret/隔离使用开发默认。
- 任何 SQLi/SSRF/open redirect/RBAC/sandbox 回归。
- 配置/镜像包包含 volume、真实 secret 或运行数据。

每一阶段保存：命令、退出码、commit、image IDs、测试报告、migration 前后 inventory、浏览器用例结果和已知限制。不得用口头“已验证”替代可复现证据。

# Dify Enterprise 1.16.0 验证计划

## 1. 目标与硬门禁

本计划用于后续 Builder 和 Reviewer。当前架构任务不修改代码、不启动 Docker、不访问或复制 `docker/volumes`。

发布必须同时证明四件事：源码正确、迁移可升级、运行容器确实包含本轮源码、离线包复用同一批已验证镜像。任一层通过都不能替代下一层。

硬门禁：

1. 基线保持官方 `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`，企业提交可清晰审计。
2. `git diff 1.16.0...HEAD` 不得包含旧源码树、`docker/volumes/**`、真实 `.env`、secret、cache、node_modules 或构建产物。
3. 官方安全修复的回归测试全部保留。
4. Alembic 只有一个企业 head，且空库、官方 1.15、旧企业 1.15 三条路径均可升级。
5. API、worker、worker_beat、api_websocket 使用同一企业 API image ID；Web 使用本轮企业 Web image ID。
6. 离线 manifest 包含 Agent backend/local sandbox，并与通过 runtime 验证的 image IDs/digests 一致。

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

1. 运行仓库官方 Console OpenAPI 生成/一致性命令。
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

- 单一企业 head。
- 历史 revision `c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5` 均可解析。
- 新 merge 同时连接 `e2f0a9b7c6d5` 与官方 `7a1c2d9e4b60`。
- 从官方 1.15 head 升级会执行官方实际新增的 5 个 revision，再收敛到企业 head。
- 三个在 1.15 已存在但 1.16 修改的 Agent migrations，不得被错误地当作升级时会重跑。

数据库矩阵：

| 起点 | 预置状态 | 必验结果 |
| --- | --- | --- |
| 空库 | 无表 | 完整 upgrade；智慧广场表/索引存在；单 head |
| 官方 1.15 | `d9e8f7a6b5c4` | 执行 5 个官方新增 migration + 企业分支；数据不丢 |
| 旧企业 1.15 | `e2f0a9b7c6d5`，含智慧广场行 | 执行官方新链 + 新 merge；资产行/状态保留 |
| 官方 1.16 | `7a1c2d9e4b60` | 只执行企业历史分支/merge；无重复建表失败 |

至少在 PostgreSQL 运行完整矩阵；MySQL 运行空库和旧企业升级。PostgreSQL 18 还要保留官方 uuidv7 migration 测试。

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
```

检查：

- `api`、`worker`、`worker_beat`、`api_websocket` 指向同一企业 API tag。
- `web` 指向企业 Web tag。
- 包含 `dify-agent-backend:1.16.0`、`dify-agent-local-sandbox:1.16.0`。
- `api`/`worker` 仍依赖 `agent_backend`；agent backend 仍依赖 Redis/plugin daemon/local sandbox。
- `DIFY_AGENT_INNER_API_KEY` 来源与 `INNER_API_KEY_FOR_PLUGIN` 一致。
- Landlock 默认开启；Agent server secret 不使用发布环境的开发默认值。
- 企业 overlay 没有覆盖官方 volume、network、healthcheck 和安全变量。

### Phase F：镜像构建与容器身份

仅在 Phase A–E 通过后构建：

1. 构建企业 API 和 Web image，版本均为 `1.16.0-enterprise`。
2. recreate API 相关服务与 Web；包含 collaboration profile 和 Agent 新服务。
3. 记录 image ID、RepoDigest、`COMMIT_SHA`、启动时间和 Compose project/workdir。
4. 检查所有 bind mount 指向当前 1.16 部署目录，无旧工作树路径。

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
- 平台管理员跨 workspace 列表/成员操作正确；当前 workspace、最后 workspace、owner 和 seat limit guard 生效。
- 所有高风险操作产生可检索审计；若 Builder 任务未交付审计，则密码重置/归档不得进入发布范围。

#### 智慧广场

- Workspace A editor/owner 提交，普通成员按产品权限被允许或拒绝。
- Admin 审核批准/拒绝/下架；状态机拒绝非法转换。
- Workspace B 只能看到已批准资产，复制到 B 后 source secret 不泄漏。
- 源 app 删除、归档或修改时行为符合已确认的快照/引用语义。
- 重复提交/重复复制有幂等或明确冲突结果。

#### Agent App Beta

- 新建 roster Agent，配置 model/Skills/files/tools/knowledge，发布为 Web App 并对话。
- 工作流引用 roster Agent；创建 inline Agent；输出传递正确。
- shell 命令和文件操作在 Landlock 边界内；越界读取/写入失败。
- Agent backend 断线/超时/重连/取消/失败清理可观测。
- `DIFY_AGENT_SERVER_SECRET_KEY` 非默认，stub token 可用且不能跨部署复用。

#### Workflow、HITL 与 WebSocket

- workflow create/run/import/export、失败 settlement、retry details。
- HITL pause→表单→resume，刷新后状态恢复；并行 human input 和 timeout。
- 两浏览器 workflow collaboration，多 worker、断线重连、顺序一致。
- API websocket 容器确实使用企业 API image ID。

#### Plugin、Dataset 与向量索引

- marketplace plugin callback、权限、cache；本地 `.difypkg` 安装与签名失败。
- 离线镜像源下 plugin 依赖安装。
- dataset create/upload/index/hit testing；索引异常必须在 UI/API 显示。
- 非法 MyScale metadata key 被拒绝；API tool schema URL 走 SSRF helper。
- 迁移 dataset 的关系库计数与向量 class/collection 对齐，hit testing 有可见结果。

### Phase H：离线包验证

在 Phase F/G 完成后用 `Mode=reuse`：

1. 脚本拒绝 COMMIT_SHA 不一致或缺失的企业镜像。
2. `images-*.txt` 与 Compose `config --images` 集合一致。
3. manifest 记录版本、基线、企业 commit、image tag、ID/digest。
4. tar 内容扫描排除 `.env`、secret、`docker/volumes/**`、`.git`、cache、node_modules、`.venv`、`.next`。
5. 配置包包含所有 `docker/envs/**/*.env.example`，特别是 dify-agent/local-sandbox。
6. 在无外网目标 `docker load`，用 `--pull never` 启动并重复最小 G 阶段 smoke。

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

特别断言：

- `alembic_version` 从 `e2f0a9b7c6d5` 或官方 head 收敛到唯一企业 head。
- `enterprise_marketplace_assets` 行数和状态不因 merge migration 改变。
- Postgres 有 completed documents 时，目标 vector store 必须存在对应 class/collection；只看 UI 列表不算通过。
- plugin 数据、上传 storage 和 Redis 丢失不能被“应用能打开”掩盖。
- 不复制旧 sandbox dependencies 到离线发布包；Agent/local sandbox 依赖由 1.16 镜像和明确持久化策略提供。

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
